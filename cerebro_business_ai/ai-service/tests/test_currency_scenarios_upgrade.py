from datetime import date
import math
import pytest
from fastapi.testclient import TestClient
from services.compensation import pay_details, stated_hours, short_day
from services.scenarios import ScenarioPlannerRequest, scenario_planner
from services.demand.service import app


@pytest.mark.parametrize('text,currency,minimum,maximum',[
    ('9,000 to 12,000 TND per month','TND',9000,12000),
    ('9 000 à 12 000 dinars tunisiens par mois','TND',9000,12000),
    ('9000 dinars par mois','DINAR_UNSPECIFIED',9000,9000),
    ('1 200,50 euros/mois','EUR',1200.5,1200.5),
    ('1.200,50 EUR par mois','EUR',1200.5,1200.5),
    ('EUR 1,200.50 per month','EUR',1200.5,1200.5),
    ('€3,000–€4,000 per month','EUR',3000,4000),
    ('3,000 EUR - 4,000 EUR/month','EUR',3000,4000),
    ('3000€/mois','EUR',3000,3000),
    ('3k to 4k euros monthly','EUR',3000,4000),
    ('3\u202f500 dinars tunisiens par mois','TND',3500,3500),
    ('500 dinars algériens par jour','DZD',500,500),
    ('USD 20 per hour','USD',20,20),
    ('$20/hour','DOLLAR_UNSPECIFIED',20,20),
    ('30 dollars per hour','DOLLAR_UNSPECIFIED',30,30),
    ('£300 per day','GBP',300,300),
    ('٩٠٠٠ دينار تونسي شهريا','TND',9000,9000),
])
def test_currency_names_formats_and_exact_offsets(text,currency,minimum,maximum):
    posting='Salary: '+text+'. Apply through the official careers page.'
    details=pay_details(posting)
    assert len(details)==1
    result=details[0]
    assert result['currency']==currency
    assert result['minimum']==pytest.approx(minimum)
    assert result['maximum']==pytest.approx(maximum)
    assert posting[result['start']:result['end']]==result['text']
    assert result['text']==text


@pytest.mark.parametrize('text,short',[
    ('2h/jour',True),('two hours daily',True),('3 à 4 heures par jour',True),
    ('8 hours per day',False),('20 hours per week',False),('deux heures par jour',True),
])
def test_hours_formats(text,short):
    matches=stated_hours(text)
    assert len(matches)==1
    assert short_day(matches[0])==short


def test_daily_scenario_has_real_horizon_projection_and_stock_math():
    result=scenario_planner(ScenarioPlannerRequest(product_name='Coffee',low=3,expected=8,high=15,current_stock=30,incoming=0,lead_days=7,horizon=14,start_date=date(2026,10,19)))
    assert result['model_used'] is False
    assert len(result['daily_projection'])==14
    assert result['end_date']=='2026-11-01'
    assert result['scenarios'][1]['period_units']==112
    assert result['scenarios'][1]['recommended_order']==26
    assert result['scenarios'][1]['stockout_before_delivery']


def test_traffic_scenario_converts_visits_to_units():
    result=scenario_planner(ScenarioPlannerRequest(product_name='Coffee',basis='traffic',visitors=200,conversion_low=1,conversion_expected=2,conversion_high=4,horizon=14))
    assert [r['daily_units'] for r in result['scenarios']]==[2,4,8]
    assert result['scenarios'][1]['period_units']==56


def test_fractional_stock_shortage_rounds_up_and_zero_case_stays_defined():
    result=scenario_planner(ScenarioPlannerRequest(product_name='Parts',low=0,expected=.1,high=1,current_stock=0,lead_days=1))
    assert result['scenarios'][0]['coverage_days'] is None
    assert result['scenarios'][1]['recommended_order']==1


@pytest.mark.parametrize('payload',[
    {'low':10,'expected':3,'high':5},
    {'basis':'traffic','visitors':None},
    {'basis':'traffic','visitors':100,'conversion_low':10,'conversion_expected':2},
    {'basis':'traffic','visitors':100,'conversion_high':101},
    {'low':-1}, {'product_name':'   '}, {'horizon':0}, {'lead_days':0},
])
def test_bad_scenario_inputs_return_validation_error(payload):
    response=TestClient(app).post('/scenario-planner',json={'product_name':'Coffee',**payload})
    assert response.status_code==422


def test_scenario_schema_rejects_nan():
    with pytest.raises(ValueError):ScenarioPlannerRequest(product_name='Test',expected=math.nan)


def test_fee_amount_is_not_presented_as_salary():
    details=pay_details('Salaire de 3000 euros par mois. Payez des frais de dossier de 80 euros avant de commencer.')
    assert [d['kind'] for d in details]==['compensation','requested_payment']
