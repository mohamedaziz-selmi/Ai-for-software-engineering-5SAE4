"""Project assistant: retrieve from the project's documents, generate a grounded answer, verify it."""

from __future__ import annotations

import json
import re
import sqlite3
import uuid

from ..db import utcnow
from ..llm.prompts import ASSISTANT_PROMPT_VERSION, ContextChunk, render_assistant_messages
from ..llm.schemas import ASSISTANT_ANSWER_JSON_SCHEMA, AssistantAnswer
from ..llm.service import LlmService
from ..rag.embeddings import Embedder
from ..rag.retriever import retrieve
from ..rag.vector_store import ChromaChunkStore
from .verify import verify_citations

NOT_FOUND = {
    "en": "This is not covered in the project documents.",
    "fr": "Cette information ne figure pas dans les documents du projet.",
}
_FRENCH_HINTS = re.compile(r"\b(quel|quelle|quels|quelles|est-ce|projet|le|la|les|des|du|une|pour|dans|sont)\b|[éèêàùç]", re.I)


def _language(text: str) -> str:
    return "fr" if len(_FRENCH_HINTS.findall(text)) >= 2 else "en"


def _conversation(conn: sqlite3.Connection, conversation_id: str | None, project_id: str, user_id: str) -> str:
    if conversation_id:
        row = conn.execute("SELECT project_id, user_id FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
        if row and row["project_id"] == project_id and row["user_id"] == user_id:
            return conversation_id
    new_id = f"conv-{uuid.uuid4().hex[:12]}"
    conn.execute("INSERT INTO conversations (id, project_id, user_id, created_at) VALUES (?, ?, ?, ?)", (new_id, project_id, user_id, utcnow()))
    return new_id


def answer_question(
    conn: sqlite3.Connection,
    embedder: Embedder,
    store: ChromaChunkStore,
    llm: LlmService,
    *,
    project_id: str,
    user_id: str,
    question: str,
    conversation_id: str | None,
    top_k: int,
) -> dict:
    retrieved = retrieve(conn, embedder, store, project_id=project_id, query=question, k=top_k)
    labelled = {f"C{i + 1}": chunk for i, chunk in enumerate(retrieved)}
    retrieval_info = [
        {"label": label, "chunk_id": c.chunk_id, "document_title": c.document_title, "section": c.heading_path, "score": round(c.score, 4)}
        for label, c in labelled.items()
    ]
    language = _language(question)

    base = {"retrieval": retrieval_info, "prompt_version": ASSISTANT_PROMPT_VERSION, "dropped_citations": [], "attempts": []}
    if not retrieved:
        result = {**base, "status": "no_documents", "grounded": False, "answer": NOT_FOUND[language], "citations": [],
                  "scope_verdict": None, "served_by": None, "model": None, "latency_ms": 0}
    else:
        messages = render_assistant_messages(
            [ContextChunk(label, c.document_title, c.heading_path, c.text) for label, c in labelled.items()], question
        )
        # Raises AssistantUnavailable when the local model and the (optional) backup both fail.
        llm_result = llm.assistant_json(
            messages, ASSISTANT_ANSWER_JSON_SCHEMA, AssistantAnswer,
            schema_name="assistant_answer", prompt_version=ASSISTANT_PROMPT_VERSION,
        )
        parsed: AssistantAnswer = llm_result.parsed  # type: ignore[assignment]
        unmask = llm_result.masker.unmask
        verification = verify_citations([(c.chunk_id, unmask(c.quote)) for c in parsed.citations], labelled)

        model_answer = unmask(parsed.answer).strip()
        if parsed.grounded and verification.valid and model_answer:
            status, answer = "answered", model_answer
        elif parsed.grounded:
            # The model claimed support but no citation survived (or it gave no text): never show an unverified answer.
            status, answer = "not_found_after_verification", NOT_FOUND[language]
        else:
            status, answer = "not_found", model_answer or NOT_FOUND[language]
        grounded = status == "answered"
        result = {
            **base,
            "status": status,
            "grounded": grounded,
            "answer": answer,
            "scope_verdict": parsed.scope_verdict if grounded else None,
            "citations": [
                {"label": v.label, "chunk_id": v.chunk.chunk_id, "document_title": v.chunk.document_title,
                 "document_version": v.chunk.document_version, "section": v.chunk.heading_path, "page": v.chunk.page,
                 "line_start": v.chunk.line_start, "line_end": v.chunk.line_end, "quote": v.quote, "verified": True}
                for v in verification.valid
            ] if grounded else [],
            "dropped_citations": verification.dropped,
            "served_by": llm_result.served_by,
            "model": llm_result.model,
            "latency_ms": llm_result.latency_ms,
            "attempts": llm_result.attempts,
        }

    with conn:
        conv_id = _conversation(conn, conversation_id, project_id, user_id)
        conn.execute(
            "INSERT INTO messages (id, conversation_id, role, text, created_at) VALUES (?, ?, 'user', ?, ?)",
            (f"msg-{uuid.uuid4().hex[:12]}", conv_id, question, utcnow()),
        )
        message_id = f"msg-{uuid.uuid4().hex[:12]}"
        conn.execute(
            "INSERT INTO messages (id, conversation_id, role, text, citations, grounded, status, scope_verdict, served_by,"
            " model, prompt_version, retrieval, verification, created_at) VALUES (?, ?, 'assistant', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (message_id, conv_id, result["answer"], json.dumps(result["citations"]), int(result["grounded"]), result["status"],
             result["scope_verdict"], result["served_by"], result["model"], result["prompt_version"],
             json.dumps(retrieval_info), json.dumps(result["dropped_citations"]), utcnow()),
        )
    return {"conversation_id": conv_id, "message_id": message_id, **result}
