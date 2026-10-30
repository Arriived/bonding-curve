# Clarified objective: convergence on whichever token wins

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
| first_buyer_5pct_exact_fixed_badge0 / none | 70.4% | 69.4% | +0.98 pp | +0.85 pp | $0 / $0 |
| volume120_buyer_10pct_exact_fixed_badge0 / none | 71.4% | 69.4% | +1.97 pp | +1.71 pp | $0 / $0 |
| threshold100000_buyer_10pct_exact_fixed_badge0 / race | 86.7% | 72.5% | +14.24 pp | +6.12 pp | $502,012 / $200,927 |
| held5_buyer_10pct_exact_fixed_badge0 / race | 86.5% | 72.1% | +14.35 pp | +5.24 pp | $502,012 / $200,927 |

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
.\.venv\Scripts\python.exe scripts/copycat_winner_reanalysis.py
```
