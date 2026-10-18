"""Module-owned SQLite storage (storage/assistant.sqlite3). No shared database exists (docs/AUDIT.md)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    file_kind TEXT NOT NULL,
    source_name TEXT NOT NULL,
    version INTEGER NOT NULL,
    language TEXT,
    uploaded_by TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'superseded')),
    content_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_documents_project ON documents(project_id, source_name);

-- Chunk text + provenance. Vectors live in the module's Chroma collection under the same chunk id.
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    heading_path TEXT NOT NULL,
    text TEXT NOT NULL,
    page INTEGER,
    line_start INTEGER NOT NULL,
    line_end INTEGER NOT NULL,
    embedding_model TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_chunks_project ON chunks(project_id);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    text TEXT NOT NULL,
    citations TEXT,
    grounded INTEGER,
    status TEXT,
    scope_verdict TEXT,
    served_by TEXT,
    model TEXT,
    prompt_version TEXT,
    retrieval TEXT,
    verification TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS requirements (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    code TEXT NOT NULL,
    text TEXT NOT NULL,
    priority TEXT NOT NULL CHECK (priority IN ('must', 'should', 'could')),
    source_document_id TEXT,
    source_chunk_id TEXT,
    edited_by_user INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    UNIQUE (project_id, code)
);

CREATE TABLE IF NOT EXISTS deliverables (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    milestone_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    submitted_by TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    note TEXT
);

CREATE TABLE IF NOT EXISTS deliverable_files (
    id TEXT PRIMARY KEY,
    deliverable_id TEXT NOT NULL REFERENCES deliverables(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    kind TEXT NOT NULL,
    size INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    content_text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    deliverable_id TEXT NOT NULL REFERENCES deliverables(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'done', 'failed')),
    model TEXT,
    served_by TEXT,
    prompt_version TEXT NOT NULL,
    summary TEXT,
    error TEXT,
    started_at TEXT,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS requirement_results (
    review_id TEXT NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    requirement_id TEXT NOT NULL REFERENCES requirements(id),
    status TEXT NOT NULL CHECK (status IN ('ok', 'review_failed')),
    model_verdict TEXT,
    verdict TEXT,
    note TEXT,
    excerpts TEXT,
    dropped TEXT,
    PRIMARY KEY (review_id, requirement_id)
);

CREATE TABLE IF NOT EXISTS findings (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    requirement_id TEXT REFERENCES requirements(id),
    file_path TEXT,
    line_start INTEGER,
    line_end INTEGER,
    severity TEXT NOT NULL CHECK (severity IN ('info', 'minor', 'major', 'blocker')),
    explanation TEXT NOT NULL,
    suggested_fix TEXT,
    evidence_quote TEXT NOT NULL,
    confidence REAL,
    client_decision TEXT NOT NULL DEFAULT 'pending' CHECK (client_decision IN ('pending', 'accepted', 'dismissed')),
    client_comment TEXT,
    decided_by TEXT,
    decided_at TEXT
);

CREATE TABLE IF NOT EXISTS faq_entries (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    language TEXT NOT NULL CHECK (language IN ('en', 'fr')),
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS support_requests (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    user_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('question', 'bug', 'account', 'other')),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'closed')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Metadata only: never prompt or response text (spec 8.4).
CREATE TABLE IF NOT EXISTS llm_call_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature TEXT NOT NULL,
    served_by TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_version TEXT,
    latency_ms INTEGER,
    tokens_in INTEGER,
    tokens_out INTEGER,
    status TEXT NOT NULL,
    error_type TEXT,
    created_at TEXT NOT NULL
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    # One connection per request; FastAPI may open it in a worker thread and use it in the event loop.
    conn = sqlite3.connect(path, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


MIGRATIONS = {("requirement_results", "dropped"): "ALTER TABLE requirement_results ADD COLUMN dropped TEXT"}


def init_db(path: Path) -> None:
    with connect(path) as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        for (table, column), statement in MIGRATIONS.items():
            if column not in {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}:
                conn.execute(statement)


def log_llm_call(
    conn: sqlite3.Connection,
    *,
    feature: str,
    served_by: str,
    model: str,
    prompt_version: str | None,
    latency_ms: int,
    status: str,
    error_type: str | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
) -> None:
    conn.execute(
        "INSERT INTO llm_call_log (feature, served_by, model, prompt_version, latency_ms, tokens_in,"
        " tokens_out, status, error_type, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (feature, served_by, model, prompt_version, latency_ms, tokens_in, tokens_out, status, error_type, utcnow()),
    )
