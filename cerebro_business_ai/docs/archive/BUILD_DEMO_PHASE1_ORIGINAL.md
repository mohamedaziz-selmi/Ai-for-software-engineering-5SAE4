# Historical Phase 1 build/demo notes — not the current startup instructions

## Local commands

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r ai-service/requirements.txt
python data/generate_all.py
python ai-service/train_models.py
pytest ai-service/tests
docker compose up --build
```

## 15-minute demo

1. Create a listing and show top-three category suggestions.
2. Generate its description with an unavailable key to demonstrate the deterministic fallback.
3. Enter price, rating, response time, and delivery time; show the demand potential score and SHAP-style factors.
4. Generate a CV and show name/email anonymization in the service logs/tests.
5. Open the admin fraud view with an intentionally duplicated synthetic profile and explain that the result is advisory.
6. Show `ai-service/artifacts/metrics.json`: majority baseline, linear SVM, logistic final, Isolation Forest, and XGBoost/logistic demand comparison on held-out data.

## Report skeleton

1. Problem and ethical scope.
2. Architecture and API contract.
3. Reproducible synthetic data rules.
4. Listing classifier: baseline, alternatives, macro F1, confusion matrix.
5. Demand potential score: PR-AUC and interpretability.
6. Fraud/background checks: imbalance, PR-AUC, rules, advisory safeguards.
7. LLM reliability: anonymization, schema validation, retry, fallback, human-rating sheet.
8. Limitations and future work.
