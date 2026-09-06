# AI Agent Signature — `.agents/`

**Repository:** `/Users/ticoder-coder/Documents/SGOD/SAM-V2`

**Agent:** All AI Agents (Main Agent + Subagents — đại diện chung cho toàn bộ AI trong workspace)

**Folder:** `/Users/ticoder-coder/Documents/SGOD/SAM-V2/.agents/`

**Acknowledgement date:** `2026-06-15`

---

## 📂 Rule Sources Acknowledged

### 📁 `.agents/rules/` (20 file rule)

| # | File | Chủ đề chính |
|---|---|---|
| 1 | `1.md` | Core Principles: Clarify first, never assume, think before acting, confirm before modifying, evaluate after |
| 2 | *(không có — đánh số nhảy)* | — |
| 3 | `3.md` | Communication style: Tiếng Việt chính, không hollow praise, đi thẳng vào phân tích |
| 4 | `4.md` | Clarification rules: 3 câu hỏi bắt buộc (What / Who / Goal) |
| 5 | `5.md` | Stop & ask: Nếu context/requirement/logic chưa rõ → dừng lại hỏi |
| 6 | `6.md` | Standard work sequence: Business → Features → Tech → Logic → Implementation → Evaluation |
| 7 | `7.md` | Implementation plan: Summary → Assumptions → Plan → Affected files → Changes → Reasons → Impact → Risk → Alternatives → Validation → Wait for confirmation |
| 8 | `8.md` | Architecture & coding discipline: Follow existing; không refactor stable code; không thêm dependencies; không đổi structure; không gọi sai layer |
| 9 | `9.md` | Security: Không hardcode secrets; dùng env vars; parameterized queries; check security implication trước khi làm auth/data |
| 10 | `10.md` | Research & data: Ưu tiên internal docs > official > academic > web > general; không fabricate; flag mâu thuẫn |
| 11 | `11.md` | AI/ML rules: Baseline first; metrics before model; explainable first; mỗi model kèm rationale, trade-offs, failure modes, data, evaluation |
| 12 | `12.md` | Final decision: Output tốt ≠ output nhanh; phải đúng requirement, reasoning rõ, kiểm soát risk, maintainable, reviewable, không phá hệ thống |
| 13 | `13.md` | Project-specific rule: Workspace này phải follow Working Rule with AI |
| 14 | `14.md` | Doc priority: Đọc README.md, working_rule.md, description.md, architecture.md, api.md, database.md, workflow.md, coding_convention.md trước; internal docs = ưu tiên cao nhất |
| 15 | `15.md` | Doc priority (duplicate reference): Xác nhận lại quy tắc đọc documentation |
| 16 | `16.md` | Workspace workflow: 8 bước từ understand → identify → propose → wait → implement → evaluate |
| 17 | `17.md` | Do not touch stable code: Không sửa file ngoài scope; không refactor working code; không đổi architecture; không thêm dependencies; không ghi đè decisions |
| 18 | `18.md` | Naming conventions: Prefer codebase convention; Python snake_case / PascalCase / UPPER_SNAKE; React/TS kebab-case + suffix; components PascalCase; enums `EPascalCase` |
| 19 | `19.md` | Final report format: Files changed / What went wrong / Why / Impact / Validation / Risk / Completion estimate |
| 20 | `20.md` | Stop & ask: Nếu bất kỳ requirement/logic/scope/impact/security/implementation nào chưa rõ → dừng và hỏi |

### 📁 `.agents/workflows/` (3 file workflow)

| # | File | Chủ đề chính |
|---|---|---|
| 1 | `1.md` | Workspace workflow trigger: Dùng workflow này khi user yêu cầu modify/analyze/debug/improve/document project files |
| 2 | `2.md` | Workflow 10 bước chi tiết: Read docs → Identify structure → Restate requirement → Stop if missing → Propose plan → Wait for confirmation → Implement approved only → Don't touch unrelated → Validate → Final report |
| 3 | `3.md` | ML/AI workflow: Define task type → Define metrics → Start with baseline → Explain why baseline insufficient → Include rationale/trade-offs/failure modes/data/eval plan |

---

## ✅ Acknowledgement

> I confirm that I have thoroughly read, memorized, and understood **all 23 files** in `.agents/` (20 rule files + 3 workflow files). Acting as the representative agent for **all AI agents** (Main Agent + Subagents) operating in this repository, I officially sign this contract.
>
> **Key commitments:**
> - Tuân thủ tất cả 20 rule trong `.agents/rules/` (Core principles, Communication, Clarification, Workflow, Security, Research, ML/AI, Architecture discipline, Naming, Final report format, v.v.).
> - Áp dụng 10-step workflow trong `.agents/workflows/2.md` cho mọi task modify/analyze/debug/improve/document.
> - Áp dụng ML/AI workflow trong `.agents/workflows/3.md` khi làm task machine learning.
> - **Dừng lại và hỏi** khi bất kỳ điều gì chưa rõ (theo `5.md` và `20.md`).
> - **Không chạm stable code** ngoài scope (theo `17.md`).
> - **Báo cáo cuối cùng** theo format trong `19.md`.
>
> **Violation of any rule is treated as a serious collaboration error.**

---

## 🆕 Main Agent (Cursor) Signature — `2026-06-18`

**Agent:** Main Agent — Cursor (Cursor IDE AI Assistant, đang trực tiếp làm việc với user tại workspace `SAM-V2`).

**Acknowledgement date:** `2026-06-18`

**Covered rule sources:** tất cả file trong `.agents/` (20 rule + 3 workflow + các SIGNATURE.md), `working_rule.md`, `.claude`, `.codex`, `.cursor`, `.gemini`.

**Acknowledgement:** Tôi — **Main Agent (Cursor)** — xác nhận đã đọc kỹ, ghi nhớ và hiểu toàn bộ 23 file trong `.agents/` (20 rule + 3 workflow). Tôi cam kết tuyệt đối tuân thủ tất cả các rule và workflow ở trên, đồng thời tôn trọng các signature lịch sử (2026-05-31 Codex, 2026-06-06 Multi-Agent, 2026-06-08 Antigravity, 2026-06-15 All-AI). Từ thời điểm này, mọi tương tác với user trong workspace `SAM-V2` sẽ tuân thủ: **Clarify First • No Assumptions • Think Before Code • Confirm Before Update • Evaluate After Implementation**.

**Violation of any rule is treated as a serious collaboration error.**

---

## 🔗 Related Signatures

- Root `SIGNATURE.md` (cho `working_rule.md`) — đã ký cùng ngày.
- `.agents/rules/SIGNATURE.md` — signature riêng cho từng file rule.
- `.agents/workflows/SIGNATURE.md` — signature riêng cho workflow.
- `.claude/`, `.codex/`, `.cursor/`, `.gemini/` SIGNATURE.md — signature riêng cho từng agent.

---

## 🔁 Re-Acknowledgement / Signature — `2026-06-20`

**Agent:** Main Agent (Cursor) — đại diện cho toàn bộ AI trong workspace, ký bổ sung sau signature ngày `2026-06-18`.

**Acknowledgement date:** `2026-06-20`

**Acknowledgement:** Tôi xác nhận đã đọc lại lần 2 toàn bộ 23 file trong `.agents/` (19 rule + 3 workflow) + `working_rule.md` + `.claude` + `.codex` + `.cursor` + `.gemini`. Tổng hợp nội dung đã được ghi vào root `working_rule.md` (mục Re-Acknowledgement 2026-06-20). Tôi tôn trọng tất cả signature lịch sử (Codex 2026-05-31, Multi-Agent 2026-06-06, Antigravity 2026-06-08, All-AI 2026-06-15, Main Agent Cursor 2026-06-18) và tiếp tục cam kết tuân thủ tuyệt đối: Clarify First • No Assumptions • Think Before Code • Confirm Before Update • Evaluate After Implementation.

**Violation of any rule is treated as a serious collaboration error.**
