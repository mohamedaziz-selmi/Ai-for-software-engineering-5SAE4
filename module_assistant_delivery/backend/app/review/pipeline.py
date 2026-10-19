"""Delivery review pipeline (spec 8.3): per requirement, retrieve deliverable excerpts, judge with the
review model, verify evidence in code, aggregate. Findings are advisory; the client decides.

Rules enforced in code, not trusted to the model:
- evidence_quote must occur in the named file within the stated lines (+/- 3); otherwise the finding is dropped;
- conforms/partial/violates need at least one verified finding, else the verdict becomes cannot_determine
  (retrieved excerpts are a subset: not seeing something is not proof that it is absent);
- "blocker" is only allowed for MUST requirements (downgraded to "major" otherwise).
"""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from collections import Counter

import numpy as np

from ..assistant.verify import normalize, quote_in_text
from ..db import utcnow
from ..llm.prompts import REVIEW_PROMPT_VERSION, Excerpt, render_review_messages
from ..llm.schemas import REVIEW_JUDGEMENT_JSON_SCHEMA, ReviewJudgement
from ..llm.service import AssistantUnavailable, LlmService, ReviewNotConfigured
from ..rag.chunking import Page, chunk_code, chunk_pages
from ..rag.embeddings import Embedder
from .requirements import list_requirements

TOP_K = 4
LINE_SLACK = 3
LINE_PREFIX = re.compile(r"^\s*\d+\|\s?", re.M)  # the model may copy the line-number gutter
CODE_FENCE = re.compile(r"^\s*```[\w+-]*\s*$", re.M)  # ... or wrap the quote in a Markdown code fence
GUTTER_LINE = re.compile(r"^\s*(\d+)\|\s?(.*)$")


def _excerpt_chunks(files: list[sqlite3.Row], embedder: Embedder):
    chunks = []
    for f in files:
        if f["kind"] == "code":
            parts = chunk_code(f["content_text"], f["path"])
        else:
            parts = chunk_pages([Page(f["content_text"])], markdown=f["kind"] == "markdown", count=embedder.count_tokens)
        for c in parts:
            lines = f["content_text"].split("\n")[c.line_start - 1 : c.line_end]
            chunks.append((f["path"], c.line_start, "\n".join(lines), f"{f['path']}\n{c.heading_path}\n{c.text}"))
    vectors = embedder.embed_passages([c[3] for c in chunks]) if chunks else np.zeros((0, 1))
    return chunks, vectors


def clean_quote(quote: str) -> str:
    return LINE_PREFIX.sub("", CODE_FENCE.sub("", quote)).strip("\n")


def verify_finding(finding: dict, files_by_path: dict[str, str]) -> str | None:
    """Return None if the evidence is verified, else the reason it is not."""
    text = files_by_path.get(finding["file_path"].strip().lstrip("./"))
    if text is None:
        return "unknown_file"
    lines = text.split("\n")
    start, end = min(finding["line_start"], finding["line_end"]), max(finding["line_start"], finding["line_end"])
    if start > len(lines):
        return "lines_out_of_range"
    window = "\n".join(lines[max(0, start - 1 - LINE_SLACK) : min(len(lines), end + LINE_SLACK)])
    # Elided multi-line quote where every line carries its line number ("5| ...", "10| ..."), as
    # openai/gpt-oss-120b produced on 2026-10-18: each line must match the file at exactly that line number
    # and lie in the stated range. Stricter than the window check, not fuzzy.
    numbered = [GUTTER_LINE.match(line) for line in CODE_FENCE.sub("", finding["evidence_quote"]).split("\n") if line.strip()]
    if len(numbered) > 1 and all(numbered):
        substantial = False
        for match in numbered:
            n, text = int(match.group(1)), normalize(match.group(2))
            if not (start - LINE_SLACK <= n <= end + LINE_SLACK) or n > len(lines) or not text or text not in normalize(lines[n - 1]):
                return "quote_not_at_location"
            substantial = substantial or len(text) >= 8
        return None if substantial else "quote_not_at_location"
    # Formatting only (fences, gutter) is removed; the wording itself must match exactly.
    quote = clean_quote(finding["evidence_quote"])
    if quote_in_text(quote, window):
        return None
    # Multi-line quote that skips lines (a docstring, a blank line) or drops a trailing comment without marking it,
    # as observed on 2026-10-19: every quoted line must occur inside a real line of the window, in order, each in a
    # different line. Text that is not in the file, or lines out of order, cannot pass.
    window_lines = [normalize(line) for line in window.split("\n")]
    quoted = [normalize(line) for line in quote.split("\n")]
    quoted = [line for line in quoted if line and line.strip(". ") != ""]
    if len(quoted) >= 2 and any(len(line) >= 8 for line in quoted):
        position = 0
        for line in quoted:
            position = next((i + 1 for i in range(position, len(window_lines)) if line in window_lines[i]), -1)
            if position < 0:
                break
        else:
            return None
    return "quote_not_at_location"


def run_review(conn: sqlite3.Connection, embedder: Embedder, llm: LlmService, review_id: str) -> dict:
    review = conn.execute(
        "SELECT r.id, d.id AS deliverable_id, d.project_id FROM reviews r JOIN deliverables d ON d.id = r.deliverable_id WHERE r.id = ?",
        (review_id,),
    ).fetchone()
    with conn:
        conn.execute("UPDATE reviews SET status = 'running', started_at = ? WHERE id = ?", (utcnow(), review_id))
    try:
        files = conn.execute("SELECT path, kind, content_text FROM deliverable_files WHERE deliverable_id = ?",
                             (review["deliverable_id"],)).fetchall()
        files_by_path = {f["path"]: f["content_text"] for f in files}
        requirements = list_requirements(conn, review["project_id"])
        chunks, vectors = _excerpt_chunks(files, embedder)
        verdicts, severities, dropped, suppressed, failed = Counter(), Counter(), Counter(), Counter(), 0
        model = served_by = None
        for req in requirements:
            label = f"{req['code']} ({req['priority'].upper()}): {req['text']}"
            order = np.argsort(-(vectors @ embedder.embed_query(req["text"])))[:TOP_K] if len(chunks) else []
            excerpts = [Excerpt(chunks[i][0], chunks[i][1], chunks[i][2]) for i in order]
            try:
                result = llm.review_json(render_review_messages(label, excerpts), REVIEW_JUDGEMENT_JSON_SCHEMA, ReviewJudgement,
                                         schema_name="review_judgement", prompt_version=REVIEW_PROMPT_VERSION)
            except ReviewNotConfigured:
                raise
            except AssistantUnavailable as exc:
                failed += 1
                with conn:
                    conn.execute("INSERT OR REPLACE INTO requirement_results (review_id, requirement_id, status, note) VALUES (?, ?, 'review_failed', ?)",
                                 (review_id, req["id"], json.dumps(exc.attempts)))
                continue
            model, served_by = result.model, result.served_by
            judgement: ReviewJudgement = result.parsed  # type: ignore[assignment]
            kept, rejected = [], []
            for f in judgement.findings:
                item = f.model_dump()
                item["evidence_quote"] = result.masker.unmask(item["evidence_quote"])
                item["explanation"] = result.masker.unmask(item["explanation"])
                item["suggested_fix"] = result.masker.unmask(item["suggested_fix"])
                item["file_path"] = item["file_path"].strip().lstrip("./")
                reason = verify_finding(item, files_by_path)
                if reason:
                    dropped[reason] += 1
                    rejected.append({"reason": reason, "file_path": item["file_path"], "line_start": item["line_start"],
                                     "line_end": item["line_end"], "evidence_quote": item["evidence_quote"][:500]})
                    continue
                if item["severity"] == "blocker" and req["priority"] != "must":
                    item["severity"] = "major"
                item["evidence_quote"] = clean_quote(item["evidence_quote"])
                kept.append(item)
            verdict, note = judgement.verdict, None
            if verdict != "cannot_determine" and not kept:
                verdict, note = "cannot_determine", f"model said {judgement.verdict} but no evidence could be verified"
            if verdict == "cannot_determine":
                suppressed["info_on_undetermined"] += sum(1 for k in kept if k["severity"] == "info")
                kept = [k for k in kept if k["severity"] != "info"]
            verdicts[verdict] += 1
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO requirement_results (review_id, requirement_id, status, model_verdict, verdict, note, excerpts, dropped)"
                    " VALUES (?, ?, 'ok', ?, ?, ?, ?, ?)",
                    (review_id, req["id"], judgement.verdict, verdict, note,
                     json.dumps([{"path": e.path, "line_start": e.line_start} for e in excerpts]), json.dumps(rejected)),
                )
                for item in kept:
                    severities[item["severity"]] += 1
                    conn.execute(
                        "INSERT INTO findings (id, review_id, requirement_id, file_path, line_start, line_end, severity, explanation,"
                        " suggested_fix, evidence_quote, confidence) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (f"fnd-{uuid.uuid4().hex[:12]}", review_id, req["id"], item["file_path"], item["line_start"], item["line_end"],
                         item["severity"], item["explanation"], item["suggested_fix"], item["evidence_quote"], item["confidence"]),
                    )
        summary = {"requirements": len(requirements), "review_failed": failed, "coverage": dict(verdicts),
                   "findings_by_severity": dict(severities), "dropped_unverified_findings": dict(dropped),
                   "suppressed_findings": dict(suppressed),
                   "files": len(files), "excerpts_per_requirement": TOP_K}
        status = "failed" if requirements and failed == len(requirements) else "done"
        with conn:
            conn.execute("UPDATE reviews SET status = ?, model = ?, served_by = ?, summary = ?, finished_at = ? WHERE id = ?",
                         (status, model, served_by, json.dumps(summary), utcnow(), review_id))
        return summary
    except Exception as exc:  # recorded on the review; the API never surfaces a traceback
        with conn:
            conn.execute("UPDATE reviews SET status = 'failed', error = ?, finished_at = ? WHERE id = ?",
                         (f"{type(exc).__name__}", utcnow(), review_id))
        raise
