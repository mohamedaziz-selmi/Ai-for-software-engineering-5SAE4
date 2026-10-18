"""Deliverable upload validation: text files only, size limits, safe paths. Code is never executed."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import PurePosixPath

from ..rag.loaders import CODE, MARKDOWN, PLAIN

MAX_FILES = 50          # [ASSUMPTION] spec 8.3
MAX_FILE_BYTES = 200_000
ALLOWED = CODE | MARKDOWN | PLAIN


class RejectedUpload(ValueError):
    pass


@dataclass(frozen=True)
class DeliverableFile:
    path: str
    kind: str
    size: int
    sha256: str
    text: str


def safe_path(name: str) -> str:
    parts = [p for p in PurePosixPath(name.replace("\\", "/")).parts if p not in ("", ".", "/")]
    if not parts or any(p == ".." or ":" in p for p in parts):
        raise RejectedUpload(f"Unsafe file path: {name!r}")
    return "/".join(parts)


def validate_files(files: list[tuple[str, bytes]]) -> list[DeliverableFile]:
    if not files:
        raise RejectedUpload("No files uploaded.")
    if len(files) > MAX_FILES:
        raise RejectedUpload(f"At most {MAX_FILES} files per deliverable.")
    result, seen = [], set()
    for name, raw in files:
        path = safe_path(name)
        suffix = PurePosixPath(path).suffix.lower()
        if suffix not in ALLOWED:
            raise RejectedUpload(f"{path}: only text and source-code files are reviewed.")
        if len(raw) > MAX_FILE_BYTES:
            raise RejectedUpload(f"{path}: larger than {MAX_FILE_BYTES // 1000} KB.")
        if b"\x00" in raw:
            raise RejectedUpload(f"{path}: looks binary.")
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise RejectedUpload(f"{path}: not UTF-8 text.") from exc
        if path in seen:
            raise RejectedUpload(f"Duplicate path {path}.")
        seen.add(path)
        kind = "code" if suffix in CODE else "markdown" if suffix in MARKDOWN else "text"
        result.append(DeliverableFile(path, kind, len(raw), hashlib.sha256(raw).hexdigest(), text.replace("\r\n", "\n")))
    return result
