"""Builds the prompts of the hand-written validation set used to choose between RAFT run 2 candidates.

Service venv. For each question of raft/data/handwritten_val/questions.jsonl, retrieves the top-k chunks of its
document like the runtime retriever (e5 query embedding, cosine similarity, labels C1..Ck in rank order), renders
the runtime prompt and masks it with the runtime Masker. These documents are not in any training split and are
not the final test set (eval/datasets/assistant_dev.jsonl).

  .venv\\Scripts\\python.exe raft\\build_val_prompts.py      ->  raft/data/handwritten_val/prompts.jsonl
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_ROOT / "backend"))

from app.config import load_settings  # noqa: E402
from app.llm.masking import Masker  # noqa: E402
from app.llm.prompts import ContextChunk, render_assistant_messages  # noqa: E402
from app.rag.chunking import Page, chunk_pages  # noqa: E402
from app.rag.embeddings import LlamaIndexEmbedder  # noqa: E402
from app.rag.ingest import embedding_text  # noqa: E402

VAL = MODULE_ROOT / "raft" / "data" / "handwritten_val"


def main() -> None:
    settings = load_settings()
    embedder = LlamaIndexEmbedder(settings.embedding_model, settings.embedding_device, settings.hf_home)
    docs = {}
    for path in sorted(VAL.glob("VAL-*.md")):
        markdown = path.read_text(encoding="utf-8")
        chunks = chunk_pages([Page(markdown)], markdown=True, count=embedder.count_tokens)
        vectors = embedder.embed_passages([embedding_text(c.heading_path, c.text) for c in chunks])
        docs[path.stem] = (markdown.splitlines()[0].lstrip("# ").strip(), chunks, vectors)
    rows = []
    for line in (VAL / "questions.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        q = json.loads(line)
        title, chunks, vectors = docs[q["doc"]]
        order = list(np.argsort(-(vectors @ embedder.embed_query(q["question"]))))[: settings.top_k]
        context = [ContextChunk(f"C{n + 1}", title, chunks[i].heading_path, chunks[i].text) for n, i in enumerate(order)]
        masker = Masker()
        messages = [{"role": m["role"], "content": masker.mask(m["content"])} for m in render_assistant_messages(context, q["question"])]
        rows.append({**q, "messages": messages, "chunks": {f"C{n + 1}": masker.mask(chunks[i].text) for n, i in enumerate(order)}})
    out = VAL / "prompts.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"{len(rows)} prompts -> {out.relative_to(MODULE_ROOT)}")


if __name__ == "__main__":
    main()
