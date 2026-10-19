import json
from pathlib import Path
import numpy as np


def main():
    root=Path(__file__).resolve().parents[1]/'data/reliability_review'
    comparison={}
    for phase in ('before','after','after_final'):
        data=json.loads((root/f'{phase}.json').read_text(encoding='utf-8'))
        cases=[c for c in data['forecast'] if c['case']=='default' and c['horizon']==14]
        errors=[];actuals=[]
        for case in cases:
            for p in case['holdout']['points']:
                if not p.get('stockout'):
                    errors.append(p['actual']-p['predicted']);actuals.append(p['actual'])
        errors=np.asarray(errors)
        resources=[s for c in data['forecast'] for s in (c.get('resources') or {}).values()]
        comparison[phase]={'cases':len(data['forecast']),'http_200':sum(c['http']==200 for c in data['forecast']),
            'default_zero_total_cases':sum(c['case']=='default' and c['baseline_units']==0 for c in data['forecast']),
            'synthetic_14_day_aggregate':{'mae':float(np.mean(abs(errors))),'rmse':float(np.sqrt(np.mean(errors**2))),'wape':float(np.sum(abs(errors))/sum(actuals)*100)},
            'sampled_maxima':{key:max([s[key] for s in resources if s.get(key) is not None],default=None) for key in ('cpu_percent','ram_percent','gpu_percent','vram_percent','temperature_c')},
            'gpu_sensor_errors':sum(bool(s.get('sensor_error')) for s in resources),
            'mean_response_seconds':float(np.mean([c['seconds'] for c in data['forecast']])),
            'sparse_series':[{k:c[k] for k in ('horizon','method','predicted_units','zero_days')} for c in data['forecast'] if 'intermittent_spare' in c['file']]}
    path=root/'final_summary.json'
    with path.open('x',encoding='utf-8') as f:json.dump(comparison,f,indent=2)
    print(json.dumps(comparison,indent=2))


if __name__=='__main__':main()
