# Bounded study implementation record

All behavioral values are synthetic scenario inputs. No new real-market data,
wallets, contracts, paid data or dashboard are used. The original four Phase 1
documents remain unchanged. This record describes the new bounded implementation;
completed gates and counts are reported separately in manifests and findings.

## Settlement and ownership

The primary curve remains a=.01, b=.0001 in abstract quote units. Quote quantum is
1e-6 and claim quantum 1e-4. For integer claim quantity q, cumulative backing in
quote quanta is `q + floor(q*q/2000000)`. Every buy/sale uses a difference of that
same cumulative function, so integer backing telescopes exactly. Integer square
root inverts the curve. Buy quantities round down to a funded amount; separate
protocol and creator fees round up to a quote quantum. Unspent dust stays with
its owner. There is no float funding tolerance. Inputs are bounded nonnegative
integers <=1e18. The unrounded reference reuses the existing high-precision ledger
at coupling zero. Fractional analysis and integer execution are different layers.

All quote accounts, including market, protocol, creator, support, network, sponsor
and escrow, appear once in cash conservation. Every pricing claim has an owner.
Literal destruction reduces pricing supply and leaves a labeled inaccessible
buffer; locking leaves supply and redemption rights intact. No buffer is counted
as trader-accessible backing. Support fund claims unlock at finalization+72h;
the fund attempts full redemption then, and no further support epochs run.

D uses aggregate batch fees, a public supply cap, minimum raise and worst-case
all-in average price ceiling. Compatible contributions are scaled to actual spend;
quote and claim allocations use largest remainders with receipt-ID tie order.
The sponsor pays settlement network cost. A rounding allocation violating a
receipt price limit causes refund rather than an unauthorized fill. The initial
batch has no preexisting winner spot inventory. Incompatible, cancelled, failed,
expired and over-cap principal returns to the original owner. Repeated settlement
and refund are idempotent. The code does not promise fixed token quantities or
par redemption. Batch average entry below the marginal exit price creates an
early-exit incentive by construction; that outcome must remain in the results.

## Gates and development failures

The first mechanical test run passed 25 tests and failed one assertion that
mistakenly required two different-price fixed-budget paths to spend exactly the
same amount despite claim-quantum dust. The corrected test checks exact cash plus
backing conservation and attributes the reserve difference exactly to owned
unspent cash. The failed output and source snapshot remain in `gate1_mechanics/`.
No old source, tests, results or dependency was repaired or overwritten.

The first full behavior-gate collection found a basename collision between the
new and old `test_world.py` modules. Adding a package marker only in the new
test directory isolates their namespaces. The failed collection is preserved
under `gate2_pass/`; the corrected complete run uses a different directory.

Later development repairs, if any, are retained in named gate/failure artifacts.
Passing tests establish mechanical behavior on their stated cases, not economic
viability. The frozen economic matrix will be written only after development and
attack training; confirmation seeds cannot be used to tune it.

## Synthetic behavior and scope

Each world starts with exactly 39,100 quote units: 32,000 across 64 traders (whales
have larger funded wallets), 2,000 across ten creators, 5,000 for the coordinated
actor and 100 for settlement costs. Outside spending buys a distinct funded
alternative curve or a refused creator's outside candidate; it does not disappear
from world cash. Ten creator submissions each cost one unit and promotion costs
five; no free token allocation exists. Unused control creators retain their money.

Roles include retail, narrative followers, loyalists, momentum, whales, promoter
followers, bundlers, snipers, migrators and arbitrageurs. The bounded primary
world has no cross-venue fungible dealer quotes, so the arbitrageur role has no
claimed arbitrage profit and behaves as a price-sensitive trader. These are
synthetic heterogeneous preferences. Searcher opportunities are tested explicitly
in funded ordering experiments. No population share is empirically estimated.

480 latent opportunities include 120 before the 30-minute primary close; the
rest span seven days with an explicit late tail. Attention decays; current prices,
participation and momentum affect choices. Opportunities, consent, cancellation,
exit and endowment draws use separately keyed seeded streams. Executed paths
cannot shift unrelated future draws. Wallets receive no spending replenishment.
Refunds and sale proceeds remain actual owned cash usable for later opportunities.

C's assumed acceptance is a ceiling reduced by loyalty, price and grouping
friction; realized acceptance is separate. Reach applies to eligible loser entry
points. Rejection alternatives are direct purchase, funded outside purchase or
cash retention. D separately varies lock willingness and allowed winners; its
postlaunch winner-choice parameter is independent of C acceptance. An A/C
commitment-score overlay locks five units per trader, then refunds after scoring.
Its funding and lockup are explicit. D's preissuance spot metrics are unavailable.

The evaluator's benchmark is the candidate with the largest future *latent offered*
quote under neutral exposure. It is not true value or a perfect predictor of
price-sensitive execution. Elections use only pre-close public balances/receipts.
A records a diagnostic winner without routing orders. No policy sees future draws.

Primary B uses half the protocol fee; its alternative pools authorized creator
fees and splits them 60/30/10. Each has separate lock/destruction variants. Epochs
are finalization, +1h, +6h, +24h and +48h; unlock is +72h. Before/after unlock,
+1h/+24h/+7d and common creation checkpoints are recorded. Feasible terminal exits
follow all observations and never count as seven-day organic activity.

Creator refusal is an exogenous outside-option stress, not a solved adoption
equilibrium. Refused creators retain funded outside markets and their fees are
excluded from platform support. Grouping stress reduces consent by a disclosed
synthetic penalty. Neither stress estimates human willingness or classifier error.

Pre-confirmation review found that batch cash settlement was correct but the
per-subscriber acquisition/fee export counters omitted aggregate batch payments.
That reporting defect was repaired and tested before confirmation; 4,600 exported
rows of the interrupted initial attack search and its source snapshot remain in
`training/` and are not used for policy selection. The final search is separately
stored in `training_final/`, includes 8/32/64-wallet splits under the same actor
funding limit, and uses the repaired attribution. Development also motivated a
second C acceptance grid with migration disabled, to isolate routing effects.
Timeout refunds execute at the published deadline even if the finalizer is late.
Snapshot `finalized=0` marks a provisional ranking rather than an executable title.
