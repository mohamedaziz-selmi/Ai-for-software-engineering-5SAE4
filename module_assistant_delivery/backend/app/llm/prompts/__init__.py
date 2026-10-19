"""Versioned prompt files. The runtime and the RAFT data generator both render prompts from here,
so the tuned model sees at inference exactly the format it was trained on (spec 8.2)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent
ASSISTANT_PROMPT_VERSION = "assistant_answer.v1"


@dataclass(frozen=True)
class ContextChunk:
    label: str  # C1..Ck, assigned per request
    document_title: str
    section: str
    text: str


def _load(version: str) -> tuple[str, str]:
    raw = (PROMPT_DIR / f"{version}.md").read_text(encoding="utf-8")
    system, user = raw.split("=== USER ===", 1)
    return system.replace("=== SYSTEM ===", "", 1).strip(), user.strip()


def _attr(value: str) -> str:
    return value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def render_context(chunks: list[ContextChunk]) -> str:
    blocks = []
    for c in chunks:
        # Document text is untrusted: stop it from closing its own delimiter.
        body = c.text.replace("</chunk", "</ chunk")
        blocks.append(f'<chunk id="{c.label}" document="{_attr(c.document_title)}" section="{_attr(c.section)}">\n{body}\n</chunk>')
    return "\n\n".join(blocks)


def render_assistant_messages(chunks: list[ContextChunk], question: str, version: str = ASSISTANT_PROMPT_VERSION) -> list[dict]:
    system, user = _load(version)
    user = user.replace("{{context}}", render_context(chunks)).replace("{{question}}", question.strip())
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# v2: explicit verdict definitions and order; absence of code is not evidence.
# v3 (tried 2026-10-19, NOT used): measured worse than v2 (more flipping verdicts); kept for traceability.
REVIEW_PROMPT_VERSION = "review_judge.v2"


@dataclass(frozen=True)
class Excerpt:
    path: str
    line_start: int
    text: str  # the file lines starting at line_start


def render_excerpts(excerpts: list[Excerpt]) -> str:
    blocks = []
    for e in excerpts:
        lines = e.text.split("\n")
        numbered = "\n".join(f"{e.line_start + i:>5}| {line}" for i, line in enumerate(lines)).replace("</file", "</ file")
        end = e.line_start + len(lines) - 1
        blocks.append(f'<file path="{_attr(e.path)}" lines="{e.line_start}-{end}">\n{numbered}\n</file>')
    return "\n\n".join(blocks)


def render_review_messages(requirement: str, excerpts: list[Excerpt], version: str = REVIEW_PROMPT_VERSION) -> list[dict]:
    system, user = _load(version)
    user = user.replace("{{requirement}}", requirement.strip()).replace("{{excerpts}}", render_excerpts(excerpts))
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
