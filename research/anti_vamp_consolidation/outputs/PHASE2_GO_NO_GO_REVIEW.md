# Narrative consolidation: Phase 2 go/no-go review

30 October 2026. Read-only review of the four uploaded Phase 1 documents. This assessment introduces analytical counterexamples and implementation requirements; it does not report a new A–D simulation, behavioral calibration, or protocol audit.

## Decision

**Conditional GO for the bounded Phase 2 accounting and settlement research engine. NO-GO for a claim of economic superiority, a production build, or deployment.** Phase 1 provides a credible specification to test, with important remaining details to resolve in code. It does not establish that winner selection creates demand, improves cohort retention, resists capture, or attracts consenting buyers and creators.

Implement A and C first to isolate the core hypothesis: can voluntarily concentrating purchases improve usable winner liquidity without reducing cohort participation and retained capital? Add B as a fee-redistribution comparator. Implement D faithfully as a separate launch instrument with an explicit first-exit counterexample. This is an implementation priority, not an empirically demonstrated ranking.

The proposed automatic conversion of ordinary loser holders or use of their backing without authorization is outside the admissible design. The documents correctly exclude it. Venue migration, fee recycling, voluntary asset conversion, and conditional subscription have different ownership and liquidity consequences.

The research plan uses “Phase 2” specifically for accounting, A–D, and settlement. Endogenous behavior, strategic policy search, Monte Carlo, and the dashboard are its later Phases 3–6. Passing the Phase 2 gate would establish mechanical correctness within the modeled domain, not viability.

## Evidence checked

All four uploaded texts are byte-identical to the corresponding repository documents. I independently rehashed the 445 originals in the Phase 1 preservation manifest; none differed or was missing. I parsed the archived JUnit report: 138 tests, zero failures/errors/skips, recorded duration 63.447 seconds. I did not rerun pytest or execute repository models or Phase 1 scripts. Existing tests therefore remain historical baseline evidence, not tests of the proposed A–D engine.

The public-data evidence records two keyword snapshots, each with 30 pairs and 17 distinct chain/base-token keys. That supports discovery access only. It supplies no historical narrative cohort, routing acceptance, creator willingness, identity count, or causal comparison. Saved arithmetic and preservation details accompany this report in `REVIEW_EVIDENCE.json`.

## What Phase 1 gets right

`PRIOR_ART.md` distinguishes mechanism descriptions from outcome evidence and avoids claiming novelty from familiar components. `MECHANISM_DESIGNS.md` separates buyer-owned principal, fee-funded support, and escrow subscription; freezes consent and winner rules; and preserves ordinary loser claims. `ECONOMIC_INVARIANTS.md` separates custody from ownership, cap from collateral, and marked wealth from realizable cash. `RESEARCH_PLAN.md` requires funded attackers, matched opportunities, unseen confirmation seeds, creator outside options, and single-token batch controls.

Those are substantive strengths. They remove several easy ways to obtain a misleading positive result. The remaining weaknesses are mainly missing operational definitions and unsupported economic responses, rather than an identified error in the stated continuous reserve equations.

## Assumptions that need stronger falsification

### 1. Routing can concentrate activity while destroying business

Source: `ECONOMIC_INVARIANTS.md` §6; `MECHANISM_DESIGNS.md` §4.

The supplied acceptance break-even formula is algebraically correct under its stated constant-fraction simplification. It is not an estimated threshold. A useful stronger control sets winner and loser retention equal, `r_W = r_L = r`, with no additional loss `K`:

```
Delta cohort retained = -D * r * (1-a) * (1-z)
```

If every rejection still buys the preferred token (`z=1`), routing alone produces zero cohort gain. If some rejected money leaves, it produces a loss unless another modeled effect offsets it. For D=100, r=.4, a=.5, z=0, the loss is 20 quote units. If no rejection buys another candidate, winner share of executed orders can nevertheless be 100%.

There is another missing input: **router reach**. C can affect orders submitted through a venue that honors the relevant authorization. Ordinary purchases through outside venues continue to buy their specified asset. In a simple homogeneous approximation only `reach × acceptance` of eligible loser-directed opportunities is captured; the full model must represent venue choice explicitly. Creator refusal and direct external trading can reduce reach even when conditional acceptance is high.

Required test: report offered quote, reachable quote, authorized quote, filled principal, outside fills, unspent cash, and cohort reserves separately. Use zero acceptance, zero reach, unchanged exit behavior, and zero attention feedback as distinct controls. Do not infer acceptance from following a link, owning a loser token, or a scripted diversion fraction.

### 2. D has a cash-realizable first-exit advantage before new demand arrives

Source: `MECHANISM_DESIGNS.md` §6, especially steps 5–6; `ECONOMIC_INVARIANTS.md` §2.

The documents correctly warn that batch average price is below the next marginal price. They should make the resulting resale incentive explicit. With `R(Q)=aQ+bQ²/2`, a subscriber owning fraction h of the equally priced batch pays hR(Q). If that subscriber sells first, gross proceeds are `R(Q)-R((1-h)Q)`, giving zero-fee profit:

```
first-exit profit = (b Q² / 2) * h * (1-h)
```

At a=.01, b=.0001, Q=1,000, total principal is 60. Two equal buyers pay 30 each. The first can redeem 500 claims for 42.50; the last receives 17.50. No post-launch buyer is required. Fees reduce this gain but do not structurally remove the ordering incentive. For buy/sell rates f_b/f_s, test `(1-f_s)*first_exit_proceeds - (1+f_b)*hR(Q) - funded_costs`.

This is a transfer from slower subscribers, not insolvency or free aggregate profit. It applies to the specified D curve handoff; a matched single-token batch can exhibit the same problem. Thus it does not prove narrative election causes the problem, but it prevents uniform allocation from being treated as fair exit pricing or durable retention.

Required test: two subscribers, no outside demand, both sale orders; then unequal positions, realistic fees, competing exit priority, and random exit order. Fail the economic fairness/retention claim if it relies on subscribers remaining passive while a strategic subscriber redeems. Keep the primary D specification intact when exposing this result. A fixed-lot auction and finite AMM handoff would be a separately named experiment.

### 3. B can subsidize exits rather than retain its support spend

Source: `MECHANISM_DESIGNS.md` §3; `ECONOMIC_INVARIANTS.md` §§3, 5.

An exact zero-fee witness starts with q=1,000 and reserve 60 on the same curve. A support fund with 30 of already funded cash buys approximately 245.3624 claims and locks them. If all original holders then redeem their 1,000 claims, they receive 84.5362. Only 5.4638 remains backing the locked support claims. Of the support spend, 24.5362 has increased incumbent exit proceeds.

The fund cash is an explicit preexisting fee balance in this witness; it is not created from the current 60 reserve. Both matched worlds must include its original funding. This example is a feasible accounting trace, not an estimate of how frequently holders sell.

Required test: support schedule known versus unknown, strategic selling into epochs, fund exhaustion, and a matched disposition of the same protocol fee income. Report private-holder activity and reserve supported solely by locked fund inventory. Extend observation past unlock before calling the result durable. No claim of permanent LP capital follows from the curve model.

### 4. Capital capture is different from expensive irreversible manipulation

Source: `MECHANISM_DESIGNS.md` §7; `RESEARCH_PLAN.md` §4.

A cap-based contest can require large peak funding yet have low unrecoverable cost: a trader can buy before close and reverse after close, recovering principal absent adverse intervening trades. A locked commitment adds capital-time cost, but its refund or later redemption can still make peak capital much larger than net attack cost. Capital-linear selection is less vulnerable to simple address splitting than holder bonuses, but it selects capital, not independently verified enthusiasm or future demand.

Address concentration penalties can reverse that advantage. Splitting a fixed position into k equal qualifying wallets reduces that actor's observable wallet HHI contribution from 1 to 1/k, before costs and thresholds. A per-wallet “equal-access contribution cap” does not impose a per-person cap. D §6 leaves the cap's enforceable scope unspecified. Ground-truth actor IDs must be inaccessible to the election unless an explicit identity mechanism is being evaluated. The identity distinction is consistent with [Douceur's Sybil analysis](https://www.microsoft.com/en-us/research/publication/the-sybil-attack/).

Required test: distinguish title capture, forecast error, capture cost, extraction after capture, and victim loss. Include abstention and separately optimized attacks in A. A copy legitimately winning, or an ordinary profitable trade, is not by itself a routing exploit. Finite unsuccessful searches cannot establish strategy-proofness.

### 5. Holder migration moves a diminishing cash claim, not market cap

Source: `MECHANISM_DESIGNS.md` §§4–5; `ECONOMIC_INVARIANTS.md` §§2–3, 7.

The reserve-difference migration equation is correct. A loser holder has no claim on the winner's price or a market-cap-sized cash amount. Early ordinary redemptions can obtain more than the final pro-rata reserve average. S2 changes rights from inception; it cannot be offered as a harmless upgrade to existing spot holders.

Atomic sell/buy protects against a failed second leg leaving an unintended asset. It does not protect against an attacker who bought winner inventory before the batch. The documented 160-outlay/260-proceeds witness proves a possible 100-unit ordering transfer under permissive limits. With tight output limits, that same attempted strategy may instead cause cancellation and costs. Report both. [Flash Boys 2.0](https://arxiv.org/abs/1904.05234) supports the relevance of transaction-order extraction, not its profitability or frequency in this new design.

Required test: per-owner minimum winner output, full rollback, separately charged submitted-failure costs, heterogeneous batch constraints, and an explicit deterministic rule for removing or refunding incompatible allocations. Recompute clearing after exclusions; do not spend the same proceeds twice. Full liquidation must respect lock and expiry rules; residual locked inventory prevents an unqualified complete-exit claim.

### 6. More winner depth is not automatically more system liquidity

Source: `ECONOMIC_INVARIANTS.md` §5; `RESEARCH_PLAN.md` §6.

When available private inventory is not binding, the specified curve gives:

```
D_sell(delta) = (2*delta-delta²) * (R + a²/(2*b))
```

At 5% impact, one market with reserve 60 offers 5.89875 gross quote depth. Two markets with reserve 30 each offer 2.97375 each, a portfolio sum of 5.94750. Consolidation improves depth in the destination relative to either small market, but does not create backing and need not improve the portfolio sum. The sum is not executable depth for one winner holding.

Required test: same endowments, same curves, and explicit private sellable inventory; common candidate identity as well as the best realized token; identical quote-sized exit tasks and matched single-token controls. Keep parameter recalibration separate. Under a denomination change q'=kq, use a'=a/k and b'=b/k², scaling caps, holdings thresholds, and quanta consistently. Quote reserves, cap, and executable economics should then be unchanged.

### 7. Creator participation, grouping, and subscriptions are endogenous

Source: `MECHANISM_DESIGNS.md` §§1, 7–8; `RESEARCH_PLAN.md` U4, U7, U12.

If losing creators expect weaker fees, control, or brand ownership, they can launch elsewhere. Treat absent launches and their traffic as part of the outcome. Equal capital with compulsory entry is not a test of voluntary creator adoption. Use both a fixed admitted cohort comparison and a separately labeled endogenous-entry comparison; otherwise creator attrition silently changes the estimand.

A semantic cluster is neither common asset ownership nor universal substitutability. False merges can reduce acceptance and creator entry together. Their interaction is more informative than two isolated favorable sweeps. Freeze admission and receipt rights before commitments; an operator override must not expand a signed allowed set.

D has a further participation hurdle: a receipt counting toward the contest must accept the published worst-case average price. That intentionally excludes some price-sensitive subscribers. Model the decision not to subscribe and outside use of the locked cash. Broad winner authorization in D is a different observable from C's post-election acceptance; do not reuse one parameter as though the decisions were identical.

### 8. Several mechanical choices still need a contract

Source: `ECONOMIC_INVARIANTS.md` §8; `MECHANISM_DESIGNS.md` §§6–7.

Before behavioral runs, freeze: quote/token quanta; fee rounding; the reserve potential used by integer execution; dust ownership; zero-output receipt treatment; D allocation exclusions; source of failed-finalization costs; contribution-cap scope; minimum raise after fees/rounding; and deterministic ordering of cancellation, close, expiry, reveal, settlement, and refunds.

Separate close time T, public finalization time, trading handoff, and observation anchors. Hidden-close simulations must restrict what traders and operators know. A hash can bind a chosen timestamp without proving that its sampler was unbiased or unknown to the operator. Include withheld reveal and delayed finalization, not just honest replay.

The existing exact curve uses common curve parameters and an aggregate reserve. It is useful reference material, but does not by itself implement separate creator fees, per-candidate ownership, authorization, or escrow liabilities. The new engine must enforce these contracts directly. A float engine must never use tolerance to authorize an underfunded order or choose a different close/refund branch.

### 9. The experiment plan needs a narrower confirmatory question

Source: `RESEARCH_PLAN.md` §§5–7.

The proposed 528-cell spine is arithmetic, not a power analysis. At 500 confirmation seeds it implies 264,000 worlds per applicable architecture/rule before controls, attacks, and additional interactions. A/B have only 48 distinct count/window/demand cells in that spine when acceptance is inapplicable; repeating them across acceptance values creates no new independent evidence. D's allowed-set and subscription decisions need their own design rather than inheriting C's acceptance axis.

Start later experimentation with a prespecified A-versus-C question and a pilot measuring runtime and variance of paired effects. Freeze one primary endpoint/contrast and a practical effect margin before confirmation. Keep the full seed as the sampling unit, maintain separately keyed random streams, and retain failed worlds. A repeated policy search on confirmation seeds would invalidate the planned holdout. Reserve a fresh evaluation set if later design choices consume it.

Historical flows may inform attention decay, budgets, and exits when coverage permits. They cannot directly identify willingness to accept a different received mint under a new interface, or willingness to surrender losing-creator fees under a new contract. Those require separate evidence of the actual choice, with uncertainty and price/venue context. No such study was performed here. More historical trading data alone will not close every adoption gap.

## Prior-art assessment

The checked primary sources support the broad mechanism comparisons. [Pump's official description](https://github.com/pump-fun/pump-public-docs/blob/main/docs/PUMP_PROGRAM_README.md) describes per-token curve trading and migration into PumpSwap, which does not establish cross-token winner authorization. [EasyAuction](https://github.com/Gnosis-Auction/auction-contracts/blob/main/README.md) supplies a fixed-lot limit-order batch precedent. [Uniswap CCA's technical specification](https://github.com/Uniswap/continuous-clearing-auction/blob/main/docs/TechnicalDocumentation.md) describes time-distributed issuance, graduation, refunds, and downstream handoff. Neither is the initial D mechanism.

[CoW's signed-order specification](https://docs.cow.fi/cow-protocol/reference/core/signing-schemes) binds asset identities, quantities, and expiry, supporting the consent boundary. The new model must also bind its own group/rule version, fees, and fallback; citing an intent protocol is not an implementation of those protections.

Prism remains especially close prior art. Its indexed [first-party mechanism page](https://prismlaunch.fun/how-it-works) describes narrative grouping, scoring, a hidden committed close, pooled creator fees, and ranked custodial baskets. Direct retrieval failed again during this review. Its claims about manipulation resistance and winning probabilities remain unverified; indexed product prose is not deployed-code or market evidence. This review establishes no novelty or competitive moat.

## Gates and rejection rules

| Decision | Required evidence | Current assessment |
| --- | --- | --- |
| Begin Phase 2 mechanical implementation | Clear scope, immutable rights, funded accounting, explicit unresolved numerical choices | Conditional GO; use the accompanying brief |
| Mark Phase 2 complete | All architecture/settlement traces, property and boundary tests, replay, integer accounting, declared float parity, existing-suite regression, preservation | NO-GO today: proposed engine unimplemented |
| Begin behavior and attack research | Phase 2 passed; explicit opportunity/venue/entry/acceptance models; no future information | Later gate; not demonstrated |
| Claim synthetic economic benefit | Held-out paired results against A and matched simple controls; meaningful depth benefit with cohort/participant safeguards | NO-GO today: no new completed evidence |
| Claim real-market viability or deploy | Independent acceptance/entry evidence, data coverage, operational mechanism/security review, and model-specific implementation validation | NO-GO today |

For later economic confirmation, preregister one primary contrast and a limited claim domain. A reasonable proposed policy is a positive lower 95% paired confidence bound for 5%-impact winner depth improvement, a separately fixed practical effect floor, and nonnegative lower bounds for cohort reserves and organic participation at +24h and +7d against relevant controls. Adjust for multiple confirmatory claims or designate a primary one; report all tails and absolute levels. These are proposed research decision rules, not empirical facts or a universal safety standard.

Choose practical margins before inspecting confirmation outcomes. If noninferiority margins are allowed, state their cost in quote units/participants explicitly. Undefined ratios when the control is zero must not become infinite gains. A conditional result at high assumed acceptance remains a conditional simulation result. Real adoption cannot pass until the joint reach/acceptance/creator-entry region has independent support. Zero-acceptance and zero-reach controls need not show superiority; they must expose the actual mechanism limit.

Reject a variant immediately for broken conservation/consent, hidden subsidies, identity-oracle dependence, or inaccessible refunds. Reject its economic claim if the gain disappears after lock expiry, survives only by assuming away rejection or creator refusal, is explained entirely by the matched batch/single-token control, or is overwhelmed by feasible capture/ordering losses in the declared threat range. Failure of D need not terminate C research, and failure to find a universal benefit need not preclude a narrow, honestly specified result.

## Recommended next action

Use `CODEX_PHASE2_IMPLEMENTATION_BRIEF.md` for a separate implementation session. Build the smallest exact research engine that can reproduce both success paths and the adverse witnesses above. Do not build the dashboard or run the proposed broad factorial study first. Phase 1 is ready to support falsification; it is not ready to support a launch decision.
