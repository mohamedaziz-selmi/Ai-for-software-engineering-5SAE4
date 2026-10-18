# Cerebro

Cerebro is a React portfolio built with Vite. The project gallery, project-detail
dialog, theme toggle, navigation panels, and drag-to-pan interaction are
implemented as React components. Portfolio artwork is served from the local
archive of original site media.

## Run locally

```powershell
npm.cmd install
npm.cmd run dev
```

Open the local URL printed by Vite (by default, `http://localhost:8766/`).

## Local Ollama chat

The Cerebro AI triangle uses the local Ollama API at `http://127.0.0.1:11434`.
Start Ollama before opening the chat; the UI discovers installed models and
streams replies locally. It prefers `llama3.2:3b` when installed and lets you
choose another installed model from the model selector.

Below the chat, a scrollable tools area contains a freelance proposal generator
and a customer-review sentiment classifier. Both use the currently selected
Ollama model.

If you do not have a model installed yet, run:

```powershell
ollama pull llama3.2:3b
```

Create a production build with `npm.cmd run build`. The Vite development and
preview servers proxy chat requests to the local Ollama API.
