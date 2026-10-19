# Historical Phase 1 README — superseded by the root README

Standalone university mini-project module for the Cerebro freelance marketplace. The implementation follows the fixed stack in the project brief: React/Vite, Spring Boot 3/Java 21/PostgreSQL, and FastAPI/Python 3.11. AI is exposed only through the back-end API; the Spring service never forwards raw personal data to the LLM.

## Quick start

1. Activate `.venv-phase2` and verify Ollama has `gemma3:4b`.
2. Start the new local microservice topology:

```powershell
& .venv-phase2\Scripts\Activate.ps1
& .\start-cerebro.ps1
& .\check-services.ps1
```

3. Open `http://127.0.0.1:8905/`. Gateway Swagger is at `http://127.0.0.1:8900/docs`.

The legacy application on port 8000 remains available for backward compatibility. Docker files exist for future deployment, but Docker was not installed or tested.

Local development commands and the report/demo material are in [`docs/README.md`](docs/README.md).

## Research guarantees

- No RAG, vector database, embeddings retrieval, or document retrieval is used.
- Listing, demand, and transaction data are synthetic and generated with fixed seeds.
- Classical ML reports baseline and final model metrics on held-out test sets.
- LLM output is schema-validated, retried once, and replaced by a deterministic fallback when unavailable or invalid.
- Profile checking is advisory only and synthetic profiles are used for tests.

## Current implementation phases

- Phase 1: repository audit, architecture plan, hardware telemetry, and ResourceGuard.
- Phase 2: isolated environment, guarded Kaggle/Hugging Face download tooling, smoke samples, schema validation, SHA-256 provenance, and Phase 2 tests. See [`PHASE2.md`](PHASE2.md).

Full dataset downloads, model training, fine-tuning, and RAG indexing remain gated by explicit authorization and dataset credentials.
