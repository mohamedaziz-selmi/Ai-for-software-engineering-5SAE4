# Starts a module-private Ollama server. It does not touch the shared instance on :11434
# (the teammates' chat auto-selects the first model installed there).
$ErrorActionPreference = "Stop"
$moduleRoot = Split-Path -Parent $PSScriptRoot
$models = Join-Path $moduleRoot "storage\ollama\models"
New-Item -ItemType Directory -Force $models | Out-Null

$env:OLLAMA_HOST = "127.0.0.1:11435"
$env:OLLAMA_MODELS = $models
$env:OLLAMA_CONTEXT_LENGTH = "8192"
$env:OLLAMA_KEEP_ALIVE = "30m"
$env:OLLAMA_MAX_LOADED_MODELS = "1"
& ollama serve
