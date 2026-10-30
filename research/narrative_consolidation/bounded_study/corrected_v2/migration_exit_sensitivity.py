"""Exploratory holding-policy check; never changes the frozen primary study.

Carry original planned sell intents forward to the received winner after a
voluntary conversion. The primary policy retains mint-specific sell intents.
The same already-trained capture policy is evaluated, without retraining.
"""
from pathlib import Path
from dataclasses import asdict
import gzip,json,hashlib,sys
import pandas as pd

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[3]))
from bonding_lab.narrative.model import World,Config,Policy,canonical
from bonding_lab.narrative.experiments import fresh,save_csv,write_json,sources
from bonding_lab.narrative.report import ci


class ContinuousExitWorld(World):
    def voluntary_migration(self):
        before=dict(self.b.hold)
        super().voluntary_migration()
        if self.winner is None:return
        converted=set()
        for (owner,loser),qty in before.items():
            if owner.startswith('u:') and loser in self.members and loser!=self.winner and qty>0:
                if self.b.hold.get((owner,loser),0)==0 and self.b.hold.get((owner,self.winner),0)>before.get((owner,self.winner),0):
                    converted.add((owner,loser))
        self.rebound=0
        for row in self.t['opportunities']:
            key=(f"u:{row['actor']}",self.actual.get(row['id']))
            if row['t']<=self.b.time and key in converted:
                self.actual[row['id']]=self.winner;self.rebound+=1
        self.b.invariant()


def main():
    plan=json.loads((ROOT/'frozen_plan.json').read_text())
    assert sources()==plan['source_sha256']
    out=fresh(ROOT/'exit_continuity_sensitivity')
    control=next(t for t in plan['targets'] if t['name']=='C')
    attack=next(t for t in plan['targets'] if t['name']=='ATTACK_C_capture')
    rows=[]
    for seed in plan['seeds']:
        with gzip.open(ROOT/'confirmation/tapes'/f'{seed}.json.gz','rt',encoding='utf-8') as f:tape=json.load(f)
        for target in (control,attack):
            w=ContinuousExitWorld(Config(**target['config']),tape,Policy(**target['policy']))
            observations,_,_=w.run()
            for r in observations:
                if r['label'] in ('plus_7d','feasible_exit'):
                    r['rebound_sale_intents']=getattr(w,'rebound',0);rows.append(r)
    save_csv(out/'runs.csv.gz',rows)
    original=pd.read_csv(ROOT/'confirmation/runs.csv.gz')
    alternative=pd.DataFrame(rows)
    effects=[]
    for target in (control,attack):
        name=target['name']
        for label,metric in [('plus_7d','cohort_reserve'),('plus_7d','winner_depth_500'),('plus_7d','organic_active'),('feasible_exit','attacker_cash_pnl')]:
            a=alternative[(alternative.name==name)&(alternative.label==label)].set_index('seed').sort_index()
            b=original[(original.name==name)&(original.label==label)].set_index('seed').sort_index()
            mean,lo,hi=ci(a[metric]-b[metric],f'exit-continuity:{name}:{metric}')
            effects.append(dict(name=name,label=label,metric=metric,original_mean=float(b[metric].mean()),
                                continuity_mean=float(a[metric].mean()),mean_delta=mean,low=lo,high=hi))
    save_csv(out/'paired_effects.csv',effects)
    write_json(out/'manifest.json',dict(status='complete',exploratory_after_frozen_run=True,worlds=200,
               seeds=plan['seeds'],same_frozen_configurations=True,same_pretrained_attack_policy=True,
               no_policy_retraining=True,no_extra_endowments=True,
               source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               interpretation='Holding-rule sensitivity, not an additional independently confirmed design claim'))
    print(pd.DataFrame(effects).to_string(index=False))


if __name__=='__main__':main()
