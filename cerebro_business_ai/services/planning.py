"""Small, chronological demand experiments with explicit business scenarios."""
from datetime import date, timedelta
from typing import Annotated
from statistics import NormalDist
import math
import numpy as np
from fastapi import HTTPException
from pydantic import BaseModel, Field, model_validator
from services.intelligence import ResourceGuard
from app.resource_guard import ResourceLimits
import time

Nonnegative = Annotated[float, Field(ge=0, le=1e9, allow_inf_nan=False)]
class Sale(BaseModel):
    date: date
    sales: Nonnegative
    price: Nonnegative | None = None
    visitors: Nonnegative | None = None
    promotion: bool = False
    stockout: bool = False

class Plan(BaseModel):
    product_id: int | None = Field(default=None, ge=1)
    product_name: str = Field(default='', max_length=200)
    location_id: int | None = Field(default=None, ge=1)
    rows: list[Sale] = Field(min_length=7, max_length=730)
    horizon: int = Field(default=7, ge=1, le=28)
    stock: Nonnegative = 30
    incoming: Nonnegative = 0
    lead_days: int = Field(default=7, ge=1, le=90)
    service_level: float = Field(default=.95, ge=.5, le=.99, allow_inf_nan=False)
    assumed_demand_change: float = Field(default=0, ge=-100, le=300, allow_inf_nan=False)
    future_price: Nonnegative | None = None
    future_visitors: Nonnegative | None = None
    future_promotion: bool = False

    @model_validator(mode='after')
    def daily(self):
        dates = [r.date for r in self.rows]
        if any(b-a != timedelta(days=1) for a,b in zip(dates, dates[1:])):
            raise ValueError('Sales rows must have unique consecutive dates in ascending order. Fill missing dates explicitly.')
        return self

def forecast(y, h, method):
    y = np.asarray(y, dtype=float)
    if method in ('Weekday average', 'Seasonal trend'):
        recent = y[-56:]
        prediction = np.array([np.mean(recent[np.arange(len(recent)) % 7 == (len(recent)+i) % 7]) for i in range(h)])
        if method == 'Seasonal trend' and len(y) >= 28:
            # Estimate level change over full weeks; damp it outside the history.
            slope = np.clip((y[-14:].mean()-y[-28:-14].mean())/14, -y[-28:].mean()/28, y[-28:].mean()/28)
            prediction += slope * (10.5 + np.minimum(np.arange(1, h+1), 14))
        return np.maximum(0, prediction)
    if method == 'Zero demand':
        return np.zeros(h)
    if method == 'Intermittent mean':
        return np.repeat(np.mean(y[-90:]),h)
    if method == 'Weekly seasonal':
        return np.resize(y[-7:], h)
    if method == 'Moving average':
        return np.repeat(np.mean(y[-min(14,len(y)):]), h)
    if method == 'Croston SBA':
        positive = np.flatnonzero(y > 0)
        if len(positive) == 0: return np.zeros(h)
        first = positive[0]; size = y[first]; interval = float(first+1); elapsed = 1; alpha = .1
        for value in y[first+1:]:
            if value > 0:
                size += alpha*(value-size); interval += alpha*(elapsed-interval); elapsed=1
            else: elapsed+=1
        return np.repeat((1-alpha/2)*size/interval, h)
    level=float(y[0]); trend=0.; alpha=.25; beta=.1; damping=.9
    for value in y[1:]:
        previous=level
        level=alpha*value+(1-alpha)*(level+(damping*trend if method=='Damped trend' else 0))
        trend=beta*(level-previous)+(1-beta)*damping*trend
    if method=='Exponential smoothing': return np.repeat(level,h)
    return np.maximum(0, [level+trend*sum(damping**j for j in range(1,k+1)) for k in range(1,h+1)])

def context_features(rows, i, future=None, y=None):
    r = rows[i] if i<len(rows) else future
    history = y if y is not None else [x.sales for x in rows[:i]]
    return [1., history[-1], history[-7], float(np.mean(history[-7:])),
            math.sin(2*math.pi*r.date.weekday()/7), math.cos(2*math.pi*r.date.weekday()/7),
            r.price or 0., r.visitors or 0., float(r.promotion)]

def contextual(rows,h,request):
    # Fit only the current training prefix. Every lag is strictly in the past.
    x=np.array([context_features(rows,i) for i in range(7,len(rows))]); y=np.array([r.sales for r in rows[7:]])
    mu=x.mean(axis=0); sd=x.std(axis=0); sd[sd<1e-8]=1; mu[0]=0; sd[0]=1
    z=(x-mu)/sd; reg=np.eye(z.shape[1])*10; reg[0,0]=0
    coef=np.linalg.solve(z.T@z+reg,z.T@y)
    history=[r.sales for r in rows]; result=[]
    for step in range(h):
        future=Sale(date=rows[-1].date+timedelta(days=step+1),sales=0,
            price=request.future_price if request.future_price is not None else rows[-1].price,
            visitors=request.future_visitors if request.future_visitors is not None else rows[-1].visitors,
            promotion=request.future_promotion)
        f=np.array(context_features(rows,len(rows),future,history))
        value=max(0,float(((f-mu)/sd)@coef)); history.append(value); result.append(value)
    return np.array(result)

def plan(request: Plan):
    started=time.perf_counter()
    guard=ResourceGuard(ResourceLimits(cpu_start_percent=85,ram_start_percent=85,vram_start_percent=85,sample_interval_seconds=.05)); before=guard.snapshot()
    if not guard.safe_to_start(before): raise HTTPException(503,'Resource limits reached. Try again shortly.')
    rows=request.rows; y=np.array([r.sales for r in rows]); n=len(y); h=request.horizon
    # Censored sales are replaced for fitting only, using past in-stock weekdays.
    # Their observed values remain in the chart and are excluded from scoring.
    cleaned=[]
    for i,r in enumerate(rows):
        value=r.sales
        if r.stockout:
            past=[x.sales for x in rows[max(0,i-56):i] if not x.stockout and x.date.weekday()==r.date.weekday()]
            if not past: past=[x.sales for x in rows[max(0,i-28):i] if not x.stockout]
            value=float(np.mean(past)) if past else value
        cleaned.append(r.model_copy(update={'sales':value}))
    fit_y=np.array([r.sales for r in cleaned])
    # Eligibility is determined before the test window, including sparsity and context.
    test_origin=n-h if n>=max(42,3*h+14) else None
    selection_end=test_origin if test_origin is not None else n
    selection_rows=rows[:selection_end]
    selection_y=y[:selection_end]
    intermittent=bool(np.mean(selection_y==0)>=.3)
    candidates=['Moving average','Exponential smoothing','Damped trend']
    if n>=21: candidates.append('Weekly seasonal')
    if n>=35: candidates.extend(['Weekday average','Seasonal trend'])
    if np.mean(selection_y==0)>=.3: candidates.append('Croston SBA')
    if np.mean(selection_y==0)>=.3: candidates.append('Zero demand')
    if np.mean(selection_y==0)>=.3: candidates.append('Intermittent mean')
    context_ok=selection_end>=56 and (len({r.price for r in selection_rows if r.price is not None})>=4 or len({r.visitors for r in selection_rows if r.visitors is not None})>=10 or len({r.promotion for r in selection_rows})>1)
    if context_ok: candidates.append('Context regression')
    # Reserve the final horizon for an honest test of the selected method.
    origins=[selection_end-h*k for k in (3,2,1) if selection_end-h*k>=max(14,2*h)]
    if context_ok: origins=[o for o in origins if o>=35]
    scores=[]; errors={}; examples={}
    for method in candidates:
        if guard.should_pause(): raise HTTPException(503,'Resource safety threshold reached. Forecast stopped safely.')
        actual=[]; preds=[]; examples[method]=[]
        for origin in origins:
            train=cleaned[:origin]
            # Backtest context holds last known price/traffic; future actual values are never used.
            back=Plan(rows=train,horizon=h)
            p=contextual(train,h,back) if method=='Context regression' else forecast(fit_y[:origin],h,method)
            mask=np.array([not r.stockout for r in rows[origin:origin+h]])
            truth=y[origin:origin+h]; actual.extend(truth[mask]); preds.extend(p[mask])
            examples[method]=[{'date':r.date.isoformat(),'actual':r.sales,'predicted':round(float(v),3),'stockout':r.stockout} for r,v in zip(rows[origin:origin+h],p)]
        if actual:
            e=np.array(actual)-np.array(preds); errors[method]=e
            scores.append({'method':method,'mae':round(float(np.mean(abs(e))),4),'rmse':round(float(np.sqrt(np.mean(e**2))),4),
                'wape':round(float(np.sum(abs(e))/np.sum(actual)*100),2) if np.sum(actual)>0 else None,'folds':len(origins),
                'benchmark_only':method=='Zero demand' and bool(np.any(selection_y>0))})
    eligible=[s for s in scores if not s['benchmark_only']]
    # Preserve the regular-sales selection. For sparse series, squared error
    # targets expected units instead of the zero median favored by daily MAE.
    selection_metric='rmse' if intermittent else 'mae'
    selected=min(eligible,key=lambda s:s[selection_metric])['method'] if eligible else 'Moving average'
    inventory_horizon=max(h,request.lead_days)
    baseline_request=request.model_copy(update={'future_price':None,'future_visitors':None,'future_promotion':False})
    full_baseline=contextual(cleaned,inventory_horizon,baseline_request) if selected=='Context regression' else forecast(fit_y,inventory_horizon,selected)
    context_changed=request.future_price is not None or request.future_visitors is not None or request.future_promotion
    planned=contextual(cleaned,inventory_horizon,request) if selected=='Context regression' and context_changed else full_baseline
    full_adjusted=planned*(1+request.assumed_demand_change/100)
    baseline=full_baseline[:h]; adjusted=full_adjusted[:h]
    daily=float(np.mean(adjusted)); lead_demand=float(np.sum(full_adjusted[:request.lead_days]))
    residuals=errors.get(selected); sigma=float(np.std(residuals,ddof=1)) if residuals is not None and len(residuals)>1 else None
    safety=NormalDist().inv_cdf(request.service_level)*sigma*math.sqrt(request.lead_days) if sigma is not None else None
    reorder=lead_demand+(safety or 0); available=request.stock+request.incoming
    warnings=[]
    if not request.product_id and not request.product_name.strip():
        warnings.append('Product identity is missing. This result is a generic series estimate, not a product-aware forecast.')
    if not scores: warnings.append('Too little history for chronological validation at this horizon. This is a provisional average estimate.')
    if any(r.stockout for r in rows): warnings.append('Stockouts mean observed sales can understate demand. For fitting, censored observations use prior in-stock weekday averages; this is an imputation, not measured lost demand. These days are excluded from scoring.')
    if request.lead_days>h: warnings.append(f'Inventory uses a separate {request.lead_days}-day forecast to cover supplier lead time.')
    if not context_ok: warnings.append('Price/traffic/promotion effects cannot be learned from the supplied history. Use an explicit demand-change scenario.')
    elif selected!='Context regression': warnings.append('Context regression was evaluated but did not win validation. Future price/traffic inputs do not change the selected baseline.')
    if np.mean(y==0)>=.3: warnings.append('Intermittent sales: daily fractional values represent expected units, not a guarantee of an order every day. The zero forecast remains a comparison benchmark when sales have occurred.')
    scenario_applied=bool(request.assumed_demand_change or (context_changed and selected=='Context regression'))
    zero_explanation=None
    if float(np.sum(adjusted))<=1e-9:
        zero_explanation=('Your -100% demand-change assumption sets the scenario to zero; the baseline is preserved.' if request.assumed_demand_change==-100 else
            'All recorded sales are zero. The data does not support a positive sales estimate.' if not np.any(y>0) else
            'The selected method predicts zero for this horizon. Review recent sales, intermittent demand and stock availability; this does not prove there is no market demand.')
        warnings.append(zero_explanation)
    if context_changed and selected=='Context regression':
        for label,value,observed in [('price',request.future_price,[r.price for r in rows if r.price is not None]),('visitors',request.future_visitors,[r.visitors for r in rows if r.visitors is not None])]:
            if value is not None and observed and not min(observed)<=value<=max(observed): warnings.append(f'Planned {label} is outside the observed history range. The scenario extrapolates and may be unreliable.')
    holdout=None
    if test_origin is not None and scores:
        train=cleaned[:test_origin]
        test_request=Plan(rows=train,horizon=h)
        test_pred=contextual(train,h,test_request) if selected=='Context regression' else forecast(fit_y[:test_origin],h,selected)
        mask=np.array([not r.stockout for r in rows[test_origin:]])
        truth=y[test_origin:][mask]; e=truth-test_pred[mask]
        holdout={'start':rows[test_origin].date.isoformat(),'end':rows[-1].date.isoformat(),'method':selected,'observations':int(mask.sum()),
            'mae':round(float(np.mean(abs(e))),4) if len(e) else None,'rmse':round(float(np.sqrt(np.mean(e**2))),4) if len(e) else None,
            'wape':round(float(np.sum(abs(e))/np.sum(truth)*100),2) if np.sum(truth)>0 else None,
            'points':[{'date':r.date.isoformat(),'actual':r.sales,'predicted':round(float(v),3),'stockout':r.stockout} for r,v in zip(rows[test_origin:],test_pred)]}
    width=float(np.quantile(abs(residuals),.8)) if residuals is not None and len(residuals)>=14 else None
    return {'product_name':request.product_name,'method':selected,'selection_reason':f'Lowest rolling validation {selection_metric.upper()}; '+('expected-unit planning for intermittent sales. ' if intermittent else '')+('The final test period was excluded from model selection.' if holdout else 'No separate test period was available.') if scores else 'Provisional moving average; insufficient backtest history.',
        'scenario_applied':scenario_applied,'zero_explanation':zero_explanation,'selection_metric':selection_metric,
        'holdout':holdout,'duration_seconds':round(time.perf_counter()-started,3),
        'history':[{'date':r.date.isoformat(),'sales':r.sales,'stockout':r.stockout} for r in rows],
        'uncertainty':{'kind':'Descriptive error range based on the 80th percentile of validation absolute errors; coverage is not calibrated.','available':width is not None},
        'scores':scores,'backtest':examples.get(selected,[]),'warnings':warnings,'m5_used':False,
        'readiness':{'days':n,'zero_percent':round(float(np.mean(y==0)*100),1),'stockout_days':sum(r.stockout for r in rows),'daily_average':round(float(y.mean()),2),'context_evaluated':context_ok},
        'forecast':[{'date':(rows[-1].date+timedelta(days=i+1)).isoformat(),'baseline':round(float(b),3),'scenario':round(float(v),3), 'lower':round(max(0,float(v)-width),3) if width is not None else None,'upper':round(float(v)+width,3) if width is not None else None} for i,(b,v) in enumerate(zip(baseline,adjusted))],
        'inventory':{'lead_time_units':math.ceil(lead_demand),'safety_stock':math.ceil(safety) if safety is not None else None,'reorder_point':math.ceil(reorder),'order_quantity':math.ceil(max(0,reorder-available)),
            'order_explanation':'Existing and incoming stock cover the estimated reorder point; zero additional units to buy does not mean zero demand.' if available>=reorder else 'Additional stock is needed to reach estimated lead-time demand plus safety stock.',
            'coverage_days':round(available/daily,1) if daily>0 else None,'shortfall_units':math.ceil(max(0,lead_demand-available))},
        'assumptions':['Sales are observed purchases, not total market demand.','Future context defaults to last known price/visitors and no promotion.',f'User demand-change assumption: {request.assumed_demand_change}%.',
            'Safety stock uses validation residual standard deviation, normal errors and independent daily errors; the selected service level is a target, not a guarantee.','Demand and lead time are treated as stationary for inventory calculations.'],
        'resources':{'before':guard.as_dict(before),'after':guard.as_dict()}}
