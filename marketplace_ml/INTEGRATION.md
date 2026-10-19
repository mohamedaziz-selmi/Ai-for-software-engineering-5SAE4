# Freelance Marketplace AI inside the integrated platform

Two machine-learning projects by a teammate, served together by one FastAPI app, which makes this its own
microservice in the integrated project. The code and data are unchanged from the author's version.

```
marketplace_ml/
├── project budjet/     budget prediction: Upwork dataset, Random Forest + XGBoost (src/budget_pipeline.py)
└── project matching/   freelancer matching: resume dataset, TF-IDF + Sentence Transformers (src/matching_pipeline.py)
                        and the API for both: src/ai_api.py
```

The API finds both projects through their shared parent folder (`AI_ROOT = parents[2]`), so the two
folders must stay side by side in `marketplace_ml/`.

| | Value |
|---|---|
| Port | **8005**. The author's proxy used 8000, which is the retrieval service (`rag_service`) here |
| Endpoints | `GET /api/health`, `POST /api/budget` (used by the budget tab); `POST /api/match` (no longer called by the UI since the 2026-10-19 update) |
| Matcher (since the 2026-10-19 update) | **Qwen2.5 0.5B** on its own CPU-only Ollama, port **11436** (the author used 11435, which is `module_assistant_delivery`'s private Ollama here). The browser calls `/ollama-match/api/...` |
| Through the API gateway | `http://127.0.0.1:8080/api/health`, `/api/match`, `/api/budget` (paths preserved). Only these three are routed, so `/api/ai` and `/api/module5` still reach their own services |
| Through the frontend (Vite, :8766) | the same three paths, plus `/ollama-match` → :11436 (prefix removed), proxied in `vite.config.js` |
| Matcher through the gateway | `http://127.0.0.1:8080/ollama-match/api/tags` (route `marketplace-matcher`, prefix removed) |
| Dashboard | the **Freelance Marketplace AI** tile and the **Open AI lab** card under the gallery open `MarketplaceAIDialog` (matching and budget tabs) |

## Setup (once per PC, not done yet)

The author shipped no requirements file or environment. The packages, from the imports, are fastapi,
uvicorn, pandas, numpy, scikit-learn, joblib, xgboost and sentence-transformers (which brings torch). His
compiled files show Python 3.13.

The saved models (`*.joblib`) can need the **same scikit-learn and xgboost versions** he trained with. Ask
him for them (`pip freeze`) before installing. A starting point with the uv of `module_assistant_delivery`:

```powershell
cd "C:\Users\azizs\Downloads\freelance2\freelance2\marketplace_ml"
..\module_assistant_delivery\storage\tools\uv.exe venv --python 3.13 .venv
..\module_assistant_delivery\storage\tools\uv.exe pip install --python .venv\Scripts\python.exe fastapi "uvicorn[standard]" pandas numpy scikit-learn joblib xgboost sentence-transformers
```

## Matcher (Qwen2.5 0.5B, CPU only)

Its own Ollama, port and model folder (`marketplace_ml\.ollama-models`). Pulling into the shared Ollama (:11434)
could change which model the Cerebro chat picks, and :11435 belongs to `module_assistant_delivery`.

```powershell
cd "C:\Users\azizs\Downloads\freelance2\freelance2\marketplace_ml"
$env:OLLAMA_HOST = "127.0.0.1:11436"; $env:OLLAMA_MODELS = "$PWD\.ollama-models"
$env:OLLAMA_LLM_LIBRARY = "cpu"; $env:OLLAMA_NUM_PARALLEL = "1"
ollama serve
```

Once, in a second terminal: `$env:OLLAMA_HOST = "127.0.0.1:11436"; ollama pull qwen2.5:0.5b` (about 400 MB).
Without it the matching tab still works with clearly labelled sample results.

## Run (budget API)

```powershell
cd "C:\Users\azizs\Downloads\freelance2\freelance2\marketplace_ml\project matching\src"
..\..\.venv\Scripts\python.exe -m uvicorn ai_api:app --port 8005
```

Health through the gateway: http://127.0.0.1:8080/api/health

## Notes

- Size: about 467 MB.
  - Datasets: `Final_Upwork_Dataset.csv` 88 MB and `.xlsx`, `Resume.csv` 54 MB, the résumé PDFs, and `archive (5).zip` 63 MB, which appears to be the raw dataset archive.
  - Models: `sentence_transformer_joblib.joblib` 88 MB, the Random Forest model 37 MB.
  - No file exceeds GitHub's 100 MB limit. Consider a `.gitignore` for the datasets and the archive before pushing.
- The résumé dataset contains CVs. Keep the repository private, and check the dataset's licence before sharing it further.

Integrated on 2026-10-18 without running the service, at the owner's request. Updated on 2026-10-19 with his
new version (`wetransfer_ai_2026-10-18_2132`): only his frontend changed (matching dialog, project text, proxy);
both Python projects are byte-identical to the first version. His `ii.rar` (an older template snapshot) was not
integrated, and `archive (5).zip` stays removed (owner's decision). The setup and run commands above have not
been executed on this PC yet.

## Integration record

Moved here on 2026-10-19 from `module_assistant_delivery/docs/AUDIT.md` (the owner keeps colleagues' integrations out of that module's documentation).

### Freelance Marketplace AI integrated (2026-10-18, owner's request, not run)

- **Source:** a colleague's work in `C:\Users\azizs\Downloads\ai\ai`: `project budjet`, `project matching` and a template copy `front`. His copy was again older than ours, so only his additions were transplanted.
- **Service:** `marketplace_ml/` holds both projects unchanged, side by side, as his API (`project matching/src/ai_api.py`) requires.
  - 2,505 files, 467 MB, with no `__pycache__`.
  - It runs on **port 8005** (his proxy used 8000, which is the retrieval service).
  - He shipped no requirements file or environment. Instructions: `marketplace_ml/INTEGRATION.md`.
- **Frontend:** `src/marketplace-ai-preview.svg` added. In `src/App.jsx`:
  - His import, his project entry as the constant `marketplaceAiProject` and a gallery tile, his sample constants, and `MarketplaceAIDialog` (383 lines, verbatim).
  - His three label fallbacks in `ProjectDialog` (`employerLabel`, `frontendLabel`, `backendLabel`; existing projects unaffected).
  - His **Open AI lab** card under the gallery, pointed at `marketplaceAiProject` instead of `galleryProjects[0]`, which is Bee Tickets in our order.
  - A routing branch.
- **Styles and proxy:**
  - `src/styles.css` received his 812 inserted lines at the same positions. None of our lines changed, and our shared workspace styles, missing in his copy, were kept.
  - `vite.config.js` proxies only `/api/health`, `/api/match` and `/api/budget` to :8005. His proxy took all of `/api`, which would have captured `/api/ai` and `/api/module5`.
- **Gateway:** the same three paths → `MARKETPLACE_ORIGIN` (default `http://127.0.0.1:8005`, service `marketplace-ml`, paths preserved). The test now expects 4 origins and asserts that `/api/ai` and `/api/module5` still resolve to their own services. `.env.example` and README updated.
- **Checks (static only):**
  - The merge verified line by line against backups (4 previous `App.jsx` lines changed: 3 labels and 1 routing line; 0 in `styles.css`).
  - `App.jsx` and `styles.css` compile, and the full esbuild bundle has 0 warnings. Gateway tests pass 9/9.
  - The restarted gateway routes `/api/match` to `marketplace-ml`, while `/api/ai/health` and `/api/module5/health` still answer ready.

### Freelance Marketplace AI updated (2026-10-19, owner's request, not run)

- **Source:** `C:\Users\azizs\Downloads\wetransfer_ai_2026-10-18_2132\ai`, compared file by file (SHA-256) with his first version.
  - Changed: only his frontend: `src/App.jsx` (175 lines), `vite.config.js`, `README.md` and his built bundle. Both Python projects are byte-identical, so `marketplace_ml/` code and data were left as they are.
  - Not integrated: `ii.rar` (17 MB, an older snapshot of the template with `node_modules`). `archive (5).zip` stays removed (owner).
- **What changed for users:** matching now ranks the 3 sample profiles with **Qwen2.5 0.5B** on a CPU-only Ollama, or with an in-browser keyword baseline; budget prediction still uses his API (:8005).
- **Port conflict fixed:** his matcher Ollama used **11435**, which is this module's private Ollama (one model in memory: his calls would have evicted ours). It runs on **11436** with its own model folder (`marketplace_ml\.ollama-models`), so the shared Ollama (:11434) used by the Cerebro chat is not touched either.
- **Applied:**
  - `src/App.jsx`: `MarketplaceAIDialog` replaced by his new version after checking ours was identical to his previous one (ignoring line endings); his 2 project-text changes. Net difference = exactly his 175 lines.
  - `vite.config.js`: `/ollama-match` → :11436 (prefix removed), listed before `/ollama`.
  - Gateway: route `/ollama-match` → `MATCHER_OLLAMA_ORIGIN` (default :11436, service `marketplace-matcher`, prefix removed); test, README and `.env.example` updated.
  - `marketplace_ml/INTEGRATION.md`: matcher setup and commands.
- **Checks (static only):** the esbuild bundle of the dashboard builds with 0 warnings; `vite.config.js` loads and resolves `/ollama-match/api/tags` → :11436 `/api/tags`; gateway tests 9/9 (including `/ollama-match` → matcher and `/ollama` unchanged). Protected baseline refreshed for these 7 files and the removed zip: 0 changed, 0 missing.

## Integration log

The owner's prompts for this integration, verbatim, with what was done. Moved here on 2026-10-19 from `module_assistant_delivery/docs/AI_USAGE_LOG.md`.

### Same session, part 15: a second colleague's module integrated (2026-10-18)

- **Owner's message (verbatim):** "id like for you to do the same for another colleague whose work is here : C:\Users\azizs\Downloads\ai"
- **What was done:** his Freelance Marketplace AI (budget prediction with Random Forest/XGBoost, freelancer matching with TF-IDF/Sentence Transformers, one FastAPI app) became its own microservice `marketplace_ml/` on port 8005.
  - Dashboard: a tile, his "Open AI lab" card, his dialog and his styles.
  - Vite proxy and gateway routes for exactly `/api/health`, `/api/match` and `/api/budget`.
  - Details in `docs/AUDIT.md` and `marketplace_ml/INTEGRATION.md`.
- **Found while merging:**
  - His template copy was older than ours, so only his additions were transplanted.
  - His proxy used port 8000 (the retrieval service) and captured all of `/api`, which would have broken `/api/ai` and `/api/module5`; narrowed to his three paths on 8005.
  - His launcher opened `galleryProjects[0]`, which is Bee Tickets in our order; pointed at his project instead.
- **Not done (owner's instruction):** the service was not set up or started. He shipped no requirements file. The saved models may need his exact scikit-learn/xgboost versions (to ask him).
- **Checks run:**
  - The merge verified against backups; compile and bundle clean.
  - Gateway tests 9/9, routes live after restart.
  - Protected baseline updated. Nothing committed or pushed.

### Session of 2026-10-19, part 18: a colleague's updated module integrated
- **Owner's message (verbatim), 09:15:** "remember when i told you my friend, the latest one we did the integration for, has sent me his updated work, you can find it here : C:\Users\azizs\Downloads\wetransfer_ai_2026-10-18_2132<br><br><br>i need it to be integrated , of course in place of his already integrated work , youll find it here :<br>C:\Users\azizs\Downloads\wetransfer_ai_2026-10-18_2132"
  - Compared with his first version file by file: only his frontend changed (matching via Qwen2.5 0.5B on a CPU-only Ollama); both Python projects identical. `ii.rar` (old template snapshot) not integrated.
  - His matcher Ollama port 11435 collided with this module's private Ollama: moved to 11436 with its own model folder, so neither this module's Ollama nor the shared one is touched.
  - Applied to `src/App.jsx` (exactly his 175 changed lines), `vite.config.js`, the gateway (route, test, README, `.env.example`) and `marketplace_ml/INTEGRATION.md`. Not run, as for his first version. Checks: bundle 0 warnings, gateway tests 9/9, protected baseline refreshed (0 changed).
