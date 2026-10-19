# AI Assistant & Delivery Review (module service)

A separate service of the freelance platform, run like the template's other services (FastAPI `api.py` with
uvicorn); its interface has its own design (this module only). Through the existing gateway (`platform_gateway/`):

- UI: `http://127.0.0.1:8080/assistant/`
- API: `http://127.0.0.1:8080/api/ai/...` (OpenAPI docs at `/api/ai/docs`)

Directly, without the gateway: `http://127.0.0.1:8003/assistant/`.

From the template dashboard (`npm run dev` in the application root, then `http://127.0.0.1:8080/`, or
`http://127.0.0.1:8766/`), the **AI Assistant & Delivery Review** tile opens the module. The tile and the Vite
proxy for `/api/ai` and `/assistant` come from `docs/integration/dashboard_link.patch`, applied 2026-10-18.

Everything lives in this folder: its own Python (uv-managed, in `storage/python`), virtual
environments, private Ollama instance and model store, SQLite and Chroma databases, React app and docs.
No teammate file, environment, database or the shared Ollama (:11434) is used or modified.

> **Identity is a demo adapter, not authentication.** The platform has no users or projects
> (`docs/AUDIT.md`), so the UI lets you *choose* a synthetic identity. Never expose this service
> beyond localhost.

## Demo

`demo/README.md` walks through every scenario, each verified live, with the files to use: a document to
upload, a defective and a corrected deliverable, and help-desk texts. Short run-and-test guide:
`docs/RUN_AND_TEST.md`. The whole documentation in one file:
`docs/AI_Assistant_Delivery_Review_Mohamed_Aziz_Selmi.pdf` (`scripts\build_report_pdf.py`).

## GitHub

The integrated project (template, teammates' modules, gateway, this module) is in the private repository
https://github.com/mohamedaziz-selmi/freelance-platform. After `git clone`, run `scripts\setup.ps1` here.
- Not in Git: `.env` (keys), downloaded tools and models (`storage\`), `.venv`, the built UI (`frontend\dist`) and the RAFT files.
- Setup re-creates the tools, models and environment, and builds the UI with Node.js 22+. The RAFT adapter and model come with the handoff zip.
- Rayen's 116 MB `train.csv` is stored with Git LFS.

## Setup on a new machine (one command)

Needs: Windows 10/11, [Ollama](https://ollama.com/download) installed, internet on the first run and about
7 GB of free disk (13 GB with the RAFT model; 19 GB free while setup installs it, then it deletes the shipped copy). An NVIDIA GPU is optional (the local model also runs on CPU, more slowly). Node.js is
needed only when `frontend\dist` is missing (a Git clone); the handoff zip ships the built UI.
Keep the folder's path at most 159 characters (e.g. `C:\dev\...\module_assistant_delivery`): Ollama cannot
load a model file whose path exceeds 260 characters, and the setup refuses deeper folders. Setup takes about
30 minutes on the first run (mostly downloads). If you move the folder later, run the setup again (the
`.venv` holds absolute paths).

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

It downloads everything into this folder: `uv` (checksum-verified) and CPython 3.12.15 into `storage\`,
the pinned packages into `.venv\`, `qwen2.5:7b-instruct` into the private Ollama store
(`storage\ollama\models`), the e5 embedding model into `storage\hf`. It then seeds the demo data and runs
the tests. Nothing is installed system-wide. Run it again at any time; finished steps are skipped or
re-checked. `-OllamaModelsFrom <models folder>` copies an existing Ollama store instead of downloading the
model; `-SkipTests` skips the last step.

Copying the whole folder (with `storage\`) instead of the zip also works. Run `setup.ps1` once on the new PC:
it keeps the copied model, embeddings and data and rebuilds `.venv` (internet needed, ~15 minutes). A
whole-folder copy contains your `.env` and therefore your key: remove the `HOSTED_API_KEY` value from the
copy first, and let the receiver put in their own.

## Run

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_all.ps1
```

It starts the private Ollama (:11435), the service (:8003) and, when `..\platform_gateway` exists, the
existing gateway (:8080, unchanged), each in its own minimized window (close a window to stop that
service). The individual scripts still work: `scripts\start_ollama.ps1`, `scripts\run_backend.ps1`.

## Handoff package

```powershell
powershell -ExecutionPolicy Bypass -File scripts\make_handoff.ps1                    # small zip, base model only
powershell -ExecutionPolicy Bypass -File scripts\make_handoff.ps1 -IncludeRaftModel  # + the RAFT model (5.7 GB)
```

| Zip | Size | On the receiver's PC |
|---|---|---|
| Default | 147 MB | Base + RAG; RAFT shows as "not installed" in the model menu |
| `-IncludeRaftModel` | 5.4 GB (builds in about 5 min) | `setup.ps1` installs RAFT in the private Ollama: both models selectable |

`-NoAdapter` also leaves out the 165 MB RAFT adapter (only needed to rebuild the model).

It writes `handoff\module_assistant_delivery.zip`: the module's own work only (code, docs, data, built UI,
lock files, RAFT run 2a adapter and results, scripts), with a SHA-256 manifest. Left out: `.env` (your key),
`.venv*`, `storage\` (Python, models, databases, caches), `node_modules` and logs. It refuses to package
anything that looks like a key. The receiver unzips it next to the other modules and runs `scripts\setup.ps1`.

Configuration: `.env` (git-ignored, created from `.env.example`). Put your Groq key in `HOSTED_API_KEY=`
yourself (never in chat or Git). It enables the delivery review and the assistant fallback (used only when
the local model fails). Then check quality and quota once:

```powershell
.\.venv\Scripts\python.exe eval\check_hosted_api.py
```

## Checks

```powershell
cd backend; ..\.venv\Scripts\python.exe -m pytest; cd ..
.\scripts\check_protected.ps1                    # no teammate/shared file changed since the baseline
```

Evaluations (fallback always off), with results in `eval/results/`:

```powershell
.\.venv\Scripts\python.exe eval\run_retrieval_eval.py intfloat/multilingual-e5-base
.\.venv\Scripts\python.exe eval\run_assistant_eval.py --model qwen2.5:7b-instruct --label qwen2.5-7b-base
.\.venv\Scripts\python.exe eval\run_raft_test_eval.py --model qwen2.5:7b-instruct --label qwen2.5-7b-base
.\.venv\Scripts\python.exe eval\run_review_live.py --label qwen2.5-7b-base     # needs the backend on :8003
```

## Models

- Assistant: `Qwen/Qwen2.5-7B-Instruct`, served as Ollama `qwen2.5:7b-instruct` (Q4_K_M) by the private Ollama.
  Chosen by measurement against `Qwen/Qwen3-4B-Instruct-2507`: `eval/results/model_selection.md`.
- Delivery review and assistant fallback: hosted `openai/gpt-oss-120b` on Groq's free tier (key in `.env`).
- RAFT run 2a: `assistant-raft2a:qwen2.5-7b` (same checkpoint + LoRA, merged, Q5_0), in the same private Ollama.
  A choice in the UI's model menu and the base model's first backup; **not the default**: it lost the final test
  (19/24 vs 23/24, `docs/report/raft2_results.md`). One model is loaded at a time. Run 1 was not adopted
  (`eval/results/raft_findings.md`).
- Disk: the folder is about 13 GB, 9.6 GB of it the two served models. The RAFT model file is kept once, inside the
  private Ollama (`make_handoff.ps1 -IncludeRaftModel` reads it from there). Training-only files were deleted on
  2026-10-19 (`.venv-raft`, the 4-bit training weights, export intermediates, checkpoint); to train again, rebuild
  them with the first and third commands of the RAFT section below.
- Embeddings: `intfloat/multilingual-e5-base` on CPU.

## RAFT

```powershell
.\raft\setup_raft.ps1                                              # .venv-raft: CUDA torch + Unsloth (pinned: raft\requirements-raft.lock.txt)
.\.venv\Scripts\python.exe raft\data_gen.py --projects 40 --seed 7 # synthetic FR/EN data, split by project
.\.venv-raft\Scripts\python.exe raft\download.py unsloth/Qwen2.5-7B-Instruct-bnb-4bit
# stop the private Ollama first (frees VRAM), then:
.\.venv-raft\Scripts\python.exe raft\train.py --model unsloth/Qwen2.5-7B-Instruct-bnb-4bit --run qwen2.5-7b-smoke --smoke
.\.venv-raft\Scripts\python.exe raft\train.py --model unsloth/Qwen2.5-7B-Instruct-bnb-4bit --run qwen2.5-7b-raft --epochs 2
.\raft\after_training.ps1                                          # merge -> GGUF -> Q5_0 -> Ollama (base + RAFT), evals (fallback off)
.\.venv\Scripts\python.exe eval\compare_base_raft.py --base qwen2.5-7b-base-requant --raft qwen2.5-7b-raft
```

## Layout

See `docs/MODULE_SPEC.md` §6. Documentation: `CLAUDE.md` (working rules), `docs/MODULE_SPEC.md`
(spec working copy), `docs/AUDIT.md` (verified repository facts), `docs/AI_USAGE_LOG.md`.

## Licences of third-party models

Qwen2.5-7B-Instruct and Qwen3-4B-Instruct-2507: Apache-2.0 (Alibaba Qwen). multilingual-e5-base: MIT
(Microsoft). The weights are downloaded into `storage/` and are not redistributed with this code.
