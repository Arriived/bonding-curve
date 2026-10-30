"""Deterministic process-parallel orchestration; the economic engine is unchanged.

Can resume a completed prefix of the serial training checkpoint. Identical market
calls in an evaluation stage are computed once, then copied into the original
evaluate() function. A cache hit is never counted as an independent observation.
"""
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pandas as pd
from bonding_lab.copycat import experiments as e
from bonding_lab.copycat.config import Variant, MarketConfig, Strategy
from bonding_lab.copycat.attacks import FAMILIES, candidates
from bonding_lab.copycat.market import run as market_run


def train_job(payload):
    v,c,seeds=payload
    cache={};rows=[];counter=[0]
    selected=e.selected_strategies(v,c,seeds,cache,rows,counter)
    return e.serialize(v),selected,rows,counter[0]


def call_key(v,c,s):return (e.serialize(v),e.serialize(c),e.serialize(s))


def market_job(payload):
    v,c,s=payload
    result,_,_=market_run(v,c,s,capture=True)
    return call_key(v,c,s),result


def parallel_evaluate(pool,variants,policies,config,seeds,stage,out):
    jobs={}
    for v in variants:
        for s in policies[e.serialize(v)].values():
            for seed in seeds:
                c=replace(config,seed=seed)
                for actual in (v,v.control()):
                    jobs[call_key(actual,c,s)]=(actual,c,s)
    cached={};done=0
    futures=[pool.submit(market_job,payload) for payload in jobs.values()]
    for future in as_completed(futures):
        key,result=future.result();cached[key]=result;done+=1
        if done%200==0:print(f"{stage}: computed {done}/{len(jobs)} unique markets",flush=True)
    original=e.run
    def lookup(v,c,s,capture=True,details=False):
        assert capture and not details
        return dict(cached[call_key(v,c,s)]),[],[]
    counter=[0]
    try:
        e.run=lookup
        raw=e.evaluate(variants,policies,config,seeds,stage,out,counter)
    finally:e.run=original
    return raw,len(jobs),counter[0]


def verify(workers):
    import tempfile
    c=MarketConfig(events=30)
    variants=[Variant(form="buyer"),Variant(rule="volume",form="holders",changes="flip",window=5)]
    policies={e.serialize(v):{"none":Strategy(),"spam":Strategy(family="spam",copies=2),
                             "front":Strategy(family="front")} for v in variants}
    with tempfile.TemporaryDirectory(dir=ROOT/".tmp") as name:
        out=Path(name)
        serial=e.evaluate(variants,policies,c,[101,102],"parity",out,[0])
        with ProcessPoolExecutor(max_workers=workers) as pool:
            parallel,physical,logical=parallel_evaluate(pool,variants,policies,c,[101,102],"parity",out)
        pd.testing.assert_frame_equal(serial,parallel,check_exact=True)
    record=dict(status="complete",rows=len(serial),comparison="bit-identical seed-level records",physical_calls=physical,logical_calls=logical,
                script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (ROOT/"research/copycat_diversion/development/parallel_parity.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
    print(json.dumps(record,indent=2))


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="research/copycat_diversion/results")
    p.add_argument("--workers",type=int,default=6)
    p.add_argument("--resume",action="store_true")
    p.add_argument("--verify",action="store_true")
    args=p.parse_args()
    if args.verify:return verify(args.workers)
    out=ROOT/args.out;out.mkdir(parents=True,exist_ok=True)
    examples=out/"examples";examples.mkdir(exist_ok=True)
    variants=e.plan("full");config=MarketConfig(events=160)
    train=[11,22];screen_seeds=list(range(100,106));confirm_seeds=list(range(1000,1030))
    path=out/"manifest.json";start=time.perf_counter()
    sources=sorted((ROOT/"bonding_lab/copycat").glob("*.py"))+[ROOT/"bonding_lab"/f for f in ("fast.py","engine.py","experiments.py")]
    hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    cache={};rows=[];count=0;resumed=0;elapsed_prefix=0
    if args.resume:
        old=json.loads(path.read_text())
        assert old["sources"]==hashes and old["base_config"]==asdict(config)
        assert not old["completed"] and old["status"] in ("running","failed")
        saved=pd.read_csv(out/"search_checkpoint.csv.gz")
        names=list(saved.variant.drop_duplicates());resumed=len(names)
        assert names==[v.label for v in variants[:resumed]],"Checkpoint is not a complete training prefix"
        for v in variants[:resumed]:
            g=saved[saved.variant==v.label];selected={"none":Strategy()}
            for family in FAMILIES:
                fg=g[g.family==family]
                expected=[e.serialize(s) for s in candidates(v,family)]
                assert list(fg.strategy)==expected,"Incomplete or changed candidate order"
                baseline=fg[fg.strategy.apply(lambda s:json.loads(s)["family"]=="idle")].train_mean_profit.iloc[0]
                best=Strategy();score=baseline
                for row in fg.itertuples():
                    if row.train_mean_profit>score+1e-8:score=row.train_mean_profit;best=Strategy(**json.loads(row.strategy))
                selected[family]=best
            cache[e.serialize(v)]=selected
        rows=saved.to_dict("records")
        count=len(train)*(resumed+sum(json.loads(row["strategy"])["family"]!="idle" for row in rows))
        assert count==old["actual_market_executions"],"Checkpoint execution count disagrees"
        prefix=ROOT/"research/copycat_diversion/development/serial_training_prefix"
        prefix.mkdir(exist_ok=False)
        for name in ("manifest.json","search_checkpoint.csv.gz","variants.csv"):shutil.copy2(out/name,prefix/name)
        stamp=datetime.fromisoformat(old["created_utc"])
        elapsed_prefix=(datetime.now(timezone.utc)-stamp).total_seconds()
    elif any(p.name!="examples" for p in out.iterdir()):raise ValueError("Choose an empty output directory or --resume")
    manifest=dict(status="running",created_utc=datetime.now(timezone.utc).isoformat(),mode="full",base_config=asdict(config),
                  variants=len(variants),training_seeds=train,screen_seeds=screen_seeds,confirmation_seeds=confirm_seeds,
                  training_events=160,screen_events=240,confirmation_events=480,synthetic=True,
                  search_claim="best found in disclosed finite policy classes; not global optimality",sources=hashes,
                  packages={p:importlib.metadata.version(p) for p in ("numpy","pandas","pytest","hypothesis")},completed=[],
                  execution_mode="deterministic process parallel with exact-call evaluation deduplication",workers=args.workers,
                  orchestrator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),resumed_training_variants=resumed,
                  resumed_training_calls=count,serial_prefix_wall_seconds=elapsed_prefix,actual_market_executions=count)
    def save():path.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    save();pd.DataFrame([dict(variant=v.label,**asdict(v)) for v in variants]).to_csv(out/"variants.csv",index=False)
    try:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures={pool.submit(train_job,(v,config,train)):v for v in variants[resumed:]}
            completed={}
            for future in as_completed(futures):
                key,selected,newrows,n=future.result();completed[key]=(selected,newrows,n)
                if len(completed)%10==0:print(f"Parallel search {resumed+len(completed)}/{len(variants)} variants",flush=True)
            # Keep exports in the identical serial variant and candidate order.
            for v in variants[resumed:]:
                selected,newrows,n=completed[e.serialize(v)];cache[e.serialize(v)]=selected;rows.extend(newrows);count+=n
            pd.DataFrame(rows).to_csv(out/"strategy_search.csv.gz",index=False,compression="gzip")
            (out/"selected_policies.json").write_text(json.dumps(cache,default=lambda s:asdict(s),indent=2),encoding="utf-8")
            manifest.update(training_market_executions=count,actual_market_executions=count);manifest["completed"].append("strategy_search");save()
            raw,n,logical=parallel_evaluate(pool,variants,cache,replace(config,events=240),screen_seeds,"screen",out)
            count+=n;manifest.update(screen_market_executions=n,screen_logical_market_calls=logical,actual_market_executions=count)
            e.summarize(raw).to_csv(out/"screen_summary.csv",index=False)
            ranks=e.ranking(raw);ranks.to_csv(out/"screen_ranking.csv",index=False)
            manifest["completed"].append("screen");save()
            ids=[]
            def pick(frame,n=1):
                for item in frame.variant.head(n):
                    if item not in ids:ids.append(item)
            pick(ranks[ranks.form!="control"],3)
            for form in ("creator","holders","buyer","burn","treasury"):pick(ranks[ranks.form==form])
            for rule in ("threshold","held","volume"):pick(ranks[(ranks.rule==rule)&(ranks.form=="buyer")])
            pick(ranks[(ranks.form=="control")&(ranks.badge>0)])
            for target in (Variant().label,Variant(form="burn",burn="supply").label):
                if target in set(ranks.variant) and target not in ids:ids.append(target)
            ids=ids[:12];chosen=[v for name in ids for v in variants if v.label==name]
            raw,n,logical=parallel_evaluate(pool,chosen,cache,replace(config,events=480),confirm_seeds,"confirmation",out)
            count+=n;manifest.update(confirmation_market_executions=n,confirmation_logical_market_calls=logical,actual_market_executions=count)
            e.summarize(raw).to_csv(out/"confirmation_summary.csv",index=False)
            e.ranking(raw).to_csv(out/"confirmation_ranking.csv",index=False)
        for v in chosen:
            for family in ("none","race","front"):
                _,history,wallets=market_run(v,replace(config,events=480,seed=confirm_seeds[0]),cache[e.serialize(v)][family],details=True)
                count+=1;stem=f"{v.label}_{family}"
                pd.DataFrame(history).to_csv(examples/(stem+"_history.csv"),index=False)
                pd.DataFrame(wallets).to_csv(examples/(stem+"_wallets.csv"),index=False)
        manifest.update(example_market_executions=len(chosen)*3,
                        actual_demand_events=manifest["training_market_executions"]*160+manifest["screen_market_executions"]*240+
                        (manifest["confirmation_market_executions"]+len(chosen)*3)*480,
                        finalists=ids,status="complete")
        manifest["completed"].append("confirmation")
    except BaseException as exc:manifest.update(status="failed",failure=repr(exc));raise
    finally:
        manifest.update(actual_market_executions=count,elapsed_seconds=time.perf_counter()-start+elapsed_prefix);save()
    print(json.dumps({k:v for k,v in manifest.items() if k not in ("sources","packages","base_config")},indent=2))


if __name__=="__main__":main()
