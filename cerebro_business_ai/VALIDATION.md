# Portable release validation — 19 October 2026

Executed on the development Windows x64 PC, not on the recipient's machine. No new training or Kaggle download was performed. Original models/results were preserved.

## Executed checks

- Frontend production build: passed (TypeScript + Vite).
- Backend suite: **113 passed**, 2 warnings (Starlette deprecation and an existing XGBoost serialization compatibility warning).
- A ZIP was extracted into a separate folder containing spaces. The official embedded Python runtime was extracted there; 31 application packages plus pip were installed from bundled wheels with `--no-index`. `pip check`: no broken requirements.
- The private runtime loaded the actual fraud classifier and predicted; loaded the M5 regressor and forecast seven days; imported all five FastAPI applications. Catalog retrieval was checked separately against a known matching query, `Bones skateboard wheels`.
- Six packaged servers ran on ports **18900–18905**, separate from the original app on 8900–8905. **21/21 HTTP integration checks passed**, including all health/OpenAPI endpoints, built frontend, dynamic API configuration, saved fraud/M5 inference, history planning, no-history scenarios, invalid-input rejection, catalog retrieval and two real Gemma generations.
- **11/11 Edge browser tests passed** against the built packaged frontend: CSV validation, chronological holdout/charts/export, intermittent demand, planned-change reset, no-history scenarios and multilingual fraud evidence.
- Ownership-checked shutdown stopped all six packaged processes and left the original app and Ollama running. No unrelated process was killed.

## Actual local inference observations

| Request | HTTP latency | Schema | Repairs |
|---|---:|---|---:|
| English hiring package | 64.384 s | valid | 1 |
| French product listing | 17.730 s | valid | 0 |

Generation used the existing `gemma3:4b` model; no duplicate pull was initiated. Responses contain editable proposed recommendations, not comprehensive factual verification. The sample product generated from supplied facts; the separate positive catalog probe establishes retrieval, not automatic verification of those facts.

Resource snapshots across those two inference requests: CPU **7.8–35.2%**, RAM **39.2–47.4%**, VRAM **4.01–66.69%**, GPU temperature **52–60°C**. These are before/after snapshots, **not continuous peaks**. One GPU-utilization snapshot reached **95%**: ResourceGuard does not hard-cap GPU compute utilization, so an 85% utilization ceiling was not achieved or guaranteed. Admission checks, observed-memory/temperature safety checks and half-core thread requests remain active. Inference on another PC may differ or be rejected when resources are busy.

## Fixes found during packaging validation

Windows pip bootstrap invocation was corrected. Windows PowerShell 5 JSON-array handling in process ownership checks was corrected. A browser test fixture path was made independent of the shell's launch directory. No trained model was modified.

## Scope limits

The actual recipient's Windows installation, GPU driver, Visual C++ prerequisite and Ollama download have not been tested. A native-DLL failure may require the official Microsoft x64 Visual C++ Redistributable; see README_FIRST.md. No raw training datasets, personal registries, API keys, original environment files or original runtime directories are included. Historical benchmark results do not establish accuracy on unseen business data.

## Reproduce local checks

From the extracted package:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File portable/cerebro.ps1 -Action Setup -BasePort 18900 -NoBrowser -NoStart
powershell -NoProfile -ExecutionPolicy Bypass -File portable/cerebro.ps1 -Action Start -BasePort 18900 -NoBrowser
.runtime/python/python.exe portable/verify_api.py --base-port 18900 --llm --output local-api-verification.json
.runtime/python/python.exe -m pip check
powershell -NoProfile -ExecutionPolicy Bypass -File portable/cerebro.ps1 -Action Stop -BasePort 18900
```

The HTTP verifier writes to a new report path only; it will not overwrite previous evidence. Browser/backend source tests require development test dependencies, which setup intentionally does not install.
