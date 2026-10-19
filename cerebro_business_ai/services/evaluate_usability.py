"""Sequential real HTTP checks for the two reported workflows. No training."""
import argparse
import csv
import json
import time
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:8900'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['before','after','after_final','final_fraud'],required=True)
    phase=parser.parse_args().phase
    output=ROOT/f'data/reliability_review/{phase}.json'
    if output.exists(): raise SystemExit(f'Evidence already exists: {output}')
    started=time.perf_counter();results={'phase':phase,'synthetic_forecast_data':True,'fraud':[],'forecast':[]}
    postings={
        'brightpath':(ROOT/'data/reliability_review/brightpath.txt').read_text(encoding='utf-8'),
        'detailed_junior':'Junior Frontend Developer. Company: Demo Software. Full-time, 40 hours per week. No professional experience required. Build React components, use TypeScript and Git, implement accessible HTML and CSS, and write unit tests. Mentoring and training provided. Salary 1800 to 2400 TND per month. Apply through careers.demo-software.tn. Two technical interviews and a paid practical exercise.',
        'urgent_senior':'Senior Frontend Developer, urgent hiring. Full-time, 40 hours per week. Salary 9000 to 12000 TND per month. Five years of React and TypeScript, performance profiling, component architecture and accessibility experience required. Technical interview and references required. Apply via careers.example.com.',
        'payment_request':'Remote data entry assistant. No experience required, earn $500/day for one hour per day. Please pay a registration fee before the interview and contact us on Telegram.'}
    for name,text in postings.items():
        response=requests.post(BASE+'/api/ai/jobs/review',json={'text':text},timeout=45)
        results['fraud'].append({'case':name,'http':response.status_code,'response':response.json()})
    if phase=='final_fraud':
        output.write_text(json.dumps(results,indent=2),encoding='utf-8')
        print(json.dumps({'output':str(output),'fraud':[{'case':r['case'],'http':r['http'],'advisory':r['response'].get('advisory'),'model_probability':r['response'].get('model_probability'),'warnings':r['response'].get('warning_count')} for r in results['fraud']]},indent=2))
        return
    inputs={}
    for file in sorted((ROOT/'sample_sales_histories').glob('*.csv')):
        with file.open(newline='',encoding='utf-8') as stream: records=list(csv.DictReader(stream))
        rows=[{'date':r['date'],'sales':float(r['sales']),'price':float(r['price']),'visitors':float(r['visitors']),'promotion':r['promotion']=='1','stockout':r['stockout']=='1'} for r in records]
        inputs[file.name]={'product_name':records[0]['product'],'rows':rows,'stock':30,'incoming':0,'lead_days':7}
        for horizon in (7,14,28):
            payload={**inputs[file.name],'horizon':horizon}
            check_forecast(results,file.name,payload,'default')
    traffic=next(v for k,v in inputs.items() if 'traffic_driven' in k)
    for name,extra in [('zero_traffic',{'future_visitors':0}),('minus_100_percent',{'assumed_demand_change':-100}),('huge_stock',{'stock':100000})]:
        check_forecast(results,'traffic_driven_controls',{**traffic,'horizon':14,**extra},name)
    results['seconds']=round(time.perf_counter()-started,3)
    output.write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps({'output':str(output),'seconds':results['seconds'],'fraud':[{'case':x['case'],'http':x['http'],'advisory':x['response'].get('advisory'),'model_probability':x['response'].get('model_probability'),'warnings':x['response'].get('warning_count')} for x in results['fraud']],
        'forecast':[ {k:v for k,v in x.items() if k not in ('resources','holdout')} for x in results['forecast']]},indent=2))


def check_forecast(results,file,payload,case):
    start=time.perf_counter();response=requests.post(BASE+'/api/ai/demand/plan',json=payload,timeout=45);data=response.json()
    points=data.get('forecast',[])
    results['forecast'].append({'file':file,'case':case,'horizon':payload['horizon'],'http':response.status_code,'method':data.get('method'),'predicted_units':round(sum(p['scenario'] for p in points),3),'baseline_units':round(sum(p['baseline'] for p in points),3),'zero_days':sum(p['scenario']==0 for p in points),'order_quantity':data.get('inventory',{}).get('order_quantity'),'holdout':data.get('holdout'),'warnings':data.get('warnings'),'zero_explanation':data.get('zero_explanation'),'resources':data.get('resources'),'seconds':round(time.perf_counter()-start,3),'error':data.get('detail')})


if __name__=='__main__': main()
