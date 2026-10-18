"""Leakage-safe time-series features for the daily aggregate sales forecast."""

import numpy as np
import pandas as pd

from .config import SALES_LAGS, SALES_ROLLING_WINDOWS

CALENDAR_FLAG_COLUMNS = ["is_closure_day", "is_national_holiday", "is_national_event", "is_work_day"]

FEATURE_DICTIONARY = {
	"day_of_week": ("int", "date.dayofweek (Monday = 0)", "Weekly shopping cycle."),
	"day_of_month": ("int", "date.day", "Within-month pattern (salary timing)."),
	"month": ("int", "date.month", "Annual seasonality."),
	"quarter": ("int", "date.quarter", "Coarse annual seasonality."),
	"year": ("int", "date.year", "Long-term trend level."),
	"day_of_year": ("int", "date.dayofyear", "Position in the year for holiday seasons."),
	"is_weekend": ("binary", "1 when day_of_week >= 5", "Weekend demand uplift."),
	"is_payday": ("binary", "1 on the 15th and the last day of the month", "Public-sector wages in Ecuador are paid on these days."),
	"is_new_year": ("binary", "1 on 1 January", "Most stores are closed or nearly closed."),
	"is_closure_day": ("binary", "1 on 25 December (absent from every store)", "Known store closure."),
	"is_national_holiday": ("binary", "National Holiday/Transfer/Additional/Bridge day, not transferred", "Holiday calendar published in advance."),
	"is_national_event": ("binary", "National Event in holidays_events.csv", "Events such as Black Friday, Cyber Monday, Mother's Day."),
	"is_work_day": ("binary", "National compensatory Work Day", "Weekend days that become working days."),
	**{f"lag_{lag}": ("float", f"daily sales shifted by {lag} day(s)", "Recent demand level; only past values.") for lag in SALES_LAGS},
	**{f"roll_mean_{window}": ("float", f"mean of sales over days t-{window}..t-1 (shift(1).rolling({window}))", "Smoothed recent level, excludes day t.") for window in SALES_ROLLING_WINDOWS},
	**{f"roll_std_{window}": ("float", f"std of sales over days t-{window}..t-1", "Recent volatility, excludes day t.") for window in (7, 28)},
}
FEATURE_COLUMNS = list(FEATURE_DICTIONARY)
TARGET = "sales"


def calendar_features(dates, calendar_flags=None):
	"""Features that are known in advance for any date (calendar and holiday schedule)."""
	dates = pd.DatetimeIndex(dates)
	frame = pd.DataFrame(index=dates)
	frame["day_of_week"] = dates.dayofweek
	frame["day_of_month"] = dates.day
	frame["month"] = dates.month
	frame["quarter"] = dates.quarter
	frame["year"] = dates.year
	frame["day_of_year"] = dates.dayofyear
	frame["is_weekend"] = (dates.dayofweek >= 5).astype(int)
	frame["is_payday"] = ((dates.day == 15) | dates.is_month_end).astype(int)
	frame["is_new_year"] = ((dates.month == 1) & (dates.day == 1)).astype(int)
	christmas = pd.Series(((dates.month == 12) & (dates.day == 25)).astype(int), index=dates)
	if calendar_flags is not None:
		flags = calendar_flags.reindex(dates)
		for column in CALENDAR_FLAG_COLUMNS:
			values = flags[column] if column in flags else pd.Series(np.nan, index=dates)
			frame[column] = values.fillna(christmas if column == "is_closure_day" else 0).astype(int).to_numpy()
	else:
		frame["is_closure_day"] = christmas
		for column in CALENDAR_FLAG_COLUMNS[1:]:
			frame[column] = 0
	return frame


def history_features(sales):
	"""Lag and rolling features computed strictly from values before each date."""
	sales = pd.Series(sales, dtype=float)
	frame = pd.DataFrame(index=sales.index)
	for lag in SALES_LAGS:
		frame[f"lag_{lag}"] = sales.shift(lag)
	past = sales.shift(1)
	for window in SALES_ROLLING_WINDOWS:
		frame[f"roll_mean_{window}"] = past.rolling(window, min_periods=window).mean()
	for window in (7, 28):
		frame[f"roll_std_{window}"] = past.rolling(window, min_periods=window).std()
	return frame


def build_features(daily, calendar_flags=None):
	"""daily: frame with a regular daily 'date' column and 'sales'. Returns features plus target."""
	daily = daily.sort_values("date").set_index("date")
	expected = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
	if len(expected) != len(daily) or not daily.index.equals(expected):
		raise ValueError("Daily sales must have exactly one row per calendar day; insert closure days first.")
	flags = calendar_flags if calendar_flags is not None else daily[[c for c in CALENDAR_FLAG_COLUMNS if c in daily]]
	frame = calendar_features(daily.index, flags).join(history_features(daily["sales"]))
	frame[TARGET] = daily["sales"]
	return frame[FEATURE_COLUMNS + [TARGET]].rename_axis("date")


def features_for_next_day(history, next_date, calendar_flags=None):
	"""One feature row for next_date from a history series (actuals or earlier recursive predictions)."""
	next_date = pd.Timestamp(next_date)
	if history.index.max() != next_date - pd.Timedelta(days=1):
		raise ValueError("History must end on the day before the forecast date.")
	recent = history.iloc[-(max(SALES_LAGS + SALES_ROLLING_WINDOWS) + 1):].astype(float)
	extended = pd.concat([recent, pd.Series([np.nan], index=[next_date])])
	row = calendar_features([next_date], calendar_flags).join(history_features(extended).loc[[next_date]])
	return row[FEATURE_COLUMNS]


def chronological_split(frame, splits):
	"""Split a date-indexed frame into the configured, non-overlapping chronological periods."""
	parts = {}
	previous_end = None
	for name, (start, end) in splits.items():
		start, end = pd.Timestamp(start), pd.Timestamp(end)
		if previous_end is not None and start <= previous_end:
			raise ValueError(f"Split '{name}' overlaps the previous period.")
		parts[name] = frame.loc[(frame.index >= start) & (frame.index <= end)]
		previous_end = end
	return parts
