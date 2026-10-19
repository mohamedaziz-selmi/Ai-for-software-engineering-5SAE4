"""Inference helpers for the lightweight, leakage-safe M5 artifact."""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import joblib
import numpy as np

from .resource_guard import ResourceGuard

ROOT = Path(__file__).parents[2]
MODEL_PATH = ROOT / "ai-service" / "artifacts" / "m5_xgboost.joblib"
META_PATH = ROOT / "data" / "phase4" / "m5_model_metadata.json"


def forecast_from_history(history: list[float], horizon: int, last_date: date | None = None, sell_price: float = 0.0) -> list[float]:
    guard = ResourceGuard()
    snap = guard.snapshot()
    if not guard.safe_to_start(snap):
        raise RuntimeError("ResourceGuard denied demand inference")
    if not MODEL_PATH.exists() or not META_PATH.exists():
        raise FileNotFoundError("M5 model artifact is not available")
    model = joblib.load(MODEL_PATH)
    features = __import__("json").loads(META_PATH.read_text(encoding="utf-8"))["feature_names"]
    values = [max(0.0, float(x)) for x in history]
    anchor = last_date or date.today()
    output = []
    for step in range(1, horizon + 1):
        d = anchor + timedelta(days=step)
        row = {"lag_1": values[-1], "lag_7": values[-7], "lag_28": values[-28],
               "rolling_mean_7": float(np.mean(values[-7:])), "rolling_mean_28": float(np.mean(values[-28:])),
               "dayofweek": d.weekday(), "dayofmonth": d.day, "month": d.month,
               "weekofyear": int(d.isocalendar().week), "has_event": 0,
               "sell_price": max(0.0, float(sell_price)), "price_change": 0.0}
        prediction = max(0.0, float(model.predict([[row[name] for name in features]])[0]))
        values.append(prediction); output.append(prediction)
    return output
