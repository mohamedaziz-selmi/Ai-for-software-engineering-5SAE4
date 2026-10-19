"""Deterministic decision-support logic shared by the Cerebro services.

This module deliberately keeps business checks separate from model and LLM output.
The functions return evidence and assumptions so the UI can explain what happened.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from statistics import mean, pstdev
from typing import Any


FRAUD_RULES = [
    ("payment_request", r"\b(pay|payment|fee|registration fee|deposit)\b", "high", "Never pay to apply; verify the employer independently."),
    ("bank_information_request", r"\b(bank account|routing number|iban|card number|crypto wallet)\b", "high", "Do not share financial information before verified employment."),
    ("personal_information_request", r"\b(passport|ssn|social security|national id|bank details)\b", "high", "Ask why the information is needed and use a verified HR channel."),
    ("external_contact_instruction", r"\b(telegram|whatsapp|signal|sms[- ]only|gmail\.com|outlook\.com)\b", "medium", "Confirm the contact address on the official company domain."),
    ("unrealistic_salary", r"(?:\$|€|£)\s?\d{3,6}\s*(?:(?:-|to)\s*(?:\$|€|£)?\d{3,6}\s*)?(?:/|per\s+)(?:day|daily|week|hour)", "medium", "Compare compensation with a trusted market source."),
    ("weak_qualification_high_pay", r"\b(?:18\+|basic english|smartphone|no experience)\b", "medium", "Check whether the compensation and requirements are consistent with the role."),
]


def fraud_evidence(text: str) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for category, pattern, severity, action in FRAUD_RULES:
        for match in re.finditer(pattern, text, flags=re.I):
            evidence.append({"category": category, "severity": severity, "evidence": match.group(0), "start": match.start(), "end": match.end(), "explanation": "Rule matched submitted text; this is an advisory signal, not a fraud finding.", "recommended_action": action})
    return evidence


def fraud_report(fields: dict[str, str], model_probability: float) -> dict[str, Any]:
    text = " ".join(v for v in fields.values() if v).strip()
    evidence = fraud_evidence(text)
    missing = [name for name, value in fields.items() if name in {"company_profile", "requirements", "benefits"} and not value.strip()]
    if len(text) < 120:
        evidence.append({"category": "vague_posting", "severity": "low", "evidence": text[:120], "start": 0, "end": min(len(text), 120), "explanation": "The submitted posting contains limited detail.", "recommended_action": "Request verifiable company, role, and hiring-process details."})
    domain = fields.get("domain", "").strip().lower()
    company = fields.get("company_profile", "").strip().lower()
    if domain and company and not any(token in domain for token in re.findall(r"[a-z0-9]+", company) if len(token) > 3):
        evidence.append({"category": "employer_domain_mismatch", "severity": "high", "evidence": f"Employer: {fields.get('company_profile')} | Domain: {fields.get('domain')}", "start": 0, "end": 0, "explanation": "The submitted employer name and domain do not obviously correspond.", "recommended_action": "Verify the employer using its official website and public contact details."})
    warning_count = len(evidence)
    rule_score = min(1.0, sum(0.35 if e["severity"] == "high" else 0.15 if e["severity"] == "medium" else 0.05 for e in evidence))
    # No rule match is neutral; it must never reduce the model signal.
    advisory_score = max(model_probability, rule_score)
    if any(e["severity"] == "high" for e in evidence):
        risk = "high"
    elif advisory_score >= .65 or sum(e["severity"] == "medium" for e in evidence) >= 2:
        risk = "high"
    elif advisory_score >= .35 or evidence:
        risk = "medium"
    else:
        risk = "low"
    checks = ["Verify company domain and registration", "Confirm recruiter identity through an official channel", "Do not send money or financial credentials"]
    return {"model_probability": round(model_probability, 6), "rule_signal": round(rule_score, 6), "overall_risk_score": round(advisory_score, 6), "risk": risk, "warning_count": warning_count, "evidence": evidence, "missing_information": missing, "recommended_checks": checks, "advisory": True, "limitations": "The model probability and deterministic warnings are separate advisory signals; neither establishes that an employer is fraudulent."}


def audit_job(data: dict[str, Any]) -> dict[str, Any]:
    checks = []
    required = [("salary", "Salary information"), ("location", "Location"), ("employment_type", "Contract type"), ("responsibilities", "Responsibilities"), ("skills", "Required skills"), ("company_information", "Company information")]
    for key, label in required:
        value = data.get(key, "")
        present = bool(value) if isinstance(value, str) else bool(value)
        checks.append({"key": key, "label": label, "passed": present, "message": "Provided" if present else f"Missing {label.lower()}"})
    score = round(100 * sum(1 for c in checks if c["passed"]) / len(checks))
    warnings = [c["message"] for c in checks if not c["passed"]]
    return {"score": score, "checks": checks, "warnings": warnings, "formula": "passed checks / 6 × 100", "disclaimer": "This is a transparent input-completeness checklist, not a scientifically validated job-quality score."}


PACKAGE_FIELDS = ["normalized_job_title", "professional_summary", "responsibilities", "required_qualifications", "preferred_qualifications", "required_skills", "optional_skills", "interview_questions", "interview_rubric", "screening_criteria", "linkedin_post", "seo_title", "seo_summary"]


def package_missing(package: dict[str, Any]) -> list[str]:
    return [key for key in PACKAGE_FIELDS if not package.get(key) or (isinstance(package.get(key), list) and not any(str(x).strip() for x in package[key]))]


def validate_history(values: list[float], dates: list[str] | None = None) -> dict[str, Any]:
    clean = [max(0.0, float(v)) for v in values]
    gaps: list[str] = []
    if dates:
        parsed = sorted(date.fromisoformat(x) for x in dates)
        expected = {parsed[0] + timedelta(days=i) for i in range((parsed[-1] - parsed[0]).days + 1)} if parsed else set()
        gaps = [d.isoformat() for d in sorted(expected - set(parsed))]
    avg = mean(clean) if clean else 0.0
    recent = mean(clean[-7:]) if clean else 0.0
    volatility = pstdev(clean) if len(clean) > 1 else 0.0
    trend = "up" if recent > avg * 1.05 else "down" if recent < avg * .95 else "stable"
    zero_pct = round(100 * sum(v == 0 for v in clean) / len(clean), 2) if clean else 100.0
    seasonality = "weekly" if len(clean) >= 28 and pstdev([mean(clean[i::7]) for i in range(7)]) > max(.1, avg * .1) else "not established"
    return {"records": len(clean), "missing_dates": gaps[:100], "zero_demand_percent": zero_pct, "average_daily_demand": round(avg, 4), "recent_7_day_average": round(recent, 4), "volatility": round(volatility, 4), "trend": trend, "seasonality": seasonality, "suitable_for_m5_lightweight": len(clean) >= 28 and not gaps, "warnings": ([] if len(clean) >= 28 else ["More history is recommended for this horizon; the custom lightweight method can still provide an estimate."]) + (["Dates contain gaps; provide a complete daily series."] if gaps else [])}


def _mae(actual: list[float], predicted: list[float]) -> float:
    return mean(abs(a - p) for a, p in zip(actual, predicted)) if actual else float("inf")


def _predict_method(values: list[float], horizon: int, method: str) -> list[float]:
    values = [max(0.0, float(v)) for v in values]
    if method == "croston_sba":
        nonzero = [v for v in values if v > 0]
        return [max(0.0, (mean(nonzero) if nonzero else 0.0) * .95) for _ in range(horizon)]
    if method == "seasonal_naive" and len(values) >= 14:
        return [values[-7 + i % 7] for i in range(horizon)]
    if method == "holt_trend" and len(values) >= 4:
        slope = (mean(values[-7:]) - mean(values[-14:-7])) / 7 if len(values) >= 14 else (values[-1] - values[0]) / max(1, len(values) - 1)
        base = mean(values[-7:])
        return [max(0.0, base + slope * (i + 1)) for i in range(horizon)]
    window = min(7, len(values))
    return [max(0.0, mean(values[-window:])) for _ in range(horizon)]


def smart_forecast(values: list[float], horizon: int) -> dict[str, Any]:
    clean = [max(0.0, float(v)) for v in values]
    diagnostics = validate_history(clean)
    zero_share = diagnostics["zero_demand_percent"] / 100
    candidates = ["moving_average", "holt_trend"]
    if zero_share >= .4:
        candidates.append("croston_sba")
    if diagnostics["seasonality"] == "weekly":
        candidates.append("seasonal_naive")
    holdout = min(7, max(1, len(clean) // 4))
    train, actual = clean[:-holdout], clean[-holdout:]
    scores = {method: round(_mae(actual, _predict_method(train, holdout, method)), 6) for method in candidates} if len(train) >= 4 else {}
    method = min(scores, key=scores.get) if scores else "moving_average"
    why = "lowest holdout MAE among lightweight methods"
    if method == "croston_sba":
        why = "intermittent demand detected from frequent zero-demand days"
    elif method == "seasonal_naive":
        why = "weekly seasonality detected and lowest holdout MAE"
    return {"status": "complete", "model": method, "method": method, "why": why, "predictions": [round(x, 4) for x in _predict_method(clean, horizon, method)], "backtest_mae": scores.get(method), "candidate_scores": scores, "diagnostics": diagnostics, "m5_used": False, "disclaimer": "This is a lightweight custom-history forecast, not the Walmart M5 XGBoost model."}


def inventory_plan(history: list[float], lead_time: int, stock: float, service_level: float = .95, incoming: float = 0.0) -> dict[str, Any]:
    diagnostics = validate_history(history)
    daily = diagnostics["recent_7_day_average"] or diagnostics["average_daily_demand"]
    volatility = diagnostics["volatility"]
    z = 1.645 if service_level >= .95 else 1.282 if service_level >= .90 else 1.0
    safety_stock = z * volatility * (lead_time ** .5)
    lead_demand = daily * lead_time
    reorder_point = lead_demand + safety_stock
    available = stock + incoming
    return {"assumptions": {"daily_demand": daily, "service_level": service_level, "lead_time_days": lead_time, "safety_stock_formula": "z * demand_stddev * sqrt(lead_time)"}, "expected_lead_time_demand": round(lead_demand, 4), "safety_stock": round(safety_stock, 4), "reorder_point": round(reorder_point, 4), "stock_coverage_days": round(available / daily, 2) if daily > 0 else None, "estimated_stockout_risk": "high" if available < lead_demand else "medium" if available < reorder_point else "low", "suggested_replenishment": round(max(0.0, reorder_point - available), 4), "diagnostics": diagnostics}


def demand_scenario(base: float, demand_change_percent: float, stock: float, lead_time: int, replenishment: float) -> dict[str, Any]:
    adjusted = max(0.0, base * (1 + demand_change_percent / 100))
    return {"assumption": f"Demand changes by {demand_change_percent:.2f}% supplied by the user; no price-elasticity model is applied.", "daily_demand": round(adjusted, 4), "lead_time_demand": round(adjusted * lead_time, 4), "ending_stock_after_lead_time": round(stock + replenishment - adjusted * lead_time, 4), "stockout_under_assumption": stock + replenishment < adjusted * lead_time}


def product_audit(data: dict[str, Any]) -> dict[str, Any]:
    checks = []
    for key, label in [("title", "Title"), ("category", "Category"), ("brand", "Brand"), ("specifications", "Specifications"), ("description", "Description"), ("features", "Features")]:
        value = data.get(key, "")
        checks.append({"key": key, "label": label, "passed": bool(value), "message": "Provided" if value else f"Missing {label.lower()}"})
    score = round(100 * sum(c["passed"] for c in checks) / len(checks))
    return {"score": score, "checks": checks, "warnings": [c["message"] for c in checks if not c["passed"]], "claim_policy": "User facts and retrieved catalog facts must be verified separately; generated suggestions are not product evidence."}
