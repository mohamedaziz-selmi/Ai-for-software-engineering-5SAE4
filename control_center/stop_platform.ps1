# Stops every running module through the control center (the platform last), then the control center itself.
# The user's own Ollama app is never stopped; its models are unloaded so the GPU is free.
#
#   powershell -ExecutionPolicy Bypass -File control_center\stop_platform.ps1 [-KeepControl]
param([switch]$KeepControl)
$ErrorActionPreference = "Stop"
$control = "http://127.0.0.1:8090"
function Get-State { try { Invoke-RestMethod "$control/api/state" -TimeoutSec 5 } catch { $null } }

$state = Get-State
if (-not $state) { Write-Host "The control center is not running: nothing to stop through it."; exit 0 }
$order = @($state.modules | Where-Object { $_.status -in @("on", "partial") -and $_.id -ne "platform" }) + @($state.modules | Where-Object { $_.id -eq "platform" -and $_.status -in @("on", "partial") })
foreach ($m in $order) {
    Write-Host "  stopping $($m.name)..."
    Invoke-RestMethod "$control/api/modules/$($m.id)/stop" -Method Post -Headers @{ "X-Control" = "1" } | Out-Null
    $deadline = (Get-Date).AddSeconds(60)
    do { Start-Sleep -Milliseconds 800; $now = (Get-State).modules | Where-Object id -eq $m.id } while ($now.status -eq "stopping" -and (Get-Date) -lt $deadline)
    Write-Host "  $($m.name): $($now.status). $($now.note)"
}
if (-not $KeepControl) {
    $line = netstat -ano -p TCP | Select-String ":8090\s+\S+\s+LISTENING\s+(\d+)" | Select-Object -First 1
    if ($line) {
        $pid8090 = [int]$line.Matches[0].Groups[1].Value
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $pid8090"
        if ($proc.CommandLine -match "control_center[\\/]server\.mjs") { Stop-Process -Id $pid8090; Write-Host "Control center stopped." }
    }
}
