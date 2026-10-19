"""Helpers shared by the research tools: HTTP client, error mapping and untrusted-text handling."""

import html
import re
from datetime import date, datetime, timezone
from typing import Any

import httpx

from app.schemas.research import ErrorCode, ToolError, ToolResult

USER_AGENT = "agentic-freelance-advisor/0.1 (technical research tool)"
MAX_QUERY_CHARS = 200

REMOVED_MARKER = "[removed: possible prompt injection]"

_TAG = re.compile(r"<[^>]+>")
# Chat-role markup must be handled before generic tag stripping, or its payload would survive.
_ROLE_BLOCK = re.compile(r"<\s*(system|assistant|tool|developer)\b[^>]*>.*?<\s*/\s*\1\s*>", re.IGNORECASE | re.DOTALL)
_ROLE_TAG = re.compile(r"</?\s*(?:system|assistant|tool|developer)\b[^>]*>", re.IGNORECASE)
_SPECIAL_TOKEN = re.compile(r"<\|[^|>]{1,30}\|>")
_BARE_URL = re.compile(r"https?://[^\s)\]>\"']+")
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_SPACES = re.compile(r"[ \t\f\v]+")
_SEGMENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

# Retrieved web pages and repositories are untrusted data. Segments that look like instructions
# aimed at an AI assistant are removed before the text can reach the model.
_INJECTION = re.compile(
    "|".join(
        [
            r"ignore\s+(?:all\s+|any\s+|the\s+|your\s+)?(?:previous|prior|above|earlier)\s+(?:instructions?|prompts?|messages?|rules?)",
            r"disregard\s+.{0,40}(?:instructions?|rules?|prompt)",
            r"forget\s+(?:everything|all|your)\b.{0,40}(?:instructions?|rules?|told)",
            r"you\s+are\s+now\s+(?:a|an|the|in)\b",
            r"(?:new|updated|revised|override)\s+(?:system\s+)?instructions?\s*:",
            r"system\s+prompt",
            r"(?:reveal|print|show|output|leak|send)\s+.{0,40}(?:api[\s_-]?key|secret|password|token|credentials)",
            r"do\s+not\s+(?:tell|inform|mention|reveal)\s+(?:this\s+to\s+)?the\s+user",
        ]
    ),
    re.IGNORECASE,
)


def sanitize_untrusted(text: str | None, max_chars: int) -> tuple[str, bool]:
    """Clean text from an external source and bound its length.

    Returns the cleaned text and whether instruction-like content had to be removed.
    HTML tags, markdown images/links and control characters are stripped, whitespace is
    collapsed, and any sentence that looks like an instruction to an AI assistant is replaced.
    """
    if not text:
        return "", False
    text = html.unescape(str(text))
    text = _CONTROL.sub(" ", text)

    text, blocks = _ROLE_BLOCK.subn(f" {REMOVED_MARKER} ", text)
    text, tokens = _SPECIAL_TOKEN.subn(" ", text)
    removed = bool(blocks or tokens or _ROLE_TAG.search(text))
    marker_added = bool(blocks)

    text = _MD_IMAGE.sub("", text)
    text = _MD_LINK.sub(r"\1", text)
    # Descriptions often contain raw URLs. They are not sources (the `url` field is), they get cut off by
    # truncation into broken links, and they are a channel for injected links, so they are dropped.
    text = _BARE_URL.sub("[link]", text)
    text = _TAG.sub(" ", text)

    kept: list[str] = []
    for segment in _SEGMENT_SPLIT.split(text):
        segment = _SPACES.sub(" ", segment).strip()
        if not segment:
            continue
        if _INJECTION.search(segment):
            if not marker_added:
                kept.append(REMOVED_MARKER)
                marker_added = True
            removed = True
            continue
        kept.append(segment)
    return truncate(" ".join(kept), max_chars), removed


def truncate(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 1)].rstrip() + "…"


def clean_query(query: Any) -> str:
    """Validate and normalise a search query that came from the model."""
    if not isinstance(query, str):
        raise ValueError("query must be a string")
    cleaned = _SPACES.sub(" ", _CONTROL.sub(" ", query.replace("\n", " "))).strip()
    if len(cleaned) < 2:
        raise ValueError("query is empty or too short")
    return cleaned[:MAX_QUERY_CHARS]


def make_client(timeout: float, headers: dict[str, str] | None = None) -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(timeout),
        headers={"User-Agent": USER_AGENT, **(headers or {})},
        follow_redirects=True,
    )


def failure(
    tool: str,
    arguments: dict[str, Any],
    code: ErrorCode,
    message: str,
    retry_after_seconds: int | None = None,
) -> ToolResult:
    return ToolResult(
        tool=tool,
        arguments=arguments,
        ok=False,
        error=ToolError(code=code, message=message, retry_after_seconds=retry_after_seconds),
    )


def error_from_exception(error: Exception, service: str) -> tuple[ErrorCode, str]:
    if isinstance(error, httpx.TimeoutException):
        return "timeout", f"{service} did not answer in time."
    if isinstance(error, httpx.TransportError):
        return "network_error", f"Could not reach {service} ({type(error).__name__})."
    return "unexpected", f"Unexpected error while calling {service}: {type(error).__name__}: {error}"


def retry_after_from_headers(headers: httpx.Headers) -> int | None:
    """Seconds to wait, from Retry-After or GitHub's x-ratelimit-reset epoch."""
    retry_after = headers.get("retry-after")
    if retry_after and retry_after.isdigit():
        return int(retry_after)
    reset = headers.get("x-ratelimit-reset")
    if reset and reset.isdigit():
        return max(0, int(reset) - int(datetime.now(timezone.utc).timestamp()))
    return None


def to_date(value: Any) -> str | None:
    """ISO date (YYYY-MM-DD) from a datetime, date or ISO string."""
    if isinstance(value, (datetime, date)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, str) and len(value) >= 10:
        return value[:10]
    return None


def days_since(iso_date: str | None) -> int | None:
    if not iso_date:
        return None
    try:
        then = datetime.fromisoformat(iso_date).replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return max(0, (datetime.now(timezone.utc) - then).days)
