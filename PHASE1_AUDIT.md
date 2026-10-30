# Audit of the original quadratic study

29 October 2026. The audit does not treat successful implementation as evidence
of economic merit. Machine-readable evidence is in `results/phase2_audit/audit.json`.

## Evidence verified

- All eight original source-file hashes in both completed manifests match the
  preserved source under `results/phase2_audit/legacy_source/bonding_lab/`.
- All **2,800 recorded runs and 8,800,000 demand events** were counted and their
  seed-level means, medians, standard deviations, quantiles, extrema and approximate
  intervals recomputed from CSVs. Matched-model difference summaries agree.
- Seeds 42, 77 and 141 were re-executed for all 12 pilot scenario/basis combinations
  and both longer-baseline bases; recorded metric vectors reproduced within the
  declared numerical comparison tolerances. This is **84 reproduced market runs**.
- For every equal-capital seed pair, both initial required backing and total
  initial external cash agree. This verifies funding equality in the old design,
  not equality of initial token prices or quantities.
- The 42 original non-UI tests passed again in 19.97 seconds. The historical full
  suite contained two additional dashboard tests. The new dashboard is not rebuilt.

The complete source/hash, CSV and selected-seed audit finished in 40.22 seconds.
The original dataset remains intact; the current fast engine has the narrow fix
below, so a source-hash guard correctly detects it differs from the historical
snapshot. Reproduce the audit with `python scripts/audit_phase1.py`, which imports
the preserved source intentionally.

## Mathematical conclusions

These follow from the potential, not behavioral assumptions:

```
H_ii=k; H_ij=k lambda
M=2R-p0 Q
full gross redemption=R
cross-token ordering transfer=k lambda d_A d_B
```

The Hessian is positive semidefinite on the specified range. Funded buys/burns
preserve the reserve obligation; fees remain outside backing. Gross closed paths
telescope. A zero-supply token launch changes neither reserve nor existing prices.
At fixed coefficients/issued quantities, coupling raises intercepts, required
collateral and unrelated-token exposure, without changing own absolute slope.
At lambda=1 price discovery depends only on aggregate supply. At fixed per-token
units and positive coupling, reserve growth is quadratic in token count.

Those conditional conclusions survive this audit. They do not imply that every
possible parameter calibration with shared infrastructure has the same slope,
or that a different AMM cannot improve local depth by accepting inventory risk.

## Comparison methodology and slippage qualification

Default initial states, gross execution, no fees in this geometry diagnostic:

| Matching | Model | Initial price | Initial backing | Δ price / 100 units | Relative slippage / 100 units | Relative slippage / $20 |
| --- | --- | --- | --- | --- | --- | --- |
| Supplies | shared | .335000 | 1,725 | .010000 | 1.493% | .883% |
| Supplies | independent | .110000 | 600 | .010000 | 4.545% | 7.675% |
| Backing capital | shared | .335000 | 1,725 | .010000 | 1.493% | .883% |
| Backing capital | independent | .186011 | 1,725 | .010000 | 2.688% | 2.811% |

For quantity d, relative average slippage is `k d/(2p)`. For budget B, the exact
quantity is the quadratic inverse and the same formula applies. The table shows
that price normalization alone can reduce reported relative slippage while
absolute fixed-quantity impact is identical. That effect is not a demonstrated
liquidity improvement. The old study explicitly retained this caveat; this audit
strengthens it with reproducible counterfactual geometry.

Equal-capital matching was fiscally correct for its stated backing-plus-trading
cash definition. It was not a price-aligned causal liquidity comparison. Different
supplies, average genesis cost allocations, wallet constraints, momentum response,
skipped sell intentions and endogenous fill quantities also change outcomes.
Phase 2 therefore records full budgets, price-aligned calibrations, every changed
coefficient, finite inventories and external-price execution benchmarks.

## Accounting defect found and repaired

Legacy `FastBook` admitted `capital + 1e-9 >= required`. A two-token state requiring
$145 accepted $144.9999999995, leaving a negative donated buffer of approximately
`-5e-10`. This was tiny but contradicted the claim that underfunded genesis is
always rejected. The current check is strict `capital < required -> reject`, and
a regression test covers the exact example.

This defect does not affect the published default runs: their reserve-capital
setting was zero, which explicitly funds the computed exact requirement. No
historical results were silently patched or reissued. Float tolerances remain
appropriate for research accumulation, not permission to intentionally underfund.

The Decimal reference's input bounds, immutable parameters, funded issuance,
wallet constraints and cash/supply invariants were reviewed and tested. Its
private Python storage is not a production security boundary. Cost-basis division
can round; it is reporting-only and does not determine reserve cashflows.

## Findings that remain assumptions or limited evidence

- Relative-slippage averages, trader profit rankings, run dynamics and attack
  success frequency depend on synthetic demand, horizon, allocation and ordering.
- The default attacker's negative aggregate P&L does not bound an optimized
  adversary or negate the positive exact attack formula.
- Marked cap, reserve level and turnover/backing ratios are not executable depth.
- Summed first-exit wallet quotes are incompatible; the current dashboard keeps
  them in individual rows and does not add them into group executable proceeds.
- No external market, LP inventory, real gas auction or immutable economic
  denomination policy existed in Phase 1. It cannot establish performance against
  a real launchpad or an inventory AMM, nor safe permissionless token admission.
- Raw float shortfalls were within declared tolerance; the insolvency exclusion
  is a conditional accounting proof, not evidence against economic holder losses.

The original economic verdict is retained as a statement about the original
fixed-coefficient model and its tested synthetic policies. The broader shared
liquidity question remains open for the separate Phase 2 mechanisms.
