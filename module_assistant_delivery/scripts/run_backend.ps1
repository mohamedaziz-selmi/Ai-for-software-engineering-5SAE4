# Runs the module service on 127.0.0.1:8003 (API under /api/ai, UI under /assistant/).
$ErrorActionPreference = "Stop"
$moduleRoot = Split-Path -Parent $PSScriptRoot
$env:HF_HOME = Join-Path $moduleRoot "storage\hf"
Set-Location (Join-Path $moduleRoot "backend")
& (Join-Path $moduleRoot ".venv\Scripts\python.exe") -m uvicorn api:app --host 127.0.0.1 --port 8003
