# After a planned RAFT run: build the matched base and the RAFT model in the private Ollama
# (raft\export_gguf.ps1), then evaluate both with exactly the same retrieval, documents, questions and
# prompts. Fallback is always off in the eval runners.
param(
    [string]$Run = "qwen2.5-7b-raft",
    [string]$BaseTag = "qwen2.5:7b-instruct",
    [string]$Tag = "assistant-raft:qwen2.5-7b"
)
$ErrorActionPreference = "Stop"
$moduleRoot = Split-Path -Parent $PSScriptRoot
Set-Location $moduleRoot
$env:HF_HOME = Join-Path $moduleRoot "storage\hf"

$up = $false
try { $null = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:11435/api/version -TimeoutSec 2; $up = $true } catch {}
if (-not $up) {
    Start-Process powershell -ArgumentList "-NoProfile", "-File", (Join-Path $moduleRoot "scripts\start_ollama.ps1") -WindowStyle Hidden
    for ($i = 0; $i -lt 60 -and -not $up; $i++) {
        try { $null = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:11435/api/version -TimeoutSec 2; $up = $true } catch { Start-Sleep -Seconds 1 }
    }
}

& (Join-Path $PSScriptRoot "export_gguf.ps1") -Run $Run -BaseTag $BaseTag

foreach ($pair in @(@("assistant-base-requant:qwen2.5-7b", "qwen2.5-7b-base-requant"), @($Tag, $Run))) {
    & .\.venv\Scripts\python.exe eval\run_raft_test_eval.py --model $pair[0] --label $pair[1]
    & .\.venv\Scripts\python.exe eval\run_assistant_eval.py --model $pair[0] --label $pair[1]
}
& .\.venv\Scripts\python.exe eval\compare_base_raft.py --base qwen2.5-7b-base-requant --raft $Run
