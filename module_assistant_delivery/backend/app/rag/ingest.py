"""Document ingestion: load -> chunk (clause-preserving) -> embed -> store.

SQLite keeps documents, versions, chunk text and provenance; Chroma keeps the vectors.
A new upload of the same source name creates a new version; retrieval uses the active version only.
"""

from __future__ import annotations

import hashlib
import sqlite3
import uuid

from ..db import utcnow
from .embeddings import Embedder
from .loaders import load_chunks
from .vector_store import ChromaChunkStore


def embedding_text(heading_path: str, text: str) -> str:
    return f"{heading_path}\n{text}"


def ingest_document(
    conn: sqlite3.Connection,
    embedder: Embedder,
    store: ChromaChunkStore,
    *,
    project_id: str,
    title: str,
    doc_type: str,
    source_name: str,
    raw: bytes,
    uploaded_by: str,
    language: str | None = None,
) -> dict:
    digest = hashlib.sha256(raw).hexdigest()
    current = conn.execute(
        "SELECT id, version, content_sha256 FROM documents WHERE project_id = ? AND source_name = ? AND status = 'active'",
        (project_id, source_name),
    ).fetchone()
    if current and current["content_sha256"] == digest:
        count = conn.execute("SELECT COUNT(*) FROM chunks WHERE document_id = ?", (current["id"],)).fetchone()[0]
        return {"document_id": current["id"], "version": current["version"], "chunks": count, "unchanged": True}

    kind, chunks = load_chunks(source_name, raw, count=embedder.count_tokens)
    if not chunks:
        raise ValueError("The document contains no text to index.")
    texts = [embedding_text(c.heading_path, c.text) for c in chunks]
    vectors = embedder.embed_passages(texts)

    version = (current["version"] + 1) if current else 1
    document_id = f"doc-{uuid.uuid4().hex[:12]}"
    chunk_ids = [f"{document_id}-c{c.idx:03d}" for c in chunks]
    store.add(document_id=document_id, project_id=project_id, embedding_model=embedder.model_name,
              rows=list(zip(chunk_ids, texts, vectors)))
    try:
        with conn:
            if current:
                conn.execute("UPDATE documents SET status = 'superseded' WHERE id = ?", (current["id"],))
            conn.execute(
                "INSERT INTO documents (id, project_id, title, doc_type, file_kind, source_name, version, language,"
                " uploaded_by, status, content_sha256, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)",
                (document_id, project_id, title, doc_type, kind, source_name, version, language, uploaded_by, digest, utcnow()),
            )
            conn.executemany(
                "INSERT INTO chunks (id, document_id, project_id, idx, heading_path, text, page, line_start, line_end,"
                " embedding_model) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(cid, document_id, project_id, c.idx, c.heading_path, c.text, c.page, c.line_start, c.line_end,
                  embedder.model_name) for cid, c in zip(chunk_ids, chunks)],
            )
    except sqlite3.Error:
        store.delete_document(document_id)  # keep the two stores consistent
        raise
    return {"document_id": document_id, "version": version, "chunks": len(chunks), "kind": kind, "unchanged": False}
