# Research findings: shared quadratic bonding surface

Generated from completed local runs on 28 October 2026. All behavioral outcomes
are **synthetic**, not historical market evidence. The precise equations in
[MATHEMATICS.md](MATHEMATICS.md) define the mechanism being evaluated.

## Assessment

For this model, positive coupling does **not improve fixed-quantity own-token
depth**: the absolute marginal price slope remains k. It raises prices and
required backing when other supplies are positive, adds deterministic contagion,
and enables cross-token transaction-order transfers. Full funding preserves
reserve solvency, but does not make those transfers fair or price discovery useful.
The runs below do not establish a welfare or liquidity advantage over independent
quadratic curves. This is a negative result for that proposed justification;
organic demand, user preferences and alternative mechanisms remain untested.

## What actually ran

- **44 tests passed** in the full implementation suite (55.68 seconds). This
  includes 100-example deterministic Hypothesis properties, randomized valid
  transaction sequences, 1,000-trade Float64/Decimal parity at each of six coupling
  values, accounting identities, constraints, attack formulas and Streamlit app
  interactions. A further targeted app check followed replay refinements.
- Pilot: **100 seeds × 2,000 demand events × six scenarios × two comparison
  bases × two models** = 2,400 market runs and 4,800,000 demand events.
- Longer baseline: **100 seeds × 10,000 events × two bases × two models** =
  400 market runs and 4,000,000 demand events.
- Combined Monte Carlo: **2,800 runs, 8,800,000 demand events**. Seeds are
  42–141. Rejected/skipped intentions are counted; they are not fabricated fills.
- Exact analyses: 108 fee/coupling/payment-cap/competition attack cases;
  90 complete bank runs with 900 recorded redemptions;
  coordinated-wallet acquisition/exit permutations; controlled popular-token and
  crash transitions; 2×/10×/100× capital calculations.
- Scaling: 36 actually executed 1,000-event markets across 2, 10,
  100 and 1,000 tokens; three coupling settings and three seeds per setting.
  These scaling runs supplement the Monte Carlo event count above.
- No completed batch used 1,000 seeds, and the non-baseline scenarios were not
  run at 10,000 events per seed. Those larger jobs are supported by the CLI.

Pilot elapsed: 382.7 seconds; longer baseline:
335.2 seconds. The jobs ran concurrently, so elapsed
times reflect local contention and are not independent performance benchmarks.
Both manifests have `status=complete` and source SHA-256 hashes verified against
the current engine. Interrupted development batches are preserved under ignored
`results/scratch`; they are excluded here.

Default assumptions: 10 tokens; p0=.01; k=.0001; shared λ=.25 versus λ=0;
1,000 units per token before capital matching; 100 traders with $1,000 additional
trading cash each; retail 60%, whale 10%, other roles cycled; mean base trade
notional $20 with log-size volatility .8; buy pressure .55; fee 0.3%. The pending
order scenario gives each attacker $500 and a 2% victim payment tolerance. No
network cost applies to Monte Carlo; exact attacks can include an explicit cost.

## Experiment A: independent versus shared

**Proof.** At equal supplies, 10 tokens with 1,000 units each require $600
independent backing and $1,725 shared backing. The initial marginal price rises
from $.11 to $.335. Buying another 100 units costs $11.50 versus $34.00 gross.
The absolute marginal price increase is $.01 in both. Equal initial capital is a
separate comparison: the independent system must begin with more token units.

**Simulated findings.** The table reports paired mean *shared minus independent*
outcomes. Capital is genesis required backing, redemption is the completed-run
collective net redemption, and slippage is average gross execution deviation from
the pre-trade quote. Attacker profit is the shared pending-order scenario's mean,
not a paired difference. Fractions labeled pp are percentage points.

| Scenario | Matched basis | Δ initial backing | Δ final net redemption | Δ mean slippage | Attacker mean |
| --- | --- | --- | --- | --- | --- |
| baseline | supplies | $1,125.00 | -$540.05 | -0.610 pp | n/a |
| baseline | capital | $0.00 | -$665.06 | -0.441 pp | n/a |
| popular | supplies | $1,125.00 | $669.30 | -0.294 pp | n/a |
| popular | capital | $0.00 | -$200.73 | -0.167 pp | n/a |
| crash | supplies | $1,125.00 | -$1,609.85 | -1.114 pp | n/a |
| crash | capital | $0.00 | -$1,913.39 | -0.902 pp | n/a |
| bundled | supplies | $1,125.00 | -$616.72 | -0.624 pp | n/a |
| bundled | capital | $0.00 | -$753.80 | -0.451 pp | n/a |
| frontrun | supplies | $1,125.00 | -$839.20 | -0.722 pp | -$91.67 |
| frontrun | capital | $0.00 | -$964.21 | -0.499 pp | -$91.67 |
| bank_run | supplies | $1,125.00 | $3.35 | -1.182 pp | n/a |
| bank_run | capital | $0.00 | -$7.57 | -0.956 pp | n/a |

Longer baseline paired differences, with approximate 95% seed-mean intervals:

| Basis | Metric | Mean difference | 95% interval |
| --- | --- | --- | --- |
| supplies | collective_liquidation | -3,246.0535 USDC | [-3,340.3701, -3,151.7370] |
| supplies | mean_slippage | -0.2143 pp | [-0.2154, -0.2132] |
| supplies | trader_realized_pnl | 2,886.6047 USDC | [2,802.4987, 2,970.7107] |
| capital | collective_liquidation | -2,913.8563 USDC | [-3,009.5352, -2,818.1775] |
| capital | mean_slippage | -0.1790 pp | [-0.1798, -0.1781] |
| capital | trader_realized_pnl | 2,188.3827 USDC | [2,113.8948, 2,262.8707] |

These policies adapt to prices and wallet constraints: matching shocks does not
force identical filled quantities. Greater final reserves can reflect greater
capital paid in, rather than better liquidity. Realized P&L alone excludes
remaining inventory; marked P&L and first-exit values are exported separately.
Gross volume per initial backing is reported as an activity ratio, not established
capital efficiency. No utility function or organic adoption benefit was measured.

## Experiments B and C: popularity and crash contagion

**Exact controlled result.** In the 10-token state above, a 10,000-unit purchase
of Token 0 raises each untouched token by $.25 at λ=.25. Their own demand is zero,
so 100% of that price change is mechanical spillover. Redeeming all 11,000 units
of Token 0 then lowers each other price by $.275, including removal of its
original 1,000 units. These changes are zero at λ=0. The reserve remains backed.

The stochastic popular/crash results are in the paired table and CSVs; their
mixed policies need not create the same magnitude as this controlled example.
Exported price attribution uses the exact identity `Δp_i=kΔq_i+kλΣ(other Δq)`.
Successful issuance can fund early exits in unrelated holdings. Calling it a
subsidy requires the entry/exit sequence: there is no unconditional value creation.

## Experiment D: coordinated launches

**Exact finding.** Coordinated acquisition and complete exit with no intervening
victim trade produces zero aggregate gross profit for every tested acquisition
and exit order; positive fees make it a loss. Wallet splitting does not defeat the
reserve potential. With an intervening purchase, coordinated wallets can capture
order-dependent transfers. Four wallets buying a total of 1,000 B units before
a victim buys 1,000 A units earn $25 gross at λ=.25, or $24.565 after 0.3% fees,
when fully funded and allowed that order. See `cross_token_bundle_checks.csv`.

Same-token early positioning also profits from subsequent buyers at λ=0, so
same-token bundle profits are not evidence of a new shared-reserve flaw.
Mixed-token sequences in `bundle_grid.csv` separate aggregate cost from the
distribution across coordinated wallets. No creator receives unbacked issuance.

## Experiment E: cross-token frontrunning

**Proof and numerical verification.** With one attacker, fixed quantities and a
filled victim, `gross profit=kλab`. This exactly equals the victim's extra gross
purchase cost. Fee-adjusted profit is `(1-f)kλab-2fC-network_cost`, where C is the
attacker's gross acquisition cost. This is value extraction from ordering, while
the reserve stays solvent. It is not a closed-loop collateral-draining arbitrage.

Standard exact workbench cases (p0=.01, k=.0001, initial A=B=1,000):

| Quantity / constraint | Victim fills | Aggregate net profit |
| --- | --- | --- |
| a=1,000, b=500, λ=.25, no fees, one attacker | yes | $12.50 |
| Same, 0.3% trading fee | yes | $11.98 |
| Same fee, 2% victim payment cap | no | -$0.48 |
| Same fee, victim executes first | yes | -$0.56 |
| Same fee, $1 network cost per attacker transaction | yes | $9.98 |

The 2% cap rejects this large victim order after the attack; the attacker still
pays round-trip trading fees. Competitors are separately funded wallets and the
exit order is explicit. Their aggregate and individual profits are available in
the workbench. Network charges are explicitly capital constrained and transferred
to a modeled network account, with no assumed gas market or private ordering.

**Synthetic distribution**, equal initial supplies, λ=.25, 0.3% fee, 2% cap:
mean attacker total realized profit -$91.67 per 2,000-event run;
median -$91.43; standard deviation $10.57;
5th/95th percentiles -$108.55/-$77.02;
worst observed -$120.02; mean 95% interval
[-$93.74, -$89.60].
Profitable-run frequency 0.0%, with Wilson 95% interval
[0.0%, 3.7%]. Mean within-run
profitable-opportunity fraction 3.7%.
These are different denominators; neither estimates a real-world attack rate.
Attack sizing/order is a synthetic heuristic, not an optimal adversary.

## Experiment F: scaling

Uniform supply 1,000 units per existing token; p0=.01, k=.0001:

| Tokens | λ=0 backing | λ=.25 backing | λ=.25 new-token price |
| --- | --- | --- | --- |
| 2 | $120.00 | $145.00 | $0.06 |
| 10 | $600.00 | $1,725.00 | $0.26 |
| 100 | $6,000.00 | $129,750.00 | $2.51 |
| 1000 | $60,000.00 | $12,547,500.00 | $25.01 |

**Proof.** With fixed per-token units and positive λ, backing grows quadratically
with token count and existing/new token price intercepts grow linearly. A token
can start expensive before receiving any demand. Denomination comparability is a
major modeling assumption: this surface is not invariant to arbitrary token
decimal/unit changes. At λ=1 all token marginal prices coincide regardless of
which name attracted demand.

**Executed scale runs.** All 36 completed scaling simulations stayed
within the declared reserve tolerance. Their max material shortfall was
0 USDC. Timing distributions are saved
in `scaling_simulations.csv`; median 1,000-token run time was
0.0408 seconds for 1,000
events. This demonstrates local computability at those settings, not economic
safety, production capacity, or a large trader-population benchmark. Engine
quotes/trades are O(1); full snapshots, scans and storage are not.

## Experiment G: bank runs, solvency and fairness

**Proof and exact execution.** Fully funded issuance and reserve-difference
redemption telescope: all holders can redeem, and aggregate gross receipts equal
R regardless of exit order. The exact full-redemption tests left zero required
reserve. Fees and donated buffers are separately accounted for.

At λ=.25 with ten 1,000-unit positions, first exit receives
$285.00; last exit receives
$60.00, even though quantities match.
At λ=0 each receives $60. Entry costs also depend on order, so gross receipts are
not themselves P&L; the bank-run export includes cost-aware realized P&L.
Total system solvency therefore coexists with meaningful order risk and contagion.

Across the Monte Carlo batches, largest raw floating backing discrepancy was
1.1059456e-09 USDC and largest material shortfall was 0 USDC. The fast
engine tolerance is `1e-9 * max(1, initial external capital, current reserve)`;
no such tolerance is used by the Decimal accounting tests. Floating evidence is
not a substitute for the mathematical solvency proof or settlement-rounding tests.

## Experiment H: price runs and paper capitalization

Fixed initial 10-token supplies; no fees; only the target token receives new
issuance. Gross new capital needed for the indicated marginal-price multiple:

| Own-price multiple | Independent capital | Shared λ=.25 capital |
| --- | --- | --- |
| 2× | $181.50 | $1,683.38 |
| 10× | $5,989.50 | $55,551.38 |
| 100× | $604,939.50 | $5,610,688.88 |

**Proof.** Capital equals `p²(m²-1)/(2k)` for an own-token run. Coupling's higher
starting intercept makes the same relative move more expensive at the matched
supply state. Cross-token issuance can raise a target's price without target
buying, but the other buyers must still fund their reserve differences. The growth
CSV reports that route separately. No calibrated adoption model supports a claim
that coupling makes large organic price runs more likely.

Collective paper market cap satisfies `M=2R-p0Q`, hence lies between R and 2R
for positive supplies. Complete gross liquidation is R, not M. Per-token or
per-wallet first-exit quotes cannot be added into jointly executable proceeds.

## Answers to the ten design questions

1. **Better liquidity?** No fixed-quantity depth improvement follows from this
   surface; own slope is unchanged. Simulated relative slippage cannot establish it.
2. **More capital to buy?** Yes at matched supplies with other positive supplies;
   initial backing also rises. Equal-capital results must change initial issuance.
3. **Unrelated appreciation?** Exactly `kλΣΔq_other`; the controlled example had
   entirely unrelated appreciation. Real demand attribution remains untested.
4. **Indirect manipulation?** Yes, funded issuance elsewhere deterministically
   moves a token's quote; it costs actual capital and unwind changes the quote again.
5. **Cross-token ordering profits?** Yes under funded, fee/slippage-feasible
   sequences, as the exact formula and workbench verify.
6. **Subsidies?** Cross terms can transfer value from later successful issuance
   to earlier unrelated holdings, conditional on entry and exit ordering.
7. **Fragility?** Mechanical price contagion and exit-order risk increase with λ.
   Endogenous real-world run probability is not established by these policies.
8. **Thousands of tokens?** Computable and solvent under valid accounting in
   tested runs; economically costly at fixed units, with elevated new-token prices.
9. **Larger runs easier?** Not for matched-supply own-token relative moves in this
   model. Spillover paper runs require external issuance capital elsewhere.
10. **Useful shared reserve?** Shared custody alone changes no λ=0 execution
   economics. Positive coupling redistributes exposure; no measured net welfare
   benefit here compensates for that added exposure and ordering risk.

## Proposed mitigations — not implemented or validated as replacements

- Cap coupling or use fixed-capacity isolated cohorts to limit total exposure.
  Repricing λ when membership changes requires explicit collateral and ownership
  accounting; it must not be silently normalized during trading.
- Investigate batch clearing or protected transaction submission against the
  specified ordering attack. Their effectiveness and decentralization assumptions
  need separate models; this simulator does not establish them.
- Study a different convex potential, e.g. separable own-token terms plus a global
  term with bounded marginal derivative. Re-derive funding, derivatives, attack
  profits and scaling from that potential before claiming an improvement.
- Retain λ=0 with shared custody as a control. Operational simplicity or shared
  infrastructure might be useful, but those benefits were not measured here.

## Limits, evidence and reproduction

No real market data, external exchange/arbitrage, gas auction, latency network,
strategic equilibrium, borrower, short seller, organic narrative model, protocol
governance, denomination policy or six-decimal cash rounding is included. Roles
are transparent assumed heuristics. Genesis inventory is paid for by attributed
holder contributions in addition to their trading cash; extra reserve is donated.
Net external flow means trader-to-curve cash including fees, within a closed
simulated economy. Fee recipients and the donation sponsor are distinct from
trader P&L. A minimum marginal price is not a promise that every holder can exit
at the displayed quote.

Seed-mean intervals use the normal approximation across 100 independent seeds;
paired intervals use matched seed differences. They quantify uncertainty inside
this simulator, not model uncertainty or out-of-sample predictive accuracy. The
2,000-event and 10,000-event horizons must not be pooled as one identical design.
Worst observed outcomes are sample extrema, not guaranteed bounds.

Artifacts: `results/pilot/*_runs.csv` and `*_summary.csv`,
`results/long_baseline/*`, `results/cross_token_bundle_checks.csv`, and
`results/research_charts.html`. Manifests include exact versions, configurations,
completion states, source hashes and elapsed time. Reproduce with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m bonding_lab.cli research --seeds 100 --events 2000 --out results/reproduce_pilot
.\.venv\Scripts\python.exe -m bonding_lab.cli research --seeds 100 --events 10000 --scenarios baseline --out results/reproduce_long
.\.venv\Scripts\python.exe -m streamlit run dashboard.py
```

Run `python scripts/build_report.py` to regenerate this report from its original
completed directories. A failed or interrupted manifest is rejected, and source
hash mismatches stop report generation. See README for install commands and the
supported larger CLI batches.
