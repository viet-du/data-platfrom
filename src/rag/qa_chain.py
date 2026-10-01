"""
RAG QA Chain - Retrieval + Gemini generation with citations.
"""
import os
from typing import List, Dict, Any, Optional

from src.pipeline.schema import ArticleSchema


SYSTEM_PROMPT_VI = """Bạn là trợ lý AI chuyên phân tích tin tức Việt Nam.
Nhiệm vụ: trả lời câu hỏi của người dùng DỰA TRÊN các bài báo được cung cấp.

QUY TẮC:
1. Chỉ sử dụng thông tin từ CONTEXT bên dưới. Không bịa đặt.
2. Trả lời ngắn gọn, rõ ràng bằng tiếng Việt.
3. LUÔN cite nguồn theo format: [Nguồn: <tên nguồn>](<url>)
4. Nếu context không đủ thông tin, nói "Tôi không tìm thấy thông tin liên quan trong dữ liệu hiện có."
5. Nếu có nhiều bài liên quan, tổng hợp từ nhiều nguồn.

CONTEXT:
{context}
"""


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
    """Retrieval-Augmented QA pipeline."""

    def __init__(self, vector_store, gemini: Optional[GeminiClient] = None):
        self.store = vector_store
        self.gemini = gemini or GeminiClient()

    def _format_context(self, hits: List[Dict[str, Any]]) -> str:
        blocks = []
        for i, h in enumerate(hits, 1):
            meta = h.get("metadata", {})
            title = meta.get("title", "(no title)")
            source = meta.get("source", "?")
            url = meta.get("url", "")
            text = h.get("text", "")[:800]
            blocks.append(f"[{i}] {title}\nNguồn: {source} | URL: {url}\nNội dung: {text}")
        return "\n\n".join(blocks)

    def _format_hits_for_telegram(self, hits: List[Dict[str, Any]]) -> str:
        lines = []
        for i, h in enumerate(hits, 1):
            meta = h.get("metadata", {})
            score = h.get("score", 0.0)
            title = meta.get("title", "(no title)")
            url = meta.get("url", "")
            source = meta.get("source", "?")
            lines.append(f"{i}. [{source}] {title}\n   {url}\n   (relevance: {score:.2f})")
        return "\n\n".join(lines)

    def ask(self, question: str, top_k: int = 5) -> Dict[str, Any]:
        hits = self.store.query(question, top_k=top_k)

        if not hits:
            return {
                "answer": "Tôi không tìm thấy bài báo nào liên quan trong cơ sở dữ liệu.",
                "sources": [],
            }

        context = self._format_context(hits)
        system = SYSTEM_PROMPT_VI.format(context=context)
        prompt = f"Câu hỏi: {question}\n\nTrả lời:"

        if self.gemini.is_available():
            answer = self.gemini.generate(prompt, system=system)
        else:
            # Fallback: extractive summary if Gemini unavailable
            answer = self._extractive_answer(question, hits)

        return {
            "answer": answer,
            "sources": self._format_hits_for_telegram(hits),
        }

    def _extractive_answer(self, question: str, hits: List[Dict[str, Any]]) -> str:
        """No-LLM fallback: list top retrieved articles."""
        lines = ["🔎 *Không có Gemini API, trả về top bài liên quan:*\n"]
        for i, h in enumerate(hits, 1):
            meta = h.get("metadata", {})
            title = meta.get("title", "(no title)")
            url = meta.get("url", "")
            source = meta.get("source", "?")
            score = h.get("score", 0.0)
            lines.append(f"{i}. [{source}] *{title}*\n   {url}\n   _{score:.2f}_")
        return "\n\n".join(lines)
