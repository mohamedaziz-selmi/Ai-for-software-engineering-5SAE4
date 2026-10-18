"""Optional advanced model: store x product-family forecasts with a direct multi-step strategy.

Every history feature is lagged by at least ADVANCED_MIN_LAG days, so a single model can forecast
any day up to that horizon without recursion and without touching actuals after the forecast origin.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from .config import ADVANCED_MIN_LAG
from .sales_data import HOLIDAY_DAY_TYPES

L = ADVANCED_MIN_LAG
CATEGORICAL = ["store_code", "family_code", "store_type_code", "city_code"]
FEATURES = CATEGORICAL + [
	"cluster", "day_of_week", "day_of_month", "month", "is_payday", "is_closure_day",
	"is_national_holiday", "is_regional_holiday", "is_local_holiday", "is_national_event",
	"onpromotion", f"lag_{L}", f"lag_{L + 5}", f"lag_{L + 12}", f"lag_{L + 19}",
	f"roll_mean_7_at_{L}", f"roll_mean_28_at_{L}", f"roll_mean_91_at_{L}", f"oil_lag_{L}",
]
FEATURE_NOTES = {
	"store_code / family_code / store_type_code / city_code": "Categorical codes from stores.csv and the family label (fixed mapping saved with the model).",
	"onpromotion": "Items on promotion that day; provided in advance for future dates in test.csv.",
	"is_regional_holiday / is_local_holiday": "Holiday whose locale_name matches the store's state / city.",
	f"lag_{L}..lag_{L + 19}": f"Series sales {L}, {L + 5}, {L + 12}, {L + 19} days earlier (all >= {L}).",
	f"roll_mean_*_at_{L}": f"Mean series sales over windows ending {L} days before the target date.",
	f"oil_lag_{L}": f"Forward-filled oil price {L} days earlier.",
	"target": "log1p(sales); predictions are transformed back with expm1 and clipped at zero.",
}


def category_maps(train, stores):
	return {
		"store": {int(v): i for i, v in enumerate(sorted(stores["store_nbr"].unique()))},
		"family": {v: i for i, v in enumerate(sorted(train["family"].unique()))},
		"store_type": {v: i for i, v in enumerate(sorted(stores["type"].unique()))},
		"city": {v: i for i, v in enumerate(sorted(stores["city"].unique()))},
	}


def build_panel(train, test, stores, holidays, oil_daily, maps, start):
	"""Panel of store x family x date rows from `start` (including the unlabelled test dates)."""
	panel = pd.concat([train[["date", "store_nbr", "family", "sales", "onpromotion"]], test[["date", "store_nbr", "family", "onpromotion"]].assign(sales=np.nan)], ignore_index=True)
	panel = panel.sort_values(["store_nbr", "family", "date"]).reset_index(drop=True)

	# Closure days (25 Dec) are absent from the raw panel; insert them so shifts are calendar-exact.
	all_dates = pd.date_range(panel["date"].min(), panel["date"].max(), freq="D")
	keys = panel[["store_nbr", "family"]].drop_duplicates()
	full = keys.merge(pd.DataFrame({"date": all_dates}), how="cross")
	panel = full.merge(panel, on=["store_nbr", "family", "date"], how="left")
	closure = ~panel["date"].isin(train["date"]) & (panel["date"] <= train["date"].max())
	panel.loc[closure, ["sales", "onpromotion"]] = 0
	panel["is_closure_day"] = ((panel["date"].dt.month == 12) & (panel["date"].dt.day == 25)).astype(int)
	panel = panel.sort_values(["store_nbr", "family", "date"]).reset_index(drop=True)

	grouped = panel.groupby(["store_nbr", "family"], sort=False)["sales"]
	for lag in (L, L + 5, L + 12, L + 19):
		panel[f"lag_{lag}"] = grouped.shift(lag)
	shifted = grouped.shift(L)
	shifted_group = shifted.groupby([panel["store_nbr"], panel["family"]], sort=False)
	for window in (7, 28, 91):
		panel[f"roll_mean_{window}_at_{L}"] = shifted_group.transform(lambda s, w=window: s.rolling(w, min_periods=1).mean())

	panel = panel[panel["date"] >= pd.Timestamp(start)].copy()
	store_info = stores.set_index("store_nbr")
	panel["cluster"] = panel["store_nbr"].map(store_info["cluster"])
	panel["store_code"] = panel["store_nbr"].map(maps["store"])
	panel["family_code"] = panel["family"].map(maps["family"])
	panel["store_type_code"] = panel["store_nbr"].map(store_info["type"]).map(maps["store_type"])
	panel["city_code"] = panel["store_nbr"].map(store_info["city"]).map(maps["city"])
	panel["day_of_week"] = panel["date"].dt.dayofweek
	panel["day_of_month"] = panel["date"].dt.day
	panel["month"] = panel["date"].dt.month
	panel["is_payday"] = ((panel["date"].dt.day == 15) | panel["date"].dt.is_month_end).astype(int)

	active = holidays[holidays["type"].isin(HOLIDAY_DAY_TYPES) & ~holidays["transferred"]]
	national = set(active.loc[active["locale"] == "National", "date"])
	events = set(holidays.loc[(holidays["locale"] == "National") & (holidays["type"] == "Event"), "date"])
	regional = set(zip(active.loc[active["locale"] == "Regional", "date"], active.loc[active["locale"] == "Regional", "locale_name"]))
	local = set(zip(active.loc[active["locale"] == "Local", "date"], active.loc[active["locale"] == "Local", "locale_name"]))
	state = panel["store_nbr"].map(store_info["state"])
	city = panel["store_nbr"].map(store_info["city"])
	panel["is_national_holiday"] = panel["date"].isin(national).astype(int)
	panel["is_national_event"] = panel["date"].isin(events).astype(int)
	panel["is_regional_holiday"] = [int((d, s) in regional) for d, s in zip(panel["date"], state)]
	panel["is_local_holiday"] = [int((d, c) in local) for d, c in zip(panel["date"], city)]
	panel[f"oil_lag_{L}"] = (panel["date"] - pd.Timedelta(days=L)).map(oil_daily)
	panel["onpromotion"] = panel["onpromotion"].fillna(0)
	return panel.reset_index(drop=True)


def make_model(seed):
	categorical = [FEATURES.index(column) for column in CATEGORICAL]
	return HistGradientBoostingRegressor(
		max_iter=500, learning_rate=0.06, max_leaf_nodes=127, min_samples_leaf=40,
		l2_regularization=1.0, categorical_features=categorical, random_state=seed,
	)


def fit(model, rows):
	model.fit(rows[FEATURES], np.log1p(rows["sales"].clip(lower=0)))
	return model


def predict(model, rows):
	return np.clip(np.expm1(model.predict(rows[FEATURES])), 0, None)


def series_seasonal_naive(panel, start, end, block_days):
	"""Per-series seasonal-naive multi-step forecast using the last observed week before each block origin."""
	sales = panel.set_index(["store_nbr", "family", "date"])["sales"]
	parts = []
	origin = pd.Timestamp(start) - pd.Timedelta(days=1)
	end = pd.Timestamp(end)
	while origin < end:
		horizon = min(block_days, (end - origin).days)
		for step in range(horizon):
			day = origin + pd.Timedelta(days=step + 1)
			source = origin - pd.Timedelta(days=6 - step % 7)
			values = sales.xs(source, level="date")
			parts.append(pd.DataFrame({"store_nbr": values.index.get_level_values(0), "family": values.index.get_level_values(1), "date": day, "seasonal_naive": values.to_numpy()}))
		origin += pd.Timedelta(days=horizon)
	return pd.concat(parts, ignore_index=True)
