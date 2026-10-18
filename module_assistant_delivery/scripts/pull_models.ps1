# Pulls the assistant base model into the module-private Ollama instance (start_ollama.ps1 must be running).
param([string]$Model = "qwen2.5:7b-instruct")
$env:OLLAMA_HOST = "127.0.0.1:11435"
& ollama pull $Model
