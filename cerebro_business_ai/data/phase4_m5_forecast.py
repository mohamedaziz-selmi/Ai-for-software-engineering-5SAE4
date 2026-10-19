"""Guarded, lightweight M5 demand experiment and artifact writer."""
from __future__ import annotations

import json, os, sys, time
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from xgboost import XGBRegressor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai-service"))
from app.resource_guard import ResourceGuard  # noqa: E402
from m5_pipeline import add_lag_calendar_features, forecast_metrics  # noqa: E402

DATA = ROOT / "data" / "phase2" / "kaggle" / "product_demand" / "extracted"
OUT = ROOT / "data" / "phase4"
ART = ROOT / "ai-service" / "artifacts"
FEATURES = ["lag_1", "lag_7", "lag_28", "rolling_mean_7", "rolling_mean_28",
            "dayofweek", "dayofmonth", "month", "weekofyear", "has_event",
            "sell_price", "price_change"]


def main() -> None:
    started = time.perf_counter()
    guard = ResourceGuard()
    before = guard.snapshot()
    if not guard.safe_to_start(before):
        raise RuntimeError(f"ResourceGuard denied start: {guard.as_dict(before)}")
    os.environ.update(guard.environment())
    sales_path = DATA / "sales_train_validation.csv"
    cal_path = DATA / "calendar.csv"
    prices_path = DATA / "sell_prices.csv"
    sales = pd.read_csv(sales_path, nrows=20)
    # Read the full header once, then load only a small deterministic series subset.
    all_sales = pd.read_csv(sales_path, nrows=20)
    day_cols = [c for c in all_sales.columns if c.startswith("d_")]
    long = all_sales.melt(id_vars=["item_id", "store_id"], value_vars=day_cols,
                          var_name="d", value_name="sales")
    cal = pd.read_csv(cal_path, usecols=["date", "wm_yr_wk", "d", "event_name_1", "event_type_1", "snap_CA", "snap_TX", "snap_WI"])
    long = long.merge(cal, on="d", how="left", validate="many_to_one")
    # Price is loaded with only required columns and filtered to the 20 selected series.
    prices = pd.read_csv(prices_path, usecols=["store_id", "item_id", "wm_yr_wk", "sell_price"])
    long = long.merge(prices, on=["store_id", "item_id", "wm_yr_wk"], how="left", validate="many_to_one")
    long["sell_price"] = long["sell_price"].ffill().bfill().fillna(0.0)
    long = add_lag_calendar_features(long, group_columns=("item_id", "store_id"), target="sales")
    long["has_event"] = long.get("has_event", 0)
    long["price_change"] = long.get("price_change", 0).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    long["sales"] = pd.to_numeric(long["sales"], errors="coerce").fillna(0.0)
    long = long.sort_values(["date", "item_id", "store_id"])
    dates = sorted(pd.to_datetime(long["date"]).unique())
    test_start, val_start = dates[-28], dates[-56]
    train = long[pd.to_datetime(long.date) < val_start].copy()
    valid = long[(pd.to_datetime(long.date) >= val_start) & (pd.to_datetime(long.date) < test_start)].copy()
    test = long[pd.to_datetime(long.date) >= test_start].copy()
    usable = [c for c in FEATURES if c in long.columns]
    for frame in (train, valid, test):
        frame.dropna(subset=usable, inplace=True)
    x_train, y_train = train[usable], train["sales"]
    x_val, y_val = valid[usable], valid["sales"]
    x_test, y_test = test[usable], test["sales"]
    model = XGBRegressor(n_estimators=180, max_depth=4, learning_rate=0.08,
                         subsample=0.8, colsample_bytree=0.85,
                         objective="reg:squarederror", eval_metric="rmse",
                         early_stopping_rounds=20, tree_method="hist",
                         n_jobs=guard.bounded_thread_count(), random_state=42)
    model.fit(x_train, y_train, eval_set=[(x_val, y_val)], verbose=False)
    predictions = []
    for name, frame, actual in (("validation", valid, y_val), ("test", test, y_test)):
        pred = np.maximum(0, model.predict(frame[usable]))
        naive = frame["lag_7"].fillna(0).to_numpy()
        predictions.append(pd.DataFrame({"split": name, "date": frame["date"].to_numpy(), "actual": actual.to_numpy(), "seasonal_naive": naive, "xgboost": pred}))
    pred_df = pd.concat(predictions, ignore_index=True)
    metrics = {"validation": {}, "test": {}}
    for split in metrics:
        part = pred_df[pred_df.split == split]
        metrics[split]["seasonal_naive"] = forecast_metrics(part.actual, part.seasonal_naive)
        metrics[split]["xgboost"] = forecast_metrics(part.actual, part.xgboost)
    after = guard.snapshot()
    metadata = {"status": "complete", "dataset": "M5 Forecasting Accuracy", "source": "https://www.kaggle.com/competitions/m5-forecasting-accuracy/data", "subset_series": 20, "train_dates": [str(pd.Timestamp(train.date.min()).date()), str(pd.Timestamp(train.date.max()).date())], "validation_dates": [str(pd.Timestamp(valid.date.min()).date()), str(pd.Timestamp(valid.date.max()).date())], "test_dates": [str(pd.Timestamp(test.date.min()).date()), str(pd.Timestamp(test.date.max()).date())], "feature_names": usable, "n_train": len(train), "n_validation": len(valid), "n_test": len(test), "metrics": metrics, "best_iteration": int(getattr(model, "best_iteration", -1)), "elapsed_seconds": round(time.perf_counter() - started, 3), "resource_before": guard.as_dict(before), "resource_after": guard.as_dict(after), "resource_policy": {"target_percent": 85, "safety_threshold_percent": 90, "threads": guard.bounded_thread_count()}}
    OUT.mkdir(parents=True, exist_ok=True); ART.mkdir(parents=True, exist_ok=True)
    pred_df.to_csv(OUT / "m5_forecast_predictions.csv", index=False)
    (OUT / "m5_forecast_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (OUT / "m5_model_metadata.json").write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
    joblib.dump(model, ART / "m5_xgboost.joblib")
    plot = pred_df[pred_df.split == "test"].groupby("date", as_index=False)[["actual", "seasonal_naive", "xgboost"]].sum()
    plt.figure(figsize=(11, 4)); plt.plot(plot.date, plot.actual, label="actual"); plt.plot(plot.date, plot.seasonal_naive, label="seasonal naive"); plt.plot(plot.date, plot.xgboost, label="xgboost"); plt.legend(); plt.tight_layout(); plt.savefig(OUT / "m5_actual_vs_predicted.png", dpi=120); plt.close()
    print(json.dumps(metadata, indent=2, default=str))


if __name__ == "__main__":
    main()
