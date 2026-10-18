"""API validation and error handling, plus checks that saved metrics match the real artifacts."""

import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import api
from src import inference
from src.common import read_json
from src.config import MODELS_DIR, PROCESSED_DIR, SALES_SPLITS
from src.metrics import forecast_metrics
from src.sales_features import FEATURE_COLUMNS, build_features

ARTIFACTS_READY = (MODELS_DIR / "sales_evaluation.json").exists() and (MODELS_DIR / "customer_evaluation.json").exists()
needs_artifacts = pytest.mark.skipif(not ARTIFACTS_READY, reason="Run both pipelines on the real datasets first.")
client = TestClient(api.app)
FRONTEND = Path(__file__).resolve().parents[2] / "src" / "BusinessIntelligence.jsx"


@pytest.fixture
def no_artifacts(tmp_path, monkeypatch):
	monkeypatch.setattr(inference, "MODELS_DIR", tmp_path)
	monkeypatch.setattr(inference, "PROCESSED_DIR", tmp_path)
	monkeypatch.setattr(api, "MODELS_DIR", tmp_path)
	monkeypatch.setattr(api, "DATA_REPORTS_DIR", tmp_path)
	inference.clear_caches()
	yield
	inference.clear_caches()


def test_missing_artifacts_return_clear_503(no_artifacts):
	for path in ("/api/module5/sales/evaluation", "/api/module5/sales/forecast", "/api/module5/segmentation/customers", "/api/module5/segmentation/clusters"):
		response = client.get(path)
		assert response.status_code == 503, path
		assert "Run" in response.json()["detail"]
	status = client.get("/api/module5/training-status").json()
	assert not any(model["ready"] for model in status["models"].values())
	overview = client.get("/api/module5/overview").json()
	assert "unavailable" in overview["sales"] and "unavailable" in overview["segmentation"]


@pytest.mark.parametrize("query", ["horizon=0", "horizon=29", "history_days=3", "origin=not-a-date", "store_nbr=0"])
def test_forecast_input_validation(query):
	assert client.get(f"/api/module5/sales/forecast?{query}").status_code == 422


@pytest.mark.parametrize("query", ["page=0", "page_size=500", "search=abc", "sort=country", "order=sideways"])
def test_customer_query_validation(query):
	assert client.get(f"/api/module5/segmentation/customers?{query}").status_code == 422


@needs_artifacts
def test_forecast_endpoints():
	result = client.post("/api/module5/sales/forecast", json={"horizon": 7, "history_days": 30}).json()
	assert len(result["points"]) == 7 and len(result["history"]) == 30
	assert result["points"][0]["date"] == "2017-08-16" and all(p["actual"] is None for p in result["points"])
	backtest = client.get("/api/module5/sales/forecast?origin=2017-07-01&horizon=5").json()
	assert all(p["actual"] is not None for p in backtest["points"]) and backtest["in_sample_warning"] is None
	assert client.get("/api/module5/sales/forecast?origin=2010-01-01").status_code == 422
	assert client.get("/api/module5/sales/forecast?store_nbr=999").status_code == 422
	assert client.get("/api/module5/sales/forecast?family=NOPE").status_code == 422
	filtered = client.get("/api/module5/sales/forecast?store_nbr=1&family=BEVERAGES&horizon=4").json()
	assert filtered["model"] == "advanced" and len(filtered["points"]) == 4


@needs_artifacts
def test_customer_listing_filters_and_privacy():
	page = client.get("/api/module5/segmentation/customers?page_size=10&sort=recency_days&order=asc").json()
	assert len(page["customers"]) == 10
	assert [c["recency_days"] for c in page["customers"]] == sorted(c["recency_days"] for c in page["customers"])
	assert set(page["customers"][0]) == {"customer_id", "recency_days", "frequency", "monetary", "avg_order_value", "unique_products", "active_months", "cluster", "segment_label"}
	segment = page["segments"][0]
	only = client.get("/api/module5/segmentation/customers", params={"segment": segment, "page_size": 100}).json()
	assert all(c["segment_label"] == segment for c in only["customers"])
	search = client.get("/api/module5/segmentation/customers?search=1234").json()
	assert all(c["customer_id"].startswith("1234") for c in search["customers"])


@needs_artifacts
def test_saved_sales_metrics_match_artifacts():
	"""Recompute test-period metrics from daily_sales.csv and the saved model; they must equal the JSON report."""
	evaluation = read_json(MODELS_DIR / "sales_evaluation.json")
	model, _, history, calendar = inference.sales_artifacts()
	daily = history.reset_index()[["date", "sales"]]
	features = build_features(daily, calendar_flags=calendar)
	start, end = map(pd.Timestamp, SALES_SPLITS["test"])
	test = features.loc[start:end]
	saved = evaluation["test"]["metrics"]
	assert forecast_metrics(test["sales"], test["lag_7"])["mae"] == pytest.approx(saved["seasonal_naive"]["mae"])
	assert forecast_metrics(test["sales"], model.predict(test[FEATURE_COLUMNS]))["wape"] == pytest.approx(saved["random_forest"]["wape"])
	assert evaluation["test"]["period"]["start"] == SALES_SPLITS["test"][0]
	assert evaluation["validation"]["period"]["n_days"] == evaluation["validation"]["metrics"]["random_forest"]["n_observations"]


@needs_artifacts
def test_saved_segments_match_model():
	model, scaler, config = inference.segmentation_model()
	segments = pd.read_csv(PROCESSED_DIR / "customer_segments.csv", dtype={"customer_id": str})
	frame = segments[config["features"]].astype(float)
	for feature in config["log1p_features"]:
		frame[feature] = np.log1p(frame[feature])
	assert (model.predict(scaler.transform(frame)) == segments["cluster"]).mean() > 0.999
	assert segments["customer_id"].is_unique and segments["segment_label"].notna().all()
	evaluation = read_json(MODELS_DIR / "customer_evaluation.json")
	assert sum(evaluation["comparison"]["after_preprocessing"]["cluster_sizes"]) == len(segments)


@needs_artifacts
@pytest.mark.skipif(not FRONTEND.exists(), reason="Dashboard component not present.")
def test_dashboard_calls_only_existing_endpoints():
	"""Every Module 5 endpoint referenced by the React dashboard must exist and answer with JSON."""
	source = FRONTEND.read_text(encoding="utf-8")
	assert 'const API = "/api/module5";' in source
	paths = sorted({f"/api/module5{suffix}" for suffix in re.findall(r"\$\{API\}(/[a-z\-/]+)", source)})
	assert paths, "Dashboard does not call the Module 5 API."
	routes = {route.path for route in api.router.routes}
	for path in paths:
		assert path in routes, f"{path} is used by the dashboard but not served"
		if path.endswith("/assign"):
			continue
		methods = set().union(*(getattr(r, "methods", None) or set() for r in api.router.routes if r.path == path))
		response = client.get(path) if "GET" in methods else client.post(path, json={})
		assert response.status_code == 200, path
		assert isinstance(response.json(), dict)
