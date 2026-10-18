"""Small helpers for JSON reports, step logging, and environment metadata."""

import hashlib
import json
import math
import platform
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def to_jsonable(value):
	if isinstance(value, dict):
		return {str(key): to_jsonable(item) for key, item in value.items()}
	if isinstance(value, (list, tuple, set)):
		return [to_jsonable(item) for item in value]
	if isinstance(value, (np.integer,)):
		return int(value)
	if isinstance(value, (np.floating, float)):
		number = float(value)
		return None if math.isnan(number) or math.isinf(number) else number
	if isinstance(value, (np.bool_,)):
		return bool(value)
	if isinstance(value, (pd.Timestamp, datetime, date)):
		return value.isoformat()
	if isinstance(value, Path):
		return value.as_posix()
	if isinstance(value, np.ndarray):
		return to_jsonable(value.tolist())
	return value


def write_json(path, payload):
	path = Path(path)
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(to_jsonable(payload), indent=2, ensure_ascii=False), encoding="utf-8")
	return path


def read_json(path):
	return json.loads(Path(path).read_text(encoding="utf-8"))


def update_report(path, key, payload):
	"""Shared report files hold one section per AI work; each pipeline replaces only its own section."""
	path = Path(path)
	report = read_json(path) if path.exists() else {}
	report[key] = payload
	report["updated_at"] = utc_now()
	return write_json(path, report)


def utc_now():
	return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def file_sha256(path, chunk_size=1 << 20):
	digest = hashlib.sha256()
	with open(path, "rb") as handle:
		for chunk in iter(lambda: handle.read(chunk_size), b""):
			digest.update(chunk)
	return digest.hexdigest()


def environment_versions():
	import joblib
	import sklearn

	return {
		"python": sys.version.split()[0],
		"platform": platform.platform(),
		"pandas": pd.__version__,
		"numpy": np.__version__,
		"scikit-learn": sklearn.__version__,
		"joblib": joblib.__version__,
	}


class StepLog:
	"""Records row counts before and after every cleaning operation."""

	def __init__(self):
		self.steps = []

	def record(self, name, before, after, reason, policy=None, **details):
		entry = {
			"step": name,
			"rows_before": int(before),
			"rows_after": int(after),
			"rows_removed": int(before - after),
			"reason": reason,
		}
		if policy:
			entry["policy"] = policy
		entry.update(details)
		self.steps.append(entry)
		return entry


def describe_series(series):
	series = pd.Series(series).dropna()
	if series.empty:
		return {"count": 0}
	return {
		"count": int(series.size),
		"mean": float(series.mean()),
		"median": float(series.median()),
		"std": float(series.std()) if series.size > 1 else 0.0,
		"min": float(series.min()),
		"p01": float(series.quantile(0.01)),
		"p25": float(series.quantile(0.25)),
		"p75": float(series.quantile(0.75)),
		"p99": float(series.quantile(0.99)),
		"max": float(series.max()),
		"skewness": float(series.skew()) if series.size > 2 else 0.0,
	}


def histogram(series, bins=30, log=False):
	values = pd.Series(series).dropna().to_numpy(dtype=float)
	if log:
		values = np.log1p(np.clip(values, 0, None))
	if values.size == 0:
		return {"edges": [], "counts": [], "log1p": log}
	counts, edges = np.histogram(values, bins=bins)
	return {"edges": edges.tolist(), "counts": counts.tolist(), "log1p": log}


def missing_summary(frame):
	total = len(frame)
	return {
		column: {
			"missing": int(count),
			"missing_pct": float(count / total * 100) if total else 0.0,
		}
		for column, count in frame.isna().sum().items()
	}
