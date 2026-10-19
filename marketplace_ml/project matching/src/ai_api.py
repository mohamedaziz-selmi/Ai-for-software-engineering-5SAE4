from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

AI_ROOT = Path(__file__).resolve().parents[2]
BUDGET_ARTIFACTS = AI_ROOT / "project budjet" / "artifacts"
MATCHING_ROOT = AI_ROOT / "project matching"
MATCHING_ARTIFACTS = MATCHING_ROOT / "artifacts"
RESUME_DATA = MATCHING_ROOT / "dataset" / "Resume" / "Resume.csv"

app = FastAPI(title="Freelance Marketplace ML Demo", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8766", "http://127.0.0.1:8766"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class MatchRequest(BaseModel):
    project_text: str = Field(min_length=3, max_length=8000)
    model: Literal["tfidf", "semantic"] = "semantic"
    k: int = Field(default=5, ge=3, le=10)

    @field_validator("project_text")
    @classmethod
    def require_non_whitespace_text(cls, value: str) -> str:
        text = re.sub(r"\s+", " ", value).strip()
        if len(text) < 3:
            raise ValueError("Enter a project brief with at least 3 non-space characters.")
        return text


class BudgetRequest(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    category: str = Field(min_length=2, max_length=100)
    skills: str = Field(default="", max_length=500)
    experience_level: Literal["Entry level", "Intermediate", "Expert"] = "Intermediate"
    payment_type: Literal["Fixed-price", "Hourly"] = "Fixed-price"
    model: Literal["random_forest", "xgboost"] = "random_forest"

    @field_validator("title", "description", "category", "skills")
    @classmethod
    def trim_text_inputs(cls, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    @field_validator("title", "description", "category")
    @classmethod
    def require_non_whitespace_inputs(cls, value: str) -> str:
        if not value:
            raise ValueError("This field cannot be blank.")
        return value


def _clean_resume_text(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    text = re.sub(r"<[^>]*>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@lru_cache(maxsize=2)
def _budget_model(model_name: str):
    model_filename = (
        "random_forest_budget_model.joblib"
        if model_name == "random_forest"
        else "xgboost_budget_model.joblib"
    )
    model_path = BUDGET_ARTIFACTS / model_filename
    if not model_path.is_file():
        raise FileNotFoundError(
            f"Budget model artifact is missing: {model_path}. Run the budget training script first."
        )
    return joblib.load(model_path)


@lru_cache(maxsize=1)
def _matching_resources():
    if not RESUME_DATA.is_file():
        raise FileNotFoundError(f"Resume data was not found: {RESUME_DATA}")
    if not (MATCHING_ARTIFACTS / "resume_embeddings.npy").is_file():
        raise FileNotFoundError("Missing resume_embeddings.npy; run the matching pipeline first.")
    if not (MATCHING_ARTIFACTS / "sentence_transformer_joblib.joblib").is_file():
        raise FileNotFoundError("Missing Sentence Transformer artifact; run the matching pipeline first.")

    resumes = pd.read_csv(RESUME_DATA, encoding="utf-8-sig")
    resumes["resume_text"] = resumes["Resume_str"].map(_clean_resume_text)
    resumes["Category"] = resumes["Category"].fillna("Other").astype(str).str.replace("-", " ").str.title()
    embeddings = np.load(MATCHING_ARTIFACTS / "resume_embeddings.npy")
    if len(resumes) != len(embeddings):
        raise RuntimeError(
            f"Resume/embedding count mismatch ({len(resumes)} records, {len(embeddings)} vectors); retrain the matching pipeline."
        )

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=2,
        max_features=5000,
        stop_words="english",
    )
    tfidf_matrix = vectorizer.fit_transform(resumes["resume_text"].tolist())
    sentence_model = joblib.load(MATCHING_ARTIFACTS / "sentence_transformer_joblib.joblib")
    return resumes, vectorizer, tfidf_matrix, sentence_model, embeddings


def _budget_features(request: BudgetRequest, feature_names: list[str]) -> pd.DataFrame:
    category_columns = [f"Category_{index}" for index in range(1, 10)]
    category_values = [request.category, *[skill.strip() for skill in request.skills.split(",") if skill.strip()]]
    category_values = list(dict.fromkeys(category_values))
    features: dict[str, object] = {
        "EX_level_demand": request.experience_level,
        "Search_Keyword": request.category,
        "Payment_type": request.payment_type,
        "Payment_Situation": "Unknown",
        "Client_Country": "Unknown",
        "Time_Limitation": "Unknown",
        "project_text": re.sub(
            r"\s+",
            " ",
            f"{request.title} {request.description} {request.category} {request.skills}",
        ).strip(),
    }
    features.update({
        column: category_values[index] if index < len(category_values) else "Unknown"
        for index, column in enumerate(category_columns)
    })
    return pd.DataFrame([{name: features.get(name, np.nan) for name in feature_names}])


@app.get("/api/health")
def health():
    budget_available = all(
        (BUDGET_ARTIFACTS / name).is_file()
        for name in ("random_forest_budget_model.joblib", "xgboost_budget_model.joblib")
    )
    matching_available = all(
        (MATCHING_ARTIFACTS / name).is_file()
        for name in ("resume_embeddings.npy", "sentence_transformer_joblib.joblib")
    ) and RESUME_DATA.is_file()
    return {
        "status": "ready" if budget_available and matching_available else "missing_artifacts",
        "models": {
            "budget": budget_available,
            "matching": matching_available,
        },
    }


@app.post("/api/match")
def match_freelancers(request: MatchRequest):
    try:
        resumes, vectorizer, tfidf_matrix, sentence_model, embeddings = _matching_resources()
    except (FileNotFoundError, RuntimeError, OSError, ValueError) as error:
        raise HTTPException(status_code=503, detail=f"Matching model unavailable: {error}") from error

    try:
        if request.model == "tfidf":
            project_vector = vectorizer.transform([request.project_text])
            scores = cosine_similarity(project_vector, tfidf_matrix).ravel()
            model_label = "TF-IDF cosine similarity"
        else:
            query_embedding = sentence_model.encode(
                [request.project_text],
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            scores = np.asarray(embeddings @ query_embedding[0], dtype=float)
            model_label = "Sentence Transformer cosine similarity"
    except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as error:
        raise HTTPException(status_code=503, detail=f"Matching model could not rank profiles: {error}") from error

    ranked = np.argsort(scores)[::-1][: request.k]
    candidates = []
    for rank, index in enumerate(ranked, start=1):
        resume = resumes.iloc[int(index)]
        excerpt = re.sub(r"\s+", " ", resume["resume_text"]).strip()
        candidates.append(
            {
                "rank": rank,
                "freelancer_id": str(resume["ID"]),
                "category": resume["Category"],
                "score": round(float(scores[index]), 4),
                "excerpt": excerpt[:240] + ("…" if len(excerpt) > 240 else ""),
            }
        )
    return {"model": model_label, "candidates": candidates}


@app.post("/api/budget")
def predict_budget(request: BudgetRequest):
    try:
        model = _budget_model(request.model)
        feature_names = model.feature_names_in_.tolist()
        input_features = _budget_features(request, feature_names)
        predicted_log_cost = float(model.predict(input_features)[0])
        predicted_cost = float(np.expm1(predicted_log_cost))
    except (AttributeError, OSError, ValueError, TypeError) as error:
        raise HTTPException(status_code=503, detail=f"Budget model could not produce a prediction: {error}") from error

    if not np.isfinite(predicted_cost) or predicted_cost <= 0:
        raise HTTPException(status_code=500, detail="The budget model returned an invalid estimate.")
    return {
        "model": "Random Forest" if request.model == "random_forest" else "XGBoost",
        "estimated_budget": round(predicted_cost, 2),
        "currency": "USD",
        "note": "Experimental estimate from historical Upwork listings, not a quote.",
    }
