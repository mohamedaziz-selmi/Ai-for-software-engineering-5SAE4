# Starts the module: its private Ollama (port 11435), the backend + UI (port 8003) and, when the platform
# gateway sits next to this module (..\platform_gateway), the gateway (port 8080). Each service runs in its
# own window; close a window to stop that service. Already-running services are left as they are.
#
#     powershell -ExecutionPolicy Bypass -File scripts\start_all.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
function Test-Port($port) { [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) }
function Wait-Port($port, $seconds) { for ($i = 0; $i -lt $seconds -and -not (Test-Port $port); $i++) { Start-Sleep -Seconds 1 }; Test-Port $port }

if (-not (Test-Path (Join-Path $root ".venv\Scripts\python.exe"))) { throw "Run scripts\setup.ps1 first." }

if (-not (Test-Port 11435)) {
    Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "start_ollama.ps1") -WindowStyle Minimized
    if (-not (Wait-Port 11435 60)) { throw "The private Ollama did not start on port 11435" }
}
Write-Host "Private Ollama: http://127.0.0.1:11435"

if (-not (Test-Port 8003)) {
    Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "run_backend.ps1") -WindowStyle Minimized
    if (-not (Wait-Port 8003 120)) { throw "The backend did not start on port 8003 (see its window)" }
}
Write-Host "Module (direct): http://127.0.0.1:8003/assistant/"

$gateway = Join-Path (Split-Path -Parent $root) "platform_gateway"
if ((Test-Path (Join-Path $gateway "run.mjs")) -and (Get-Command node -ErrorAction SilentlyContinue)) {
    if (-not (Test-Port 8080)) {
        Start-Process node -ArgumentList "run.mjs", "gateway" -WorkingDirectory $gateway -WindowStyle Minimized
        [void](Wait-Port 8080 30)
    }
    Write-Host "Through the gateway: http://127.0.0.1:8080/assistant/"
}
