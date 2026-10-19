import json
from pathlib import Path


def test_phase4_fraud_artifacts_have_real_metrics():
    root = Path(__file__).parents[2]
    metrics = json.loads((root / "data/phase4/job_fraud/metrics.json").read_text(encoding="utf-8"))
    assert metrics["status"] == "complete"
    assert metrics["rows_after_dedupe"] == 6000
    assert 0 <= metrics["metrics"]["logistic_regression"]["pr_auc"] <= 1
    assert 0 <= metrics["metrics"]["xgboost"]["pr_auc"] <= 1


def test_m5_access_blocker_is_recorded():
    root = Path(__file__).parents[2]
    report = json.loads((root / "data/phase4_m5_access.json").read_text(encoding="utf-8"))
    assert report["download_status"] == "blocked"
    assert "403" in report["download_error"]
