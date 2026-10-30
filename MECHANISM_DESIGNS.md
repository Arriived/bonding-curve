# Narrative consolidation: economic designs

Phase 1 specification, 30 October 2026. A–D below are proposed research models,
not implemented features. Decisions marked **sensitivity** must remain separate
experimental settings. Defaults define a testable starting point, not empirical
parameter estimates. Read `PRIOR_ART.md` for external evidence and
`ECONOMIC_INVARIANTS.md` for ledger requirements.

## 1. Instrument, accounts and authority

Use one abstract quote asset with no price volatility in the first comparison.
Each A–C candidate has an independent redeemable issuance curve:

```
p_i(q) = a_i + b_i q,   a_i > 0, b_i > 0
R_i(q) = a_i q + b_i q²/2
buy cost C_i(d) = R_i(q+d) - R_i(q)
sell proceeds V_i(d) = R_i(q) - R_i(q-d)
```

No cross-token price derivative is introduced. Candidate supply is curve-issued
claims owned by funded holders; creators receive no free redeemable allocation.
This is an abstract independent reference market, not Pump's formula. A finite
issuance cap and a separately validated constant-product market are later
robustness checks. Raw token units must be fixed and redenomination-invariant.

All models share the same fee convention: a gross buy cost C debits
`C(1+f_p+f_c)+network`; a gross sale V returns
`V(1-f_p-f_c)-network`, where protocol and creator fees have distinct owners.
Fees are transfers, not reserve. Every creator, trader, promoter, network,
protocol, fee-support fund, escrow and external dealer has an explicit account.
Opening capital, launch fees and subsidies are included in world endowments.

Consent records bind owner, group/version, eligible received mint(s) or the
published winner rule, quote budget, expiry, price/output limits, cancellation
cutoff, fee schedule and fallback. Page visits and token ownership confer no
routing authorization. No post-election change to groups or settlement rights
can reach existing claims. A creator can refuse admission and use an outside
venue; model that option rather than granting the platform all launch traffic.

## 2. Architecture comparison

| Model | Before close | After valid election | Ownership of funded tokens | No qualified winner |
| --- | --- | --- | --- | --- |
| A independent | Separate curves and balances | Same independent markets; election computed only as a diagnostic | Buyer owns chosen candidate | Markets continue |
| B fee-fed winner | Independent trading; eligible fees accrue in support escrow | Support fund buys winner on a published schedule; candidate trading continues | Support fund owns and locks purchased claims in primary B | Accrued conditional fee contributions revert to named fee beneficiaries; no forced winner |
| C winner router | Independent trading | Fresh, authorized eligible purchases can execute entirely into winner; rejection has explicit alternatives | Buyer owns actual received mint; loser holders keep their claims | Direct candidate purchases continue |
| D narrative launch auction | Quote escrow and conditional nontransferable receipts; no candidate spot tokens | Eligible commitments buy batch-issued winner claims; incompatible claims refund | Each subscriber owns allocated winner tokens; no loser asset exists | All unspent principal refundable |

A diagnostic election in A uses the same rule where its inputs exist; A does not
move funds. Compare B and C to their same-world pre-election state. D changes the
launch instrument and delays trading, so comparisons must isolate those effects
with a single-token batch control and matched lockup controls.

## 3. B: what fee support buys

Default eligible amount is a published fraction eta of protocol trading fees,
earmarked from inception. Creator fees remain with their own creators. A
Prism-like sensitivity pools only previously authorized creator fees; it must
deduct those receipts from creators rather than retaining them twice. No trader
principal or candidate reserve is classified as a fee. Support applies to all
admitted candidate trades through a disclosed end time, including after close.

At each published epoch the fund spends at most its available cash, buys through
the same market interface and pays all execution fees/costs. Primary B locks the
purchased token claims in an identifiable account through the observation horizon.
It has no assumed cash redemption for users and does not lower pricing supply.
Unlock-and-sell, distribution to users and literal destruction are separate
ownership variants, because their redemption rights differ. Skipped purchases
retain cash in the fund. No qualified winner returns conditional contributions
to their recorded fee beneficiaries; ordinary fees already earned remain theirs.

Report both the temporary support purchase and sales into it. A predictable
epoch can pay informed early holders. Recycling fees does not inject external
money or create permanent LP capital. A horizon-limited lock is not permanent.

## 4. C: authorized routing and voluntary migration

The registered candidate cohort closes before finalization. After the immutable
winner is announced, an incoming buyer sees the actual received mint and either
authorizes it or follows a sampled outside option. Default routing fraction for
an accepted eligible order is 100% of that order's budget to the winner. Partial
splits are an explicit secondary setting. The winner receives only net principal
after fees. Acquired tokens belong to the buyer, with normal sale rights.

On rejection, the buyer can (a) buy the originally preferred candidate through
its continuing market, (b) choose another candidate/outside venue, or (c) leave
with unspent cash. Probabilities depend on loyalty, prices, expected proceeds,
authenticity beliefs and time costs. Track actual fills and cash left outside.
Order rejection does not destroy its nominal budget. Count incurred network or
promotion expense separately from foregone potential business.

Loser holdings are unchanged. A voluntary migrator supplies a signed sell/buy
instruction: redeem owned loser quantity d for actual V, pay sell fees/costs,
then buy winner using only the funded net proceeds. The whole conversion is
atomic under a minimum winner output, or explicitly split with a quote-cash
fallback authorized in advance. In the primary design failed conversion leaves
both legs unexecuted. Actual submitted-failure network costs are recorded by a
separate policy; a pre-submission refusal has no network charge.

No new winner is chosen merely because the incumbent falls in popularity. Test
an expiry of routing and renewed user choice; repeated elections would introduce
a separate contest and repeated consent obligations. Winner status is no claim
on another token's collateral.

## 5. Settlement comparison: three different instruments

**S1: voluntary loser redemption.** C's ordinary spot claims stay freely
redeemable. Individual migration timing determines actual sale proceeds. Batch
redemption of voluntarily escrowed e_i claims releases
`R_i(q_i)-R_i(q_i-e_i)`; distribute the net amount pro rata to those escrowed
claims. The remaining reserve backs q_i-e_i. Nonparticipants lose no rights.

**S2: precommitted terminal settlement.** A distinct candidate instrument can
specify from entry that all its claims terminate at T and divide the actual
terminal reserve pro rata. To compare exit incentives, run both an expressly
redeemable-before-T version and a locked-until-T version. The redeemable version
lets informed holders exit at the favorable early curve price before others
receive terminal average value. The locked version removes this escape by
changing liquidity rights, not by improving the same spot token. Every transferee
must inherit the disclosed terminal rule; existing ordinary claims cannot be
enrolled by majority vote. Terminal proceeds become quote refunds unless an
independent winner-purchase authorization exists. In A or B that can simply be
a terminal cash diagnostic; it is not implicitly routing.

**S3: conditional winner subscription.** D has escrow receipts and neither loser
token supply nor trading reserves before finalization. A preferred candidate is
a voting designation, not a freely tradable spot asset. Receipts define an allowed
winner set, maximum all-in spend/price, expiry and refund entitlement. No allowed
set can be expanded after commitment. Preferred-only receipts refund if they lose.
Broadly authorized receipts can settle to any eligible winner in their fixed set.

## 6. D: fully specified initial batch mechanism

The initial research D uses a **capital contest followed by uniform-price batch
curve issuance**. It is a narrative launch auction, not a reproduction of a
fixed-lot Gnosis auction or Uniswap CCA. Price discovery follows a published
reserve curve and aggregate accepted budget. A fixed-supply auction with AMM
handoff is a separate robustness design; it must not be quietly substituted.

1. Publish group, candidate slots, a/b, maximum batch supply Qmax, fees, minimum
   qualifying escrow, minimum settlement raise, cancellation time, close rule,
   finalization timeout, receipt rights and equal-access contribution cap.
   Default cancellation ends at the earliest possible close. Committed cash is
   unavailable for other trades. A receipt designates one preferred candidate.
2. Receipts contributing to selection must be irrevocable after that cutoff,
   valid through the finalization deadline, and accept at least the published
   worst-case average price `Pbar = a+b Qmax/2`, including a separately stated
   fee budget. This prevents a low-price unfillable bid from counting as funded
   support. Lower-limit bids are excluded from this initial D design.
3. At close select from qualified candidates using only information available
   then. Repeated use of the same quote in several candidates is prohibited.
   Compatibility with the winner determines which receipts can settle; losers'
   preferred-only money is refundable. A candidate can win the title but fail
   the minimum compatible raise; default is abort/refund, without runner-up
   reselection. Test reselection only with a separately published rule.
4. Let U be compatible all-in escrow available after explicitly budgeted network
   costs, and f=f_p+f_c. Maximum feasible all-in spend is
   `(1+f)R(Qmax)`. Set spent total `S=min(U,(1+f)R(Qmax))`; if the net principal
   B=S/(1+f) fails the published minimum, abort. Scale compatible receipts
   proportionally by S/U. Refund unused cash; cancellation/abort never incurs
   a success fee. Network costs on aborted attempts need a funded sponsor or
   the receipt's explicit cost allowance, never an undisclosed principal haircut.
5. Issue `Q=(-a+sqrt(a²+2bB))/b` winner claims against B real reserve, allocate
   `x_j=Q*(spent_j/S)`, and split the fees to their named beneficiaries. All
   batch buyers pay the same average net price B/Q. This is lower than the
   first post-batch marginal price a+bQ; the resulting initial paper gain is
   not earned cash or additional reserve. R(Q)=B exactly before rounding.
6. Enable independent winner trading after atomic settlement. No outsider spot
   market in that mint is admitted before this handoff in primary D. Consequently
   a pre-handoff secondary-price manipulation is inapplicable here, while bid
   concentration and immediate resale remain applicable. The attack on an
   existing winner market belongs to C/S1 and the separate external-handoff D.

Default D creator has no token preallocation and earns only disclosed fees.
Unselected candidates do not become ten independently redeemable assets. Return
all refundable quote to its original owner or retain an immediately claimable
refund liability; unclaimed money is not retained trading capital.

States are `OPEN -> LOCKED -> CLOSED -> SETTLED`, or `CANCELLED/EXPIRED ->
REFUNDABLE`. Any actor can trigger deterministic finalization in the off-chain
model. Missing reveal, invalid inputs, no qualified candidate or settlement timeout
produce refunds without discretionary selection. Each receipt can settle or
refund exactly once. Partial external execution is excluded from the atomic
primary mechanism; an asynchronous extension requires funded recovery per leg.

## 7. Election engine and information model

| Rule | Definition/input contract | Strategic weakness to test |
| --- | --- | --- |
| Market cap | p_i times explicitly defined circulating supply; also export fully diluted value | Temporary purchases, supply-unit errors, thin quotes and immediate dump; reserve is different |
| Net committed capital | Current unspent, irrevocably locked quote assigned once to candidate | Whale capture, borrowed/temporary commitments, low compatible settlement capital |
| Time-weighted commitment | Integral of qualifying locked quote over time; common group-time denominator | Early capital dominance, lockup cost, cutoff secrecy and creator seed advantage |
| Sustained net buying | Windowed principal buys minus gross redemptions, with disclosed nonnegative transform | Recycled sale proceeds, coordinated timing and later reversal; signed flows still exported |
| Fee generation | Actual paid fees, reported net of receipts returned to the actor in diagnostics | Wash/rebate loops and bribing fee beneficiaries |
| Holders/concentration | Address counts above economic threshold and observable holdings HHI | Capital splitting, dust, custodial aggregation and hidden coordination |
| Composite | Frozen normalization, weights, missing/zero handling and concentration rule | Combined attacks; no guaranteed truth or calibrated winning probability |
| Random close/commit-reveal | Closing-time procedure applied to the scoring rules, not a new demand metric | Operator foresight, biased draw, censorship, reveal withholding and selection grinding |

Metrics unavailable for an instrument are **N/A**, never fabricated: D has no
prelaunch spot cap, trading fees or token-holder count; A–C do not have irrevocable
quote commitments unless a separately funded optional overlay is introduced in
all matched worlds. Such overlays change capital availability and are separate
comparisons. Raw volume/address/social metrics are attack controls, not organic
demand ground truth.

For a concrete composite sensitivity, freeze positive scale constants L_m before
runs and use bounded features `z_m=max(0,x_m)/(L_m+max(0,x_m))`, weighted sum with
published nonnegative weights summing to one, and a published address-HHI penalty.
Do not normalize to the current candidate maximum: spam can alter that denominator.
Ground-truth actor HHI is an audit counterfactual unavailable to the election.

Eligibility requires admitted membership, minimum age, required data and a
declared economic funding threshold. Ties within the scoring quantum produce
no winner and the model's no-winner path; a public random tie-break is a separately
costed setting. Fixed close admits events strictly before T; close precedes any
same-timestamp event at T. Rankings replay from the full timestamped log.

Primary fixed close is transparent. A randomized sensitivity samples T in
`[0.9W,1.1W]`, with hash/seed commitment and a reveal deadline at creation.
Cancellation ends before 0.9W. Treat an honest hidden draw, an operator-known
draw, and biased/withheld draws as distinct threat models. Do not retroactively
reverse valid trades after a hidden close; use the last pre-T scoring state and
route only after public finalization.

The highest score is distinct from highest genuine future demand. On a separate
unseen future tape, measure which candidate would receive the most funded
non-adversarial demand under neutral presentation and comparable prices. Export
selection error and foregone demand; this is an evaluator-only benchmark that
neither agents nor the election can inspect.

## 8. Behavioral and creator assumptions requiring experiments

Use a common narrative attention process, finite agent endowments and common
latent opportunities. Candidate utilities combine launch timing, visibility,
holder participation, paid promotion, performance, authenticity beliefs, loyalty
and estimated winner chances. Price elasticity and an outside option reduce
participation. No victory creates extra organic opportunities in the primary
case. Attention feedback, if enabled, has an explicit coefficient and cost or
mechanism; zero and negative feedback are required controls.

Retail, narrative followers, loyalists, momentum traders, whales, creators,
promoters, bundlers, snipers/searchers, arbitrageurs, adversarial creators and
migrators differ in utility, risk budget, information and opportunities. All use
actual cash/inventories. Do not force an arbitrageur to trade without a finite
countervenue and profitable two-leg execution. Creator promotion debits real
cash; one actor may control many funded wallets and candidate identities.

Creator participation requires expected fees and other explicit receipts minus
launch/promotion costs and opportunity cost to compete with an outside option.
Losing creators' enthusiasm, winner acceptance, migration participation,
grouping accuracy and attention persistence are unresolved empirical inputs.
These uncertainties require sensitivity analysis before an economic verdict.
