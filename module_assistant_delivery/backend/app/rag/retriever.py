"""Project-scoped retrieval. Access is checked by the caller (membership) BEFORE this runs, and every
query is filtered to the project's active documents (spec 8.1, 11)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .embeddings import Embedder
from .vector_store import ChromaChunkStore


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_title: str
    document_version: int
    project_id: str
    heading_path: str
    text: str
    score: float
    page: int | None
    line_start: int
    line_end: int


def retrieve(
    conn: sqlite3.Connection, embedder: Embedder, store: ChromaChunkStore, *, project_id: str, query: str, k: int
) -> list[RetrievedChunk]:
    active = [r["id"] for r in conn.execute(
        "SELECT id FROM documents WHERE project_id = ? AND status = 'active'", (project_id,)
    )]
    hits = store.query(vector=embedder.embed_query(query), project_id=project_id, document_ids=active,
                       embedding_model=embedder.model_name, k=k)
    if not hits:
        return []
    placeholders = ",".join("?" * len(hits))
    rows = {r["id"]: r for r in conn.execute(
        "SELECT c.*, d.title, d.version FROM chunks c JOIN documents d ON d.id = c.document_id"
        f" WHERE c.id IN ({placeholders}) AND c.project_id = ? AND d.status = 'active'",
        [h.chunk_id for h in hits] + [project_id],
    )}
    results = []
    for hit in hits:
        row = rows.get(hit.chunk_id)
        if row is None or hit.project_id != project_id:  # defence in depth: never cross projects
            continue
        results.append(RetrievedChunk(
            chunk_id=row["id"], document_id=row["document_id"], document_title=row["title"], document_version=row["version"],
            project_id=row["project_id"], heading_path=row["heading_path"], text=row["text"], score=hit.score,
            page=row["page"], line_start=row["line_start"], line_end=row["line_end"],
        ))
    return results
