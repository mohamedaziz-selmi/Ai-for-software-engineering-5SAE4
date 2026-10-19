from datetime import date
from pathlib import Path
import csv
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from services.upgrade_logic import validate_history, inventory_plan, demand_scenario, smart_forecast

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-service"))
from app.m5_forecasting import forecast_from_history, META_PATH, MODEL_PATH  # noqa: E402

app = FastAPI(title="Cerebro Demand Forecast Service", version="1.0.0", description="Chronological M5 demand forecasts with the saved 200-series XGBoost experiment preserved.")
from services.planning import Plan, plan
app.post('/plan', tags=['Sales and inventory planning'])(plan)
from services.registry import add_product, products, readiness, save_sales
class ProductRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(default='', max_length=120)
    brand: str = Field(default='', max_length=120)
class RegistrySale(BaseModel):
    date: date
    units: float = Field(ge=0)
    price: float|None = Field(default=None, ge=0)
    promotion: bool = False
    visitors: float|None = Field(default=None, ge=0)
    stockout: bool = False
class RegistrySalesRequest(BaseModel):
    product_id: int = Field(ge=1)
    rows: list[RegistrySale] = Field(min_length=1, max_length=730)
@app.post('/products', tags=['Product registry'])
def create_product(request: ProductRequest): return add_product(request.name, request.category, request.brand)
@app.get('/products', tags=['Product registry'])
def list_products(): return {'products': products()}
@app.post('/products/sales', tags=['Product registry'])
def add_sales(request: RegistrySalesRequest):
    try: return save_sales(request.product_id, [r.model_dump(mode='json') for r in request.rows])
    except ValueError as exc: raise HTTPException(422, str(exc))
@app.get('/products/{product_id}/readiness', tags=['Product registry'])
def product_readiness(product_id: int):
    try: return readiness(product_id)
    except ValueError as exc: raise HTTPException(404, str(exc))

from services.scenarios import ScenarioPlannerRequest, scenario_planner
app.post('/scenario-planner', tags=['Scenario planning'])(scenario_planner)

class ForecastRequest(BaseModel):
    history: list[float] = Field(min_length=28, max_length=400)
    horizon: int = Field(default=7, ge=1, le=28)
    last_date: str | None = None
    sell_price: float = Field(default=0, ge=0, le=100000)

class HistoryValidationRequest(BaseModel):
    history: list[float] = Field(min_length=1, max_length=10000)
    dates: list[str] | None = Field(default=None, max_length=10000)

class InventoryPlanRequest(BaseModel):
    history: list[float] = Field(min_length=1, max_length=10000)
    lead_time_days: int = Field(ge=1, le=365)
    current_stock: float = Field(ge=0)
    service_level: float = Field(default=.95, ge=.5, le=.999)
    incoming_stock: float = Field(default=0, ge=0)

class ScenarioRequest(BaseModel):
    baseline_daily_demand: float = Field(ge=0)
    demand_change_percent: float = Field(ge=-100, le=1000)
    current_stock: float = Field(ge=0)
    lead_time_days: int = Field(ge=1, le=365)
    replenishment: float = Field(default=0, ge=0)

class SmartForecastRequest(BaseModel):
    history: list[float] = Field(min_length=7, max_length=10000)
    horizon: int = Field(default=7, ge=1, le=28)

@app.get("/health", tags=["health"])
def health(): return {"status": "ok", "service": "demand-forecast", "model_available": MODEL_PATH.exists()}

@app.get("/model/info", tags=["model"])
def model_info(): return {"model": "XGBoost", "artifact": str(MODEL_PATH), "metadata": str(META_PATH), "experiment": "200 representative series", "available": MODEL_PATH.exists()}

@app.post("/forecast", tags=["forecast"])
def forecast(request: ForecastRequest):
    try:
        anchor = date.fromisoformat(request.last_date) if request.last_date else None
        predictions = forecast_from_history(request.history, request.horizon, anchor, request.sell_price)
    except ValueError as exc: raise HTTPException(status_code=422, detail=str(exc))
    except (FileNotFoundError, RuntimeError) as exc: raise HTTPException(status_code=503, detail=str(exc))
    return {"status": "complete", "model": "m5-xgboost-lightweight", "predictions": predictions, "horizon": request.horizon, "resource_guard": True}

@app.post("/forecast-smart", tags=["forecast"])
def forecast_smart(request: SmartForecastRequest):
    return smart_forecast(request.history, request.horizon)

@app.post("/validate-history", tags=["data-quality"])
def validate_history_route(request: HistoryValidationRequest):
    try:
        return validate_history(request.history, request.dates)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

@app.post("/inventory-plan", tags=["inventory"])
def inventory_plan_route(request: InventoryPlanRequest):
    return inventory_plan(request.history, request.lead_time_days, request.current_stock, request.service_level, request.incoming_stock)

@app.post("/scenario", tags=["inventory"])
def scenario_route(request: ScenarioRequest):
    return demand_scenario(request.baseline_daily_demand, request.demand_change_percent, request.current_stock, request.lead_time_days, request.replenishment)

@app.get("/demo-products", tags=["data-quality"])
def demo_products():
    path = ROOT / "data" / "phase4" / "m5_200_series_predictions.csv"
    products = []
    if path.exists():
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                raw_id = row.get("id", "")
                if raw_id and raw_id not in {x["id"] for x in products}:
                    products.append({"id": raw_id, "label": f"M5 representative series {raw_id}", "note": "Anonymous dataset identifier; use its stored historical series."})
                if len(products) >= 12:
                    break
    return {"status": "available" if products else "unavailable", "source": "Walmart M5 representative experiment", "products": products}
