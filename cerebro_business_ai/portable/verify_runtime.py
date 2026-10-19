"""Checks the copied artifacts with the private runtime, without training."""
import json
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root),str(root/'ai-service')]
import joblib
import numpy as np
from app.main import load_real_fraud_model
from app.rag import retrieve
from app.m5_forecasting import forecast_from_history
from app.resource_guard import ResourceGuard

fraud=load_real_fraud_model()
if fraud is None:raise SystemExit('Missing fraud model')
p=fraud.predict_proba(['Software developer. React TypeScript. Technical interview, full time.'])
assert np.isfinite(p).all()
refs=retrieve('Bones skateboard wheels',3,'Sports & Outdoors')
assert refs, 'Known catalog probe returned no retrieval matches'
pred=forecast_from_history([1,2,3,4,5,6,7]*8,7)
assert len(pred)==7 and all(np.isfinite(pred))
for module in ('services.gateway','services.fraud.service','services.job.service','services.demand.service','services.product.service'):
    __import__(module)
assert (root/'frontend/dist/index.html').is_file()
print(json.dumps({'status':'passed','fraud_model':'loaded and predicted','rag_index':'loaded and queried','rag_matches':len(refs),'m5_model':'loaded and predicted','services_imported':5,'resources':ResourceGuard().as_dict()},indent=2))
