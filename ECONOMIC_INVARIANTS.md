# Narrative consolidation: accounting and falsification invariants

Phase 1, 30 October 2026. These are requirements for the next implementation.
The Phase 1 validation script checks only the explicitly labeled arithmetic
witnesses and preservation evidence; it does not validate an unbuilt A–D engine.

## 1. Conservation, ownership and atomicity

Let W be all wallet quote balances, R_i actual candidate backing, E refundable
escrow, F unspent fee-support cash, P accrued protocol fees not already in W,
C accrued creator fees not already in W, and N modeled external/network cash
not already in W. Physical custody and economic ownership are separate. Then:

```
sum(W) + sum(R_i) + E + F + P + C + N = initial world quote + explicit new endowments
```

Every account appears once. If an external dealer or network is in W, omit its
duplicate category. External endowment changes must be common across matched
worlds. In the primary closed-world experiment they are zero after initialization.
Movement between two platform accounts creates no net external deposit.

For each candidate, outstanding pricing supply equals all owned curve-issued
claims, including market/settlement escrow and locked protocol claims. A burn
either cancels an owned redemption claim and changes pricing supply consistently,
or locks the claim without changing supply. These have different economics.
Candidate reserves cannot fund another candidate unless owned claims are validly
redeemed or a separate preauthorized reserve rule changes the instrument.

No negative cash, inventory, outstanding supply, refund liability or fee balance.
Creator allocations, pool inventory, collateral donations, loans and flash
capital cannot appear unfunded. Borrowing, if introduced, requires an actual
lender, debt, interest, repayment and collateral liquidation path. It is disabled
in the primary comparison.

Validate complete transaction feasibility before mutation. Unauthorized winner
replacement, underfunding, expiry and breached output limits reject atomically.
Submitting an actually failed transaction may pay a separately authorized network
cost; refusal before submission does not. Finalization, claim and refund calls
are idempotent. Replay yields the same owners, balances and election outcome.

## 2. Independent curve accounting

For `p=a+bq`, `R(q)=aq+bq²/2`, a buy d adds
`C=pd+bd²/2` to backing and charges fees separately. A redemption d removes
`V=pd-bd²/2` from backing, returns V minus fees, and burns exactly the redeemed
claims. Paid genesis issuance is subject to the same funding requirement.

```
actual_backing_i = R_i(outstanding_i) + explicit_unencumbered_buffer_i
market_cap_i = p_i * outstanding_i
market_cap_i = 2 R_i - a_i q_i     (no extra buffer)
```

Market cap is not collateral. Aggregate full redemption releases R(q) gross,
not cap. A buffer needs a named owner and withdrawal rule; it is not automatically
accessible to holders. An AMM variant instead tracks finite actual inventories
and LP residual ownership; curve redemption solvency is not its liability model.

**Arithmetic witness:** a=.01, b=.0001, q=1,000 gives R=60 and cap=110. Two
500-token holders dividing full terminal backing receive 30 each before fees.
If early redemption is allowed, the first 500-token exit receives 42.50 and the
second 17.50. Aggregate redemption remains 60. Identical holder token balances
do not imply identical acquisition costs. The example establishes exit-order
incentives, not a measured probability of a run.

## 3. Fees, routing and migration

Fee-support spending debits F and credits exactly the market principal, named
fees and network cost. Its purchased inventory belongs to the support fund or
the explicitly declared recipient. A second fee on that buy is a real funded
expense. Support spending cannot recursively create more available cash than
was earned. Creator self-payments are internal actor transfers, not external
profit; only net payments by other actors count as external fee receipts.

A C buy changes the purchased mint only under a matching authorization. Rejected
cash stays with its owner unless a separately chosen direct/outside trade executes.
An accepted gross budget is split into reserve principal, fees, costs and unspent
dust exactly once. Count partial accepted orders by actual spend, not offered size.

For voluntarily escrowed loser claims e_i out of q_i, the batch has at most
`V_i = R_i(q_i)-R_i(q_i-e_i)` gross cash. After sell fees and costs its available
quote U_i funds the winner's buy plus its fees/costs. If winner net principal is
B, then `sum(U_i)=B+buy_fees+buy_costs+cash_refunds+dust`, absent another explicit
funding source. Winner tokens are allocated by actually spent quote, not by
loser market cap, nominal token units or quoted first-exit values.

Migration removes loser backing before adding winner backing. World reserves
change only by fees, refunds, costs, external buys/sells and explicit donations.
The transfer is not a new external deposit. Batch clearing may equalize members'
average execution; it does not erase a manipulator's pre-batch position.

## 4. Escrow, terminal instruments and D settlement

Before D settlement, sum live refundable/conditional receipt principal equals E.
A cash unit can support only one outstanding commitment. Receipt preferences
may be split across wallets, but all aliases share their actor's real endowment.
Candidate preference does not mint a separately redeemable loser token.

Successful batch: `escrow_before = spent_principal + success_fees + funded_costs
+ refunds + escrow_after`; issued winner quantity Q satisfies R(Q)=spent_principal.
Each receipt is marked spent/refunded once and receives Q times its actual share
of net principal, subject to declared rounding. Incompatible receipts, over-cap
cash, no-winner, cancellation and timeout follow explicit refund paths. After
claims, E is zero except identified unclaimed refund liabilities. Such liabilities
never count as winner reserve, revenue, or unencumbered capital retained.

Terminal settlement divides only remaining actual reserve. If just some ordinary
claims consent, redeem that subset using the reserve difference and keep the
others intact. All-claim pro-rata division requires that terminal liability was
part of every claim from inception. A favorable market-cap mark cannot increase
the cash that terminal claims divide.

## 5. Executable liquidity and capital measurements

Use these separate measures with both winner and whole-cohort denominators:

| Measure | Required definition |
| --- | --- |
| Gross flow | Executed buys and sells separately; repeat turnover is allowed and is not new money |
| Net trading deposits | Quote crossing from non-market accounts into trading reserves minus quote released by redemptions; internal migrations cancel in the cohort sum |
| Retained trading capital | Current actual market quote reserves, reporting genesis separately; exclude fees, refundable escrow, buffers without trader claims and outside cash |
| Organic-funded retention | Tagged initial outside participant capital still in reserves, versus attacker/creator capital; tracing convention disclosed for mixed cash |
| Broad platform custody | Reserves plus fees plus escrow, with owners/liabilities visible; not a success metric on its own |
| Executable sell depth | Gross and net proceeds available at fixed marginal impacts, constrained by circulating privately owned inventory and actual reserves |
| Permanent LP capital | N/A for curves; zero claimed by default. LP deposits/ownership/withdrawal restrictions must exist before this term is used |
| Abandonment | Unspent offered quote and lost opportunities, separate from fees or realized cash loss |

For linear curves, for marginal impact cap delta in (0,1):

```
d_sell = min(private_sellable_quantity, q, delta*p/b)
D_sell_gross(delta) = p*d_sell - b*d_sell²/2
buy average slippage(d) = b*d/(2p)
sell average slippage(d) = b*d/(2p)
```

Return gross and fee/cost-inclusive execution; label marginal impact separately
from average slippage. Compare 1%, 5%, 10% depth and identical quote notionals,
starting prices, total capital and changed curve calibrations. The winner's depth
can increase by reallocating existing backing while total retained capital falls.
Summing independent-token depth is a portfolio diagnostic, not liquidity available
to sell a single winner holding. Within one token do not add incompatible
first-exit quotes of multiple wallets.

**Arithmetic witness:** at a=.01, b=.0001 and R=60, gross 5% sell-depth is
5.89875. Redistributing the same reserve into one curve improves that curve over
each of several smaller curves; it creates no additional reserve. Recalibrating
b changes depth and must be reported as a separate treatment.

Report organic active funded actors and trades at finalization+1h, +24h and +7d,
using common age windows and excluding forced terminal unwind. Also report time
since narrative creation, so longer auctions do not receive shorter follow-up.
Prices of unattended curves can remain positive after attention disappears;
nonzero terminal price alone is not survival. Report active participation,
retention and priced executable depth together, including zero-demand runs.

## 6. Break-even conditions: analytical, not estimated acceptance thresholds

Let D be post-close loser-directed gross opportunities; a their realized
quote-weighted winner acceptance, z the fraction of rejected quote still buying
the original token, r_L the control reserve-retention fraction per gross unit,
and r_W that of an accepted winner order. Let K be additional net reserve loss
from induced exits, execution costs and displaced orders outside those fractions.
Under this deliberately simplified constant-fraction decomposition:

```
Delta retained = D * [ a*r_W + (1-a)*z*r_L - r_L ] - K
a_break_even = [(1-z)*r_L + K/D] / [r_W-z*r_L]
```

The expression requires D>0 and a positive denominator. Thresholds above one are
infeasible. Zero/negative denominators require direct inequality evaluation;
there is no universal acceptance percentage. In the full model r, a, z and K
are endogenous and correlated, so estimate break-even by paired simulation and
uncertainty intervals, without using this formula as a causal estimate.

**Illustration:** z=0, r_L=.4, r_W=.6, K=0 requires acceptance above 2/3 for a
strict gain. K/D=.1 raises it to 5/6. At a=.5 and K=0 the cohort loses .1D of
retained capital even though the winner gets more orders. These chosen numbers
are not observed memecoin behavior.

If winner starts with gross intention share s, its share of executed buy quote is
`[s+a(1-s)]/[s+a(1-s)+(1-a)z(1-s)]`, assuming unchanged direct winner buys.
For z=0 this is 100% whenever the denominator is positive: perfect concentration
can coexist with substantial abandonment. A zero denominator means no executed
buys and the share is N/A. Always report the missing original demand and absolute
reserve alongside share.

## 7. Adversary P&L, manipulation cost and welfare

Aggregate aliases by controlling actor in evaluation. Capital at risk is peak
funded net cash deployed plus separately identified collateral and contingent
liabilities, not total wash turnover. Export acquisition principal, buy fees,
sell fees, launch/promotion/network costs, opportunity cost and creator/support
receipts separately. Do not subtract already-debited fees twice.

Realized trading P&L uses removed cost basis plus cash distributions; cash wealth
change after complete feasible exit is the primary attack-profit test. Export
unrealized marked P&L and executable residual value separately. Dust/unexitable
inventory prevents an unqualified complete-exit claim. Countervenue execution
must debit its finite inventory and cash. Peak risk and unrecoverable cost of
capturing a title are different quantities.

Measure participant losses against both (i) no-attack same-mechanism worlds and
(ii) matched independent worlds, with separately optimized attacker controls.
Do not attribute ordinary profitable trading, self-funded rebates or a creator
winning fairly to a novel routing exploit. Protocol revenue is a transfer paid
by someone; if all positions liquidate, cash gains/losses plus recipient accounts
reconcile. Mark-to-market wealth need not sum to cash wealth.

**Ordering witness:** with the above curve and initial q=1,000, an attacker buys
1,000 before a known victim purchase of 1,000 and then sells its full position.
At zero fees/costs attacker outlay is 160 and proceeds 260, profit 100; the
victim pays 100 more than without the attacker. This proves a possible funded
same-token migration attack under permissive limits, not profitability under
every slippage cap. Optimization must include refusal and failed execution.

## 8. Precision and acceptance tests for Phase 2

Use the existing high-precision Decimal reference with independent curves for
unrounded identities, and a separate integer quote/token-quantum settlement
reference for rounding. Mathematical decimal precision is not six-decimal token
execution. Round funded spend down; return unspent quote to its owner. Use a
published largest-remainder allocation with receipt-ID tie order for token quanta,
only if it respects each owner's limits; otherwise refund that allocation.
Never use float tolerance to admit knowingly underfunded execution.

The optimized float model must match reference outputs on supported states;
declare absolute/relative audit tolerances in manifests. Property tests cover
multi-event conservation, cash constraints, partial escrow redemption, full exit,
idempotence, replay, consent rejection, refund paths, alias budgets, redenomination,
fee support and no-winner states. Differential tests include near-quantum and
near-total-balance boundaries. A disabled feature gives the correct matched
control. Failing invariants halt a run and retain its event tape and state.
