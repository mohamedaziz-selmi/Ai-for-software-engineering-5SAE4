"""REST endpoints under /api/ai (gateway routes /api/ai/* here with the path preserved)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import PurePath
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from ..assistant.service import answer_question
from ..db import connect
from ..integrations.demo import DEMO_NOTICE, DemoDirectory, DemoUser
from ..llm.service import AssistantUnavailable
from ..rag.ingest import ingest_document
from ..rag.loaders import SUPPORTED, UnsupportedDocument

router = APIRouter(prefix="/api/ai")

MAX_UPLOAD_BYTES = 5_000_000
DOC_TYPES = {"cahier_des_charges", "contract", "spec", "faq", "other"}


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="allow")
    error: str
    message: str | None = None


class ErrorBody(BaseModel):
    detail: ErrorDetail


class UnavailableBody(BaseModel):
    error: str
    message: str
    attempts: list[dict]


ERROR_DOCS = {
    401: "No demo identity: send X-Demo-User (a demo identity, not authentication).",
    403: "Not a member of this project, or not the role this action needs.",
    404: "The project or the item does not exist (or is not yours).",
    413: "The file is larger than 5 MB.",
    415: "This file type is not supported; the message lists what is.",
    503: "The review model is not configured (no HOSTED_API_KEY). The assistant keeps working.",
}


def errors(*codes: int | str) -> dict:
    """OpenAPI entries for the refusals a route returns, so Swagger documents each one ("unavailable": every model failed)."""
    docs = {code: {"model": ErrorBody, "description": ERROR_DOCS[code]} for code in codes if code != "unavailable"}
    if "unavailable" in codes:
        docs[503] = {"model": UnavailableBody, "description": "Every model in the chain failed; the attempts are listed."}
    return docs


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    conn = connect(request.app.state.settings.database_path)
    try:
        yield conn
    finally:
        conn.close()


def directory(request: Request) -> DemoDirectory:
    return request.app.state.directory


def current_user(request: Request, x_demo_user: str | None = Header(default=None)) -> DemoUser:
    user = directory(request).get_user(x_demo_user)
    if user is None:
        raise HTTPException(401, detail={"error": "demo_identity_required", "message": f"Choose a demo identity. {DEMO_NOTICE}"})
    return user


def require_member(request: Request, user: DemoUser, project_id: str) -> str:
    if directory(request).get_project(project_id) is None:
        raise HTTPException(404, detail={"error": "project_not_found", "message": "This project does not exist."})
    role = directory(request).project_role(user.id, project_id)
    if role is None:
        raise HTTPException(403, detail={"error": "not_a_project_member", "message": "You are not a member of this project."})
    return role


def _review_health(llm, local_status: str) -> dict:
    if llm.review_served_by == "local":
        return {"status": "up" if local_status == "up" else "down", "provider": "local", "model": llm.review.model,
                "note": "REVIEW_PROVIDER=local (explicit offline option)."}
    if llm.review is None:
        return {"status": "degraded", "provider": "hosted", "model": None,
                "note": "HOSTED_API_KEY is not set in module_assistant_delivery/.env: reviews are unavailable; the assistant keeps working."}
    return {"status": "configured", "provider": "hosted", "model": llm.review.model,
            "note": "Key present; the hosted API is not called by health checks (quota)."}


@router.get("/health", summary="Health of the module and its models")
def health(request: Request) -> dict:
    state = request.app.state
    settings = state.settings
    local = state.llm.local.probe()
    embed_status = state.embedder.status()
    try:
        with connect(settings.database_path) as conn:
            counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("documents", "chunks", "messages")}
        database = {"status": "up", "engine": "sqlite", **counts, "vector_store": "chroma", "vectors": state.store.count()}
    except Exception as exc:  # sqlite or chroma
        database = {"status": "down", "error": type(exc).__name__}
    backup = state.llm.backup_status
    healthy = local == "up" and embed_status in {"loaded", "not_loaded", "loading"} and database["status"] == "up"
    return {
        "service": "assistant-delivery",
        "ready": healthy,  # same flag as the other platform services' /health
        "status": "ok" if healthy else "degraded",
        "assistant": {
            "local": local, "model": settings.assistant_model, "endpoint": settings.assistant_base_url,
            # Selectable models (one runs at a time): status "up" = installed in the private Ollama
            "models": {name: {"tag": client.model, "status": local if name == "base" else client.probe()}
                       for name, client in state.llm.local_models.items()},
            "default": "base",
        },
        "backup": {
            "status": backup,
            "model": settings.backup_model if backup == "configured" else None,
            "note": "Configured means a key is set; the hosted API is not called by health checks." if backup == "configured" else None,
        },
        "review": _review_health(state.llm, local),
        "embeddings": {"status": embed_status, "model": state.embedder.model_name, "error": getattr(state.embedder, "error", None)},
        "database": database,
        "identity": {"mode": state.directory.mode, "authentication": state.directory.authentication, "notice": DEMO_NOTICE},
    }


@router.get("/demo/identities", summary="Demo identities (not authentication)")
def demo_identities(request: Request) -> dict:
    return {
        "authentication": False,
        "notice": DEMO_NOTICE,
        "identities": [{"id": u.id, "display_name": u.display_name, "role": u.role} for u in directory(request).users()],
    }


@router.get("/projects", responses=errors(401), summary="Projects of the demo identity")
def projects(request: Request, user: DemoUser = Depends(current_user)) -> dict:
    return {
        "identity_mode": "demo",
        "projects": [{"id": p.id, "name": p.name, "my_role": p.members[user.id],
                      "milestones": [{"id": m[0], "name": m[1]} for m in p.milestones]} for p in directory(request).projects_for(user.id)],
    }


@router.get("/documents", responses=errors(401, 403, 404), summary="List a project's documents")
def list_documents(request: Request, project_id: str, user: DemoUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    require_member(request, user, project_id)
    rows = conn.execute(
        "SELECT d.id, d.title, d.doc_type, d.file_kind, d.source_name, d.version, d.status, d.created_at,"
        " (SELECT COUNT(*) FROM chunks c WHERE c.document_id = d.id) AS chunk_count"
        " FROM documents d WHERE d.project_id = ? ORDER BY d.source_name, d.version DESC",
        (project_id,),
    ).fetchall()
    return {"project_id": project_id, "documents": [dict(r) for r in rows]}


@router.post("/documents", status_code=201, responses=errors(401, 403, 404, 413, 415), summary="Upload a project document (MD, TXT, PDF, DOCX)")
async def upload_document(
    request: Request,
    project_id: str = Form(...),
    title: str = Form(default=""),
    doc_type: str = Form(default="other"),
    file: UploadFile = File(...),
    user: DemoUser = Depends(current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    require_member(request, user, project_id)
    name = PurePath(file.filename or "").name
    suffix = PurePath(name).suffix.lower()
    if suffix not in SUPPORTED:
        raise HTTPException(415, detail={"error": "unsupported_type",
                                         "message": f"{suffix or 'This'} files are not supported. Upload a PDF, DOCX, Markdown or text file.",
                                         "allowed": sorted(SUPPORTED)})
    if doc_type not in DOC_TYPES:
        raise HTTPException(422, detail={"error": "invalid_doc_type", "message": "Unknown document type.", "allowed": sorted(DOC_TYPES)})
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, detail={"error": "file_too_large", "message": f"The file is larger than {MAX_UPLOAD_BYTES // 1_000_000} MB.",
                                         "limit_bytes": MAX_UPLOAD_BYTES})
    try:
        result = ingest_document(
            conn, request.app.state.embedder, request.app.state.store, project_id=project_id,
            title=title.strip() or name, doc_type=doc_type, source_name=name, raw=raw, uploaded_by=user.id,
        )
    except UnsupportedDocument as exc:
        raise HTTPException(422, detail={"error": "unsupported_content", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(422, detail={"error": "empty_document", "message": str(exc)}) from exc
    return {"project_id": project_id, **result}


@router.delete("/documents/{document_id}", responses=errors(401, 403, 404), summary="Remove a document (its previous version becomes active)")
def delete_document(request: Request, document_id: str, user: DemoUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    """Remove a wrong upload: its passages leave SQLite and Chroma at once, so the assistant stops answering from it.
    If an older version of the same file exists, the newest one becomes active again."""
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
    if row is None:
        raise HTTPException(404, detail={"error": "document_not_found"})
    require_member(request, user, row["project_id"])
    request.app.state.store.delete_document(document_id)
    restored = None
    with conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))  # chunks cascade
        if row["status"] == "active":
            previous = conn.execute(
                "SELECT id, version FROM documents WHERE project_id = ? AND source_name = ? AND status = 'superseded'"
                " ORDER BY version DESC LIMIT 1", (row["project_id"], row["source_name"])).fetchone()
            if previous:
                conn.execute("UPDATE documents SET status = 'active' WHERE id = ?", (previous["id"],))
                restored = {"id": previous["id"], "version": previous["version"]}
    return {"deleted": document_id, "restored": restored}


class ChatRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=2, max_length=2000)
    conversation_id: str | None = Field(default=None, max_length=64)
    model: Literal["base", "raft"] = "base"  # base model + RAG (default) or the RAFT fine-tuned model
    simulate_failure: bool = False  # demo failure drill: skip the chosen model to show the backup chain


@router.post("/chat", responses=errors(401, 403, 404, "unavailable"), summary="Ask the project assistant")
def chat(request: Request, body: ChatRequest, user: DemoUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)):
    require_member(request, user, body.project_id)
    state = request.app.state
    try:
        return answer_question(
            conn, state.embedder, state.store, state.llm, project_id=body.project_id, user_id=user.id,
            question=body.message, conversation_id=body.conversation_id, top_k=state.settings.top_k,
            model=body.model, simulate_failure=body.simulate_failure,
        )
    except AssistantUnavailable as exc:
        return JSONResponse(status_code=503, content={
            "error": "assistant_unavailable",
            "message": "The assistant is temporarily unavailable. Please try again in a moment.",
            "attempts": exc.attempts,
        })
