import json
from pathlib import Path
from fastapi.testclient import TestClient

from services.fraud.service import app as fraud_app
from services.job.service import app as job_app
from services.demand.service import app as demand_app
from services.product.service import app as product_app
from services.gateway import app as gateway_app

def test_independent_service_openapi_and_health():
    for application in (fraud_app, job_app, demand_app, product_app, gateway_app):
        client = TestClient(application)
        assert client.get('/health').status_code == 200
        spec = client.get('/openapi.json').json()
        assert spec['openapi'].startswith('3.')
        assert spec['paths']

def test_independent_fraud_service_uses_real_model():
    response = TestClient(fraud_app).post('/predict', json={'title': 'Urgent remote job', 'description': 'Pay a fee before interview', 'requirements': 'None'})
    assert response.status_code == 200
    assert 0 <= response.json()['fraud_probability'] <= 1
    assert response.json()['advisory'] is True

def test_independent_demand_service_uses_saved_artifact():
    response = TestClient(demand_app).post('/forecast', json={'history': list(range(1, 29)), 'horizon': 7})
    assert response.status_code == 200
    assert len(response.json()['predictions']) == 7

def test_openapi_documents_required_service_paths():
    gateway = TestClient(gateway_app).get('/openapi.json').json()['paths']
    assert '/api/ai/jobs/detect-fraud' in gateway
    assert '/api/ai/jobs/generate-description' in gateway
    assert '/api/ai/demand/forecast' in gateway
    assert '/api/ai/products/generate-listing' in gateway
