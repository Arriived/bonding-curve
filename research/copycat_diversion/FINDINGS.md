# Copycat diversion ("vamps feed the leader"): findings

29 October 2026. Off-chain **synthetic research**, not historical market evidence.
Read [DESIGN.md](DESIGN.md) for definitions written before implementation and
[README.md](README.md) for commands, data fields and limitations.

## Clarified objective: whichever token wins

The user clarified that success means concentration on **any enduring ticker
winner**, including a copy. Original survival is not required. The original-
focused ranking and verdict below therefore do not settle that objective.
Read [WINNER_REANALYSIS.md](WINNER_REANALYSIS.md) for the corrected interpretation,
identity-free concentration comparisons and remaining uncertainties. The earlier
analysis is retained for audit; its accounting and measured cash flows stand.

## Earlier verdict, retained with its original scope

**Not viable as a mandatory, permissionless, ticker-defined consolidation mechanism.**

The useful distinction is between a creator/holder transfer, a buyer-owned
portfolio split, and non-redeemable price support. They are not interchangeable
liquidity improvements. The results below rank actual accessible redemption,
who bears the cost, identity capture and incremental adversarial profit against
matched controls. A higher named-leader share alone is not sufficient evidence.

Buyer-owned routing to an independently verified original remains a conditional
product hypothesis: the buyer retains both funded assets. The present ticker
rules are not an identity oracle, and large automatic leader orders expose the
buyer to ordering extraction. Treasury ownership is a different economic right.
Display/provenance steering is a control worth validating with real users; its
assumed steering percentages are not observed behavioral effectiveness.

The default first-launch/buyer-owned 5% setting increased original accessible-
liquidity share by **+0.98 pp** and its time-averaged
accessible redemption by **$923.33** in
confirmation. Total accessible redemption changed by
-$228.53, aggregate retail cash P&L by
-$134.26, and confused-buyer mean cash P&L by
$0.91. This is real redistribution of funded
claims, with mixed distributional effects, rather than new liquidity creation.

The largest confirmed financial share increase was
`volume5_burn_10pct_exact_fixed_badge0`: +2.46 pp,
with $4,219.37 more original
accessible redemption and a -$56.22
change in mean cash P&L for confused buyers. Its fixed-volume identification also benefits
from the original's deterministic early-address head start. The conditional
buyer-owned candidate should not be dismissed using a restricted-control spam
comparison; the stronger comparison below materially changes that attribution.

## What actually ran

- **138 project tests passed**; reference paths reuse the original Decimal
  independent engine and the existing curve fee. Cash funding, payouts, burn
  accounting, first-address volume, dwell/cooldown, evasion, and the repeated
  budget-depletion failure have regression coverage.
- Main grid: **322 settings**, including the 144 leader/form/rate core
  and declared robustness/ownership/badge controls. It is not every possible
  combination of all knobs.
- Attack policies were selected on **[11, 22]**, 160
  buyer arrivals, separately for each variant/family. Search export contains
  **17,694 candidate evaluations** (including reused abstention scores).
- Screening used **6 distinct held-out seeds**,
  240 arrivals per market. Confirmation used **30
  fresh seeds** and 480 arrivals for 12
  selected settings. Attack policies were not retuned on these confirmation seeds.
- The main workflow executed **45,412 market calls /
  8,923,360 organic-arrival events**, including training,
  matched counterfactuals and recorded examples, in 4863.9
  elapsed seconds (including the preserved serial training prefix). Deterministic
  worker processes completed the remaining calls, after bit-identical serial/
  parallel validation. Exact-call cache hits and repeated idle policies are not
  extra independent observations.
- 216 independent funded large-order response searches validated
  realized cash against the analytic prediction, with fees, gas, minimum output
  and abstention. Separately searched small-badge controls and independently
  optimized zero-tax confirmation opponents are also saved.
- Individual no-attack panels add 540
  source-checked market calls and 172,800 matched wallet
  records, reproducing confirmed retail totals. Wallets are not independent markets.
- A further 1,296 calls broadened buyer-route
  spam/evasion controls to voluntarily buy leader-token portfolios, using the
  original training seeds and untouched confirmation seeds.
- 43 badge settings were independently retrained/retested
  with steering disabled until an elected leader exists. This corrects the
  original-to-undefined-leader fallback for delayed badge rules, with
  6,726 additional market calls.
- Source hashes, completion states and key seed summaries were checked again
  before this report. The failed development search is preserved and excluded.

All stages span 240 simulated minutes. Total intended organic notional is $600k,
organic starting capital $1m, and the attacker has $1.1m **across** its aliases.
Initial world funding is $2.225m, unchanged by the variant. Each organic arrival
has its own funded wallet; scheduled and terminal exits determine actual P&L.
The original launches first; 14 ordinary copies arrive later, and attack policies
can launch a main plus up to 24 additional copies. Pre-squatting before the true
original is excluded. Confusion is 35%; informed share 20%; launch cost $10;
network expense $.05 per curve operation; curve fee .3%.

Training, screening and confirmation have different arrival resolution/per-wallet
cash limits. They are separate experiments; do not pool their returns or interpret
their differing attack opportunities as statistical replication of one design.
This matters particularly for front-running large orders.

## Exact results: what the mechanism actually pays for

Let rho=(1-f)/(1+f), budget B, diversion D=alpha B.
Every token still has `p_i=p0+k q_i`, with unchanged own slope k and zero
cross-token price derivative. Any consolidation comes from redirecting funded
order flow or attention; no variant creates a new shared reserve or deeper
curve merely by attaching a ticker label.

1. **Creator/holder cash transfers** leave `rho(1-alpha)B` as an isolated copy
   position's immediate redemption versus `rho B` without diversion. The recipient
   gets D; the leader's curve does not automatically receive new backing.
2. **Buyer-owned routing** gives the same buyer two fully funded positions.
   Combined immediate redemption is `rho B` before network expense, if nobody
   else trades. It reallocates exposure, rather than giving away that whole share
   of the buyer's capital. Subsequent relative token performance/order matters.
3. **Never-selling treasury versus buy-and-lock:** their public price/redemption
   paths match under the tested policies. Treasury retains a redemption option and
   overhang risk; the locked address does not. Buying tokens for existing holders
   is already the holder-payout variant, not a third ownership interpretation.
4. **Literal reduction of pricing supply** restores the pre-buy price. Retained
   collateral becomes a surplus with no invented holder payout right. Treating
   that surplus as deeper usable leader liquidity would be a measurement error.
5. **Self-paid creator diversion is not revenue:** a funded own-copy round trip
   nets `-(1-rho)(1-alpha)B`, before launch/gas. Wallet splitting cannot make
   self-paid cash an outside subsidy.

If an actor captures fraction phi of outsiders' copy spending V through direct
diversions, break-even requires
`phi alpha V + other realized trading gains > launches + election cost + wash losses`.
For phi=1 and 25 actor tokens, launch fees alone require outside spending of
$25,000/$8,333/$5,000/$2,500 at 1%/3%/5%/10%. These are conditional arithmetic,
not a claim about organic adoption; own washing is excluded from V.

Quoted-cap threshold races distinguish **reusable bankroll** from net expense:

| Cap threshold | Entry cash required | No-external-trade round-trip fees | Outside taxed spend to cover costs at 5% |
| --- | --- | --- | --- |
| $100,000.00 | $50,308.34 | $300.95 | $6,220.94 |
| $1,000,000.00 | $502,001.25 | $3,003.00 | $60,261.97 |

The calculation includes the $10 launch and $.10 two-transaction expense in its
break-even spending. Holding/market interaction can add cost or profit; no borrowing
or capital opportunity cost is modeled. A fixed title may survive its qualifying
pump being fully unwound. That is a financial entitlement design issue even when
the reserve remains solvent.

## Ranking table: held-out finalists

Rows are separately evaluated configurations. Share changes are percentage points
of time-averaged **actual original** private-holder redemption, relative to the
same rule/matcher without diversion. Dollar columns expose denominator-only
"consolidation." Attack Δ compares each configuration with the matched control's
**independently training-selected** policy in the same family, then takes the
worst tested family mean. Buyer-route spam/evasion use the expanded voluntary-
portfolio control below. This is a stress envelope, not a globally optimal policy.

| Configuration | Δ original share | Δ original accessible $ | Δ total accessible $ | Δ confused buyer mean P&L | Δ fixed vamper P&L | Worst mean extra attack profit | Minimum original-leader time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| first_control_0pct_exact_fixed_badge75 | +18.65 pp | $21,242.22 | -$2,036.92 | -$43.13 | -$1,845.93 | $0.00 | 100.0% |
| volume5_burn_10pct_exact_fixed_badge0 | +2.46 pp | $4,219.37 | $1,934.69 | -$56.22 | -$578.74 | $81.15 | 97.9% |
| volume30_burn_10pct_exact_fixed_badge0 | +2.44 pp | $4,219.37 | $1,960.67 | -$57.08 | -$578.74 | $53.95 | 97.9% |
| volume120_burn_10pct_exact_fixed_badge0 | +2.44 pp | $4,219.37 | $1,963.92 | -$57.29 | -$578.74 | $80.34 | 97.9% |
| volume120_buyer_10pct_exact_fixed_badge0 | +1.97 pp | $1,847.19 | -$450.76 | $1.69 | -$59.99 | $7.38 | 97.9% |
| held5_buyer_10pct_exact_fixed_badge0 | +1.61 pp | $1,739.29 | -$274.77 | $0.42 | -$201.68 | $5,945.84 | 0.0% |
| volume120_holders_10pct_exact_fixed_badge0 | +1.51 pp | $0.00 | -$2,437.05 | -$57.02 | -$578.69 | $766.59 | 97.9% |
| volume120_creator_10pct_exact_fixed_badge0 | +1.51 pp | $0.00 | -$2,437.05 | -$61.15 | -$578.69 | $5,793.63 | 97.9% |
| volume30_treasury_exit_5pct_exact_fixed_badge0 | +1.24 pp | $2,148.60 | $1,022.41 | -$30.77 | -$289.41 | $36.59 | 97.9% |
| threshold100000_buyer_10pct_exact_fixed_badge0 | +1.03 pp | $1,268.09 | -$120.65 | -$5.06 | -$128.14 | $6,785.01 | 0.0% |
| first_buyer_5pct_exact_fixed_badge0 | +0.98 pp | $923.33 | -$228.53 | $0.91 | -$31.08 | $80.37 | 100.0% |
| first_burn_supply_5pct_exact_fixed_badge0 | +0.75 pp | $0.00 | -$1,230.87 | -$30.79 | -$289.41 | $0.00 | 100.0% |

The complete screen ranking and leader/form frontier are in `results/screen_ranking.csv`
and `results/leader_form_screen_frontier.csv`; every rate and window is retained.
No apparent winner is certified safe merely because this finite search found
no profitable intervention. Thresholds that rarely choose any leader are not
credited as successful protection.

| Leader rule | Research interpretation |
| --- | --- |
| First launched | Clearest candidate for buyer-owned routing **when chronology is an acceptable identity rule**. Original correctness is assumed through launch order; near-ticker groups still fragment, and original-holder/retail welfare is mixed. |
| Cap threshold | A reversible pump can acquire a persistent entitlement and informed flow. The tested capture policies materially worsen outcomes; large qualifying bankroll is not the same as permanent attack expense. |
| Sustained cap lead | Dwell adds time/capital exposure, but tested races still capture the title and profit. Longer windows can also leave the title undefined for much of a short viral event. |
| Distinct-address volume | Fixed early selection performed better in this tape, where funded original snipers qualify first. It is not an identity or Sybil-resistance result; flipping and late qualification need separate safeguards. |

Cash creator/holder forms do not add original-curve dollars. Buy-and-lock produces
larger measured original claims for remaining holders at copy buyers' expense.
Treasury exit retains the pre-exit consolidation statistic while later reducing
retail cash; it cannot be credited with both permanent locking and recoverable
protocol capital. Buyer ownership is the least confiscatory financial form here.

## Adaptive attacks: best found within each policy class

Each family includes no action. Policies search actual funding, timing, residual
inventory, aliases/spam counts and ticker strings. Volume attacks use funded
addresses; held-cap attacks keep a real quote lead; front-runs optimize against
the relevant payout or leader leg. Fixed-title impossibilities and creator-only
front-runs can optimally abstain. The worst-family display below chooses a
configuration *after* evaluating the stress set; use the individual per-setting
distributions in `confirmation_summary.csv` for inference.

| Attack | Setting with largest mean extra gain | Mean cash profit | Median | Mean Δ vs same-policy no-tax control | 95% Δ interval | Profitable runs | Maximum observed cash profit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| race | threshold100000_buyer_10pct_exact_fixed_badge0 | $26,296.56 | $23,802.11 | $6,785.01 | [$5,067.11, $8,502.91] | 90.0% | $66,646.95 |
| spam | first_buyer_5pct_exact_fixed_badge0 | $5,274.07 | $5,442.27 | $664.92 | [$596.39, $733.45] | 100.0% | $9,730.35 |
| evasion | volume120_creator_10pct_exact_fixed_badge0 | $11,120.67 | $10,894.67 | $5,793.63 | [$5,461.38, $6,125.88] | 100.0% | $16,891.61 |
| flip | threshold100000_buyer_10pct_exact_fixed_badge0 | $26,296.56 | $23,802.11 | $6,785.01 | [$5,067.11, $8,502.91] | 90.0% | $66,646.95 |
| front | volume120_holders_10pct_exact_fixed_badge0 | $155.44 | $137.82 | $155.44 | [$115.65, $195.23] | 100.0% | $320.15 |

The search space is disclosed in `attacks.py` and all candidate scores in
`strategy_search.csv.gz`. Search is not globally exhaustive, including possible
joint attacks, longer strategies, more spellings or different identity systems.
Search-selection uncertainty is not included in the displayed mean intervals.
Ordinary copy-launch trading gains already available without diversion are
separated from incremental diversion gains; the fixed single-copy vamper is
reported separately from the adaptive, well-funded attacker.
In particular, adding visible copies increases an actor's share of uniform
confused impressions even in the no-diversion model. That attention assumption
can make copy spam profitable on its own; the matched increments distinguish
that source of profit from collecting a new diversion entitlement.

### Control-policy breadth changes the spam attribution

The main search's zero-tax copy-spam strategy bought only its copy positions.
Buyer-owned diversion also gave that actor a leader position. It would be unfair
to describe every resulting profit difference as a new, unreplicable exploit.
The additional control searches voluntary leader splits of 0%,1%,3%,5%,10% on
the actor's own buys, charging the same fees/gas. Outsider buys remain undiverted.
It trains independently for spam/evasion on the same original training seeds:

| Buyer-route setting | Family | Selected control split | Variant mean cash profit | Expanded control mean | Mean difference | 95% difference interval |
| --- | --- | --- | --- | --- | --- | --- |
| first_buyer_5pct_exact_fixed_badge0 | spam | 10.0% | $5,274.07 | $6,207.67 | -$933.60 | [-$985.17, -$882.03] |
| first_buyer_5pct_exact_fixed_badge0 | evasion | 10.0% | $5,915.24 | $5,834.86 | $80.37 | [-$11.78, $172.53] |
| held5_buyer_10pct_exact_fixed_badge0 | spam | 0.0% | $4,301.11 | $4,609.15 | -$308.04 | [-$360.33, -$255.75] |
| held5_buyer_10pct_exact_fixed_badge0 | evasion | 0.0% | $6,241.12 | $5,327.04 | $914.08 | [$679.58, $1,148.58] |
| threshold100000_buyer_10pct_exact_fixed_badge0 | spam | 0.0% | $4,438.24 | $4,609.15 | -$170.92 | [-$218.93, -$122.90] |
| threshold100000_buyer_10pct_exact_fixed_badge0 | evasion | 0.0% | $5,327.04 | $5,327.04 | $0.00 | [$0.00, $0.00] |
| volume120_buyer_10pct_exact_fixed_badge0 | spam | 0.0% | $4,285.99 | $4,609.15 | -$323.16 | [-$375.06, -$271.27] |
| volume120_buyer_10pct_exact_fixed_badge0 | evasion | 0.0% | $5,196.95 | $5,327.04 | -$130.09 | [-$178.73, -$81.45] |

The apparent default first/5% **spam** uplift against the narrow control does not
survive this stronger comparison. It is not evidence of a novel copy-spam exploit.
This is a conservative attribution check that broadens the control's options;
it does not symmetrically optimize every possible portfolio under the diversion
variant or establish a global best response. Both sets of records are retained.

### Large pending copy buys: controlled best-response search

Small-wallet Monte Carlo non-profitability is not a proof against this attack.
For a diverted buy budget D, the victim's leader quantity is the exact inverse
at the front-run price p+kb. Gross attacker gain is `k b d(b)`, not a quantity
assumed unchanged by the attack. Holder dividends instead give
`D b/(q+b)`, less round-trip fees. Pure creator cash transfer gives no such
inventory-buy reward. Literal supply destruction cancels the price increment.

The funded control uses leader caps $2k/$100k/$1m, copy buy budgets
$10k/$100k/$500k, all four rates and the ownership/burn interpretations. Each
response compares 65 golden-section iterations, 100 logarithmic sizes and idle.
The leader-buy leg enforces at least 98% of its pre-attack output. Maxima within
this **controlled grid**, including trading fees and $.10 attacker network cost:

| Form | Best cash profit | Leader cap | Copy buy budget | Rate | Cash committed | Positive cases |
| --- | --- | --- | --- | --- | --- | --- |
| creator | $0.00 | $2,000.00 | $10,000.00 | 1.0% | $0.00 | 0 |
| holders | $45,375.49 | $2,000.00 | $500,000.00 | 10.0% | $257,238.40 | 25 |
| buyer | $1,662.52 | $2,000.00 | $500,000.00 | 10.0% | $301.50 | 25 |
| treasury | $1,662.52 | $2,000.00 | $500,000.00 | 10.0% | $301.50 | 25 |
| burn (lock) | $1,662.52 | $2,000.00 | $500,000.00 | 10.0% | $301.50 | 25 |
| burn (supply) | $0.00 | $2,000.00 | $10,000.00 | 1.0% | $0.00 | 0 |

These are executed synthetic stress cases, not estimated real-world probabilities.
They isolate front-running of the **leader leg**. Public independent-curve buys
are also order-sensitive; this search does not compare the best combined
copy-and-leader sandwich with the best sandwich of an undiverted copy order.
Leader-leg extraction therefore establishes an exposure, not a measured increase
in total MEV over every possible independent-curve control strategy.
The treasury-never-sells and buy-and-lock response agree; a later treasury sale
would create overhang. Existing holders receiving cash is a snapshot entitlement
and can be bought just before the payout. The contracts' continued solvency does
not prevent any of these transfers from a paying copy buyer.

## Identity, ticker matching and copy spam

The headline leader is the leader of the original's matching group. Near-ticker
groups can have their own attacker leaders; they remain in the campaign's total
liquidity/volume denominator. `attacker_led_groups_liquidity_share_time_mean` and
`original_matching_group_share_time_mean` expose that fragmentation instead of
quietly excluding unrecognized copies. All spelling candidates are assumed
semantically related in this synthetic market, including out-of-radius strings.

| Rule among confirmed cases | Mean original-leader time | Mean defined-leader time | Final real original | Final attacker | Final ordinary copy | Final undefined |
| --- | --- | --- | --- | --- | --- | --- |
| first | 100.0% | 100.0% | 100.0% | 0.0% | 0.0% | 0.0% |
| threshold | 50.3% | 89.9% | 60.0% | 40.0% | 0.0% | 0.0% |
| held | 57.5% | 95.5% | 60.0% | 40.0% | 0.0% | 0.0% |
| volume | 97.9% | 97.9% | 100.0% | 0.0% | 0.0% | 0.0% |

First-launch identification is correct **by the launch-order assumption** here;
it does not establish real authorship. Fixed volume selection also benefits from
an early original with multiple snipers/organic addresses. This is not evidence
of Sybil-resistant identity. Held caps can be supported with recoverable capital;
distinct wallet addresses can be bundled; a cooldown delays changes but can
preserve a captured title while its inventory is unwound.
In this tape, the original has four funded sniper addresses before age five;
fixed distinct-wallet election can lock it before any post-launch attacker token
reaches minimum age. Its low measured capture rate relies on that head start,
not on the distinct-address score being a Sybil-resistant identity test.

Exact matching is evaded by case or whitespace, case folding by other spellings,
and the declared fuzzy rule by out-of-radius/homoglyph candidates. The economic
success of an evasive string depends on human confusion: equal synthetic
visibility is an assumption, not evidence that ELONXX is as persuasive as ELON.
Fuzzy false positives against unrelated legitimate tickers were not modeled.
Pure string rules cannot certify which independently launched asset is authentic.

## Who pays, who gains, and timing

These form-level rows are **descriptive averages across selected settings**, not
one pooled treatment or a causal estimate. Cohorts are defined by purchase time
and intended leader/copy target; buyer-owned diversion can add a second asset.
P&L is actual final cash after funded exits, fees, launch/network costs and cash
payments. The matched increments and configuration-specific cohort distributions
are provided in the CSVs.

| Form | Creator cash diversion | Holder cash dividends | Original creator P&L | Δ confused buyer mean | Early leader mean | Late leader mean | Early copy mean | Late copy mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| creator | $9,853.10 | $0.00 | $19,704.70 | -$61.15 | $129.44 | -$386.09 | $41.04 | -$383.16 |
| holders | $0.00 | $9,853.10 | $11,730.49 | -$57.02 | $165.23 | -$380.96 | $46.86 | -$381.66 |
| buyer | $0.00 | $0.00 | $10,647.36 | -$0.51 | $114.55 | -$386.06 | $128.46 | -$345.37 |
| burn (lock) | $0.00 | $0.00 | $11,431.07 | -$56.86 | $150.67 | -$362.56 | $44.50 | -$379.08 |
| burn (supply) | $0.00 | $0.00 | $10,546.28 | -$30.79 | $271.05 | -$386.09 | $83.89 | -$363.01 |
| treasury (exit=first) | $0.00 | $0.00 | $10,412.90 | -$30.77 | $126.16 | -$397.65 | $84.99 | -$364.55 |

Worst observed confirmed actor cash profit was $66,646.95
(`threshold100000_buyer_10pct_exact_fixed_badge0`, family `race`, seed 1009). The worst
observed confused-buyer *cohort mean* was -$253.42
in `first_control_0pct_exact_fixed_badge75`, seed 1023. These are sample
extrema, not bounds or individual-buyer worst cases. Creator/holder receipts
include their entitlements; external attacker receipts separately exclude
self-funded payouts. No capital is created by the independent reserve potential.

Matched wallet panels hold the *control's confused-wallet membership* fixed.
They therefore also capture buyers a badge steers out of confusion, avoiding a
changing-cohort comparison. No-attack per-buyer mean cash changes, with intervals
across seeds rather than pooled wallet observations:

| Configuration | Fixed confused cohort mean Δ | 95% mean interval | Seeds |
| --- | --- | --- | --- |
| first_burn_supply_5pct_exact_fixed_badge0 | -$30.79 | [-$31.72, -$29.86] | 30 |
| first_buyer_5pct_exact_fixed_badge0 | $0.91 | [$0.11, $1.72] | 30 |
| first_control_0pct_exact_fixed_badge75 | -$23.79 | [-$39.23, -$8.36] | 30 |
| held5_buyer_10pct_exact_fixed_badge0 | $0.42 | [-$1.13, $1.98] | 30 |
| threshold100000_buyer_10pct_exact_fixed_badge0 | -$5.06 | [-$6.20, -$3.93] | 30 |
| volume120_burn_10pct_exact_fixed_badge0 | -$57.29 | [-$59.22, -$55.35] | 30 |
| volume120_buyer_10pct_exact_fixed_badge0 | $1.69 | [$0.14, $3.24] | 30 |
| volume120_creator_10pct_exact_fixed_badge0 | -$61.15 | [-$63.07, -$59.23] | 30 |
| volume120_holders_10pct_exact_fixed_badge0 | -$57.02 | [-$58.95, -$55.09] | 30 |
| volume30_burn_10pct_exact_fixed_badge0 | -$57.08 | [-$58.96, -$55.20] | 30 |
| volume30_treasury_exit_5pct_exact_fixed_badge0 | -$30.77 | [-$31.73, -$29.81] | 30 |
| volume5_burn_10pct_exact_fixed_badge0 | -$56.22 | [-$58.21, -$54.22] | 30 |

Across these no-attack individual panels, the worst individual realized cash P&L
was -$2,072.97; the worst individual matched
change was -$4,330.48. Those are distinct
sample extrema and need not be the same wallet. Full early/middle/late, intended
leader/copy, median, tail and matched-change records are in
`wallet_panels/wallets.csv.gz`, `seed_cohorts.csv` and `cohort_summary.csv`.

## Display-only comparison at low steering shares

**Badge audit:** the original simulator lets badge-selected impressions fall back
to the original when no leader qualifies. That grants delayed-rule badges useful
information before the election. Those raw records are preserved, but are not
used as evidence for a delayed elected badge. `strict_badges/` retrains all 27
high-steering and 16 low-steering controls with zero badge steering until a
leader is defined; informed traders retain their explicitly assumed original
fallback. The table below uses these strict runs. First-launch badges always
have a leader, and a regression test confirms their paths are identical.
The main screen ranking retains the legacy delayed-badge rows for audit; the
confirmed badge finalist is first-launch and is unaffected. Do not pool the two
definitions or use legacy rows as proof of an elected badge's effectiveness.

A 25% badge is not a fair substitute for assuming a 1% diversion has the same
behavioral reach. The separate controls below therefore also use nominal
steering shares of 1%,3%,5%,10%, independently searched on the training seeds.
Steering probability and dollar allocation are still different interventions,
so these are transparent scenarios, not empirically matched persuasion costs.

| Leader rule | Assumed badge steering | Δ original share | Δ original accessible $ | Δ total retail P&L | Δ remaining confused-buyer mean | Δ fixed vamper P&L |
| --- | --- | --- | --- | --- | --- | --- |
| first | 1.0% | +0.14 pp | $92.37 | -$25.80 | -$1.55 | $0.00 |
| first | 3.0% | +1.09 pp | $1,030.51 | $60.20 | -$2.60 | $0.00 |
| first | 5.0% | +1.25 pp | $1,268.00 | $165.93 | -$2.25 | $0.00 |
| first | 10.0% | +2.14 pp | $2,118.21 | $412.17 | -$2.91 | -$34.31 |
| held | 1.0% | +0.02 pp | $25.81 | -$17.38 | -$0.86 | $0.00 |
| held | 3.0% | +0.46 pp | $507.62 | $39.91 | -$2.22 | $0.00 |
| held | 5.0% | +0.62 pp | $745.11 | $145.64 | -$1.87 | $0.00 |
| held | 10.0% | +1.40 pp | $1,552.15 | $337.58 | -$2.76 | -$34.31 |
| threshold | 1.0% | +0.02 pp | $25.81 | -$17.38 | -$0.86 | $0.00 |
| threshold | 3.0% | +0.46 pp | $507.62 | $39.91 | -$2.22 | $0.00 |
| threshold | 5.0% | +0.62 pp | $745.11 | $145.64 | -$1.87 | $0.00 |
| threshold | 10.0% | +1.40 pp | $1,552.15 | $337.58 | -$2.76 | -$34.31 |
| volume | 1.0% | +0.14 pp | $92.37 | -$25.80 | -$1.55 | $0.00 |
| volume | 3.0% | +1.09 pp | $1,030.51 | $60.20 | -$2.60 | $0.00 |
| volume | 5.0% | +1.25 pp | $1,268.00 | $165.93 | -$2.25 | $0.00 |
| volume | 10.0% | +2.14 pp | $2,118.21 | $412.17 | -$2.91 | -$34.31 |

These controls grant no creator/holder entitlement and no mandatory secondary
leader order. They still depend on leader identification and assumed user
response, and a manipulable badge can steer users toward an attacker too.
Badge steering also changes which wallets remain confused: that column compares
the remaining confused cohorts, not the same individuals' causal treatment effect.
The total-retail column retains the same funded population across each pair.
Verified provenance versus a financially elected badge is an untested product
choice. A field/user study would be needed to quantify actual confusion reduction.

For the same six screening seeds, first-launch buyer routing and first-launch
display controls at equal **nominal** percentages were:

| Intervention | Nominal rate | Δ original share | Δ original accessible $ | Δ total retail P&L |
| --- | --- | --- | --- | --- |
| Buyer-owned diversion | 1.0% | +0.21 pp | $202.78 | $0.10 |
| Display steering | 1.0% | +0.14 pp | $92.37 | -$25.80 |
| Buyer-owned diversion | 3.0% | +0.64 pp | $608.32 | $5.34 |
| Display steering | 3.0% | +1.09 pp | $1,030.51 | $60.20 |
| Buyer-owned diversion | 5.0% | +1.07 pp | $1,013.83 | $8.05 |
| Display steering | 5.0% | +1.25 pp | $1,268.00 | $165.93 |
| Buyer-owned diversion | 10.0% | +2.14 pp | $2,027.48 | $8.31 |
| Display steering | 10.0% | +2.14 pp | $2,118.21 | $412.17 |

This is a within-stage comparison, avoiding the different confirmation wallet
sizes. A steering probability is still not the same intervention as a dollar
allocation fraction. The display scenario's favorable results are conditional
on those behavioral probabilities, not proof of real-world persuasion dominance.

## Conservative interpretation and conditions

- Creator/holder payments are distributions, not automatic leader-reserve deposits.
  A higher reserve share from draining copies is not new absolute liquidity.
- Buyer-owned splitting is the closest variant to the stated consolidation goal
  while preserving the buyer's funded claims. It requires justified leader identity,
  explicit ownership/consent, output protection and an ordering policy before a
  safety claim. Those mitigations are conditions to test, not proven fixes here.
- A never-selling treasury is close to permanent locking, with additional future
  redemption/overhang risk. Literal supply burn is different and mainly leaves
  a surplus rather than maintaining the funded buy's price effect.
- A quoted-cap or address-volume title is not proof of authenticity. Fixed titles,
  flippable titles and cooldowns trade different capture/entrenchment risks.
- Any finite matching boundary can leave semantic copies outside the levy. If
  confused demand migrates there, the scheme can create royalty farms or evasion
  incentives instead of one authentic liquidity pool.

The result does not establish that every opt-in portfolio-split product is bad,
nor that every real memecoin market behaves like these wallets. It does separate
the original consolidation claim from irreversible transfers, selection capture,
predictable-order MEV and simple display steering. The general mandatory mechanism
has not earned a permissionless safety or welfare claim from these experiments.

## Accounting evidence and limits

Largest recorded cash-conservation error across screen/confirmation:
8.84756e-09 USDC; largest backing error 1.1053e-08 USDC; minimum wallet cash
0 USDC. These float discrepancies are scoped to the research tolerance;
the reference ledger enforces exact Decimal funded accounting. The funding-boundary
defect found during development was fixed and regression-tested, not suppressed.
Residual unprofitable-to-redeem token dust is exported; it is not valued as cash.

Mean intervals use seed-level t critical values (screen n=6,
confirmation n=30); attack success intervals use Wilson
binomial intervals. Quantiles and minima/maxima are in the summaries. These quantify
uncertainty inside this assumed process, not model uncertainty or global attack
optimality. Ranked settings/families involve selection; per-family intervals do
not correct for that selection. Screening and confirmation are never pooled.

The model has no external exchange, supply allocations, real meme utility,
endogenous demand elasticity, identity attestations, pre-squatting, latency race,
gas auction or enforcement against other launchpads. It assumes atomic routing
and publicly observable pending large orders. All participants are funded and
own what they sell. Confirmation has more smaller wallets than training; the
large-order control prevents treating that wallet-size choice as an MEV defense.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=research/copycat_diversion/reproduce/validation.xml
.\.venv\Scripts\python.exe scripts/copycat_parallel.py --out research/copycat_diversion/reproduce/results --workers 6
.\.venv\Scripts\python.exe scripts/copycat_controlled_attacks.py --out research/copycat_diversion/reproduce/controlled
.\.venv\Scripts\python.exe scripts/copycat_badge_controls.py --out research/copycat_diversion/reproduce/badge_controls
.\.venv\Scripts\python.exe scripts/copycat_confirmation_controls.py --study research/copycat_diversion/reproduce/results --out research/copycat_diversion/reproduce/confirmation_controls --all-controls --workers 6
.\.venv\Scripts\python.exe scripts/copycat_wallet_panels.py --study research/copycat_diversion/reproduce/results --out research/copycat_diversion/reproduce/wallet_panels --workers 6
.\.venv\Scripts\python.exe scripts/copycat_portfolio_controls.py --base research/copycat_diversion/reproduce --workers 6
.\.venv\Scripts\python.exe scripts/copycat_strict_badges.py --out research/copycat_diversion/reproduce/strict_badges --workers 6
Copy-Item research/copycat_diversion/DESIGN.md,research/copycat_diversion/README.md -Destination research/copycat_diversion/reproduce
.\.venv\Scripts\python.exe scripts/build_copycat_report.py --base research/copycat_diversion/reproduce --verdict not_viable
```

The standalone plots are `results/research_charts.html`. All candidate definitions,
chosen policies, seed records, cohorts, examples and manifests are included. The
fresh bundle paths preserve the original evidence. The verdict flag records the
research judgment after inspection; it does not alter statistics. See README for
smaller smoke runs and configurable
confusion, informed share, attacker budget, launch fee and network expense.
