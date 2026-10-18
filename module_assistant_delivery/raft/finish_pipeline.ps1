# Unattended post-training pipeline: wait for the planned run, then export + evals + comparison.
# Writes raft/results/<run>-pipeline.log. Never switches the app's ASSISTANT_MODEL: that stays a human decision.
# Reviews use the hosted model (owner decision), so the RAFT adapter only affects the assistant.
param([string]$Run = "qwen2.5-7b-raft", [string]$Tag = "assistant-raft:qwen2.5-7b", [string]$BaseLabel = "qwen2.5-7b-base")
$moduleRoot = Split-Path -Parent $PSScriptRoot
Set-Location $moduleRoot
$log = Join-Path $moduleRoot "raft\results\$Run-pipeline.log"
function Note($m) { "$(Get-Date -Format s) $m" | Tee-Object -FilePath $log -Append }

Note "waiting for training process"
while (Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object { $_.CommandLine -like "*train.py*--run $Run*" }) { Start-Sleep -Seconds 30 }
$result = Join-Path $moduleRoot "raft\results\$Run.json"
if (-not (Test-Path $result)) { Note "no result file: training did not finish; stopping"; exit 1 }
$status = (Get-Content $result -Raw | ConvertFrom-Json).status
Note "training status: $status"
if ($status -ne "completed") { exit 1 }

Note "export + evals"
& (Join-Path $PSScriptRoot "after_training.ps1") -Run $Run -Tag $Tag *>> $log

& .\.venv\Scripts\python.exe eval\compare_base_raft.py --base $BaseLabel --raft $Run *>> $log
Note "pipeline finished"
