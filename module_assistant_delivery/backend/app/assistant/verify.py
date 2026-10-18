"""Citation verification in code (spec 8.2).

A citation survives only if it names a chunk that was actually provided and its quote occurs in that
chunk after normalisation. Passing this check proves the quote exists. It does not prove the quote
supports the claim; the faithfulness eval measures that.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from ..rag.retriever import RetrievedChunk

_TRANSLATE = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "})
MIN_QUOTE_CHARS = 8


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_TRANSLATE)
    text = re.sub(r"[*_`]+", "", text)  # Markdown emphasis is not part of the wording
    text = text.replace("|", " ")  # nor are table cell separators (models drop them across rows)
    text = re.sub(r"(^|\n)[ \t]*[-*•][ \t]+", r"\1", text)  # nor list bullets (models add or drop them)
    return re.sub(r"\s+", " ", text).strip().casefold()


def quote_in_text(quote: str, text: str) -> bool:
    q = normalize(quote).strip(" \"'.,;:")
    if len(q) < MIN_QUOTE_CHARS:
        return False
    haystack = normalize(text)
    position = 0
    for part in (p.strip(" \"'.,;:") for p in q.split("...")):
        if not part:
            continue
        found = haystack.find(part, position)
        if found < 0:
            return False
        position = found + len(part)
    return True


@dataclass(frozen=True)
class VerifiedCitation:
    label: str
    chunk: RetrievedChunk
    quote: str


@dataclass(frozen=True)
class Verification:
    valid: list[VerifiedCitation]
    dropped: list[dict]


def verify_citations(citations: list[tuple[str, str]], provided: dict[str, RetrievedChunk]) -> Verification:
    valid: list[VerifiedCitation] = []
    dropped: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for label, quote in citations:
        label = label.strip().strip("[]").upper()
        chunk = provided.get(label)
        if chunk is None:
            dropped.append({"label": label, "quote": quote, "reason": "unknown_chunk"})
        elif not quote_in_text(quote, f"{chunk.heading_path}\n{chunk.text}"):
            dropped.append({"label": label, "quote": quote, "reason": "quote_not_in_chunk"})
        elif (label, normalize(quote)) not in seen:
            seen.add((label, normalize(quote)))
            valid.append(VerifiedCitation(label, chunk, quote.strip()))
    return Verification(valid, dropped)
