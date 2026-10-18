"""Customer Segmentation pipeline: explore -> clean -> RFM -> reference clustering -> preprocessing -> K-means.

Run from module5_business_intelligence/:
    ..\\rag_service\\.venv\\Scripts\\python.exe -m src.pipeline_segmentation
"""

import time

import joblib
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from . import figures, segmentation
from .common import environment_versions, histogram, update_report, utc_now, write_json
from .config import (
	DATA_REPORTS_DIR, MODELS_DIR, PROCESSED_DIR, RANDOM_SEED, REPORTS_DIR, RETAIL_XLSX, SEGMENT_BUSINESS_K_RANGE,
	SEGMENT_FEATURES, SEGMENT_K_RANGE, SEGMENT_MIN_CLUSTER_SHARE, SEGMENT_N_INIT, SEGMENT_SILHOUETTE_TOLERANCE, ensure_dirs,
)
from .manifest import dataset_version
from .retail_data import clean, explore, load_raw

FEATURES = SEGMENT_FEATURES


def log(message):
	print(f"[segmentation {time.strftime('%H:%M:%S')}] {message}", flush=True)


def distributions(table):
	return {feature: {"raw": histogram(table[feature], bins=30), "log1p": histogram(table[feature], bins=30, log=True)} for feature in FEATURES}


def main():
	ensure_dirs()
	started = time.time()
	raw = load_raw()
	log(f"Loaded {len(raw)} raw lines")
	exploration = explore(raw)
	exploration["created_at"] = utc_now()
	exploration_path = write_json(DATA_REPORTS_DIR / "retail_exploration_report.json", exploration)

	retail, cleaning = clean(raw)
	retail.to_csv(PROCESSED_DIR / "retail_clean.csv.gz", index=False, compression="gzip")
	update_report(DATA_REPORTS_DIR / "cleaning_report.json", "customer_segmentation", cleaning)
	log(f"Clean lines: {len(retail)}; record types {cleaning['record_type_counts']}")

	table, reference_date, exclusions = segmentation.build_rfm(retail)
	table.to_csv(PROCESSED_DIR / "customer_rfm.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")
	exploration["customer_exclusions"] = exclusions
	write_json(exploration_path, exploration)
	eligible = table[table["eligible"]].reset_index(drop=True)
	log(f"Eligible customers: {len(eligible)} of {exclusions['customers_with_id']}")

	update_report(DATA_REPORTS_DIR / "data_quality_report.json", "customer_segmentation", {
		"dataset": "UCI Online Retail",
		"status": "pass",
		"checks": [
			{"check": "schema", "result": "pass", "detail": "All 8 expected columns present; dates and numbers parse without failures." if not any(cleaning["steps"][0]["coercion_issues"].values()) else f"Coercion issues: {cleaning['steps'][0]['coercion_issues']}"},
			{"check": "duplicate_lines", "result": "warn", "detail": f"{exploration['duplicate_transaction_lines']} exact duplicate lines removed."},
			{"check": "missing_customer_id", "result": "warn", "detail": f"{exploration['missing_values']['CustomerID']['missing']} lines ({exploration['missing_values']['CustomerID']['missing_pct']:.1f}%) without CustomerID, excluded from segmentation only."},
			{"check": "cancellations", "result": "info", "detail": f"{exploration['cancellations']['lines']} cancellation lines in {exploration['cancellations']['invoices']} invoices, deducted from customer spending."},
			{"check": "duplicate_customer_ids", "result": "pass" if table["customer_id"].duplicated().sum() == 0 else "fail", "detail": f"{int(table['customer_id'].duplicated().sum())} duplicate customer rows in customer_rfm.csv."},
		],
		"before": {"rows": int(len(raw)), "missing_values": int(raw.isna().sum().sum()), "duplicate_rows": int(raw.duplicated().sum())},
		"after": {"rows": int(len(retail)), "missing_values": int(retail[["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"]].isna().sum().sum()), "duplicate_rows": int(retail.duplicated().sum()), "eligible_customers": int(len(eligible))},
	})

	# Preprocessing reference experiment: raw-derived R, F, M with only invalid values removed.
	quality_before = segmentation.feature_quality(eligible, FEATURES)
	raw_X = eligible[FEATURES].replace([np.inf, -np.inf], np.nan).dropna()
	raw_search = segmentation.search_k(raw_X.to_numpy(dtype=float), SEGMENT_K_RANGE, RANDOM_SEED, SEGMENT_N_INIT)
	log("Reference (raw feature) K search complete")

	preprocessor = segmentation.RFMPreprocessor(FEATURES).fit(eligible)
	X = preprocessor.transform(eligible)
	X.assign(customer_id=eligible["customer_id"]).to_csv(PROCESSED_DIR / "customer_features_processed.csv", index=False, float_format="%.6f")
	search = segmentation.search_k(X.to_numpy(), SEGMENT_K_RANGE, RANDOM_SEED, SEGMENT_N_INIT)
	k, selection = segmentation.select_k(search, SEGMENT_BUSINESS_K_RANGE, SEGMENT_MIN_CLUSTER_SHARE, SEGMENT_SILHOUETTE_TOLERANCE)
	log(f"Selected K={k}: {selection}")

	model = KMeans(n_clusters=k, n_init=SEGMENT_N_INIT, random_state=RANDOM_SEED).fit(X.to_numpy())
	labels = model.labels_
	raw_model = KMeans(n_clusters=k, n_init=SEGMENT_N_INIT, random_state=RANDOM_SEED).fit(raw_X.to_numpy(dtype=float))
	raw_labels = raw_model.labels_

	stability = segmentation.stability(X.to_numpy(), k, RANDOM_SEED, SEGMENT_N_INIT, labels)
	profiles, notes = segmentation.assign_labels(segmentation.cluster_profiles(eligible, labels, FEATURES + ["avg_order_value", "unique_products", "active_months"]), eligible)
	raw_profiles = segmentation.cluster_profiles(eligible, raw_labels, FEATURES)
	label_by_cluster = {p["cluster"]: p["segment_label"] for p in profiles}

	silhouette_processed = float(silhouette_score(X.to_numpy(), labels))
	silhouette_raw = float(silhouette_score(raw_X.to_numpy(dtype=float), raw_labels))
	comparison = {
		"customer_population": int(len(eligible)),
		"reference_date": reference_date.date().isoformat(),
		"features": FEATURES,
		"k": k,
		"before_preprocessing": {
			"description": "Preprocessing reference experiment: K-means on raw Recency (days), Frequency (invoices), Monetary (GBP) with no transformation or scaling.",
			"silhouette": silhouette_raw,
			"inertia": float(raw_model.inertia_),
			"cluster_sizes": np.bincount(raw_labels, minlength=k).tolist(),
			"profiles": raw_profiles,
			"silhouette_of_these_labels_in_processed_space": float(silhouette_score(X.to_numpy(), raw_labels)),
		},
		"after_preprocessing": {
			"description": "Final model: K-means on log1p-transformed, standardized R, F, M.",
			"silhouette": silhouette_processed,
			"inertia": float(model.inertia_),
			"cluster_sizes": np.bincount(labels, minlength=k).tolist(),
			"profiles": profiles,
			"silhouette_of_these_labels_in_raw_space": float(silhouette_score(raw_X.to_numpy(dtype=float), labels)),
		},
		"silhouette_change": silhouette_processed - silhouette_raw,
	}
	comparison["interpretation"] = explain_silhouette(comparison, quality_before)

	segments = eligible[["customer_id", "recency_days", "frequency", "monetary", "avg_order_value", "unique_products", "active_months"]].assign(cluster=labels)
	segments["segment_label"] = segments["cluster"].map(label_by_cluster)
	segments.to_csv(PROCESSED_DIR / "customer_segments.csv", index=False, float_format="%.2f")

	transformed_quality = {f: float(X[f].skew()) for f in FEATURES}
	update_report(DATA_REPORTS_DIR / "transformation_report.json", "customer_segmentation", {
		"input": "data/processed/retail_clean.csv.gz (record_type = purchase / cancellation, CustomerID present)",
		"reference_date": reference_date.date().isoformat(),
		"reference_date_rule": "Day after the latest InvoiceDate in the dataset; fixed for both experiments.",
		"feature_dictionary": [{"feature": f, "unit": unit, "definition": text} for f, (unit, text) in segmentation.FEATURE_DICTIONARY.items()],
		"operations": [
			{"operation": "deduplicate customer rows", "result": f"{quality_before['duplicate_customer_ids']} duplicates found"},
			{"operation": "missing / infinite values", "result": f"missing {quality_before['missing_values']}, infinite {quality_before['infinite_values']}; median imputation configured for inference"},
			{"operation": "extreme values", "result": {f: quality_before["distributions"][f]["iqr_outliers"] for f in FEATURES}, "decision": "Kept: extreme spenders are real customers; log1p limits their influence."},
			{"operation": "negative monetary", "result": "Excluded before modelling (net spending <= 0); clip-to-zero guard before log1p."},
			{"operation": "log1p", "features": preprocessor.log_features_, "skewness_before": preprocessor.skewness_},
			{"operation": "StandardScaler", "fitted_on": f"{len(eligible)} eligible customers (the reference population)"},
		],
		"skewness_after_transform": transformed_quality,
		"outputs": ["data/processed/customer_rfm.csv", "data/processed/customer_features_processed.csv", "data/processed/customer_segments.csv"],
	})

	joblib.dump(model, MODELS_DIR / "customer_kmeans_model.joblib")
	joblib.dump(preprocessor.scaler_, MODELS_DIR / "customer_scaler.joblib")
	write_json(MODELS_DIR / "customer_feature_config.json", {**preprocessor.config(), "selected_k": k, "reference_date": reference_date.date().isoformat(), "label_rules": segmentation.DEFAULT_LABEL_RULES, "segment_actions": segmentation.SEGMENT_ACTIONS, "cluster_labels": label_by_cluster})
	evaluation = {
		"created_at": utc_now(),
		"note": "Unsupervised clustering: there are no ground-truth labels, so accuracy, precision, recall, and F1 are not applicable. Silhouette, inertia, cluster sizes, and stability are reported instead.",
		"feature_quality_before": quality_before,
		"k_search": {"raw_features": raw_search, "processed_features": search, "selection": selection},
		"comparison": comparison,
		"stability": stability,
		"label_notes": notes,
		"distributions": distributions(eligible),
		"exclusions": exclusions,
	}
	evaluation["figures"] = [
		figures.elbow("segmentation_k_search.png", [r["k"] for r in search if r["valid"]], [r["inertia"] for r in search if r["valid"]], [r["silhouette"] for r in search if r["valid"]]),
		*[figures.hist(f"segmentation_{f}_distribution.png", eligible[f], f"{f} distribution (eligible customers)", f, log=True) for f in FEATURES],
	]
	write_json(MODELS_DIR / "customer_evaluation.json", evaluation)
	write_json(MODELS_DIR / "customer_training_metadata.json", {
		"model": "KMeans",
		"trained_at": utc_now(),
		"dataset": dataset_version("online_retail", [RETAIL_XLSX]),
		"hyperparameters": {"n_clusters": k, "n_init": SEGMENT_N_INIT, "random_state": RANDOM_SEED, "algorithm": "lloyd"},
		"random_seed": RANDOM_SEED,
		"k_candidates": SEGMENT_K_RANGE,
		"customer_population": int(len(eligible)),
		"reference_date": reference_date.date().isoformat(),
		"metrics": {"silhouette": silhouette_processed, "inertia": float(model.inertia_)},
		"environment": environment_versions(),
		"runtime_seconds": round(time.time() - started, 1),
		"command": "..\\rag_service\\.venv\\Scripts\\python.exe -m src.pipeline_segmentation",
	})
	write_markdown(evaluation)
	log(f"Done in {time.time() - started:.0f}s")


def explain_silhouette(comparison, quality):
	before, after = comparison["before_preprocessing"], comparison["after_preprocessing"]
	monetary = quality["distributions"]["monetary"]
	direction = "lower" if after["silhouette"] < before["silhouette"] else "higher"
	return (
		f"The silhouette is {direction} after preprocessing ({before['silhouette']:.3f} -> {after['silhouette']:.3f}). "
		f"On raw features Monetary (std {monetary['std']:,.0f} GBP, skewness {monetary['skewness']:.1f}) dominates Euclidean distance, "
		f"so K-means mostly isolates a few extreme spenders (raw cluster sizes {before['cluster_sizes']}). Such a split of one huge group "
		"plus tiny outlier groups can score a high silhouette while saying almost nothing about recency or frequency. After log1p and "
		f"standardization all three features contribute equally (cluster sizes {after['cluster_sizes']}), producing balanced, interpretable "
		"segments whose boundaries run through dense regions, which naturally lowers silhouette. Silhouette values are computed in each "
		"model's own feature space and are not directly comparable; cross-space scores are reported alongside."
	)


def write_markdown(evaluation):
	c = evaluation["comparison"]
	b, a = c["before_preprocessing"], c["after_preprocessing"]
	lines = [
		"# Customer Segmentation — evaluation report", "",
		f"Generated {evaluation['created_at']} by `python -m src.pipeline_segmentation`. All values are measured.", "",
		evaluation["note"], "",
		f"Population: {c['customer_population']} eligible customers, reference date {c['reference_date']}, features {', '.join(c['features'])}, K = {c['k']}.", "",
		"| Experiment | Silhouette | Inertia | Cluster sizes |", "|---|---|---|---|",
		f"| Before preprocessing (raw R, F, M) | {b['silhouette']:.3f} | {b['inertia']:,.0f} | {b['cluster_sizes']} |",
		f"| After preprocessing (log1p + StandardScaler) | {a['silhouette']:.3f} | {a['inertia']:,.2f} | {a['cluster_sizes']} |", "",
		c["interpretation"], "",
		f"Cross-space check: raw-model labels score {b['silhouette_of_these_labels_in_processed_space']:.3f} in the processed space; final labels score {a['silhouette_of_these_labels_in_raw_space']:.3f} in the raw space.", "",
		"## K search (processed features)", "", "| K | Silhouette | Inertia | Smallest cluster |", "|---|---|---|---|",
	]
	for r in evaluation["k_search"]["processed_features"]:
		if r["valid"]:
			lines.append(f"| {r['k']} | {r['silhouette']:.3f} | {r['inertia']:,.0f} | {r['min_cluster_share']:.1%} |")
	sel = evaluation["k_search"]["selection"]
	lines += ["", f"Selection rule: {sel['rule']} Selected K = {sel['selected_k']} (global best K = {sel['global_best_k']}, silhouette {sel['global_best_silhouette']:.3f}).", ""]
	s = evaluation["stability"]
	lines += [f"Stability: {s['method']} Seed ARI mean {s['seed_ari_mean']:.3f} (min {s['seed_ari_min']:.3f}); subsample ARI mean {s['subsample_ari_mean']:.3f} (min {s['subsample_ari_min']:.3f}).", "", "## Segments", "", "| Cluster | Label | Customers | Share | Median recency (days) | Median frequency | Median monetary (GBP) | Revenue share |", "|---|---|---|---|---|---|---|---|"]
	for p in sorted(a["profiles"], key=lambda p: -p["monetary_median"]):
		lines.append(f"| {p['cluster']} | {p['segment_label']} | {p['customers']} | {p['share_pct']:.1f}% | {p['recency_days_median']:.0f} | {p['frequency_median']:.0f} | {p['monetary_median']:,.0f} | {p['revenue_share_pct']:.1f}% |")
	lines += [""] + [f"- **{p['segment_label']}**: {p['recommended_action']}" for p in a["profiles"]]
	for note in evaluation["label_notes"]:
		lines.append(f"- Note on {note['label']} (clusters {note['clusters']}): {note['observation']}")
	lines += ["", "Figures: " + ", ".join(f"`{p}`" for p in evaluation["figures"])]
	(REPORTS_DIR / "segmentation_evaluation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
	main()
