"""No-history planning from explicit assumptions, with no fitted model."""
from datetime import date, timedelta
from typing import Literal
import math
import time
from fastapi import HTTPException
from pydantic import BaseModel, Field, model_validator
from services.planning import Nonnegative
from app.resource_guard import ResourceGuard, ResourceLimits


class ScenarioPlannerRequest(BaseModel):
    product_name:str=Field(min_length=1,max_length=200)
    basis:Literal['daily','traffic']='daily'
    low:Nonnegative=3
    expected:Nonnegative=8
    high:Nonnegative=15
    visitors:Nonnegative|None=None
    conversion_low:float=Field(default=1,ge=0,le=100,allow_inf_nan=False)
    conversion_expected:float=Field(default=2,ge=0,le=100,allow_inf_nan=False)
    conversion_high:float=Field(default=4,ge=0,le=100,allow_inf_nan=False)
    current_stock:Nonnegative=30
    lead_days:int=Field(default=7,ge=1,le=90)
    incoming:Nonnegative=0
    horizon:int=Field(default=14,ge=1,le=90)
    start_date:date=Field(default_factory=date.today)
    unit_price:Nonnegative|None=None

    @model_validator(mode='after')
    def ordered(self):
        self.product_name=self.product_name.strip()
        if not self.product_name:raise ValueError('Enter a product name to plan scenarios.')
        if self.basis=='daily' and not self.low<=self.expected<=self.high:raise ValueError('Daily units must satisfy low ≤ expected ≤ high.')
        if self.basis=='traffic':
            if self.visitors is None:raise ValueError('Daily visitors are required for a traffic-based scenario.')
            if not self.conversion_low<=self.conversion_expected<=self.conversion_high:raise ValueError('Conversion rates must satisfy low ≤ expected ≤ high.')
        return self


def scenario_planner(request:ScenarioPlannerRequest):
    started=time.perf_counter();guard=ResourceGuard(ResourceLimits(cpu_start_percent=85,ram_start_percent=85,vram_start_percent=85,sample_interval_seconds=.05))
    before=guard.snapshot()
    if not guard.safe_to_start(before):raise HTTPException(503,'Resource limits reached. Try scenario planning again shortly.')
    daily=[request.low,request.expected,request.high] if request.basis=='daily' else [request.visitors*c/100 for c in (request.conversion_low,request.conversion_expected,request.conversion_high)]
    available=request.current_stock+request.incoming
    scenarios=[]
    for name,units in zip(('Low case','Base case','High case'),daily):
        lead=units*request.lead_days;period=units*request.horizon
        scenarios.append({'name':name,'daily_units':round(units,4),'period_units':round(period,2),'lead_time_units':round(lead,2),
            'coverage_days':round(available/units,1) if units else None,'recommended_order':math.ceil(max(0,lead-available)),
            'period_revenue':round(period*request.unit_price,2) if request.unit_price is not None else None,
            'stockout_before_delivery':bool(units and available<lead)})
    return {'status':'scenario_only','model_used':False,'basis':request.basis,'product_name':request.product_name,'horizon':request.horizon,
        'start_date':request.start_date.isoformat(),'end_date':(request.start_date+timedelta(days=request.horizon-1)).isoformat(),'scenarios':scenarios,
        'daily_projection':[{'date':(request.start_date+timedelta(days=i)).isoformat(),'low':round(daily[0],4),'expected':round(daily[1],4),'high':round(daily[2],4)} for i in range(request.horizon)],
        'stock':{'on_hand':request.current_stock,'incoming':request.incoming,'available':available,'lead_days':request.lead_days},
        'message':'Scenario planning from your assumptions. No sales history or trained forecasting model was used.',
        'assumptions':(['Daily units are the low, expected and high estimates you supplied.'] if request.basis=='daily' else ['Daily units = visitors × assumed purchase conversion rate. Visitors must describe the sales channel for this product.'])+
            ['The same daily assumptions apply throughout the selected period.','Low and high cases are assumptions, not statistical confidence bounds.','Incoming stock is assumed to arrive in time. No safety stock is inferred without observed variability.'],
        'duration_seconds':round(time.perf_counter()-started,3),'resources':{'before':guard.as_dict(before),'after':guard.as_dict()}}
