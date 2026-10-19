"""Chunked quality validation for the full Phase 3 Hugging Face downloads."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

import sys
ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "ai-service"))
from app.resource_guard import ResourceGuard  # noqa: E402

SOURCES = json.loads((ROOT / "data" / "phase2_sources.json").read_text(encoding="utf-8"))


def validate_csv(path: Path, expected: list[str]) -> dict:
    guard = ResourceGuard()
    if not guard.safe_to_start():
        raise RuntimeError("ResourceGuard denied CSV validation")
    rows = 0
    nulls: dict[str, int] = {}
    duplicate_count = 0
    duplicate_scope = "within_chunk_and_first_100000_rows"
    sample_rows = 0
    sample = None
    columns = []
    for chunk in pd.read_csv(path, chunksize=10000, low_memory=False):
        if not columns:
            columns = list(chunk.columns)
            nulls = {column: 0 for column in columns}
        rows += len(chunk)
        for column in columns:
            nulls[column] += int(chunk[column].isna().sum())
        duplicate_count += int(chunk.duplicated().sum())
        if sample_rows < 100000:
            sample = chunk.head(100000 - sample_rows) if sample is None else pd.concat([sample, chunk.head(100000 - sample_rows)], ignore_index=True)
            sample_rows = len(sample)
    missing = sorted(set(expected) - set(columns))
    sample_duplicate_rows = int(sample.duplicated().sum()) if sample is not None else 0
    return {"path": str(path), "rows": rows, "columns": columns, "missing_expected_columns": missing, "null_counts": nulls, "duplicate_rows_observed_within_chunks": duplicate_count, "duplicate_rows_in_first_100000": sample_duplicate_rows, "duplicate_check_scope": duplicate_scope, "valid": not missing}


def validate_parquet(directory: Path, expected: list[str]) -> dict:
    guard = ResourceGuard()
    files = sorted(directory.rglob("*.parquet"))
    if not files:
        return {"path": str(directory), "status": "not_available"}
    total_rows = 0
    columns: list[str] = []
    sample_duplicates = 0
    sample = None
    file_results = []
    for path in files:
        table = pq.ParquetFile(path)
        total_rows += table.metadata.num_rows
        if not columns:
            columns = table.schema_arrow.names
        if sample is None:
            sample = table.read_row_group(0).to_pandas().head(1000)
        file_results.append({"file": str(path), "rows": table.metadata.num_rows, "size_bytes": path.stat().st_size})
    if guard.should_pause():
        raise RuntimeError("ResourceGuard requested validation pause")
    if sample is not None:
        sample_duplicates = int(sample.astype(str).duplicated().sum())
    missing = sorted(set(expected) - set(columns))
    return {"path": str(directory), "files": file_results, "rows": total_rows, "columns": columns, "missing_expected_columns": missing, "sample_duplicate_rows": sample_duplicates, "valid": not missing}


def main() -> None:
    results = []
    data_jobs = ROOT / "data/phase2/huggingface/job_description/data_jobs.csv"
    if data_jobs.exists():
        results.append({"module": "job_description", **validate_csv(data_jobs, SOURCES["job_description"]["expected_columns"])})
    else:
        results.append({"module": "job_description", "status": "not_available"})
    amazon = ROOT / "data/phase2/huggingface/product_listing/data"
    results.append({"module": "product_listing", **validate_parquet(amazon, SOURCES["product_listing"]["expected_columns"])})
    destination = ROOT / "data/phase3/validation_full.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    if any(result.get("valid") is False for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
