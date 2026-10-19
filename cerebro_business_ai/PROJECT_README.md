# CEREBRO — start here

Local AI decision-support application: hiring assistance, sales/inventory planning, job-posting risk review and product-listing assistance. Current interface: React; current running backend: a FastAPI gateway and four independent AI services; local generation: Ollama with `gemma3:4b`.

**Sending the entire `ai` folder to a friend is possible. Use the tested portable application inside it. Do not reuse your copied Python environment or run the old machine-specific launcher on the friend's PC.**

## Your friend's first launch — Windows 10/11 x64

1. Copy/extract the whole folder to a writable local directory, for example `C:\Cerebro\ai`. Do not run it inside an archive or from Program Files.
2. Open **`release\Cerebro_Windows_x64`** inside that folder.
3. Double-click **`SETUP.cmd`** in that directory. It prepares its own Python runtime, installs the bundled dependencies offline, verifies the saved models and checks Ollama. Since your friend already has Ollama, no reinstall is normally necessary.
4. Setup downloads **`gemma3:4b` only if missing**. Allow approximately 3–4 GB of internet download and keep the window open. If an existing matching CLI pull is detected, setup stops instead of launching a duplicate; let it finish, then retry.
5. When the servers are healthy, the browser opens **http://127.0.0.1:8905/**.

Later, run **`START.cmd`** from the same directory. Use **`STOP.cmd`** to stop that copy of Cerebro and **`CHECK.cmd`** to inspect its models/services. Ollama is deliberately left running by STOP.

No system Python, Node.js, Docker, Maven or database server is required for this portable launch. A clean Windows installation may need Microsoft's official x64 Visual C++ Redistributable if a native DLL fails; see the handover guide. The recipient's PC has not been tested.

**Do not run `portable\cerebro.ps1` directly from the outer source folder:** that folder does not have the portable release's installer layout and checksum manifest. **Do not use root `start-cerebro.ps1` on another PC:** it contains original-machine paths. The portable `SETUP.cmd` is the handover entry point.

## Before sending the whole folder

Read [the sharing checklist](docs/FRIEND_HANDOVER.md#before-you-send-the-folder). A raw project copy is not a sanitized distribution. Avoid transferring API tokens, real `.env` files, personal sales/customer/job inputs, local databases and request logs. Review dataset redistribution conditions; the friend does **not** need raw training datasets for inference.

The prepared [portable ZIP](release/Cerebro_Windows_x64.zip) is approximately **233 MB** and is the cleaner alternative. It excludes original virtual environments, private runtime state, raw training datasets and credential files. Gemma weights are not embedded in either the ZIP or the source folder: Ollama stores those separately on each PC.

The entire source folder contains **duplicate release/test copies**. In particular, `release\Friend Test` is an installation-validation workspace, **not** the copy your friend should launch.

## What the four modules actually do

| Module | What it needs | What it returns | Important limit |
|---|---|---|---|
| Hiring assistant | Short role/business brief and English/French selection | Editable advertisement, proposed outcomes/skills, interview kit, exercise, onboarding plan and missing decisions | Needs Gemma; recommendations are not employer facts |
| Sales & inventory | One identified product's dated sales history; optional price/traffic/promotion/stock context | Chronological validation, selected baseline, forecast chart/table, warnings and inventory quantities | Learns from supplied history; cannot infer market demand from a name alone |
| Job verification | Original job-posting text; optional employer and known official domain | Saved classifier signal, separate evidence warnings, extracted pay/contact details and verification actions | Uncalibrated model signal, not proof or an employer background investigation |
| Product assistant | Short brief containing verified product facts, optional title/category and language | Editable listing, feature/benefit pairs, buyer questions, missing facts and catalog comparison references when relevant | RAG does not verify your product's specifications; needs Gemma for writing |

With no sales history, choose **No history: scenarios**. It projects your explicitly supplied low/base/high unit estimates or traffic × conversion assumptions. It is **not a trained demand forecast**.

## Documentation

- [Friend handover, sharing checklist and troubleshooting](docs/FRIEND_HANDOVER.md)
- [Full technical documentation: architecture, inputs/outputs, models, data, setup, APIs, testing and limitations](docs/TECHNICAL_HANDBOOK.md)
- [Documentation index and historical-note guidance](docs/README.md)
- [Portable release validation record](release/Cerebro_Windows_x64/VALIDATION.md)
- [Portable model/source and licensing notices](release/Cerebro_Windows_x64/MODEL_SOURCES.md)

Swagger: http://127.0.0.1:8900/docs for the gateway; ports 8901–8904 `/docs` for individual services. Swagger URLs work after startup.

## Last executed verification — 19 October 2026

Frontend production build passed; **113 backend tests passed**, **11 Edge browser tests passed**, and **21 portable HTTP integration checks passed**, including actual Gemma hiring/product generation, fraud inference, M5 inference and a positive catalog retrieval probe. Setup was exercised with a fresh private runtime in a folder containing spaces; restart, duplicate-start protection and ownership-checked shutdown were checked. See the validation record for timings, warnings and hardware snapshots.

These results are from the development PC, not the friend's hardware. They are functionality checks, not a claim of 90% accuracy across all modules. ResourceGuard cannot guarantee a hard GPU-utilization ceiling. Existing phase reports and the legacy Spring Boot prototype are retained; their old descriptions must not override the current handbooks or executed evidence.
