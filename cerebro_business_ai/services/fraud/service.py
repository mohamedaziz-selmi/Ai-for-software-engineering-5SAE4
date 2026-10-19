from pathlib import Path
import sys
from typing import Any
from fastapi import FastAPI
from pydantic import BaseModel, Field
from services.upgrade_logic import fraud_report

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-service"))
from app.main import load_real_fraud_model  # noqa: E402

app = FastAPI(title="Cerebro Fraud Detection Service", version="1.0.0", description="Real TF-IDF Logistic Regression job-fraud inference.")
from services.job_review import Posting, review
from services.smart_intake import fraud_intake
app.post('/review', tags=['Evidence review'])(review)
class IntakeRequest(BaseModel):
    text: str = Field(min_length=15, max_length=16000)
    employer: str = Field(default='', max_length=200)
    official_domain: str = Field(default='', max_length=200)
@app.post('/intake', tags=['Smart intake'])
def intake(request: IntakeRequest):
    return fraud_intake(request.text, request.employer, request.official_domain)
MODEL_PATH = ROOT / "data" / "phase4" / "job_fraud" / "tfidf_logistic.joblib"

class FraudPredictRequest(BaseModel):
    title: str = Field(default="", max_length=300)
    description: str = Field(default="", max_length=10000)
    company_profile: str = Field(default="", max_length=5000)
    requirements: str = Field(default="", max_length=5000)
    benefits: str = Field(default="", max_length=5000)
    profile: dict[str, Any] = Field(default_factory=dict)

class FraudPredictResponse(BaseModel):
    fraud_probability: float
    risk: str
    model: str
    indicators: list[str]
    advisory: bool = True

class FraudAnalyzeRequest(FraudPredictRequest):
    salary: str = Field(default="", max_length=100)
    contact_information: str = Field(default="", max_length=1000)
    domain: str = Field(default="", max_length=300)

class FraudAnalyzeResponse(BaseModel):
    model_probability: float
    rule_signal: float
    overall_risk_score: float
    risk: str
    warning_count: int
    evidence: list[dict]
    missing_information: list[str]
    recommended_checks: list[str]
    advisory: bool
    limitations: str

@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": "fraud-detection", "model_available": MODEL_PATH.exists()}

@app.get("/model/info", tags=["model"])
def model_info():
    return {"model": "TF-IDF + Logistic Regression", "version": "phase4-production-fallback", "artifact": str(MODEL_PATH), "available": MODEL_PATH.exists(), "historical_metrics": {"precision": .868, "recall": .852, "f1": .860, "roc_auc": .984, "pr_auc": .881}}

@app.post("/predict", response_model=FraudPredictResponse, tags=["fraud"])
def predict(request: FraudPredictRequest):
    profile_text = " ".join(str(request.profile.get(k, "")) for k in ("title", "description", "bio", "company_profile", "requirements", "benefits"))
    text = " ".join((request.title, request.description, request.company_profile, request.requirements, request.benefits, profile_text)).strip()
    model = load_real_fraud_model()
    probability = float(model.predict_proba([text])[0][1]) if model and text else 0.0
    indicators = []
    if not request.company_profile.strip(): indicators.append("company_profile_missing")
    if not request.requirements.strip(): indicators.append("requirements_missing")
    if len(text) < 120: indicators.append("short_text")
    return {"fraud_probability": probability, "risk": "high" if probability >= .5 else "low", "model": "phase4-tfidf-logistic", "indicators": indicators, "advisory": True}

@app.post("/analyze", response_model=FraudAnalyzeResponse, tags=["fraud"])
def analyze(request: FraudAnalyzeRequest):
    base = predict(request)
    fields = {"title": request.title, "description": request.description, "company_profile": request.company_profile, "requirements": request.requirements, "benefits": request.benefits, "salary": request.salary, "contact_information": request.contact_information, "domain": request.domain}
    return fraud_report(fields, float(base["fraud_probability"]))

@app.post("/export-report", tags=["fraud"])
def export_report(request: FraudAnalyzeRequest):
    report = analyze(request)
    lines = ["CEREBRO JOB POSTING RISK REPORT", "", f"Risk: {report['risk']}", f"Model probability: {report['model_probability']:.4f}", f"Rule signal: {report['rule_signal']:.4f}", "", "Evidence:"]
    lines += [f"- [{x['severity']}] {x['category']}: {x['evidence']} — {x['recommended_action']}" for x in report["evidence"]]
    lines += ["", "Advisory: results require human verification."]
    return {"filename": "cerebro-fraud-report.txt", "content_type": "text/plain", "content": "\n".join(lines), "report": report}
