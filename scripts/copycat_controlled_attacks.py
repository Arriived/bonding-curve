"""Exact implications and funded large-order best responses; separate from MC."""
from pathlib import Path
from dataclasses import replace
import json
import math
import sys
import argparse
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bonding_lab.fast import FastBook
from bonding_lab.copycat.config import Variant
from bonding_lab.copycat.router import Router


def setup(v,M,B):
    b=FastBook(2,7,.01,.0001,0,.003,0.)
    q=2*M/(.01+math.sqrt(.01**2+4*.0001*M))
    R=.01*q+.0001*q*q/2
    b.cash=np.array([R*1.003+1.,B+1.,0.,1100000.,0.,0.,0.])
    b.initial_external=float(b.cash.sum());b.initial_wealth=b.cash.copy()
    b.execute(0,0,q,"buy")
    return b,Router(b,v,4,5,6,gas=.05),q


def case(v,M,B):
    b,r,q=setup(v,M,B)
    D=v.rate*B;f=b.fee_rate;p=b.price(0);k=b.k
    limit=b.buy_quantity(0,b.cash[3]-.15)
    victim0=b.buy_quantity(0,D)
    def profit(d):
        C=p*d+k*d*d/2
        if v.form in ("creator","control") or (v.form=="burn" and v.burn=="supply"):return -2*f*C-.1
        if v.form=="holders":return D*d/(q+d)-2*f*C-.1
        P=p+k*d;vd=2*(D/(1+f))/(P+math.sqrt(P*P+2*k*D/(1+f)))
        if vd<.98*victim0:return -1e20
        return (1-f)*k*d*vd-2*f*C-.1
    lo,hi=0.,limit
    for _ in range(65):
        x=lo+(hi-lo)*.38196601125;y=lo+(hi-lo)*.61803398875
        if profit(x)<profit(y):lo=x
        else:hi=y
    d=(lo+hi)/2
    # Compare the continuous search to an explicit logarithmic size grid plus idle.
    grid=np.geomspace(max(1e-8,limit*1e-9),limit,100)
    options=[(profit(d),d)]+[(profit(float(x)),float(x)) for x in grid]
    predicted,d=max(options)
    if predicted<=0:
        return dict(form=v.form,burn=v.burn,rate=v.rate,leader_cap=M,copy_buy_budget=B,profit=0.,quantity=0.,
                    capital_committed=0.,predicted_profit=0.,victim_filled=True,abstained=True)
    before=b.cash[3]
    r.buy(0,3,0,(p*d+k*d*d/2)*(1+f),0,2)
    capital=before-b.cash[3]
    r.buy(0,1,1,B,0,2,min_leader_quantity=.98*victim0 if v.form in ("buyer","treasury","burn") else 0.)
    r.sell(0,3,0,float(b.holdings[3,0]));b.assert_invariants()
    actual=b.cash[3]-before
    assert abs(actual-predicted)<1e-6,(v,M,B,actual,predicted)
    return dict(form=v.form,burn=v.burn,rate=v.rate,leader_cap=M,copy_buy_budget=B,profit=actual,quantity=d,
                capital_committed=capital,predicted_profit=predicted,victim_filled=True,abstained=False)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",default="research/copycat_diversion/controlled")
    args=parser.parse_args()
    out=ROOT/args.out
    if out.exists() and any(out.iterdir()):raise ValueError("Choose a new output directory")
    out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for form,burn in (("creator","lock"),("holders","lock"),("buyer","lock"),("treasury","lock"),("burn","lock"),("burn","supply")):
        for rate in (.01,.03,.05,.1):
            for M in (2000.,100000.,1000000.):
                for B in (10000.,100000.,500000.):rows.append(case(Variant(form=form,rate=rate,burn=burn),M,B))
    pd.DataFrame(rows).to_csv(out/"front_response_search.csv",index=False)
    fees=[]
    for M in (100000.,1000000.):
        q=2*M/(.01+math.sqrt(.01**2+4*.0001*M));R=.01*q+.0001*q*q/2
        for rate in (.01,.03,.05,.1):
            fees.append(dict(leader_threshold=M,supply=q,required_reserve=R,entry_capital=1.003*R,
                             roundtrip_curve_fees=2*.003*R,launch_and_two_tx=10.1,rate=rate,
                             outsider_spending_break_even=(2*.003*R+10.1)/rate))
    pd.DataFrame(fees).to_csv(out/"capital_race_break_even.csv",index=False)
    spam=[]
    for n in (1,7,25):
        for rate in (.01,.03,.05,.1):
            spam.append(dict(actor_tokens=n,rate=rate,launch_cost=10*n,
                             creator_external_diversion_spending_break_even=10*n/rate,
                             qualification="phi=1, no other profit/cost; self-paid diversion excluded"))
    pd.DataFrame(spam).to_csv(out/"spam_break_even.csv",index=False)
    result=pd.DataFrame(rows)
    metadata=dict(status="complete",cases=len(result),positive_cases=int((result.profit>0).sum()),
                  max_positive_profit=float(result.profit.max()),
                  search="65-iteration golden-section plus 100 logarithmic sizes and abstention; funded execution validated",
                  minimum_leader_output_fraction=.98,gas_per_transaction=.05,synthetic=True)
    (out/"manifest.json").write_text(json.dumps(metadata,indent=2),encoding="utf-8")
    print(json.dumps(metadata,indent=2))


if __name__=="__main__":main()
