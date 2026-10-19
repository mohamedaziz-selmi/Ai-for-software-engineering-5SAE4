"""Run real, sequential HTTP checks; optionally include local Gemma inference."""
import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import time
import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-port', type=int, default=8900)
    parser.add_argument('--llm', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    base = f'http://127.0.0.1:{args.base_port}'
    results = []

    def check(name, method, url, payload=None, predicate=lambda d: True, status=200):
        start = time.perf_counter()
        try:
            response = requests.request(method, url, json=payload, timeout=240)
            try:
                data = response.json()
            except ValueError:
                data = response.text
            passed = response.status_code == status and bool(predicate(data))
            results.append({'case': name, 'passed': passed, 'http_status': response.status_code,
                            'seconds': round(time.perf_counter()-start, 3), 'response': data})
        except Exception as exc:
            results.append({'case': name, 'passed': False, 'seconds': round(time.perf_counter()-start, 3), 'error': str(exc)})

    for offset in range(5):
        check(f'health_{offset}', 'GET', f'http://127.0.0.1:{args.base_port+offset}/health')
        check(f'openapi_{offset}', 'GET', f'http://127.0.0.1:{args.base_port+offset}/openapi.json', predicate=lambda d: 'paths' in d)
    check('frontend', 'GET', f'http://127.0.0.1:{args.base_port+5}/', predicate=lambda d: 'id="root"' in d)
    check('frontend_api_config', 'GET', f'http://127.0.0.1:{args.base_port+5}/cerebro-config.js', predicate=lambda d: base in d)
    check('saved_fraud_prediction', 'POST', base+'/api/ai/jobs/detect-fraud',
          {'title': 'Frontend Developer', 'description': 'React and TypeScript engineer. Full time. Technical interview with our team.'},
          lambda d: 0 <= d['fraud_probability'] <= 1)
    check('french_euro_evidence', 'POST', base+'/api/ai/jobs/review',
          {'text': 'Travail à domicile sans expérience. Salaire de 3000 euros par mois. Payez 150 euros de frais avant de commencer. Contact Telegram.'},
          lambda d: any(p['currency']=='EUR' for p in d['compensation_details']) and d['risk_tier']=='high')
    check('m5_real_prediction', 'POST', base+'/api/ai/demand/forecast',
          {'history': [1,2,3,4,5,6,7]*8, 'horizon': 7}, lambda d: len(d['predictions'])==7)
    rows = [{'date': (date(2026,1,1)+timedelta(days=i)).isoformat(), 'sales': 8+i%7, 'price': 12.5} for i in range(56)]
    check('history_inventory_plan', 'POST', base+'/api/ai/demand/plan',
          {'product_name':'Coffee 250g', 'rows':rows, 'horizon':7, 'stock':30}, lambda d: bool(d))
    check('no_history_scenario', 'POST', base+'/api/ai/demand/scenario-planner',
          {'product_name':'Coffee launch', 'low':3,'expected':8,'high':15},
          lambda d: not d['model_used'] and d['scenarios'][1]['period_units']==112)
    check('invalid_scenario_rejected', 'POST', base+'/api/ai/demand/scenario-planner',
          {'product_name':'Coffee','low':20,'expected':8,'high':15}, status=422)
    check('rag_retrieval', 'POST', base+'/api/ai/products/retrieve',
          {'query':'Bones skateboard wheels','category':'Sports & Outdoors','top_k':3}, lambda d: len(d['references'])>0)
    if args.llm:
        check('real_hiring_gemma', 'POST', base+'/api/ai/jobs/brief',
              {'brief':'Hire a full-time React and TypeScript frontend developer in Tunis. Maintain an appointment booking application. Salary and benefits are not decided; flag them as missing. Two years of React experience are required.', 'language':'en'},
              lambda d: d.get('status')=='complete' and bool(d.get('output',{}).get('advertisement')))
        check('real_listing_gemma', 'POST', base+'/api/ai/products/brief',
              {'brief':'Je vends un casque Bluetooth noir, neuf, avec câble USB inclus. Autonomie, marque et garantie non confirmées. Ne pas inventer ces caractéristiques.', 'category':'Electronics','language':'fr'},
              lambda d: d.get('status')=='complete' and bool(d.get('output',{}).get('description')))
    report = {'passed': sum(x['passed'] for x in results), 'total':len(results), 'results':results,
              'scope':'Real local runtime checks with synthetic inputs, not accuracy benchmarking or a test on the recipient PC.'}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps({**report, 'results':[{k:v for k,v in r.items() if k!='response'} for r in results]}, indent=2))
    raise SystemExit(0 if report['passed']==report['total'] else 1)


if __name__=='__main__':
    main()
