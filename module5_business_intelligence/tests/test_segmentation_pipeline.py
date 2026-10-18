import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.cluster import KMeans

from src.retail_data import classify, clean, normalize, validate_schema
from src.sales_data import SchemaError
from src.segmentation import RFMPreprocessor, assign_labels, build_rfm, cluster_profiles, search_k, select_k


def test_retail_schema_validation(retail_raw):
	with pytest.raises(SchemaError):
		validate_schema(retail_raw.drop(columns="CustomerID"))


def test_normalize_parses_types_and_identifiers(retail_raw):
	raw = retail_raw.assign(InvoiceDate=retail_raw["InvoiceDate"].astype(str), Quantity=retail_raw["Quantity"].astype(str))
	frame, issues = normalize(raw)
	assert pd.api.types.is_datetime64_any_dtype(frame["InvoiceDate"])
	assert pd.api.types.is_numeric_dtype(frame["Quantity"])
	assert frame.loc[0, "CustomerID"] == "17850"
	assert pd.isna(frame.loc[6, "CustomerID"])
	assert not any(issues.values())


def test_record_classification(retail_raw):
	frame, _ = normalize(retail_raw)
	types = classify(frame).tolist()
	assert types == [
		"purchase", "purchase", "purchase", "cancellation", "non_merchandise", "purchase",
		"stock_adjustment", "zero_price", "accounting_adjustment", "purchase", "cancellation",
	]


def test_cleaning_removes_duplicates_and_keeps_missing_values_separate(retail_raw):
	frame, report = clean(retail_raw)
	assert len(frame) == len(retail_raw) - 1
	assert next(s for s in report["steps"] if s["step"] == "drop_exact_duplicate_lines")["rows_removed"] == 1
	missing_description = frame[frame["Description"].isna()]
	assert missing_description["record_type"].tolist() == ["purchase"]  # missing text alone is not invalid
	assert (~frame["has_customer"]).sum() == 3  # kept for revenue reporting


def test_line_revenue(retail_raw):
	frame, _ = clean(retail_raw)
	assert np.allclose(frame["LineRevenue"], frame["Quantity"] * frame["UnitPrice"])
	assert frame.loc[frame["InvoiceNo"] == "C536367", "LineRevenue"].item() == -5.0


def test_rfm_calculation(retail_raw):
	frame, _ = clean(retail_raw)
	table, reference, exclusions = build_rfm(frame)
	assert reference == pd.Timestamp("2011-03-07")
	rows = table.set_index("customer_id")
	a = rows.loc["17850"]
	assert a["frequency"] == 2  # duplicate removed, two distinct purchase invoices
	assert a["gross_revenue"] == pytest.approx(15 + 10)
	assert a["cancelled_revenue"] == pytest.approx(5)
	assert a["monetary"] == pytest.approx(20)
	assert a["recency_days"] == (reference - pd.Timestamp("2011-02-01")).days
	b = rows.loc["12345"]
	assert b["monetary"] == pytest.approx(4)  # postage and zero-price lines excluded
	assert b["unique_products"] == 1
	assert "99999" not in rows.index and exclusions["no_valid_purchase"]["count"] == 1
	assert rows["eligible"].all()


def test_rfm_flags_non_positive_net_spending(retail_raw):
	extra = pd.DataFrame([("C9", "85123A", "MUG", -100, pd.Timestamp("2011-03-01"), 2.5, 17850.0, "United Kingdom")], columns=retail_raw.columns)
	frame, _ = clean(pd.concat([retail_raw, extra], ignore_index=True))
	table, _, exclusions = build_rfm(frame)
	assert not table.set_index("customer_id").loc["17850", "eligible"]
	assert exclusions["non_positive_net_spending"]["count"] == 1


@pytest.fixture
def customers():
	rng = np.random.default_rng(0)
	n = 300
	return pd.DataFrame({
		"customer_id": [str(10000 + i) for i in range(n)],
		"recency_days": rng.integers(1, 365, n),
		"frequency": rng.geometric(0.3, n),
		"monetary": rng.lognormal(6, 1.2, n),
	})


def test_preprocessor_scales_and_logs_skewed_features(customers):
	features = ["recency_days", "frequency", "monetary"]
	prep = RFMPreprocessor(features).fit(customers)
	X = prep.transform(customers)
	assert np.allclose(X.mean(), 0, atol=1e-9) and np.allclose(X.std(ddof=0), 1)
	assert "monetary" in prep.log_features_ and "frequency" in prep.log_features_
	shifted = customers.assign(monetary=customers["monetary"] * 10)
	assert not np.allclose(prep.transform(shifted).mean(), 0)  # learned on reference data only


def test_preprocessor_handles_invalid_values(customers):
	prep = RFMPreprocessor(["recency_days", "frequency", "monetary"]).fit(customers)
	bad = customers.head(3).astype({"monetary": float}).copy()
	bad.loc[0, "monetary"] = np.inf
	bad.loc[1, "monetary"] = -50.0
	assert np.isfinite(prep.transform(bad).to_numpy()).all()
	with pytest.raises(ValueError, match="Missing feature"):
		prep.transform(customers.drop(columns="frequency"))


def test_k_search_rejects_invalid_configurations():
	X = np.array([[0.0, 0.0], [0.0, 0.0], [1.0, 1.0], [1.0, 1.0], [2.0, 2.0]])
	results = search_k(X, [2, 3, 4, 5], seed=0, n_init=3)
	assert [r["valid"] for r in results] == [True, True, False, False]
	assert -1 <= results[0]["silhouette"] <= 1


def test_k_selection_rule():
	results = [
		{"k": 2, "valid": True, "silhouette": 0.6, "min_cluster_share": 0.4},
		{"k": 3, "valid": True, "silhouette": 0.40, "min_cluster_share": 0.2},
		{"k": 4, "valid": True, "silhouette": 0.395, "min_cluster_share": 0.1},
		{"k": 5, "valid": True, "silhouette": 0.5, "min_cluster_share": 0.01},
	]
	k, info = select_k(results, (3, 6), 0.02, tolerance=0.01)
	assert k == 4 and info["global_best_k"] == 2
	assert select_k(results, (3, 6), 0.02, tolerance=0.0)[0] == 3


def test_labels_follow_statistics_not_cluster_numbers(customers):
	table = customers.assign(avg_order_value=1.0, unique_products=1, active_months=1)
	labels = (table["monetary"] > table["monetary"].median()).astype(int).to_numpy()
	first, _ = assign_labels(cluster_profiles(table, labels, ["recency_days", "frequency", "monetary"]), table)
	second, _ = assign_labels(cluster_profiles(table, 1 - labels, ["recency_days", "frequency", "monetary"]), table)
	by_profile = lambda profiles: {round(p["monetary_median"], 6): p["segment_label"] for p in profiles}
	assert by_profile(first) == by_profile(second)
	assert {p["cluster"] for p in first} == {0, 1}
	assert all(p["recommended_action"] for p in first)


def test_duplicate_labels_are_documented():
	table = pd.DataFrame({
		"recency_days": [300, 300, 301, 301] + list(range(5, 15)),
		"frequency": [1, 1, 1, 1] + [20] * 10,
		"monetary": [100, 100, 101, 101] + [9000] * 10,
	})
	profiles = cluster_profiles(table, [0, 0, 1, 1] + [2] * 10, ["recency_days", "frequency", "monetary"])
	profiles, notes = assign_labels(profiles, table)
	labels = [p["segment_label"] for p in profiles]
	assert len(set(labels)) == 3 and notes and "similar" in notes[0]["observation"]


def test_kmeans_serialization_round_trip(customers, tmp_path):
	prep = RFMPreprocessor(["recency_days", "frequency", "monetary"]).fit(customers)
	X = prep.transform(customers).to_numpy()
	model = KMeans(n_clusters=3, n_init=5, random_state=0).fit(X)
	joblib.dump(model, tmp_path / "k.joblib")
	joblib.dump(prep.scaler_, tmp_path / "s.joblib")
	reloaded = joblib.load(tmp_path / "k.joblib")
	assert (reloaded.predict(X) == model.labels_).all()
	assert list(joblib.load(tmp_path / "s.joblib").feature_names_in_) == ["recency_days", "frequency", "monetary"]
