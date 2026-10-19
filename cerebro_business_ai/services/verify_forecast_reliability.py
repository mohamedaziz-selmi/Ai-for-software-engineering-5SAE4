"""Bounded local M5 audit of user-history methods; no model training or downloads."""
import csv
import json
import time
from datetime import date, timedelta
from itertools import islice
from pathlib import Path
import numpy as np
from services.planning import Plan, Sale, forecast, plan
from services.intelligence import ResourceGuard


def main():
    root=Path(__file__).resolve().parents[1]
    source=root/'data/phase2/kaggle/product_demand/extracted/sales_train_evaluation.csv'
    guard=ResourceGuard();before=guard.snapshot()
    if not guard.safe_to_start(before): raise SystemExit('ResourceGuard denied audit')
    started=time.perf_counter()
    with source.open(newline='',encoding='utf-8') as f:
        reader=csv.DictReader(f)
        days=[c for c in reader.fieldnames if c.startswith('d_')][-196:]
        pool=[{'id':r['id'],'y':np.array([float(r[c]) for c in days])} for r in islice(reader,120)]
    selected=[];used=set()
    rankings=[('intermittent',sorted(pool,key=lambda r:np.mean(r['y'][:-14]==0),reverse=True)),
              ('high_volume',sorted(pool,key=lambda r:r['y'][:-14].mean(),reverse=True)),
              ('low_volume',sorted(pool,key=lambda r:r['y'][:-14].mean()))]
    for group,ranked in rankings:
        available=[r for r in ranked if r['id'] not in used][:3]
        for r in available: used.add(r['id']);selected.append((group,r))
    old={'Moving average','Exponential smoothing','Damped trend','Weekly seasonal','Croston SBA','Context regression'}
    records=[];agg={'previous_method_family':[],'revised_selection':[]};actuals=[]
    first=date(2011,1,29)+timedelta(days=int(days[0][2:])-1)
    for group,r in selected:
        if guard.should_pause(): raise SystemExit('ResourceGuard stopped audit')
        rows=[Sale(date=first+timedelta(days=i),sales=v) for i,v in enumerate(r['y'])]
        result=plan(Plan(product_name=r['id'],rows=rows,horizon=14))
        prior=min((s for s in result['scores'] if s['method'] in old),key=lambda s:s['mae'])['method']
        prior_pred=forecast(r['y'][:-14],14,prior)
        revised_pred=np.array([p['predicted'] for p in result['holdout']['points']])
        truth=r['y'][-14:];actuals.extend(truth.tolist())
        for name,pred in [('previous_method_family',prior_pred),('revised_selection',revised_pred)]:agg[name].extend((truth-pred).tolist())
        records.append({'product':r['id'],'group':group,'train_zero_percent':round(float(np.mean(r['y'][:-14]==0)*100),2),'previous_method':prior,'revised_method':result['method'],'previous_test_mae':float(np.mean(abs(truth-prior_pred))),'revised_test':result['holdout']})
    metrics={}
    for name,errors in agg.items():
        e=np.array(errors);metrics[name]={'mae':float(np.mean(abs(e))),'rmse':float(np.sqrt(np.mean(e**2))),'wape':float(np.sum(abs(e))/np.sum(actuals)*100) if sum(actuals)>0 else None}
    report={'scope':'9 series selected from the first 120 M5 evaluation rows; bounded diagnostic sample, not a representative benchmark. Previous method family and revised selection use identical rolling validation and a final 14-day test. Existing M5 model metrics remain unchanged.',
            'source':str(source),'history_days':196,'series':len(records),'metrics':metrics,'records':records,'seconds':round(time.perf_counter()-started,3),'resources':{'before':guard.as_dict(before),'after':guard.as_dict()}}
    output=root/'data/forecast_reliability_v1.json'
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2))


if __name__=='__main__': main()
