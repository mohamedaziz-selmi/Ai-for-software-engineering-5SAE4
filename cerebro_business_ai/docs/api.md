# Cerebro API contract

Base URL: `http://localhost:8080/api` (the AI service itself listens on port 8000 for internal calls).

## `POST /classify-listing`

Request: `{ "title": "...", "description": "...", "skills": ["python"] }`.
Response: `{ "categories": [{"category":"Web Development","confidence":0.82}], "model":"tfidf-logistic-regression" }`.

## `POST /generate-description`

Request: `{ "title":"...", "skills":["React"], "audience":"...", "requirements":"..." }`.
Response: `{ "description":"...", "source":"llm|fallback", "prompt_version":"v1" }`.

## `POST /generate-cv`

Request: `{ "name":"...", "email":"...", "skills":["Java"], "experience":"...", "education":"..." }`.
Response: `{ "cv": {"summary":"...","skills":[],"experience":[],"education":"..."}, "source":"llm|fallback" }`.

## `POST /predict-demand`

Request: `{ "category":"Web Development", "price":500, "description_length":300, "rating":4.8, "response_time_hours":3, "delivery_days":7, "skill_demand_index":0.8 }`.
Response: `{ "probability":0.74, "label":"high", "factors":[{"feature":"rating","impact":0.21}] }`.

## `POST /check-fraud`

Request: `{ "transaction": {...}, "profile": {...} }`.
Response: `{ "risk_score":42, "reasons":["..."], "advisory":true }`.

The public Spring API validates and limits all inputs, applies timeouts when calling FastAPI, and returns deterministic fallbacks when the AI service is unavailable. Generated text is advisory and must be reviewed by a human.
