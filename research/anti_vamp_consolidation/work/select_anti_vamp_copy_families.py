"""Reproduce the pre-confirmation copy-only policy selection from the full grid."""
from pathlib import Path
import sys,json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'work/anti_vamp'))
import study

out=ROOT/'outputs/anti_vamp_study'
assert not (out/'confirmation.csv.gz').exists(),'Select and freeze policies before confirmation'
plan=json.loads((out/'plan.json').read_text());frozen=json.loads((out/'frozen.json').read_text())
assert not any(x.get('family')=='copy_only' for x in frozen['selected'])
assert frozen['source_hashes']==study.hashes()
data=pd.read_csv(out/'training.csv.gz');options=study.policies()
eligible=[i for i,p in enumerate(options) if p.target==1 or p.budget==0]
for selected in frozen['selected']:selected['family']='overall'
for cell in dict.fromkeys(data.cell):
    scores=data[(data.cell==cell)&data.policy.isin(eligible)].groupby('policy').profit.mean()
    best=max(scores.index,key=lambda i:(scores[i],-i))
    frozen['selected'].append(dict(cell=cell,family='copy_only',policy=study.asdict(options[best]),training_mean=float(scores[best])))
plan['copy_family_selection']='Best mean complete-exit P&L among copy-target policies and abstention; frozen before confirmation'
frozen['plan_hash']=study.digest(plan)
(out/'plan.json').write_text(json.dumps(plan,indent=2))
(out/'frozen.json').write_text(json.dumps(frozen,indent=2))
print('Overall and copy-only policies frozen; confirmation may now run')
