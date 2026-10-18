"""Safe loading of Module 5 artifacts and inference helpers used by the API."""

from functools import lru_cache

import joblib
import pandas as pd

from .common import read_json
from .config import MODELS_DIR, PROCESSED_DIR, SALES_SPLITS
from .sales_features import CALENDAR_FLAG_COLUMNS
from .sales_model import recursive_forecast


class ArtifactMissing(RuntimeError):
	"""Raised when a model or dataset artifact has not been produced yet."""


def require(path, command):
	if not path.exists():
		raise ArtifactMissing(f"{path.relative_to(MODELS_DIR.parent).as_posix()} is missing. Run `{command}` in module5_business_intelligence/.")
	return path


SALES_CMD = "..\\rag_service\\.venv\\Scripts\\python.exe -m src.pipeline_sales"
SEGMENT_CMD = "..\\rag_service\\.venv\\Scripts\\python.exe -m src.pipeline_segmentation"


@lru_cache(maxsize=None)
def sales_artifacts():
	config = read_json(require(MODELS_DIR / "sales_feature_config.json", SALES_CMD))
	model = joblib.load(require(MODELS_DIR / "sales_forecast_model.joblib", SALES_CMD))
	names = list(getattr(model, "feature_names_in_", []))
	if names != config["feature_columns"]:
		raise ArtifactMissing("Saved sales model feature order does not match sales_feature_config.json; retrain the model.")
	history = pd.read_csv(require(PROCESSED_DIR / "daily_sales.csv", SALES_CMD), parse_dates=["date"]).set_index("date")
	calendar = pd.read_csv(require(PROCESSED_DIR / "sales_calendar.csv", SALES_CMD), parse_dates=["date"]).set_index("date")[CALENDAR_FLAG_COLUMNS]
	return model, config, history, calendar


@lru_cache(maxsize=None)
def advanced_forecast():
	path = MODELS_DIR / "sales_advanced_future_forecast.csv"
	if not path.exists():
		return None
	return pd.read_csv(path, parse_dates=["date"])


def forecast(horizon, origin=None):
	model, config, history, calendar = sales_artifacts()
	sales = history["sales"]
	origin = pd.Timestamp(origin) if origin is not None else sales.index.max()
	if origin < sales.index.min() + pd.Timedelta(days=29) or origin > sales.index.max():
		raise ValueError(f"Forecast origin must be between {(sales.index.min() + pd.Timedelta(days=29)).date()} and {sales.index.max().date()}.")
	if horizon < 1 or horizon > config["max_horizon_days"]:
		raise ValueError(f"Horizon must be between 1 and {config['max_horizon_days']} days.")
	last_needed = origin + pd.Timedelta(days=horizon)
	if last_needed > calendar.index.max():
		raise ValueError(f"The holiday calendar is only known until {calendar.index.max().date()}.")
	predictions = recursive_forecast(model, sales.loc[:origin], horizon, calendar)
	actual = sales.reindex(predictions.index)
	final_fit_end = pd.Timestamp(SALES_SPLITS["validation"][1])
	return {
		"origin": origin.date().isoformat(),
		"horizon": horizon,
		"method": "Random Forest, recursive multi-step (each prediction feeds the next day's lags)",
		"in_sample_warning": (
			"This origin lies inside the final model's fitting period (up to " + final_fit_end.date().isoformat() + "); forecasts may be optimistic."
			if origin < final_fit_end else None
		),
		"points": [
			{"date": day.date().isoformat(), "forecast": round(float(value), 2), "actual": None if pd.isna(actual.loc[day]) else round(float(actual.loc[day]), 2)}
			for day, value in predictions.items()
		],
	}


@lru_cache(maxsize=None)
def segments():
	table = pd.read_csv(require(PROCESSED_DIR / "customer_segments.csv", SEGMENT_CMD), dtype={"customer_id": str})
	config = read_json(require(MODELS_DIR / "customer_feature_config.json", SEGMENT_CMD))
	require(MODELS_DIR / "customer_kmeans_model.joblib", SEGMENT_CMD)
	return table, config


@lru_cache(maxsize=None)
def segmentation_model():
	model = joblib.load(require(MODELS_DIR / "customer_kmeans_model.joblib", SEGMENT_CMD))
	scaler = joblib.load(require(MODELS_DIR / "customer_scaler.joblib", SEGMENT_CMD))
	config = read_json(require(MODELS_DIR / "customer_feature_config.json", SEGMENT_CMD))
	if list(getattr(scaler, "feature_names_in_", config["features"])) != config["features"]:
		raise ArtifactMissing("Saved scaler feature order does not match customer_feature_config.json; retrain the model.")
	return model, scaler, config


def assign_segment(recency_days, frequency, monetary):
	"""Score one customer profile with the saved preprocessing settings and K-means model."""
	import numpy as np

	model, scaler, config = segmentation_model()
	values = {"recency_days": recency_days, "frequency": frequency, "monetary": max(0.0, monetary)}
	frame = pd.DataFrame([[float(values[f]) for f in config["features"]]], columns=config["features"])
	for feature in config["log1p_features"]:
		frame[feature] = np.log1p(frame[feature])
	cluster = int(model.predict(scaler.transform(frame))[0])
	return {"cluster": cluster, "segment_label": config["cluster_labels"].get(str(cluster), config["cluster_labels"].get(cluster))}


def clear_caches():
	for function in (sales_artifacts, advanced_forecast, segments, segmentation_model):
		function.cache_clear()
