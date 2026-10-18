"""Local inference API for the saved customer-review sentiment model."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from predict import predict_review

app = FastAPI(title="Cerebro Sentiment API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictionRequest(BaseModel):
    review_text: str = Field(min_length=1, max_length=10000)


@app.get("/health")
def health():
    try:
        predict_review("health check")
        return {"ready": True, "model": "saved TF-IDF sentiment classifier"}
    except RuntimeError as error:
        return {"ready": False, "detail": str(error)}


@app.post("/predict")
def predict(request: PredictionRequest):
    try:
        return predict_review(request.review_text)
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=503 if isinstance(error, RuntimeError) else 422, detail=str(error)) from error
