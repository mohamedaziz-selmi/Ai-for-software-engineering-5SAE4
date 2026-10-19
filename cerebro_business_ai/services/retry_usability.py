"""Retry only ResourceGuard-deferred local cases, preserving the original evidence."""
import csv
import json
from pathlib import Path
from services.evaluate_usability import check_forecast


def main():
    root=Path(__file__).resolve().parents[1]
    evidence=root/'data/reliability_review'
    original=json.loads((evidence/'after_final.json').read_text(encoding='utf-8'))
    retry={'forecast':[],'reason':'Sequential retry after a recorded ResourceGuard 503; original evidence retained.'}
    allowed={p.name:p for p in (root/'sample_sales_histories').glob('*.csv')}
    for case in original['forecast']:
        if case['http']!=503:continue
        if case['file'] not in allowed or case['case']!='default':raise ValueError('Unexpected retry target')
        with allowed[case['file']].open(newline='',encoding='utf-8') as f:records=list(csv.DictReader(f))
        rows=[{'date':r['date'],'sales':float(r['sales']),'price':float(r['price']),'visitors':float(r['visitors']),'promotion':r['promotion']=='1','stockout':r['stockout']=='1'} for r in records]
        check_forecast(retry,case['file'],{'product_name':records[0]['product'],'rows':rows,'stock':30,'incoming':0,'lead_days':7,'horizon':case['horizon']},case['case'])
    with (evidence/'retry_failed.json').open('x',encoding='utf-8') as f:json.dump(retry,f,indent=2)
    print(json.dumps([{k:c[k] for k in ('file','horizon','http','method','predicted_units','error')} for c in retry['forecast']],indent=2))


if __name__=='__main__':main()
