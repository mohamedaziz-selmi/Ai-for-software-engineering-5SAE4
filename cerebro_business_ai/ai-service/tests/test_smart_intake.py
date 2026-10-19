from datetime import date, timedelta
import pytest
from services.smart_intake import fraud_intake, hiring_intake, product_intake
from services.registry import add_product, readiness, save_sales

def test_fraud_intake_extracts_combined_evidence():
    result = fraud_intake('Data entry remote. Earn $500/day for one hour. No experience. Contact Telegram.')
    assert result['fields']['compensation'][0]['value'] == '$500/day'
    assert any(x['value'].casefold() == 'telegram' for x in result['evidence'])

def test_hiring_intake_extracts_minimal_brief():
    result = hiring_intake('Need senior ML engineer in Tunis, Python XGBoost FastAPI, 5000/month, food housing')
    assert result['fields']['role']
    assert result['fields']['location'] == 'Tunis'
    assert set(result['fields']['skills']) == {'Python','XGBoost','FastAPI'}
    assert 'Contract type' in result['missing']

def test_product_intake_keeps_facts_and_reports_missing():
    result = product_intake('Wireless headphones, NovaSound, 30h battery, bluetooth 5.3, USB-C, ANC')
    assert result['fields']['category'] == 'Headphones'
    assert len(result['fields']['facts']) >= 3
    assert 'Warranty' in result['missing']

def test_registry_attaches_sales_to_named_product(tmp_path, monkeypatch):
    import services.registry as registry
    monkeypatch.setattr(registry, 'DB', tmp_path / 'registry.sqlite')
    product = add_product('Wireless Headphones', 'Electronics', 'NovaSound')
    rows=[{'date':(date(2026,1,1)+timedelta(days=i)).isoformat(),'units':i%5+1} for i in range(30)]
    status=save_sales(product['id'], rows)
    assert status['product']['name'] == 'Wireless Headphones'
    assert status['days'] == 30
    assert status['status'] == 'READY'

def test_registry_rejects_duplicate_or_unsorted_dates(tmp_path, monkeypatch):
    import services.registry as registry
    monkeypatch.setattr(registry, 'DB', tmp_path / 'registry.sqlite')
    product=add_product('Test product')
    with pytest.raises(ValueError, match='unique and sorted'):
        save_sales(product['id'], [{'date':'2026-01-02','units':1},{'date':'2026-01-02','units':2}])
