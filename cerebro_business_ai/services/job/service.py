from pathlib import Path
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from services.upgrade_logic import audit_job, package_missing

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-service"))
from app.llm import call_json, prompt  # noqa: E402

app = FastAPI(title="Cerebro Job Description Service", version="1.0.0", description="Gemma 3 4B structured job-description generation through shared Ollama.")
from services.intelligence import Brief, HiringPackage, Rewrite, hiring, rewrite
from services.smart_intake import hiring_intake
app.post('/brief', tags=['Hiring assistant'])(hiring)
app.post('/rewrite', tags=['Hiring assistant'])(rewrite)
@app.post('/intake', tags=['Smart intake'])
def intake(request: Brief):
    return hiring_intake(request.brief)

class JobGenerateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    industry: str = Field(default="", max_length=200)
    location: str = Field(default="", max_length=200)
    employment_type: str = Field(default="", max_length=100)
    skills: list[str] = Field(default_factory=list, max_length=30)
    experience: str = Field(default="", max_length=500)
    responsibilities: list[str] = Field(default_factory=list, max_length=20)
    salary: str = Field(default="", max_length=100)
    company_information: str = Field(default="", max_length=2000)
    language: str = Field(default="en", pattern="^(en|fr)$")
    tone: str = Field(default="professional", max_length=40)

class JobPackageRequest(JobGenerateRequest):
    company_name: str = Field(default="", max_length=200)
    optional_skills: list[str] = Field(default_factory=list, max_length=30)
    benefits: list[str] = Field(default_factory=list, max_length=20)

class JobAuditRequest(BaseModel):
    title: str = ""
    description: str = ""
    salary: str = ""
    location: str = ""
    employment_type: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    company_information: str = ""

class RegenerateSectionRequest(JobPackageRequest):
    section: str = Field(min_length=1, max_length=80)
    current_content: str = Field(default="", max_length=8000)

@app.get("/health", tags=["health"])
def health(): return {"status": "ok", "service": "job-description", "provider": "ollama"}

@app.get("/model/info", tags=["model"])
def model_info(): return {"provider": "ollama", "model": "gemma3:4b", "shared_server": True, "prompt_version": "v2-structured"}

@app.post("/generate", tags=["generation"])
def generate(request: JobGenerateRequest):
    data, source = call_json(prompt("description_v1.txt"), request.model_dump())
    if not data or not isinstance(data.get("description"), str) or not data["description"].strip():
        raise HTTPException(status_code=503, detail={"code": "llm_unavailable", "provider_status": source})
    return {"status": "complete", "description": data["description"], "language": request.language, "source": source, "prompt_version": "v2-structured"}

@app.post("/build-package", tags=["recruitment"])
def build_package(request: JobPackageRequest):
    package_prompt = "Return strict JSON with non-empty values for exactly these keys: normalized_job_title, professional_summary, responsibilities, required_qualifications, preferred_qualifications, required_skills, optional_skills, interview_questions, interview_rubric, screening_criteria, linkedin_post, seo_title, seo_summary, language. Preserve the user's title, salary and benefits exactly when supplied. Professionalize rough notes instead of copying them verbatim as responsibilities. Use only supplied facts. Screening criteria must be job-related and non-discriminatory."
    data, source = call_json(package_prompt, request.model_dump())
    if not data or not isinstance(data, dict):
        raise HTTPException(status_code=503, detail={"code": "llm_unavailable", "provider_status": source})
    data["normalized_job_title"] = request.title
    if not data.get("professional_summary") and data.get("description"):
        data["professional_summary"] = data["description"]
    data.setdefault("required_skills", request.skills)
    data.setdefault("optional_skills", request.optional_skills)
    missing = package_missing(data)
    if missing:
        repair_prompt = "Return strict JSON containing only the missing recruitment package keys. Each list must contain useful non-empty items. Preserve the supplied title and facts. Missing keys: " + ", ".join(missing)
        repair, repair_source = call_json(repair_prompt, {"job": request.model_dump(), "partial_package": data, "missing": missing})
        if repair and isinstance(repair, dict):
            data.update({key: value for key, value in repair.items() if key in missing})
            source = source + "+repair"
    missing = package_missing(data)
    if missing:
        raise HTTPException(status_code=502, detail={"code": "invalid_llm_package", "missing_sections": missing, "message": "The model did not return a complete recruitment package."})
    input_audit = audit_job(request.model_dump())
    return {"status": "complete", "package": data, "input_audit": input_audit, "audit": input_audit, "source": source, "language": request.language, "output_valid": True}

@app.post("/audit-description", tags=["recruitment"])
def audit_description(request: JobAuditRequest):
    return audit_job(request.model_dump())

@app.post("/regenerate-section", tags=["recruitment"])
def regenerate_section(request: RegenerateSectionRequest):
    instruction = f"Return strict JSON with one key 'content'. Rewrite only the {request.section} section. Preserve facts and user edits elsewhere. Requested job data: {request.model_dump()}"
    data, source = call_json(instruction, request.model_dump())
    if not data or not isinstance(data.get("content"), str):
        raise HTTPException(status_code=503, detail={"code": "llm_unavailable", "provider_status": source})
    return {"status": "complete", "section": request.section, "content": data["content"], "source": source}

@app.post("/translate-description", tags=["recruitment"])
def translate_description(request: JobGenerateRequest):
    target = "French" if request.language == "fr" else "English"
    instruction = f"Return strict JSON with one key 'description'. Translate and professionally edit the supplied job data into {target}. Do not add unsupported claims."
    data, source = call_json(instruction, request.model_dump())
    if not data or not isinstance(data.get("description"), str):
        raise HTTPException(status_code=503, detail={"code": "llm_unavailable", "provider_status": source})
    return {"status": "complete", "description": data["description"], "language": request.language, "source": source}
