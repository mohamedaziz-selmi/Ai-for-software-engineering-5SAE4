# AI Usage Log

Record of how AI assistants were used to build this module. One entry per working session. Raw evidence (screenshots, exported chats) goes in `docs/ai-usage/`. Never include API keys or other secrets.

## Entry template

### YYYY-MM-DD | Tool (Claude Code / Claude chat / Codex / other) | Topic

- **Goal:** what I wanted to achieve
- **Key prompts (verbatim):**
  > paste the important prompts here
- **What the AI produced:** short summary (files, design, code, text)
- **What I changed or rejected, and why:**
- **Result:** commits / files / decisions (link or hash)
- **Evidence:** `docs/ai-usage/<file>`

---

## Entries

### 2026-10-18 | Claude (chat) | Module design

- **Goal:** choose and define the AI Assistant & Delivery Review module, decide RAFT vs API usage, and prepare a spec for Claude Code.
- **Key prompts (verbatim):** _paste from the conversation_
- **What the AI produced:** module description, architecture options, `CLAUDE.md` and `MODULE_SPEC.md`.
- **What I changed or rejected, and why:** dropped intent classification; kept the API only as a backup for the assistant; reordered the build to start the RAFT track early.
- **Result:** `docs/MODULE_SPEC.md`, `CLAUDE.md`
- **Evidence:** _export or screenshots of the conversation_
