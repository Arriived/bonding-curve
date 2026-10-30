"""Training/held-out experiments. Best found policies, not global optimality claims."""
from dataclasses import asdict,replace
from datetime import datetime,timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd

from ..experiments import distribution
from .config import Variant,MarketConfig,Strategy
from .attacks import FAMILIES,candidates
from .market import run


def leader_specs():
    return ([dict(rule="first")]+[dict(rule="threshold",threshold=m) for m in (100000.,1000000.)]
            +[dict(rule=r,window=w) for r in ("held","volume") for w in (5.,30.,120.)])


def plan(mode="study"):
    variants={}
    def add(v):variants[v.label]=v
    leaders=leader_specs()
    for spec in leaders:
        for form in ("creator","holders","buyer","burn"):
            for rate in (.01,.03,.05,.1):add(Variant(**spec,form=form,rate=rate))
    representatives=[leaders[i] for i in (0,1,4,7)] # first, threshold100k, held30, volume30
    for spec in representatives:
        for match in ("exact","case","fuzzy"):
            for change in (("fixed",) if spec["rule"]=="first" else ("fixed","flip","cooldown")):
                forms=("buyer",) if mode=="study" else ("creator","holders","buyer","burn")
                for form in forms:add(Variant(**spec,form=form,matching=match,changes=change))
        for form,burn,exit in (("treasury","lock","never"),("treasury","lock","first"),("burn","supply","never")):
            add(Variant(**spec,form=form,burn=burn,treasury_exit=exit))
    financial=list(variants.values())
    for v in financial:add(v.control())
    for spec in leaders:
        for badge in (.25,.5,.75):add(Variant(**spec,form="control",rate=0,badge=badge))
    if mode=="smoke":
        chosen=[Variant(),Variant(rule="threshold",form="creator"),Variant(rule="volume",changes="flip",form="holders"),
                Variant(rule="held",window=30,form="burn"),Variant(form="treasury"),Variant(form="burn",burn="supply")]
        return chosen+list({v.control().label:v.control() for v in chosen}.values())+[Variant(form="control",rate=0,badge=.5)]
    return list(variants.values())


def serialize(value):return json.dumps(asdict(value),sort_keys=True)


def selected_strategies(v,config,seeds,cache,training_rows,counter):
    key=serialize(v)
    if key in cache:return cache[key]
    base={}
    for seed in seeds:
        result,_,_=run(v,replace(config,seed=seed),Strategy(),capture=False)
        base[seed]=result["attacker_profit"];counter[0]+=1
    selected={"none":Strategy()}
    for family in FAMILIES:
        best=Strategy();best_score=float(np.mean(list(base.values())))
        for strategy in candidates(v,family):
            if strategy.family=="idle":values=list(base.values())
            else:
                values=[]
                for seed in seeds:
                    try:result,_,_=run(v,replace(config,seed=seed),strategy,capture=False)
                    except Exception as exc:
                        raise RuntimeError(f"Search failure: {v.label}, seed={seed}, strategy={serialize(strategy)}") from exc
                    values.append(result["attacker_profit"]);counter[0]+=1
            score=float(np.mean(values))
            training_rows.append(dict(variant=v.label,family=family,strategy=serialize(strategy),train_mean_profit=score,
                                      train_min_profit=min(values),train_max_profit=max(values),training_seeds=json.dumps(seeds)))
            if score>best_score+1e-8:best_score=score;best=strategy
        selected[family]=best
    cache[key]=selected
    return selected


def evaluate(variants,policies,config,seeds,stage,out,counter,details=False):
    rows=[];counterfactual_cache={}
    for vi,v in enumerate(variants):
        if vi%10==0:print(f"{stage}: variant {vi+1}/{len(variants)} {v.label}",flush=True)
        for family,strategy in policies[serialize(v)].items():
            for seed in seeds:
                c=replace(config,seed=seed)
                rich=details and seed==seeds[0] and family in ("none","race","front")
                result,history,wallets=run(v,c,strategy,capture=True,details=rich);counter[0]+=1
                control=v.control()
                ck=(serialize(control),serialize(strategy),seed,config.events)
                if v.form=="control" and not v.badge:base=result
                elif ck in counterfactual_cache:base=counterfactual_cache[ck]
                else:
                    base,_,_=run(control,c,strategy,capture=True);counter[0]+=1;counterfactual_cache[ck]=base
                result.update(variant=v.label,stage=stage,seed=seed,family=family,strategy=serialize(strategy),
                              rule=v.rule,form=v.form,rate=v.rate,matching=v.matching,changes=v.changes,
                              window=v.window,threshold=v.threshold,badge=v.badge,burn=v.burn,treasury_exit=v.treasury_exit,
                              attacker_increment_vs_same_policy_control=result["attacker_profit"]-base["attacker_profit"],
                              vamp_increment_vs_control=result["vamper_profit"]-base["vamper_profit"],
                              original_consolidation_increment=result["original_liquidity_share_time_mean"]-base["original_liquidity_share_time_mean"],
                              leader_consolidation_increment=result["leader_liquidity_share_time_mean"]-base["leader_liquidity_share_time_mean"],
                              original_absolute_liquidity_increment=result["original_accessible_liquidity_time_mean"]-base["original_accessible_liquidity_time_mean"],
                              total_absolute_liquidity_increment=result["total_accessible_liquidity_time_mean"]-base["total_accessible_liquidity_time_mean"],
                              retail_increment_vs_control=result["retail_profit"]-base["retail_profit"],
                              confused_increment_vs_control=(result["confused_mean_profit"]-base["confused_mean_profit"])
                                  if result["confused_mean_profit"] is not None and base["confused_mean_profit"] is not None else None)
                rows.append(result)
                if rich:
                    stem=f"{v.label}_{family}"
                    pd.DataFrame(history).to_csv(out/(stem+"_history.csv"),index=False)
                    pd.DataFrame(wallets).to_csv(out/(stem+"_wallets.csv"),index=False)
        # Incremental checkpoints make partial completion auditable.
        if (vi+1)%10==0:pd.DataFrame(rows).to_csv(out/(stage+"_checkpoint.csv"),index=False)
    raw=pd.DataFrame(rows);raw.to_csv(out/(stage+"_runs.csv"),index=False)
    return raw


def summarize(raw):
    ignored={"seed","window","threshold","rate","badge"}
    metrics=[k for k in raw.select_dtypes("number").columns if k not in ignored]
    rows=[]
    for (variant,family),group in raw.groupby(["variant","family"]):
        for metric in metrics:
            stats=distribution(group[metric])
            # Small screening samples need wider intervals than a z=1.96 rule.
            # Exact critical values for the executed n=6 and n=30, with explicit
            # approximations for other research batch sizes.
            n=stats.get("n",0)
            if n>1:
                df=n-1
                z=1.95996398454
                approx=z+(z**3+z)/(4*df)+(5*z**5+16*z**3+3*z)/(96*df**2)+(3*z**7+19*z**5+17*z**3-15*z)/(384*df**3)
                critical={1:12.7062,2:4.30265,3:3.18245,4:2.77645,5:2.57058,6:2.44691,7:2.36462,8:2.306,9:2.26216,
                          29:2.04523}.get(df,approx)
                half=critical*stats["std"]/np.sqrt(n)
                stats.update(mean_ci95_low=stats["mean"]-half,mean_ci95_high=stats["mean"]+half)
            rows.append(dict(variant=variant,family=family,metric=metric,**stats))
        x=group.attacker_profit.to_numpy()>1e-6;n=len(x);p=float(x.mean());z=1.96
        center=(p+z*z/(2*n))/(1+z*z/n);half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
        rows.append(dict(variant=variant,family=family,metric="profitable_attack_frequency",n=n,mean=p,
                         mean_ci95_low=center-half,mean_ci95_high=center+half))
    return pd.DataFrame(rows)


def ranking(raw):
    rows=[]
    for variant,group in raw.groupby("variant"):
        baseline=group[group.family=="none"]
        attack=group[group.family!="none"]
        means=attack.groupby("family").attacker_increment_vs_same_policy_control.mean()
        worst=means.idxmax()
        chosen=attack[attack.family==worst]
        meta=baseline.iloc[0]
        rows.append(dict(variant=variant,rule=meta.rule,form=meta.form,rate=meta.rate,matching=meta.matching,
                         changes=meta.changes,window=meta.window,threshold=meta.threshold,badge=meta.badge,burn=meta.burn,
                         original_consolidation_gain=baseline.original_consolidation_increment.mean(),
                         named_leader_consolidation_gain=baseline.leader_consolidation_increment.mean(),
                         original_absolute_liquidity_gain=baseline.original_absolute_liquidity_increment.mean(),
                         total_absolute_liquidity_gain=baseline.total_absolute_liquidity_increment.mean(),
                         original_leader_fraction=baseline.original_leader_time_fraction.mean(),
                         leader_defined_fraction=baseline.leader_defined_time_fraction.mean(),
                         retail_pnl_change=baseline.retail_increment_vs_control.mean(),
                         confused_buyer_pnl_change=baseline.confused_increment_vs_control.mean(),
                         vamper_pnl_change=baseline.vamp_increment_vs_control.mean(),
                         worst_incremental_attack_family=worst,
                         worst_mean_incremental_attack_gain=chosen.attacker_increment_vs_same_policy_control.mean(),
                         worst_absolute_attack_profit=float(attack.attacker_profit.max()),
                         worst_original_identity_fraction=float(attack.original_leader_time_fraction.min()),
                         minimum_attacked_original_share=float(attack.original_liquidity_share_time_mean.min())))
    result=pd.DataFrame(rows)
    return result.sort_values(["original_consolidation_gain","worst_mean_incremental_attack_gain"],ascending=[False,True])


def run_study(output,mode="study",train_events=160,screen_events=240,screen_seeds=6,confirm_seeds=30,finalists=12,config_overrides=None):
    out=Path(output)
    if out.exists() and any(out.iterdir()):raise ValueError("Choose a new or empty output directory")
    out.mkdir(parents=True,exist_ok=True);examples=out/"examples";examples.mkdir()
    variants=plan(mode);config=MarketConfig(events=train_events,**(config_overrides or {}))
    seed_train=[11,22];seed_screen=list(range(100,100+screen_seeds));seed_confirm=list(range(1000,1000+confirm_seeds))
    if mode=="smoke":seed_train=[11];finalists=min(finalists,3)
    root=Path(__file__).parents[2]
    sources=sorted(Path(__file__).parent.glob("*.py"))+[root/"bonding_lab"/p for p in ("fast.py","engine.py","experiments.py")]
    manifest=dict(status="running",created_utc=datetime.now(timezone.utc).isoformat(),mode=mode,base_config=asdict(config),
                  variants=len(variants),training_seeds=seed_train,screen_seeds=seed_screen,confirmation_seeds=seed_confirm,
                  training_events=train_events,screen_events=screen_events,confirmation_events=480,
                  synthetic=True,search_claim="best found in disclosed finite policy classes; not global optimality",
                  sources={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                  packages={p:importlib.metadata.version(p) for p in ("numpy","pandas","pytest","hypothesis")},
                  completed=[])
    path=out/"manifest.json";path.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    pd.DataFrame([dict(variant=v.label,**asdict(v)) for v in variants]).to_csv(out/"variants.csv",index=False)
    start=time.perf_counter();counter=[0];cache={};training_rows=[]
    try:
        for i,v in enumerate(variants):
            if i%10==0:print(f"Search: variant {i+1}/{len(variants)}",flush=True)
            selected_strategies(v,config,seed_train,cache,training_rows,counter)
            if (i+1)%10==0:
                pd.DataFrame(training_rows).to_csv(out/"search_checkpoint.csv.gz",index=False,compression="gzip")
                path.write_text(json.dumps({**manifest,"actual_market_executions":counter[0]},indent=2),encoding="utf-8")
        pd.DataFrame(training_rows).to_csv(out/"strategy_search.csv.gz",index=False,compression="gzip")
        (out/"selected_policies.json").write_text(json.dumps(cache,default=lambda s:asdict(s),indent=2),encoding="utf-8")
        manifest["training_market_executions"]=counter[0]
        manifest["completed"].append("strategy_search")
        screen=evaluate(variants,cache,replace(config,events=screen_events),seed_screen,"screen",out,counter)
        summarize(screen).to_csv(out/"screen_summary.csv",index=False)
        ranks=ranking(screen);ranks.to_csv(out/"screen_ranking.csv",index=False)
        manifest["screen_market_executions"]=counter[0]-manifest["training_market_executions"]
        manifest["completed"].append("screen")
        # Hold-out confirmation includes leading financial candidates, all forms,
        # representative alternative elections, and a display-only badge.
        ids=[]
        def pick(frame,count=1):
            for item in frame.variant.head(count):
                if item not in ids:ids.append(item)
        pick(ranks[ranks.form!="control"],3)
        for form in ("creator","holders","buyer","burn","treasury"):pick(ranks[ranks.form==form])
        for rule in ("threshold","held","volume"):pick(ranks[(ranks.rule==rule)&(ranks.form=="buyer")])
        pick(ranks[(ranks.form=="control")&(ranks.badge>0)])
        for target in (Variant(form="buyer").label,Variant(form="burn",burn="supply").label):
            if target in set(ranks.variant) and target not in ids:ids.append(target)
        ids=ids[:finalists]
        chosen=[v for name in ids for v in variants if v.label==name]
        confirmation=evaluate(chosen,cache,replace(config,events=480),seed_confirm,"confirmation",out,counter,details=False)
        summarize(confirmation).to_csv(out/"confirmation_summary.csv",index=False)
        ranking(confirmation).to_csv(out/"confirmation_ranking.csv",index=False)
        manifest["confirmation_market_executions"]=counter[0]-manifest["training_market_executions"]-manifest["screen_market_executions"]
        before_examples=counter[0]
        for v in chosen:
            for family in ("none","race","front"):
                result,history,wallets=run(v,replace(config,events=480,seed=seed_confirm[0]),cache[serialize(v)][family],details=True)
                counter[0]+=1;stem=f"{v.label}_{family}"
                pd.DataFrame(history).to_csv(examples/(stem+"_history.csv"),index=False)
                pd.DataFrame(wallets).to_csv(examples/(stem+"_wallets.csv"),index=False)
        manifest["example_market_executions"]=counter[0]-before_examples
        manifest["actual_demand_events"]=(manifest["training_market_executions"]*train_events+
                                           manifest["screen_market_executions"]*screen_events+
                                           (manifest["confirmation_market_executions"]+manifest["example_market_executions"])*480)
        manifest["completed"].append("confirmation");manifest["finalists"]=ids;manifest["status"]="complete"
    except BaseException as exc:manifest.update(status="failed",failure=repr(exc));raise
    finally:
        manifest.update(actual_market_executions=counter[0],elapsed_seconds=time.perf_counter()-start)
        path.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest
