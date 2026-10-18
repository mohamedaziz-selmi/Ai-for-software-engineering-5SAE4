"""Resumable download of a training checkpoint into the module's HF cache (storage/hf).

Uses plain HTTP downloads (Xet disabled) with timeouts and retries, because on this network the
default path stalled with no open connection (observed 2026-10-18). Partial files are resumed.

  .venv-raft\\Scripts\\python.exe raft\\download.py unsloth/Qwen3-4B-Instruct-2507-bnb-4bit
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("HF_HOME", str(MODULE_ROOT / "storage" / "hf"))
os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "60")
os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "30")

from huggingface_hub import snapshot_download  # noqa: E402


def main(repo: str, attempts: int = 30) -> None:
    for attempt in range(1, attempts + 1):
        started = time.time()
        try:
            path = snapshot_download(repo, max_workers=2)
            print(f"done {repo} -> {path} (attempt {attempt}, {time.time() - started:.0f}s)", flush=True)
            return
        except Exception as exc:  # network errors: back off and resume
            print(f"attempt {attempt} failed after {time.time() - started:.0f}s: {type(exc).__name__}: {str(exc)[:200]}", flush=True)
            time.sleep(min(60, 5 * attempt))
    raise SystemExit(f"could not download {repo}")


if __name__ == "__main__":
    main(sys.argv[1])
