"""Baselines, Random Forest training, and recursive multi-step forecasting for daily sales."""

import itertools

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.model_selection import TimeSeriesSplit

from .metrics import forecast_metrics
from .sales_features import FEATURE_COLUMNS, TARGET, features_for_next_day

PARAM_GRID = {
	"max_depth": [None, 12, 20],
	"min_samples_leaf": [1, 3, 5],
	"max_features": [1.0, 0.6, 0.33],
}
FIXED_PARAMS = {"n_estimators": 300, "n_jobs": -1}


def seasonal_naive(frame):
	"""prediction(t) = actual_sales(t - 7 days); equals the lag_7 feature."""
	return frame["lag_7"].to_numpy(dtype=float)


def historical_mean(train_target, n):
	return np.full(n, float(np.mean(train_target)))


def seasonal_naive_multistep(history, horizon):
	"""Repeat the last observed week; never uses values after the forecast origin."""
	last_week = np.asarray(history, dtype=float)[-7:]
	if last_week.size < 7:
		raise ValueError("Seasonal-naive multi-step forecasting needs at least 7 days of history.")
	return np.array([last_week[step % 7] for step in range(horizon)])


def make_model(params, seed):
	return RandomForestRegressor(random_state=seed, **FIXED_PARAMS, **params)


def tune(train, seed, n_splits=5):
	"""Rolling-origin cross-validation inside the training period only."""
	X, y = train[FEATURE_COLUMNS], train[TARGET]
	splitter = TimeSeriesSplit(n_splits=n_splits)
	results = []
	keys = list(PARAM_GRID)
	for values in itertools.product(*(PARAM_GRID[key] for key in keys)):
		params = dict(zip(keys, values))
		fold_mae = []
		for fit_index, check_index in splitter.split(X):
			model = make_model(params, seed)
			model.fit(X.iloc[fit_index], y.iloc[fit_index])
			fold_mae.append(float(np.mean(np.abs(y.iloc[check_index] - model.predict(X.iloc[check_index])))))
		results.append({"params": params, "fold_mae": fold_mae, "mean_mae": float(np.mean(fold_mae))})
	results.sort(key=lambda item: item["mean_mae"])
	folds = [
		{"fit_start": X.index[fit[0]], "fit_end": X.index[fit[-1]], "check_start": X.index[check[0]], "check_end": X.index[check[-1]]}
		for fit, check in splitter.split(X)
	]
	return results[0]["params"], {"folds": folds, "candidates": results, "selection_metric": "mean MAE over rolling-origin folds"}


def evaluate_period(model, period, train_target):
	actual = period[TARGET].to_numpy(dtype=float)
	predictions = {
		"seasonal_naive": seasonal_naive(period),
		"historical_mean": historical_mean(train_target, len(period)),
		"random_forest": model.predict(period[FEATURE_COLUMNS]),
	}
	return actual, predictions, {name: forecast_metrics(actual, values) for name, values in predictions.items()}


def recursive_forecast(model, history, horizon, calendar_flags=None):
	"""Predict horizon days after history.index[-1], feeding each prediction back as history."""
	history = history.astype(float).copy()
	predictions = []
	for _ in range(horizon):
		next_date = history.index[-1] + pd.Timedelta(days=1)
		row = features_for_next_day(history, next_date, calendar_flags)
		if row.isna().any(axis=None):
			raise ValueError("Not enough history to build lag and rolling features.")
		value = max(0.0, float(model.predict(row)[0]))
		predictions.append((next_date, value))
		history.loc[next_date] = value
	return pd.Series(dict(predictions), name="forecast")


def multistep_evaluation(model, daily_sales, start, end, block_days, calendar_flags=None):
	"""Rolling-origin blocks: each block forecasts block_days ahead from actual history up to its origin."""
	start, end = pd.Timestamp(start), pd.Timestamp(end)
	rows = []
	origin = start - pd.Timedelta(days=1)
	while origin < end:
		horizon = min(block_days, (end - origin).days)
		history = daily_sales.loc[:origin]
		rf = recursive_forecast(model, history, horizon, calendar_flags)
		naive = seasonal_naive_multistep(history.to_numpy(), horizon)
		for step, (day, value) in enumerate(rf.items()):
			rows.append({"date": day, "origin": origin, "horizon": step + 1, "actual": float(daily_sales.loc[day]), "random_forest": value, "seasonal_naive": float(naive[step])})
		origin += pd.Timedelta(days=horizon)
	frame = pd.DataFrame(rows)
	metrics = {name: forecast_metrics(frame["actual"], frame[name]) for name in ("seasonal_naive", "random_forest")}
	by_horizon = frame.assign(rf_abs=(frame.actual - frame.random_forest).abs(), naive_abs=(frame.actual - frame.seasonal_naive).abs()).groupby("horizon")[["rf_abs", "naive_abs"]].mean()
	return frame, metrics, {int(h): {"random_forest_mae": float(r.rf_abs), "seasonal_naive_mae": float(r.naive_abs)} for h, r in by_horizon.iterrows()}


def error_breakdown(dates, actual, predicted):
	frame = pd.DataFrame({"date": pd.DatetimeIndex(dates), "abs_error": np.abs(np.asarray(actual) - np.asarray(predicted)), "actual": actual})
	names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
	weekday = frame.groupby(frame.date.dt.dayofweek).agg(mae=("abs_error", "mean"), n=("abs_error", "size"), abs_error_sum=("abs_error", "sum"), actual_sum=("actual", "sum"))
	month = frame.groupby(frame.date.dt.month).agg(mae=("abs_error", "mean"), n=("abs_error", "size"), abs_error_sum=("abs_error", "sum"), actual_sum=("actual", "sum"))
	fmt = lambda table, label: [
		{"group": label(index), "mae": float(row.mae), "wape": float(row.abs_error_sum / row.actual_sum * 100) if row.actual_sum else None, "n": int(row.n)}
		for index, row in table.iterrows()
	]
	return {"by_weekday": fmt(weekday, lambda i: names[i]), "by_month": fmt(month, lambda i: pd.Timestamp(2000, i, 1).strftime("%b"))}


def feature_importances(model, period, seed):
	impurity = dict(zip(FEATURE_COLUMNS, model.feature_importances_.tolist()))
	permutation = permutation_importance(model, period[FEATURE_COLUMNS], period[TARGET], n_repeats=10, random_state=seed, scoring="neg_mean_absolute_error", n_jobs=-1)
	rows = [
		{"feature": name, "impurity_importance": impurity[name], "permutation_mae_increase": float(permutation.importances_mean[index]), "permutation_std": float(permutation.importances_std[index])}
		for index, name in enumerate(FEATURE_COLUMNS)
	]
	return sorted(rows, key=lambda item: item["permutation_mae_increase"], reverse=True)


def residual_histogram(actual, predicted, bins=25):
	residuals = np.asarray(actual) - np.asarray(predicted)
	counts, edges = np.histogram(residuals, bins=bins)
	return {"edges": edges.tolist(), "counts": counts.tolist(), "mean": float(residuals.mean()), "std": float(residuals.std()), "median": float(np.median(residuals))}
