"""Inspect, clean, standardize, and split local sentiment-review datasets.

No model is trained here. Input files are read only; all outputs are written to
data/processed. Run from this folder or pass --input-dir explicitly.
"""

from __future__ import annotations

import argparse
import html
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

SEED = 42
LABELS = {"positive", "negative", "neutral"}
WHITESPACE = re.compile(r"\s+")
HTML_TAGS = re.compile(r"<[^>]+>")


def locate_csvs(input_dir: Path) -> list[Path]:
    """Find CSVs while excluding generated data and unrelated dictionary files."""
    return [
        path for path in sorted(input_dir.rglob("*.csv"))
        if "processed" not in path.parts and "data_dictionary" not in path.name.lower()
    ]


def load_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode {path.name} with supported encodings.")


def column_lookup(frame: pd.DataFrame) -> dict[str, str]:
    return {re.sub(r"[^a-z0-9]", "", column.lower()): column for column in frame.columns}


def choose_column(frame: pd.DataFrame, candidates: list[str], role: str, file_name: str) -> str:
    lookup = column_lookup(frame)
    for candidate in candidates:
        if candidate in lookup:
            return lookup[candidate]
    raise ValueError(f"{file_name}: could not identify {role}. Columns found: {list(frame.columns)}")


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = html.unescape(str(value))
    text = HTML_TAGS.sub(" ", text)
    return WHITESPACE.sub(" ", text).strip()


def inspection_block(path: Path, frame: pd.DataFrame) -> str:
    lines = [f"FILE: {path.name}", f"Rows: {len(frame):,}", f"Columns: {list(frame.columns)}", "Data types:"]
    lines.extend(f"  - {column}: {dtype}" for column, dtype in frame.dtypes.items())
    lines.append("Missing values:")
    lines.extend(f"  - {column}: {count:,}" for column, count in frame.isna().sum().items())
    lines.append("Sample records:")
    lines.append(frame.head(3).to_string(index=False))
    return "\n".join(lines)


def identify_dataset(path: Path, frame: pd.DataFrame) -> str:
    lookup = column_lookup(frame)
    if "reviewtext" in lookup and "rating" in lookup:
        return "womens_ecommerce"
    if "review" in lookup and "sentiment" in lookup:
        return "multidomain_reviews"
    raise ValueError(f"{path.name}: not a recognized dataset schema; cannot safely infer label semantics.")


def standardize_womens(frame: pd.DataFrame, source_file: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    text_col = choose_column(frame, ["reviewtext"], "review-text column", source_file)
    rating_col = choose_column(frame, ["rating"], "rating column", source_file)
    ratings = pd.to_numeric(frame[rating_col], errors="coerce")
    sentiment = pd.Series(np.select([ratings.isin([1, 2]), ratings.eq(3), ratings.isin([4, 5])], ["negative", "neutral", "positive"], default=""), index=frame.index)
    standardized = pd.DataFrame({"review_text": frame[text_col].map(clean_text), "sentiment": sentiment, "source_dataset": "womens_ecommerce"})
    metadata = frame.copy()
    metadata.insert(0, "source_file", source_file)
    metadata.insert(1, "source_dataset", "womens_ecommerce")
    metadata.insert(2, "original_row", frame.index)
    return standardized, metadata, {"text_column": text_col, "label_column": rating_col, "unexpected_ratings": int((~ratings.isin([1, 2, 3, 4, 5]) & ratings.notna()).sum())}


def standardize_multidomain(frame: pd.DataFrame, source_file: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    text_col = choose_column(frame, ["review", "reviewtext", "text"], "review-text column", source_file)
    label_col = choose_column(frame, ["sentiment", "label"], "sentiment column", source_file)
    raw_labels = frame[label_col].astype("string").str.strip().str.casefold()
    verified = {"positive": "positive", "negative": "negative", "neutral": "neutral"}
    sentiment = raw_labels.map(verified).fillna("")
    standardized = pd.DataFrame({"review_text": frame[text_col].map(clean_text), "sentiment": sentiment, "source_dataset": "multidomain_reviews"})
    metadata = frame.copy()
    metadata.insert(0, "source_file", source_file)
    metadata.insert(1, "source_dataset", "multidomain_reviews")
    metadata.insert(2, "original_row", frame.index)
    return standardized, metadata, {"text_column": text_col, "label_column": label_col, "raw_label_counts": raw_labels.value_counts(dropna=False).to_dict(), "unverified_labels": int((~raw_labels.isin(verified) & raw_labels.notna()).sum())}


def distribution(frame: pd.DataFrame, stage: str) -> pd.DataFrame:
    counts = frame.groupby(["source_dataset", "sentiment"], dropna=False).size().rename("count").reset_index()
    counts["stage"] = stage
    counts["percentage_within_stage"] = (counts["count"] / max(len(frame), 1) * 100).round(3)
    return counts[["stage", "source_dataset", "sentiment", "count", "percentage_within_stage"]]


def main(input_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = locate_csvs(input_dir)
    if not paths:
        raise FileNotFoundError(f"No input CSV files found under {input_dir}")

    inspection, standardized_frames, metadata_frames, findings = [], [], [], []
    for path in paths:
        frame = load_csv(path)
        inspection.append(inspection_block(path, frame))
        kind = identify_dataset(path, frame)
        if kind == "womens_ecommerce":
            standardized, metadata, detail = standardize_womens(frame, path.name)
        else:
            standardized, metadata, detail = standardize_multidomain(frame, path.name)
        detail.update({"file": path.name, "dataset": kind, "input_rows": len(frame)})
        findings.append(detail)
        standardized_frames.append(standardized)
        metadata_frames.append(metadata)

    (output_dir / "inspection_report.txt").write_text("\n\n".join(inspection), encoding="utf-8")
    raw = pd.concat(standardized_frames, ignore_index=True)
    metadata = pd.concat(metadata_frames, ignore_index=True)
    before_distribution = distribution(raw, "before_cleaning")

    summary: Counter[str] = Counter(input_rows=len(raw))
    empty_mask = raw["review_text"].eq("")
    invalid_mask = ~raw["sentiment"].isin(LABELS)
    summary["empty_reviews_removed"] = int(empty_mask.sum())
    summary["invalid_or_unverified_labels_removed"] = int(invalid_mask.sum())
    clean = raw.loc[~empty_mask & ~invalid_mask].copy()

    duplicate_mask = clean.duplicated("review_text", keep="first")
    summary["exact_duplicates_removed"] = int(duplicate_mask.sum())
    clean = clean.loc[~duplicate_mask].reset_index(drop=True)

    # A conflicting text cannot safely train a single-label classifier.
    all_labeled = raw.loc[~empty_mask & ~invalid_mask]
    conflicting_texts = all_labeled.groupby("review_text")["sentiment"].nunique()
    conflicts = set(conflicting_texts[conflicting_texts > 1].index)
    conflict_mask = clean["review_text"].isin(conflicts)
    summary["label_conflicts_removed"] = int(conflict_mask.sum())
    clean = clean.loc[~conflict_mask].reset_index(drop=True)
    summary["final_rows"] = len(clean)

    # Exact duplicates were removed before splitting, so no identical review can leak.
    train, temporary = train_test_split(clean, test_size=0.30, random_state=SEED, stratify=clean["sentiment"])
    validation, test = train_test_split(temporary, test_size=0.50, random_state=SEED, stratify=temporary["sentiment"])
    for frame in (train, validation, test):
        frame.sort_index(inplace=True)

    clean.to_csv(output_dir / "combined_reviews_clean.csv", index=False)
    train.to_csv(output_dir / "train.csv", index=False)
    validation.to_csv(output_dir / "validation.csv", index=False)
    test.to_csv(output_dir / "test.csv", index=False)
    metadata.to_csv(output_dir / "source_metadata.csv", index=False)
    pd.concat([before_distribution, distribution(clean, "after_cleaning"), distribution(train, "train"), distribution(validation, "validation"), distribution(test, "test")]).to_csv(output_dir / "class_distribution.csv", index=False)

    warnings = []
    for source, subset in clean.groupby("source_dataset"):
        shares = subset["sentiment"].value_counts(normalize=True)
        if shares.max() > 0.80:
            warnings.append(f"{source}: strong class imbalance ({shares.idxmax()} = {shares.max():.1%}).")
    report = ["SENTIMENT DATA CLEANING REPORT", f"Random seed: {SEED}", "", "Detected schemas:"]
    report.extend(f"- {item['file']}: {item}" for item in findings)
    report.extend(["", "Cleaning summary:"])
    report.extend(f"- {key.replace('_', ' ')}: {value:,}" for key, value in summary.items())
    report.extend(["", f"Split sizes: train={len(train):,}, validation={len(validation):,}, test={len(test):,}", "Exact duplicate leakage check: passed (duplicates were removed before stratified splitting).", "Near duplicates: not removed; only exact normalized duplicates were removed to avoid deleting legitimate similar reviews.", "Text policy: HTML/entities and repeated whitespace normalized; punctuation, negations, emojis, stopwords, and word forms preserved.", "Warnings:"])
    report.extend(f"- {warning}" for warning in warnings) if warnings else report.append("- None")
    (output_dir / "cleaning_report.txt").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare local three-class sentiment datasets without training a model.")
    parser.add_argument("--input-dir", type=Path, default=Path(__file__).resolve().parent, help="Folder containing downloaded datasets.")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "data" / "processed", help="Output directory for cleaned data and reports.")
    args = parser.parse_args()
    main(args.input_dir, args.output_dir)
