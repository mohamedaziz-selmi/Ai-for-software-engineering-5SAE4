"""PII and secret masking applied to every LLM input (course brief; spec 8.4).

Pattern-based, so it reduces exposure but cannot guarantee that all personal data is removed.
Placeholders are stable within one Masker (same value -> same placeholder), and `unmask` restores
the originals in model output shown to the user.
"""

from __future__ import annotations

import re

# Order matters: secrets and emails before generic number patterns.
_PATTERNS: list[tuple[str, re.Pattern[str], int]] = [
    # Quoted literal assigned to a secret-like name, including identifiers such as SMTP_PASSWORD or apiKey.
    # Only the literal is replaced, so code structure (and expressions like token_urlsafe(32)) stays intact.
    ("SECRET", re.compile(r"(?i)\b\w*(?:api[_-]?key|secret|password|passwd|pwd|token)\w*\s*[:=]\s*[\"']([^\"'\s]{6,})[\"']"), 1),
    # Prose form: "password: hunter22"
    ("SECRET", re.compile(r"(?i)\b(?:api[_-]?key|password|passwd|token)\s*:\s*([^\s\"'<]{6,})"), 1),
    ("SECRET", re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|gsk_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16})\b"), 0),
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), 0),
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}(?: ?[A-Z0-9]{1,3})?\b"), 0),
    ("CARD", re.compile(r"\b(?:\d[ -]?){12,18}\d\b"), 0),
    # Tunisian numbers: +216/00216 prefix, or the spaced "XX XXX XXX" national format.
    ("PHONE", re.compile(r"(?:\+|00)216[ .-]?\d{2}[ .-]?\d{3}[ .-]?\d{3}\b|\b[2-9]\d[ .-]\d{3}[ .-]\d{3}\b"), 0),
    ("PHONE", re.compile(r"\+\d{1,3}[ .-]?(?:\(\d{1,4}\)[ .-]?)?\d{2,4}(?:[ .-]?\d{2,4}){2,4}\b"), 0),
    # National ID (CIN) only next to an explicit label, so plain 8-digit amounts stay intact.
    ("CIN", re.compile(r"(?i)\b(?:CIN|carte d'identit[ée]|national id)\s*(?:n[°o]\.?)?\s*:?\s*(\d{8})\b"), 1),
]


def _luhn_ok(number: str) -> bool:
    digits = [int(d) for d in re.sub(r"\D", "", number)]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0


class Masker:
    def __init__(self) -> None:
        self._by_value: dict[str, str] = {}
        self._by_placeholder: dict[str, str] = {}
        self._counts: dict[str, int] = {}

    @property
    def replacements(self) -> int:
        return len(self._by_value)

    def _placeholder(self, kind: str, value: str) -> str:
        if value not in self._by_value:
            self._counts[kind] = self._counts.get(kind, 0) + 1
            placeholder = f"<{kind}_{self._counts[kind]}>"
            self._by_value[value] = placeholder
            self._by_placeholder[placeholder] = value
        return self._by_value[value]

    def mask(self, text: str) -> str:
        for kind, pattern, group in _PATTERNS:

            def replace(match: re.Match[str], kind: str = kind, group: int = group) -> str:
                value = match.group(group)
                if kind == "CARD" and not _luhn_ok(value):
                    return match.group(0)
                if value.startswith("<") and value.endswith(">"):
                    return match.group(0)
                start, end = match.start(group) - match.start(0), match.end(group) - match.start(0)
                whole = match.group(0)
                return whole[:start] + self._placeholder(kind, value) + whole[end:]

            text = pattern.sub(replace, text)
        return text

    def unmask(self, text: str) -> str:
        if not self._by_placeholder:
            return text
        return re.sub(r"<[A-Z]+_\d+>", lambda m: self._by_placeholder.get(m.group(0), m.group(0)), text)
