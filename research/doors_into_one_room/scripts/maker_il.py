"""Usage: python3 research/doors_into_one_room/scripts/maker_il.py   (run from the repo root; no dependencies)

Fees versus impermanent loss for a maker providing liquidity to a memecoin / room.

Price on the curve is p(R) = (v_sol+R)^2/(v_sol*v_tok), so the price ratio from launch to a final reserve R is
r = ((v_sol+R)/v_sol)^2. For constant product, an LP's value relative to holding the same initial basket is
2*sqrt(r)/(1+r). Fees are earned on volume. We do not have per-coin volume, so we express the fee side as a
multiple m of the coin's final reserve (net buying is a hard lower bound on volume, so m >= 1 always).

LIMIT: the dataset holds launch state and one final reading, not a price path. Real impermanent loss is
path-dependent, so these figures are a LOWER BOUND on the loss for a maker who provides at launch and holds to
the end. They say nothing about a maker who enters mid-life at an elevated price — which is exactly the product
in MAKER_ROLE.md §3b. Settling that needs price and volume time series, which the watcher can collect.
"""
import json, statistics
from math import sqrt

q = json.load(open("research/doors_into_one_room/outputs/curve_quantities.json"))
VS = q["v_sol_lamports"]
rows = [json.loads(l) for l in open("research/doors_into_one_room/outputs/narrative/consolidation_outcomes.jsonl")]
res = [int(r["real_quote_reserves_raw"]) for r in rows if r.get("real_quote_reserves_raw") is not None]
n = len(res)
print(f"{n:,} coins with a final reserve reading\n")

buckets = [(0, 0.01), (0.01, 0.1), (0.1, 1), (1, 5), (5, 20), (20, 10**9)]
print("where they ended up (final reserve, SOL):")
for lo, hi in buckets:
    c = sum(1 for x in res if lo <= x/1e9 < hi)
    print(f"  {lo:>6.2f} to {hi if hi<10**8 else float('inf'):>8}  {c:>5}  {c/n:>6.1%}")

def il(r):                      # LP value / hold value, constant product
    return 2*sqrt(r)/(1+r) if r > 0 else 0.0

print("\nA maker who provides liquidity AT LAUNCH and holds to the end:")
ratios = [((VS + x)/VS)**2 for x in res]
keep = [il(r) for r in ratios]
print(f"  median LP value vs holding: {statistics.median(keep):.1%}  (100% = no loss)")
print(f"  mean:                       {statistics.mean(keep):.1%}")
worse = sum(1 for k in keep if k < 0.99)
print(f"  coins where the maker lost to simply holding: {worse:,} of {n:,} ({worse/n:.0%})")

print("\nBreak-even: fee income must cover that loss. Fee = 1% of volume; volume = m x final reserve.")
for lab, sub in (("all coins", res), ("survivors: final reserve >= 1 SOL", [x for x in res if x >= 10**9]),
                 ("survivors: final reserve >= 5 SOL", [x for x in res if x >= 5*10**9])):
    if not sub: continue
    # maker owns the whole pool; pool value ~ 2*reserve (both sides). loss = (1-il)*2R ; fees = 0.01*m*R
    need = []
    for x in sub:
        r = ((VS+x)/VS)**2
        loss = (1 - il(r)) * 2 * x
        need.append(loss/(0.01*x) if x else 0)
    print(f"  {lab:<36} n={len(sub):>5}  median break-even volume = {statistics.median(need):>8.1f}x final reserve")
