# Serve a trained RAFT adapter (and a matched base) from the private Ollama.
#
# Why this path: Ollama 0.40.6 rejects LoRA ADAPTER lines ("LoRA adapters are no longer supported"), its
# safetensors importer (the only one that quantizes) rejects Qwen2ForCausalLM, and GGUF imports must arrive
# pre-quantized. So: merge offline -> bf16 GGUF (llama.cpp converter, pure Python) -> Q5_0 GGUF (gguf-py,
# pure Python) -> `ollama create` without quantization. No compiled third-party binaries are used.
# Base and RAFT go through the identical path, so the comparison isolates the adapter.
#
# Requires: storage\tools\llama.cpp-v0.5.0-src\extracted (llama.cpp v0.5.0 source, released 2026-09-23),
# the private Ollama running (scripts\start_ollama.ps1), and the trained adapter in raft\outputs\<Run>\adapter.
param([string]$Run = "qwen2.5-7b-raft", [string]$BaseTag = "qwen2.5:7b-instruct")
$ErrorActionPreference = "Stop"
$moduleRoot = Split-Path -Parent $PSScriptRoot
Set-Location $moduleRoot
$env:HF_HOME = Join-Path $moduleRoot "storage\hf"
$env:OLLAMA_HOST = "127.0.0.1:11435"
$py = ".\.venv-raft\Scripts\python.exe"
$converter = "storage\tools\llama.cpp-v0.5.0-src\extracted\convert_hf_to_gguf.py"
$out = "raft\outputs\$Run"
$template = (ollama show --modelfile $BaseTag) | Where-Object { $_ -notmatch '^FROM ' }

foreach ($mode in "base", "raft") {
    $tag = if ($mode -eq "base") { "assistant-base-requant:qwen2.5-7b" } else { "assistant-raft:qwen2.5-7b" }
    & $py raft\merge_export.py --mode $mode --run $Run --tag $tag --no-import
    if ($LASTEXITCODE) { throw "merge $mode failed" }
    if (-not (Test-Path "$out\$mode-bf16.gguf")) {
        & $py -E -s $converter "$out\merged-$mode-bf16" --outtype bf16 --outfile "$out\$mode-bf16.gguf"
        if ($LASTEXITCODE) { throw "GGUF conversion $mode failed" }
    }
    & $py -E -s raft\requant_gguf.py "$out\$mode-bf16.gguf" "$out\$mode-q5_0.gguf"
    if ($LASTEXITCODE) { throw "requantization $mode failed" }
    $gguf = (Resolve-Path "$out\$mode-q5_0.gguf").Path.Replace('\', '/')
    ("FROM $gguf`n" + ($template -join "`n")) | Set-Content -Encoding utf8 "$out\Modelfile.$mode-q5_0"
    ollama create $tag -f "$out\Modelfile.$mode-q5_0"
    if ($LASTEXITCODE) { throw "ollama create $tag failed" }
}
ollama list
