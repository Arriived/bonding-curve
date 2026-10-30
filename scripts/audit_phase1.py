"""Recompute historical evidence using the preserved exact historical source."""
from pathlib import Path
import hashlib
import json
import sys
import time
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"results/phase2_audit"
SNAPSHOT=OUT/"legacy_source"
sys.path.insert(0,str(SNAPSHOT))
from bonding_lab.simulation import Config, compare
from bonding_lab.experiments import distribution
from bonding_lab.fast import FastBook


def main():
    start=time.perf_counter()
    checks=[]
    run_count=event_count=0
    for directory in ("pilot","long_baseline"):
        path=ROOT/"results"/directory
        manifest=json.loads((path/"manifest.json").read_text())
        assert manifest["status"]=="complete"
        for name,digest in manifest["source_sha256"].items():
            file=SNAPSHOT/name.replace("\\","/")
            assert hashlib.sha256(file.read_bytes()).hexdigest()==digest, name
        for scenario in manifest["scenarios"]:
            for basis in manifest["bases"]:
                stem=scenario+"_"+basis
                raw=pd.read_csv(path/(stem+"_runs.csv"))
                summary=pd.read_csv(path/(stem+"_summary.csv"))
                assert len(raw)==2*manifest["seeds"]
                assert raw.groupby("seed").size().eq(2).all()
                run_count+=len(raw)
                event_count+=int(raw.events.sum())
                for model in ("shared","independent","shared_minus_independent"):
                    group=raw[raw.model==model]
                    for row in summary[summary.model==model].to_dict("records"):
                        metric=row["metric"]
                        if metric=="probability_profitable_attack_run":
                            value=float((group.attacker_profit>0).mean())
                            assert np.isclose(value,row["mean"])
                            continue
                        if model=="shared_minus_independent":
                            pivot=raw.pivot(index="seed",columns="model",values=metric)
                            values=pivot.shared-pivot.independent
                        else:
                            values=group[metric]
                        recomputed=distribution(values)
                        for stat,value in recomputed.items():
                            assert np.isclose(row[stat],value,rtol=1e-8,atol=1e-8), (stem,model,metric,stat)
                if basis=="equal_capital":
                    pivot=raw.pivot(index="seed",columns="model",values="initial_required")
                    assert np.allclose(pivot.shared,pivot.independent,rtol=1e-12,atol=1e-9)
                    pivot=raw.pivot(index="seed",columns="model",values="initial_external")
                    assert np.allclose(pivot.shared,pivot.independent,rtol=1e-12,atol=1e-9)
                for seed in (42,77,141):
                    config=Config(**{**manifest["config"],"seed":seed,"scenario":scenario})
                    pair=compare(config,basis,record=False)
                    for model,result in pair.items():
                        recorded=raw[(raw.seed==seed)&(raw.model==model)].iloc[0]
                        for key,value in result.metrics.items():
                            assert np.isclose(recorded[key],value,rtol=1e-9,atol=1e-8), (stem,seed,model,key)
                checks.append(dict(batch=directory,scenario=scenario,basis=basis,summary_verified=True,
                                   replicated_seeds=[42,77,141],equal_capital_verified=basis=="equal_capital"))
    legacy=FastBook(2,2,.01,.0001,.25,.003,1000,q0=1000,reserve_capital=145-5e-10)
    legacy.assert_invariants()
    diagnostic=[]
    for basis in ("equal_supplies","equal_capital"):
        c=Config(events=1)
        results=compare(c,basis)
        for model,r in results.items():
            conf=r.config
            p=conf.p0+conf.k*conf.initial_supply*(1+conf.coupling*(conf.tokens-1))
            quantity=100
            budget=20
            d=2*budget/(p+np.sqrt(p*p+2*conf.k*budget))
            diagnostic.append(dict(basis=basis,model=model,initial_price=p,required=r.metrics["initial_required"],
                                   fixed_100_price_change=conf.k*quantity,
                                   fixed_100_relative_slippage=conf.k*quantity/(2*p),
                                   fixed_20_budget_relative_slippage=conf.k*d/(2*p)))
    report=dict(status="complete",historical_runs_verified=run_count,historical_events_verified=event_count,
                source_hashes_verified=True,checks=checks,slippage_diagnostics=diagnostic,
                legacy_underfunding_example=dict(required=145,actual=legacy.reserve,buffer=legacy.buffer,
                                                 accepted_by_legacy=True),elapsed_seconds=time.perf_counter()-start)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"audit.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    pd.DataFrame(diagnostic).to_csv(OUT/"slippage_diagnostics.csv",index=False)
    print(json.dumps({k:v for k,v in report.items() if k not in ("checks","slippage_diagnostics")},indent=2))


if __name__=="__main__":main()
