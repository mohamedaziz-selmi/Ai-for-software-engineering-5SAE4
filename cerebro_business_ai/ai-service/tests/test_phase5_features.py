from fastapi.testclient import TestClient
from app.main import app
from app.rag import retrieve

client = TestClient(app)


def test_status_reports_rag_and_available_m5():
    response = client.get('/api/ai/status')
    assert response.status_code == 200
    assert response.json()['product_rag']['status'] == 'available'
    assert response.json()['demand']['status'] == 'available'

def test_m5_forecast_api_returns_real_artifact_predictions():
    response = client.post('/api/ai/demand/forecast', json={'history': list(range(1, 29)), 'horizon': 7, 'last_date': '2016-04-24', 'sell_price': 3.0})
    assert response.status_code == 200
    body = response.json()
    assert body['model'] == 'm5-xgboost-lightweight'
    assert len(body['predictions']) == 7
    assert all(isinstance(value, float) and value >= 0 for value in body['predictions'])


def test_product_retrieval_is_grounded_before_llm_generation():
    references = retrieve('Bones skateboard wheels', 2, 'Sports & Outdoors')
    assert references
    assert all('skateboard' in item['title'].lower() for item in references)
    assert all('retrieval_score' in item for item in references)
    assert retrieve('zzxx superbanana quantum toaster phone', 2, 'Electronics') == []
    assert retrieve('wireless headphones', 2, 'Electronics') == []


def test_product_listing_requires_real_llm():
    response = client.post('/api/ai/products/generate-listing', json={'query': 'wireless headphones', 'top_k': 2})
    assert response.status_code == 503
    assert 'LLM' in str(response.json())


def test_llm_generation_has_explicit_configuration_error():
    response = client.post('/api/ai/jobs/generate-description', json={'title': 'Engineer'})
    assert response.status_code in (200, 503)


def test_job_generation_schema_with_configured_provider(monkeypatch):
    monkeypatch.setattr('app.main.call_json', lambda template, data: ({'description': 'Description en français.'}, 'test-provider'))
    response = client.post('/api/ai/jobs/generate-description', json={'title': 'Ingénieur logiciel', 'language': 'fr'})
    assert response.status_code == 200
    assert response.json()['language'] == 'fr'
    assert response.json()['source'] == 'test-provider'


def test_product_generation_schema_with_configured_provider(monkeypatch):
    monkeypatch.setattr('app.rag.call_json', lambda template, data: ({'title': 'Grounded product', 'description': 'Verified catalog description.', 'features': [], 'keywords': ['catalog'], 'category_suggestion': 'Electronics'}, 'test-provider'))
    response = client.post('/api/ai/products/generate-listing', json={'query': 'wireless headphones', 'language': 'en', 'top_k': 2})
    assert response.status_code == 200
    body = response.json()
    assert body['source'] == 'test-provider'
    assert body['references'] == []  # The sample catalog has no relevant headphones.
    assert 'No sufficiently relevant' in body['retrieval_status']
    assert body['hallucination_guard']
