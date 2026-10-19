"""Delivery review endpoints under /api/ai. Membership is checked on every call; only the project's
freelancer submits deliverables and only the project's client decides on findings ([DEMO] roles)."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from ..db import connect, utcnow
from ..integrations.demo import DemoUser
from ..llm.prompts import REVIEW_PROMPT_VERSION
from ..review.files import RejectedUpload, validate_files
from ..review.pipeline import run_review
from ..review.requirements import extract_requirements, list_requirements
from .routes import current_user, directory, errors, get_conn, require_member

router = APIRouter(prefix="/api/ai")
_gpu_lock = threading.Lock()  # one review at a time on the single local GPU


def _require_role(request: Request, user: DemoUser, project_id: str, role: str) -> None:
    if require_member(request, user, project_id) != role:
        raise HTTPException(403, detail={"error": f"only_the_project_{role}"})


@router.get("/requirements", responses=errors(401, 403, 404), summary="List the project's requirements")
def requirements(request: Request, project_id: str, user: DemoUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    require_member(request, user, project_id)
    return {"project_id": project_id, "requirements": list_requirements(conn, project_id)}


@router.post("/requirements/extract", responses=errors(401, 403, 404), summary="Extract requirements from the documents")
def extract(request: Request, project_id: str, user: DemoUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    require_member(request, user, project_id)
    reqs = extract_requirements(conn, project_id)
    return {"project_id": project_id, "requirements": reqs, "method": "explicit REQ-/NN- codes in the active documents"}


class RequirementIn(BaseModel):
    text: str = Field(min_length=3, max_length=2000)
    priority: Literal["must", "should", "could"]


@router.put("/requirements/{requirement_id}", responses=errors(401, 403, 404), summary="Edit a requirement")
def edit_requirement(request: Request, requirement_id: str, body: RequirementIn, user: DemoUser = Depends(current_user),
                     conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    """A project member corrects an extracted requirement; re-extraction never overwrites it (edited_by_user)."""
    row = conn.execute("SELECT project_id FROM requirements WHERE id = ?", (requirement_id,)).fetchone()
    if row is None:
        raise HTTPException(404, detail={"error": "requirement_not_found"})
    require_member(request, user, row["project_id"])
    with conn:
        conn.execute("UPDATE requirements SET text = ?, priority = ?, edited_by_user = 1 WHERE id = ?",
                     (body.text.strip(), body.priority, requirement_id))
    return dict(conn.execute("SELECT * FROM requirements WHERE id = ?", (requirement_id,)).fetchone())


@router.post("/deliverables", status_code=201, responses=errors(401, 403, 404), summary="Submit a deliverable (freelancer)")
async def submit_deliverable(
    request: Request,
    project_id: str = Form(...),
    milestone_id: str = Form(...),
    note: str = Form(default=""),
    files: list[UploadFile] = File(...),
    user: DemoUser = Depends(current_user),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    _require_role(request, user, project_id, "freelancer")
    project = directory(request).get_project(project_id)
    if milestone_id not in {m[0] for m in project.milestones}:
        raise HTTPException(422, detail={"error": "unknown_milestone"})
    try:
        validated = validate_files([(f.filename or "", await f.read(200_001)) for f in files])
    except RejectedUpload as exc:
        raise HTTPException(422, detail={"error": "rejected_upload", "message": str(exc)}) from exc
    version = conn.execute("SELECT COALESCE(MAX(version), 0) + 1 FROM deliverables WHERE project_id = ? AND milestone_id = ?",
                           (project_id, milestone_id)).fetchone()[0]
    deliverable_id = f"dlv-{uuid.uuid4().hex[:12]}"
    with conn:
        conn.execute("INSERT INTO deliverables (id, project_id, milestone_id, version, submitted_by, submitted_at, note) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (deliverable_id, project_id, milestone_id, version, user.id, utcnow(), note[:1000]))
        conn.executemany("INSERT INTO deliverable_files (id, deliverable_id, path, kind, size, sha256, content_text) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         [(f"dfl-{uuid.uuid4().hex[:12]}", deliverable_id, f.path, f.kind, f.size, f.sha256, f.text) for f in validated])
    return {"deliverable_id": deliverable_id, "version": version, "files": [f.path for f in validated]}


@router.get("/deliverables", responses=errors(401, 403, 404), summary="List deliverables")
def deliverables(request: Request, project_id: str, user: DemoUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    require_member(request, user, project_id)
    rows = conn.execute(
        "SELECT d.*, (SELECT COUNT(*) FROM deliverable_files f WHERE f.deliverable_id = d.id) AS file_count,"
        " (SELECT r.id FROM reviews r WHERE r.deliverable_id = d.id ORDER BY r.started_at DESC LIMIT 1) AS latest_review_id"
        " FROM deliverables d WHERE d.project_id = ? ORDER BY d.milestone_id, d.version DESC", (project_id,)).fetchall()
    return {"project_id": project_id, "deliverables": [dict(r) for r in rows]}


def _deliverable_project(conn: sqlite3.Connection, deliverable_id: str) -> str:
    row = conn.execute("SELECT project_id FROM deliverables WHERE id = ?", (deliverable_id,)).fetchone()
    if row is None:
        raise HTTPException(404, detail={"error": "deliverable_not_found"})
    return row["project_id"]


@router.post("/deliverables/{deliverable_id}/review", status_code=202, responses=errors(401, 403, 404, 503), summary="Start a delivery review")
def start_review(request: Request, deliverable_id: str, user: DemoUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    project_id = _deliverable_project(conn, deliverable_id)
    require_member(request, user, project_id)
    if request.app.state.llm.review is None:
        raise HTTPException(503, detail={"error": "review_unavailable", "message":
                            "The review model is not configured: set HOSTED_API_KEY in module_assistant_delivery/.env. "
                            "The assistant keeps working."})
    if not list_requirements(conn, project_id):
        extract_requirements(conn, project_id)
    review_id = f"rev-{uuid.uuid4().hex[:12]}"
    with conn:
        conn.execute("INSERT INTO reviews (id, deliverable_id, status, prompt_version) VALUES (?, ?, 'pending', ?)",
                     (review_id, deliverable_id, REVIEW_PROMPT_VERSION))
    state = request.app.state

    def work() -> None:
        with _gpu_lock:
            worker_conn = connect(state.settings.database_path)
            try:
                run_review(worker_conn, state.embedder, state.llm, review_id)
            except Exception:
                pass  # status 'failed' and the error type are stored on the review
            finally:
                worker_conn.close()

    if getattr(state, "run_reviews_inline", False):
        work()
    else:
        threading.Thread(target=work, daemon=True).start()
    return {"review_id": review_id, "status": "pending"}


@router.get("/reviews/{review_id}", responses=errors(401, 403, 404), summary="Read a delivery review")
def get_review(request: Request, review_id: str, user: DemoUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    review = conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
    if review is None:
        raise HTTPException(404, detail={"error": "review_not_found"})
    require_member(request, user, _deliverable_project(conn, review["deliverable_id"]))
    results = conn.execute(
        "SELECT q.code, q.priority, q.text, rr.* FROM requirement_results rr JOIN requirements q ON q.id = rr.requirement_id"
        " WHERE rr.review_id = ? ORDER BY CASE q.priority WHEN 'must' THEN 0 WHEN 'should' THEN 1 ELSE 2 END,"
        " q.code", (review_id,)).fetchall()
    findings = conn.execute(
        "SELECT f.*, q.code AS requirement_code, q.priority AS requirement_priority FROM findings f"
        " LEFT JOIN requirements q ON q.id = f.requirement_id WHERE f.review_id = ?"
        " ORDER BY CASE f.severity WHEN 'blocker' THEN 0 WHEN 'major' THEN 1 WHEN 'minor' THEN 2 ELSE 3 END, q.code", (review_id,)).fetchall()
    data = dict(review)
    data["summary"] = json.loads(review["summary"]) if review["summary"] else None
    data["requirement_results"] = [dict(r) for r in results]
    data["findings"] = [dict(f) for f in findings]
    # Live progress for the UI while the review runs (requirements are judged one by one).
    total = data["summary"]["requirements"] if data["summary"] else len(list_requirements(conn, _deliverable_project(conn, review["deliverable_id"])))
    data["progress"] = {"done": len(results), "total": total}
    data["advisory_notice"] = "Findings are advisory. The client decides whether to accept the delivery."
    return data


class DeliveryDecision(BaseModel):
    decision: Literal["accepted", "changes_requested", "pending"]
    comment: str = Field(default="", max_length=2000)


@router.patch("/deliverables/{deliverable_id}/decision", responses=errors(401, 403, 404), summary="Accept a delivery or request changes (client)")
def decide_delivery(request: Request, deliverable_id: str, body: DeliveryDecision, user: DemoUser = Depends(current_user),
                    conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    """The client accepts the delivery or requests changes; the review only advises."""
    project_id = _deliverable_project(conn, deliverable_id)
    _require_role(request, user, project_id, "client")
    with conn:
        conn.execute("UPDATE deliverables SET client_decision = ?, client_comment = ?, decided_by = ?, decided_at = ? WHERE id = ?",
                     (body.decision, body.comment.strip(), user.id, utcnow(), deliverable_id))
    return {"id": deliverable_id, "client_decision": body.decision}


class Decision(BaseModel):
    client_decision: Literal["accepted", "dismissed", "pending"]
    client_comment: str = Field(default="", max_length=2000)


@router.patch("/findings/{finding_id}", responses=errors(401, 403, 404), summary="Accept or dismiss a finding (client)")
def decide(request: Request, finding_id: str, body: Decision, user: DemoUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    row = conn.execute("SELECT f.id, d.project_id FROM findings f JOIN reviews r ON r.id = f.review_id"
                       " JOIN deliverables d ON d.id = r.deliverable_id WHERE f.id = ?", (finding_id,)).fetchone()
    if row is None:
        raise HTTPException(404, detail={"error": "finding_not_found"})
    _require_role(request, user, row["project_id"], "client")
    with conn:
        conn.execute("UPDATE findings SET client_decision = ?, client_comment = ?, decided_by = ?, decided_at = ? WHERE id = ?",
                     (body.client_decision, body.client_comment, user.id, utcnow(), finding_id))
    return {"id": finding_id, "client_decision": body.client_decision}
