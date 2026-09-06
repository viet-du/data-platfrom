# AI Agent Signature — `.gemini/`

**Repository:** `/Users/ticoder-coder/Documents/SGOD/SAM-V2`

**Agent:** All AI Agents (Main Agent + Subagents)

**Folder:** `/Users/ticoder-coder/Documents/SGOD/SAM-V2/.gemini/`

**Acknowledgement date:** `2026-06-15`

---

## 📂 Rule Sources Acknowledged

### 📄 `.gemini/settings.json`

```json
{
  "mcpServers": {
    "nx-mcp": {
      "type": "stdio",
      "command": "npx",
      "args": ["nx", "mcp"]
    }
  },
  "contextFileName": "AGENTS.md"
}
```

> I acknowledge that **Gemini (Google AI / Antigravity)** is configured for this workspace with:
>
> - **MCP server:** `nx-mcp` (Nx Model Context Protocol) — chạy với `npx nx mcp`
> - **Context file name:** `AGENTS.md` — file context chính mà Gemini sẽ tìm và load
>
> ⚠️ **Quan trọng:** `contextFileName: "AGENTS.md"` có nghĩa là Gemini sẽ tự động đọc file `AGENTS.md` (nếu có) làm context. Hiện tại repo chưa có file `AGENTS.md` ở root — chỉ có `working_rule.md`. Có thể cần tạo `AGENTS.md` sau nếu Gemini yêu cầu.

### 📁 `.gemini/commands/`

| File | Mô tả |
|---|---|
| `monitor-ci.toml` | **Monitor CI Command** cho Gemini — tương tự `.cursor/commands/monitor-ci.md`, orchestrator cho Nx Cloud CI pipeline. |

### 📁 `.gemini/skills/`

| Skill | Mô tả |
|---|---|
| `nx-workspace/` | Explore Nx workspace — projects, tasks, configuration, dependencies |
| `nx-generate/` | Generate code với Nx generators |
| `nx-plugins/` | Find và add Nx plugins |
| `nx-run-tasks/` | Run tasks trong Nx workspace |
| `link-workspace-packages/` | Link workspace packages trong monorepos |
| `monitor-ci/` | Monitor Nx Cloud CI pipeline và handle self-healing fixes |

### 📜 Lịch sử signature (trong `working_rule.md`)

> **Antigravity (Gemini AI Agent)** đã có signature lịch sử:
>
> > **Representative Agent:** Antigravity (Gemini AI Agent)
> > **Acknowledgement date:** `2026-06-08`
> >
> > I confirm that I have thoroughly read, memorized, and understood the project-wide working contract in `working_rule.md`, as well as the shared agent rules and workflows in `.agents`, and the agent-specific configurations in `.claude`, `.codex`, `.cursor`, and `.gemini`...

---

## ✅ Acknowledgement

> I confirm that I have thoroughly read and understood the configuration in `.gemini/`. I acknowledge that:
>
> 1. **Gemini (Google AI / Antigravity)** đang hoạt động với **MCP server `nx-mcp`** (chạy `npx nx mcp` — khác với Codex là `nx-mcp@latest --minimal`).
> 2. **Context file name = `AGENTS.md`** — Gemini sẽ tìm file này. Hiện chưa có trong repo, có thể cần tạo sau nếu Gemini yêu cầu.
> 3. Tận dụng các **`nx-*` skills** tương tự như Cursor khi làm task Nx.
> 4. Gemini signature lịch sử (2026-06-08) được **tôn trọng** và không thay thế — signature mới này (2026-06-15) bổ sung đại diện cho **All AI Agents**.
> 5. Tuân thủ `working_rule.md` và tất cả rules trong `.agents/`.
>
> **Violation of any Gemini-specific configuration rule is treated as a serious collaboration error.**

---

## 🆕 Main Agent (Cursor) Signature — `2026-06-18`

**Agent:** Main Agent — Cursor (đại diện cho AI đang trực tiếp làm việc với user).

**Acknowledgement date:** `2026-06-18`.

**Acknowledgement:** Tôi xác nhận đã đọc và hiểu cấu hình `.gemini/settings.json` (Gemini + MCP `nx mcp`, context file `AGENTS.md`). Tôi tôn trọng signature lịch sử Antigravity (2026-06-08) và sẽ tận dụng Nx skills khi cần. Đồng thời tuân thủ `working_rule.md` và toàn bộ rules trong `.agents/`.

**Note về AGENTS.md:** Hiện repo chưa có file `AGENTS.md` ở root — chỉ có `working_rule.md`. Tôi sẽ dùng `working_rule.md` làm context chính cho đến khi `AGENTS.md` được tạo (nếu cần).

**Violation of any Gemini-specific configuration rule is treated as a serious collaboration error.**

---

## 🔗 Related Signatures

- Root `SIGNATURE.md` (cho `working_rule.md`)
- `.agents/SIGNATURE.md` (cho `.agents/`)
- `.claude/SIGNATURE.md` (cho `.claude/`)
- `.codex/SIGNATURE.md` (cho `.codex/`)
- `.cursor/SIGNATURE.md` (cho `.cursor/`)

---

## 🔁 Re-Acknowledgement / Signature — `2026-06-20`

**Agent:** Main Agent (Cursor).

**Acknowledgement date:** `2026-06-20`.

**Acknowledgement:** Tôi xác nhận đã đọc lại `.gemini/settings.json` (MCP `npx nx mcp`, context file `AGENTS.md` chưa có — dùng `working_rule.md` thay thế). Tôn trọng signature lịch sử Antigravity 2026-06-08 và Main Agent Cursor 2026-06-18. Sẽ tận dụng Nx skills khi cần. Cam kết tuân thủ `working_rule.md` + toàn bộ rules trong `.agents/`.

**Violation of any Gemini-specific configuration rule is treated as a serious collaboration error.**
