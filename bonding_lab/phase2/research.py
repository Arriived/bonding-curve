"""Controlled liquidity/risk experiments and matched external-arbitrage research."""
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
from .world import World,Study,ARCHITECTURES,RETAIL,ARB,SPONSOR
from .surfaces import FloatSurface,Spec,F,ExactSurface,Asset,bounded_order_profit
from .amm import WeightedPool,HubPool,check_admission


def liquidity_at_start(config):
    rows=[]
    for architecture in ARCHITECTURES+("hub",):
        w=World(architecture,config);m=w.mechanism;P=config.reference_price
        for side in ("buy","sell"):
            limit=m.max_buy(0) if side=="buy" else m.max_sell(0)
            lo,hi=0.,limit
            def deviation(d):
                if d<=0:return 0.
                value=m.quote(0,d,side)/(d*P)
                return value-1 if side=="buy" else 1-value
            for _ in range(55):
                mid=(lo+hi)/2
                if deviation(mid)<=.01:lo=mid
                else:hi=mid
            d=min(100/P,limit*.99)
            rows.append(dict(architecture=architecture,side=side,tokens=config.tokens,
                             initial_price=m.price(0),sponsor_capital=config.capital,
                             total_initial_cash=w.total_initial_cash,initial_reserve=m.cash,
                             normalized_quantity=d,reference_notional=d*P,
                             executed_cash=m.quote(0,d,side),cost_deviation=deviation(d),
                             executable_reference_notional_1pct=lo*P,fee=config.fee,**w.calibration))
    return pd.DataFrame(rows)


def joint_liquidity(config):
    """Sequential quotes: demonstrate that individually quoted depth is not additive."""
    rows=[]
    for architecture in ARCHITECTURES+("hub",):
        for ordering in ("forward","reverse"):
            w=World(architecture,replace(config,fee=0));m=w.mechanism
            d=min(.01,100/config.reference_price,config.retail_capital/(10*config.tokens*config.reference_price),
                  config.capital/(4*config.tokens*config.reference_price))
            initial_quotes=sum(m.quote(i,d,"buy") for i in range(config.tokens))
            order=list(range(config.tokens))
            if ordering=="reverse":order.reverse()
            actual=0.
            for i in order:actual+=w.internal(RETAIL,i,d,"buy")
            w.assert_invariants()
            rows.append(dict(architecture=architecture,tokens=config.tokens,ordering=ordering,
                             summed_initial_buy_quotes=initial_quotes,actual_joint_buy_cost=actual,
                             extra_joint_cost=actual-initial_quotes))
    return pd.DataFrame(rows)


def shock_tape(c):
    rng=np.random.default_rng(c.seed)
    shocks=rng.normal(size=(c.events,c.tokens))
    z=c.reference_price*np.exp(np.cumsum(c.volatility*shocks-c.volatility**2/2,axis=0))
    onset=c.events//3
    if c.scenario=="divergent":
        z[onset:,0]*=2
        z[onset:,1]*=.5
    elif c.scenario in ("crash","toxic_admission"):
        z[onset:,0]*=.01 if c.scenario=="crash" else .0001
    elif c.scenario=="joint_run":z[c.events//2:]*=.5
    return z,rng.integers(c.tokens,size=c.events),rng.random(c.events),c.retail_size*np.minimum(10,rng.lognormal(-.32,.8,c.events))


def run_world(architecture,c,tape=None,record=False):
    w=World(architecture,c)
    z,tokens,draw,budgets=shock_tape(c) if tape is None else tape
    fills=skips=0;volume=slip=mispricing=0.
    history=[]
    for t in range(c.events):
        w.refresh(z[t])
        if c.scenario=="toxic_admission" and t==c.events//3:w.toxic_creator_sale()
        i=int(tokens[t]);side="buy" if draw[t]<c.buy_pressure else "sell"
        if c.scenario=="joint_run" and t>c.events//2:
            side="sell";i=int(np.argmax(w.h[RETAIL]))
        if side=="buy":
            d=w.buy_quantity(i,min(budgets[t],w.cash[RETAIL]*.95))
        else:
            d=min(w.h[RETAIL,i],budgets[t]/w.reference[i],w.mechanism.max_sell(i))
        if d>1e-10:
            paid=w.internal(RETAIL,i,d,side)
            volume+=paid
            slip+=(paid/(d*w.reference[i])-1)*(1 if side=="buy" else -1)
            fills+=1
        else:skips+=1
        w.arbitrage()
        mispricing+=float(np.mean(np.abs(w.mechanism.prices()/w.reference-1)))
        if t%25==0 or t==c.events-1:w.assert_invariants()
        if record and (t%max(1,c.events//100)==0 or t==c.events-1):
            history.append(dict(event=t+1,cash_reserve=w.mechanism.cash,arb_profit=w.arb_profit,
                                retail_pnl=w.cash[RETAIL]+float(np.dot(w.h[RETAIL],w.reference))-c.retail_capital,
                                lp_nav=w.mechanism.nav(w.reference) if isinstance(w.mechanism,WeightedPool) else None,
                                mean_mispricing=float(np.mean(np.abs(w.mechanism.prices()/w.reference-1)))))
    metrics=w.metrics()
    metrics.update(retail_fills=fills,retail_skips=skips,retail_cash_volume=volume,
                   mean_execution_cost_vs_reference=slip/max(1,fills),
                   mean_path_mispricing=mispricing/c.events)
    return metrics,pd.DataFrame(history)


def controlled_toxic(config):
    rows=[]
    for architecture in ARCHITECTURES+("hub",):
        w=World(architecture,config)
        prices=w.reference.copy();prices[0]*=.0001
        before_unrelated=w.mechanism.price(1)
        w.refresh(prices)
        before_nav=w.mechanism.nav(prices) if isinstance(w.mechanism,WeightedPool) else None
        profit=w.toxic_creator_sale()
        metrics=w.metrics()
        metrics.update(attack_profit=profit,unrelated_price_change=w.mechanism.price(1)/before_unrelated-1,
                       lp_nav_after_reference_collapse_before_attack=before_nav)
        rows.append(metrics)
    return pd.DataFrame(rows)


def order_attacks(config):
    rows=[]
    for architecture in ARCHITECTURES:
        for fraction in (.001,.005,.01):
            for fee in (0.,.003):
                w=World(architecture,replace(config,fee=fee))
                m=w.mechanism;d=fraction;b=fraction
                pre=m.quote(0,d,"buy")
                start=w.cash[ARB]
                w.internal(ARB,1,b,"buy")
                victim=w.internal(RETAIL,0,d,"buy")
                w.internal(ARB,1,b,"sell")
                w.assert_invariants()
                expected=None
                if isinstance(m,FloatSurface):
                    # Initial global X, before either mint, is final X minus victim.
                    expected=float(bounded_order_profit(m.spec,m.X-d,d,b))
                rows.append(dict(architecture=architecture,fee=fee,victim_fraction=d,attacker_fraction=b,
                                 attacker_net_profit=w.cash[ARB]-start,victim_extra_payment=victim-pre,
                                 predicted_gross=expected,gas=0.))
    return pd.DataFrame(rows)


def bounded_exact_checks():
    rows=[]
    for count in (2,10,100,1000):
        spec=Spec("bounded",2000,40000,gamma=2000,tau=1)
        X=F(count)/10
        premium=spec.global_slope(X,True)
        profit=bounded_order_profit(spec,X,F(".01"),F(".01"),True)
        rows.append(dict(tokens=count,normalized_total=float(X),global_premium=float(premium),premium_cap=2000,
                         bounded_required=float(spec.reserve([F(".1")]*count,True)),
                         quadratic_required=float(Spec("quadratic",2000,40000).reserve([F(".1")]*count,True)),
                         gross_order_profit=float(profit),cross_curvature=float(spec.global_curvature(X,True))))
    c=ExactSurface(Spec("bounded",2000,40000),fee=".003")
    for i in range(10):c.admit(Asset(str(i),10**9))
    c.wallet("funded",100000)
    for i in range(10):c.trade("funded",i,".1","buy")
    before=c.reserve
    gross=F(0)
    for i in reversed(range(10)):
        g,_=c.quote(i,".1","sell");gross+=g
        c.trade("funded",i,".1","sell")
    assert gross==before and c.reserve==0
    c.assert_invariants()
    return pd.DataFrame(rows)


def arbitrage_controls(config):
    """No retail flow: isolate external mispricing extraction with finite inventory."""
    rows=[]
    for shock in (.5,2.):
        for architecture in ARCHITECTURES:
            c=replace(config,retail_size=0.,volatility=0.)
            w=World(architecture,c)
            prices=w.reference.copy();prices[0]*=shock
            w.refresh(prices)
            start_error=abs(w.mechanism.price(0)/prices[0]-1)
            before_lp=w.mechanism.nav(prices) if isinstance(w.mechanism,WeightedPool) else None
            for _ in range(20):
                w.refresh(prices);w.arbitrage()
            r=w.metrics()
            r.update(shock_factor=shock,initial_token0_mispricing=start_error,
                     final_token0_mispricing=abs(w.mechanism.price(0)/prices[0]-1),
                     lp_nav_after_shock_before_arb=before_lp)
            rows.append(r)
    return pd.DataFrame(rows)


def depth_matched_independent(config):
    """Counterexample: coupling is unnecessary to reproduce a local buy slope."""
    from math import sqrt
    c=replace(config,fee=0)
    qworld=World("quadratic",c)
    target_b=float(qworld.mechanism.spec.b)
    R=qworld.mechanism.cash;n=c.tokens;P=c.reference_price
    a=sqrt(P*P-2*R*target_b/n)
    x=2*R/(n*(P+a))
    alternative=FloatSurface(Spec("independent",a,target_b),n,x,0)
    d=.01
    assert abs(alternative.cash-R)<1e-7
    assert abs(alternative.price(0)-P)<1e-7
    return pd.DataFrame([dict(architecture=name,a=float(m.spec.a),b=float(m.spec.b),
                              starting_fraction=m.q[0],required=m.cash,initial_price=m.price(0),
                              exact_buy_100_reference_notional=m.quote(0,d,"buy"),
                              exact_sell_100_reference_notional=m.quote(0,d,"sell"))
                         for name,m in (("quadratic",qworld.mechanism),("depth_matched_independent",alternative))])


def scaling(config):
    rows=[]
    for n in (2,10,100,1000):
        c=replace(config,tokens=n,events=100,scenario="baseline")
        for architecture in ARCHITECTURES+("hub",):
            start=time.perf_counter()
            result,_=run_world(architecture,c)
            result["elapsed_seconds"]=time.perf_counter()-start
            rows.append(result)
    return pd.DataFrame(rows)


def summaries(raw):
    numeric=[name for name in raw.select_dtypes("number").columns if name not in ("seed",)]
    rows=[]
    for (scenario,arch),group in raw.groupby(["scenario","architecture"]):
        for metric in numeric:
            rows.append(dict(scenario=scenario,architecture=arch,metric=metric,**distribution(group[metric])))
    for scenario,group in raw.groupby("scenario"):
        baseline=group[group.architecture=="independent"].set_index("seed")
        for arch in ARCHITECTURES[1:]:
            other=group[group.architecture==arch].set_index("seed")
            for metric in numeric:
                rows.append(dict(scenario=scenario,architecture=arch+"_minus_independent",metric=metric,
                                 **distribution(other[metric]-baseline[metric])))
    return pd.DataFrame(rows)


def run_suite(output,config,seeds=100,scenarios=("baseline","divergent","crash","toxic_admission","joint_run")):
    output=Path(output)
    if output.exists() and any(output.iterdir()):raise ValueError("Choose a new/empty output directory")
    if type(seeds) is not int or seeds<1:raise ValueError("Positive seed count required")
    output.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).parents[2]
    sources=sorted((root/"bonding_lab").glob("*.py"))+sorted(Path(__file__).parent.glob("*.py"))
    manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),status="running",config=asdict(config),seeds=seeds,
                  scenarios=list(scenarios),synthetic=True,capital_basis="identical sponsor net deployment + identical dealer/retail/bot cash endowments; paid inventory counted",
                  packages={p:importlib.metadata.version(p) for p in ("numpy","pandas","pytest","hypothesis")},
                  source_sha256={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                  completed=[])
    path=output/"manifest.json"
    path.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    start=time.perf_counter();all_rows=[]
    try:
        for scenario in scenarios:
            print(f"{scenario}: {seeds} matched seeds x {config.events} events x 4 architectures",flush=True)
            rows=[]
            for j in range(seeds):
                c=replace(config,seed=config.seed+j,scenario=scenario)
                tape=shock_tape(c)
                for architecture in ARCHITECTURES:
                    result,history=run_world(architecture,c,tape,record=j==0)
                    rows.append(result)
                    if j==0:history.to_csv(output/f"{scenario}_{architecture}_example.csv",index=False)
            raw=pd.DataFrame(rows);raw.to_csv(output/f"{scenario}_runs.csv",index=False)
            all_rows+=rows
            manifest["completed"].append(scenario)
            path.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
        raw=pd.DataFrame(all_rows)
        raw.to_csv(output/"all_runs.csv",index=False)
        summaries(raw).to_csv(output/"summary.csv",index=False)
        for name,table in (("initial_liquidity",liquidity_at_start(config)),
                           ("zero_fee_liquidity",liquidity_at_start(replace(config,fee=0))),
                           ("joint_liquidity",joint_liquidity(config)),("toxic_control",controlled_toxic(config)),
                           ("order_attacks",order_attacks(config)),("bounded_exact",bounded_exact_checks()),
                           ("scaling",scaling(config)),("arbitrage_controls",arbitrage_controls(config)),
                           ("depth_matched_independent",depth_matched_independent(config))):
            table.to_csv(output/f"{name}.csv",index=False)
            manifest["completed"].append(name)
        manifest["status"]="complete"
    except BaseException as exc:
        manifest.update(status="failed",failure=repr(exc));raise
    finally:
        manifest["elapsed_seconds"]=time.perf_counter()-start
        path.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest
