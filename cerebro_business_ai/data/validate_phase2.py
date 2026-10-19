"""Validate Phase 2 smoke files and local dataset schemas."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
SOURCES = json.loads((ROOT / "data" / "phase2_sources.json").read_text(encoding="utf-8"))


def validate_jsonl(path: Path, expected: list[str]) -> dict:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip(): rows.append(json.loads(line))
    if not rows: raise AssertionError(f"Empty smoke file: {path}")
    columns = list(rows[0])
    missing = sorted(set(expected) - set(columns))
    nulls = {column: sum(row.get(column) is None for row in rows) for column in columns}
    duplicates = len(rows) - len({json.dumps(row, sort_keys=True) for row in rows})
    return {"path": str(path), "rows": len(rows), "columns": columns, "missing_expected_columns": missing, "null_counts": nulls, "duplicate_rows": duplicates, "valid": not missing}


def validate_csv(path: Path, expected: list[str]) -> dict:
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        sample = [next(reader) for _ in range(10)]
    missing = sorted(set(expected) - set(columns))
    return {"path": str(path), "columns": columns, "sample_rows": len(sample), "missing_expected_columns": missing, "valid": not missing}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, default=ROOT / "data" / "phase2" / "smoke")
    args = parser.parse_args()
    results = []
    for module, source in SOURCES.items():
        jsonl = args.path / f"{module}.jsonl"
        if jsonl.exists(): results.append(validate_jsonl(jsonl, source.get("expected_columns", [])))
        else: results.append({"module": module, "status": "not_available", "reason": "No smoke file; Kaggle credentials or explicit large-download approval may be required."})
    print(json.dumps(results, indent=2))
    if any(item.get("valid") is False for item in results): raise SystemExit(1)


if __name__ == "__main__": main()
