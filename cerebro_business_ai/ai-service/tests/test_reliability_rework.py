from fastapi.testclient import TestClient

from services.upgrade_logic import fraud_report, package_missing, smart_forecast, validate_history
from services.demand.service import app as demand_app
from services.product.service import app as product_app


def test_rule_score_zero_does_not_reduce_ml_probability():
    report = fraud_report({"description": "A detailed software role with normal duties."}, .61)
    assert report["overall_risk_score"] >= .61


def test_high_pay_low_hours_detected():
    report = fraud_report({"description": "Work 1 hour per day and earn $500/day on Telegram."}, .2)
    categories = {item["category"] for item in report["evidence"]}
    assert "unrealistic_salary" in categories
    assert "external_contact_instruction" in categories


def test_company_domain_mismatch():
    report = fraud_report({"company_profile": "Indeed Career Services", "domain": "teste.com", "description": "Software role"}, .1)
    assert any(item["category"] == "employer_domain_mismatch" for item in report["evidence"])


def test_recruitment_required_fields_are_explicit():
    missing = package_missing({"normalized_job_title": "Senior Machine Learning Engineer"})
    assert "professional_summary" in missing
    assert "responsibilities" in missing


def test_custom_history_does_not_use_m5():
    result = smart_forecast([1, 2, 3, 4, 5, 6, 7] * 4, 7)
    assert result["m5_used"] is False
    assert result["predictions"]


def test_short_history_is_explained():
    result = validate_history([1, 2, 3, 4, 5, 6, 7])
    assert result["records"] == 7
    assert result["warnings"]


def test_negative_stock_rejected():
    client = TestClient(demand_app)
    response = client.post("/inventory-plan", json={"history": [1] * 28, "lead_time_days": 7, "current_stock": -1})
    assert response.status_code == 422


def test_ambiguous_product_requests_clarification():
    client = TestClient(product_app)
    response = client.post("/generate", json={"query": "apple 15", "category": "Electronics", "language": "en"})
    assert response.status_code == 200
    assert response.json()["status"] == "clarification_required"
