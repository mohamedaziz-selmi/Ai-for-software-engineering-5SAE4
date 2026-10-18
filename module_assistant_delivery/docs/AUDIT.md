# Repository audit: verified against the files (2026-10-18)

Checks the read-only audit in `PROJECT_KICKOFF.md` §7A (copy in `reference/`) against the
application root `C:\Users\azizs\Downloads\freelance2\freelance2`. Every row was checked in this
session by reading files or running commands that do not write anything. Teammate files were read only.
A SHA-256 baseline of all 286 protected files (outside `node_modules/` and `.venv/`) is in
`protected_baseline.sha256` and is re-checked after each work session.

## Verdict per audit claim

| Kickoff claim | Status | Evidence / correction |
|---|---|---|
| Frontend is React 18.3 + Vite 6.4, caret ranges | **Confirmed** | `package.json`; `index.html` → `src/main.jsx` |
| Dashboard navigation is hard-coded in `src/App.jsx` | **Confirmed** | `galleryProjects` array (line ~64). Adding a tile means editing `App.jsx` (protected) |
| Retrieval service: FastAPI, Chroma, MiniLM, BM25 + RRF; stale header comment | **Confirmed** | `rag_service/api.py` line 1 says "no BM25"; the code imports `BM25Index`, `fuse_rrf` |
| Sentiment service exposes `/predict` | **Confirmed** | `sentiment classifier/api.py` |
| BI has its own React workspace + FastAPI | **Confirmed** | `src/BusinessIntelligence.jsx`, `module5_business_intelligence/api.py` |
| Ports: Vite 8766, Ollama 11434, retrieval 8000, sentiment 8001, BI 8002 | **Confirmed** | `vite.config.js` (`strictPort: true`) |
| No auth / JWT / login / project membership | **Confirmed** | Search over `src/`, all three backends and the gateway: the only `role` hits are ARIA roles and chat-message roles. No users, sessions, tokens or membership checks exist anywhere |
| `JOB-001..JOB-010` are UI options, not a project DB | **Confirmed, with an addition** | See discrepancy 3 |
| Retrieval has no `project_id` isolation | **Confirmed** | `SearchRequest` has only `query`, `limit`, `category`, `mode` |
| Documented frontend commands; no frontend test script | **Confirmed** | `package.json` scripts: `dev`, `build`, `preview` only |
| Sentiment and BI reuse `rag_service/.venv` | **Confirmed** | Both READMEs and the BI error message in `BusinessIntelligence.jsx` |
| Source-control status unverified | **Now resolved: no repository** | See discrepancy 1 |
| Gateway routes `/api/ai/*` and `/assistant/*` to :8003, path preserved | **Confirmed** | `platform_gateway/config.mjs` (no `strip` on those routes) |
| Gateway tests: 9 passed | **Re-confirmed on this machine** | `node --test test/gateway.test.mjs` → 9 pass, 0 fail, on Node **22.13.1** |

## Important discrepancies

1. **There is no Git repository.** `git status` (PortableGit) answers `fatal: not a git repository`
   at the application root and its parent. There is no `.git` directory. The root `.gitignore` exists
   but is not active. Consequence: there is no commit history, and the old CLAUDE.md conventions
   (feature branches, conventional commits, "individual grading from Git contribution") cannot be
   followed in this folder yet. No repository has been initialised, because creating one at the root
   would change shared project state. **Open question for the owner:** where is the team's real
   repository (remote URL), and should this module be committed there?

2. **The shared Ollama instance only has a vision model.** Ollama 0.40.6 is running on :11434
   with exactly one model, `qwen2.5vl:3b`. The README's preferred `llama3.2:3b` is not installed.
   The teammates' chat (`App.jsx`, `loadModels`) selects `llama3.2:3b` if present, **otherwise the
   first installed model**. Pulling an assistant model into the shared store could therefore change
   the teammates' default model. **Decision taken:** this module runs its own Ollama process on
   **:11435** with its model store under `module_assistant_delivery/storage/ollama/` (see
   `scripts/start_ollama.ps1`). The shared instance and its store are untouched.

3. **More data folders exist than the audit lists, but none is a platform record store.**
   - `Rayen/` holds raw BI datasets (Online Retail workbook, store-sales CSVs). The audit does not
     mention it. Ownership was not inferred from the folder name.
   - `rag/cerebro_rag_full_30/synthetic_dataset/` holds static synthetic CSVs: `projects.csv`
     (`PRJ-*`, *completed historical portfolio projects*), `jobs.csv` (`JOB-*`, job postings),
     `freelancers.csv`, `proposals.csv`, `delivery_records.csv` (aggregate on-time statistics),
     plus `CR-03_Requirements_Specs_and_Acceptance_Criteria.pdf`. These support the proposal-scoring
     feature. There is **no API, database, active agreed project, milestone, deliverable or
     membership entity** behind them. This module does not read, reuse or train on them; it uses
     its own synthetic documents.

4. **Teammate documentation drift (informational only, not touched).** The sentiment README documents
   `train_model.py`, which does not exist in `sentiment classifier/` (only `api.py`, `predict.py`,
   `prepare_sentiment_data.py`). `rag_service` CORS allows `http://localhost:5173` while Vite runs on
   8766 (harmless behind the same-origin proxy).

5. **Gateway validation runtime.** `VALIDATION.md` records Node 24.19.0. The installed Node is 22.13.1.
   The suite still passes 9/9 here, and `package.json` requires `>=22`.

6. **Nothing else is running.** Only the shared Ollama (:11434) was listening when audited. Ports
   8000–8003, 8080, 8081 and 8766 were free. The gateway, facade and teammates' services were not
   started by this audit.

## Template conventions the module follows (read 2026-10-18)

| Convention in the template | Where | How this module follows it |
|---|---|---|
| A module opens as a workspace: `review-workspace` shell (`#f1edf4` card on the paper backdrop), eyebrow path "Cerebro / Module …", large title, mono status pill, `×` close | `src/BusinessIntelligence.jsx`, `src/styles.css` (review-workspace rules) | `AssistantWorkspace.jsx` uses the same structure; shell rules copied to `frontend/src/template-shell.css` |
| Sticky numbered tabs, `Section` headings (eyebrow + h3 + description), tiles, pass/warn/fail badges, `review-error` with the exact start command when the API is offline | `src/bi-workspace.css`, `BusinessIntelligence.jsx` | Same patterns with an `ad-` prefix (`assistant-workspace.css`) |
| Arial + Consolas, palette `#302b39` / `#625e68` / `#286443` / `#963d3d` | `src/styles.css`, `bi-workspace.css` | Same values |
| Each backend is a FastAPI `api.py` run with `uvicorn api:app --port <n>`, with `/health` reporting `ready` | `module5_business_intelligence/api.py`, `rag_service/api.py`, `sentiment classifier/api.py` | `backend/api.py`, port 8003, `/api/ai/health` includes `ready` |
| Module API under its own prefix (`/api/module5`) | `vite.config.js`, BI `api.py` | `/api/ai` (already routed by the gateway) |

Embedding the workspace in the dashboard remains the shell owner's change: either a gallery tile that links
to `/assistant/`, or mounting `AssistantWorkspace` with an `onClose` prop like `BusinessIntelligence`.

## What this means for the module

| Platform capability the old spec assumed | Reality | Module handling |
|---|---|---|
| Template auth, users, roles | None | `DemoIdentityAdapter`: an explicit demo identity selector, labelled as **not authentication** |
| Projects, membership | None | `DemoProjectDirectory`: seeded synthetic projects and members behind an adapter |
| Milestones, deliverables | None | Module-owned later; demo milestones behind the same adapter |
| Shared database | None (each service keeps its own files) | Module-owned SQLite under `storage/` (first slice) |
| Navigation entry | Requires editing `src/App.jsx` | **Done 2026-10-18 with the owner's approval**: dashboard tile "AI Assistant & Delivery Review" opens `/assistant/` (`docs/integration/dashboard_link.patch`) |
| Gateway registration | Already present (`/api/ai`, `/assistant` → :8003) | Reused read-only |

## Protected paths (read-only for this module)

Everything under the application root except `module_assistant_delivery/`. That includes `src/`,
`vite.config.js`, `package.json`, `package-lock.json`, `node_modules/`, `index.html`, `dist/`, `rag/`,
`rag_service/` (including `.venv/` and `chroma_db/`), `sentiment classifier/`,
`module5_business_intelligence/`, `Rayen/`, `cerebro/`, `plausible.io/`, root `.gitignore`, and
`platform_gateway/` (read-only for this milestone). The shared Ollama model store
(`%USERPROFILE%\.ollama`) is also left untouched.

## Integration changes that need another owner (described, not performed)

1. **Dashboard link** (shell owner): add a gallery tile or link in `src/App.jsx` that navigates to
   `/assistant/` (a plain `<a href="/assistant/">` works through the gateway).
   - The owner asked for this on 2026-10-18 ("go ahead and do it, now, the template thing"). Claude Code's permission check blocked the edit of the two template files.
   - The partial edits were reverted; both files are byte-identical to the baseline.
   - The exact change is in `docs/integration/dashboard_link.patch`:
     - `src/App.jsx`: a gallery tile "AI Assistant & Delivery Review" that opens `/assistant/` (image `frontend/tile-preview.svg`, drawn like the BI tile).
     - `vite.config.js`: `/api/ai` and `/assistant` proxied to :8003, like `/api/module5`, so the tile also works on the Vite port :8766 and not only through the gateway.
   - Checked on copies of the originals: applies with either `core.autocrlf` setting, the result compiles (esbuild), and `apply -R` restores the originals byte-exact.
   - Apply from the application root: `git apply module_assistant_delivery/docs/integration/dashboard_link.patch` (undo: `git apply -R ...`). Then restart the Vite dev server and refresh the protected baseline.
   - **Applied on 2026-10-18** after the owner confirmed the permission ("of course you have permission, just dont mess up anything that can result in problems with my colleagues' work").
     - Hashes before: `src\App.jsx` A401AD59…3E3F, `vite.config.js` 4CC7D97C…3E4D. After: DFB045A8…EEE7 and B320FA07…E160. The baseline was updated for these two files only.
     - **Checked in the browser** through the gateway (:8080), with the template's own Vite dev server started for the check (cache in a temporary folder, nothing written into `node_modules`):
       - The tile is drawn in the 3D gallery next to Cerebro AI and Business Intelligence, and clicking it opens `/assistant/`. No console errors.
       - The Business Intelligence, Cerebro AI and Bee Tickets tiles still open their own workspaces.
       - The only errors were `/api/module5/*` 502s, because the BI backend (:8002) was not running.
     - `dist/` (the template's old build) was not rebuilt; the gateway serves the Vite dev server.
2. **None needed in the gateway**: its existing routes already cover this module.
