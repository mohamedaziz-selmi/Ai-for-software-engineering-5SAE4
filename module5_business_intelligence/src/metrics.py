"""Forecast error metrics with explicit handling of degenerate inputs."""

import numpy as np


def _arrays(actual, predicted):
	actual = np.asarray(actual, dtype=float)
	predicted = np.asarray(predicted, dtype=float)
	if actual.shape != predicted.shape:
		raise ValueError(f"Shape mismatch: actual {actual.shape} vs predicted {predicted.shape}.")
	if actual.size == 0:
		raise ValueError("Metrics need at least one observation.")
	if not (np.isfinite(actual).all() and np.isfinite(predicted).all()):
		raise ValueError("Metrics received NaN or infinite values.")
	return actual, predicted


def mae(actual, predicted):
	actual, predicted = _arrays(actual, predicted)
	return float(np.mean(np.abs(actual - predicted)))


def rmse(actual, predicted):
	actual, predicted = _arrays(actual, predicted)
	return float(np.sqrt(np.mean((actual - predicted) ** 2)))


def wape(actual, predicted):
	"""sum(|actual - predicted|) / sum(|actual|) * 100; None when the denominator is zero."""
	actual, predicted = _arrays(actual, predicted)
	denominator = np.abs(actual).sum()
	if denominator == 0:
		return None
	return float(np.abs(actual - predicted).sum() / denominator * 100)


def r2(actual, predicted):
	"""Coefficient of determination; None when the actual values are constant."""
	actual, predicted = _arrays(actual, predicted)
	total = np.sum((actual - actual.mean()) ** 2)
	if total == 0:
		return None
	return float(1 - np.sum((actual - predicted) ** 2) / total)


def forecast_metrics(actual, predicted):
	return {
		"mae": mae(actual, predicted),
		"rmse": rmse(actual, predicted),
		"wape": wape(actual, predicted),
		"r2": r2(actual, predicted),
		"n_observations": int(np.asarray(actual).size),
	}


def improvement(baseline, model):
	"""Absolute and percentage error reduction of model versus baseline (positive = better)."""
	result = {}
	for name in ("mae", "rmse", "wape"):
		before, after = baseline.get(name), model.get(name)
		if before is None or after is None:
			result[name] = {"absolute_reduction": None, "percent_reduction": None}
			continue
		result[name] = {
			"absolute_reduction": before - after,
			"percent_reduction": (before - after) / before * 100 if before else None,
		}
	return result
