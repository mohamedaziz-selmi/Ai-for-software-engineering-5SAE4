from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from xgboost import XGBRegressor

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "dataset" / "Final_Upwork_Dataset.csv"
REPORTS_DIR = ROOT / "reports"
ARTIFACTS_DIR = ROOT / "artifacts"


def parse_money(value):
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, float, np.integer, np.floating)):
        num = float(value)
        return num if np.isfinite(num) else np.nan
    txt = str(value).strip()
    if txt.lower() in {"nan", "n/a", "na", "none", "null", ""}:
        return np.nan
    txt = txt.replace("$", "").replace(",", "").replace("USD", "").replace("usd", "")
    txt = txt.replace("(", "").replace(")", "").replace(" ", "")
    try:
        num = float(txt)
    except ValueError:
        return np.nan
    return num if np.isfinite(num) else np.nan


def build_audit(raw_df: pd.DataFrame) -> dict:
    numeric_target = pd.to_numeric(raw_df["Job_Cost"].astype(str).str.replace(r"[$,\s]", "", regex=True), errors="coerce")
    audit = {
        "rows": int(raw_df.shape[0]),
        "columns": int(raw_df.shape[1]),
        "duplicate_rows": int(raw_df.duplicated().sum()),
        "missing_values_before": {k: int(v) for k, v in raw_df.isna().sum().items()},
        "target_missing": int(raw_df["Job_Cost"].isna().sum()),
        "target_non_numeric": int(numeric_target.isna().sum()),
        "job_cost_summary": {
            "min": float(numeric_target.min()) if numeric_target.notna().any() else None,
            "max": float(numeric_target.max()) if numeric_target.notna().any() else None,
        },
    }
    return audit


def clean_budget_dataset(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    working = raw_df.copy()
    before = build_audit(working)

    working = working.drop_duplicates().copy()
    working["Job Title"] = working["Job Title"].fillna("Unknown").astype(str).str.strip()
    working["Description"] = working["Description"].fillna("No description provided").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()

    category_cols = [f"Category_{idx}" for idx in range(1, 10)]
    for col in category_cols:
        working[col] = working[col].fillna("Unknown").astype(str).str.strip()
    working["category_text"] = working[category_cols].astype(str).apply(lambda row: " | ".join(v for v in row if v not in {"nan", "Unknown", ""}), axis=1)

    for col in ["Payment_type", "EX_level_demand", "Search_Keyword", "Client_Country", "Payment_Situation"]:
        working[col] = working[col].fillna("Unknown").astype(str).str.strip()
    working["Time_Limitation"] = working["Time_Limitation"].fillna("Unknown").astype(str).str.strip()

    working["Job_Cost_clean"] = working["Job_Cost"].map(parse_money)
    valid_budget_mask = working["Job_Cost_clean"].notna() & (working["Job_Cost_clean"] > 0) & (working["Job_Cost_clean"] <= 1_000_000)
    excluded_rows = working.loc[~valid_budget_mask].copy()
    working = working.loc[valid_budget_mask].copy().reset_index(drop=True)

    working["target"] = working["Job_Cost_clean"].astype(float)
    working["project_text"] = (
        working["Job Title"].fillna("").astype(str)
        + " "
        + working["Description"].fillna("").astype(str)
        + " "
        + working["category_text"].fillna("").astype(str)
    ).str.replace(r"\s+", " ", regex=True).str.strip()
    working = working.dropna(subset=["target"]).copy()

    after = {
        "rows": int(working.shape[0]),
        "columns": int(working.shape[1]),
        "duplicate_rows": int(working.duplicated().sum()),
        "missing_values_after": {k: int(v) for k, v in working.isna().sum().items()},
        "excluded_rows": int(excluded_rows.shape[0]),
        "excluded_reasons": {
            "missing_or_invalid_budget": int((~valid_budget_mask).sum()),
        },
        "target_summary": {
            "min": float(working["target"].min()),
            "max": float(working["target"].max()),
            "mean": float(working["target"].mean()),
        },
    }
    report = {
        "before": before,
        "after": after,
        "excluded_rows_preview": excluded_rows.head(5).to_dict(orient="records"),
    }
    return working, report


def build_model_pipeline():
    cat_cols = [
        "EX_level_demand",
        "Search_Keyword",
        "Payment_type",
        "Client_Country",
        "Time_Limitation",
        "Category_1",
        "Category_2",
        "Category_3",
        "Category_4",
        "Category_5",
        "Category_6",
    ]

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", min_frequency=20)),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", categorical_transformer, cat_cols),
            (
                "text",
                TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_features=10000, stop_words="english", sublinear_tf=True),
                "project_text",
            ),
        ]
    )
    return preprocessor


def train_and_evaluate(cleaned_df: pd.DataFrame):
    X = cleaned_df[
        [
            "EX_level_demand",
            "Search_Keyword",
            "Payment_type",
            "Client_Country",
            "Time_Limitation",
            "Category_1",
            "Category_2",
            "Category_3",
            "Category_4",
            "Category_5",
            "Category_6",
            "project_text",
        ]
    ]
    y = cleaned_df["target"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    rf = Pipeline(
        steps=[
            ("preprocessor", build_model_pipeline()),
            ("model", RandomForestRegressor(n_estimators=180, max_depth=18, random_state=42, n_jobs=-1)),
        ]
    )
    rf.fit(X_train, np.log1p(y_train))
    rf_pred = np.expm1(rf.predict(X_test))

    xgb = Pipeline(
        steps=[
            ("preprocessor", build_model_pipeline()),
            (
                "model",
                XGBRegressor(
                    n_estimators=350,
                    max_depth=6,
                    learning_rate=0.05,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    objective="reg:squarederror",
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    xgb.fit(X_train, np.log1p(y_train))
    xgb_pred = np.expm1(xgb.predict(X_test))

    metrics = {
        "RandomForest": {
            "MAE": float(mean_absolute_error(y_test, rf_pred)),
            "RMSE": float(np.sqrt(mean_squared_error(y_test, rf_pred))),
            "R2": float(r2_score(y_test, rf_pred)),
        },
        "XGBoost": {
            "MAE": float(mean_absolute_error(y_test, xgb_pred)),
            "RMSE": float(np.sqrt(mean_squared_error(y_test, xgb_pred))),
            "R2": float(r2_score(y_test, xgb_pred)),
        },
    }
    return rf, xgb, metrics


def save_reports(cleaned_df: pd.DataFrame, report: dict, metrics: dict):
    REPORTS_DIR.mkdir(exist_ok=True, parents=True)
    ARTIFACTS_DIR.mkdir(exist_ok=True, parents=True)

    audit_md = f"""# Project Budget Data Audit Report

## Source
- File: `{DATA_PATH}`
- Rows: {report['before']['rows']}
- Columns: {report['before']['columns']}

## Duplicate and missing values
- Exact duplicate rows: {report['before']['duplicate_rows']}
- Target missing values before cleaning: {report['before']['target_missing']}
- Rows excluded for invalid or missing `Job_Cost`: {report['after']['excluded_rows']}

## Final dataset
- Final rows: {report['after']['rows']}
- Final columns: {report['after']['columns']}
- Missing values in final set: {report['after']['missing_values_after']}

## Cleaning decisions
1. Drop exact duplicate records.
2. Parse `Job_Cost` as currency values and remove invalid/missing/non-positive values or values above $1,000,000.
3. Keep only budget labels that represent actual job budgets; exclude rows with missing or impossible values.
4. Impute missing categorical inputs and fit a TF-IDF transform on training text only.
5. Exclude post-listing outcomes (spend, applicant/freelancer counts, ratings, and feedback) to reduce leakage.
6. Train against `log1p(Job_Cost)` and convert predictions back to dollars.

## Model metrics
- RandomForest: MAE={metrics['RandomForest']['MAE']:.2f}, RMSE={metrics['RandomForest']['RMSE']:.2f}, R2={metrics['RandomForest']['R2']:.4f}
- XGBoost: MAE={metrics['XGBoost']['MAE']:.2f}, RMSE={metrics['XGBoost']['RMSE']:.2f}, R2={metrics['XGBoost']['R2']:.4f}
"""
    (REPORTS_DIR / "budget_data_audit_report.md").write_text(audit_md, encoding="utf-8")

    cleaning_md = f"""# Budget Cleaning Report

## Original vs final shape
- Original rows: {report['before']['rows']}
- Original columns: {report['before']['columns']}
- Final rows: {report['after']['rows']}
- Final columns: {report['after']['columns']}

## Missing values
- Missing before: {report['before']['missing_values_before']}
- Missing after: {report['after']['missing_values_after']}

## Duplicate rows
- Before cleaning: {report['before']['duplicate_rows']}
- After cleaning: {report['after']['duplicate_rows']}

## Transformations applied
- parsed the target currency string into numeric dollars
- removed exact duplicates
- cleaned title/description whitespace and combined them with listed categories
- imputed missing categories and fit one-hot/TF-IDF transformations on training data
- excluded missing/non-positive and greater-than-$1,000,000 target values

## Exclusions
- Rows removed because target budget was missing or invalid: {report['after']['excluded_rows']}
- Reason: project budget could not be used as a valid supervised label.
- Post-listing outcome fields (realized spending, applicant counts, ratings and feedback) are deliberately excluded from model inputs.

## Decision rationale
`Job_Cost` is the clearest available budget label. The models use listing-time information only; `Spent($)`, applicant/freelancer counts, ratings and feedback are excluded to avoid target leakage.
"""
    (REPORTS_DIR / "budget_cleaning_report.md").write_text(cleaning_md, encoding="utf-8")

    cleaned_df.to_csv(ARTIFACTS_DIR / "budget_cleaned_dataset.csv", index=False)
    with open(ARTIFACTS_DIR / "budget_metrics.json", "w", encoding="utf-8") as fp:
        json.dump(metrics, fp, indent=2)


def main():
    raw_df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    cleaned_df, report = clean_budget_dataset(raw_df)
    rf_model, xgb_model, metrics = train_and_evaluate(cleaned_df)
    save_reports(cleaned_df, report, metrics)

    joblib.dump(rf_model, ARTIFACTS_DIR / "random_forest_budget_model.joblib")
    joblib.dump(xgb_model, ARTIFACTS_DIR / "xgboost_budget_model.joblib")
    print("Budget pipeline complete")
    print(metrics)


if __name__ == "__main__":
    main()
