"""Leakage-safe M5 feature engineering and evaluation helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd


def chronological_split(frame: pd.DataFrame, date_column: str = "date", validation_days: int = 28, test_days: int = 28):
    dates = sorted(pd.to_datetime(frame[date_column]).dropna().unique())
    if len(dates) <= validation_days + test_days:
        raise ValueError("Not enough chronological dates for requested splits")
    train_end = dates[-validation_days - test_days - 1]
    validation_start = dates[-validation_days - test_days]
    test_start = dates[-test_days]
    dates_series = pd.to_datetime(frame[date_column])
    return frame[dates_series <= train_end].copy(), frame[(dates_series >= validation_start) & (dates_series < test_start)].copy(), frame[dates_series >= test_start].copy()


def add_lag_calendar_features(frame: pd.DataFrame, group_columns=("item_id", "store_id"), target="sales") -> pd.DataFrame:
    result = frame.copy()
    result["date"] = pd.to_datetime(result["date"])
    result = result.sort_values([*group_columns, "date"])
    grouped = result.groupby(list(group_columns), sort=False)[target]
    for lag in (1, 7, 28):
        result[f"lag_{lag}"] = grouped.shift(lag)
    for window in (7, 28):
        result[f"rolling_mean_{window}"] = grouped.transform(lambda values: values.shift(1).rolling(window, min_periods=1).mean())
    result["dayofweek"] = result["date"].dt.dayofweek
    result["dayofmonth"] = result["date"].dt.day
    result["month"] = result["date"].dt.month
    result["weekofyear"] = result["date"].dt.isocalendar().week.astype(int)
    if "event_name_1" in result:
        result["has_event"] = result["event_name_1"].notna().astype(int)
    if "sell_price" in result:
        result["price_change"] = result.groupby(list(group_columns))["sell_price"].pct_change().replace([np.inf, -np.inf], np.nan)
    return result


def seasonal_naive(frame: pd.DataFrame, lag: int = 7, group_columns=("item_id", "store_id"), target="sales") -> pd.Series:
    ordered = frame.sort_values([*group_columns, "date"])
    return ordered.groupby(list(group_columns), sort=False)[target].shift(lag).fillna(0)


def forecast_metrics(actual, predicted) -> dict:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    error = actual - predicted
    return {"mae": float(np.mean(np.abs(error))), "rmse": float(np.sqrt(np.mean(error ** 2))), "wape": float(np.sum(np.abs(error)) / max(np.sum(np.abs(actual)), 1e-9))}
