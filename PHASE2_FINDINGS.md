# Phase 2 findings and research verdict

29 October 2026. **All market data in this study are synthetic.** The mechanics
are mathematical models; the measured distributions do not predict real memecoin
returns, demand, attack rates or safe admission decisions.

## Verdict

**No tested design establishes a robust liquidity improvement without a material
tradeoff in exposure or assumptions.** The bounded potential fixes the original
unbounded global premium and quadratic fixed-supply scaling, but does not create
free depth or remove ordering transfers. An inventory AMM genuinely reuses cash
across tokens and improves *one-token local depth* over equally funded isolated
pools. It also socializes toxic-token losses across the common reserve. The
unvetted memecoin admission case does not support calling that tradeoff safe.

An isolated USDC hub/cohort is the conservative control for further work: it can
share custody, routing and software while enforcing cash-risk boundaries. That
is infrastructure sharing, not a claim of pooled financial liquidity gains.
No production protocol or token admission recommendation follows from this study.

## Completed work and validation

- Original audit verified **2,800 old runs /
  8,800,000 demand events**, both manifests and source
  hashes, all stored distribution summaries, matched funding and 84 selected-seed
  re-executions. See [PHASE1_AUDIT.md](PHASE1_AUDIT.md).
- **96 tests passed** in 55.47 seconds, including the unchanged
  dashboard tests, exact rational invariant/property tests, raw redenomination,
  calibration, finite wallets/dealer depth, convexity, attack identities, and
  Decimal/float AMM checks. Test evidence: `results/phase2_validation.xml`.
- Main batch: **50 matched seeds × 300
  demand events × five scenarios × four architectures = 1,000 market runs
  and 300,000 demand events**. Seeds 42–91; elapsed
  507.32 seconds. There are no claimed 1,000-seed results.
- Additional controls: exact redemption, bounded-premium scaling, finite-size
  pending-order attacks, joint execution, an independently depth-matched curve,
  external-price divergence without retail flow, a finite toxic-inventory sale,
  and 20 executed scaling markets at 2/10/100/1,000 tokens.
- A further check reproduced 60 saved terminal market states (three selected
  seeds in every scenario/architecture) and executed 120 retail portfolio exits
  in forward/reverse order. These are replay validations, not additional
  independent Monte Carlo samples.
- All Phase 2 source hashes and seed distribution summaries were independently
  verified again before writing this report. The manifest is complete. A separate
  small development smoke batch is not pooled into these findings.

## 1. Audit: what survives and what needs qualification

At fixed original coefficients, own slope remains k and cross slope is kλ.
Funded reserve differences telescope, market cap is `2R-p0Q`, and the no-fee
ordering transfer is `kλab`. These are proven conditional properties. The old
equal-capital runs fairly matched backing plus trading cash, but began at different
prices. Their lower relative slippage was not proof of improved depth. For example,
equal-backed initial prices were .335 shared and .186011 independent; both moved
by .01 for a 100-unit trade. Relative slippage divides by those different prices.

One defect was repaired: the old fast constructor accepted underfunding within
1e-9, including a $145 obligation funded with $144.9999999995. It now rejects
strictly lower genesis funding. None of the old default runs used that branch;
they automatically funded the computed requirement. The original source is
preserved for provenance, and the old findings are not silently rewritten.

## 2. Bounded coupling: mathematical result

Use fractions `x_i=q_i/S_i` of each verified immutable authorized supply, with
fixed cohort admission and no arbitrary raw-unit sums:

```
R = sum(a_i x_i+b_i x_i²/2) + gamma X²/(tau+X), X=sum x_i
P_i = a_i+b_i x_i+gamma[1-tau²/(tau+X)²]
raw price = P_i/S_i
H_ij = 2 gamma tau²/(tau+X)³ (i != j)
H_ii = b_i+H_ij
```

The Hessian is positive definite for positive b_i; prices are positive. Global
influence is less than gamma even with many assets. Changing raw denomination
with S leaves every cashflow invariant; exact property tests verify it. This does
not solve Sybil identity or false supply-attestation problems. Only screened,
fixed-capacity cohorts are admitted, at zero newly issued supply, without changing
old coefficients. There is no claim of safe permissionless admission.

Funded mint/burn uses exact potential differences. The rational reference enforces
cash, ownership and reserve equalities exactly. Full redemption returned all
required gross backing. At fixed parameters and .1 issued fraction per token:

| Tokens | Global premium per full claim (cap 2,000) | Bounded backing | Quadratic backing |
| --- | --- | --- | --- |
| 2 | 611.1111 | $866.67 | $900.00 |
| 10 | 1,500.0000 | $5,000.00 | $8,500.00 |
| 100 | 1,983.4711 | $58,181.82 | $535,000.00 |
| 1000 | 1,999.8039 | $598,019.80 | $50,350,000.00 |

The bounded fixed-state reserve scales linearly with n, while the original
quadratic cross term scales as n². **This is an improvement in exposure bounds
and scaling, not evidence of extra executable liquidity.** All parameters stay
fixed within each run. Raw prices inherit the cap divided by S_i.

## 3. Budget fairness and instrument differences

Every sponsor deploys a net $10,000. Every world begins with $136,000 total USDC,
including identical dealer, retail and arbitrage funding. Dealer inventory costs
$1,000 and is paid, and an AMM's $5,000 seed token inventory is also paid. All
starting token/reference prices equal $10,000 **per whole authorized-supply claim**;
this is not one raw memecoin's price. See the full flow derivation in
[PHASE2_DESIGN.md](PHASE2_DESIGN.md).

| Architecture | Sponsor net deployment | World initial USDC | Initial mechanism cash | Paid pool inventory | Creator cash after seeding | Initial genesis mark/cost gain |
| --- | --- | --- | --- | --- | --- | --- |
| independent | $10,000.00 | $136,000.00 | $11,000.00 | $0.00 | $0.00 | $7,333.33 |
| quadratic | $10,000.00 | $136,000.00 | $11,000.00 | $0.00 | $0.00 | $7,333.33 |
| bounded | $10,000.00 | $136,000.00 | $11,000.00 | $0.00 | $0.00 | $6,188.38 |
| weighted | $10,000.00 | $136,000.00 | $5,000.00 | $5,000.00 | $6,000.00 | $0.00 |

The extra $1,000 curve collateral is funded by the dealer's secondary purchase,
not hidden free capital. In an AMM, paid token purchases go to the creator instead.
Those flows conserve the same global starting USDC. The AMM creator's remaining
authorized stock is finite; its undeployed FDV is not treated as LP funding.

The instruments differ: a surface issues funded redemption claims; an AMM trades
existing tokens and LPs hold a residual portfolio. We therefore report curve
operator fee income, sponsor mark changes and AMM LP NAV separately. Collateral
offset by redemption liabilities is never called LP profit. Initial genesis
mark/cost gains are excluded from subsequent sponsor mark changes. Identical
deployed cash budgets do not imply identical claims, genesis asset amounts or
total marked value of undeployed creator inventory. These are comparison limits,
not reasons to ignore the real inventory expense.

## 4. Executable liquidity at aligned starts

Zero-fee controls isolate curve/pool geometry. A $100 reference-notional trade is
.01 of an authorized supply. Sell quotes require owned eligible tokens; the
engine does not permit selling arbitrary unissued creator tokens into a surface.
The last columns show token reference notional within a 1% all-in execution
deviation at the aligned initial price, with zero and 0.3% fees respectively.

| Architecture | Initial cash | Buy $100 token notional: cash paid | Sell $100 notional: cash received | 1% buy depth, no fee | 1% buy depth, fee |
| --- | --- | --- | --- | --- | --- |
| independent | $11,000.00 | $102.18 | $97.82 | $45.83 | $31.99 |
| quadratic | $11,000.00 | $100.67 | $99.33 | $148.96 | $103.96 |
| bounded | $11,000.00 | $101.83 | $98.17 | $54.53 | $38.05 |
| weighted | $5,000.00 | $112.83 | $90.33 | $8.98 | $6.28 |
| hub | $5,000.00 | $125.00 | $83.33 | $4.95 | $3.46 |

The original quadratic has been recalibrated here: b is reduced from
43,636.36 independent to 13,426.57 quadratic to align prices and budgets. The
old statement `H_ii=k` still holds. We must not mislabel this coefficient change
as the effect of sharing reserves at fixed k.

**Falsification control:** a fully independent curve with floor coefficient
8,394.1371, b=13,426.5734, the same $11,000 backing and
same initial $10,000 price executes the $100 buy for
$100.67, matching the recalibrated
quadratic exactly. Its seed quantity differs and is reported. Coupling is not
necessary for this local depth. Parameters and seed distribution are economic
choices; this single counterexample is not a universal optimal curve either.

The bounded curve's modest depth gain over the fixed-floor independent baseline
is similarly calibration-dependent. It does not establish a unique shared-cash
liquidity advantage. No paper cap or rising quote is used as a depth measure.

## 5. Genuine shared AMM: benefit and joint-capacity test

The weighted pool has actual USDC plus paid token inventories. It uses a
constant-mean invariant with half the weight on USDC and equal remaining weights.
A separate hub control holds the **same total cash and token inventory**, with
each token's USDC allocation ring-fenced in a 50/50 pool. See the
[weighted invariant source](https://docs.balancer.fi/whitepaper.pdf) and
[swap definitions](https://docs-v2.balancer.fi/reference/math/weighted-math.html).

At n=10, the weighted pool supplies **1.813×** the hub's zero-fee local
1%-cost buy depth. The initial differential slope ratio is `(n+1)/(2n)=.55`,
approaching a 2× depth gain for many tokens. It is not n copies of the cash pool.
This is a measurable genuine cash-sharing effect under the matched inventory
weights, unlike price spillover on a minting surface.

For a .01-fraction buy in **each** of the ten tokens, the initial one-token quotes
are incompatible simultaneous states. Sequential exact executions give:

| Architecture | Sum of initial individual quotes | Actual joint buy cost |
| --- | --- | --- |
| independent | $1,021.82 | $1,021.82 |
| quadratic | $1,006.71 | $1,021.82 |
| bounded | $1,018.34 | $1,019.20 |
| weighted | $1,128.26 | $1,250.00 |
| hub | $1,250.00 | $1,250.00 |

The weighted and hub pools both require $1,250 for this symmetric joint demand.
The one-token benefit disappears for that balanced portfolio trade. Inventory
depletion and price changes prevent every token from treating the cash as its
own untouched liquidity reserve.

## 6. Toxic admission and socialized LP risk

A fixed pool rejects attaching a new token to existing cash and changing weights
mid-run. Known bad admission prices/unverified supply are also rejected by the
declared screening check. The stress scenario represents weak screening/future
failure: a previously admitted token's external value collapses by 99.99%.

A bot **pays $0.94** for .94 of the authorized issue from the creator at that
collapsed reference price, then sells the real finite stock to the AMM. This
explicit private OTC leg is not constrained by the public dealer's displayed
depth, but is constrained by creator inventory and bot capital. It is not a free
mint into a curve. The surface admits no such creator redemption right.

| AMM | Attacker cash profit after fee/gas | Common cash depleted | Healthy-token quote change | LP final NAV | LP loss vs holding after collapse |
| --- | --- | --- | --- | --- | --- |
| weighted | $1,288.59 | 25.79% | -25.79% | $8,211.45 | -$1,288.60 |
| hub | $473.73 | 9.49% | 0.00% | $9,026.31 | -$473.74 |

The shared pool's loss goes beyond the toxic asset's isolated cash allocation.
Selling that asset lowers the common cash and all other token quotes. The hub
loss is confined to the toxic subpool; healthy quotes are unchanged. Pool balances
stay positive in both: **cash positivity does not mean LP capital was preserved**.
No fixed-dollar LP deposit guarantee exists in this model. Losses are borne by
pro-rata LP shares; for illustrative 20%/30%/50% owners of this shared pool:

| LP share | Original capital | Post-stress NAV share | Total marked loss |
| --- | --- | --- | --- |
| 20% | $2,000.00 | $1,642.29 | -$357.71 |
| 30% | $3,000.00 | $2,463.43 | -$536.57 |
| 50% | $5,000.00 | $4,105.72 | -$894.28 |

This share table is a pro-rata accounting allocation of the executed pool NAV,
not another stochastic LP simulation. No insurance or replenishment is assumed.
It does not model LP withdrawals during the attack. Cash cannot be safely exposed
to arbitrary low-quality assets merely by choosing a common invariant.

## 7. External markets, extraction and trader/LP outcomes

Each token gets independent lognormal reference innovations with per-event
volatility .02; the divergence scenario additionally doubles one token and halves
another, the crash reduces one by 99%, and the joint run halves every reference
mid. All models receive the same shocks and retail intentions. These are chosen
stress assumptions, not empirically fitted return distributions.
Each world has a sponsor, one finite dealer, an aggregate retail wallet, an atomic
arbitrage wallet, a creator and a network-expense account.

The outside dealer has finite cash and paid token inventory. A window's linear
quote curve has finite depth and spread; order flow moves its quote, and inventory
never resets. Two-leg arbitrage must fund both legs, obey ownership/capacity, and
cover a $.01 route expense after fees. Up to two optimized candidate routes are
executed per event. This is a limited, atomic arbitrage policy rather than an
optimal latency-aware adversary or an equilibrium solver.

The following are seed means. Intervals are approximate 95% intervals for the
mean arb cash gain across 50 seeds. AMM LP metrics are intentionally N/A for
surfaces. Every gain here is realized bot cash; reference marking is used for
inventory holders and LP NAV, not to manufacture bot profits.

| Scenario | Architecture | Arb cash gain | 95% mean interval | Retail realized P&L | Retail marked P&L | AMM LP marked P&L | AMM LP vs HODL |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | independent | $513.66 | [$469.73, $557.60] | $15.46 | -$62.80 | n/a | n/a |
| baseline | quadratic | $1,127.54 | [$1,015.42, $1,239.66] | $58.35 | -$59.93 | n/a | n/a |
| baseline | bounded | $595.16 | [$541.91, $648.42] | $17.61 | -$59.66 | n/a | n/a |
| baseline | weighted | $153.30 | [$146.35, $160.25] | -$7.49 | -$154.25 | -$70.96 | -$83.25 |
| divergent | independent | $1,295.60 | [$1,134.81, $1,456.40] | $41.06 | -$16.03 | n/a | n/a |
| divergent | quadratic | $2,929.16 | [$2,582.63, $3,275.70] | $111.68 | -$1.50 | n/a | n/a |
| divergent | bounded | $1,510.78 | [$1,324.71, $1,696.86] | $43.40 | -$12.79 | n/a | n/a |
| divergent | weighted | $245.29 | [$230.64, $259.94] | $23.27 | -$105.15 | $14.28 | -$255.20 |
| crash | independent | $692.46 | [$573.90, $811.02] | $6.96 | -$89.21 | n/a | n/a |
| crash | quadratic | $1,453.59 | [$1,158.62, $1,748.55] | $50.05 | -$77.49 | n/a | n/a |
| crash | bounded | $796.95 | [$657.64, $936.25] | $9.34 | -$85.75 | n/a | n/a |
| crash | weighted | $195.80 | [$174.29, $217.30] | -$26.52 | -$182.38 | -$614.19 | -$134.01 |
| toxic_admission | independent | $695.56 | [$575.59, $815.53] | $6.96 | -$89.52 | n/a | n/a |
| toxic_admission | quadratic | $1,459.04 | [$1,160.56, $1,757.51] | $50.05 | -$77.75 | n/a | n/a |
| toxic_admission | bounded | $800.47 | [$659.53, $941.42] | $9.34 | -$86.06 | n/a | n/a |
| toxic_admission | weighted | $1,587.16 | [$1,564.68, $1,609.64] | -$152.30 | -$276.60 | -$1,952.02 | -$1,466.92 |
| joint_run | independent | $1,043.08 | [$938.22, $1,147.94] | -$52.68 | -$52.68 | n/a | n/a |
| joint_run | quadratic | $1,832.19 | [$1,663.40, $2,000.99] | -$48.57 | -$48.57 | n/a | n/a |
| joint_run | bounded | $1,192.76 | [$1,071.75, $1,313.76] | -$49.38 | -$49.38 | n/a | n/a |
| joint_run | weighted | $247.14 | [$232.62, $261.67] | -$202.82 | -$202.82 | -$2,827.43 | -$333.57 |

Matched-seed **bounded minus independent** arb-profit differences:

| Scenario | Mean difference | 95% paired interval |
| --- | --- | --- |
| baseline | $81.50 | [$71.90, $91.10] |
| divergent | $215.18 | [$187.98, $242.38] |
| crash | $104.48 | [$83.07, $125.90] |
| toxic_admission | $104.91 | [$83.26, $126.56] |
| joint_run | $149.68 | [$132.38, $166.97] |

Bounding influence reduces the quadratic surface's exposure in these settings,
but does not make independent assets track unrelated markets. In the no-retail
2×-one-token reference control, realized bot gains were
$585.36
independent,
$1,407.86
quadratic,
$681.68
bounded and
$96.21
weighted. Finite available claims/depth constrain the opposite-direction route.
Both direction controls and dealer P&L are exported, so extraction is not
automatically attributed to LPs or backing insolvency.

**Important validity limit:** a frictionless market cannot persistently sell
immediately redeemable funded claims below their available redemption value.
Here an exogenous finite dealer can post such a quote and lose stock/cash.
Large residual quote/reference gaps can remain after its inventory is exhausted.
They are not automatically executable arbitrage opportunities. This limits any
economic ranking based on this synthetic reference process, especially crash
cases with puttable claims. It does not invalidate the recorded funded trades or
the cross-derivative/ordering proofs.

**Executed closing control:** reference marks are not assumed to equal available
redemption cash. The following diagnostic replays seeds 42, 77 and 91, verifies
their terminal cash/reserve/P&L against the stored main runs, then actually sells
the retail portfolio through the mechanism. Values are means of those three
selected states and both exit orders, **not** new population estimates:

| Scenario | Architecture | Pre-exit reference-marked P&L | Actual closing cash P&L |
| --- | --- | --- | --- |
| baseline | bounded | -$66.30 | -$22.11 |
| baseline | independent | -$67.72 | -$24.57 |
| baseline | quadratic | -$104.31 | -$9.65 |
| baseline | weighted | -$160.44 | -$215.09 |
| crash | bounded | -$137.33 | -$27.35 |
| crash | independent | -$138.51 | -$29.35 |
| crash | quadratic | -$164.69 | -$24.41 |
| crash | weighted | -$229.16 | -$200.10 |
| divergent | bounded | -$86.76 | $3.02 |
| divergent | independent | -$88.98 | -$1.94 |
| divergent | quadratic | -$124.56 | $27.52 |
| divergent | weighted | -$172.84 | -$176.71 |
| joint_run | bounded | -$47.10 | -$47.10 |
| joint_run | independent | -$53.11 | -$53.11 |
| joint_run | quadratic | -$48.41 | -$48.41 |
| joint_run | weighted | -$203.78 | -$203.78 |
| toxic_admission | bounded | -$138.11 | -$27.35 |
| toxic_admission | independent | -$139.29 | -$29.35 |
| toxic_admission | quadratic | -$165.36 | -$24.41 |
| toxic_admission | weighted | -$326.72 | -$399.12 |

This exposes both effects: funded claims may redeem above a distressed outside
mark; AMM inventory can execute below a favorable paper mark because of price
impact. No simultaneous other holder exits are assumed. The largest remaining
float cap-boundary dust was 1.665e-16 of one
authorized supply. The exit caller respected strict input caps, recorded the
remainder and did not erase it; exact rational surface tests have no such dust.
Raw exit cases are in `retail_exit_checks.csv`.

Worst observed AMM LP marked outcome in this batch was -$3,649.39
(scenario `joint_run`, seed 54). This is a sample extreme,
not a worst-case bound. Fee tokens valued at an internal quote can look valuable
while being toxic externally; the exported `fee_value_at_execution` is only that
internal-mark inventory diagnostic. LP profitability above uses outside-valued
NAV, not paper fee income.

## 8. Ordering attacks remain after bounding

The bounded exact gross transfer, with t=tau+X, is:

```
gamma tau² a b (2t+a+b) / [t(t+a)(t+b)(t+a+b)]
```

It is positive when gamma,a,b are positive. Net profit subtracts proportional
trading fees and network costs; tighter victim payment limits can reject some
sequences. For a=.01, b=.01 in the aligned initial state:

| Architecture | Fee | Attacker net cash gain | Victim extra payment |
| --- | --- | --- | --- |
| independent | 0.0% | $0.00 | $0.00 |
| independent | 0.3% | -$0.61 | $0.00 |
| quadratic | 0.0% | $0.34 | $0.34 |
| quadratic | 0.3% | -$0.27 | $0.34 |
| bounded | 0.0% | $0.02 | $0.02 |
| bounded | 0.3% | -$0.59 | $0.02 |
| weighted | 0.0% | $2.55 | $2.55 |
| weighted | 0.3% | $1.91 | $2.56 |

Small sampled bounded orders lose after the fee; that is not a security proof.
An additional **exact rational funded execution** with a=.6, b=.1, attacker
capital $5,000 and victim capital $20,000 earned
1.344072 USDC after 0.3% fees, before
network expense. Its victim's extra payment was
8.495091 USDC on an initial quote of
$12,633.79; the victim still filled with a **1%**
maximum-payment tolerance. All issuance fractions stayed below 1. Details and
exact-accounting scope are saved in `large_bounded_attack.json`. Bounding limits
the attack's magnitude; it does not eliminate the transfer or guarantee fees do.

## 9. Solvency, conservation and scale

Exact rational surface tests proved equality of required/actual backing on tested
funded paths and complete redemption. The proof is inductive potential-difference
accounting, conditional on the admitted token rules. Float dynamic runs showed
max cash-conservation error 4.075e-10 USDC and max backing absolute error
1.019e-10 USDC. Raw positive surface shortfalls were at most
8.185e-11 USDC. All were within the declared research tolerances; none
is evidence of intentional underfunding being allowed. AMM solvency means honoring
pro-rata inventory ownership, not a fictitious full-dollar guarantee.

Fixed **total** capital scaling tests (100 events each, all four plus the hub):

| Tokens | Executed worlds | Largest per-world elapsed seconds | Max cash error USDC |
| --- | --- | --- | --- |
| 2 | 5 | 0.1418 | 1.16e-10 |
| 10 | 5 | 0.5584 | 1.16e-10 |
| 100 | 5 | 0.2295 | 1.16e-10 |
| 1000 | 5 | 0.3343 | 8.73e-11 |

At fixed total capital, per-asset inventory/depth must shrink as more independent
assets share it. O(1) local surface/pool quote formulas do not remove that economic
constraint. Reports and bot candidate scans are O(n), not O(1); holdings storage
is O(number of wallets × n). These timings test local research computation,
not deployment throughput or robust large-cohort economics.

## 10. What is and is not demonstrated

| Design | Demonstrated property | Unresolved or adverse consequence |
| --- | --- | --- |
| Independent curves | Funded issuance/redemption; no mechanical cross-token quote effects | Parameters/price floors drive depth; external option-value/reference process needs care |
| Original quadratic | Lower local slope is possible after explicit recalibration | Same local depth is reproducible without coupling; external divergence/order transfers and unbounded fixed-shape scaling |
| Bounded surface | Unit invariance, capped global premium, convexity, linear fixed-shape reserve scaling | Coupling transfers remain; no unique liquidity advantage established; screened admission assumptions |
| Shared weighted AMM | Real, paid-inventory local depth gain versus isolated hub at matched seed value | Finite/joint capacity, toxic reserve depletion, LP inventory risk and healthy-token contagion |

None establishes a permissionless, risk-free reserve-sharing advantage. A pooled
AMM may be worth studying for a **pre-screened, exposure-capped asset cohort**
whose LPs explicitly accept inventory risk. Whether its fees compensate that risk
requires calibrated demand, asset-quality assumptions, admission costs and a stated
risk budget; these simulations do not answer it. For independently launched
unvetted memecoins, the present evidence favors retaining financial isolation as
the safety baseline while sharing operational infrastructure.

The bounded potential is useful as an exposure-limited control, not a reason to
force price coupling. No design is defended simply because it was implemented.

## Reproduction and limitations

See [PHASE2_README.md](PHASE2_README.md) for full commands and the data dictionary:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/audit_phase1.py
.\.venv\Scripts\python.exe -m bonding_lab.phase2 --seeds 50 --events 300 --out results/phase2_reproduction
.\.venv\Scripts\python.exe scripts/verify_phase2_exits.py
.\.venv\Scripts\python.exe scripts/build_phase2_report.py
```

The existing Streamlit dashboard was not rebuilt. The new standalone interactive
figures are `results/phase2/research_charts.html`. CSVs and a complete manifest
record the parameters, paid budgets, seeds, hashes and actual outcomes. Exact
extra-attack and report validation metadata are saved next to them.

No real exchanges, contracts, oracle security, transfer-tax/rebase tokens,
borrowing, gas auctions, delayed settlement, token admission attestations, dynamic
weight changes, strategic LP withdrawals, optimal adversary, or real memecoin
calibration were implemented. Screening inputs are assumptions. Input fee
conventions differ slightly between the legacy-style surface (fee on reserve
difference) and the AMM (input fee); zero-fee controls isolate geometry and
fee-inclusive costs show actual implemented cashflows. Seed intervals quantify
only uncertainty within this assumed process. More data cannot turn those
assumptions into proven real-market behavior.
