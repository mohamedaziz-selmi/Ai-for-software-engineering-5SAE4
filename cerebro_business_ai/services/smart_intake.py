"""Deterministic smart-intake helpers.

These extract only evidence that can be pointed back to the user's text. They
prepare model inputs; they do not invent missing business facts.
"""
from __future__ import annotations
import re
from typing import Any

def _hit(text: str, pattern: str, label: str) -> list[dict[str, Any]]:
    return [{'value': m.group().strip(), 'start': m.start(), 'end': m.end(), 'source': 'user text', 'confidence': 1.0, 'label': label}
            for m in re.finditer(pattern, text, re.I)]

def fraud_intake(text: str, employer: str = '', official_domain: str = '') -> dict:
    from services.job_review import PAY_PATTERN, HOURS_PATTERN
    from services.compensation import pay_details
    fields = {
        'employer': _hit(text, r'(?:at|for|company(?:\s+name)?[:\s]+)([A-Z][\w& .-]{2,60})', 'claimed employer'),
        'compensation': _hit(text, PAY_PATTERN, 'compensation'),
        'hours': _hit(text, HOURS_PATTERN, 'working hours'),
        'location': _hit(text, r'\b(?:remote|on[- ]site|hybrid|in\s+[A-Z][A-Za-z .-]+)', 'location'),
        'email': _hit(text, r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', 'email'),
        'domain': _hit(text, r'(?<![@\w-])(?:[a-z0-9-]+\.)+(?:com|org|net|io|co|fr|tn|uk)\b', 'domain'),
        'telegram': _hit(text, r'\bTelegram\b', 'Telegram'),
        'whatsapp': _hit(text, r'\bWhatsApp\b', 'WhatsApp'),
        'url': _hit(text, r'https?://[^\s)]+', 'URL'),
        'financial_request': _hit(text, r'\b(?:bank account|routing number|card number|crypto wallet|IBAN|pay\s+(?:a|an|the)?\s*(?:registration|application|training|equipment|processing)?\s*fee)\b', 'financial request'),
        'identity_request': _hit(text, r'\b(?:passport|social security number|national ID|identity document)\b', 'identity document request'),
    }
    amounts=pay_details(text)
    fields['compensation']=[{'value':d['text'],'start':d['start'],'end':d['end'],'source':'user text','confidence':1.0,'label':'stated compensation or amount'} for d in amounts if d['kind']!='requested_payment']
    fields['requested_payment']=[{'value':d['text'],'start':d['start'],'end':d['end'],'source':'user text','confidence':1.0,'label':'requested payment amount'} for d in amounts if d['kind']=='requested_payment']
    flattened = [x for values in fields.values() for x in values]
    missing = []
    if not employer and not fields['employer']: missing.append('Employer identity has not been confirmed.')
    if not fields['email'] and not fields['domain'] and not fields['telegram'] and not fields['whatsapp']: missing.append('No contact channel was found.')
    if len(text.split()) < 20: missing.append('The posting is too short to assess the duties and hiring process.')
    return {'fields': fields, 'evidence': sorted(flattened, key=lambda x: x['start']), 'missing': missing, 'text_length': len(text), 'ready': len(text.split()) >= 20}

def _unique(values: list[str]) -> list[str]:
    seen = set(); out = []
    for value in values:
        key = value.casefold()
        if value and key not in seen: seen.add(key); out.append(value)
    return out

def hiring_intake(brief: str) -> dict:
    lower = brief.casefold()
    skills = _unique([x for x in ['Python','XGBoost','FastAPI','SQL','React','TypeScript','Docker','PyTorch','TensorFlow'] if x.casefold() in lower])
    seniority = next((x for x in ['principal','staff','senior','mid-level','junior','entry-level','lead'] if x in lower), '')
    locations = re.findall(r'\b(?:in|based in|located in)\s+([A-Z][A-Za-zÀ-ÿ -]{2,30})', brief)
    salary = re.findall(r'(?:[$€£]\s*)?\d[\d,.]*(?:\s*/|\s+per\s+)(?:hour|day|week|month|year)', brief, re.I)
    benefits = _unique([x for x in ['food','housing','health insurance','transport','meals','equipment','bonus'] if x in lower])
    title_words = re.search(r'\b((?:senior|junior|lead|staff|principal|mid-level|entry-level)\s+[A-Za-z][\w -]{2,45}?)(?=\s+(?:in|at|with|using|,|\.|$))', brief, re.I)
    title = title_words.group(1).strip(' ,.') if title_words else ''
    if not title:
        for candidate in ['machine learning engineer','software engineer','data scientist','developer','designer']:
            if candidate in lower: title = candidate.title(); break
    fields = {'role': title, 'seniority': seniority.title(), 'location': locations[0].strip() if locations else '', 'skills': skills,
              'salary': salary[0] if salary else '', 'benefits': benefits, 'work_arrangement': next((x for x in ['remote','hybrid','on-site','onsite'] if x in lower), ''),
              'contract_type': next((x for x in ['full-time','part-time','contract','freelance'] if x in lower), '')}
    missing = [label for key,label in [('contract_type','Contract type'),('work_arrangement','Work arrangement'),('experience','Experience years')] if not fields.get(key)]
    return {'fields': fields, 'missing': missing, 'source': 'deterministic extraction from brief'}

def product_intake(text: str, title: str = '', brand: str = '', category: str = '') -> dict:
    lower = text.casefold()
    known = [('battery', r'\b\d+\s*(?:-?hour|h)\s+battery\b'), ('bluetooth', r'\bbluetooth(?:\s+[\d.]+)?\b'), ('charging', r'\bUSB[- ]?C\b|\bwireless charging\b'), ('noise cancelling', r'\b(?:ANC|active noise cancelling|noise cancelling)\b'), ('microphone', r'\bmicrophone\b'), ('warranty', r'\bwarranty\b')]
    facts=[]
    for label, pattern in known:
        for hit in _hit(text, pattern, label): facts.append(hit)
    inferred_category = category or ('Headphones' if 'headphone' in lower else 'Electronics' if any(x in lower for x in ['bluetooth','usb','battery']) else '')
    brand_match = re.search(r'(?:^|,)\s*([A-Z][A-Za-z0-9-]{2,20})(?=\s*(?:,|\b(?:wireless|over-ear|in-ear|headphones?|speaker|laptop|phone)\b))', text)
    inferred_brand = brand or (brand_match.group(1) if brand_match and brand_match.group(1).casefold() not in {'wireless','bluetooth'} else '')
    inferred_title = title or (re.search(r'\b(?:wireless|over-ear|in-ear)?\s*(?:headphones?|speaker|laptop|phone)\b', text, re.I).group(0).strip().title() if re.search(r'\b(?:wireless|over-ear|in-ear)?\s*(?:headphones?|speaker|laptop|phone)\b', text, re.I) else '')
    missing = [label for label, marker in [('Compatibility','compatibility'),('Warranty','warranty'),('Microphone','microphone')] if marker not in lower]
    return {'fields': {'product': inferred_title, 'brand': inferred_brand, 'category': inferred_category, 'facts': facts}, 'missing': missing, 'source': 'deterministic extraction from verified facts'}
