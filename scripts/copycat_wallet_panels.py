"""Matched individual cash outcomes for no-attack confirmed settings.

Buyer-level records expose tails and changing badge-cohort composition. Mean
intervals are computed over seed cohorts; wallets are not independent markets.
"""
from concurrent.futures import ProcessPoolExecutor,as_completed
from dataclasses import fields,replace
from pathlib import Path
import argparse,hashlib,json,sys,time
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bonding_lab.copycat.config import Variant,MarketConfig,Strategy
from bonding_lab.copycat.market import run
from bonding_lab.copycat.experiments import serialize
from bonding_lab.experiments import distribution


def job(payload):
    v,c=payload
    metrics,_,wallets=run(v,c,Strategy(),details=True)
    return (serialize(v),c.seed),metrics,wallets


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--study",default="research/copycat_diversion/results")
    p.add_argument("--out",default="research/copycat_diversion/wallet_panels")
    p.add_argument("--workers",type=int,default=6)
    args=p.parse_args();base=ROOT/args.study;out=ROOT/args.out
    m=json.loads((base/"manifest.json").read_text());assert m["status"]=="complete"
    for name,digest in m["sources"].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    if out.exists() and any(out.iterdir()):raise ValueError("Choose a new output directory")
    out.mkdir(parents=True)
    config=MarketConfig(**{**m["base_config"],"events":m["confirmation_events"]})
    variants=[]
    for row in pd.read_csv(base/"variants.csv").to_dict("records"):
        if row["variant"] in m["finalists"]:variants.append(Variant(**{f.name:row[f.name] for f in fields(Variant)}))
    jobs={}
    for v in variants:
        for seed in m["confirmation_seeds"]:
            c=replace(config,seed=seed)
            for a in (v,v.control()):jobs[serialize(a),seed]=(a,c)
    start=time.perf_counter();cache={}
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(job,payload) for payload in jobs.values()]
        for i,f in enumerate(as_completed(futures),1):
            key,metrics,wallets=f.result();cache[key]=(metrics,wallets)
            if i%100==0:print(f"Wallet panels {i}/{len(jobs)} markets",flush=True)
    expected=pd.read_csv(base/"confirmation_runs.csv").query("family == 'none'").set_index(["variant","seed"])
    panels=[];stats=[]
    for v in variants:
        for seed in m["confirmation_seeds"]:
            metrics,wallets=cache[serialize(v),seed]
            assert np.isclose(metrics["retail_profit"],expected.loc[(v.label,seed),"retail_profit"],rtol=1e-10,atol=1e-7)
            _,control=cache[serialize(v.control()),seed]
            a=pd.DataFrame(wallets).set_index("wallet");b=pd.DataFrame(control).set_index("wallet")
            assert np.isclose(a.realized_cash_pnl.sum(),metrics["retail_profit"],rtol=1e-10,atol=1e-7)
            a["variant"]=v.label;a["seed"]=seed
            a["baseline_confused"]=b.confused;a["baseline_target_role"]=b.target_role
            a["control_cash_pnl"]=b.realized_cash_pnl
            a["cash_pnl_change"]=a.realized_cash_pnl-b.realized_cash_pnl
            a["timing"]=np.where(a.minute<config.horizon/3,"early",np.where(a.minute>=2*config.horizon/3,"late","middle"))
            panels.append(a.reset_index())
            masks={"all":np.ones(len(a),dtype=bool),"fixed_confused":a.baseline_confused,"remaining_confused":a.confused}
            for timing in ("early","middle","late"):
                for role in ("leader","copy","original_unselected"):
                    masks[timing+"_"+role]=(a.timing==timing)&(a.target_role==role)
            for cohort,mask in masks.items():
                g=a[mask]
                if g.empty:continue
                row=dict(variant=v.label,family=cohort,seed=seed,buyers=len(g))
                for field in ("realized_cash_pnl","cash_pnl_change"):
                    x=g[field]
                    row.update({field+"_"+k:val for k,val in dict(mean=x.mean(),median=x.median(),q05=x.quantile(.05),q95=x.quantile(.95),min=x.min(),max=x.max()).items()})
                stats.append(row)
    panel=pd.concat(panels,ignore_index=True);panel.to_csv(out/"wallets.csv.gz",index=False,compression="gzip")
    cohorts=pd.DataFrame(stats);cohorts.to_csv(out/"seed_cohorts.csv",index=False)
    summary=[]
    for (name,cohort),g in cohorts.groupby(["variant","family"]):
        for metric in g.select_dtypes("number").columns.difference(["seed"]):
            s=distribution(g[metric]);n=s["n"]
            if n>1:
                df=n-1;z=1.95996398454
                approx=z+(z**3+z)/(4*df)+(5*z**5+16*z**3+3*z)/(96*df**2)+(3*z**7+19*z**5+17*z**3-15*z)/(384*df**3)
                critical={1:12.7062,2:4.30265,3:3.18245,4:2.77645,5:2.57058,29:2.04523}.get(df,approx)
                half=critical*s["std"]/np.sqrt(n);s.update(mean_ci95_low=s["mean"]-half,mean_ci95_high=s["mean"]+half)
            summary.append(dict(variant=name,cohort=cohort,metric=metric,**s))
    pd.DataFrame(summary).to_csv(out/"cohort_summary.csv",index=False)
    record=dict(status="complete",actual_market_executions=len(jobs),wallet_records=len(panel),variants=len(variants),
                seeds=m["confirmation_seeds"],elapsed_seconds=time.perf_counter()-start,
                note="No-attack individual outcomes; confidence intervals use seed cohorts, never pooled wallets",
                sources=m["sources"],script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                minimum_individual_pnl=float(panel.realized_cash_pnl.min()),minimum_matched_change=float(panel.cash_pnl_change.min()))
    (out/"manifest.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
    print(json.dumps(record,indent=2))


if __name__=="__main__":main()
