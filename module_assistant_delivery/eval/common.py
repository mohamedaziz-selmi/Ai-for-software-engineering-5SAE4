"""Shared helpers for eval runners. Runners import the backend package directly (no HTTP)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_ROOT / "backend"))
RESULTS = MODULE_ROOT / "eval" / "results"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def keyword_match(answer: str, groups: list[list[str]]) -> bool:
    """Crude correctness proxy: every keyword group must have at least one alternative in the answer."""
    text = answer.casefold()
    return all(any(k.casefold() in text for k in group) for group in groups)


def percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(p / 100 * (len(ordered) - 1))))
    return ordered[index]
