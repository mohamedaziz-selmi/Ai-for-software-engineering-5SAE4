"""Sales Forecasting pipeline: explore -> clean -> features -> baselines -> Random Forest -> evaluation.

Run from module5_business_intelligence/:
    ..\\rag_service\\.venv\\Scripts\\python.exe -m src.pipeline_sales [--skip-advanced]
"""

import argparse
import time

import joblib
import numpy as np
import pandas as pd

from . import figures, sales_advanced, sales_model
from .common import environment_versions, update_report, utc_now, write_json
from .config import (
	ADVANCED_MIN_LAG, ADVANCED_TRAIN_START, DATA_REPORTS_DIR, MODELS_DIR, MULTISTEP_BLOCK_DAYS,
	PROCESSED_DIR, RANDOM_SEED, REPORTS_DIR, SALES_MAX_HORIZON, SALES_SPLITS, STORE_SALES_FILES, ensure_dirs,
)
from .manifest import dataset_version
from .metrics import forecast_metrics, improvement
from .sales_data import calendar_table, clean, explore, load_raw
from .sales_features import CALENDAR_FLAG_COLUMNS, FEATURE_COLUMNS, FEATURE_DICTIONARY, TARGET, build_features, chronological_split


def log(message):
	print(f"[sales {time.strftime('%H:%M:%S')}] {message}", flush=True)


def period_info(frame):
	return {"start": frame.index.min().date().isoformat(), "end": frame.index.max().date().isoformat(), "n_days": int(len(frame))}


def series_points(dates, **columns):
	return [{"date": pd.Timestamp(day).date().isoformat(), **{name: (None if pd.isna(values[i]) else float(values[i])) for name, values in columns.items()}} for i, day in enumerate(dates)]


def run_exploration_and_cleaning():
	frames = load_raw()
	log(f"Loaded raw files: { {name: len(frame) for name, frame in frames.items()} }")
	exploration = explore(frames)
	cleaned, daily, cleaning = clean(frames)

	daily_series = daily.set_index("date")["sales"]
	exploration["figures"] = [
		figures.line("sales_daily_total.png", daily_series.index, [("daily sales", daily_series.values, figures.ACCENT)], "Store Sales: total daily sales (all stores and families)", "sales"),
		figures.hist("sales_daily_distribution.png", daily_series.values, "Distribution of daily total sales", "daily sales"),
		figures.bars("sales_by_weekday.png", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], daily_series.groupby(daily_series.index.dayofweek).mean().values, "Mean daily sales by weekday", "mean sales"),
	]
	exploration["created_at"] = utc_now()
	write_json(DATA_REPORTS_DIR / "sales_exploration_report.json", exploration)
	update_report(DATA_REPORTS_DIR / "cleaning_report.json", "sales_forecasting", cleaning)
	return frames, cleaned, daily, exploration, cleaning


def data_quality_section(frames, cleaned, daily, exploration):
	train_raw, train_clean = frames["train"], cleaned["train"]
	return {
		"dataset": "Store Sales - Time Series Forecasting",
		"status": "pass",
		"checks": [
			{"check": "schema", "result": "pass", "detail": "All six files contain the expected columns and parse with the %Y-%m-%d date format."},
			{"check": "duplicate_business_keys", "result": "pass" if exploration["files"]["train"]["duplicate_business_keys"] == 0 else "fail", "detail": f"{exploration['files']['train']['duplicate_business_keys']} duplicate (date, store_nbr, family) keys."},
			{"check": "negative_sales", "result": "pass" if exploration["train_sales"]["negative_sales_rows"] == 0 else "warn", "detail": f"{exploration['train_sales']['negative_sales_rows']} negative sales rows."},
			{"check": "missing_dates", "result": "warn", "detail": f"{exploration['files']['train']['date_coverage']['missing_dates_count']} dates absent for all stores (25 December closures)."},
			{"check": "oil_missing", "result": "warn", "detail": f"{exploration['files']['oil']['missing']['dcoilwtico']['missing']} missing oil prices, forward-filled only."},
		],
		"before": {"rows": int(len(train_raw)), "missing_values": int(train_raw.isna().sum().sum()), "duplicate_rows": int(train_raw.duplicated().sum())},
		"after": {"rows": int(len(train_clean)), "missing_values": int(train_clean.isna().sum().sum()), "duplicate_rows": int(train_clean.duplicated().sum()), "daily_rows": int(len(daily))},
	}


def run_basic_model(daily, calendar):
	features = build_features(daily, calendar_flags=calendar)
	usable = features.dropna(subset=FEATURE_COLUMNS)
	dropped_warmup = len(features) - len(usable)
	parts = chronological_split(usable, SALES_SPLITS)
	train, validation, test = parts["train"], parts["validation"], parts["test"]
	log(f"Split sizes: train={len(train)} validation={len(validation)} test={len(test)}")

	log("Tuning Random Forest with rolling-origin CV on the training period")
	best_params, tuning = sales_model.tune(train, RANDOM_SEED)
	log(f"Best params: {best_params}")

	model = sales_model.make_model(best_params, RANDOM_SEED).fit(train[FEATURE_COLUMNS], train[TARGET])
	val_actual, val_preds, val_metrics = sales_model.evaluate_period(model, validation, train[TARGET])

	train_val = pd.concat([train, validation])
	final_model = sales_model.make_model(best_params, RANDOM_SEED).fit(train_val[FEATURE_COLUMNS], train_val[TARGET])
	test_actual, test_preds, test_metrics = sales_model.evaluate_period(final_model, test, train_val[TARGET])
	log(f"Validation RF MAE={val_metrics['random_forest']['mae']:.0f} vs naive {val_metrics['seasonal_naive']['mae']:.0f}; test RF MAE={test_metrics['random_forest']['mae']:.0f} vs naive {test_metrics['seasonal_naive']['mae']:.0f}")

	daily_sales = daily.set_index("date")["sales"]
	ms_frame, ms_metrics, ms_by_horizon = sales_model.multistep_evaluation(final_model, daily_sales, *SALES_SPLITS["test"], MULTISTEP_BLOCK_DAYS, calendar)
	importances = sales_model.feature_importances(model, validation, RANDOM_SEED)

	def section(period, actual, preds, metrics, fit_period):
		return {
			"period": period_info(period),
			"fit_period": fit_period,
			"metrics": metrics,
			"improvement_vs_seasonal_naive": improvement(metrics["seasonal_naive"], metrics["random_forest"]),
			"improvement_vs_historical_mean": improvement(metrics["historical_mean"], metrics["random_forest"]),
			"series": series_points(period.index, actual=actual, seasonal_naive=preds["seasonal_naive"], random_forest=preds["random_forest"]),
			"residuals": {name: sales_model.residual_histogram(actual, preds[name]) for name in ("seasonal_naive", "random_forest")},
			"error_breakdown": {name: sales_model.error_breakdown(period.index, actual, preds[name]) for name in ("seasonal_naive", "random_forest")},
		}

	evaluation = {
		"created_at": utc_now(),
		"target": "Total daily unit sales across all stores and product families (sum of train.csv 'sales').",
		"protocol": (
			"Chronological split, no shuffling. Hyperparameters chosen by rolling-origin CV inside the training period. "
			"Validation: model fit on the training period only. Test: untouched final period, model refit on training + validation. "
			"All models are scored on exactly the same dates and target. One-step-ahead rows use actual sales up to the previous day; "
			"the multi-step section forecasts recursively in 16-day blocks without any actuals after each block origin."
		),
		"metric_definitions": {
			"mae": "mean(|actual - predicted|), in units sold",
			"rmse": "sqrt(mean((actual - predicted)^2)), in units sold",
			"wape": "sum(|actual - predicted|) / sum(|actual|) * 100; null when sum(|actual|) = 0",
			"r2": "1 - SSE/SST, descriptive only",
		},
		"baselines": {
			"seasonal_naive": "prediction(t) = actual_sales(t - 7 days)",
			"historical_mean": "mean daily sales of the fitting period",
		},
		"warmup_rows_dropped": int(dropped_warmup),
		"validation": section(validation, val_actual, val_preds, val_metrics, period_info(train)),
		"test": section(test, test_actual, test_preds, test_metrics, period_info(train_val)),
		"multistep_test": {
			"description": f"Rolling-origin recursive forecasts in blocks of {MULTISTEP_BLOCK_DAYS} days over the test period; seasonal naive repeats the last observed week.",
			"metrics": ms_metrics,
			"improvement_vs_seasonal_naive": improvement(ms_metrics["seasonal_naive"], ms_metrics["random_forest"]),
			"mae_by_horizon": ms_by_horizon,
			"series": series_points(ms_frame["date"], actual=ms_frame["actual"].to_numpy(), seasonal_naive=ms_frame["seasonal_naive"].to_numpy(), random_forest=ms_frame["random_forest"].to_numpy()),
		},
		"feature_importance": {"source": "validation period, model fit on training period", "features": importances},
	}
	evaluation["figures"] = [
		figures.line("sales_validation_actual_vs_predicted.png", validation.index, [("actual", val_actual, figures.INK), ("seasonal naive", val_preds["seasonal_naive"], figures.SECOND), ("random forest", val_preds["random_forest"], figures.ACCENT)], "Validation: actual vs predicted daily sales", "sales"),
		figures.line("sales_test_actual_vs_predicted.png", test.index, [("actual", test_actual, figures.INK), ("seasonal naive", test_preds["seasonal_naive"], figures.SECOND), ("random forest", test_preds["random_forest"], figures.ACCENT)], "Test: actual vs predicted daily sales", "sales"),
		figures.hist("sales_test_residuals_rf.png", test_actual - test_preds["random_forest"], "Test residuals (actual - Random Forest)", "residual", bins=25),
	]

	tuning_out = {"best_params": best_params, **tuning}
	return final_model, best_params, evaluation, tuning_out, features, {"train": train, "validation": validation, "test": test, "train_val": train_val}


def run_advanced_model(cleaned, basic_ms, export_features=False):
	log("Building advanced store x family panel")
	train, test, stores = cleaned["train"], cleaned["test"], cleaned["stores"]
	maps = sales_advanced.category_maps(train, stores)
	panel = sales_advanced.build_panel(train, test, stores, cleaned["holidays_events"], cleaned["oil_daily"], maps, ADVANCED_TRAIN_START)
	labelled = panel[panel["sales"].notna()]
	parts = {name: labelled[(labelled["date"] >= pd.Timestamp(a)) & (labelled["date"] <= pd.Timestamp(b))] for name, (a, b) in SALES_SPLITS.items()}
	log(f"Advanced rows: train={len(parts['train'])} validation={len(parts['validation'])} test={len(parts['test'])}")

	if export_features:
		# ~30 MB gzipped; only for inspection, nothing downstream reads it.
		export_columns = ["date", "store_nbr", "family", "sales"] + sales_advanced.FEATURES
		panel[export_columns].to_csv(PROCESSED_DIR / "store_sales_features.csv.gz", index=False, float_format="%.4f", compression="gzip")

	model = sales_advanced.fit(sales_advanced.make_model(RANDOM_SEED), parts["train"])
	val_pred = sales_advanced.predict(model, parts["validation"])
	val_daily = parts["validation"].assign(pred=val_pred).groupby("date")[["sales", "pred"]].sum()

	final = sales_advanced.fit(sales_advanced.make_model(RANDOM_SEED), pd.concat([parts["train"], parts["validation"]]))
	test_rows = parts["test"].assign(advanced=sales_advanced.predict(final, parts["test"]))
	test_daily = test_rows.groupby("date")[["sales", "advanced"]].sum()

	naive_rows = sales_advanced.series_seasonal_naive(panel[panel["sales"].notna()], *SALES_SPLITS["test"], MULTISTEP_BLOCK_DAYS)
	test_rows = test_rows.merge(naive_rows, on=["store_nbr", "family", "date"], how="left")

	basic = pd.DataFrame(basic_ms["series"]).assign(date=lambda f: pd.to_datetime(f["date"])).set_index("date")
	aligned = test_daily.join(basic[["random_forest", "seasonal_naive"]], how="inner")
	comparison = {name: forecast_metrics(aligned["sales"], aligned[name]) for name in ("advanced", "random_forest", "seasonal_naive")}

	future = panel[panel["sales"].isna()].copy()
	future["forecast"] = sales_advanced.predict(final, future)
	future[["date", "store_nbr", "family", "onpromotion", "forecast"]].to_csv(MODELS_DIR / "sales_advanced_future_forecast.csv", index=False, float_format="%.3f")
	joblib.dump({"model": final, "features": sales_advanced.FEATURES, "category_maps": maps}, MODELS_DIR / "sales_advanced_model.joblib")

	return {
		"created_at": utc_now(),
		"model": "HistGradientBoostingRegressor on log1p(sales), one row per store x family x day",
		"strategy": f"Direct multi-step: every history feature lagged >= {ADVANCED_MIN_LAG} days, so forecasts up to {ADVANCED_MIN_LAG} days ahead never use actuals after the origin.",
		"features": sales_advanced.FEATURES,
		"feature_notes": sales_advanced.FEATURE_NOTES,
		"excluded_features": {"transactions": "Not known for future dates.", "id": "Row identifier."},
		"training_rows": int(len(parts["train"])),
		"training_start": ADVANCED_TRAIN_START,
		"validation_daily_total_metrics": forecast_metrics(val_daily["sales"], val_daily["pred"]),
		"test_series_level_metrics": {
			"advanced": forecast_metrics(test_rows["sales"], test_rows["advanced"]),
			"seasonal_naive_per_series": forecast_metrics(test_rows["sales"], test_rows["seasonal_naive"]),
		},
		"test_daily_total_comparison": {
			"description": "Advanced predictions summed per day vs the basic Random Forest and seasonal naive, all as multi-step forecasts over the same 16-day test blocks.",
			"metrics": comparison,
			"n_days": int(len(aligned)),
		},
		"future_forecast_period": {"start": future["date"].min().date().isoformat(), "end": future["date"].max().date().isoformat(), "rows": int(len(future))},
		"stores": sorted(int(s) for s in maps["store"]),
		"families": sorted(maps["family"]),
	}


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--skip-advanced", action="store_true")
	parser.add_argument("--export-features", action="store_true", help="Also write the store x family feature panel (data/processed/store_sales_features.csv.gz).")
	args = parser.parse_args()
	ensure_dirs()
	started = time.time()

	frames, cleaned, daily, exploration, cleaning = run_exploration_and_cleaning()
	update_report(DATA_REPORTS_DIR / "data_quality_report.json", "sales_forecasting", data_quality_section(frames, cleaned, daily, exploration))

	last_calendar_day = frames["holidays_events"]["date"].max()
	calendar = calendar_table(frames["holidays_events"], daily["date"].min(), last_calendar_day, closure_dates=daily.loc[daily["is_closure_day"] == 1, "date"])
	calendar.to_csv(PROCESSED_DIR / "sales_calendar.csv")

	model, params, evaluation, tuning, features, parts = run_basic_model(daily, calendar)
	daily_out = daily.set_index("date")
	daily_out.join(features[[c for c in FEATURE_COLUMNS if c not in daily_out.columns]]).to_csv(PROCESSED_DIR / "daily_sales.csv", float_format="%.4f")

	update_report(DATA_REPORTS_DIR / "transformation_report.json", "sales_forecasting", {
		"input": "data/processed after cleaning: one row per calendar day",
		"aggregation": "daily_sales = sum(sales over all stores and product families for each date)",
		"closure_days": "25 December inserted with sales = 0 and is_closure_day = 1 (verified absent for every store).",
		"leakage_controls": [
			"lag_k = sales.shift(k) with k >= 1",
			"rolling statistics computed on sales.shift(1), so day t is never included",
			"no future actuals: multi-step forecasts feed predictions back recursively",
			"transactions and row id excluded; oil and promotions only in the advanced model (lagged / known in advance)",
		],
		"warmup_rows_without_full_lags": evaluation["warmup_rows_dropped"],
		"feature_dictionary": [{"feature": name, "dtype": kind, "transformation": how, "purpose": why} for name, (kind, how, why) in FEATURE_DICTIONARY.items()],
		"output": "data/processed/daily_sales.csv",
	})

	future = sales_model.recursive_forecast(model, daily.set_index("date")["sales"], SALES_MAX_HORIZON, calendar)
	advanced = None
	if not args.skip_advanced:
		advanced = run_advanced_model(cleaned, evaluation["multistep_test"], export_features=args.export_features)
		write_json(MODELS_DIR / "sales_advanced_evaluation.json", advanced)

	evaluation["advanced_model_available"] = advanced is not None
	evaluation["future_forecast"] = {"origin": daily["date"].max().date().isoformat(), "horizon_days": SALES_MAX_HORIZON, "method": "recursive Random Forest", "series": series_points(future.index, forecast=future.to_numpy())}

	joblib.dump(model, MODELS_DIR / "sales_forecast_model.joblib")
	write_json(MODELS_DIR / "sales_feature_config.json", {
		"feature_columns": FEATURE_COLUMNS,
		"target": TARGET,
		"calendar_flag_columns": CALENDAR_FLAG_COLUMNS,
		"calendar_file": "data/processed/sales_calendar.csv",
		"history_file": "data/processed/daily_sales.csv",
		"calendar_known_until": last_calendar_day.date().isoformat(),
		"max_horizon_days": SALES_MAX_HORIZON,
		"lags": [int(c.split("_")[1]) for c in FEATURE_COLUMNS if c.startswith("lag_")],
	})
	write_json(MODELS_DIR / "sales_evaluation.json", evaluation)
	write_json(MODELS_DIR / "sales_training_metadata.json", {
		"model": "RandomForestRegressor",
		"trained_at": utc_now(),
		"dataset": dataset_version("store_sales", [STORE_SALES_FILES["train"], STORE_SALES_FILES["holidays_events"]]),
		"hyperparameters": {**sales_model.FIXED_PARAMS, **params, "random_state": RANDOM_SEED},
		"random_seed": RANDOM_SEED,
		"periods": {name: {"start": a, "end": b} for name, (a, b) in SALES_SPLITS.items()},
		"fit_periods": {"validation_model": period_info(parts["train"]), "final_model": period_info(parts["train_val"])},
		"tuning": tuning,
		"environment": environment_versions(),
		"runtime_seconds": round(time.time() - started, 1),
		"command": "..\\rag_service\\.venv\\Scripts\\python.exe -m src.pipeline_sales",
	})
	write_sales_markdown(evaluation, advanced)
	log(f"Done in {time.time() - started:.0f}s")


def fmt(value, digits=0):
	return "n/a" if value is None else f"{value:,.{digits}f}"


def write_sales_markdown(evaluation, advanced):
	lines = ["# Sales Forecasting — evaluation report", "", f"Generated {evaluation['created_at']} by `python -m src.pipeline_sales`. All numbers are measured, not estimated.", "", f"Target: {evaluation['target']}", "", evaluation["protocol"], ""]
	for key, title in (("validation", "Validation"), ("test", "Test (untouched)")):
		section = evaluation[key]
		lines += [f"## {title}: {section['period']['start']} → {section['period']['end']} ({section['period']['n_days']} days, fit on {section['fit_period']['start']} → {section['fit_period']['end']})", "", "| Model | MAE | RMSE | WAPE % | R² |", "|---|---|---|---|---|"]
		for name, label in (("historical_mean", "Historical mean (baseline)"), ("seasonal_naive", "Seasonal naive t-7 (baseline)"), ("random_forest", "Random Forest")):
			m = section["metrics"][name]
			lines.append(f"| {label} | {fmt(m['mae'])} | {fmt(m['rmse'])} | {fmt(m['wape'], 2)} | {fmt(m['r2'], 3)} |")
		imp = section["improvement_vs_seasonal_naive"]
		lines += ["", f"Random Forest vs seasonal naive: MAE {fmt(imp['mae']['absolute_reduction'])} ({fmt(imp['mae']['percent_reduction'], 1)} %), RMSE {fmt(imp['rmse']['absolute_reduction'])} ({fmt(imp['rmse']['percent_reduction'], 1)} %), WAPE {fmt(imp['wape']['absolute_reduction'], 2)} points ({fmt(imp['wape']['percent_reduction'], 1)} %). Positive = lower error than baseline.", ""]
	ms = evaluation["multistep_test"]
	lines += ["## Multi-step (recursive, 16-day blocks) on the test period", "", ms["description"], "", "| Model | MAE | RMSE | WAPE % |", "|---|---|---|---|"]
	for name in ("seasonal_naive", "random_forest"):
		m = ms["metrics"][name]
		lines.append(f"| {name} | {fmt(m['mae'])} | {fmt(m['rmse'])} | {fmt(m['wape'], 2)} |")
	lines += ["", "## Top features (permutation importance on validation)", ""]
	for row in evaluation["feature_importance"]["features"][:8]:
		lines.append(f"- `{row['feature']}`: MAE increase {fmt(row['permutation_mae_increase'])} when shuffled")
	if advanced:
		lines += ["", "## Advanced store × family model", "", advanced["strategy"], "", "| Model (daily totals, multi-step test blocks) | MAE | RMSE | WAPE % |", "|---|---|---|---|"]
		for name, m in advanced["test_daily_total_comparison"]["metrics"].items():
			lines.append(f"| {name} | {fmt(m['mae'])} | {fmt(m['rmse'])} | {fmt(m['wape'], 2)} |")
		s = advanced["test_series_level_metrics"]
		lines += ["", f"Series level (store × family × day) test WAPE: advanced {fmt(s['advanced']['wape'], 2)} % vs per-series seasonal naive {fmt(s['seasonal_naive_per_series']['wape'], 2)} %."]
	lines += ["", "Figures: " + ", ".join(f"`{p}`" for p in evaluation["figures"])]
	(REPORTS_DIR / "sales_evaluation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
	main()
