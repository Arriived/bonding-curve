"""Reproduce selected completed states, then actually liquidate retail positions.

This distinguishes realized executable exits from reference marks, particularly
when a synthetic reference quotes puttable curve claims below redemption value.
It does not change the frozen main experiment source or fabricate new seeds.
"""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bonding_lab.phase2.world import World,Study,ARCHITECTURES,RETAIL
from bonding_lab.phase2.research import shock_tape


def main():
    out=ROOT/"results/phase2"
    manifest=json.loads((out/"manifest.json").read_text())
    assert manifest["status"]=="complete"
    raw=pd.read_csv(out/"all_runs.csv")
    rows=[]
    for scenario in manifest["scenarios"]:
        for seed in (42,77,91):
            c=Study(**{**manifest["config"],"scenario":scenario,"seed":seed})
            z,tokens,draw,budgets=shock_tape(c)
            for architecture in ARCHITECTURES:
                w=World(architecture,c)
                for t in range(c.events):
                    w.refresh(z[t])
                    if scenario=="toxic_admission" and t==c.events//3:w.toxic_creator_sale()
                    i=int(tokens[t]);side="buy" if draw[t]<c.buy_pressure else "sell"
                    if scenario=="joint_run" and t>c.events//2:side="sell";i=int(np.argmax(w.h[RETAIL]))
                    d=(w.buy_quantity(i,min(budgets[t],w.cash[RETAIL]*.95)) if side=="buy" else
                       min(w.h[RETAIL,i],budgets[t]/w.reference[i],w.mechanism.max_sell(i)))
                    if d>1e-10:w.internal(RETAIL,i,d,side)
                    w.arbitrage()
                m=w.metrics()
                old=raw[(raw.scenario==scenario)&(raw.seed==seed)&(raw.architecture==architecture)].iloc[0]
                for metric in ("final_cash_reserve","arb_profit","retail_pnl","retail_realized_pnl"):
                    assert np.isclose(m[metric],old[metric],atol=1e-7,rtol=1e-9),(scenario,seed,architecture,metric)
                for order in ("forward","reverse"):
                    clone=deepcopy(w)
                    indices=list(range(c.tokens))
                    if order=="reverse":indices.reverse()
                    proceeds=0.
                    boundary_dust=0.
                    for i in indices:
                        held=clone.h[RETAIL,i]
                        limit=clone.mechanism.max_sell(i)
                        if held>limit:
                            # Strict input guards remain strict. At a float cap
                            # boundary the separately accumulated ownership can
                            # exceed 1-y by a few ulps; execute only legal input
                            # and report the actual remainder, never erase it.
                            assert held-limit<1e-10,(scenario,seed,architecture,held,limit)
                            boundary_dust=max(boundary_dust,float(held-limit))
                        d=min(held,limit)
                        if d>1e-12:proceeds+=clone.internal(RETAIL,i,float(d),"sell")
                    clone.assert_invariants()
                    pnl=clone.cash[RETAIL]-c.retail_capital
                    assert abs(pnl-clone.retail_realized)<1e-6
                    assert clone.h[RETAIL].sum()<1e-10
                    rows.append(dict(scenario=scenario,seed=seed,architecture=architecture,exit_order=order,
                                     pre_exit_marked_pnl=m["retail_pnl"],pre_exit_realized_pnl=m["retail_realized_pnl"],
                                     actual_full_exit_pnl=pnl,actual_sale_receipts=proceeds,
                                     remaining_token_fraction=float(clone.h[RETAIL].sum()),
                                     maximum_cap_boundary_dust=boundary_dust,
                                     source_state_reproduced=True))
    result=pd.DataFrame(rows)
    result.to_csv(out/"retail_exit_checks.csv",index=False)
    print(f"Reproduced 60 saved market states; executed {len(result)} funded retail exits in both orders")


if __name__=="__main__":main()
