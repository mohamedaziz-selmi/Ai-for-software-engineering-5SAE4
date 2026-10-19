"""Real sequential API verification for scenarios and bilingual job examples."""
import json
import time
from pathlib import Path
import requests


def main():
    root=Path(__file__).resolve().parents[1];output=root/'data/reliability_review/scenario_currency_v2.json'
    if output.exists():raise SystemExit('Verification evidence already exists; choose a new output path to run again.')
    results=[];start=time.perf_counter()
    def call(name,route,payload,check,status=200):
        t=time.perf_counter();response=requests.post('http://127.0.0.1:8900'+route,json=payload,timeout=45);data=response.json()
        valid=response.status_code==status and check(data)
        results.append({'case':name,'status':response.status_code,'passed':bool(valid),'seconds':round(time.perf_counter()-t,3),'request':payload,'response':data})
    scenario='/api/ai/demand/scenario-planner';fraud='/api/ai/jobs/review'
    call('daily_coffee',scenario,{'product_name':'Coffee launch','low':3,'expected':8,'high':15,'horizon':14,'current_stock':30,'lead_days':7},lambda d:d['scenarios'][1]['period_units']==112 and d['scenarios'][1]['recommended_order']==26 and not d['model_used'])
    call('traffic_conversion',scenario,{'product_name':'New product','basis':'traffic','visitors':200,'conversion_low':1,'conversion_expected':2,'conversion_high':4,'horizon':14},lambda d:d['scenarios'][1]['period_units']==56)
    call('fractional_order_rounds_up',scenario,{'product_name':'Part','low':0,'expected':.1,'high':1,'current_stock':0,'lead_days':1},lambda d:d['scenarios'][1]['recommended_order']==1)
    call('zero_demand_case',scenario,{'product_name':'Zero assumption','low':0,'expected':0,'high':0},lambda d:all(s['period_units']==0 and s['coverage_days'] is None for s in d['scenarios']))
    call('invalid_order_rejected',scenario,{'product_name':'Bad assumptions','low':10,'expected':2,'high':5},lambda d:'detail' in d,status=422)
    examples=[
        ('written_tunisian_dinars','Frontend Developer. Full-time, no experience required, work 3 to 4 hours a day. Salary 9000 to 12000 dinars tunisiens per month. Excellent salary; contact Telegram.','Compensation, short days and minimal requirements','TND'),
        ('bare_dinars','Développeur web sans expérience, temps plein. Revenu garanti de 9000 dinars par mois pour 2h/jour. Contact Telegram.','Compensation, short days and minimal requirements','DINAR_UNSPECIFIED'),
        ('euros_french_fee','Assistant sans expérience. Salaire 3000 euros par mois pour 2 heures par jour, revenu garanti. Payez des frais de dossier de 80 euros. WhatsApp uniquement.','Upfront payment','EUR'),
        ('decimal_euro_salary','Senior developer, 1.200,50 euros/mois. React TypeScript HTML CSS. 40 hours per week, technical interview and references.','no_high_rule','EUR'),
        ('usd_fee','Remote assistant. No experience required. Pay a registration fee of USD 80 before your interview and contact Telegram.','Upfront payment','USD'),
        ('credentials','Remote job offer. Please send your password and OTP to the recruiter before signing the contract.','Credentials or verification codes requested',None),
        ('no_interview_french','Assistant à distance. Aucun entretien. Embauche garantie, contactez WhatsApp pour votre contrat.','Hiring bypassed through informal contact',None),
        ('cheque_equipment','We send a cheque for equipment. Deposit the cheque and return the difference to our hiring agent before you start.','Cheque and onward-payment arrangement',None),
        ('negated_french_fee','Développeur React TypeScript. Salaire 3000 euros par mois, 40 heures par semaine, entretien technique. Aucun frais de dossier.','no_high_rule','EUR'),
        ('negated_credentials','Security engineer. We never ask you to share your password. TypeScript, secure API development and five years experience required.','no_high_rule',None),
        ('banking_duties','Backend developer for bank account APIs. Implement transaction processing using Java SQL and Git. Technical interview and references required.','no_high_rule',None),
    ]
    for name,text,category,currency in examples:
        def check(d,category=category,currency=currency):
            evidence=d['evidence'];rule_ok=not any(e['severity']=='high' for e in evidence) if category=='no_high_rule' else any(e['category']==category for e in evidence)
            offsets_ok=all(d['text'][e['start']:e['end']]==e['text'] for e in evidence)
            currency_ok=currency is None or any(p['currency']==currency for p in d['compensation_details'])
            return rule_ok and offsets_ok and currency_ok
        call(name,fraud,{'text':text},check)
    report={'scope':'Hand-authored synthetic behavior checks against the real saved classifier and APIs; not a measured real-world fraud accuracy benchmark.','seconds':round(time.perf_counter()-start,3),'passed':sum(r['passed'] for r in results),'total':len(results),'results':results}
    with output.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2,ensure_ascii=False)
    print(json.dumps({'output':str(output),'passed':report['passed'],'total':report['total'],'seconds':report['seconds'],'cases':[{k:r[k] for k in ('case','status','passed','seconds')} for r in results]},indent=2))
    if report['passed']!=report['total']:raise SystemExit(1)


if __name__=='__main__':main()
