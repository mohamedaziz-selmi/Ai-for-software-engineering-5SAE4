"""Train and compare TF-IDF Logistic Regression and Linear SVM sentiment models."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "processed"
MODELS = ROOT / "models"
LABELS = ["negative", "neutral", "positive"]


def load_split(name: str) -> pd.DataFrame:
    path = DATA / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run prepare_sentiment_data.py first.")
    frame = pd.read_csv(path)
    required = {"review_text", "sentiment"}
    if not required.issubset(frame.columns):
        raise ValueError(f"{path} must contain {required}.")
    return frame


def vectorizer() -> TfidfVectorizer:
    # No stopword removal: negations and natural review language are meaningful.
    return TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.98, sublinear_tf=True, max_features=100_000)


def metrics(y_true, y_pred) -> dict:
    precision, recall, f1, support = precision_recall_fscore_support(y_true, y_pred, labels=LABELS, zero_division=0)
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "macro_f1": f1_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0),
        "per_class": {label: {"precision": float(p), "recall": float(r), "f1": float(score), "support": int(count)} for label, p, r, score, count in zip(LABELS, precision, recall, f1, support)},
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=LABELS).tolist(),
        "labels": LABELS,
    }


def write_evaluation(name: str, results: dict) -> None:
    (MODELS / f"{name}_evaluation.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    pd.DataFrame(results["confusion_matrix"], index=LABELS, columns=LABELS).to_csv(MODELS / f"{name}_confusion_matrix.csv", index_label="actual\\predicted")


def main() -> None:
    MODELS.mkdir(exist_ok=True)
    train, validation, test = (load_split(name) for name in ("train", "validation", "test"))
    candidates = {
        "logistic_regression": LogisticRegression(max_iter=2000, class_weight="balanced", n_jobs=-1, random_state=42),
        # Calibration makes LinearSVC confidence estimates usable at inference.
        "linear_svm": CalibratedClassifierCV(LinearSVC(class_weight="balanced", random_state=42), method="sigmoid", cv=3),
    }
    trained, validation_results = {}, {}
    for name, classifier in candidates.items():
        model = Pipeline([( "tfidf", vectorizer()), ("classifier", classifier)])
        model.fit(train.review_text, train.sentiment)
        result = metrics(validation.sentiment, model.predict(validation.review_text))
        validation_results[name] = result
        trained[name] = model
        write_evaluation(f"validation_{name}", result)
        print(f"{name}: validation macro F1={result['macro_f1']:.4f}, accuracy={result['accuracy']:.4f}")

    winner = max(validation_results, key=lambda name: validation_results[name]["macro_f1"])
    model = trained[winner]
    test_result = metrics(test.sentiment, model.predict(test.review_text))
    write_evaluation("test_selected_model", test_result)

    # Persist separately as requested; API loads these artifacts without retraining.
    joblib.dump(model.named_steps["tfidf"], MODELS / "tfidf_vectorizer.joblib")
    joblib.dump(model.named_steps["classifier"], MODELS / "sentiment_classifier.joblib")
    summary = {"selected_model": winner, "selection_metric": "validation macro_f1", "validation": validation_results, "final_test": test_result, "labels": LABELS}
    (MODELS / "model_report.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Selected {winner}; final test macro F1={test_result['macro_f1']:.4f}, accuracy={test_result['accuracy']:.4f}")


if __name__ == "__main__":
    main()
