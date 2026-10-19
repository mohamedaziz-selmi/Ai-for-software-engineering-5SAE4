# Cerebro Business AI inside the integrated platform

A colleague's application: four local AI services behind his own gateway, with his own React app.

| Module | What it does | Model |
|---|---|---|
| Hiring assistant | Job ad, interview kit, onboarding plan from a role brief (EN/FR) | `gemma3:4b` (Ollama) |
| Sales & inventory | Forecast and reorder quantities from a product's sales history | Saved M5 XGBoost |
| Job verification | Fraud signal and evidence warnings for a job posting | Saved TF-IDF + Logistic Regression |
| Product assistant | Listing draft from verified facts, with catalog comparisons | TF-IDF Amazon index + `gemma3:4b` |

Source: `C:\Users\azizs\Downloads\ai`, his tested portable release (`release\Cerebro_Windows_x64`), plus his
`docs\`, slides (`presentation\`) and main README (`PROJECT_README.md`). All 168 files listed in his
`release-manifest.json` were verified by SHA-256 after copying.

## What to download

Only **`gemma3:4b`** (about 3.3 GB), into the normal shared Ollama (:11434). `SETUP.cmd` pulls it if it is
missing. Everything else is included: a private Python 3.11.9, offline wheels, and the saved models and index.

| Side effect | What to do |
|---|---|
| The Cerebro chat uses `llama3.2:3b` if installed, otherwise the first model Ollama lists. After pulling Gemma, the chat can switch to Gemma | To keep the chat on its intended model: `ollama pull llama3.2:3b` (2 GB) |
| Gemma (shared Ollama) and the assistant module's Qwen 7B (private Ollama) do not both fit in 8 GB of GPU memory | Demo one module at a time; otherwise answers slow down |

## Run

```powershell
cd "C:\Users\azizs\Downloads\freelance2\freelance2\cerebro_business_ai"
.\SETUP.cmd     # once: private runtime, offline install, model checks, Gemma download (internet)
.\START.cmd     # later starts; STOP.cmd stops only these servers; CHECK.cmd checks models and services
```

| | Address |
|---|---|
| His screens, through the group gateway | http://127.0.0.1:8080/business-ai/ (the dashboard tile **Cerebro Business AI** opens it) |
| His screens, directly | http://127.0.0.1:8905/ (works as before) |
| His gateway (Swagger) | http://127.0.0.1:8900/docs; services 8901 to 8904 `/docs` |
| His API, through the group gateway | http://127.0.0.1:8080/business-ai-api/api/ai/status (prefix removed). His API uses `/api/ai/...`, which is the assistant module's prefix here |

Ports 8900 to 8905 are free in the group project. If one is taken: `START.cmd -BasePort 18900`.

## How it plugs into the group frontend

It stays its own microservice: his servers, ports and START/STOP are unchanged. The group gateway (and the
dashboard's Vite dev server) forwards `/business-ai/...` to his screens on :8905 and `/business-ai-api/...` to his
gateway on :8900. Two of his files changed, both `index.html` (built and source):

- Asset links are relative (`./assets/...`), so they load under `/business-ai/` and at `/` alike.
- A small inline script: under `/business-ai/` his screens call `/business-ai-api` (same origin, so no CORS);
  directly on :8905 they keep his configured `http://127.0.0.1:8900`. `/business-ai` without a slash redirects.
- `release-manifest.json` was refreshed for these two files, so `SETUP.cmd`'s integrity check still passes
  (168/168). To rebuild his frontend later, keep these lines in `frontend/index.html` and build with `--base ./`.

## Notes

- Not copied: his Python environment (`.venv-phase2`, built for his PC), his Node runtime (`.tools`), the
  `release\Friend Test` copy, installer caches and ZIP duplicates, raw training datasets (`data\phase2`, 1.1 GB,
  not needed to run), logs and test outputs.
- `SETUP.cmd` creates `.runtime\` here (private Python, logs, local state) and `data\inference-admission.sqlite`
  (his resource guard's state): keep both out of Git.
- His resource guard refuses work when CPU or RAM is at 80% or more (`ai-service/app/resource_guard.py`). With
  16 GB of RAM and several apps open, setup failed on that check until other apps were closed (85% → 67%).
- `installer\wheels\xgboost-2.1.4-py3-none-win_amd64.whl` is 125 MB, over GitHub's 100 MB limit: track it with
  Git LFS before pushing.
- Integrated on 2026-10-19 at the owner's request, then set up and run on this PC the same day:
  - `SETUP.cmd`: private runtime, offline install, model checks, `gemma3:4b` pulled into the shared Ollama.
  - His `portable/verify_api.py --llm`: **21/21 checks passed**, including saved fraud and forecast models,
    retrieval and real Gemma generation (hiring brief 65 s with the first model load, listing 12 s). GPU peak 61 °C.
  - App at http://127.0.0.1:8905/ renders, and through the group gateway at http://127.0.0.1:8080/business-ai/:
    a job-posting analysis from his screen went to `/business-ai-api/api/ai/jobs/intake` (200), nothing called
    :8900 directly, and the console showed no errors.
  - As expected, the shared Ollama now lists `gemma3:4b` first, so the Cerebro chat uses Gemma until `llama3.2:3b`
    is installed.

## Integration record

Moved here on 2026-10-19 from `module_assistant_delivery/docs/AUDIT.md` (the owner keeps colleagues' integrations out of that module's documentation).

### Cerebro Business AI integrated (2026-10-19, owner's request, not run)

- **Source:** `C:\Users\azizs\Downloads\ai` (3.5 GB). Integrated: his tested portable release `release\Cerebro_Windows_x64` (181 files with his docs and slides, 238 MB) as `cerebro_business_ai/`. All 168 files in his `release-manifest.json` match (SHA-256).
  - Left out: `.venv-phase2` (his PC's environment), `.tools` (his Node), `release\Friend Test`, installer caches and ZIP duplicates, raw datasets `data\phase2` (1.1 GB, not needed to run), logs, `.codex-*` build outputs, test results.
- **Service:** his gateway :8900, services :8901 to :8904, his React app :8905. No conflict with the group ports.
- **Download needed:** `gemma3:4b` (3.3 GB) into the shared Ollama, pulled by his `SETUP.cmd`. Nothing else (private Python and offline wheels are bundled). Side effects documented in `cerebro_business_ai/INTEGRATION.md`: the Cerebro chat may switch to Gemma unless `llama3.2:3b` is installed; Gemma and this module's Qwen 7B do not fit in 8 GB of GPU memory together.
- **Dashboard:** tile **Cerebro Business AI** (`src/cerebro-business-ai-preview.svg`, drawn in the style of the other tiles) opening `/business-ai/` (his screens through the group gateway, like `/assistant/`). 1 import + 7 lines in `src/App.jsx`.
- **Gateway (owner's choice, "option 1", his module stays its own microservice):** `/business-ai` → his screens (`BUSINESS_AI_UI_ORIGIN`, :8905) and `/business-ai-api` → his gateway (`BUSINESS_AI_ORIGIN`, :8900), prefixes removed; his API paths start with `/api/ai`, this module's prefix. The same two prefixes in `vite.config.js` (API first). His `index.html` (built and source): relative asset links and a script that sends API calls to `/business-ai-api` under the gateway; his `release-manifest.json` refreshed for these two files (168/168 still verify). Test, README and `.env.example` updated.
- **Checks (static only):** dashboard bundle builds with 0 warnings (tile image included); gateway tests 9/9 (`/business-ai/api/ai/status` → his `/api/ai/status`, `/api/ai/status` still → this module). Protected baseline updated.
- **Git:** `installer\wheels\xgboost-2.1.4-py3-none-win_amd64.whl` (125 MB) needs Git LFS before a push.
- **Run on this PC (owner's request, same day):** first `SETUP.cmd` stopped at his resource guard (RAM 85%, limit 80%); after the owner closed apps (67%) it completed and pulled `gemma3:4b` into the shared Ollama. His `verify_api.py --llm`: 21/21 passed, real Gemma generation included; GPU peak 61 °C. The group gateway route answered 200. `check_protected.ps1` now skips `cerebro_business_ai\.runtime\` (his runtime state, like `rag_service\chroma_db`).
- **Side effect confirmed:** the shared Ollama lists `gemma3:4b` first, so the Cerebro chat uses it unless `llama3.2:3b` is installed.

## Integration log

The owner's prompts for this integration, verbatim, with what was done. Moved here on 2026-10-19 from `module_assistant_delivery/docs/AI_USAGE_LOG.md`.

### Session of 2026-10-19, part 19: the last colleague's module integrated
- **Owner's message (verbatim), 18:34:** "i have one final colleague 's work i need to integrate onto the group work<br><br>you can find his work hereC:\Users\azizs\Downloads\ai<br>he said something about having to download a model or something in order to run and test his work <br><br>i dont know, verify if there is anything to download"
  - The folder now held a different project: Cerebro Business AI (hiring assistant, sales and inventory forecasting, job-posting verification, product listing), 4 FastAPI services behind his gateway (:8900 to :8904) and a React app (:8905).
  - Download needed: only `gemma3:4b` (3.3 GB) through the shared Ollama, pulled by his `SETUP.cmd`. Not downloaded (the owner decides). Side effects recorded: the Cerebro chat may switch to Gemma unless `llama3.2:3b` is installed; Gemma and the assistant's Qwen 7B do not fit in 8 GB of GPU memory together.
  - Integrated his tested portable release (238 MB of 3.5 GB; duplicates, his environments and raw datasets left out) as `cerebro_business_ai/`, 168/168 manifest files verified; dashboard tile; gateway route `/business-ai` (his API uses `/api/ai`, this module's prefix). Not run. Checks: bundle 0 warnings, gateway tests 9/9.
- **Owner's message (verbatim), 18:43:** "Yes, run cerebro_business_ai\SETUP.cmd now (it downloads gemma3:4b), then check that his app answers at http://127.0.0.1:8905/."
- **Owner's message (verbatim), 18:52:** "I closed some apps. Check that RAM is under 80%, then rerun cerebro_business_ai setup (with the gemma3:4b download) and check his app at http://127.0.0.1:8905/."
- **Owner's message (verbatim), 18:53:** "I closed more apps. Check that RAM is under 80%, then rerun cerebro_business_ai setup (with the gemma3:4b download) and check his app at http://127.0.0.1:8905/."
  - First setup: private runtime and offline install done, then his resource guard refused the forecast check (RAM 84.7%, limit 80%). Nothing was downloaded. The biggest RAM users were listed for the owner; nothing was changed in his code (it would also fail his setup's checksum check).
  - Second attempt: RAM still 82.4%, not rerun. Third: RAM 66.7%, setup completed and pulled `gemma3:4b` (3.3 GB) into the shared Ollama, with `OLLAMA_HOST` cleared so it could not land in this module's private Ollama.
  - Checks: his `verify_api.py --llm` 21/21 passed (real Gemma generation: hiring 65 s with the first load, listing 12 s; GPU peak 61 °C); his app renders at :8905; the group gateway route `/business-ai/api/ai/status` answered 200. The shared Ollama now lists `gemma3:4b` first, as predicted for the Cerebro chat.
- **Owner's message (verbatim), 19:13:** "cerebro chat ? what the fuck ? what module is that ? the latest one we integrated ? also where did llama 3.2:3b come from ? is it used in this module ? the one were integrating just now ?"
- **Owner's message (verbatim), 19:15:** "theyre not different apps you dumb fuckin idiot, the C:\Users\azizs\Downloads\ai folder is just the module of our colleague also that he wanted me to integrate his work onto ours"
- **Owner's message (verbatim), 19:16:** "is his front end integrated with our front end ?"
- **Owner's message (verbatim), 19:17:** "option 1 feels good, but remember , hes his own microservice"
  - Answered: the Cerebro AI chat is the template's existing chat tile (`src/App.jsx`), not the new module; `llama3.2:3b` is that chat's preferred model, not used by the new module (which uses only `gemma3:4b`). Corrected: the colleague's folder is his module of the group's Cerebro platform, not a separate app.
  - His frontend was linked by a tile but not served through the group frontend. Owner chose option 1 (served through the group gateway like the assistant module), with his module kept as its own microservice.
  - Done without rebuilding his frontend: relative asset links and an inline API switch in his `index.html` (built and source), manifest refreshed (168/168 verify); group gateway and Vite: `/business-ai` → :8905, `/business-ai-api` → :8900; tile → `/business-ai/`. Tests: gateway 9/9; dashboard bundle builds; in the browser through the gateway his screens load and a job-posting analysis went to `/business-ai-api/api/ai/jobs/intake` (200), no console errors; direct :8905 unchanged.
