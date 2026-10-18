"""RFM feature construction, preprocessing, K-means search, and rule-based segment labelling."""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from .common import describe_series

FEATURE_DICTIONARY = {
	"recency_days": ("days", "Days between the reference date and the customer's latest valid purchase (calendar dates)."),
	"frequency": ("invoices", "Number of distinct valid purchase invoices."),
	"monetary": ("GBP", "Net merchandise spending: purchase revenue minus cancelled revenue."),
	"gross_revenue": ("GBP", "Revenue of valid purchase lines before cancellations."),
	"cancelled_revenue": ("GBP", "Absolute revenue of the customer's cancellation lines."),
	"avg_order_value": ("GBP per invoice", "gross_revenue / frequency."),
	"avg_quantity_per_order": ("units per invoice", "Purchased units / frequency."),
	"unique_products": ("products", "Distinct StockCodes purchased."),
	"active_months": ("months", "Distinct calendar months with at least one purchase."),
	"tenure_days": ("days", "Days between the first valid purchase and the reference date."),
}

# Business rules evaluated in order; each threshold compares the cluster median with the
# customer-population percentile of that median (0 = lowest value, 1 = highest value).
DEFAULT_LABEL_RULES = [
	{"label": "High-value customers", "all": {"monetary_pct": [">=", 0.8], "frequency_pct": [">=", 0.75], "recency_pct": ["<=", 0.5]}},
	{"label": "Loyal customers", "all": {"frequency_pct": [">=", 0.6], "recency_pct": ["<=", 0.5]}},
	{"label": "At-risk customers", "all": {"monetary_pct": [">=", 0.5], "recency_pct": [">=", 0.6]}},
	{"label": "Inactive customers", "all": {"recency_pct": [">=", 0.7], "frequency_pct": ["<", 0.5]}},
	{"label": "Recent occasional customers", "all": {"recency_pct": ["<=", 0.4], "frequency_pct": ["<", 0.5]}},
	{"label": "Occasional customers", "all": {"frequency_pct": ["<", 0.5]}},
	{"label": "Regular customers", "all": {}},
]
SEGMENT_ACTIONS = {
	"High-value customers": "Protect: VIP loyalty rewards, early access, and account management; monitor for any drop in order frequency.",
	"Loyal customers": "Grow: loyalty points, cross-sell related product ranges, and referral incentives.",
	"At-risk customers": "Win back: personalised re-engagement offers based on past purchases before they lapse.",
	"Inactive customers": "Reactivate cheaply: low-cost reminder campaigns; suppress from expensive channels if they stay inactive.",
	"Recent occasional customers": "Nurture: onboarding sequence and a second-purchase incentive to build frequency.",
	"Occasional customers": "Develop: seasonal promotions and bundles to increase order frequency.",
	"Regular customers": "Maintain: standard newsletters and periodic offers; test upsell to higher order values.",
}
OPERATORS = {">=": np.greater_equal, "<=": np.less_equal, ">": np.greater, "<": np.less}


def build_rfm(clean, reference_date=None):
	"""One row per customer with a valid CustomerID. Returns the table, the reference date, and exclusions."""
	customers = clean[clean["has_customer"]]
	purchases = customers[customers["record_type"] == "purchase"]
	cancels = customers[customers["record_type"] == "cancellation"]
	if reference_date is None:
		reference_date = clean["InvoiceDate"].max().normalize() + pd.Timedelta(days=1)
	reference_date = pd.Timestamp(reference_date)

	grouped = purchases.groupby("CustomerID")
	table = pd.DataFrame({
		"last_purchase": grouped["InvoiceDate"].max(),
		"first_purchase": grouped["InvoiceDate"].min(),
		"frequency": grouped["InvoiceNo"].nunique(),
		"gross_revenue": grouped["LineRevenue"].sum(),
		"units": grouped["Quantity"].sum(),
		"unique_products": grouped["StockCode"].nunique(),
		"active_months": grouped["InvoiceDate"].agg(lambda s: s.dt.to_period("M").nunique()),
		"country": grouped["Country"].agg(lambda s: s.mode().iat[0]),
	})
	table["cancelled_revenue"] = (-cancels.groupby("CustomerID")["LineRevenue"].sum()).reindex(table.index).fillna(0.0)
	table["monetary"] = table["gross_revenue"] - table["cancelled_revenue"]
	table["recency_days"] = (reference_date - table["last_purchase"].dt.normalize()).dt.days
	table["tenure_days"] = (reference_date - table["first_purchase"].dt.normalize()).dt.days
	table["avg_order_value"] = table["gross_revenue"] / table["frequency"]
	table["avg_quantity_per_order"] = table["units"] / table["frequency"]
	table["eligible"] = table["monetary"] > 0

	all_ids = set(customers["CustomerID"].unique())
	no_purchase = all_ids - set(table.index)
	exclusions = {
		"customers_with_id": len(all_ids),
		"no_valid_purchase": {"count": len(no_purchase), "reason": "Only cancellations, adjustments, or non-merchandise lines; nothing to segment."},
		"non_positive_net_spending": {"count": int((~table["eligible"]).sum()), "reason": "Cancellations exceed purchases inside the data window (refunds of earlier orders)."},
		"eligible_customers": int(table["eligible"].sum()),
	}
	columns = ["recency_days", "frequency", "monetary", "gross_revenue", "cancelled_revenue", "avg_order_value", "avg_quantity_per_order", "unique_products", "active_months", "tenure_days", "country", "eligible", "first_purchase", "last_purchase"]
	return table[columns].rename_axis("customer_id").reset_index(), reference_date, exclusions


def feature_quality(table, features):
	values = table[features]
	numeric = values.to_numpy(dtype=float)
	quality = {
		"rows": int(len(table)),
		"duplicate_customer_ids": int(table["customer_id"].duplicated().sum()),
		"missing_values": {f: int(values[f].isna().sum()) for f in features},
		"infinite_values": {f: int(np.isinf(numeric[:, i]).sum()) for i, f in enumerate(features)},
		"distributions": {},
	}
	for feature in features:
		series = values[feature]
		q1, q3 = series.quantile([0.25, 0.75])
		quality["distributions"][feature] = {**describe_series(series), "iqr_outliers": int(((series < q1 - 1.5 * (q3 - q1)) | (series > q3 + 1.5 * (q3 - q1))).sum())}
	return quality


class RFMPreprocessor:
	"""Deduplicate, impute, guard negatives, log1p skewed features, and standardize. Fit on reference data only."""

	def __init__(self, features, skew_threshold=1.0):
		self.features = list(features)
		self.skew_threshold = skew_threshold

	def fit(self, table):
		frame = self._base(table)
		self.medians_ = frame.median().to_dict()
		frame = frame.fillna(self.medians_)
		self.skewness_ = {f: float(frame[f].skew()) for f in self.features}
		self.log_features_ = [f for f in self.features if abs(self.skewness_[f]) > self.skew_threshold and (frame[f] >= 0).all()]
		self.scaler_ = StandardScaler().fit(self._log(frame))
		return self

	def transform(self, table):
		frame = self._base(table).fillna(self.medians_)
		scaled = self.scaler_.transform(self._log(frame))
		return pd.DataFrame(scaled, columns=self.features, index=table.index)

	def _base(self, table):
		missing = [f for f in self.features if f not in table.columns]
		if missing:
			raise ValueError(f"Missing feature columns: {missing}")
		frame = table[self.features].astype(float).replace([np.inf, -np.inf], np.nan)
		if "monetary" in frame:
			frame["monetary"] = frame["monetary"].clip(lower=0)
		return frame

	def _log(self, frame):
		frame = frame.copy()
		for feature in self.log_features_:
			frame[feature] = np.log1p(frame[feature])
		return frame[self.features]

	def config(self):
		return {
			"features": self.features,
			"feature_order": self.features,
			"imputation": {"strategy": "median of reference population", "values": self.medians_},
			"negative_monetary_policy": "clip to 0 before log1p (only eligible customers with net spending > 0 are modelled)",
			"skew_threshold": self.skew_threshold,
			"skewness_before_log": self.skewness_,
			"log1p_features": self.log_features_,
			"scaler": {"type": "StandardScaler", "mean": self.scaler_.mean_.tolist(), "scale": self.scaler_.scale_.tolist()},
		}


def valid_k(n_samples, n_distinct, k):
	return 2 <= k < n_samples and k <= n_distinct


def search_k(X, k_values, seed, n_init):
	X = np.asarray(X, dtype=float)
	n_distinct = len(np.unique(X, axis=0))
	results = []
	for k in k_values:
		if not valid_k(len(X), n_distinct, k):
			results.append({"k": k, "valid": False, "reason": f"needs 2 <= K < n_samples and K <= distinct points ({n_distinct})"})
			continue
		model = KMeans(n_clusters=k, n_init=n_init, random_state=seed).fit(X)
		sizes = np.bincount(model.labels_, minlength=k)
		results.append({
			"k": k, "valid": True, "inertia": float(model.inertia_),
			"silhouette": float(silhouette_score(X, model.labels_)),
			"cluster_sizes": sizes.tolist(), "min_cluster_share": float(sizes.min() / len(X)),
		})
	return results


def select_k(results, business_range, min_share, tolerance=0.0):
	low, high = business_range
	candidates = [r for r in results if r["valid"] and low <= r["k"] <= high and r["min_cluster_share"] >= min_share]
	if not candidates:
		candidates = [r for r in results if r["valid"]]
	top = max(r["silhouette"] for r in candidates)
	best = max((r for r in candidates if r["silhouette"] >= top - tolerance), key=lambda r: r["k"])
	overall = max((r for r in results if r["valid"]), key=lambda r: r["silhouette"])
	return best["k"], {
		"rule": (
			f"Among K in [{low}, {high}] whose smallest cluster holds >= {min_share:.0%} of customers, take the largest K whose "
			f"silhouette is within {tolerance:.3f} of the best candidate (more actionable segments at an equivalent separation)."
		),
		"best_candidate_silhouette": top,
		"selected_k": best["k"], "selected_silhouette": best["silhouette"],
		"global_best_k": overall["k"], "global_best_silhouette": overall["silhouette"],
		"note": "K = 2 often maximises silhouette but only separates active from lapsed customers; the business range keeps segments actionable.",
	}


def stability(X, k, seed, n_init, reference_labels, n_runs=10, sample_fraction=0.8):
	X = np.asarray(X, dtype=float)
	rng = np.random.default_rng(seed)
	seeds = [adjusted_rand_score(reference_labels, KMeans(n_clusters=k, n_init=n_init, random_state=seed + 1 + i).fit_predict(X)) for i in range(n_runs)]
	subsample = []
	for _ in range(n_runs):
		index = rng.choice(len(X), size=int(len(X) * sample_fraction), replace=False)
		model = KMeans(n_clusters=k, n_init=n_init, random_state=seed).fit(X[index])
		subsample.append(adjusted_rand_score(reference_labels, model.predict(X)))
	return {
		"method": f"Adjusted Rand Index vs the final labels: {n_runs} different seeds, and {n_runs} fits on random {sample_fraction:.0%} subsamples predicted on all customers.",
		"seed_ari_mean": float(np.mean(seeds)), "seed_ari_min": float(np.min(seeds)),
		"subsample_ari_mean": float(np.mean(subsample)), "subsample_ari_min": float(np.min(subsample)),
	}


def cluster_profiles(table, labels, features):
	frame = table.assign(cluster=np.asarray(labels))
	total = len(frame)
	profiles = []
	for cluster, group in frame.groupby("cluster"):
		profile = {"cluster": int(cluster), "customers": int(len(group)), "share_pct": float(len(group) / total * 100), "revenue_share_pct": float(group["monetary"].sum() / frame["monetary"].sum() * 100)}
		for feature in features:
			profile[f"{feature}_mean"] = float(group[feature].mean())
			profile[f"{feature}_median"] = float(group[feature].median())
		profiles.append(profile)
	return profiles


def population_percentile(population, value):
	population = np.asarray(population, dtype=float)
	return float((population < value).mean() + 0.5 * (population == value).mean())


def assign_labels(profiles, table, rules=None, similarity_tolerance=0.25):
	"""Label clusters from their RFM medians with ordered, configurable business rules."""
	rules = rules or DEFAULT_LABEL_RULES
	for profile in profiles:
		scores = {
			"recency_pct": population_percentile(table["recency_days"], profile["recency_days_median"]),
			"frequency_pct": population_percentile(table["frequency"], profile["frequency_median"]),
			"monetary_pct": population_percentile(table["monetary"], profile["monetary_median"]),
		}
		profile["rule_scores"] = scores
		for rule in rules:
			if all(OPERATORS[op](scores[key], threshold) for key, (op, threshold) in rule["all"].items()):
				profile["segment_label"] = rule["label"]
				profile["matched_rule"] = rule
				break
		profile["recommended_action"] = SEGMENT_ACTIONS.get(profile["segment_label"], "")

	notes = []
	by_label = {}
	for profile in profiles:
		by_label.setdefault(profile["segment_label"], []).append(profile)
	for label, group in by_label.items():
		if len(group) < 2:
			continue
		group.sort(key=lambda p: p["monetary_median"], reverse=True)
		for rank, profile in enumerate(group):
			profile["segment_label"] = f"{label} ({'higher' if rank == 0 else 'lower'} spend)" if len(group) == 2 else f"{label} ({rank + 1})"
		a, b = group[0], group[1]
		similar = all(abs(a[f"{f}_median"] - b[f"{f}_median"]) <= similarity_tolerance * max(abs(a[f"{f}_median"]), abs(b[f"{f}_median"]), 1e-9) for f in ("recency_days", "frequency", "monetary"))
		notes.append({
			"label": label, "clusters": [p["cluster"] for p in group],
			"observation": "Clusters match the same business rule and have similar RFM medians (within 25%)." if similar else "Clusters match the same business rule but differ in at least one RFM median by more than 25%; suffixes distinguish them by spend.",
		})
	return profiles, notes
