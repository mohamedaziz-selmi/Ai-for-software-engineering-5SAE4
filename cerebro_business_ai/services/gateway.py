from contextlib import asynccontextmanager
import os, uuid
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .config import CONFIG
from services.intelligence import Brief, ProductBrief, Rewrite
from services.planning import Plan
from services.scenarios import ScenarioPlannerRequest
from services.job_review import Posting
from pydantic import BaseModel, Field

SERVICES = {"fraud": f"http://{CONFIG.host}:{CONFIG.fraud_port}", "job": f"http://{CONFIG.host}:{CONFIG.job_port}", "demand": f"http://{CONFIG.host}:{CONFIG.demand_port}", "product": f"http://{CONFIG.host}:{CONFIG.product_port}"}
app = FastAPI(title="Cerebro API Gateway", version="1.0.0", description="Gateway for Cerebro AI microservices. Internal service ports are local-only.")
app.add_middleware(CORSMiddleware, allow_origins=[f"http://localhost:{CONFIG.frontend_port}",f"http://127.0.0.1:{CONFIG.frontend_port}", "http://localhost:5173"], allow_credentials=False, allow_methods=["*"] ,allow_headers=["*"])

async def structured_proxy(service, path, body):
    try:
        async with httpx.AsyncClient(timeout=220) as client:
            result = await client.post(SERVICES[service]+path, json=body.model_dump(mode='json'))
        return JSONResponse(status_code=result.status_code, content=result.json())
    except (httpx.RequestError, ValueError):
        raise HTTPException(503, 'The requested service is unavailable. Your inputs have been retained.')

@app.post('/api/ai/jobs/brief', tags=['Hiring assistant'])
async def hiring_brief(body: Brief):
    return await structured_proxy('job','/brief',body)

@app.post('/api/ai/products/brief', tags=['Listing assistant'])
async def listing_brief(body: ProductBrief):
    return await structured_proxy('product','/brief',body)

@app.post('/api/ai/jobs/rewrite', tags=['Hiring assistant'])
async def hiring_rewrite(body: Rewrite):
    return await structured_proxy('job','/rewrite',body)

@app.post('/api/ai/products/rewrite', tags=['Listing assistant'])
async def listing_rewrite(body: Rewrite):
    return await structured_proxy('product','/rewrite',body)

@app.post('/api/ai/demand/plan', tags=['Sales and inventory planning'])
async def inventory_plan_v2(body: Plan):
    return await structured_proxy('demand','/plan',body)

@app.post('/api/ai/jobs/review', tags=['Evidence review'])
async def posting_review(body: Posting):
    return await structured_proxy('fraud','/review',body)

class IntakeBody(BaseModel):
    text: str = Field(min_length=15, max_length=16000)
    employer: str = ''
    official_domain: str = ''
@app.post('/api/ai/jobs/intake', tags=['Smart intake'])
async def job_intake(body: IntakeBody): return await structured_proxy('fraud','/intake',body)
@app.post('/api/ai/hiring/intake', tags=['Smart intake'])
async def hiring_intake(body: Brief): return await structured_proxy('job','/intake',body)
@app.post('/api/ai/products/intake', tags=['Smart intake'])
async def product_intake(body: ProductBrief): return await structured_proxy('product','/intake',body)

@app.middleware("http")
async def correlation(request: Request, call_next):
    response = await call_next(request); response.headers["X-Correlation-ID"] = request.headers.get("X-Correlation-ID", str(uuid.uuid4())); return response

async def proxy(service: str, path: str, request: Request):
    try:
        async with httpx.AsyncClient(timeout=float(os.getenv("GATEWAY_TIMEOUT_SECONDS", "120"))) as client:
            upstream = await client.request(request.method, SERVICES[service] + path, content=await request.body(), headers={"content-type": request.headers.get("content-type", "application/json")})
        return upstream
    except httpx.RequestError as exc: raise HTTPException(status_code=503, detail={"service": service, "message": str(exc)})

@app.get("/health", tags=["health"])
async def health(): return {"status": "ok", "service": "gateway", "ports": {"gateway": CONFIG.gateway_port, "frontend": CONFIG.frontend_port}}

@app.get("/api/ai/status", tags=["health"])
async def status():
    result = {}
    async with httpx.AsyncClient(timeout=3) as client:
        for name, base in SERVICES.items():
            try:
                details = (await client.get(base + "/health")).json()
                result[name] = {"status": "available" if details.get("status") == "ok" else "unavailable", **details}
            except Exception as exc: result[name] = {"status": "unavailable", "reason": str(exc)}
    return result

@app.post("/api/ai/jobs/detect-fraud", tags=["fraud"])
async def detect_fraud(request: Request):
    upstream = await proxy("fraud", "/predict", request); return JSONResponse(status_code=upstream.status_code, content=upstream.json())
@app.post("/api/ai/jobs/analyze-fraud", tags=["fraud"])
async def analyze_fraud(request: Request):
    upstream = await proxy("fraud", "/analyze", request); return JSONResponse(status_code=upstream.status_code, content=upstream.json())
@app.post("/api/ai/jobs/export-fraud-report", tags=["fraud"])
async def export_fraud_report(request: Request):
    upstream = await proxy("fraud", "/export-report", request); return JSONResponse(status_code=upstream.status_code, content=upstream.json())
@app.post("/check-fraud", tags=["compatibility"])
async def legacy_fraud(request: Request):
    upstream = await proxy("fraud", "/predict", request); return JSONResponse(status_code=upstream.status_code, content=upstream.json())
@app.post("/api/ai/jobs/generate-description", tags=["generation"])
async def generate_description(request: Request):
    upstream = await proxy("job", "/generate", request); return JSONResponse(status_code=upstream.status_code, content=upstream.json())
@app.post("/api/ai/jobs/build-package", tags=["recruitment"])
async def build_package(request: Request):
    upstream = await proxy("job", "/build-package", request); return JSONResponse(status_code=upstream.status_code, content=upstream.json())
@app.post("/api/ai/jobs/audit-description", tags=["recruitment"])
async def audit_description(request: Request):
    upstream = await proxy("job", "/audit-description", request); return JSONResponse(status_code=upstream.status_code, content=upstream.json())
@app.post("/api/ai/jobs/regenerate-section", tags=["recruitment"])
async def regenerate_job_section(request: Request):
    upstream = await proxy("job", "/regenerate-section", request); return JSONResponse(status_code=upstream.status_code, content=upstream.json())
@app.post("/api/ai/jobs/translate-description", tags=["recruitment"])
async def translate_description(request: Request):
    upstream = await proxy("job", "/translate-description", request); return JSONResponse(status_code=upstream.status_code, content=upstream.json())
@app.post("/api/ai/demand/forecast", tags=["forecast"])
async def demand_forecast(request: Request):
    upstream = await proxy("demand", "/forecast", request); return JSONResponse(status_code=upstream.status_code, content=upstream.json())
@app.post("/api/ai/demand/forecast-smart", tags=["forecast"])
async def demand_forecast_smart(request: Request):
    upstream = await proxy("demand", "/forecast-smart", request); return JSONResponse(status_code=upstream.status_code, content=upstream.json())
@app.post("/api/ai/demand/validate-history", tags=["forecast"])
async def validate_history(request: Request):
    upstream = await proxy("demand", "/validate-history", request); return JSONResponse(status_code=upstream.status_code, content=upstream.json())
@app.post("/api/ai/demand/inventory-plan", tags=["forecast"])
async def inventory_plan(request: Request):
    upstream = await proxy("demand", "/inventory-plan", request); return JSONResponse(status_code=upstream.status_code, content=upstream.json())
@app.post("/api/ai/demand/scenario", tags=["forecast"])
async def demand_scenario(request: Request):
    upstream = await proxy("demand", "/scenario", request); return JSONResponse(status_code=upstream.status_code, content=upstream.json())
@app.post('/api/ai/demand/scenario-planner', tags=['scenario planning'])
async def demand_scenario_planner(body: ScenarioPlannerRequest):
    return await structured_proxy('demand', '/scenario-planner', body)
@app.get("/api/ai/demand/demo-products", tags=["forecast"])
async def demo_products(request: Request):
    upstream = await proxy("demand", "/demo-products", request); return JSONResponse(status_code=upstream.status_code, content=upstream.json())
@app.post("/api/ai/products/generate-listing", tags=["generation"])
async def generate_listing(request: Request):
    upstream = await proxy("product", "/generate", request); return JSONResponse(status_code=upstream.status_code, content=upstream.json())
@app.post("/api/ai/products/retrieve", tags=["retrieval"])
async def product_retrieve(request: Request):
    upstream = await proxy("product", "/retrieve", request); return JSONResponse(status_code=upstream.status_code, content=upstream.json())
@app.post("/api/ai/products/analyze", tags=["product-intelligence"])
async def analyze_product(request: Request):
    upstream = await proxy("product", "/analyze", request); return JSONResponse(status_code=upstream.status_code, content=upstream.json())
@app.post("/api/ai/products/compare", tags=["product-intelligence"])
async def compare_products(request: Request):
    upstream = await proxy("product", "/compare", request); return JSONResponse(status_code=upstream.status_code, content=upstream.json())
@app.post("/api/ai/products/audit-listing", tags=["product-intelligence"])
async def audit_product(request: Request):
    upstream = await proxy("product", "/audit-listing", request); return JSONResponse(status_code=upstream.status_code, content=upstream.json())
@app.post("/api/ai/products/regenerate-section", tags=["product-intelligence"])
async def regenerate_product_section(request: Request):
    upstream = await proxy("product", "/regenerate-section", request); return JSONResponse(status_code=upstream.status_code, content=upstream.json())
