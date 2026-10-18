# Cerebro semantic RAG baseline

This service indexes the complete 30-PDF knowledge base into a persistent Chroma database and exposes semantic-vector search for the proposal-review product. It reads the flat `../rag/pdfs` folder and the missing category PDFs under `../rag/cerebro_rag_full_30/`, then de-duplicates identical filenames.

The current retriever is hybrid: Chroma semantic-vector search plus BM25 lexical search fused with Reciprocal Rank Fusion (RRF). It has no reranker, LLM answer generation, or evaluation scoring.

## Setup

Use Python 3.11 or newer. From this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python ingest.py --reset
uvicorn api:app --reload --port 8000
```

The first ingestion downloads `all-MiniLM-L6-v2`, the local embedding model used consistently for indexing and queries. The database is stored in `chroma_db/` and is excluded from version control.

## Test the baseline

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/search -ContentType 'application/json' -Body '{"query":"What is the hard budget limit and deadline type for JOB-003?","limit":5}'
```

Use `../rag/cerebro_rag_full_30/synthetic_dataset/retrieval_test_questions.csv` as the evaluation set. Compare its Recall@K, MRR, and nDCG@K against the saved semantic-only baseline report.

## Metadata returned with every result

- PDF file and PDF id
- PDF category
- Page number
- Source/entity ids found on the source page

This metadata is designed to support evidence citations in the later proposal-evaluation UI.
