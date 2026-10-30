"""Broaden no-tax spam/evasion responses to voluntary leader portfolio splits.

This sensitivity prevents attributing a restricted control policy's missing
portfolio choice to an intrinsically unreplicable diversion exploit.
"""
from concurrent.futures import ProcessPoolExecutor,as_completed
from dataclasses import fields,replace,asdict
from pathlib import Path
import argparse,hashlib,json,sys,time
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bonding_lab.copycat.config import Variant,MarketConfig,Strategy
from bonding_lab.copycat.market import Market
from bonding_lab.copycat.attacks import candidates
from bonding_lab.copycat.experiments import serialize


class PortfolioControl(Market):
    def __init__(self,v,c,s,split):
        super().__init__(v.control(),c,s,capture=True)
        self.actor_split=split

    def buy(self,t,w,token,budget,organic=False,minimum=0.):
        original=self.router.v
        if int(w) in self.router.actor_wallets and self.actor_split:
            # The actor voluntarily spends its own budget on a second curve.
            # Outsider orders remain entirely undiverted.
            self.router.v=replace(original,form="buyer",rate=self.actor_split)
        try:return super().buy(t,w,token,budget,organic,minimum)
        finally:self.router.v=original


def job(payload):
    v,c,s,split=payload
    metrics,_,_=PortfolioControl(v,c,s,split).run()
    return metrics["attacker_profit"]


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base",default="research/copycat_diversion")
    p.add_argument("--workers",type=int,default=6)
    args=p.parse_args();base=ROOT/args.base;out=base/"portfolio_controls"
    m=json.loads((base/"results/manifest.json").read_text());assert m["status"]=="complete"
    for name,digest in m["sources"].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    if out.exists() and any(out.iterdir()):raise ValueError("Choose a fresh study bundle")
    out.mkdir(parents=True)
    variants=[]
    for row in pd.read_csv(base/"results/variants.csv").to_dict("records"):
        if row["variant"] in m["finalists"] and row["form"]=="buyer":
            variants.append(Variant(**{f.name:row[f.name] for f in fields(Variant)}))
    c=MarketConfig(**m["base_config"]);start=time.perf_counter();training=[];selected={};counter=0
    # Variant rate validation caps ordinary diversion at 10%, so search voluntary
    # splits at 0%,1%,3%,5%,10% through the same router's funded execution.
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for v in variants:
            for family in ("spam","evasion"):
                options=[(Strategy(),0.)]+[(s,split) for s in candidates(v.control(),family) if s.family!="idle"
                                           for split in sorted({0.,.01,.03,.05,.1,v.rate})]
                jobs=[pool.submit(job,(v,replace(c,seed=seed),s,split)) for s,split in options for seed in m["training_seeds"]]
                scores=[f.result() for f in jobs];counter+=len(jobs)
                means=np.array(scores).reshape(len(options),len(m["training_seeds"])).mean(axis=1)
                best=0
                for i,score in enumerate(means):
                    if score>means[best]+1e-8:best=i
                    training.append(dict(variant=v.label,family=family,strategy=serialize(options[i][0]),split=options[i][1],train_mean=float(score)))
                selected[v.label,family]=options[best]
                print(f"Portfolio control selected {v.label} {family}: split={options[best][1]:.0%}",flush=True)
        rows=[]
        for (name,family),(s,split) in selected.items():
            v=next(x for x in variants if x.label==name)
            jobs=[pool.submit(job,(v,replace(c,events=480,seed=seed),s,split)) for seed in m["confirmation_seeds"]]
            for seed,future in zip(m["confirmation_seeds"],jobs):
                rows.append(dict(variant=name,family=family,seed=seed,strategy=serialize(s),split=split,attacker_profit=future.result()))
            counter+=len(jobs)
    pd.DataFrame(training).to_csv(out/"training.csv.gz",index=False,compression="gzip")
    pd.DataFrame(rows).to_csv(out/"confirmation.csv",index=False)
    record=dict(status="complete",actual_market_executions=counter,variants=len(variants),sources=m["sources"],
                elapsed_seconds=time.perf_counter()-start,training_seeds=m["training_seeds"],seeds=m["confirmation_seeds"],
                script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                note="Independent no-tax training-selected spam/evasion responses can voluntarily buy a leader-token portfolio; no outsider diversion")
    (out/"manifest.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in record.items() if k!="sources"},indent=2))


if __name__=="__main__":main()
