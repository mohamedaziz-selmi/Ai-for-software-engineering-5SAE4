"""Install bundled pip locally into the private embedded Python runtime."""
from pathlib import Path
import runpy
import sys

root=Path(__file__).resolve().parents[1]
wheels=root/'installer/wheels'
pip_wheels=list(wheels.glob('pip-*.whl'))
if len(pip_wheels)!=1:raise SystemExit('Exactly one bundled pip wheel is required.')
sys.path.insert(0,str(pip_wheels[0]))
sys.argv=[__file__,'install','--no-index','--find-links',str(wheels),'--no-warn-script-location','pip==26.2.1']
runpy.run_module('pip',run_name='__main__')
