from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
def test_fallback_description():
    r = client.post('/generate-description', json={'title':'React app','skills':['React']})
    assert r.status_code == 200 and r.json()['source'] == 'fallback'
def test_fraud_advisory():
    r = client.post('/check-fraud', json={'profile':{'email':'x@mailinator.com'},'transaction':{}})
    assert r.json()['advisory'] is True and r.json()['risk_score'] >= 30
