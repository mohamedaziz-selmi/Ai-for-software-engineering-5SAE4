import joblib
import numpy as np
import pandas as pd
import pytest

from src.metrics import forecast_metrics, improvement, mae, r2, rmse, wape
from src.sales_data import SchemaError, calendar_table, clean, parse_dates, validate_schema
from src.sales_features import FEATURE_COLUMNS, build_features, chronological_split, features_for_next_day
from src.sales_model import make_model, recursive_forecast, seasonal_naive, seasonal_naive_multistep


# --- schema and parsing -------------------------------------------------------------------

def test_schema_validation_rejects_missing_column(store_frames):
	with pytest.raises(SchemaError, match="missing required columns"):
		validate_schema(store_frames["train"].drop(columns="sales"), "train")


def test_schema_validation_rejects_bad_dates_and_numbers(store_frames):
	bad = store_frames["train"].astype({"date": str, "sales": object})
	bad.loc[0, "date"] = "01/02/2020"
	bad.loc[1, "sales"] = "abc"
	with pytest.raises(SchemaError) as error:
		validate_schema(bad, "train")
	assert "date" in str(error.value) and "sales" in str(error.value)


def test_parse_dates_uses_iso_format():
	frame = parse_dates(pd.DataFrame({"date": ["2017-08-15", "2013-01-01"]}))
	assert frame["date"].tolist() == [pd.Timestamp("2017-08-15"), pd.Timestamp("2013-01-01")]
	with pytest.raises(ValueError):
		parse_dates(pd.DataFrame({"date": ["15/08/2017"]}))


# --- cleaning ---------------------------------------------------------------------------

def test_clean_removes_exact_duplicates_and_reports_counts(store_frames):
	frames = dict(store_frames)
	frames["train"] = pd.concat([frames["train"], frames["train"].iloc[[0]]])
	_, _, report = clean(frames)
	step = next(s for s in report["steps"] if s["step"] == "drop_exact_duplicates")
	assert step["rows_removed"] == 1


def test_clean_refuses_conflicting_business_keys(store_frames):
	frames = dict(store_frames)
	conflict = frames["train"].iloc[[0]].assign(sales=999.0, id=1000)
	frames["train"] = pd.concat([frames["train"], conflict])
	with pytest.raises(SchemaError, match="business key"):
		clean(frames)


def test_clean_clips_negative_and_drops_invalid_sales(store_frames):
	frames = dict(store_frames)
	train = frames["train"].copy()
	train.loc[0, "sales"] = -5.0
	train.loc[1, "sales"] = np.inf
	frames["train"] = train
	cleaned, _, report = clean(frames)
	assert (cleaned["train"]["sales"] >= 0).all()
	assert next(s for s in report["steps"] if s["step"] == "drop_invalid_sales")["rows_removed"] == 1
	assert next(s for s in report["steps"] if s["step"] == "inspect_negative_sales")["negative_rows"] == 1


def test_daily_aggregation_inserts_missing_dates_as_closures(store_frames):
	_, daily, _ = clean(store_frames)
	assert daily["date"].tolist() == list(pd.date_range("2020-01-01", "2020-01-04"))
	expected = store_frames["train"].groupby("date")["sales"].sum()
	assert daily.set_index("date").loc[expected.index, "sales"].tolist() == pytest.approx(expected.tolist())
	gap = daily.set_index("date").loc["2020-01-03"]
	assert gap["sales"] == 0 and gap["is_closure_day"] == 1


def test_oil_is_forward_filled_only(store_frames):
	cleaned, daily, report = clean(store_frames)
	oil = cleaned["oil_daily"]
	assert np.isnan(oil.loc["2020-01-01"])  # leading gap is never back-filled with a future price
	assert oil.loc["2020-01-03"] == 50.0
	assert report["oil_missing_values"]["leading_missing_kept_as_nan"] == ["2020-01-01"]


def test_transferred_holidays_are_not_days_off(store_frames):
	table = calendar_table(store_frames["holidays_events"], "2020-01-01", "2020-01-03")
	assert table.loc["2020-01-01", "is_national_holiday"] == 1
	assert table.loc["2020-01-02", "is_national_holiday"] == 0


# --- features and leakage ----------------------------------------------------------------

def test_lag_and_rolling_features_use_only_past_values(daily_frame):
	features = build_features(daily_frame)
	sales = daily_frame.set_index("date")["sales"]
	day = sales.index[60]
	assert features.loc[day, "lag_1"] == sales.iloc[59]
	assert features.loc[day, "lag_28"] == sales.iloc[32]
	assert features.loc[day, "roll_mean_7"] == pytest.approx(sales.iloc[53:60].mean())

	changed = daily_frame.copy()
	changed.loc[60:, "sales"] = 1e9  # perturb day t and every later day
	changed_features = build_features(changed)
	assert changed_features.loc[day, FEATURE_COLUMNS].equals(features.loc[day, FEATURE_COLUMNS])


def test_build_features_rejects_gaps(daily_frame):
	with pytest.raises(ValueError, match="one row per calendar day"):
		build_features(daily_frame.drop(index=10))


def test_next_day_features_match_batch_features(daily_frame):
	features = build_features(daily_frame)
	sales = daily_frame.set_index("date")["sales"]
	day = sales.index[80]
	row = features_for_next_day(sales.loc[:day - pd.Timedelta(days=1)], day)
	pd.testing.assert_series_equal(row.iloc[0], features.loc[day, FEATURE_COLUMNS], check_names=False, check_dtype=False)


def test_chronological_split_is_ordered_and_disjoint(daily_frame):
	frame = build_features(daily_frame)
	parts = chronological_split(frame, {"train": ("2020-01-01", "2020-03-01"), "validation": ("2020-03-02", "2020-03-31"), "test": ("2020-04-01", "2020-04-29")})
	assert parts["train"].index.max() < parts["validation"].index.min() < parts["test"].index.min()
	assert len(parts["train"]) + len(parts["validation"]) + len(parts["test"]) == len(frame)
	with pytest.raises(ValueError, match="overlaps"):
		chronological_split(frame, {"a": ("2020-01-01", "2020-02-01"), "b": ("2020-01-15", "2020-03-01")})


# --- baselines and metrics ----------------------------------------------------------------

def test_seasonal_naive_is_actual_seven_days_earlier(daily_frame):
	features = build_features(daily_frame).dropna()
	sales = daily_frame.set_index("date")["sales"]
	expected = sales.shift(7).loc[features.index].to_numpy()
	assert np.allclose(seasonal_naive(features), expected)


def test_seasonal_naive_multistep_repeats_last_week():
	history = np.arange(1, 15, dtype=float)
	assert seasonal_naive_multistep(history, 9).tolist() == [8, 9, 10, 11, 12, 13, 14, 8, 9]


def test_metric_values():
	actual, predicted = [10, 20, 30], [12, 18, 33]
	assert mae(actual, predicted) == pytest.approx(7 / 3)
	assert rmse(actual, predicted) == pytest.approx(np.sqrt((4 + 4 + 9) / 3))
	assert wape(actual, predicted) == pytest.approx(7 / 60 * 100)
	assert r2(actual, actual) == 1.0


def test_metric_edge_cases():
	assert wape([0, 0], [1, 2]) is None
	assert r2([5, 5], [4, 6]) is None
	with pytest.raises(ValueError):
		mae([1, 2], [1])
	with pytest.raises(ValueError):
		mae([np.nan], [1])


def test_improvement_signs():
	result = improvement({"mae": 100, "rmse": 200, "wape": 10}, {"mae": 60, "rmse": 250, "wape": None})
	assert result["mae"] == {"absolute_reduction": 40, "percent_reduction": 40}
	assert result["rmse"]["absolute_reduction"] == -50
	assert result["wape"]["percent_reduction"] is None


# --- model, recursion, serialization ---------------------------------------------------------

@pytest.fixture
def fitted(daily_frame):
	features = build_features(daily_frame).dropna()
	train = features.iloc[:70]
	model = make_model({"max_depth": 6, "min_samples_leaf": 1, "max_features": 1.0}, seed=0)
	model.set_params(n_estimators=30)
	return model.fit(train[FEATURE_COLUMNS], train["sales"]), daily_frame.set_index("date")["sales"]


def test_recursive_forecast_never_reads_future_actuals(fitted):
	model, sales = fitted
	origin = sales.index[90]
	from_truncated = recursive_forecast(model, sales.loc[:origin], 10)
	corrupted = sales.copy()
	corrupted.loc[origin + pd.Timedelta(days=1):] = -1e9
	from_corrupted = recursive_forecast(model, corrupted.loc[:origin], 10)
	pd.testing.assert_series_equal(from_truncated, from_corrupted)
	assert from_truncated.index[0] == origin + pd.Timedelta(days=1) and len(from_truncated) == 10


def test_model_serialization_round_trip(fitted, tmp_path, daily_frame):
	model, _ = fitted
	rows = build_features(daily_frame).dropna()[FEATURE_COLUMNS].iloc[-5:]
	path = tmp_path / "model.joblib"
	joblib.dump(model, path)
	reloaded = joblib.load(path)
	assert list(reloaded.feature_names_in_) == FEATURE_COLUMNS
	assert np.allclose(reloaded.predict(rows), model.predict(rows))


def test_forecast_metrics_bundle():
	metrics = forecast_metrics([1, 2, 3], [1, 2, 4])
	assert set(metrics) == {"mae", "rmse", "wape", "r2", "n_observations"} and metrics["n_observations"] == 3
