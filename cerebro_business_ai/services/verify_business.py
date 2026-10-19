"""Real sequential local API acceptance requests. Writes evidence, never fabricated results."""
import json
import time
from pathlib import Path
import requests
from datetime import date, timedelta

ROOT=Path(__file__).resolve().parents[1]
def main():
    cases=[
        ('fraud','/api/ai/jobs/review',{'text':'Work from home 1 hour a day. Earn $500/day. No experience. Contact Telegram and pay a registration fee.'}),
        ('demand','/api/ai/demand/plan',{'rows':[{'date':(date(2026,1,1)+timedelta(days=i)).isoformat(),'sales':[2,4,6,3,8,12,10][i%7]} for i in range(84)],'horizon':7,'stock':30,'lead_days':7,'assumed_demand_change':20}),
        ('hiring','/api/ai/jobs/brief',{'brief':'We need a senior ML engineer to deploy retail forecasting APIs using Python, XGBoost and FastAPI. Pay 5000/month, meals and housing. Help define the role and assess candidates.','title':'Senior Machine Learning Engineer','language':'en'}),
        ('product','/api/ai/products/brief',{'brief':'Wireless over-ear headphones. USB-C charging, foldable design, 3.5 mm wired connection. Black. For students. Battery life and noise cancellation have not been verified.','title':'Northline headphones','category':'Electronics','language':'en'}),
        ('hiring_fr','/api/ai/jobs/brief',{'brief':'Nous cherchons un développeur Python pour automatiser nos rapports de ventes et maintenir une API FastAPI. Aidez-nous à définir les missions et les questions techniques.','language':'fr'}),
    ]
    evidence=[]
    for name,path,payload in cases:
        start=time.perf_counter()
        try:
            r=requests.post('http://127.0.0.1:8900'+path,json=payload,timeout=220)
            entry={'case':name,'status':r.status_code,'seconds':round(time.perf_counter()-start,2),'request':payload,'response':r.json()}
        except Exception as exc:
            entry={'case':name,'error':str(exc)}
        evidence.append(entry)
        print(json.dumps({k:v for k,v in entry.items() if k not in ('request','response')}),flush=True)
        out=ROOT/'data'/'business_acceptance.json'
        out.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    if any(e.get('status')!=200 for e in evidence): raise SystemExit(1)
if __name__=='__main__': main()
