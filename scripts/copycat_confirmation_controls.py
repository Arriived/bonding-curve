"""Evaluate independently optimized zero-tax opponents on confirmation seeds."""
from pathlib import Path
from dataclasses import fields,asdict
import hashlib,json,sys,time
import argparse
from concurrent.futures import ProcessPoolExecutor
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bonding_lab.copycat.config import Variant,Strategy,MarketConfig
from bonding_lab.copycat.experiments import serialize,evaluate,summarize


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--study",default="research/copycat_diversion/results")
    parser.add_argument("--out",default="research/copycat_diversion/confirmation_controls")
    parser.add_argument("--workers",type=int,default=6)
    parser.add_argument("--all-controls",action="store_true",help="Evaluate every trained zero-tax control; can start after search completes")
    args=parser.parse_args()
    base=ROOT/args.study
    manifest=json.loads((base/"manifest.json").read_text())
    if manifest["status"]!="complete" and not (args.all_controls and "strategy_search" in manifest["completed"]):
        raise RuntimeError("Required training/study stage is incomplete")
    for name,digest in manifest["sources"].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    policy=json.loads((base/"selected_policies.json").read_text())
    cache={key:{family:Strategy(**s) for family,s in value.items()} for key,value in policy.items()}
    variants=pd.read_csv(base/"variants.csv")
    wanted=variants if args.all_controls else variants[variants.variant.isin(manifest["finalists"])]
    controls={}
    for row in wanted.to_dict("records"):
        v=Variant(**{f.name:row[f.name] for f in fields(Variant)})
        controls[v.control().label]=v.control()
    out=ROOT/args.out
    if out.exists() and any(out.iterdir()):raise ValueError("Confirmation-control output already exists")
    out.mkdir(parents=True)
    c=MarketConfig(**{**manifest["base_config"],"events":manifest["confirmation_events"]})
    start=time.perf_counter();counter=[0]
    from copycat_parallel import parallel_evaluate
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        raw,physical,logical=parallel_evaluate(pool,list(controls.values()),cache,c,manifest["confirmation_seeds"],"counterfactual",out)
    counter[0]=physical
    summarize(raw).to_csv(out/"summary.csv",index=False)
    record=dict(status="complete",control_variants=len(controls),seeds=manifest["confirmation_seeds"],
                actual_market_executions=counter[0],elapsed_seconds=time.perf_counter()-start,
                logical_market_calls=logical,execution_mode="deterministic parallel with exact-call deduplication",
                sources=manifest["sources"],script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                purpose="independent training-selected best response in each family under matched zero-diversion rules")
    (out/"manifest.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
    print(json.dumps(record,indent=2))


if __name__=="__main__":main()
