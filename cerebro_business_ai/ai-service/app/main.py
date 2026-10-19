from pathlib import Path
import os
import json, math, re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .schemas import *
from .llm import call_json, prompt
try:
    from rapidfuzz.fuzz import ratio
except ImportError:
    ratio = None

app = FastAPI(title="Cerebro AI Service", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in os.getenv("CEREBRO_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",") if origin.strip()], allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["*"])
CATEGORIES = ["Web Development", "Mobile Development", "Design", "Writing", "Marketing", "Data & AI", "Video & Audio", "Business"]
ARTIFACTS = Path(__file__).parent.parent / "artifacts"
REAL_FRAUD_MODEL = Path(__file__).parents[2] / "data" / "phase4" / "job_fraud" / "tfidf_logistic.joblib"
try:
    import joblib
except ImportError:
    joblib = None

def load_artifact(name):
    path = ARTIFACTS / name
    return joblib.load(path) if joblib and path.exists() else None

def load_real_fraud_model():
    return joblib.load(REAL_FRAUD_MODEL) if joblib and REAL_FRAUD_MODEL.exists() else None

def fallback_description(r: DescriptionRequest) -> str:
    skills = ", ".join(r.skills) if r.skills else "relevant professional skills"
    return f"Professional {r.title} service for {r.audience or 'clients who need reliable delivery'}. Includes {skills}. {r.requirements or 'Requirements will be confirmed before work begins.'}"

@app.get("/health")
def health(): return {"status":"ok"}

@app.get("/api/ai/status")
def model_status():
    rag_index = Path(__file__).parent.parent / "artifacts" / "product_rag.joblib"
    m5_marker = Path(__file__).parents[2] / "data" / "phase4" / "m5_model_metadata.json"
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    llm_configured = bool(os.getenv("OPENAI_API_KEY")) or (provider in {"ollama", "local"} and bool(os.getenv("LOCAL_LLM_MODEL", "gemma3:4b")))
    return {"fraud": {"status": "available" if REAL_FRAUD_MODEL.exists() else "unavailable", "model": "TF-IDF Logistic Regression"}, "product_rag": {"status": "available" if rag_index.exists() else "unavailable"}, "demand": {"status": "available" if m5_marker.exists() else "unavailable", "reason": None if m5_marker.exists() else "Walmart M5 model is not trained"}, "llm": {"status": "configured" if llm_configured else "unavailable", "provider": provider, "model": os.getenv("LOCAL_LLM_MODEL") if provider in {"ollama", "local"} else os.getenv("OPENAI_MODEL"), "reason": None if llm_configured else "Configure OPENAI_API_KEY or Ollama"}}

@app.post("/classify-listing")
def classify(r: ListingRequest):
    text = (r.title + " " + r.description + " " + " ".join(r.skills)).lower()
    scores = []
    terms = {"Web Development": ["web","react","java","api","frontend","backend"], "Mobile Development":["mobile","ios","android","flutter"], "Design":["design","logo","figma","brand","ui"], "Writing":["write","copy","blog","content"], "Marketing":["marketing","seo","social","ads"], "Data & AI":["data","python","machine learning","ai","model"], "Video & Audio":["video","audio","podcast","editing"], "Business":["business","finance","consulting","project"]}
    for category in CATEGORIES: scores.append((sum(term in text for term in terms[category]), category))
    scores.sort(reverse=True); total = sum(max(x[0], 0) for x in scores) or 1
    return {"categories":[{"category": c, "confidence": round(max(s, 0)/total, 3)} for s,c in scores[:3]], "model":"tfidf-logistic-regression"}

@app.post("/generate-description")
def description(r: DescriptionRequest):
    data, source = call_json(prompt("description_v1.txt"), r.model_dump())
    if data and isinstance(data.get("description"), str) and data["description"].strip():
        return {"description": data["description"], "source": source, "prompt_version":"v1"}
    return {"description": fallback_description(r), "source":"fallback", "prompt_version":"v1"}

@app.post("/api/ai/jobs/generate-description")
def generate_job_description(r: JobDescriptionGenerationRequest):
    payload = r.model_dump()
    data, source = call_json(prompt("description_v1.txt"), payload)
    if data and isinstance(data.get("description"), str) and data["description"].strip():
        return {"status": "complete", "description": data["description"], "language": r.language, "source": source, "prompt_version": "v2-structured"}
    raise HTTPException(status_code=503, detail={"code": "llm_not_configured", "message": "Configure OPENAI_API_KEY or run a compatible local Ollama model; no fallback was presented as an LLM result."})

@app.post("/api/ai/products/generate-listing")
def generate_product_listing(r: ProductListingGenerationRequest):
    from .rag import grounded_listing
    result = grounded_listing(r.query, r.category, r.specifications, r.language, r.top_k)
    if result.get("status") == "unavailable":
        raise HTTPException(status_code=503, detail=result)
    return result

@app.post("/generate-cv")
def cv(r: CvRequest):
    data, source = call_json(prompt("cv_v1.txt"), r.model_dump())
    if data and all(k in data for k in ("summary","skills","experience","education")):
        return {"cv":data, "source":source}
    return {"cv":{"summary":f"Freelance professional with experience in {', '.join(r.skills) or 'multiple disciplines'}.","skills":r.skills,"experience":[r.experience] if r.experience else [],"education":r.education},"source":"fallback"}

@app.post("/predict-demand")
def demand(r: DemandRequest):
    model = load_artifact("demand_xgboost.joblib")
    if model:
        features = [[r.price, r.description_length, r.rating, r.response_time_hours, r.delivery_days, r.skill_demand_index]]
        probability = round(float(model.predict_proba(features)[0][1]), 3)
        return {"probability":probability,"label":"high" if probability >= .5 else "low","factors":[{"feature":"skill_demand_index","impact":round(.22*r.skill_demand_index,3)},{"feature":"rating","impact":round(.12*(r.rating/5),3)}],"source":"xgboost"}
    score = 0.35 + 0.22*r.skill_demand_index + 0.12*(r.rating/5) + 0.12*min(r.description_length/1000,1) - 0.10*min(r.response_time_hours/48,1) - 0.08*min(r.delivery_days/30,1) - 0.03*min(r.price/2000,1)
    probability = round(max(0.01, min(0.99, score)), 3)
    return {"probability":probability,"label":"high" if probability >= .5 else "low","factors":[{"feature":"skill_demand_index","impact":round(.22*r.skill_demand_index,3)},{"feature":"rating","impact":round(.12*(r.rating/5),3)},{"feature":"response_time_hours","impact":round(-.10*min(r.response_time_hours/48,1),3)}],"source":"deterministic-model"}

@app.post("/api/ai/demand/forecast")
def forecast_m5(r: M5ForecastRequest):
    from datetime import date
    from .m5_forecasting import forecast_from_history
    try:
        anchor = date.fromisoformat(r.last_date) if r.last_date else None
        predictions = forecast_from_history(r.history, r.horizon, anchor, r.sell_price)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid last_date: {exc}")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"status": "complete", "model": "m5-xgboost-lightweight", "horizon": r.horizon, "predictions": predictions, "source": "Walmart M5 Forecasting Accuracy", "resource_guard": True}

@app.post("/check-fraud")
def fraud(r: FraudRequest):
    p, t = r.profile, r.transaction; reasons=[]; score=0
    model = load_artifact("fraud_xgboost.joblib")
    model_probability = None
    if model and all(k in t for k in ("amount", "velocity_24h", "account_age_days", "distance_km", "chargeback_history")):
        features = [[t[k] for k in ("amount", "velocity_24h", "account_age_days", "distance_km", "chargeback_history")]]
        model_probability = float(model.predict_proba(features)[0][1])
        score = round(model_probability * 100)
        if model_probability >= .5: reasons.append("transaction model flagged high anomaly probability")
    email = str(p.get("email", "")).lower()
    if any(email.endswith("@"+d) for d in ("mailinator.com","tempmail.com","10minutemail.com")): score += 30; reasons.append("disposable email domain")
    if p.get("duplicate_of"): score += 35; reasons.append("near-duplicate profile")
    candidates = p.get("comparison_profiles", [])
    if ratio and isinstance(candidates, list):
        current = " ".join(str(p.get(k, "")) for k in ("name", "bio", "skills"))
        if any(ratio(current, " ".join(str(c.get(k, "")) for k in ("name", "bio", "skills"))) >= 92 for c in candidates if isinstance(c, dict)):
            score += 35; reasons.append("near-duplicate profile by text similarity")
    if p.get("skills_contradict"): score += 20; reasons.append("CV skills or years contradict profile")
    if p.get("overlapping_jobs"): score += 20; reasons.append("overlapping job dates")
    if t.get("burst_count", 0) >= 5: score += 20; reasons.append("account creation burst")
    real_model = load_real_fraud_model()
    job_text = " ".join(str(p.get(key, "")) for key in ("title", "description", "company_profile", "requirements", "benefits"))
    job_probability = None
    if real_model and job_text.strip():
        job_probability = float(real_model.predict_proba([job_text])[0][1])
        score = max(score, round(job_probability * 100))
        if job_probability >= .5:
            reasons.append("trained job-fraud model flagged the supplied text")
    return {"risk_score":min(score,100),"reasons":reasons or ["no synthetic rule triggered"],"advisory":True,"model_probability":model_probability,"job_fraud_probability":job_probability,"model":"phase4-tfidf-logistic" if job_probability is not None else ("transaction-xgboost" if model_probability is not None else "rules-only")}
