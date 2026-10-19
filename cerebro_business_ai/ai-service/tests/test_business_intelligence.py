from datetime import date, timedelta
import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from services.planning import Plan, Sale, forecast, plan
from services.intelligence import HiringPackage, Brief, ProductBrief, listing
from services.job_review import Posting, review
from services.gateway import app as gateway

def rows(n=84, intermittent=False):
    return [Sale(date=date(2026,1,1)+timedelta(days=i),sales=(5 if i%10==0 else 0) if intermittent else [2,4,6,3,8,12,10][i%7]) for i in range(n)]

def test_croston_models_interarrival_not_just_nonzero_size():
    sparse=forecast([5]+[0]*9+[5]+[0]*9,7,'Croston SBA')
    dense=forecast([5]*20,7,'Croston SBA')
    assert sparse.mean()<dense.mean()
    assert forecast([0]*20,7,'Croston SBA').sum()==0

def test_weekly_pattern_is_recovered_and_backtested():
    result=plan(Plan(rows=rows(),horizon=7))
    assert result['method']=='Weekly seasonal'
    assert next(s for s in result['scores'] if s['method']=='Weekly seasonal')['mae']==0
    assert len(result['backtest'])==7
    assert result['forecast'][0]['date']>rows()[-1].date.isoformat()

def test_future_context_not_used_to_score_past():
    data=[r.model_copy(update={'price':float(10+i%5),'visitors':float(100+i)}) for i,r in enumerate(rows())]
    a=plan(Plan(rows=data,future_price=10))
    b=plan(Plan(rows=data,future_price=100))
    assert a['scores']==b['scores']
    assert a['readiness']['context_evaluated']

def test_scenario_explicitly_separate_from_baseline():
    a=plan(Plan(rows=rows(),assumed_demand_change=50))
    for point in a['forecast']: assert point['scenario']==pytest.approx(point['baseline']*1.5,abs=.002)
    assert isinstance(a['inventory']['order_quantity'],int)

def test_invalid_dates_negative_and_nan_rejected():
    with pytest.raises(ValidationError): Plan(rows=rows()[:3]+rows()[4:])
    with pytest.raises(ValidationError): Plan(rows=rows(),stock=-1)
    with pytest.raises(ValidationError): Sale(date=date.today(),sales=float('nan'))

def test_short_and_stockout_history_warns():
    data=rows(7);data[0].stockout=True
    result=plan(Plan(rows=data,horizon=28))
    assert result['scores']==[]
    assert result['inventory']['safety_stock'] is None
    assert any('understate' in s for s in result['warnings'])

def test_evidence_offsets_are_exact_and_no_generic_pay_accusation():
    result=review(Posting(text='Work from home 1 hour a day. Earn $500/day. No experience. Contact Telegram.'))
    assert any(e['category']=='High pay for little time' for e in result['evidence'])
    for e in result['evidence']: assert result['text'][e['start']:e['end']]==e['text']
    normal=review(Posting(text='We pay a competitive salary for a software engineer developing APIs and testing reliable applications at our office.'))
    assert not any(e['category']=='Upfront payment' for e in normal['evidence'])

def test_short_employer_name_is_insufficient_not_accusation():
    assert review(Posting(text='Software Engineer at Microsoft'))['advisory']=='More information needed'

def test_hiring_schema_rejects_blank_string_wrong_type():
    with pytest.raises(ValidationError): HiringPackage.model_validate({'title':' '})

def test_product_writer_never_receives_catalog_specs(monkeypatch):
    import app.rag
    import services.intelligence as module
    monkeypatch.setattr(app.rag,'retrieve',lambda *a:[{'title':'Competitor','description':'100 hour battery'}])
    def fake(schema,instruction,payload):
        assert '100 hour' not in str(payload)
        return {'output':{'feature_benefits':[{'user_fact':'100 hour battery','customer_benefit':'lasts longer'}],'claims_to_verify':[]}}
    monkeypatch.setattr(module,'generate',fake)
    result=listing(ProductBrief(brief='Foldable black headphones with USB-C.'))
    assert not result['output']['feature_benefits']
    assert result['output']['claims_to_verify']

def test_gateway_exposes_real_input_schemas():
    schema=TestClient(gateway).get('/openapi.json').json()
    for route in ['/api/ai/jobs/brief','/api/ai/demand/plan','/api/ai/jobs/review','/api/ai/products/brief']:
        assert schema['paths'][route]['post']['requestBody']['content']['application/json']['schema']
