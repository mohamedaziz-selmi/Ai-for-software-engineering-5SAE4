from pathlib import Path
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from services.upgrade_logic import product_audit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-service"))
from app.rag import grounded_listing, retrieve, INDEX_PATH  # noqa: E402

app = FastAPI(title="Cerebro Product Listing Service", version="1.0.0", description="Amazon catalog retrieval and Gemma grounded listing generation.")
from services.intelligence import ProductBrief, Rewrite, listing, rewrite
from services.smart_intake import product_intake
app.post('/brief', tags=['Listing assistant'])(listing)
app.post('/rewrite', tags=['Listing assistant'])(rewrite)
@app.post('/intake', tags=['Smart intake'])
def intake(request: ProductBrief):
    return product_intake(request.brief, request.title, '', request.category)

class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=3, ge=1, le=5)
    category: str = Field(default="", max_length=200)
class GenerateRequest(RetrieveRequest):
    category: str = Field(default="", max_length=200)
    specifications: dict[str, str] = Field(default_factory=dict)
    language: str = Field(default="en", pattern="^(en|fr)$")

class ProductAnalyzeRequest(GenerateRequest):
    brand: str = Field(default="", max_length=200)
    title: str = Field(default="", max_length=300)
    description: str = Field(default="", max_length=5000)
    features: list[str] = Field(default_factory=list, max_length=30)

class ProductAuditRequest(BaseModel):
    title: str = ""
    brand: str = ""
    category: str = ""
    description: str = ""
    specifications: dict[str, str] = Field(default_factory=dict)
    features: list[str] = Field(default_factory=list)

@app.get("/health", tags=["health"])
def health(): return {"status": "ok", "service": "product-listing", "index_available": INDEX_PATH.exists(), "provider": "ollama"}
@app.get("/model/info", tags=["model"])
def model_info(): return {"retriever": "TF-IDF catalog index", "index": str(INDEX_PATH), "generator": "gemma3:4b", "available": INDEX_PATH.exists()}
@app.post("/retrieve", tags=["retrieval"])
def retrieve_route(request: RetrieveRequest): return {"references": retrieve(request.query, request.top_k, request.category), "query": request.query, "category_filter": request.category or None}
@app.post("/generate", tags=["generation"])
def generate(request: GenerateRequest):
    result = grounded_listing(request.query, request.category, request.specifications, request.language, request.top_k)
    if result.get("status") == "unavailable": raise HTTPException(status_code=503, detail=result)
    return result

@app.post("/analyze", tags=["product-intelligence"])
def analyze(request: ProductAnalyzeRequest):
    references = retrieve(request.query, request.top_k, request.category)
    audit = product_audit(request.model_dump())
    return {"query": request.query, "references": references, "audit": audit, "grounding_policy": "Generated claims must be supported by user-provided facts or these retrieved references."}

@app.post("/compare", tags=["product-intelligence"])
def compare(request: RetrieveRequest):
    references = retrieve(request.query, request.top_k, request.category)
    return {"query": request.query, "similar_products": references, "comparison_note": "Similarity is catalog retrieval relevance, not proof of competitive advantage."}

@app.post("/audit-listing", tags=["product-intelligence"])
def audit_listing(request: ProductAuditRequest):
    return product_audit(request.model_dump())

@app.post("/regenerate-section", tags=["product-intelligence"])
def regenerate_section(request: ProductAnalyzeRequest, section: str = "description"):
    result = grounded_listing(request.query, request.category, request.specifications, request.language, request.top_k)
    if result.get("status") == "unavailable":
        raise HTTPException(status_code=503, detail=result)
    return {"status": "complete", "section": section, "content": result.get(section, result.get("description", "")), "references": result.get("references", []), "source": result.get("source", "ollama")}
