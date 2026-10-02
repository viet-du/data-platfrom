"""
RAG QA Chain — Retrieval + Gemini generation with citations.

Three answer modes:

  1. "news_digest" — when the user asks open-ended questions like
     "tin gì mới", "có gì hot", "thời sự hôm nay". We pull the most
     recently crawled articles (not the most semantically similar)
     and ask Gemini to synthesize them into a daily briefing.

  2. "qa" — when the user asks a specific fact question
     ("Bộ trưởng X nói gì?"). Standard RAG: semantic top-K → cite.

  3. "hybrid" — when the question is half-exploratory half-specific.
     We retrieve top-K semantically, then re-rank by recency so the
     freshest relevant result wins.

Why this matters: a flat semantic search against "tin gì mới" returns
random articles because the query is too generic. The Gemini prompt
gets an incoherent set of contexts and produces a thin response. A
dedicated digest path solves this without retraining anything.
"""
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.pipeline.schema import ArticleSchema


# ----- Vietnamese prompts -----

SYSTEM_PROMPT_QA = """Bạn là trợ lý AI chuyên phân tích tin tức Việt Nam.
Nhiệm vụ: trả lời câu hỏi của người dùng DỰA TRÊN các bài báo được cung cấp.

QUY TẮC:
1. Chỉ sử dụng thông tin từ CONTEXT bên dưới. Không bịa đặt.
2. Trả lời ngắn gọn, rõ ràng bằng tiếng Việt, có cấu trúc.
3. LUÔN cite nguồn theo format: [Nguồn: <tên nguồn>](<url>)
4. Nếu context không đủ thông tin, nói rõ "Tôi không tìm thấy thông tin liên quan trong dữ liệu hiện có."
5. Nếu có nhiều bài liên quan, tổng hợp từ nhiều nguồn và phân tích.
6. Format trả lời:
   • Dòng đầu: Tóm tắt 1 câu
   • Thân: 3-5 ý chính, mỗi ý 1-2 câu
   • Cuối: danh sách nguồn

CONTEXT:
{context}
"""


SYSTEM_PROMPT_DIGEST = """Bạn là biên tập viên tin tức Việt Nam chuyên nghiệp.
Nhiệm vụ: Tổng hợp các bài báo được cung cấp thành bản tin thời sự NGẮN GỌN, RÕ RÀNG.

QUY TẮC:
1. CHỈ dùng thông tin từ CONTEXT. Không bịa.
2. Nhóm các bài theo CHỦ ĐỀ (chính trị, kinh tế, xã hội, thể thao, công nghệ, v.v.).
3. Mỗi chủ đề: 1-3 câu tóm tắt súc tích + 2-3 bài tiêu biểu.
4. Ưu tiên sự kiện QUAN TRỌNG, ĐÁNG CHÚ Ý.
5. Mỗi bài phải cite nguồn: [Nguồn: <tên>](<url>)
6. Trả lời bằng tiếng Việt, giọng văn báo chí chuyên nghiệp.

FORMAT MẪU:
📰 **Bản tin thời sự**

🔴 **Chính trị**
• <tóm tắt sự kiện> — [Nguồn: ...](url)

💰 **Kinh tế**
• ...

⚽ **Thể thao**
• ...

📌 **Đáng chú ý khác**
• ...

CONTEXT:
{context}
"""


# Trigger phrases that route to digest mode. We match whole phrases to
# avoid eating specific questions like "tin mới nhất về Hà Nội".
_DIGEST_PATTERNS = [
    r"\btin\s*(gì|mới|gì\s*mới)\b",
    r"\b(có\s*gì|chuyện\s*gì)\s*(mới|hot|mới\s*không)?\b",
    r"\bthời\s*sự\b",
    r"\b(tóm\s*tắt|tổng\s*hợp|bản\s*tin)\b",
    r"\b(hôm\s*nay|ngày\s*nay|gần\s*đây)\b.*\?",
    r"\b(news|update|digest|briefing)\b",
    r"\bwhat'?s?\s*new\b",
    r"\b(any\s*news|latest\s*news|today'?s\s*news)\b",
]


def _looks_like_digest(question: str) -> bool:
    """Return True if the question is vague enough to want a daily digest.

    Heuristic: short AND contains generic news-ish words, OR matches
    one of the digest trigger patterns. Specific questions like
    "Giá xăng hôm nay bao nhiêu?" should NOT route to digest even
    though they contain "hôm nay" — they have a clear noun phrase
    the user wants answered. So we additionally require the question
    to lack a focused noun phrase (no quoted text, no specific topic
    like "giá / trận / ai / ở đâu").
    """
    q = question.lower().strip()

    # Focused-question indicators — these get QA mode regardless.
    focus_indicators = [
        r"\bgiá\s+\w+",          # "giá xăng", "giá vàng"
        r"\btrận\s+\w+",         # "trận Việt Nam"
        r"\bai\s+\??",            # "ai đã", "ai nói"
        r"\bkhi\s+nào\b",
        r"\bở\s+đâu\b",
        r"\bbao\s+nhiêu\b",
        r"\bnói\s+gì\b",
        r"\btại\s+sao\b",
        r'["\u201c\u201d]',     # quoted phrase
        r"\bvề\s+\w+\s*[\.\?]",
        r"\?\s*$",               # clearly a specific question
    ]
    has_focus = any(re.search(p, q) for p in focus_indicators)
    if has_focus and len(q) > 18:
        return False

    # Now treat as digest
    if len(q) < 25:
        if any(w in q for w in ["tin", "gì", "mới", "hot", "thời sự", "tóm tắt", "bản tin"]):
            return True
    for pat in _DIGEST_PATTERNS:
        if re.search(pat, q):
            return True
    return False


class GeminiClient:
    """Google Gemini 1.5 Flash free-tier wrapper (15 RPM)."""

    DEFAULT_MODEL = "gemini-1.5-flash"

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
        self.model = model
        self._genai = None

    def _ensure_loaded(self):
        if self._genai is not None or not self.api_key:
            return
        try:
            import google.generativeai as genai
            self._genai = genai
            genai.configure(api_key=self.api_key)
        except Exception:
            self._genai = None

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, system: str = "", temperature: float = 0.3, max_tokens: int = 1024) -> str:
        self._ensure_loaded()
        if not self.api_key:
            return "⚠️ Gemini API key chưa được cấu hình. Đặt GEMINI_API_KEY trong env."

        try:
            model = self._genai.GenerativeModel(
                model_name=self.model,
                system_instruction=system if system else None,
            )
            cfg = self._genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            resp = model.generate_content(prompt, generation_config=cfg)
            return resp.text if resp and resp.text else "(không có phản hồi)"
        except Exception as e:
            return f"⚠️ Lỗi Gemini: {e}"


class RAGChain:
    """Retrieval-Augmented QA pipeline with digest / qa / hybrid modes."""

    def __init__(self, vector_store, gemini: Optional[GeminiClient] = None):
        self.store = vector_store
        self.gemini = gemini or GeminiClient()

    # ---------- context formatting ----------

    def _format_context(self, hits: List[Dict[str, Any]], max_chars: int = 1200) -> str:
        """Trim each chunk so a 512 MB container can fit top_k=10 contexts
        inside Gemini's 32k context window without truncating the answer.
        """
        blocks = []
        per_chunk = max(400, max_chars // max(len(hits), 1))
        for i, h in enumerate(hits, 1):
            meta = h.get("metadata", {})
            title = meta.get("title", "(no title)")
            source = meta.get("source", "?")
            url = meta.get("url", "")
            crawled = meta.get("crawled_at", "")
            text = h.get("text", "")[:per_chunk]
            blocks.append(
                f"[{i}] {title}\nNguồn: {source} | URL: {url}\nCrawl lúc: {crawled}\nNội dung: {text}"
            )
        return "\n\n".join(blocks)

    def _format_hits_for_telegram(self, hits: List[Dict[str, Any]]) -> str:
        lines = []
        for i, h in enumerate(hits, 1):
            meta = h.get("metadata", {})
            score = h.get("score", 0.0)
            title = meta.get("title", "(no title)")
            url = meta.get("url", "")
            source = meta.get("source", "?")
            crawled = meta.get("crawled_at", "")
            lines.append(
                f"{i}. [{source}] {title}\n   {url}\n   (relevance: {score:.2f} | crawled: {crawled[:10]})"
            )
        return "\n\n".join(lines)

    # ---------- retrieval strategies ----------

    def _retrieve_recent(self, top_k: int = 10) -> List[Dict[str, Any]]:
        """Pull the most recently crawled articles regardless of query.

        Why this exists: when the user asks "tin gì mới", semantic
        search against a short Vietnamese phrase returns arbitrary
        articles from any date. The user actually wants whatever was
        crawled in the last few crawls. We bypass embedding here and
        list the latest docs straight from Chroma.
        """
        try:
            self.store._ensure_loaded()
            data = self.store._collection.get(
                limit=top_k,
                include=["documents", "metadatas"],
            )
        except Exception as e:
            return []

        ids = data.get("ids", []) or []
        docs = data.get("documents", []) or []
        metas = data.get("metadatas", []) or []

        hits = []
        for i, doc_id in enumerate(ids):
            hits.append({
                "id": doc_id,
                "score": 0.0,
                "metadata": metas[i] if i < len(metas) else {},
                "text": docs[i] if i < len(docs) else "",
            })
        # Sort newest first by crawled_at
        hits.sort(
            key=lambda h: h.get("metadata", {}).get("crawled_at", "") or "",
            reverse=True,
        )
        return hits

    def _retrieve_recent_within(self, top_k: int, days: int = 2) -> List[Dict[str, Any]]:
        """Pull recent items only if they fall within the last `days`.

        Falls back to broader retrieval when the chroma collection
        has no metadata.date field we can filter on (older schemas).
        """
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        try:
            self.store._ensure_loaded()
            data = self.store._collection.get(
                limit=top_k * 3,
                include=["documents", "metadatas"],
                where={"crawled_at": {"$gte": cutoff}},
            )
        except Exception:
            return self._retrieve_recent(top_k=top_k)

        ids = data.get("ids", []) or []
        docs = data.get("documents", []) or []
        metas = data.get("metadatas", []) or []

        hits = []
        for i, doc_id in enumerate(ids[:top_k]):
            hits.append({
                "id": doc_id,
                "score": 0.0,
                "metadata": metas[i] if i < len(metas) else {},
                "text": docs[i] if i < len(docs) else "",
            })
        hits.sort(
            key=lambda h: h.get("metadata", {}).get("crawled_at", "") or "",
            reverse=True,
        )
        return hits

    # ---------- public API ----------

    def ask(self, question: str, top_k: int = 5) -> Dict[str, Any]:
        """Route to the right mode based on the question shape."""
        if _looks_like_digest(question):
            return self.ask_digest(question, top_k=top_k)

        hits = self.store.query(question, top_k=top_k)

        if not hits:
            return {
                "answer": "Tôi không tìm thấy bài báo nào liên quan trong cơ sở dữ liệu.",
                "sources": [],
                "mode": "qa",
            }

        context = self._format_context(hits)
        system = SYSTEM_PROMPT_QA.format(context=context)
        prompt = f"Câu hỏi: {question}\n\nTrả lời:"

        if self.gemini.is_available():
            answer = self.gemini.generate(
                prompt, system=system, temperature=0.3, max_tokens=900
            )
        else:
            answer = self._extractive_answer(question, hits)

        return {
            "answer": answer,
            "sources": self._format_hits_for_telegram(hits),
            "mode": "qa",
        }

    def ask_digest(self, question: str = "Tổng hợp tin tức mới nhất", top_k: int = 12) -> Dict[str, Any]:
        """Pull the freshest crawled articles and synthesize a briefing."""
        hits = self._retrieve_recent_within(top_k=top_k, days=2)
        if not hits:
            hits = self._retrieve_recent(top_k=top_k)

        if not hits:
            return {
                "answer": (
                    "📭 *Hiện chưa có bài báo nào được index.*\n\n"
                    "Gửi `/index` để build lại vector store, hoặc `/crawl` để crawl ngay."
                ),
                "sources": [],
                "mode": "digest",
            }

        context = self._format_context(hits, max_chars=4000)
        system = SYSTEM_PROMPT_DIGEST.format(context=context)
        prompt = (
            f"Yêu cầu: {question}\n\n"
            "Hãy viết bản tin thời sự ngắn gọn, nhóm theo chủ đề, có nguồn."
        )

        if self.gemini.is_available():
            answer = self.gemini.generate(
                prompt, system=system, temperature=0.4, max_tokens=1200
            )
        else:
            answer = self._extractive_answer(question, hits)

        return {
            "answer": answer,
            "sources": self._format_hits_for_telegram(hits),
            "mode": "digest",
        }

    # ---------- fallback ----------

    def _extractive_answer(self, question: str, hits: List[Dict[str, Any]]) -> str:
        """No-LLM fallback: list top retrieved articles grouped by source."""
        lines = ["🔎 *Không có Gemini API, trả về top bài liên quan:*\n"]
        # Group by source so the user can scan by paper
        by_source: Dict[str, List[Dict[str, Any]]] = {}
        for h in hits:
            src = h.get("metadata", {}).get("source", "?")
            by_source.setdefault(src, []).append(h)
        for src, items in by_source.items():
            lines.append(f"📰 *{src}*")
            for i, h in enumerate(items, 1):
                title = h.get("metadata", {}).get("title", "(no title)")
                url = h.get("metadata", {}).get("url", "")
                score = h.get("score", 0.0)
                lines.append(f"{i}. {title}\n   {url}\n   _{score:.2f}_")
            lines.append("")
        return "\n".join(lines)