"""Requirements used by the review, extracted from the project's active agreed documents.

Deterministic first: explicit "REQ-001 (must): ..." and "NN-1 ..." (non-negotiable = must) lines.
No requirements module exists in the platform (docs/AUDIT.md). LLM extraction for documents without
explicit codes is a later step; until then such projects show zero requirements rather than invented ones.
"""

from __future__ import annotations

import re
import sqlite3
import uuid

from ..db import utcnow

REQ = re.compile(r"^\s*[-*]?\s*(REQ-\d{1,4})\s*\((must|should|could)\)\s*[:\-]\s*(.+?)\s*$", re.I)
NN = re.compile(r"^\s*[-*]?\s*(NN-\d{1,3})\s*[:\-]?\s*(.+?)\s*$", re.I)
PRIORITY_ORDER = {"must": 0, "should": 1, "could": 2}


def extract_requirements(conn: sqlite3.Connection, project_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT c.id, c.document_id, c.text FROM chunks c JOIN documents d ON d.id = c.document_id"
        " WHERE c.project_id = ? AND d.status = 'active' ORDER BY d.created_at, c.idx",
        (project_id,),
    ).fetchall()
    found: dict[str, dict] = {}
    for row in rows:
        for line in row["text"].splitlines():
            if m := REQ.match(line):
                code, priority, text = m.group(1).upper(), m.group(2).lower(), m.group(3)
            elif m := NN.match(line):
                code, priority, text = m.group(1).upper(), "must", m.group(2)
            else:
                continue
            found.setdefault(code, {"code": code, "priority": priority, "text": text,
                                    "source_document_id": row["document_id"], "source_chunk_id": row["id"]})
    with conn:
        for req in found.values():
            existing = conn.execute("SELECT edited_by_user FROM requirements WHERE project_id = ? AND code = ?",
                                    (project_id, req["code"])).fetchone()
            if existing and existing["edited_by_user"]:
                continue  # never overwrite a user's edit
            conn.execute(
                "INSERT INTO requirements (id, project_id, code, text, priority, source_document_id, source_chunk_id, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (project_id, code) DO UPDATE SET text = excluded.text,"
                " priority = excluded.priority, source_document_id = excluded.source_document_id, source_chunk_id = excluded.source_chunk_id",
                (f"req-{uuid.uuid4().hex[:12]}", project_id, req["code"], req["text"], req["priority"],
                 req["source_document_id"], req["source_chunk_id"], utcnow()),
            )
    return list_requirements(conn, project_id)


def list_requirements(conn: sqlite3.Connection, project_id: str) -> list[dict]:
    rows = [dict(r) for r in conn.execute("SELECT * FROM requirements WHERE project_id = ?", (project_id,))]
    return sorted(rows, key=lambda r: (PRIORITY_ORDER[r["priority"]], r["code"]))
