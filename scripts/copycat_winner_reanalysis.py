"""Reinterpret existing confirmation runs for convergence on ANY ticker winner."""
from dataclasses import fields
from pathlib import Path
import argparse,hashlib,json,sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bonding_lab.copycat.config import Variant


def main():
    p=argparse.ArgumentParser();p.add_argument("--base",default="research/copycat_diversion")
    args=p.parse_args();base=ROOT/args.base
    m=json.loads((base/"results/manifest.json").read_text());assert m["status"]=="complete"
    for name,digest in m["sources"].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    raw=pd.read_csv(base/"results/confirmation_runs.csv")
    controls=pd.read_csv(base/"confirmation_controls/counterfactual_runs.csv")
    variants=pd.read_csv(base/"results/variants.csv")
    lookup={}
    for row in variants.to_dict("records"):
        lookup[row["variant"]]=Variant(**{f.name:row[f.name] for f in fields(Variant)}).control().label
    metrics=["largest_share_time_mean","leader_liquidity_share_time_mean","leader_organic_volume_share_time_mean",
             "leader_accessible_liquidity_time_mean","total_accessible_liquidity_time_mean","leader_switches",
             "peak_attacker_cash_committed","attacker_profit","retail_profit"]
    rows=[]
    for (name,family),g in raw.groupby(["variant","family"]):
        a=g.set_index("seed");b=controls[(controls.variant==lookup[name])&(controls.family==family)].set_index("seed")
        assert a.index.equals(b.index) and np.array_equal(a.initial_external_cash,b.initial_external_cash)
        for metric in metrics:
            x=a[metric]-b[metric];half=2.04523*x.std(ddof=1)/np.sqrt(len(x))
            rows.append(dict(variant=name,family=family,metric=metric,n=len(x),variant_mean=a[metric].mean(),control_mean=b[metric].mean(),
                             mean_difference=x.mean(),median_difference=x.median(),q05_difference=x.quantile(.05),q95_difference=x.quantile(.95),
                             min_difference=x.min(),max_difference=x.max(),mean_ci95_low=x.mean()-half,mean_ci95_high=x.mean()+half))
    result=pd.DataFrame(rows);result.to_csv(base/"results/winner_reanalysis.csv",index=False)
    cases=[("first_buyer_5pct_exact_fixed_badge0","none"),("volume120_buyer_10pct_exact_fixed_badge0","none"),
           ("threshold100000_buyer_10pct_exact_fixed_badge0","race"),("held5_buyer_10pct_exact_fixed_badge0","race")]
    table=[]
    for name,family in cases:
        g=result[(result.variant==name)&(result.family==family)].set_index("metric")
        r=g.loc["largest_share_time_mean"];v=g.loc["leader_organic_volume_share_time_mean"]
        cash=g.loc["peak_attacker_cash_committed"]
        table.append(f"| {name} / {family} | {r.variant_mean:.1%} | {r.control_mean:.1%} | {100*r.mean_difference:+.2f} pp | {100*v.mean_difference:+.2f} pp | ${cash.variant_mean:,.0f} / ${cash.control_mean:,.0f} |")
    text='''# Clarified objective: convergence on whichever token wins

The user clarified that the focal token may be the original or a copy. Original
survival is not a success criterion. A copy winning the title is therefore not,
by itself, an attack failure or a reason to reject the mechanism.

The previous report put too much weight on original-token share and authentic-
original identification. Its accounting, funded execution and cash results still
stand, but its ranking and broad negative verdict do not settle this clarified
winner-convergence question. This is a reanalysis of the same synthetic runs,
not a new simulation or real-market validation. No earlier result was deleted.

## What the mechanism does mathematically

For gross incoming buy budgets B_i, selected winner w, and diversion alpha, a
buyer-owned leader-purchase route sends B_w + alpha*sum(B_i for i != w) toward
the winner and (1-alpha)*B_i toward each other matched token, before fees/gas.
If the winner already gets fraction s of buys, its new budget share is
s + alpha*(1-s), holding purchase intentions fixed. This is a flow identity,
not a reserve-share forecast after exits or an endogenous adoption model.

Example: with $1m of buys, $200k aimed at the winner and $800k at copies, a 5%
route sends $240k toward the winner and $760k toward other tokens. A 10% route
sends $280k/$720k. The winner can be a copy; after selection the original can
also be a losing token that contributes. Low diversion alone does not force
almost all liquidity into one token. Stronger convergence needs more direct
buyer migration, continued asymmetric flows or a higher diversion.

Creator/holder cash payments do not implement the reserve-inflow identity: they
pay a recipient. Buyer-owned leader purchases implement it while preserving
the buyer's funded claims. Treasury/lock routes give different ownership rights.

## What existing held-out runs say under identity-free metrics

Largest-token share measures actual private-holder redemption, averaged over
time, irrespective of identity. Controls use the same initial capital, seed and
election rule, with their independently training-selected policy in the same
family. Peak actor cash deployment is shown because equal budgets do not imply
equal capital actually committed. The finite policy classes are not global best
responses; expanded portfolio controls do not export concentration metrics and
are therefore not silently substituted into this table.

| Setting / family | Largest-token share | Control | Change | Elected-leader organic-volume share change | Peak actor cash deployed: variant / control |
| --- | --- | --- | --- | --- | --- |
'''+"\n".join(table)+'''

The races can therefore look better on concentration even while the original
loses. Rejecting them solely for replacing the original would be the wrong test.
However, much higher actor cash deployment can itself produce a large dominant
reserve. It must not be mistaken for independent buyers coordinating around a
durable winner. The organic-volume column helps distinguish these effects.
Full per-setting/family paired means, medians, tails and 95% seed-level mean
intervals are saved in `results/winner_reanalysis.csv` (30 seeds per estimate).

## What remains unresolved

- Can the race settle on one enduring focal token, rather than successive titles
  and several separate near-ticker royalty groups? Maximum share at each instant
  can refer to different tokens; it is not proof of one persistent winner.
- Does concentrated liquidity remain after the winner's sponsor redeems its own
  pump capital? Existing accessible claims include funded attacker inventory.
- Do loser buyers who also receive winner tokens become more aligned with that
  winner? Such ownership-to-attention feedback was not modeled.
- Do entry incentives create useful competition or profitable copy farms that
  fragment demand further? Manipulation is harmful when it extracts funded value
  or undermines durable consolidation, not merely because the winner is a copy.
- Does the mechanism prolong participation and the meme narrative? Aggregate
  intended demand was exogenous, so narrative survival cannot be inferred.

The fair revised interpretation is **a plausible winner-convergence hypothesis
with measurable modest flow concentration, but viability remains unresolved**.
The prior verdict should not be read as a proof that this clarified idea fails.
A revised experiment should make identity-free durable concentration primary,
measure post-sponsor-exit organic liquidity, and model attention/adoption feedback
as explicit sensitivities. Cash-transfer and ordering risks remain relevant.

Reproduce this analysis without rerunning markets:

```powershell
.\\.venv\\Scripts\\python.exe scripts/copycat_winner_reanalysis.py
```
'''
    (base/"WINNER_REANALYSIS.md").write_text(text,encoding="utf-8")
    record=dict(status="complete",new_market_calls=0,rows=len(result),seeds=m["confirmation_seeds"],
                objective="durable concentration on any winner; original identity is descriptive only",
                sources_verified=True,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                inputs={str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                        [base/"results/confirmation_runs.csv",base/"confirmation_controls/counterfactual_runs.csv"]})
    (base/"winner_reanalysis_manifest.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in record.items() if k not in ("seeds","inputs")},indent=2))


if __name__=="__main__":main()
