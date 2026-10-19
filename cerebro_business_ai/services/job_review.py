"""Posting-only evidence: offsets always refer to the unchanged submitted text."""
import re
from urllib.parse import urlparse
from pydantic import BaseModel, Field
from fastapi import HTTPException
from services.intelligence import ResourceGuard
from services.compensation import NUMBER, CURRENCY, AMOUNT, PAY_PATTERN, HOURS_PATTERN, stated_pay, stated_hours, short_day, pay_details

class Posting(BaseModel):
    text: str = Field(min_length=15,max_length=16000)
    employer: str = Field(default='',max_length=200)
    official_domain: str = Field(default='',max_length=200, description='Optional known official domain supplied by the user.')

# Extract stated compensation without assuming a currency conversion or salary benchmark.
def negated_request(text,match):
    prefix=text[max(0,match.start()-85):match.start()]
    if re.search(r'\bne\s*$',prefix,re.I) and re.search(r'\b(?:pas|jamais)\b',match.group(),re.I):return True
    # Negation must be in the same clause immediately preceding the request.
    return bool(re.search(r'(?:\bno\s+|\bwithout\s+(?:a\s+)?|\b(?:aucun(?:e|es|s)?|sans)\s+|\b(?:never|do not|don[’\x27]t|will not|won[’\x27]t)\s+(?:(?:ask|require|send|share|charge|collect)\s+(?:you\s+)?(?:to\s+|for\s+)?(?:a\s+|an\s+|any\s+)?)?|\b(?:ne\s+)?(?:payez|versez|envoyez|communiquez|demandons|exigeons)\s+(?:jamais|pas)\s+(?:de\s+|d[’\x27])?)$',prefix,re.I))

def review(request: Posting):
    from app.main import load_real_fraud_model
    guard=ResourceGuard(); snap=guard.snapshot()
    if not guard.safe_to_start(snap): raise HTTPException(503,'Computer is busy. Retry shortly.')
    model=load_real_fraud_model()
    if model is None: raise HTTPException(503,'The saved fraud model is unavailable.')
    text=request.text
    probability=float(model.predict_proba([text])[0][1])
    evidence=[]
    rules=[
        ('Upfront payment',r'\b(?:pay\s+(?:a\s+|an\s+|the\s+)?(?:registration|application|training|equipment|processing)\s*(?:fee|deposit)?|registration fee|application fee|send (?:money|gift cards?|crypto)|pay for equipment|frais\s+(?:de\s+|d[’\x27])(?:inscription|dossier|formation|recrutement|candidature)|(?:payez|payer|versez|verser)\s+(?:un\s+|une\s+)?(?:acompte|caution|frais))\b','high','Ask why payment is required and independently verify the employer before paying.'),
        ('Financial information',r'\b(?:bank account|routing number|card number|crypto wallet|IBAN|RIB|coordonn[ée]es bancaires|num[ée]ro de carte|compte bancaire)\b','high','Confirm the hiring stage and verify the HR contact before sharing financial details.'),
        ('Identity document request',r'\b(?:passport|social security number|national ID|passeport|carte d[’\x27]identit[ée]|CIN)\b','medium','Verify the recipient and reason before sharing identification.'),
        ('Informal contact',r'\b(?:Telegram|WhatsApp|SMS.only)\b','medium','Find and contact the employer through an independently verified official channel.'),
        ('Personal email',r'[\w.+-]+@(?:gmail|yahoo|outlook|hotmail)\.[a-z]+','medium','A personal address alone proves nothing; confirm recruiter identity.'),
        ('Credentials or verification codes requested',r'\b(?:send|share|provide|reveal|envoyez|communiquez|partagez|fournir)\b[^.\n]{0,65}\b(?:password|OTP|one[- ]time (?:code|password)|PIN|mot de passe|code de v[ée]rification|code secret)\b','high','Do not share account passwords or one-time verification codes with a recruiter. Verify the request through an official channel.'),
        ('No interview or guaranteed selection',r'\b(?:no interview(?: required)?|without (?:an? )?interview|sans entretien|aucun entretien|embauche garantie|guaranteed (?:job|selection|hiring))\b','medium','Ask for the interview and assessment process and verify who is making the offer.'),
    ]
    def add(category,match,severity,action):
        evidence.append({'category':category,'start':match.start(),'end':match.end(),'text':match.group(), 'severity':severity,'action':action})
    for category,pattern,severity,action in rules:
        for m in re.finditer(pattern,text,re.I):
            if negated_request(text,m):continue
            if category in ('Financial information','Identity document request'):
                context=text[max(0,m.start()-90):min(len(text),m.end()+65)]
                if not re.search(r'\b(?:send|provide|share|submit|enter|ask|require[ds]?|request|upload|demandons?|envoy(?:er|ez)|communiqu(?:er|ez)|fourn(?:ir|issez)|transmett(?:re|ez)|renseigne(?:r|z)|exig[ée]s?|requis|obligatoire)\b',context,re.I):continue
            add(category,m,severity,action)
    pay=stated_pay(text)
    hours=stated_hours(text)
    short_hours=[m for m in hours if short_day(m)]
    details=pay_details(text)
    compensation=[m for m,d in zip(pay,details) if d['kind']!='requested_payment']
    high_daily=[m for m,d in zip(pay,details) if d['kind']!='requested_payment' and d['currency'] in ('EUR','GBP','USD','DOLLAR_UNSPECIFIED') and d['period'] in ('day','hour') and d['maximum']>=300]
    for m in high_daily:
        add('Compensation requires context',m,'medium','Verify hours, payment conditions and duties. This is a transparent heuristic, not a salary-market benchmark.')
    if high_daily:
        for m in short_hours: add('High pay for little time',m,'high','Ask for a written explanation of duties and how compensation is earned.')
        for m in re.finditer(r'no experience|basic English|smartphone|18\+',text,re.I): add('High pay with minimal requirements',m,'medium','Check whether the responsibilities and qualification requirements justify the offer.')
    minimal=list(re.finditer(r'\b(?:no (?:prior |professional )?experience\b(?:\s+(?:is\s+)?(?:required|needed))?|anyone with basic computer skills|basic (?:knowledge of )?computers?(?: and internet)?|smartphone)|\b(?:sans exp[ée]rience|aucune exp[ée]rience(?: requise)?|d[ée]butants? accept[ée]s?)\b',text,re.I))
    technical=re.search(r'\b(?:front[- ]?end|back[- ]?end|software|web|full[- ]?stack)\s+(?:developer|engineer)|d[ée]veloppeur\s+(?:web|front[- ]?end)',text,re.I)
    concrete_skills=re.search(r'\b(?:React|Angular|Vue|Svelte|TypeScript|JavaScript|HTML|CSS|Python|Java|C\+\+|C#|SQL|Git|accessibility|WCAG|Next\.js|PHP|Laravel|Django)\b',text,re.I)
    fulltime=re.search(r'\bfull[- ]time\b|\btemps plein\b',text,re.I)
    if fulltime and short_hours:
        for m in short_hours: add('Full-time label with short workdays',m,'medium','Ask for the contracted weekly hours and schedule; the full-time label and advertised short workdays need clarification.')
    if technical and minimal and not concrete_skills:
        add('Technical role without concrete skill requirements',technical,'medium','Ask for the technology stack, actual responsibilities, supervision and technical assessment. Entry-level hiring alone is not suspicious.')
    earnings_promise=re.search(r'great income|excellent salary|guaranteed (?:income|earnings)|revenus? garantis?|salaire exceptionnel|gagnez facilement|argent facile',text,re.I)
    if compensation and short_hours and minimal and (earnings_promise or (fulltime and technical and not concrete_skills)):
        add('Compensation, short days and minimal requirements',compensation[0],'high','Verify the written salary, hours, responsibilities and hiring process together. This combination warrants investigation; no local salary-market benchmark was used.')
    urgency=re.search(r'urgent hiring|fill this position immediately|hiring immediately|recrutement urgent',text,re.I)
    if urgency and any(e['severity']=='high' for e in evidence):
        add('Urgency alongside other warning signs',urgency,'medium','Take time to independently verify the offer rather than accepting pressure to proceed immediately.')
    no_interview=next((e for e in evidence if e['category']=='No interview or guaranteed selection'),None)
    if no_interview and any(e['category']=='Informal contact' for e in evidence):
        m=re.search(re.escape(no_interview['text']),text)
        add('Hiring bypassed through informal contact',m,'high','Verify the employer and hiring process independently before proceeding through messaging apps.')
    cheque=re.search(r'\b(?:che(?:ck|que)|ch[èe]que)\b[^.\n]{0,180}\b(?:equipment|laptop|send|return|difference|mat[ée]riel|ordinateur|rembours|diff[ée]rence)\b',text,re.I)
    if cheque and re.search(r'deposit|cash|encaisser|d[ée]poser',text,re.I) and not negated_request(text,cheque):
        add('Cheque and onward-payment arrangement',cheque,'high','Independently verify any cheque and equipment arrangement. Do not return or forward funds on an unverified payment.')
    domains=list(re.finditer(r'(?<![\w-])(?:[a-z0-9-]+\.)+(?:com|org|net|io|co|fr|tn|uk)\b',text,re.I))
    expected=request.official_domain.lower().strip().removeprefix('https://').removeprefix('http://').split('/')[0]
    if expected:
        for m in domains:
            actual=m.group().lower()
            if actual!=expected and not actual.endswith('.'+expected): add('Contact differs from supplied official domain',m,'medium','Verify this address independently. A different domain is not proof of impersonation.')
    emails=re.findall(r'[\w.+-]+@[\w.-]+\.[a-z]{2,}',text,re.I)
    insufficient=len(text.split())<20
    missing=[]
    if not request.employer.strip(): missing.append('Employer identity has not been confirmed.')
    if not domains: missing.append('No website or email domain found.')
    if insufficient: missing.append('Too little description to assess responsibilities and hiring process.')
    high=any(e['severity']=='high' for e in evidence)
    level='Investigate before proceeding' if high or (probability>=.6 and not insufficient) else 'More information needed' if insufficient or evidence or probability>=.35 else 'No strong warning detected'
    return {'advisory':level,'risk_tier':'high' if high or (probability>=.6 and not insufficient) else 'needs_review' if level=='More information needed' else 'limited_signals',
        'decision_basis':'Evidence rules and the saved classifier are assessed independently. The classifier percentage is not a verified chance of fraud.',
        'model_probability':round(probability,5),'calibration':'Uncalibrated classifier output; a low value does not clear the posting.',
        'text':text,'evidence':evidence,'warning_count':len(evidence),'missing_information':missing,
        'compensation_details':details,
        'extracted':{'pay':[m.group() for m in compensation],'payment_requests':[d['text'] for d in details if d['kind']=='requested_payment'],'hours':[m.group() for m in hours],'domains':list(dict.fromkeys(m.group() for m in domains)),'emails':emails},
        'next_actions':list(dict.fromkeys(e['action'] for e in evidence)) or ['Verify the posting on the employer website and ask for the complete role and interview process.'],
        'limitations':['This checks the supplied posting only. No employer background investigation was performed.','Missing rule matches do not reduce the model probability.','A high model score alone does not establish fraud.'], 'resources':guard.as_dict(snap)}
