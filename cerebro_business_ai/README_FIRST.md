# Cerebro — Windows 10/11 x64

## First launch

1. Extract **all** files from the ZIP to a writable folder (for example `C:\Cerebro`). Do not run inside the ZIP or Program Files.
2. Keep Ollama installed. Double-click **SETUP.cmd**. No administrator rights, Python installation or Node.js installation are needed.
3. Wait for dependencies to be installed from the bundled wheels. Setup checks Ollama and downloads `gemma3:4b` only if missing (approximately 3.3 GB; internet required for this download). Leave that window open. Interrupted pulls can be resumed by running SETUP again.
4. The application opens at **http://127.0.0.1:8905/** once the six local servers are healthy.

Later: **START.cmd** starts Cerebro; **STOP.cmd** stops only this package's servers (not Ollama); **CHECK.cmd** checks saved models and local services. Re-extract the original ZIP if setup reports damaged files. A power interruption is recoverable: run SETUP again if initial installation was incomplete, otherwise START.

## What is included

- Four AI services, gateway, prebuilt React application and editable source.
- Saved fraud and forecasting models, Amazon comparison retrieval index and recorded metrics. No training or Kaggle login is needed to run them.
- Ten **synthetic** example sales CSVs in `sample_sales_histories` for UI testing, not evidence of forecasting accuracy.
- Private Python 3.11.9 Windows x64 runtime and pinned offline dependency wheels. Installed dependencies stay in `.runtime`; nothing changes your system Python or PATH.
- Gemma weights are **not** included; Ollama stores them in its normal user model directory. Review the Gemma terms before use: https://ai.google.dev/gemma/terms

## Requirements and limitations

64-bit Intel/AMD Windows 10/11, at least 8 GB free for setup/model files, preferably 16 GB RAM. More space is needed if Ollama stores models on another volume. A GPU is optional; generation may be slow on CPU. No exact GPU fit, temperature or utilization cap can be guaranteed. ResourceGuard retains admission checks and safety limits; unavailable sensors are reported, not invented. Only one local generation is admitted at a time.

This is a local prototype: keep ports private, do not expose it to the internet. Fraud signals are not proof; check the employer independently. Forecasts require useful history; no-history mode produces assumption-driven scenarios, not learned demand. Product catalog hits are comparison material, not verified specifications of your item. Generation needs the local model and must not invent unknown facts. Historical benchmark scores do not establish accuracy on your own data.

If Windows blocks downloaded files, inspect the files and unblock the ZIP in its Properties before extracting. Do not disable antivirus or system security. Scripts use a per-process PowerShell execution policy; they do not alter the machine policy. Organization policy may still prevent launch.

## Troubleshooting

- Read `.runtime\logs\*.err.log` for startup failures.
- If a native DLL cannot load on a clean Windows PC, install Microsoft's official x64 Visual C++ Redistributable (https://aka.ms/vs/17/release/vc_redist.x64.exe) and retry. This system prerequisite is not installed silently; administrator approval may be required.
- Ollama not detected: open Ollama, then retry. Setup checks PATH and the standard per-user and Program Files locations. Official installer: https://ollama.com/download/windows
- Missing Gemma: run `ollama pull gemma3:4b` or rerun SETUP. An existing matching pull is not started twice by the script.
- Ports occupied: do not stop unrelated apps. From this folder run `START.cmd -BasePort 18900`; use `CHECK.cmd -BasePort 18900` for the matching checks. Frontend becomes http://127.0.0.1:18905/ and its API configuration follows automatically.
- If startup was interrupted, use STOP then START. Ownership checks prevent stopping a different process that reused an old PID.
- Keep the whole folder together. Do not transfer `.runtime` from a different Windows installation; transfer the original ZIP instead.

Swagger: http://127.0.0.1:8900/docs (gateway), and ports 8901–8904 `/docs` (individual services).

## Source and reproducibility

`services` and `ai-service/app` contain backend source; `frontend/src` contains frontend source; `portable/requirements-runtime.txt` pins the runtime dependencies. `release-manifest.json` contains payload SHA-256 hashes checked during setup. Dependency licenses are included in their wheel metadata and runtime archive; see `MODEL_SOURCES.md` for dataset/model notes. Local databases are newly created; no original user's registry, tokens, logs or environment files are included.
