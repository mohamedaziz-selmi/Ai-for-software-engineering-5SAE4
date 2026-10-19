# Demo inputs for the teammates' tiles

These modules belong to the teammates. Switch them on with the control center's round button (see `demo/README.md`). The dashboard is at http://127.0.0.1:8080 (through the gateway) or
http://127.0.0.1:8766 (frontend directly).

| Tile | Service behind it | Try |
|---|---|---|
| **Cerebro AI** (Proposal Review Workspace) | retrieval :8000 (hybrid semantic + BM25), sentiment :8001, shared Ollama :11434 | *What is the hard budget limit and deadline type for JOB-003?* |
| **Business Intelligence** | :8002 | Opens on the overview: 14-day sales forecast and customer segments |
| Bee Tickets, Maserati, Autotorino | none | Template portfolio pages |

Direct checks (each answers with `"ready": true` when the service runs):

- http://127.0.0.1:8080/rag-api/health
- http://127.0.0.1:8080/sentiment-api/health
- http://127.0.0.1:8080/api/module5/health

Sentiment API by hand (the field is `review_text`):

```powershell
Invoke-RestMethod http://127.0.0.1:8080/sentiment-api/predict -Method Post -ContentType "application/json" -Body '{"review_text":"Great work, delivered on time."}'
```

Observed on 2026-10-18: the sentence *"The freelancer delivered late and ignored my messages."* came back
`positive` (0.53). That is the teammate model's own behaviour, worth reporting to its owner.

The Cerebro AI chat uses `llama3.2:3b` in the shared Ollama when it is installed. Otherwise it uses the
first installed model (on this PC `qwen2.5vl:3b`). To match the teammate's setup:

```powershell
ollama pull llama3.2:3b
```
