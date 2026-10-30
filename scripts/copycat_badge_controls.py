"""Low-intensity badge controls, trained/evaluated independently of tax settings."""
from dataclasses import asdict,replace
from pathlib import Path
from datetime import datetime,timezone
import json,sys,time,hashlib
import argparse
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bonding_lab.copycat.config import Variant,MarketConfig
from bonding_lab.copycat.experiments import selected_strategies,evaluate,summarize,ranking,serialize


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",default="research/copycat_diversion/badge_controls")
    args=parser.parse_args()
    out=ROOT/args.out
    if out.exists() and any(out.iterdir()):raise ValueError("Badge output already exists; preserve it or choose a clean copy of the project")
    out.mkdir(parents=True)
    configs=[dict(rule="first"),dict(rule="threshold",threshold=100000.),dict(rule="held",window=30.),dict(rule="volume",window=30.)]
    variants=[Variant(**spec,form="control",rate=0,badge=badge) for spec in configs for badge in (.01,.03,.05,.1)]
    start=time.perf_counter();counter=[0];cache={};rows=[]
    c=MarketConfig(events=160)
    manifest=dict(status="running",created_utc=datetime.now(timezone.utc).isoformat(),
                  purpose="badge steering at the same nominal percentage levels as diversion, not assumed empirical effectiveness",
                  variants=len(variants),training_seeds=[11,22],evaluation_seeds=list(range(100,106)),
                  synthetic=True,sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                                          for p in sorted((ROOT/"bonding_lab/copycat").glob("*.py"))})
    path=out/"manifest.json";path.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    try:
        for i,v in enumerate(variants):
            print(f"Low-steering badge search {i+1}/{len(variants)}",flush=True)
            selected_strategies(v,c,[11,22],cache,rows,counter)
        pd.DataFrame(rows).to_csv(out/"strategy_search.csv.gz",index=False,compression="gzip")
        raw=evaluate(variants,cache,replace(c,events=240),list(range(100,106)),"badge",out,counter)
        summarize(raw).to_csv(out/"badge_summary.csv",index=False)
        ranking(raw).to_csv(out/"badge_ranking.csv",index=False)
        (out/"selected_policies.json").write_text(json.dumps(cache,default=lambda s:asdict(s),indent=2),encoding="utf-8")
        manifest["status"]="complete"
    except BaseException as exc:manifest.update(status="failed",failure=repr(exc));raise
    finally:
        manifest.update(actual_market_executions=counter[0],elapsed_seconds=time.perf_counter()-start)
        path.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in manifest.items() if k!="sources"},indent=2))


if __name__=="__main__":main()
