"""Clause-preserving chunking with provenance (spec 8.1).

Split by headings first (Markdown `#` headings, or numbered clause headings such as "3.2 Out of scope"
in text extracted from PDF/DOCX), then pack whole paragraphs up to a token budget measured with the
embedding model's tokenizer, so no chunk exceeds the embedding input limit. Every chunk keeps its
heading path, page (PDF) and line range, which citations show to the user.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

MD_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
# "3.2 Out of scope", "4. Non-negotiable requirements", "Article 5 - Payment" (title starts upper-case)
CLAUSE_HEADING = re.compile(r"^(?:(\d+(?:\.\d+){0,3})\.?|Article\s+(\d+))\s*[-.:)]?\s+([A-ZÀ-Ý][^.!?]{1,90})$")
MAX_TOKENS = 380  # e5 accepts 512 tokens; keep room for the "passage:" prefix and heading path
CODE_WINDOW, CODE_OVERLAP = 80, 10

TokenCounter = Callable[[str], int]


def approx_tokens(text: str) -> int:
    return int(len(text.split()) * 1.4) + 1


@dataclass(frozen=True)
class Page:
    text: str
    number: int | None = None  # 1-based page for PDFs, None otherwise


@dataclass(frozen=True)
class Chunk:
    idx: int
    heading_path: str
    text: str
    page: int | None
    line_start: int
    line_end: int


@dataclass(frozen=True)
class _Paragraph:
    text: str
    first: int
    last: int


def _heading(line: str, markdown: bool) -> tuple[int, str] | None:
    if markdown:
        match = MD_HEADING.match(line)
        return (len(match.group(1)), match.group(2).strip()) if match else None
    match = CLAUSE_HEADING.match(line.strip())
    if not match:
        return None
    level = match.group(1).count(".") + 1 if match.group(1) else 1
    return level, line.strip()


def _split_paragraph(p: _Paragraph, count: TokenCounter, max_tokens: int) -> list[_Paragraph]:
    """Split an over-long paragraph at sentence (then word) boundaries. Line provenance stays the
    paragraph's range: a cut inside a paragraph cannot be located more precisely."""
    pieces: list[str] = []
    current: list[str] = []
    for sentence in re.split(r"(?<=[.!?;:])\s+", p.text):
        while count(sentence) > max_tokens:
            words = sentence.split()
            cut = max(1, int(len(words) * max_tokens / count(sentence)))
            pieces.append(" ".join(words[:cut]))
            sentence = " ".join(words[cut:])
        if current and count(" ".join(current + [sentence])) > max_tokens:
            pieces.append(" ".join(current))
            current = []
        current.append(sentence)
    if current:
        pieces.append(" ".join(current))
    return [_Paragraph(text, p.first, p.last) for text in pieces if text.strip()]


def chunk_pages(pages: list[Page], *, markdown: bool, count: TokenCounter = approx_tokens, max_tokens: int = MAX_TOKENS) -> list[Chunk]:
    chunks: list[Chunk] = []
    stack: list[tuple[int, str]] = []
    line_no = 0

    def flush(paragraphs: list[_Paragraph], page: int | None) -> None:
        group: list[_Paragraph] = []

        def emit() -> None:
            path = " > ".join(t for _, t in stack) or "(untitled)"
            text = "\n\n".join(g.text for g in group)
            chunks.append(Chunk(len(chunks), path, text, page, group[0].first, group[-1].last))

        for paragraph in paragraphs:
            parts = [paragraph] if count(paragraph.text) <= max_tokens else _split_paragraph(paragraph, count, max_tokens)
            for part in parts:
                if group and count("\n\n".join(g.text for g in group + [part])) > max_tokens:
                    emit()
                    group = []
                group.append(part)
        if group:
            emit()
        paragraphs.clear()

    for page in pages:
        paragraphs: list[_Paragraph] = []
        lines: list[tuple[int, str]] = []

        def close() -> None:
            if lines:
                paragraphs.append(_Paragraph("\n".join(t for _, t in lines), lines[0][0], lines[-1][0]))
                lines.clear()

        for raw in page.text.replace("\r\n", "\n").split("\n"):
            line_no += 1
            heading = _heading(raw, markdown)
            if heading:
                close()
                flush(paragraphs, page.number)
                level, title = heading
                while stack and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, title))
            elif raw.strip():
                lines.append((line_no, raw.rstrip()))
            else:
                close()
        close()
        flush(paragraphs, page.number)
    return chunks


def chunk_code(text: str, path: str) -> list[Chunk]:
    """Source code: sliding windows of lines (spec 6 default); provenance = file path + lines."""
    lines = text.replace("\r\n", "\n").split("\n")
    chunks: list[Chunk] = []
    start = 0
    while start < len(lines):
        end = min(start + CODE_WINDOW, len(lines))
        body = "\n".join(lines[start:end])
        if body.strip():
            chunks.append(Chunk(len(chunks), path, body, None, start + 1, end))
        if end == len(lines):
            break
        start = end - CODE_OVERLAP
    return chunks
