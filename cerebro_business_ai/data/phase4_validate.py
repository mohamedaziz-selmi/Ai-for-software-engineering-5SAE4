"""Validate acquired Kaggle fraud data and write Phase 4 provenance."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "ai-service"))
from app.resource_guard import ResourceGuard  # noqa: E402
sys.path.insert(0, str(ROOT))
from data.provenance import record_file, write_manifest  # noqa: E402


EXPECTED = ["title", "location", "department", "salary_range", "company_profile", "description", "requirements", "benefits", "telecommuting", "has_company_logo", "has_questions", "employment_type", "required_experience", "required_education", "industry", "function", "fraudulent"]


def main() -> None:
    guard = ResourceGuard()
    if not guard.safe_to_start():
        raise RuntimeError("ResourceGuard denied validation")
    path = ROOT / "data/phase2/kaggle/job_fraud/fake_job_postings.csv"
    frame = pd.read_csv(path)
    missing = sorted(set(EXPECTED) - set(frame.columns))
    label_counts = {str(key): int(value) for key, value in frame["fraudulent"].value_counts(dropna=False).to_dict().items()}
    result = {"module": "job_fraud", "path": str(path), "rows": len(frame), "columns": list(frame.columns), "missing_expected_columns": missing, "label_counts": label_counts, "null_counts": {key: int(value) for key, value in frame.isna().sum().to_dict().items()}, "duplicate_rows": int(frame.duplicated().sum()), "duplicate_text_label_rows": int(frame.duplicated(subset=["title", "description", "requirements", "fraudulent"]).sum()), "license": "CC0-1.0 from Kaggle metadata", "valid": not missing, "resource": guard.as_dict()}
    out = ROOT / "data/phase4"
    out.mkdir(parents=True, exist_ok=True)
    (out / "job_fraud_validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    provenance = record_file(path, "https://www.kaggle.com/datasets/shivamb/real-or-fake-fake-jobposting-prediction", "CC0-1.0", len(frame), frame.columns)
    write_manifest(out / "provenance.json", [provenance])
    print(json.dumps(result, indent=2))
    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
