import json
from pathlib import Path

from data.phase3_validate_full import validate_csv


def test_full_data_jobs_schema_and_quality_artifact():
    root = Path(__file__).parents[2]
    report = root / "data/phase3/validation_full.json"
    assert report.exists()
    results = json.loads(report.read_text(encoding="utf-8"))
    job = next(item for item in results if item["module"] == "job_description")
    assert job["valid"] is True
    assert job["rows"] == 785741
    assert "company_name" in job["columns"]


def test_kaggle_blocker_is_explicit():
    root = Path(__file__).parents[2]
    result = json.loads((root / "data/phase3/metrics/job_fraud_baseline.json").read_text(encoding="utf-8"))
    assert result["status"] == "blocked"
    assert "Kaggle" in result["reason"]
