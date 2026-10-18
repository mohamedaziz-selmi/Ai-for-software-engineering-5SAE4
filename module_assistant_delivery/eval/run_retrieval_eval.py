"""Retrieval comparison for embedding models on the dev questions' gold sections (no LLM involved).

Usage (from module_assistant_delivery/):
  .venv\\Scripts\\python.exe eval\\run_retrieval_eval.py intfloat/multilingual-e5-base Qwen/Qwen3-Embedding-0.6B BAAI/bge-m3

Uses the production chunker (token budget measured with each model's tokenizer) and exact cosine
ranking over the project's chunks. Writes eval/results/retrieval_comparison.md.
"""

from __future__ import annotations

import sys
import time

import numpy as np
from common import MODULE_ROOT, RESULTS, load_jsonl

from app.config import load_settings
from app.rag.embeddings import LlamaIndexEmbedder
from app.rag.ingest import embedding_text
from app.rag.loaders import load_chunks

DOC = MODULE_ROOT / "data" / "seed" / "documents" / "PRJ-DEMO-001_cahier_des_charges.md"


def evaluate(model_name: str, questions: list[dict]) -> dict:
    settings = load_settings()
    embedder = LlamaIndexEmbedder(model_name, settings.embedding_device, settings.hf_home)
    t0 = time.perf_counter()
    embedder.load()
    load_s = time.perf_counter() - t0
    _, chunks = load_chunks(DOC.name, DOC.read_bytes(), count=embedder.count_tokens)
    t0 = time.perf_counter()
    matrix = embedder.embed_passages([embedding_text(c.heading_path, c.text) for c in chunks])
    index_s = time.perf_counter() - t0
    hits1 = hits3 = hits5 = 0
    rr = 0.0
    q_times = []
    for q in questions:
        t0 = time.perf_counter()
        scores = matrix @ embedder.embed_query(q["question"])
        q_times.append(time.perf_counter() - t0)
        ranked = [chunks[i].heading_path for i in np.argsort(-scores)]
        rank = next((i + 1 for i, path in enumerate(ranked) if q["gold_section"] in path), None)
        if rank:
            hits1 += rank <= 1
            hits3 += rank <= 3
            hits5 += rank <= 5
            rr += 1 / rank
    n = len(questions)
    return {"model": model_name, "chunks": len(chunks), "hit@1": hits1 / n, "hit@3": hits3 / n, "hit@5": hits5 / n,
            "mrr": rr / n, "load_s": load_s, "index_s": index_s, "query_ms_mean": 1000 * sum(q_times) / n}


def main() -> None:
    questions = [q for q in load_jsonl(MODULE_ROOT / "eval" / "datasets" / "assistant_dev.jsonl") if q.get("gold_section")]
    results = [evaluate(m, questions) for m in sys.argv[1:]]
    lines = ["# Retrieval comparison (dev set)", "",
             f"{len(questions)} answerable questions (EN + FR) over `{DOC.name}`; gold = the section that answers the question.",
             "Small single-document set: differences of one or two questions are not significant.", "",
             "| Model | Chunks | hit@1 | hit@3 | hit@5 | MRR | load s | index s | query ms (CPU) |", "|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| `{r['model']}` | {r['chunks']} | {r['hit@1']:.2f} | {r['hit@3']:.2f} | {r['hit@5']:.2f} | {r['mrr']:.3f} | "
                     f"{r['load_s']:.1f} | {r['index_s']:.1f} | {r['query_ms_mean']:.0f} |")
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "retrieval_comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
