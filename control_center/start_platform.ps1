# Starts the whole front end of the project in one go: the control center (:8090), then the platform module
# (group gateway :8080, facade :8081, dashboard :8766) through it, then any modules named with -With.
# Every other module is switched on or off from the floating bubble, on any page at http://127.0.0.1:8080/.
#
#   powershell -ExecutionPolicy Bypass -File control_center\start_platform.ps1 [-With assistant,business] [-NoBrowser]
#
# Module ids: platform, chat, rag, sentiment, bi, assistant, advisor, marketplace, business.
param([string[]]$With = @(), [switch]$NoBrowser)
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$control = "http://127.0.0.1:8090"

function Get-State { try { Invoke-RestMethod "$control/api/state" -TimeoutSec 5 } catch { $null } }
function Wait-Module([string]$id, [int]$seconds) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        $m = (Get-State).modules | Where-Object id -eq $id
        if ($m.status -eq "on") { return $m }
        if ($m.status -in @("off", "not_set_up") -and $m.note -and $m.note -notmatch " is (on|off)\.") { throw "$id did not start: $($m.note)" }
        Start-Sleep -Milliseconds 800
    }
    throw "$id did not start within $seconds s (see control_center\logs)"
}
function Start-Module([string]$id, [int]$seconds = 240) {
    $m = (Get-State).modules | Where-Object id -eq $id
    if (-not $m) { throw "Unknown module: $id" }
    if ($m.status -eq "on") { Write-Host "  $($m.name): already on"; return }
    if ($m.status -eq "not_set_up") { Write-Host "  $($m.name): not set up on this PC ($($m.notSetUp -join ', '))" -ForegroundColor Yellow; return }
    Invoke-RestMethod "$control/api/modules/$id/start" -Method Post -Headers @{ "X-Control" = "1" } | Out-Null
    Write-Host "  $($m.name): starting..."
    $null = Wait-Module $id $seconds
    Write-Host "  $($m.name): on" -ForegroundColor Green
}

if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw "Node.js is not installed (needed for the gateway and the dashboard)." }
if (-not (Get-State)) {
    Write-Host "Starting the control center on :8090"
    New-Item -ItemType Directory -Force (Join-Path $here "logs") | Out-Null
    Start-Process -FilePath "node" -ArgumentList "`"$(Join-Path $here 'server.mjs')`"" -WorkingDirectory (Split-Path -Parent $here) -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $here "logs\control.log") -RedirectStandardError (Join-Path $here "logs\control.err.log")
    for ($i = 0; $i -lt 40 -and -not (Get-State); $i++) { Start-Sleep -Milliseconds 500 }
    if (-not (Get-State)) { throw "The control center did not start. See control_center\logs\control.err.log" }
}
Write-Host "Control center: $control/"
Start-Module "platform" 180
foreach ($id in $With) { Start-Module $id }

Write-Host "`nReady. Open http://127.0.0.1:8080/ ; the round button on every page is the control center." -ForegroundColor Green
if (-not $NoBrowser) { Start-Process "http://127.0.0.1:8080/" }
