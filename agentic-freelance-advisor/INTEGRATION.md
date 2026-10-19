# Freelance Advisor inside the integrated platform

This service (LangGraph agent + FastAPI) is its own microservice in the integrated project. The code is
unchanged from the author's version. Only the way it is reached differs:

| | Value |
|---|---|
| Port | **8004**. The default 8000 is taken by the retrieval service (`rag_service`), so always pass `--port 8004` |
| Through the API gateway | `http://127.0.0.1:8080/advisor/...` (prefix removed, e.g. `/advisor/health` -> `/health`) |
| Through the frontend (Vite, :8766) | same `/advisor/...` paths, proxied in `vite.config.js` |
| Dashboard tile | **Freelance Advisor** (opens `AdvisorDialog`). A pill on the gallery shows a run still in progress |

## Setup (once per PC)

The author's `.venv` was not copied: it only works on the PC where it was made. Re-create it with the
locked dependencies (`uv.lock`), using the uv and Python 3.12 that `module_assistant_delivery` already has:

```powershell
cd "C:\Users\azizs\Downloads\freelance2\freelance2\agentic-freelance-advisor"
..\module_assistant_delivery\storage\tools\uv.exe sync --python ..\module_assistant_delivery\storage\python\cpython-3.12.15-windows-x86_64-none\python.exe
```

- **Model:** pull the one the author recommends into the shared Ollama (:11434), unless the `.env` names another:
  `ollama pull qwen3:4b-instruct` (about 2.5 GB).
- **Keys:** the author's `.env` was copied as it was. Git ignores it through this folder's `.gitignore`.
  - `TAVILY_API_KEY` is required for web search; `GITHUB_TOKEN` and `HF_TOKEN` are optional (see `.env.example`).
  - If the keys there are not yours to use, replace them with your own.

## Run

```powershell
cd "C:\Users\azizs\Downloads\freelance2\freelance2\agentic-freelance-advisor"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8004
```

Health check through the gateway: http://127.0.0.1:8080/advisor/health

Integrated on 2026-10-18 without running the service, at the owner's request. The setup and run commands
above have not been executed on this PC yet.

## Integration record

Moved here on 2026-10-19 from `module_assistant_delivery/docs/AUDIT.md` (the owner keeps colleagues' integrations out of that module's documentation).

### Freelance Advisor integrated (2026-10-18, owner's request, not run)

- **Source:** a colleague's work in `C:\Users\azizs\Downloads\ai for eng\ai for eng`. His template copy was older than ours (no BI wiring, no retrieval or sentiment proxy, no shared workspace CSS), so it was not copied over ours. Only his additions were transplanted.
- **Service:** `agentic-freelance-advisor/` is his backend, copied unchanged.
  - Not copied: `.venv`, `.pytest_cache`, `__pycache__`.
  - His `.env` was copied without being read; his `.gitignore` excludes it from Git.
  - It runs on **port 8004**, because his default 8000 is the retrieval service. Instructions: `agentic-freelance-advisor/INTEGRATION.md`.
- **Frontend:**
  - Six new files in `src/`: `AdvisorDialog.jsx`, `advisor-run.js`, `advisor-examples.js`, `advisor.css`, `markdown.jsx`, `advisor-preview.svg`.
  - `src/main.jsx` imports `advisor.css`.
  - `src/App.jsx` gained his three imports, a **Freelance Advisor** tile, his run-in-progress pill, and a routing branch to `AdvisorDialog`. Everything already there (BI, Cerebro AI, the assistant tile) is unchanged.
  - `vite.config.js` adds `/advisor` → `127.0.0.1:8004` with the prefix removed.
- **Gateway:**
  - `platform_gateway/config.mjs` adds `/advisor` → `ADVISOR_ORIGIN` (default `http://127.0.0.1:8004`, prefix removed, service `freelance-advisor`).
  - `.env.example`, `README.md` and `test/gateway.test.mjs` were updated (3 origins now; `/advisor` resolution asserted).
- **Checks (static only, as the owner asked not to test the module):**
  - The merged files compile.
  - A full esbuild bundle from `src/main.jsx` resolves every import (0 warnings).
  - The gateway unit tests pass (9/9).
  - The restarted gateway routes `/advisor` (answers `upstream_unavailable` for `freelance-advisor` while the service is not started).
  - The protected baseline was updated for the 7 edited files and 52 new files (329 tracked, 0 changed).

## Integration log

The owner's prompts for this integration, verbatim, with what was done. Moved here on 2026-10-19 from `module_assistant_delivery/docs/AI_USAGE_LOG.md`.

### Same session, part 14: a colleague's module integrated (2026-10-18)

- **Owner's message (verbatim):** "OKAY LISTNE TO ME, a friend of mine, another colleague sent me his work, but he already integrated on his own version of the template, his version of the template is basically the same version we have just before i integrated my work on it / so ill give you the path of his work, and id like you to integrate his work, dont test it, just integrate his work on the template we have , consider its own microservice also , make sure to connect to the api gateway, the whole shebang basically, i wanna integrate my friends work onto our current integrated project / heres my friends work : C:\Users\azizs\Downloads\ai for eng"
- **What was done:** the colleague's Freelance Advisor (LangGraph + FastAPI + Ollama) became its own microservice on port 8004, with a dashboard tile and run pill, a Vite proxy and a gateway route `/advisor`. Details in `docs/AUDIT.md` and `agentic-freelance-advisor/INTEGRATION.md`.
- **Found while merging:** his template copy was older than ours. Copying it would have removed the BI module, the retrieval and sentiment proxies, the shared workspace styles and the assistant tile, so only his additions were transplanted. His proxy used port 8000, which collides with the retrieval service; it was moved to 8004.
- **Not done (owner's instruction):** the service was not started or tested. Its `.venv` (from his PC) was not copied, and the setup command in `INTEGRATION.md` has not been run. The model `qwen3:4b-instruct` is not installed in the shared Ollama.
- **Checks run:** compile and bundle of the frontend, gateway unit tests 9/9, gateway route live, protected baseline 329/329 after the update. Nothing committed or pushed.
