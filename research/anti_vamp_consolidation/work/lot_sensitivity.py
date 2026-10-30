"""Exploratory sell-policy audit, after frozen primary confirmation; no retraining."""
from pathlib import Path
from collections import defaultdict
from dataclasses import asdict
import sys,json,hashlib,time
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'work/c_followup'))
from open_model import OpenWorld,Setting,Strategy,tape_for
from upstream.ledger import Refused
from run_study import ci,save,hashes

OUT=ROOT/'outputs/c_permissionless_study'
DEST=OUT/'lot_sensitivity'

class LotWorld(OpenWorld):
    def __init__(self,*args,**kwargs):
        self.lots={};self.pending=None
        super().__init__(*args,**kwargs)

    def opportunity(self,row):
        self.pending=row['id']
        try:super().opportunity(row)
        finally:self.pending=None

    def buy(self,owner,token,budget):
        tx=super().buy(owner,token,budget)
        if owner.startswith('u:') and self.pending is not None:
            self.lots[self.pending]=[owner,token,tx.quantity]
        return tx

    def exit_opportunity(self,row):
        lot=self.lots.get(row['id'])
        if lot is None:return
        owner,target,remaining=lot
        quantity=int(remaining*row['exit_fraction'])
        if not quantity:return
        try:tx=self.sell(owner,target,quantity)
        except Refused:return
        lot[2]-=quantity
        self.activity.append((self.b.time,owner,tx.principal))

    def snapshot(self,label):
        if label!='exit':
            expected=defaultdict(int)
            for owner,token,remaining in self.lots.values():expected[owner,token]+=remaining
            actual={(owner,token):v for (owner,token),v in self.b.hold.items() if owner.startswith('u:') and v}
            assert {key:v for key,v in expected.items() if v}==actual,'lot coverage'
        return super().snapshot(label)

def smoke():
    s=Setting();w=LotWorld(s,'A',tape_for(2003,s))
    for row in w.t['open_launches']:w.launch(row)
    w.pending=1;x=w.buy('u:0',0,20_000_000)
    w.pending=2;y=w.buy('u:0',0,20_000_000)
    w.pending=None
    before=w.b.q[0]
    w.exit_opportunity(dict(id=1,exit_fraction=.5))
    assert before-w.b.q[0]==int(x.quantity*.5)
    assert w.lots[2][2]==y.quantity
    w.snapshot('1h')
    a=LotWorld(s,'A',tape_for(2003,s));b=LotWorld(s,'A',tape_for(2003,s))
    assert a.run()==b.run()

def main():
    smoke()
    if DEST.exists():raise RuntimeError('Supplement already exists; use a new named bundle')
    DEST.mkdir()
    plan=json.loads((OUT/'plan.json').read_text());frozen=json.loads((OUT/'frozen.json').read_text())
    assert frozen['source_hashes']==hashes()
    lookup={s['name']:s for s in plan['settings']}
    predeclared=dict(created_after_primary_confirmation=True,exploratory=True,seeds=plan['confirmation_seeds'],
        settings=['base','spam90','combined90'],policies='idle and unchanged trained C policy; same policy in A',
        planned_worlds=1200,retraining=False,new_independent_seeds=False,
        change='Each planned sell redeems a fraction of its own acquisition lot rather than the full current mint balance',
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (DEST/'plan.json').write_text(json.dumps(predeclared,indent=2))
    rows=[];start=time.perf_counter()
    for seed in plan['confirmation_seeds']:
        for name in predeclared['settings']:
            s=Setting(**lookup[name])
            p=Strategy(**next(x['policy'] for x in frozen['selected'] if x['setting']==name and x['arch']=='C'))
            for arch,kind,policy in [('A','idle',Strategy()),('C','idle',Strategy()),('C','trained',p),('A','matched_C_policy',p)]:
                w=LotWorld(s,arch,tape_for(seed,s),policy)
                for row in w.run():row.update(kind=kind);rows.append(row)
        if (seed-29999)%20==0:print('LOT AUDIT',seed-29999,'/100;',round(time.perf_counter()-start,1),'sec',flush=True)
    save(DEST/'runs.csv.gz',rows)
    data=pd.DataFrame(rows);effects=[];attacks=[]
    for name in predeclared['settings']:
        for metric in ('cohort_reserve','winner_depth','active'):
            a=data[(data.setting==name)&(data.arch=='A')&(data.kind=='idle')&(data.label=='7d')].set_index('seed').sort_index()
            c=data[(data.setting==name)&(data.arch=='C')&(data.kind=='idle')&(data.label=='7d')].set_index('seed').sort_index()
            mean,lo,hi=ci(c[metric]-a[metric],f'lot:{name}:{metric}')
            effects.append(dict(setting=name,metric=metric,A_mean=float(a[metric].mean()),C_mean=float(c[metric].mean()),delta=mean,low=lo,high=hi))
        a=data[(data.setting==name)&(data.arch=='A')&(data.kind=='matched_C_policy')&(data.label=='exit')].set_index('seed').sort_index()
        c=data[(data.setting==name)&(data.arch=='C')&(data.kind=='trained')&(data.label=='exit')].set_index('seed').sort_index()
        mean,lo,hi=ci(c.attacker_profit-a.attacker_profit,f'lot-attack:{name}')
        attacks.append(dict(setting=name,C_profit=float(c.attacker_profit.mean()),A_same_policy=float(a.attacker_profit.mean()),added_profit=mean,low=lo,high=hi))
    save(DEST/'effects.csv',effects);save(DEST/'attacks.csv',attacks)
    (DEST/'manifest.json').write_text(json.dumps(dict(status='complete',worlds=1200,seeds=100,checkpoint_rows=len(rows),
        elapsed=time.perf_counter()-start,exploratory=True,new_independent_seeds=False,policies_retrained=False,
        lot_coverage_checks=True,smoke_tests=2,primary_source_unchanged=hashes()==frozen['source_hashes']),indent=2))
    (OUT/'source/lot_sensitivity.py').write_bytes(Path(__file__).read_bytes())
    print(pd.DataFrame(effects).to_string(index=False));print(pd.DataFrame(attacks).to_string(index=False))

if __name__=='__main__':main()
