"""Badge sensitivity: show an elected leader only after one actually exists.

The original market sends informed/badge impressions to the original while the
leader is undefined. First-launch badges are unaffected. Other badge rules need
this control to avoid credit for information before election qualification.
"""
from concurrent.futures import ProcessPoolExecutor,as_completed
from dataclasses import asdict,replace
from pathlib import Path
import argparse,hashlib,json,sys,time
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bonding_lab.copycat import experiments as e
from bonding_lab.copycat.config import Variant,MarketConfig,Strategy
from bonding_lab.copycat.market import Market


class EligibleBadge:
    def __init__(self,v,market):self.original=v;self.market=market
    @property
    def badge(self):return self.original.badge if self.market.root_leader() is not None else 0.
    def __getattr__(self,name):return getattr(self.original,name)


def strict_run(v,c,s=Strategy(),capture=True,details=False):
    market=Market(v,c,s,capture=capture,details=details)
    market.v=EligibleBadge(v,market)
    return market.run()


def job(payload):
    v,out=payload;c=MarketConfig(events=160)
    e.run=strict_run;cache={};training=[];counter=[0]
    e.selected_strategies(v,c,[11,22],cache,training,counter)
    raw=e.evaluate([v],cache,replace(c,events=240),list(range(100,106)),"strict",out,counter)
    return raw,training,cache,counter[0]


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="research/copycat_diversion/strict_badges")
    p.add_argument("--workers",type=int,default=6)
    args=p.parse_args();out=ROOT/args.out
    if out.exists() and any(out.iterdir()):raise ValueError("Choose a fresh output directory")
    out.mkdir(parents=True)
    variants=[v for v in e.plan("full") if v.badge>0]
    specs=[dict(rule="first"),dict(rule="threshold"),dict(rule="held",window=30.),dict(rule="volume",window=30.)]
    variants.extend(Variant(**spec,form="control",rate=0,badge=rate) for spec in specs for rate in (.01,.03,.05,.1))
    start=time.perf_counter();raws=[];training=[];cache={};counter=0
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures=[]
        for i,v in enumerate(variants):
            directory=out/f"part_{i:02}";directory.mkdir()
            futures.append(pool.submit(job,(v,directory)))
        for i,future in enumerate(as_completed(futures),1):
            raw,rows,policies,n=future.result();raws.append(raw);training.extend(rows);cache.update(policies);counter+=n
            if i%10==0:print(f"Strict badges {i}/{len(variants)}",flush=True)
    raw=pd.concat(raws,ignore_index=True);raw.to_csv(out/"strict_runs.csv",index=False)
    e.summarize(raw).to_csv(out/"strict_summary.csv",index=False)
    e.ranking(raw).to_csv(out/"strict_ranking.csv",index=False)
    pd.DataFrame(training).to_csv(out/"training.csv.gz",index=False,compression="gzip")
    (out/"policies.json").write_text(json.dumps(cache,default=lambda s:asdict(s),indent=2),encoding="utf-8")
    sources=json.loads((ROOT/"research/copycat_diversion/results/manifest.json").read_text())["sources"]
    for name,digest in sources.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    record=dict(status="complete",variants=len(variants),actual_market_executions=counter,sources=sources,
                elapsed_seconds=time.perf_counter()-start,training_seeds=[11,22],seeds=list(range(100,106)),
                script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                note="No badge steering before a selected leader exists; informed traders retain their disclosed original fallback")
    (out/"manifest.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in record.items() if k!="sources"},indent=2))


if __name__=="__main__":main()
