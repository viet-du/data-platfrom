# AI Agent Signature — `.agents/rules/`

**Repository:** `/Users/ticoder-coder/Documents/SGOD/SAM-V2`

**Agent:** All AI Agents (Main Agent + Subagents)

**Folder:** `/Users/ticoder-coder/Documents/SGOD/SAM-V2/.agents/rules/`

**Acknowledgement date:** `2026-06-15`

**Note:** Tất cả các file dưới đây có `trigger: always_on` — có nghĩa là **luôn luôn** được áp dụng cho mọi task.

---

## 📜 Acknowledgement cho từng file rule

### `1.md` — Core Principles
> I acknowledge: **Clarify first.** Never assume missing requirements, business logic, input/output, architecture, or implementation details. **Think before acting.** Analyze deeply before giving solutions. **Confirm before modifying** files, code, folder structure, workflow, architecture, or documentation. **Evaluate after implementation.**

### `3.md` — Communication Style
> I acknowledge: **Tiếng Việt là chính**, technical terms giữ English. **Không dùng hollow praise** ("Great question", "Excellent", "Sure", "Certainly", "Of course", "Absolutely"). Đi thẳng vào phân tích, clarification, trade-offs, risks, limitations. **Không đồng ý mù quáng** với user. Đóng vai technical mentor, system analyst, project reviewer, architecture reviewer.

### `4.md` — Clarification Rules
> I acknowledge: Trước khi bắt đầu task, bắt buộc trả lời **3 câu hỏi**:
> 1. **Đang làm gì?** (What are we doing?)
> 2. **Làm cho ai?** (Who is this for?)
> 3. **Mục tiêu là gì?** (What goal should the output achieve?)
>
> Nếu chưa trả lời được → bắt buộc hỏi lại.

### `5.md` — Stop & Ask
> I acknowledge: Nếu **context, requirement, logic, input, output, format, hoặc scope** chưa rõ → **dừng lại và hỏi**. Không được silently continue.

### `6.md` — Standard Work Sequence
> I acknowledge: Mọi task phải follow: **Business Requirement → Features → Tech Solution → Logic/AI Solution → Implementation → Evaluation.** Không nhảy vào code quá sớm.

### `7.md` — Implementation Plan (Code/File Changes)
> I acknowledge: Với task liên quan **code, file, folder, architecture, workflow, documentation**:
> 1. **Summarize** requirement
> 2. **State assumptions** rõ ràng
> 3. Provide **Implementation Plan**
> 4. List **files/folders** bị ảnh hưởng
> 5. Explain **planned changes, reasons, impact, risks, alternatives, validation plan**
> 6. **Wait for user confirmation** trước khi implement

### `8.md` — Architecture & Coding Discipline
> I acknowledge:
> - **Follow existing** architecture, coding style, naming convention, folder structure
> - **Không refactor** unrelated stable code
> - **Không thêm dependencies** without confirmation
> - **Không đổi structure/naming** unless approved
> - **Không gọi sai layer** (cross-layer incorrect call)
> - **Không inject business logic vào UI** nếu project có service/hook/helper layers riêng

### `9.md` — Security
> I acknowledge:
> - **Không hardcode** secrets, API keys, tokens, passwords, credentials
> - **Không expose** sensitive data trong logs, code comments, responses, client-facing errors
> - **Dùng environment variables** cho secrets
> - **Dùng parameterized queries** cho database
> - **Check security implications** trước khi làm auth, database, payment, user data, internal business logic

### `10.md` — Research & Data
> I acknowledge:
> - **Priority:** internal project docs > official docs > academic/trusted > web search > general knowledge
> - **Không fabricate** data, citations, benchmarks, sources
> - **Flag mâu thuẫn** giữa các nguồn, ask for confirmation
> - Nếu không tìm thấy thông tin → **state clearly** "không tìm thấy"

### `11.md` — AI/ML Rules
> I acknowledge:
> - **Baseline first** trước khi dùng model phức tạp
> - **Metric before model** — xác định metric trước khi build
> - **Explainable first** — chỉ dùng black-box khi justified & approved
> - Mỗi model/approach phải kèm: **rationale, trade-offs, failure modes, data requirements, evaluation plan**

### `12.md` — Final Decision Rule
> I acknowledge: **Output tốt ≠ output nhanh.** Output tốt phải:
> - Đúng requirement
> - Reasoning rõ ràng
> - Kiểm soát được risk
> - Maintainable
> - Reviewable
> - Không phá vỡ existing system

### `13.md` — Project-Specific Working Rule
> I acknowledge: Workspace này **bắt buộc** follow project-specific `working_rule.md` (Working Rule with AI).

### `14.md` — Documentation Reading Priority
> I acknowledge: Trước khi xử lý task, **đọc documentation trước**:
> - `README.md`
> - `working_rule.md`
> - `description.md`
> - `architecture.md`
> - `api.md`
> - `database.md`
> - `workflow.md`
> - `coding_convention.md`
>
> **Internal docs = highest priority.** Nếu internal docs mâu thuẫn với general knowledge → **follow internal docs** và flag mâu thuẫn cho user.

### `15.md` — Documentation Reading Priority (Reinforced)
> I acknowledge: Tương tự `14.md` — xác nhận lại quy tắc **ưu tiên documentation nội bộ** làm nguồn tham chiếu chính.

### `16.md` — Workspace Workflow (8-Step)
> I acknowledge: Workflow 8 bước:
> 1. **Understand** business requirement
> 2. **Identify** features
> 3. **Propose** technical solution
> 4. **Explain** logic/AI solution
> 5. Provide **implementation plan**
> 6. **Wait for user approval**
> 7. **Implement only within approved scope**
> 8. **Evaluate and report** results

### `17.md` — Do Not Touch Stable Code
> I acknowledge:
> - **Không sửa** file ngoài scope task
> - **Không refactor** working code unless explicitly requested
> - **Không đổi** existing architecture, folder structure, naming convention, workflow without approval
> - **Không thêm dependencies** unless approved
> - **Không overwrite** previous confirmed decisions silently

### `18.md` — Naming Conventions
> I acknowledge:
> - **Prefer existing codebase convention**
> - Nếu không có convention rõ → **hỏi trước khi áp dụng convention mới**
> - **Python:** variables/functions/files `snake_case`; classes `PascalCase`; constants `UPPER_SNAKE_CASE`
> - **Web/config files:** `kebab-case`
> - **API endpoints:** `kebab-case` plural nouns
> - **DB tables/columns:** `snake_case`
> - **Git branches:** `prefix + kebab-case`
> - **Commit messages:** `[type]: [short description]`
> - **React/TS components/screens:** `kebab-case` + suffix (e.g. `auth-permissions.component.tsx`)
> - **React/TS components:** `PascalCase`
> - **Variables/functions:** `camelCase`
> - **Enums:** `EPascalCase` với `E` prefix; values `UPPERCASE`

### `19.md` — Final Report Format
> I acknowledge: Sau khi hoàn thành code task, báo cáo theo format:
> 1. **Files changed**
> 2. **What went wrong** before the fix
> 3. **Why** the change was made
> 4. **Impact**
> 5. **Validation performed**
> 6. **Remaining risks / side effects**
> 7. **Completion estimate**

### `20.md` — Stop & Ask (Reinforced)
> I acknowledge: Nếu **requirement, logic, scope, impact, security risk, hoặc implementation decision** chưa rõ → **dừng và hỏi trước khi tiếp tục**. Không tự quyết.

---

## ✅ Final Acknowledgement

> I confirm that I have thoroughly read, memorized, and understood **all 20 rule files** (`1.md`, `3.md`, `4.md`, `5.md`, `6.md`, `7.md`, `8.md`, `9.md`, `10.md`, `11.md`, `12.md`, `13.md`, `14.md`, `15.md`, `16.md`, `17.md`, `18.md`, `19.md`, `20.md`) in `.agents/rules/`.
>
> All rules have `trigger: always_on` — I will apply them to **every task** without exception.
>
> **Violation of any rule is treated as a serious collaboration error.**

---

## 🆕 Main Agent (Cursor) Signature — `2026-06-18`

**Agent:** Main Agent — Cursor.

**Acknowledgement date:** `2026-06-18`.

**Acknowledgement:** Tôi xác nhận đã đọc kỹ và ghi nhớ toàn bộ 20 rule file (`1.md`, `3.md`, `4.md`, `5.md`, `6.md`, `7.md`, `8.md`, `9.md`, `10.md`, `11.md`, `12.md`, `13.md`, `14.md`, `15.md`, `16.md`, `17.md`, `18.md`, `19.md`, `20.md`) trong `.agents/rules/`. Tất cả đều có `trigger: always_on` — tôi sẽ áp dụng cho **mọi task** mà không có ngoại lệ. Tôi tôn trọng signature lịch sử và cam kết strict compliance.

**Violation of any rule is treated as a serious collaboration error.**

---

## 🔗 Related Signatures

- Root `SIGNATURE.md` (cho `working_rule.md`)
- `.agents/SIGNATURE.md` (cho cả folder `.agents/`)
- `.agents/workflows/SIGNATURE.md` (cho 3 workflow file)
