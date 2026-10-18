import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def daily_frame():
	"""Small synthetic daily series with a weekly pattern (unit-test fixture only)."""
	dates = pd.date_range("2020-01-01", periods=120, freq="D")
	sales = 100 + 20 * (dates.dayofweek >= 5) + np.arange(len(dates)) * 0.5
	return pd.DataFrame({"date": dates, "sales": sales.astype(float), "is_closure_day": 0, "is_national_holiday": 0, "is_national_event": 0, "is_work_day": 0})


@pytest.fixture
def store_frames():
	dates = pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-04"])
	train = pd.DataFrame([
		{"id": i, "date": d, "store_nbr": s, "family": f, "sales": 10.0 + i, "onpromotion": 0}
		for i, (d, s, f) in enumerate((d, s, f) for d in dates for s in (1, 2) for f in ("A", "B"))
	])
	return {
		"train": train,
		"test": pd.DataFrame({"id": [99], "date": pd.to_datetime(["2020-01-05"]), "store_nbr": [1], "family": ["A"], "onpromotion": [0]}),
		"stores": pd.DataFrame({"store_nbr": [1, 2], "city": ["Quito", "Quito"], "state": ["Pichincha", "Pichincha"], "type": ["A", "B"], "cluster": [1, 2]}),
		"transactions": pd.DataFrame({"date": dates, "store_nbr": [1, 1, 1], "transactions": [5, 6, 7]}),
		"oil": pd.DataFrame({"date": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]), "dcoilwtico": [np.nan, 50.0, np.nan]}),
		"holidays_events": pd.DataFrame({
			"date": pd.to_datetime(["2020-01-01", "2020-01-02"]), "type": ["Holiday", "Holiday"], "locale": ["National", "National"],
			"locale_name": ["Ecuador", "Ecuador"], "description": ["Primer dia", "Moved"], "transferred": [False, True],
		}),
	}


@pytest.fixture
def retail_raw():
	rows = [
		("536365", "85123A", "MUG", 6, "2011-01-01 10:00", 2.5, 17850.0, "United Kingdom"),
		("536365", "85123A", "MUG", 6, "2011-01-01 10:00", 2.5, 17850.0, "United Kingdom"),  # exact duplicate
		("536366", "71053", None, 2, "2011-02-01 10:00", 5.0, 17850.0, "United Kingdom"),  # missing description, valid purchase
		("C536367", "71053", "LAMP", -1, "2011-02-02 10:00", 5.0, 17850.0, "United Kingdom"),  # cancellation
		("536368", "POST", "POSTAGE", 1, "2011-02-03 10:00", 18.0, 12345.0, "France"),  # non-merchandise
		("536369", "22000", "PEN", 4, "2011-03-01 10:00", 1.0, 12345.0, "France"),
		("536370", "22001", "?", -5, "2011-03-02 10:00", 0.0, None, "United Kingdom"),  # stock adjustment
		("536371", "22002", "FREE", 3, "2011-03-03 10:00", 0.0, 12345.0, "France"),  # zero price
		("A563186", "B", "Adjust bad debt", 1, "2011-03-04 10:00", -11062.06, None, "United Kingdom"),
		("536372", "22003", "BAG", 10, "2011-03-05 10:00", 2.0, None, "United Kingdom"),  # purchase without customer
		("C536373", "22000", "PEN", -20, "2011-03-06 10:00", 1.0, 99999.0, "Spain"),  # cancellation-only customer
	]
	frame = pd.DataFrame(rows, columns=["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"])
	frame["InvoiceDate"] = pd.to_datetime(frame["InvoiceDate"])
	return frame
