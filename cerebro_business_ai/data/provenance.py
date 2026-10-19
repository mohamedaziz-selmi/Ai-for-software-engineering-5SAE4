"""Dataset provenance and integrity helpers for Phase 2."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Hash a file incrementally without loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def record_file(path: Path, source: str, license_name: str, rows: int | None = None, columns: Iterable[str] | None = None) -> dict:
    """Create a reproducible provenance record for a local artifact."""
    stat = path.stat()
    return {
        "path": str(path),
        "source": source,
        "license": license_name,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "size_bytes": stat.st_size,
        "sha256": sha256_file(path),
        "rows": rows,
        "columns": list(columns) if columns is not None else None,
    }


def write_manifest(path: Path, records: list[dict]) -> None:
    """Write sorted, indented provenance metadata."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2, sort_keys=True), encoding="utf-8")
