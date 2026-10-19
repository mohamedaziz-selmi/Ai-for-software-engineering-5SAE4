"""Controlled 200-series M5 comparison; preserves the prior 20-series results."""
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
    sales_path, cal_path, prices_path = (DATA / n for n in ("sales_train_validation.csv", "calendar.csv", "sell_prices.csv"))
    sales = pd.read_csv(sales_path)
    day_cols = [c for c in sales.columns if c.startswith("d_")]
    sales["mean_demand"] = sales[day_cols].mean(axis=1)
    # Balanced deterministic selection: 100 low-demand and 100 high-demand series.
    low = sales.sort_values(["mean_demand", "id"], ascending=[True, True]).head(100)
    high = sales.sort_values(["mean_demand", "id"], ascending=[False, True]).head(100)
    selected = pd.concat([low, high], ignore_index=True).drop_duplicates("id")
    long = selected.melt(id_vars=["item_id", "store_id", "id"], value_vars=day_cols,
                         var_name="d", value_name="sales")
    cal = pd.read_csv(cal_path, usecols=["date", "wm_yr_wk", "d", "event_name_1", "event_type_1"])
    long = long.merge(cal, on="d", how="left", validate="many_to_one")
    prices = pd.read_csv(prices_path, usecols=["store_id", "item_id", "wm_yr_wk", "sell_price"])
    long = long.merge(prices, on=["store_id", "item_id", "wm_yr_wk"], how="left", validate="many_to_one")
    long["sell_price"] = long.groupby(["item_id", "store_id"])["sell_price"].ffill().bfill().fillna(0.0)
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
    model = XGBRegressor(n_estimators=220, max_depth=5, learning_rate=0.07,
                         subsample=0.8, colsample_bytree=0.85,
                         objective="reg:squarederror", eval_metric="rmse",
                         early_stopping_rounds=20, tree_method="hist",
                         n_jobs=guard.bounded_thread_count(), random_state=42)
    if guard.should_pause(guard.snapshot()):
        raise RuntimeError("ResourceGuard requested pause before model fit")
    model.fit(train[usable], train["sales"], eval_set=[(valid[usable], valid["sales"])], verbose=False)
    output = []
    for split, frame in (("validation", valid), ("test", test)):
        xgb = np.maximum(0, model.predict(frame[usable]))
        seasonal = frame["lag_7"].fillna(0).to_numpy()
        moving = frame["rolling_mean_7"].fillna(0).to_numpy()
        part = frame[["id", "date", "sales"]].copy()
        part["split"], part["seasonal_naive"], part["moving_average"], part["xgboost"] = split, seasonal, moving, xgb
        output.append(part)
    predictions = pd.concat(output, ignore_index=True)
    metrics = {"validation": {}, "test": {}}
    volume = {}
    for split in metrics:
        part = predictions[predictions.split == split]
        for name in ("seasonal_naive", "moving_average", "xgboost"):
            metrics[split][name] = forecast_metrics(part.sales, part[name])
        # Volume/error analysis is based on the training mean, not future targets.
        means = selected.set_index("id")["mean_demand"]
        part = part.assign(volume=part.id.map(means).fillna(0))
        volume[split] = {}
        for band, subset in (("low_demand", part[part.volume <= means.quantile(.5)]), ("high_demand", part[part.volume > means.quantile(.5)])):
            volume[split][band] = {"series": int(subset.id.nunique()), "zero_actual_rate": float((subset.sales == 0).mean()), "xgboost": forecast_metrics(subset.sales, subset.xgboost), "seasonal_naive": forecast_metrics(subset.sales, subset.seasonal_naive)}
    after = guard.snapshot()
    metadata = {"status": "complete", "dataset": "M5 Forecasting Accuracy", "subset_series": int(selected.id.nunique()), "selection": "100 lowest and 100 highest training-mean-demand series", "train_dates": [str(pd.Timestamp(train.date.min()).date()), str(pd.Timestamp(train.date.max()).date())], "validation_dates": [str(pd.Timestamp(valid.date.min()).date()), str(pd.Timestamp(valid.date.max()).date())], "test_dates": [str(pd.Timestamp(test.date.min()).date()), str(pd.Timestamp(test.date.max()).date())], "n_train": len(train), "n_validation": len(valid), "n_test": len(test), "metrics": metrics, "volume_analysis": volume, "best_iteration": int(getattr(model, "best_iteration", -1)), "elapsed_seconds": round(time.perf_counter() - started, 3), "resource_before": guard.as_dict(before), "resource_after": guard.as_dict(after), "resource_policy": {"target_percent": 85, "safety_threshold_percent": 90, "threads": guard.bounded_thread_count()}}
    OUT.mkdir(parents=True, exist_ok=True); ART.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(OUT / "m5_200_series_predictions.csv", index=False)
    (OUT / "m5_200_series_metrics.json").write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
    joblib.dump(model, ART / "m5_xgboost_200_series.joblib")
    plot = predictions[predictions.split == "test"].groupby("date", as_index=False)[["sales", "seasonal_naive", "moving_average", "xgboost"]].sum()
    plt.figure(figsize=(11, 4)); plt.plot(plot.date, plot.sales, label="actual"); plt.plot(plot.date, plot.seasonal_naive, label="seasonal naive"); plt.plot(plot.date, plot.moving_average, label="moving average"); plt.plot(plot.date, plot.xgboost, label="xgboost"); plt.legend(); plt.tight_layout(); plt.savefig(OUT / "m5_200_series_actual_vs_predicted.png", dpi=120); plt.close()
    print(json.dumps(metadata, indent=2, default=str))


if __name__ == "__main__":
    main()
