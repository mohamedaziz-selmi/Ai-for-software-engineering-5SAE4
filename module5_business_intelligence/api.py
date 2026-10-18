"""Module 5 Business Intelligence API (sales forecasting + customer segmentation).

Serves saved artifacts only; it never trains models during a request.
Run: ..\\rag_service\\.venv\\Scripts\\python.exe -m uvicorn api:app --port 8002
"""

from datetime import date
from typing import Literal, Optional

import pandas as pd
from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src import inference
from src.common import read_json
from src.config import DATA_DIR, DATA_REPORTS_DIR, MODELS_DIR, REPORTS_DIR

app = FastAPI(title="Cerebro Module 5 - Business Intelligence API", version="1.0.0")
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)
router = APIRouter(prefix="/api/module5")

ARTIFACTS = {
	"sales_forecasting": ["sales_forecast_model.joblib", "sales_feature_config.json", "sales_evaluation.json", "sales_training_metadata.json"],
	"sales_advanced": ["sales_advanced_model.joblib", "sales_advanced_evaluation.json", "sales_advanced_future_forecast.csv"],
	"customer_segmentation": ["customer_kmeans_model.joblib", "customer_scaler.joblib", "customer_feature_config.json", "customer_evaluation.json", "customer_training_metadata.json"],
}


def unavailable(error):
	raise HTTPException(status_code=503, detail=str(error)) from error


def load(path, command):
	try:
		return read_json(inference.require(path, command))
	except inference.ArtifactMissing as error:
		unavailable(error)


def optional(path):
	return read_json(path) if path.exists() else None


@router.get("/health")
def health():
	status = training_status()
	return {"ready": all(item["ready"] for key, item in status["models"].items() if key != "sales_advanced"), "models": {key: item["ready"] for key, item in status["models"].items()}}


@router.get("/training-status")
def training_status():
	models = {}
	for key, files in ARTIFACTS.items():
		present = {name: (MODELS_DIR / name).exists() for name in files}
		meta_name = {"sales_forecasting": "sales_training_metadata.json", "customer_segmentation": "customer_training_metadata.json", "sales_advanced": "sales_advanced_evaluation.json"}[key]
		meta = optional(MODELS_DIR / meta_name) or {}
		models[key] = {
			"ready": all(present.values()),
			"artifacts": present,
			"trained_at": meta.get("trained_at") or meta.get("created_at"),
			"model": meta.get("model"),
			"dataset": meta.get("dataset"),
			"hyperparameters": meta.get("hyperparameters"),
			"environment": meta.get("environment"),
			"runtime_seconds": meta.get("runtime_seconds"),
			"command": meta.get("command") or "..\\rag_service\\.venv\\Scripts\\python.exe -m src.pipeline_sales",
		}
	return {"models": models, "note": "Training runs only from the command line; the API never trains during a request."}


@router.get("/overview")
def overview(
	start: Optional[date] = Query(None, description="Start of the sales period (default: last 28 days of history)."),
	end: Optional[date] = Query(None, description="End of the sales period (default: last history date)."),
	forecast_days: int = Query(14, ge=1, le=28),
):
	result = {"training_status": training_status()["models"], "sales": None, "segmentation": None, "data_quality": None}
	try:
		_, _, history, _ = inference.sales_artifacts()
		sales = history["sales"]
		end_ts = pd.Timestamp(end) if end else sales.index.max()
		start_ts = pd.Timestamp(start) if start else end_ts - pd.Timedelta(days=27)
		if start_ts > end_ts:
			raise HTTPException(status_code=422, detail="start must be on or before end.")
		window = sales.loc[start_ts:end_ts]
		evaluation = read_json(MODELS_DIR / "sales_evaluation.json")
		future = inference.forecast(forecast_days)
		result["sales"] = {
			"period": {"start": start_ts.date().isoformat(), "end": end_ts.date().isoformat(), "days": int(window.size)},
			"total_sales": float(window.sum()),
			"history_range": {"start": sales.index.min().date().isoformat(), "end": sales.index.max().date().isoformat()},
			"forecast": {"days": forecast_days, "origin": future["origin"], "total": float(sum(p["forecast"] for p in future["points"]))},
			"test_metrics": evaluation["test"]["metrics"],
			"test_period": evaluation["test"]["period"],
		}
	except inference.ArtifactMissing as error:
		result["sales"] = {"unavailable": str(error)}
	try:
		table, config = inference.segments()
		evaluation = read_json(MODELS_DIR / "customer_evaluation.json")
		result["segmentation"] = {
			"eligible_customers": int(len(table)),
			"segments": int(table["cluster"].nunique()),
			"silhouette_after": evaluation["comparison"]["after_preprocessing"]["silhouette"],
			"silhouette_before": evaluation["comparison"]["before_preprocessing"]["silhouette"],
			"reference_date": config["reference_date"],
			"segment_sizes": table["segment_label"].value_counts().to_dict(),
		}
	except inference.ArtifactMissing as error:
		result["segmentation"] = {"unavailable": str(error)}
	quality = optional(DATA_REPORTS_DIR / "data_quality_report.json")
	if quality:
		result["data_quality"] = {key: {"status": value["status"], "checks": value["checks"]} for key, value in quality.items() if isinstance(value, dict)}
	return result


@router.get("/data-quality")
def data_quality():
	reports = {
		name: optional(DATA_REPORTS_DIR / f"{name}.json")
		for name in ("data_quality_report", "cleaning_report", "transformation_report", "sales_exploration_report", "retail_exploration_report")
	}
	if not any(reports.values()):
		raise HTTPException(status_code=503, detail="No data reports found. Run the Module 5 pipelines first.")
	reports["dataset_manifest"] = optional(DATA_DIR / "dataset_manifest.json")
	reports["written_reports"] = sorted(p.name for p in REPORTS_DIR.glob("*.md"))
	return reports


@router.get("/sales/evaluation")
def sales_evaluation():
	evaluation = load(MODELS_DIR / "sales_evaluation.json", inference.SALES_CMD)
	return {"basic": evaluation, "advanced": optional(MODELS_DIR / "sales_advanced_evaluation.json"), "metadata": optional(MODELS_DIR / "sales_training_metadata.json")}


@router.get("/sales/history")
def sales_history(start: Optional[date] = None, end: Optional[date] = None):
	try:
		_, _, history, _ = inference.sales_artifacts()
	except inference.ArtifactMissing as error:
		unavailable(error)
	sales = history["sales"]
	start_ts = pd.Timestamp(start) if start else sales.index.max() - pd.Timedelta(days=179)
	end_ts = pd.Timestamp(end) if end else sales.index.max()
	if start_ts > end_ts:
		raise HTTPException(status_code=422, detail="start must be on or before end.")
	window = history.loc[start_ts:end_ts]
	if window.empty:
		raise HTTPException(status_code=422, detail=f"No history between {start_ts.date()} and {end_ts.date()}; data covers {sales.index.min().date()} to {sales.index.max().date()}.")
	return {
		"range": {"start": sales.index.min().date().isoformat(), "end": sales.index.max().date().isoformat()},
		"points": [{"date": day.date().isoformat(), "sales": round(float(row.sales), 2), "is_closure_day": int(row.is_closure_day), "is_national_holiday": int(row.is_national_holiday)} for day, row in window.iterrows()],
	}


class ForecastRequest(BaseModel):
	model: Optional[Literal["basic", "advanced"]] = Field(None, description="Defaults to advanced when a store or family filter is given, otherwise basic.")
	horizon: int = Field(14, ge=1, le=28, description="Days to forecast after the origin.")
	origin: Optional[date] = Field(None, description="Last observed day; defaults to the end of history.")
	history_days: int = Field(90, ge=7, le=730, description="Days of actual history returned for context.")
	store_nbr: Optional[int] = Field(None, ge=1, description="Advanced model filter (future period only).")
	family: Optional[str] = Field(None, min_length=1, max_length=60)


def run_forecast(request: ForecastRequest):
	if request.model == "advanced" or (request.model is None and (request.store_nbr is not None or request.family)):
		return advanced(request)
	if request.store_nbr is not None or request.family:
		raise HTTPException(status_code=422, detail="Store and family filters require the advanced model.")
	try:
		result = inference.forecast(request.horizon, request.origin)
		_, _, history, _ = inference.sales_artifacts()
	except inference.ArtifactMissing as error:
		unavailable(error)
	except ValueError as error:
		raise HTTPException(status_code=422, detail=str(error)) from error
	origin = pd.Timestamp(result["origin"])
	context = history["sales"].loc[origin - pd.Timedelta(days=request.history_days - 1):origin]
	result["history"] = [{"date": d.date().isoformat(), "actual": round(float(v), 2)} for d, v in context.items()]
	result["model"] = "basic"
	return result


def advanced(request: ForecastRequest):
	frame = inference.advanced_forecast()
	if frame is None:
		raise HTTPException(status_code=503, detail="The advanced store x family model has not been trained. Run the sales pipeline without --skip-advanced.")
	if request.origin is not None:
		raise HTTPException(status_code=422, detail="Store and family filters forecast the future period only; remove 'origin'.")
	selected = frame
	if request.store_nbr is not None:
		if request.store_nbr not in set(frame["store_nbr"]):
			raise HTTPException(status_code=422, detail=f"Unknown store_nbr {request.store_nbr}.")
		selected = selected[selected["store_nbr"] == request.store_nbr]
	if request.family:
		if request.family not in set(frame["family"]):
			raise HTTPException(status_code=422, detail=f"Unknown product family '{request.family}'.")
		selected = selected[selected["family"] == request.family]
	daily = selected.groupby("date")["forecast"].sum().sort_index().iloc[: request.horizon]
	context = []
	if request.store_nbr is None and not request.family:
		try:
			_, _, history, _ = inference.sales_artifacts()
			sales = history["sales"]
			context = [{"date": d.date().isoformat(), "actual": round(float(v), 2)} for d, v in sales.iloc[-request.history_days:].items()]
		except inference.ArtifactMissing:
			context = []
	return {
		"model": "advanced",
		"method": "HistGradientBoosting per store x family, direct multi-step (all lags >= 16 days)",
		"origin": (daily.index.min() - pd.Timedelta(days=1)).date().isoformat(),
		"horizon": int(len(daily)),
		"max_horizon": int(frame["date"].nunique()),
		"filters": {"store_nbr": request.store_nbr, "family": request.family},
		"points": [{"date": d.date().isoformat(), "forecast": round(float(v), 2), "actual": None} for d, v in daily.items()],
		"history": context,
		"history_note": None if context else "Per-series history is not served; only the aggregate total history is shown.",
	}


@router.get("/sales/forecast")
def sales_forecast_get(
	model: Optional[Literal["basic", "advanced"]] = None,
	horizon: int = Query(14, ge=1, le=28),
	origin: Optional[date] = None,
	history_days: int = Query(90, ge=7, le=730),
	store_nbr: Optional[int] = Query(None, ge=1),
	family: Optional[str] = Query(None, min_length=1, max_length=60),
):
	return run_forecast(ForecastRequest(model=model, horizon=horizon, origin=origin, history_days=history_days, store_nbr=store_nbr, family=family))


@router.post("/sales/forecast")
def sales_forecast_post(request: ForecastRequest):
	return run_forecast(request)


@router.get("/sales/options")
def sales_options():
	frame = inference.advanced_forecast()
	return {"advanced_available": frame is not None, "stores": sorted(int(s) for s in frame["store_nbr"].unique()) if frame is not None else [], "families": sorted(frame["family"].unique().tolist()) if frame is not None else []}


@router.get("/segmentation/evaluation")
def segmentation_evaluation():
	evaluation = load(MODELS_DIR / "customer_evaluation.json", inference.SEGMENT_CMD)
	return {"evaluation": evaluation, "metadata": optional(MODELS_DIR / "customer_training_metadata.json")}


@router.get("/segmentation/clusters")
def segmentation_clusters():
	evaluation = load(MODELS_DIR / "customer_evaluation.json", inference.SEGMENT_CMD)
	after = evaluation["comparison"]["after_preprocessing"]
	return {"k": evaluation["comparison"]["k"], "reference_date": evaluation["comparison"]["reference_date"], "clusters": after["profiles"], "label_notes": evaluation["label_notes"], "distributions": evaluation["distributions"]}


SORTABLE = {"customer_id", "recency_days", "frequency", "monetary", "avg_order_value", "unique_products", "active_months", "cluster"}


@router.get("/segmentation/customers")
def segmentation_customers(
	search: Optional[str] = Query(None, max_length=20, pattern=r"^\d*$", description="Customer ID prefix."),
	cluster: Optional[int] = Query(None, ge=0, le=50),
	segment: Optional[str] = Query(None, max_length=80),
	page: int = Query(1, ge=1),
	page_size: int = Query(25, ge=5, le=100),
	sort: str = Query("monetary"),
	order: Literal["asc", "desc"] = "desc",
):
	if sort not in SORTABLE:
		raise HTTPException(status_code=422, detail=f"sort must be one of {sorted(SORTABLE)}.")
	try:
		table, _ = inference.segments()
	except inference.ArtifactMissing as error:
		unavailable(error)
	selected = table
	if search:
		selected = selected[selected["customer_id"].str.startswith(search)]
	if cluster is not None:
		selected = selected[selected["cluster"] == cluster]
	if segment:
		selected = selected[selected["segment_label"] == segment]
	selected = selected.sort_values(sort, ascending=order == "asc", kind="stable")
	total = int(len(selected))
	rows = selected.iloc[(page - 1) * page_size: page * page_size]
	return {
		"total": total, "page": page, "page_size": page_size, "pages": max(1, -(-total // page_size)),
		"segments": sorted(table["segment_label"].unique().tolist()),
		"customers": rows.round(2).to_dict(orient="records"),
		"privacy": "Pseudonymous customer IDs and aggregated metrics only; no names, addresses, or transaction lines are exposed.",
	}


class SegmentRequest(BaseModel):
	recency_days: float = Field(ge=0, le=5000)
	frequency: float = Field(ge=1, le=10000)
	monetary: float = Field(ge=0, le=1e8)


@router.post("/segmentation/assign")
def segmentation_assign(request: SegmentRequest):
	try:
		return inference.assign_segment(request.recency_days, request.frequency, request.monetary)
	except inference.ArtifactMissing as error:
		unavailable(error)


app.include_router(router)
