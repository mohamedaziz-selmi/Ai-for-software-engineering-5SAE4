"""Output contracts. Every LLM output is validated against these before use (spec 8.2, 8.4)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ScopeVerdict = Literal["in_scope", "out_of_scope", "ambiguous"]


class Citation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    chunk_id: str = Field(min_length=1, max_length=32)
    quote: str = Field(min_length=1, max_length=1500)


class AssistantAnswer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # May be empty: observed from qwen3:4b-instruct-2507 on an off-topic request (2026-10-18). The service
    # replaces an empty ungrounded answer with the standard "not covered" text and withholds an empty grounded one.
    answer: str = Field(max_length=8000)
    citations: list[Citation] = Field(default_factory=list, max_length=16)
    grounded: bool
    scope_verdict: ScopeVerdict | None = None


# Hand-written (no $ref) so OpenAI-compatible servers can turn it into a decoding grammar.
ASSISTANT_ANSWER_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"chunk_id": {"type": "string"}, "quote": {"type": "string"}},
                "required": ["chunk_id", "quote"],
                "additionalProperties": False,
            },
        },
        "grounded": {"type": "boolean"},
        "scope_verdict": {"type": ["string", "null"], "enum": ["in_scope", "out_of_scope", "ambiguous", None]},
    },
    "required": ["answer", "citations", "grounded", "scope_verdict"],
    "additionalProperties": False,
}


Verdict = Literal["conforms", "partial", "violates", "cannot_determine"]
Severity = Literal["info", "minor", "major", "blocker"]


class JudgedFinding(BaseModel):
    model_config = ConfigDict(extra="ignore")
    file_path: str = Field(min_length=1, max_length=300)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    severity: Severity
    explanation: str = Field(min_length=1, max_length=2000)
    suggested_fix: str = Field(default="", max_length=2000)
    evidence_quote: str = Field(min_length=1, max_length=2000)
    confidence: float = Field(ge=0, le=1)


class ReviewJudgement(BaseModel):
    model_config = ConfigDict(extra="ignore")
    requirement_id: str = Field(min_length=1, max_length=40)
    verdict: Verdict
    findings: list[JudgedFinding] = Field(default_factory=list, max_length=10)


REVIEW_JUDGEMENT_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "requirement_id": {"type": "string"},
        "verdict": {"type": "string", "enum": ["conforms", "partial", "violates", "cannot_determine"]},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "line_start": {"type": "integer"},
                    "line_end": {"type": "integer"},
                    "severity": {"type": "string", "enum": ["info", "minor", "major", "blocker"]},
                    "explanation": {"type": "string"},
                    "suggested_fix": {"type": "string"},
                    "evidence_quote": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["file_path", "line_start", "line_end", "severity", "explanation", "suggested_fix", "evidence_quote", "confidence"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["requirement_id", "verdict", "findings"],
    "additionalProperties": False,
}
