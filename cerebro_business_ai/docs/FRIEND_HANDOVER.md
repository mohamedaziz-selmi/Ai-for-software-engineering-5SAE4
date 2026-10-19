# CEREBRO — complete friend handover

This guide assumes the entire outer **`ai` folder** was copied to another **Windows 10/11 Intel/AMD x64** PC. The friend already has Ollama, but may not have Gemma. No new training is needed.

## Before you send the folder

Do these checks on a **sharing copy**, not by deleting files from your working project:

| File/folder | Transfer guidance |
|---|---|
| `release/Cerebro_Windows_x64/` | Keep: this is the tested, self-contained application payload |
| `release/Cerebro_Windows_x64.zip` | Optional if sending the extracted payload too; redundant archive but useful for recovery |
| `services/`, `ai-service/`, `frontend/`, `docs/`, root reports | Keep if sharing source/history; inspect any local inputs/output artifacts first |
| Real `.env` files, `kaggle.json`, API tokens, private keys | **Do not send**; credentials are not required for the portable app |
| `.env.example`, `.env.microservices.example` | Share templates only after checking they contain placeholders, not real secrets |
| `.venv-phase2/`, other virtual environments, `frontend/node_modules/` | Exclude if practical: large and machine-specific; the friend must not rely on them |
| `release/Friend Test/` | Exclude: duplicate installation used for validation, with runtime/log/test state |
| `release/installer-cache/` | Optional to exclude: build cache duplicated inside the runnable release's `installer/` |
| `.runtime/` inside any already-installed release copy | Exclude from the sharing copy: setup recreates it; do not transfer an installed Python environment |
| `.tools/`, `.codex-*`, `.pytest_cache/`, `test-results/` | Not needed for portable use; logs/screenshots/results may contain private inputs |
| `.cerebro-*.log*`, `.cerebro-processes.json`, request/experiment outputs | Inspect or exclude: unnecessary for launch and may expose submitted data or local paths |
| `data/*.sqlite*`, `data/*.db*` | Do not send personal registries/history. The inference-admission SQLite file is a local lock database, not a required model; the app recreates it |
| Raw Kaggle/Hugging Face datasets | Not needed for inference. Review upstream redistribution rights before transferring them |
| `sample_sales_histories/` | Demo material in this project: explicitly synthetic, not measured business data |

The filename inspection during this handover found the root environment **examples** and inference-admission SQLite files; it did not reveal a `kaggle.json` or real `.env` filename in the inspected non-vendor scope. This is **not a comprehensive secret/content audit**. Screenshots, CSVs, reports and source can also contain sensitive information or absolute usernames.

Do not send your separate Ollama model directory or personal Kaggle configuration. Gemma will be downloaded under the friend's own Ollama installation. Nothing in this handover removes your local work automatically.

## Where your friend must click

Example layout after copying:

```text
C:\Cerebro\ai\
  README.md
  docs\FRIEND_HANDOVER.md
  services\                    editable source
  frontend\                    editable source
  release\
    Cerebro_Windows_x64\       RUN THIS COPY
      SETUP.cmd
      START.cmd
      STOP.cmd
      CHECK.cmd
      release-manifest.json
      installer\
      portable\
      services\
      ai-service\artifacts\
      frontend\dist\
```

The root source folder and the runnable release are **different copies**. Editing the outer source does not automatically update the built release. Do not launch `release/Friend Test`, reuse `.venv-phase2`, or run root `start-cerebro.ps1` with its original-machine paths.

## Minimum preparation

- Windows 10/11 x64 on Intel/AMD. ARM/native Linux/macOS support was not tested for this bundle.
- Keep at least **8 GB free** for setup/model files, plus space for the copied project. Ensure the volume holding Ollama models has enough room too.
- Prefer **16 GB RAM or more**. The original test GPU had 6 GB VRAM, but this does not guarantee the same fit or performance elsewhere. CPU generation is possible but can be slow.
- Ollama installed and able to run. It need not be on PATH: setup also checks standard per-user and Program Files executable locations.
- Internet for missing Gemma weights, approximately **3–4 GB**. Python application dependencies are bundled offline.

Use a local writable directory; avoid Program Files, running inside ZIP preview, read-only storage or cloud-synced folders during installation. Do not disable antivirus or global PowerShell security policy. If Windows blocks the downloaded archive, inspect it and use Properties → Unblock before extracting if appropriate.

## First setup

Open `ai\release\Cerebro_Windows_x64` and double-click **SETUP.cmd**.

Setup:

1. Verifies payload SHA-256 hashes against `release-manifest.json`.
2. Checks disk space on the package's own volume and reports RAM.
3. Uses a local lock to prevent concurrent setup instances.
4. Extracts Python 3.11.9 into `.runtime/python` and installs bundled binary wheels using `--no-index`.
5. Loads/predicts with saved fraud/M5 models, probes RAG and imports five FastAPI applications.
6. Connects to Ollama on `127.0.0.1:11434`, starting its server if needed and available.
7. Checks `gemma3:4b`; pulls it only if absent. A matching existing CLI pull is not duplicated.
8. Starts the gateway, four services and built frontend, checks their health, and opens the browser.

The scripts change neither global PATH nor system Python. If a native DLL prerequisite is missing, install the official [Microsoft x64 Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe), then retry. That installer may require administrator approval; Cerebro does not silently install it.

Review [Gemma terms](https://ai.google.dev/gemma/terms) and the release's model/source notices. Setup does not bypass model terms, Kaggle authentication or dataset licensing.

## Every subsequent session

From the **same runnable directory**:

- `START.cmd`: starts Cerebro and opens its interface.
- `STOP.cmd`: stops only processes matching this package's Python executable, command token and recorded creation time. Leaves Ollama alone.
- `CHECK.cmd`: loads saved artifacts and checks frontend/gateway availability. Health is not proof that every LLM request will succeed.

After a power interruption, rerun SETUP if installation was incomplete; otherwise START. Complete model pulls are reused. If a dependency installation was interrupted, rerun SETUP. If managed processes remain alive, use STOP before retrying. Do not kill unrelated processes merely to free ports.

Interface: **http://127.0.0.1:8905/**. Gateway Swagger: **http://127.0.0.1:8900/docs**. No API key is needed for local Ollama.

For occupied ports, open PowerShell in the runnable directory:

```powershell
.\START.cmd -BasePort 18900
.\CHECK.cmd -BasePort 18900
# Browser: http://127.0.0.1:18905/
.\STOP.cmd
```

All six ports must be free. The built frontend receives the matching API URL dynamically. START without `-BasePort` returns to defaults; keep using the option if needed.

## Four useful first tests

### Hiring

Brief: “Hire a full-time React and TypeScript developer in Tunis to maintain a clinic appointment-booking application. Require two years of React experience. Salary and benefits are undecided.” Select English or French and generate. Expect an editable hiring package with missing decisions, not invented salary/benefits. Inference may take tens of seconds or longer; avoid repeated submissions.

### Sales/inventory

Use a CSV from `sample_sales_histories` inside the runnable release. Select a single product, validate/import history, and initially leave planned changes **off**. Try horizon 7 days, stock 30, incoming stock 0 and supplier lead time 7 days. These are demo inputs, not optimized business settings. Inspect charts, backtests, warnings and inventory quantities. **Zero recommended order quantity is not zero sales demand.**

For a new product, select **No history: scenarios**, name it, set low 3, expected 8, high 15 units/day, horizon 14, stock 30 and lead time 7. The base scenario projects 112 units; these are assumptions, not an ML prediction.

### Job verification

Paste: “Travail à domicile sans expérience. Salaire de 3000 euros par mois. Payez 150 euros de frais avant de commencer. Contact Telegram.” Review original-text evidence, payment warnings and extracted currency. Classifier percentage and rule warnings are separate. This synthetic test is not a fraud-accuracy benchmark.

### Product listing

Brief: “Black Bluetooth headphones, new, USB cable included. Battery life, brand and warranty are unconfirmed.” Generate a listing. Unknown facts should remain missing or require verification. No relevant catalog hit is acceptable; another product's specifications must not become yours.

## Troubleshooting

| Symptom | Action |
|---|---|
| “Run SETUP first” | Use SETUP in `release/Cerebro_Windows_x64`, not the outer source `portable` folder |
| Missing/damaged payload | Re-extract the original clean ZIP; do not edit hashes to hide corruption |
| Ollama missing/unreachable | Open Ollama; check executable/local API; install only from [official Windows downloads](https://ollama.com/download/windows) if truly missing |
| Missing Gemma | Rerun SETUP, or run `ollama pull gemma3:4b`; use the absolute executable path if not on PATH |
| Pull already running | Let it finish, then rerun SETUP; do not start another |
| Port occupied | Use alternate BasePort; scripts do not kill the conflicting process |
| Writing busy/warm/unavailable | Wait for generation, reduce other workloads, inspect temperatures/model availability and retry; never bypass ResourceGuard |
| Native DLL load error | Install Microsoft's x64 Visual C++ runtime linked above and retry |
| CSV rejected | Check dates, duplicates/gaps, numeric nonnegative units and product selection; do not turn unknown sales into zero |
| No graph after failed request | Fix validation/API error; missing results do not mean zero demand |
| Outer-source edits not visible | The release is a separate prebuilt copy; use development mode or deliberately rebuild it |
| Low fraud score despite warnings | Classifier output is uncalibrated; rules can independently require investigation |

Read `.runtime/logs/*.err.log` **inside the runnable copy**, not outer `.cerebro-*` logs. Remove personal text before sharing logs.

## Evidence and limitations

The release's `VALIDATION.md` records 113 backend tests, 11 browser tests, 21 HTTP checks and actual Gemma inference timings on the development PC. The friend's PC is untested. Status badges do not establish quality, calibration or factual correctness. No full-scale training runs during setup.

Read [TECHNICAL_HANDBOOK.md](TECHNICAL_HANDBOOK.md) for internals and developer commands.
