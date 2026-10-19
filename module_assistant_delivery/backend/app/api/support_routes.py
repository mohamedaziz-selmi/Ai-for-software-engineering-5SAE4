"""Chat history, FAQ, support requests and "Explain this finding" (spec 5.1, 5.3). [DEMO] roles."""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..assistant.service import answer_question
from ..db import utcnow
from ..integrations.demo import DemoUser
from ..llm.service import AssistantUnavailable
from .routes import current_user, directory, errors, get_conn, require_member

router = APIRouter(prefix="/api/ai")


def _require_admin(user: DemoUser) -> None:
    if user.role != "admin":
        raise HTTPException(403, detail={"error": "admin_only"})


# ---------------------------------------------------------------- chat history
@router.get("/conversations", responses=errors(401, 403, 404), summary="List my conversations")
def conversations(request: Request, project_id: str, user: DemoUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    require_member(request, user, project_id)
    rows = conn.execute(
        "SELECT c.id, c.created_at, (SELECT text FROM messages m WHERE m.conversation_id = c.id AND m.role = 'user'"
        " ORDER BY m.created_at LIMIT 1) AS first_question, (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS messages"
        " FROM conversations c WHERE c.project_id = ? AND c.user_id = ? ORDER BY c.created_at DESC", (project_id, user.id)).fetchall()
    return {"conversations": [dict(r) for r in rows]}


@router.get("/conversations/{conversation_id}", responses=errors(401, 403, 404), summary="Read a conversation")
def conversation(request: Request, conversation_id: str, user: DemoUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
    if row is None or row["user_id"] != user.id:  # a conversation is private to its author
        raise HTTPException(404, detail={"error": "conversation_not_found"})
    require_member(request, user, row["project_id"])
    messages = []
    for m in conn.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at, rowid", (conversation_id,)):
        item = dict(m)
        for key in ("citations", "retrieval", "verification"):
            item[key] = json.loads(item[key]) if item[key] else None
        messages.append(item)
    return {"conversation": dict(row), "messages": messages}


# ---------------------------------------------------------------- FAQ (plain CRUD, not chat-routed)
class FaqIn(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    answer: str = Field(min_length=1, max_length=4000)
    language: Literal["en", "fr"] = "en"


@router.get("/faq", summary="List the FAQ")
def faq(conn: sqlite3.Connection = Depends(get_conn), language: str | None = None) -> dict:
    query, args = "SELECT * FROM faq_entries", ()
    if language:
        query, args = query + " WHERE language = ?", (language,)
    return {"faq": [dict(r) for r in conn.execute(query + " ORDER BY created_at", args)]}


@router.post("/faq", status_code=201, responses=errors(401, 403), summary="Add an FAQ entry (admin)")
def create_faq(body: FaqIn, user: DemoUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    _require_admin(user)
    entry_id, now = f"faq-{uuid.uuid4().hex[:10]}", utcnow()
    with conn:
        conn.execute("INSERT INTO faq_entries VALUES (?, ?, ?, ?, ?, ?, ?)", (entry_id, body.question, body.answer, body.language, user.id, now, now))
    return {"id": entry_id}


@router.put("/faq/{entry_id}", responses=errors(401, 403, 404), summary="Edit an FAQ entry (admin)")
def update_faq(entry_id: str, body: FaqIn, user: DemoUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    _require_admin(user)
    with conn:
        changed = conn.execute("UPDATE faq_entries SET question = ?, answer = ?, language = ?, updated_at = ? WHERE id = ?",
                               (body.question, body.answer, body.language, utcnow(), entry_id)).rowcount
    if not changed:
        raise HTTPException(404, detail={"error": "faq_not_found"})
    return {"id": entry_id}


@router.delete("/faq/{entry_id}", status_code=204, responses=errors(401, 403, 404), summary="Delete an FAQ entry (admin)")
def delete_faq(entry_id: str, user: DemoUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)) -> None:
    _require_admin(user)
    with conn:
        if not conn.execute("DELETE FROM faq_entries WHERE id = ?", (entry_id,)).rowcount:
            raise HTTPException(404, detail={"error": "faq_not_found"})


# ---------------------------------------------------------------- support requests
class SupportIn(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=3, max_length=5000)
    category: Literal["question", "bug", "account", "other"] = "question"
    project_id: str | None = Field(default=None, max_length=64)


@router.post("/support-requests", status_code=201, responses=errors(401, 403, 404), summary="Send a support request")
def create_support(request: Request, body: SupportIn, user: DemoUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    if body.project_id:
        require_member(request, user, body.project_id)
    request_id, now = f"sup-{uuid.uuid4().hex[:10]}", utcnow()
    with conn:
        conn.execute("INSERT INTO support_requests VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?)",
                     (request_id, body.project_id, user.id, body.subject, body.body, body.category, now, now))
    return {"id": request_id, "status": "open"}


def _support_request(conn: sqlite3.Connection, request_id: str, user: DemoUser) -> sqlite3.Row:
    """The request, if this user may see it: its author or an admin (404 otherwise, so ids are not probed)."""
    row = conn.execute("SELECT * FROM support_requests WHERE id = ?", (request_id,)).fetchone()
    if row is None or (user.role != "admin" and row["user_id"] != user.id):
        raise HTTPException(404, detail={"error": "support_request_not_found"})
    return row


@router.get("/support-requests", responses=errors(401), summary="List support requests")
def list_support(user: DemoUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    query = ("SELECT r.*, (SELECT COUNT(*) FROM support_messages m WHERE m.request_id = r.id) AS replies,"
             " (SELECT MAX(m.created_at) FROM support_messages m WHERE m.request_id = r.id) AS last_reply_at FROM support_requests r")
    if user.role == "admin":
        rows = conn.execute(query + " ORDER BY r.updated_at DESC")
    else:
        rows = conn.execute(query + " WHERE r.user_id = ? ORDER BY r.updated_at DESC", (user.id,))
    return {"support_requests": [dict(r) for r in rows]}


@router.get("/support-requests/{request_id}", responses=errors(401, 404), summary="Read a support request and its thread")
def get_support(request_id: str, user: DemoUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    row = _support_request(conn, request_id, user)
    messages = conn.execute("SELECT * FROM support_messages WHERE request_id = ? ORDER BY created_at, rowid", (request_id,))
    return {"support_request": dict(row), "messages": [dict(m) for m in messages]}


class ReplyIn(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


@router.post("/support-requests/{request_id}/messages", status_code=201, responses=errors(401, 404), summary="Reply to a support request")
def reply_support(request_id: str, body: ReplyIn, user: DemoUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    row = _support_request(conn, request_id, user)
    # An admin's first answer moves an open request to "in progress"; the author writing again reopens a closed one.
    status = row["status"]
    if user.role == "admin" and status == "open":
        status = "in_progress"
    elif user.role != "admin" and status == "closed":
        status = "open"
    message_id, now = f"spm-{uuid.uuid4().hex[:10]}", utcnow()
    with conn:
        conn.execute("INSERT INTO support_messages VALUES (?, ?, ?, ?, ?, ?)",
                     (message_id, request_id, user.id, "admin" if user.role == "admin" else "requester", body.body.strip(), now))
        conn.execute("UPDATE support_requests SET status = ?, updated_at = ? WHERE id = ?", (status, now, request_id))
    return {"id": message_id, "status": status}


class StatusIn(BaseModel):
    status: Literal["open", "in_progress", "closed"]


@router.patch("/support-requests/{request_id}", responses=errors(401, 403, 404), summary="Change a support request's status")
def update_support(request_id: str, body: StatusIn, user: DemoUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    _support_request(conn, request_id, user)
    if user.role != "admin" and body.status == "in_progress":  # the author may close or reopen; triage is the admin's
        raise HTTPException(403, detail={"error": "admin_only"})
    with conn:
        conn.execute("UPDATE support_requests SET status = ?, updated_at = ? WHERE id = ?", (body.status, utcnow(), request_id))
    return {"id": request_id, "status": body.status}


# ---------------------------------------------------------------- explain a finding (same assistant pipeline)
@router.post("/findings/{finding_id}/explain", responses=errors(401, 403, 404, "unavailable"), summary="Explain a finding from the documents")
def explain_finding(request: Request, finding_id: str, user: DemoUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)):
    row = conn.execute(
        "SELECT f.*, q.code, q.text AS requirement_text, q.priority, d.project_id FROM findings f JOIN reviews r ON r.id = f.review_id"
        " JOIN deliverables d ON d.id = r.deliverable_id LEFT JOIN requirements q ON q.id = f.requirement_id WHERE f.id = ?",
        (finding_id,)).fetchone()
    if row is None:
        raise HTTPException(404, detail={"error": "finding_not_found"})
    require_member(request, user, row["project_id"])
    question = (
        f"Explain this delivery review finding using the project documents. Requirement {row['code']} ({row['priority']}): "
        f"{row['requirement_text']} Finding ({row['severity']}) in {row['file_path']} lines {row['line_start']}-{row['line_end']}: "
        f"{row['explanation']} Code evidence: {row['evidence_quote'][:400]} What exactly do the documents require, and what should change?"
    )
    state = request.app.state
    try:
        return answer_question(conn, state.embedder, state.store, state.llm, project_id=row["project_id"], user_id=user.id,
                               question=question, conversation_id=None, top_k=state.settings.top_k)
    except AssistantUnavailable as exc:
        return JSONResponse(status_code=503, content={"error": "assistant_unavailable",
                                                      "message": "The assistant is temporarily unavailable. Please try again in a moment.",
                                                      "attempts": exc.attempts})
