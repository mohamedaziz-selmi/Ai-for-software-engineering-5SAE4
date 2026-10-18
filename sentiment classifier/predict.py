"""Load the saved sentiment artifacts and predict one review."""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib

MODELS = Path(__file__).resolve().parent / "models"
_CACHED_TFIDF = None
_CACHED_CLASSIFIER = None


def load_artifacts():
    global _CACHED_TFIDF, _CACHED_CLASSIFIER
    if _CACHED_TFIDF is not None and _CACHED_CLASSIFIER is not None:
        return _CACHED_TFIDF, _CACHED_CLASSIFIER
    try:
        _CACHED_TFIDF = joblib.load(MODELS / "tfidf_vectorizer.joblib")
        _CACHED_CLASSIFIER = joblib.load(MODELS / "sentiment_classifier.joblib")
        return _CACHED_TFIDF, _CACHED_CLASSIFIER
    except FileNotFoundError as error:
        raise RuntimeError("Model artifacts are missing. Run train_model.py first.") from error


def predict_review(text: str) -> dict:
    if not text or not text.strip():
        raise ValueError("Review text cannot be empty.")
    tfidf, classifier = load_artifacts()
    features = tfidf.transform([text.strip()])
    label = classifier.predict(features)[0]
    probabilities = classifier.predict_proba(features)[0]
    scores = {str(name): round(float(probability), 4) for name, probability in zip(classifier.classes_, probabilities)}
    return {"sentiment": str(label), "confidence": round(max(scores.values()), 4), "probabilities": scores}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Predict one customer review sentiment.")
    parser.add_argument("review")
    print(predict_review(parser.parse_args().review))
