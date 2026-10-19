from datetime import date, timedelta
import pytest
from services.planning import Plan, Sale, plan, forecast


def weekly(n=140):
    return [Sale(date=date(2026,1,1)+timedelta(days=i),sales=[1,3,2,4,8,12,10][i%7]) for i in range(n)]


def test_test_window_does_not_influence_selection_or_candidate_eligibility():
    rows=weekly()
    original=plan(Plan(product_name='Headphones',rows=rows,horizon=14))
    changed=rows[:-14]+[r.model_copy(update={'sales':0.,'price':float(i+20),'visitors':float(100+i),'promotion':bool(i%2)}) for i,r in enumerate(rows[-14:])]
    altered=plan(Plan(product_name='Headphones',rows=changed,horizon=14))
    assert original['scores']==altered['scores']
    assert original['method']==altered['method']
    assert original['holdout']['mae']==0
    assert altered['holdout']['mae']>0
    assert original['holdout']['start']>original['backtest'][-1]['date']


def test_lead_time_uses_daily_forecasts_not_horizon_average():
    rows=weekly()
    result=plan(Plan(product_name='Headphones',rows=rows,horizon=7,lead_days=3,stock=0))
    assert result['method']=='Weekly seasonal'
    assert result['inventory']['lead_time_units']==sum(p['baseline'] for p in result['forecast'][:3])
    assert len(result['history'])==140
    assert all(p['lower'] is not None for p in result['forecast'])


def test_no_sales_keeps_wape_undefined_and_forecast_zero():
    rows=[r.model_copy(update={'sales':0.}) for r in weekly()]
    result=plan(Plan(rows=rows,horizon=14))
    assert result['holdout']['wape'] is None
    assert sum(p['baseline'] for p in result['forecast'])==0
    assert result['inventory']['coverage_days'] is None


def test_stockout_is_not_scored_as_true_zero_demand():
    rows=weekly()
    rows[-1]=rows[-1].model_copy(update={'sales':0.,'stockout':True})
    result=plan(Plan(rows=rows,horizon=14))
    assert result['holdout']['observations']==13
    assert result['holdout']['mae']==0
    assert result['history'][-1]['sales']==0
    assert result['history'][-1]['stockout']


def test_weekday_average_denoises_repeated_weekly_sales():
    pattern=[1,2,3,4,5,6,7]
    history=pattern*7+[v+8 for v in pattern]
    assert forecast(history,7,'Weekday average').tolist()==pytest.approx([v+1 for v in pattern])


def test_intermittent_expected_demand_does_not_select_zero_median_benchmark():
    import csv
    from pathlib import Path
    source=Path(__file__).resolve().parents[2]/'sample_sales_histories/06_synthetic_intermittent_spare_parts.csv'
    rows=[Sale(date=r['date'],sales=float(r['sales'])) for r in csv.DictReader(source.open(encoding='utf-8'))]
    result=plan(Plan(rows=rows,horizon=14))
    assert result['selection_metric']=='rmse'
    assert result['method']!='Zero demand'
    assert sum(p['baseline'] for p in result['forecast'])>0
    assert next(s for s in result['scores'] if s['method']=='Zero demand')['benchmark_only']


def test_minus_one_hundred_is_explained_and_baseline_survives():
    result=plan(Plan(rows=weekly(),assumed_demand_change=-100))
    assert sum(p['scenario'] for p in result['forecast'])==0
    assert sum(p['baseline'] for p in result['forecast'])>0
    assert '-100%' in result['zero_explanation']


def test_inventory_settings_do_not_change_sales_forecast():
    a=plan(Plan(rows=weekly(),stock=0,incoming=0,lead_days=3))
    b=plan(Plan(rows=weekly(),stock=100000,incoming=10,lead_days=15))
    assert a['forecast']==b['forecast']
    assert b['inventory']['order_quantity']==0
    assert 'does not mean zero demand' in b['inventory']['order_explanation']
