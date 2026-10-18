"""Loading, schema validation, exploration, and cleaning of the Store Sales dataset."""

import numpy as np
import pandas as pd

from .common import StepLog, describe_series, histogram, missing_summary
from .config import STORE_SALES_FILES

SCHEMAS = {
	"train": {"id": "int", "date": "date", "store_nbr": "int", "family": "str", "sales": "float", "onpromotion": "int"},
	"test": {"id": "int", "date": "date", "store_nbr": "int", "family": "str", "onpromotion": "int"},
	"stores": {"store_nbr": "int", "city": "str", "state": "str", "type": "str", "cluster": "int"},
	"transactions": {"date": "date", "store_nbr": "int", "transactions": "int"},
	"oil": {"date": "date", "dcoilwtico": "float"},
	"holidays_events": {
		"date": "date", "type": "str", "locale": "str", "locale_name": "str",
		"description": "str", "transferred": "bool",
	},
}
BUSINESS_KEYS = {
	"train": ["date", "store_nbr", "family"],
	"test": ["date", "store_nbr", "family"],
	"stores": ["store_nbr"],
	"transactions": ["date", "store_nbr"],
	"oil": ["date"],
	"holidays_events": ["date", "type", "locale_name", "description"],
}
DATE_FORMAT = "%Y-%m-%d"
HOLIDAY_DAY_TYPES = {"Holiday", "Transfer", "Additional", "Bridge"}


class SchemaError(ValueError):
	pass


class MissingDatasetError(FileNotFoundError):
	pass


def validate_schema(frame, name):
	"""Raise SchemaError when required columns are missing or cannot be coerced."""
	expected = SCHEMAS[name]
	missing = [column for column in expected if column not in frame.columns]
	if missing:
		raise SchemaError(f"{name}: missing required columns {missing}.")
	problems = []
	for column, kind in expected.items():
		values = frame[column]
		if kind in ("int", "float"):
			coerced = pd.to_numeric(values, errors="coerce")
			bad = int(coerced.isna().sum() - values.isna().sum())
			if bad:
				problems.append(f"{column}: {bad} non-numeric values")
		elif kind == "date":
			parsed = pd.to_datetime(values, format=DATE_FORMAT, errors="coerce")
			bad = int(parsed.isna().sum() - values.isna().sum())
			if bad:
				problems.append(f"{column}: {bad} values not in {DATE_FORMAT} format")
	if problems:
		raise SchemaError(f"{name}: " + "; ".join(problems))
	return True


def parse_dates(frame, column="date"):
	frame = frame.copy()
	frame[column] = pd.to_datetime(frame[column], format=DATE_FORMAT, errors="raise")
	return frame


def load_raw(files=None):
	files = files or STORE_SALES_FILES
	missing = [str(path) for path in files.values() if not path.exists()]
	if missing:
		raise MissingDatasetError(
			"Store Sales files are missing: " + ", ".join(missing)
			+ ". Download them from https://www.kaggle.com/competitions/store-sales-time-series-forecasting/data"
			" and place them in Rayen/Sales Forecasting/Dataset/."
		)
	frames = {}
	for name, path in files.items():
		frame = pd.read_csv(path)
		validate_schema(frame, name)
		if "date" in frame.columns:
			frame = parse_dates(frame)
		if name == "holidays_events":
			frame["transferred"] = frame["transferred"].astype(str).str.lower().eq("true")
		frames[name] = frame
	return frames


def _date_coverage(frame):
	if "date" not in frame.columns:
		return None
	dates = frame["date"].drop_duplicates().sort_values()
	full = pd.date_range(dates.min(), dates.max(), freq="D")
	missing = full.difference(pd.DatetimeIndex(dates))
	return {
		"start": dates.min().strftime(DATE_FORMAT),
		"end": dates.max().strftime(DATE_FORMAT),
		"distinct_dates": int(dates.size),
		"calendar_days": int(full.size),
		"missing_dates_count": int(missing.size),
		"missing_dates": [day.strftime(DATE_FORMAT) for day in missing[:60]],
	}


def explore(frames):
	"""Initial exploration of every Store Sales file before any preprocessing."""
	report = {"files": {}}
	for name, frame in frames.items():
		keys = BUSINESS_KEYS[name]
		entry = {
			"rows": int(len(frame)),
			"columns": int(frame.shape[1]),
			"dtypes": {column: str(dtype) for column, dtype in frame.dtypes.items()},
			"missing": missing_summary(frame),
			"duplicate_rows": int(frame.duplicated().sum()),
			"business_key": keys,
			"duplicate_business_keys": int(frame.duplicated(keys).sum()),
			"date_coverage": _date_coverage(frame),
		}
		report["files"][name] = entry

	train = frames["train"]
	stores = frames["stores"]
	sales = train["sales"]
	daily = train.groupby("date")["sales"].sum()
	q1, q3 = daily.quantile([0.25, 0.75])
	iqr = q3 - q1
	unusual_daily = daily[(daily < q1 - 1.5 * iqr) | (daily > q3 + 1.5 * iqr)]
	panel_per_date = train.groupby("date").size()

	report["train_sales"] = {
		"row_level": describe_series(sales),
		"daily_total": describe_series(daily),
		"negative_sales_rows": int((sales < 0).sum()),
		"zero_sales_rows": int((sales == 0).sum()),
		"zero_sales_pct": float((sales == 0).mean() * 100),
		"non_integer_sales_rows": int((sales % 1 != 0).sum()),
		"unusual_daily_totals_iqr": {
			"rule": "daily total outside [Q1 - 1.5*IQR, Q3 + 1.5*IQR]",
			"count": int(unusual_daily.size),
			"dates": {day.strftime(DATE_FORMAT): float(value) for day, value in unusual_daily.sort_values().items()},
		},
		"rows_per_date": {"min": int(panel_per_date.min()), "max": int(panel_per_date.max())},
		"n_stores_in_train": int(train["store_nbr"].nunique()),
		"n_stores_in_stores_file": int(stores["store_nbr"].nunique()),
		"n_product_families": int(train["family"].nunique()),
		"product_families": sorted(train["family"].unique().tolist()),
		"daily_total_histogram": histogram(daily, bins=30),
	}

	tx = frames["transactions"].groupby("date")["transactions"].sum()
	promo = train.groupby("date")["onpromotion"].sum()
	oil = frames["oil"].set_index("date")["dcoilwtico"]
	joined = pd.concat({"daily_sales": daily, "transactions": tx, "onpromotion": promo, "oil": oil, "id_mean": train.groupby("date")["id"].mean()}, axis=1).dropna()
	report["correlations_with_daily_sales"] = {
		column: float(joined["daily_sales"].corr(joined[column])) for column in joined.columns if column != "daily_sales"
	}
	report["leakage_review"] = [
		{"column": "id", "risk": "high", "decision": "excluded", "reason": "Row identifier increases monotonically with date; it encodes time position rather than demand."},
		{"column": "transactions", "risk": "high", "decision": "excluded from features", "reason": "Same-day transaction counts are only known after the day ends and are not available for future dates in test.csv."},
		{"column": "sales (same day)", "risk": "target", "decision": "used only through lags >= 1 day", "reason": "Target column."},
		{"column": "onpromotion", "risk": "low", "decision": "advanced model only", "reason": "Promotions are planned in advance and supplied for future dates in test.csv."},
		{"column": "dcoilwtico", "risk": "medium", "decision": "advanced model only, lagged", "reason": "Future oil prices are unknown; only lagged, forward-filled values are used."},
	]
	return report


def _holiday_flags(holidays):
	national = holidays[holidays["locale"] == "National"]
	holiday_days = national[national["type"].isin(HOLIDAY_DAY_TYPES) & ~national["transferred"]]
	return {
		"national_holiday": set(holiday_days["date"]),
		"national_event": set(national.loc[national["type"] == "Event", "date"]),
		"work_day": set(national.loc[national["type"] == "Work Day", "date"]),
	}


def calendar_table(holidays, start, end, closure_dates=()):
	"""Holiday-schedule flags per calendar day; valid for future dates because the schedule is published ahead."""
	dates = pd.date_range(start, end, freq="D")
	flags = _holiday_flags(holidays)
	table = pd.DataFrame(index=pd.DatetimeIndex(dates, name="date"))
	christmas = (dates.month == 12) & (dates.day == 25)
	table["is_closure_day"] = (christmas | dates.isin(pd.DatetimeIndex(closure_dates))).astype(int)
	for name, days in flags.items():
		table[f"is_{name}"] = dates.isin(pd.DatetimeIndex(sorted(days))).astype(int)
	return table


def clean(frames):
	"""Apply documented cleaning policies. Returns cleaned frames and a cleaning report."""
	log = StepLog()
	train = frames["train"].copy()
	stores = frames["stores"].copy()

	before = len(train)
	exact_dupes = train.duplicated()
	train = train[~exact_dupes]
	log.record("drop_exact_duplicates", before, len(train), "Identical rows add no information.", policy="Remove exact duplicate rows only after counting them.")

	before = len(train)
	key_dupes = train[train.duplicated(BUSINESS_KEYS["train"], keep=False)]
	log.record(
		"check_business_key_duplicates", before, len(train),
		"Investigation only: conflicting rows for the same (date, store_nbr, family) would be reported, not silently dropped.",
		duplicate_key_rows=int(len(key_dupes)),
	)
	if len(key_dupes):
		raise SchemaError(f"train: {len(key_dupes)} rows share a business key with different values; investigate before continuing.")

	before = len(train)
	train["sales"] = pd.to_numeric(train["sales"], errors="coerce")
	invalid = ~np.isfinite(train["sales"])
	train = train[~invalid]
	log.record("drop_invalid_sales", before, len(train), "Sales must be a finite number.", invalid_rows=int(invalid.sum()))

	negative = int((train["sales"] < 0).sum())
	log.record(
		"inspect_negative_sales", len(train), len(train),
		"Negative sales would represent returns; the forecasting target is gross demand, so negatives would be clipped to zero.",
		policy="Clip negative sales to 0 and report them.", negative_rows=negative,
	)
	train["sales"] = train["sales"].clip(lower=0)

	known_stores = set(stores["store_nbr"])
	before = len(train)
	unknown_store = ~train["store_nbr"].isin(known_stores)
	train = train[~unknown_store]
	log.record("validate_store_ids", before, len(train), "Every store must exist in stores.csv.", unknown_store_rows=int(unknown_store.sum()))

	families = sorted(train["family"].unique())
	before = len(train)
	blank_family = train["family"].isna() | train["family"].astype(str).str.strip().eq("")
	train = train[~blank_family]
	log.record("validate_product_families", before, len(train), "Product family must be a non-empty label.", blank_family_rows=int(blank_family.sum()), n_families=len(families))

	# Distinguish genuine zero sales from absent observations.
	series_totals = train.groupby(["store_nbr", "family"])["sales"].sum()
	never_sold = series_totals[series_totals == 0]
	first_sale = train[train["sales"] > 0].groupby("store_nbr")["date"].min()
	start = train["date"].min()
	late_openings = first_sale[first_sale > start + pd.Timedelta(days=7)]
	all_dates = pd.date_range(train["date"].min(), train["date"].max(), freq="D")
	missing_dates = all_dates.difference(pd.DatetimeIndex(train["date"].unique()))
	zero_analysis = {
		"zero_sales_rows": int((train["sales"] == 0).sum()),
		"store_family_series_never_sold": int(never_sold.size),
		"stores_opening_after_start": {str(store): day.strftime(DATE_FORMAT) for store, day in late_openings.items()},
		"dates_absent_from_all_stores": [day.strftime(DATE_FORMAT) for day in missing_dates],
		"interpretation": (
			"Recorded zeros are genuine zero sales: the panel is complete for every recorded date, zeros cluster in "
			"store/family series that are never sold and in stores before their opening date. Dates absent for every "
			"store are 25 December, when stores are closed; they are treated as closure days with zero sales, not as "
			"data gaps to interpolate."
		),
	}

	daily = train.groupby("date").agg(sales=("sales", "sum"), onpromotion_total=("onpromotion", "sum"), panel_rows=("sales", "size")).reset_index()
	stores_open = train[train["sales"] > 0].groupby("date")["store_nbr"].nunique()
	daily["stores_with_sales"] = daily["date"].map(stores_open).fillna(0).astype(int)
	before = len(daily)
	daily = daily.set_index("date").reindex(all_dates).rename_axis("date").reset_index()
	daily["is_closure_day"] = daily["sales"].isna().astype(int)
	daily[["sales", "onpromotion_total", "panel_rows", "stores_with_sales"]] = daily[["sales", "onpromotion_total", "panel_rows", "stores_with_sales"]].fillna(0)
	log.record(
		"insert_closure_days", before, len(daily),
		"Calendar dates missing for every store (25 December) are inserted with zero sales and is_closure_day = 1.",
		policy="Insert closure days explicitly so lag features keep a regular daily frequency.", inserted=int(len(daily) - before),
	)

	oil = frames["oil"].set_index("date")["dcoilwtico"].reindex(all_dates.union(pd.DatetimeIndex(frames["test"]["date"].unique())))
	oil_missing_before = int(oil.isna().sum())
	oil = oil.ffill()
	oil_policy = {
		"policy": "Reindex to calendar days, forward-fill only (never backward-fill) so each day uses the latest past price.",
		"missing_before": oil_missing_before,
		"missing_after": int(oil.isna().sum()),
		"leading_missing_kept_as_nan": oil.index[oil.isna()].strftime(DATE_FORMAT).tolist(),
	}
	daily["oil_price_ffill"] = daily["date"].map(oil)

	calendar = calendar_table(frames["holidays_events"], all_dates.min(), all_dates.max(), closure_dates=missing_dates)
	daily = daily.drop(columns="is_closure_day").merge(calendar.reset_index(), on="date", how="left")

	tx = frames["transactions"].groupby("date")["transactions"].sum()
	daily["transactions_total"] = daily["date"].map(tx)

	q1, q3 = daily["sales"].quantile([0.25, 0.75])
	iqr = q3 - q1
	daily["is_outlier_iqr"] = ((daily["sales"] < q1 - 1.5 * iqr) | (daily["sales"] > q3 + 1.5 * iqr)).astype(int)
	log.record(
		"flag_outliers", len(daily), len(daily),
		"Unusual daily totals are flagged, never deleted: low totals are New Year's Day and closures, high totals are genuine demand spikes.",
		flagged_days=int(daily["is_outlier_iqr"].sum()),
	)

	report = {
		"dataset": "Store Sales - Time Series Forecasting",
		"steps": log.steps,
		"zero_sales_analysis": zero_analysis,
		"oil_missing_values": oil_policy,
		"holiday_policy": (
			"National holidays: types Holiday/Transfer/Additional/Bridge with locale National and transferred = False. "
			"Holidays marked transferred=True are moved to their Transfer date and are not treated as days off. "
			"Holiday calendars are published in advance, so they are valid inputs for future dates."
		),
		"transactions_policy": "Daily transaction totals are kept for reporting only; they are not available at prediction time.",
		"raw_rows": int(len(frames["train"])),
		"clean_rows": int(len(train)),
		"daily_rows": int(len(daily)),
	}
	cleaned = dict(frames)
	cleaned["train"] = train
	cleaned["oil_daily"] = oil
	return cleaned, daily, report
