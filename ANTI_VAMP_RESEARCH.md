# Memecoin anti-vamp research: goal, approach, and complete findings

30 October 2026. This is the current project explanation and consolidated research record.

## Your goal in simple English

You want to stop a successful meme's launch being weakened when many copycat coins appear and split the same crowd's attention and buying money.

For example, one meme coin starts gaining attention. Nine copies appear with similar names or images. People interested in that one meme end up buying ten different tokens, each with its own market. The meme can be popular while each individual market is thinner than it could have been.

Your goal is to help that crowd coordinate around one clearly identified coin during the launch's important first minutes. Success means a larger share of that meme's actual buying and usable trading depth reaches that coin. There is no requirement that the memecoin last forever. Early original buyers making a profit is compatible with this goal.

## How you are trying to achieve it

The direction is an open launchpad with a shared discovery and optional purchase layer:

1. **Keep launching open.** Anyone can create a coin, including a copy. The concept has no platform launch fee or required creator purchase. Network and account costs still need a payer. The simulations use abstract costs, not live fee quotes.
2. **Give one meme a common discovery page.** Related mints appear under one narrative instead of automatically giving every new copy another full feed slot. People can still inspect and choose individual coins.
3. **Identify the coin the page recommends.** The most promising tested anti-vamp rule is original-first: retain a fixed, disclosed original/canonical mint rather than awarding the traffic to whichever token temporarily has the highest market cap.
4. **Ask buyers to choose that actual mint.** A narrative visitor can choose the canonical coin directly. A visitor on a copy's page can review an offer to buy the canonical coin instead. The received token and mint must be clear before authorization.
5. **Concentrate new buying.** Those authorized orders add backing and trading depth to the same market. An existing holder's token or collateral is not moved by a label, recommendation, or ranking change.

This combines attention through discovery and concentrates liquidity through new paid orders. The current preferred version does not merge existing pools, confiscate losing holders' funds, require migration, or force unrelated interfaces to route orders. A shared label alone cannot move liquidity.

Here, canonical means the specific mint the group asks buyers to coordinate around. It is a disclosed coordination choice. First registration is not proof of true authorship. The default simulation assumes the real original registers first; a separate stress deliberately breaks that assumption.

## What was tested

| Stage | Question | Completed evidence | How to interpret it now |
| --- | --- | --- | --- |
| Phase 1 review | Are the four mechanism proposals and accounting assumptions coherent? | Prior art, mechanism designs, invariants, research plan, read-only review and arithmetic checks | Foundation; the initial review was not a full economic experiment |
| Four-mechanism study | A independent launches; B fee-fed winner; C winner routing; D conditional narrative auction | 10,000 corrected worlds on 100 paired confirmation seeds; 200 exploratory migration-holding runs | Broad synthetic comparison, originally focused on seven-day outcomes |
| Open-launch C follow-up | Can C work with cheap open entry, spam, voluntary consent, and outside options? | 5,600 confirmation worlds on 100 fresh paired seeds; 1,200 exploratory selling-policy worlds | Shows behavior sensitivity and election capture; its seven-day measure is not the final anti-vamp success criterion |
| Corrected anti-vamp study | One original plus 9, 49, or 99 copies; what happens in the first 5–60 minutes? | 11,700 confirmation worlds on 100 fresh paired seeds; 19 implementation tests; 3 exact replays | Main evidence for the clarified objective |

World counts include multiple conditions and attack controls on the same tapes. The 11,700 worlds are not 11,700 independent samples; confirmation inference uses 100 paired seeds. Development/training runs and corrected reruns are not extra independent confirmation observations.

The four original proposals were:

- **A, independent launches:** each coin trades on its own curve. This is the comparison group.
- **B, fee-fed winner:** a disclosed portion of trading fees buys the selected winner; modeled variants use different fee sources, locks, and destruction rules.
- **C, winner-directed routing:** buyers explicitly authorize new purchases of the selected mint; earlier research also tested voluntary holder migration. The latest anti-vamp version uses routing only and tests original-first separately from elections.
- **D, narrative auction:** people commit conditional capital before settlement, with allocations and refunds governed by preset rules.

## The main finding in plain English

In the latest one-original-plus-nine-copies experiment, the original received about a quarter of the meme's recent buying when every market operated independently. With original-first routing, it received about half. The original's measured usable sell depth also roughly doubled.

| Minute-15 measure | Independent markets | Original-first | Two-minute market-cap election |
| --- | --- | --- | --- |
| Original's share of recent narrative buying | 25.3% | 51.1% | 35.9% |
| Original's organic-holder sell depth at 5% marginal impact | 69.21 | 137.27 | 95.75 |

The buying share is measured over minutes 10–15. Depth is an executable measure in abstract quote units under the modeled curve, not market cap. It excludes attacker inventory. The original-first paired share improvement is 25.7 percentage points, with a 95% seed interval of 24.6–27.0 points. Depth improves by 68.06, interval 65.46–70.74.

The default assumes the router reaches 60% of eligible copy-directed buying and a 60% consent ceiling; loyalty reduces actual conditional consent to about 58%. Those assumptions have not been measured with real users.

With full reach and a 100% consent ceiling, realized consent is about 95%; the original receives 96.4% of recent buying and has depth 254.57, close to the no-copy reference's 264.08. That result illustrates what near-complete coordination could do in this model. It is not an adoption forecast.

The study keeps the same audience and money across comparisons. It demonstrates redistribution of assumed buying into fewer markets. It does not demonstrate that a real interface creates more attention or attracts additional buyers.

## Why original-first currently fits the goal better than an election

A market-cap election can turn the buying stream into a prize. In the tested two-minute contest, a trained actor buying a copy made that copy win in all 100 confirmation seeds. With nine copies, that policy earned 1,183.59 after complete exit, versus 318.25 for the exact same trade in independent markets. The additional 865.35 is evidence of a profitable contest-capture strategy within the tested search.

When the original-first recipient was correctly registered, buying a copy could not change it. Copies could still trade and sometimes make money. The rule removes this particular way to buy the routing prize; it does not prove universal manipulation resistance.

Buying the true original early also became more profitable with routing. That is ordinary early participation in the focal market, and is compatible with the stated anti-vamp goal. Profit alone is not the failure measure. The relevant distinction is whether a copy can purchase control of the new buying stream.

## The unresolved part: which coin is the original?

The identity decision is the main unsolved dependency. When a lookalike registers one second before the true original, original-first routes toward the wrong mint. In that stress, the true original's buying share falls from 25.3% without routing to 16.0% with the false-first rule.

A timestamp, name, ticker, or image match cannot by itself prove authorship. A product needs a clear process for canonical assignment, visible supporting evidence, disputes, false grouping, and legitimate competing communities. These rules have not been implemented or validated. Changing a label must not rewrite previously authorized orders or transfer existing backing.

The other major dependency is reach and willingness. A router only influences orders that pass through a participating interface and choose its suggestion. It cannot stop someone launching a token elsewhere or buying through another venue. Its effect falls when buyers are not reached or prefer the copy.

## What the earlier findings do and do not say

In the original four-mechanism study, B did not show a durable backing benefit, C increased seven-day cohort backing under its default assumptions, and D performed poorly under its allocation/participation design and bounded attacks. C's result was sensitive to holding behavior. In the open-launch follow-up, its favorable default seven-day backing result reversed under a different sale rule.

Those findings remain part of the evidence and are preserved below. They test broader questions than the clarified objective. They do not establish that routing fixes vampires, and they do not reject a launch-hour concentration mechanism simply because a memecoin later loses activity. The latest study changes the experiment to one original and its copies, and prioritizes early concentration and copy-led capture.

## Current decision and next implementation brief

**Proceed with a research prototype of shared discovery and explicit canonical-mint routing.** The evidence does not yet support a production launch or a claim that the vampire problem is solved. A market-cap contest is not the preferred original-protection rule because the tested actor can win it using a copy.

The next prototype should make the following concrete:

1. **Canonical assignment and grouping.** Show the narrative, candidate mints, why a mint is recommended, and a clear dispute state. Test preclaims, misleading names/images, false merges, missed copies, and legitimate forks. A disputed identity can pause the recommendation while direct mint selection remains available.
2. **Two purchase paths.** A shared narrative page offers the named canonical mint and a list of alternatives. A coin page offers direct purchase plus a separate review of the canonical coin. The confirmation binds the received mint, input amount, minimum output, fee, expiry, and destination. No silent switch after signing.
3. **Independent funded markets.** Keep reserves, creator fees, balances, and selling rights per mint. Reuse exact accounting and refusal tests. Do not invent liquidity for a new copy or move an existing holder's collateral.
4. **Measure the launch window.** Compare independent discovery with shared discovery/routing over 5, 15, 30, and 60 minutes. Measure original and top-mint buying shares separately, actual usable depth, total funded fills, rejected offers, outside purchases, and time to concentration with minimum-volume rules.
5. **Test the missing real behavior.** Measure whether people find the group, recognize the mint, accept a suggestion, and complete a purchase. Use those observed rates for a new predeclared simulation rather than treating current consent assumptions as facts.
6. **Train adversaries against the exact new rules.** Include preclaiming, paid social/discovery manipulation, late copies, creator-controlled copying, multiple wallets with a shared budget, and alternative interfaces. Distinguish ordinary early original profits from copy-led redirection or deceptive recipient changes.

The existing interface preview is a concept from the earlier elected-lead study. It illustrates explicit mint choice, but is not an implementation of a resolved canonical-identity system. Its time-weighted election and other earlier safeguards remain historical alternatives, not validated solutions to original identification.

## Where everything is

- `ANTI_VAMP_RESEARCH.md`: this single consolidated narrative, including the complete source documents in appendices.
- `research/anti_vamp_consolidation/`: all follow-up evidence, exact source snapshots, reports, tests, reproduction notes, and interface preview from this chat.
- `NARRATIVE_RESEARCH_FINDINGS.md` and `research/narrative_consolidation/bounded_study/corrected_v2/`: the earlier corrected four-mechanism study already in this project.
- Root Phase 1 and earlier shared-curve files: preserved as project history, with their original scope.

All studies are off-chain synthetic research. Human attention, consent, grouping, and creator behavior are assumptions. These models do not reproduce Pump's virtual-reserve curve, graduation, or live order execution. No real wallets, user accounts, funds, or deployed contracts were used.

The appendices preserve documents verbatim. Their older decision language and seven-day objectives should be read with the stage and scope above. Earlier statements that the repository was read-only describe those completed experiments; the later, user-authorized publication adds this package.

---

## Appendix 1: Latest anti-vamp findings

Source: `ANTI_VAMP_FINDINGS.md`. Original document follows.

# Anti-vamp study: one original, many copies, first hour

30 October 2026. Completed synthetic test. The objective is early concentration of one meme's buying and usable liquidity, not seven-day survival.

## Decision against the anti-vamp objective

**Conditional go for an original-first routing prototype as an anti-fragmentation mechanism, within these assumptions.** The goal is to concentrate the original meme's early market, not make a coin survive indefinitely. Creation remains open and unredirected purchases remain possible.

- At default 60% reach and 60% consent ceiling, original-first raises the original's minute-15 recent buying share from 25.3% to 51.1% and its organic-holder 5%-impact sell depth from 69.21 to 137.27. This is a measured recovery of concentration, not new money.
- With 100% reach and 100% consent ceiling, loyalty leaves realized consent around 95%. The original receives 96.4% of recent buying and depth is 254.57, versus 264.08 in the no-copy reference. High reach and willingness can therefore approximate the unfragmented market in this particular model.
- The two-minute cap election can also consolidate a market, but a trained copy-target policy makes the copy the selected recipient in all 100 confirmation seeds. With nine copies it earns 1,183.59 versus 318.25 for the same trade in independent markets, an additional 865.35. Buying the original early is a separate ordinary speculation case, not automatically a vampire exploit.
- With correct first registration, the tested copy purchases cannot replace the original-first recipient. That does not mean the copies cannot trade or their holders cannot profit; the mechanism reduces the routing advantage of competing copies rather than banning them.
- The central unresolved product choices are defining the canonical original mint, obtaining real order-flow reach, and buyers choosing the proposed recipient. A false-first registration sends recommendations to the wrong asset. The simulation does not validate an authenticity classifier or actual adoption.

**Research preference:** shared narrative discovery plus explicit original-mint purchases is more aligned with protecting the original than a capital contest that awards a copy the buying stream. If the objective is instead whichever coin becomes a focal point, report elected-lead concentration separately; a copy winning is not itself a failure on that different objective. These are off-chain synthetic findings, not a production validation.

## Primary result

With one original and nine copies, immediate original-first routing changes the original's share of executed narrative buying in the five-minute window ending at minute 15 from **25.3% to 51.1%**. The paired difference is **25.7 percentage points**, with 95% interval [24.6, 27.0].

Original-holder executable sell depth at 5% marginal impact changes from **69.21 to 137.27 quote units** at the same checkpoint. The difference is 68.06, interval [65.46, 70.74]. The no-copy reference's original depth is 264.08. These are funded, instrument-specific execution measures, not market cap or newly created money.

The key interpretation is whether routing recovers concentration quickly, how much traffic/consent it requires, and whether an elected lead can be captured by a copy. A profitable early original-holder trade is not automatically a vampire exploit or a reason to reject this objective.

## What actually ran

- 95 unique no-active-attack economic cells × 100 fresh paired seeds: 9,500 worlds.
- Trained-strategy and exact-same-policy independent controls: 2,200 additional worlds.
- **Total confirmation: 11,700 worlds**, seeds 50000–50099. 58,500 checkpoint/terminal rows and 702,000 minute-flow rows.
- Development pilot: 90 worlds on seeds 3000–3004. Training: 1,800 worlds on distinct seeds 500–511. Training and repeated settings do not increase the 100-seed confirmation sample size.
- Nineteen implementation tests pass, including funding, consent, lot isolation, no-copy world funding, deterministic replay, an independent invariant check, no-winner fallback, and false first registration.
- Three arbitrary confirmation worlds replay exactly. The original repository remains read-only; preservation is checked separately.

The v1 development plan and pilot are preserved. Before training/confirmation, the design added a no-copy reference and explicit narrative fills, and used deterministic process parallelism. Before confirmation, copy-only strategies were selected separately from the already completed disclosed training grid. Both pre-confirmation versions are retained. No confirmation result was used to tune parameters or policies.

## The experiment

One true-original asset launches at time zero. Nine, 49, or 99 lookalikes follow, beginning after 15 seconds and normally all within three minutes. All refer to the same narrative. There are no ten unrelated fundamental demands or independent narrative endowments.

Each seed has the same 480 narrative visits, timestamps, users, and budget opportunities across matched worlds. Defaults are a ten-minute attention-arrival half-life within a one-hour horizon; 25% of post-copy landing intentions favor the original and 75% favor copies collectively. Copy intentions split uniformly unless a named viral-copy sensitivity gives one copy tenfold weight. More coins divide existing visits; they do not create more buyers or money.

World endowment is fixed at 39,100 quote: 32,000 across 64 traders, 2,000 across original/copy creators, 5,000 for a trading actor, and 100 sponsor cash. Platform launch fee and required creator buy are zero. Each creator funds .01 network cost and .02 account deposit. No free redeemable allocations exist. The no-copy control parks unused creator capital; its copy-creator cash metric is N/A, not an economic loss.

All markets use the earlier independently funded integer linear curve, with a=.01, b=.0001, quote quantum 10^-6 and claim quantum 10^-4. Default fees total .4%, including .3% creator fees; a 1.25% total-fee sensitivity is separate. This is not a replication of Pump's virtual reserves or graduation process. Each mint keeps its own reserve and creator fees. No loser principal is confiscated or migrated.

**Independent:** all buyers buy their intended mint.

**Original-first:** a fresh buyer at a participating copy entry point may authorize the first-registered mint instead. The first registration is fixed; it is not an identity oracle proving true authorship. In the default case the true original registers first. The false-first stress explicitly breaks that correspondence.

**Elected:** independent trading continues until a frozen market-cap selection after 30 seconds, two, five, or fifteen minutes. Only observations before close select the lead. After that, newly authorized orders may buy it. No eligible winner or a tie gives direct trading. An election can concentrate on a copy; that is distinct from protecting the original.

Default router reach and consent ceiling are both 60%. Loyalty modestly reduces realized consent. Buyers declining a recommendation buy their preferred mint in the primary experiment. Named sensitivities instead let them retain cash or buy an outside asset. Total narrative execution and top-flow capture of common latent budgets are recorded so abandonment cannot masquerade as successful concentration.

The primary holding rule sells only the acquisition lot associated with a planned sale. A whole-position sale sensitivity is separate. No winning-generated attention or external money is added. User acceptance, attention, copy arrivals, and holding behavior remain uncalibrated synthetic assumptions.

## Minute-15 concentration and depth

Shares are of executed narrative buy quote over minutes 10–15. Top share is the largest actual mint's share, whether original or copy. Original depth is constrained by organic holder inventory and actual backing. The selected lead's depth is separately compared with the same mint in the independent world in `paired_effects.csv`.

| Coins | Mechanism | Original buy share | Largest buy share | Original depth | Selected depth | Narrative fills / latent budgets |
| --- | --- | --- | --- | --- | --- | --- |
| 10 | independent | 25.3% | 25.5% | 69.21 | N/A | 100.0% |
| 10 | original_first | 51.1% | 51.1% | 137.27 | 137.27 | 100.0% |
| 10 | elected_30s | 43.7% | 48.4% | 117.95 | 129.79 | 100.0% |
| 10 | elected_120s | 35.9% | 46.4% | 95.75 | 118.97 | 100.0% |
| 10 | elected_300s | 47.3% | 50.1% | 112.99 | 117.76 | 100.0% |
| 10 | elected_900s | 25.4% | 25.5% | 69.25 | 69.29 | 100.0% |
| 50 | independent | 25.3% | 25.3% | 69.21 | N/A | 100.0% |
| 50 | original_first | 51.1% | 51.1% | 137.27 | 137.27 | 100.0% |
| 50 | elected_30s | 47.3% | 49.3% | 126.87 | 131.71 | 100.0% |
| 50 | elected_120s | 50.0% | 50.7% | 128.64 | 130.32 | 100.0% |
| 50 | elected_300s | 51.1% | 51.1% | 120.54 | 120.54 | 100.0% |
| 50 | elected_900s | 25.4% | 25.4% | 69.25 | 69.25 | 100.0% |
| 100 | independent | 25.3% | 25.3% | 69.21 | N/A | 100.0% |
| 100 | original_first | 51.1% | 51.1% | 137.27 | 137.27 | 100.0% |
| 100 | elected_30s | 49.4% | 50.2% | 132.23 | 134.24 | 100.0% |
| 100 | elected_120s | 50.6% | 50.9% | 130.51 | 130.90 | 100.0% |
| 100 | elected_300s | 51.1% | 51.1% | 120.54 | 120.54 | 100.0% |
| 100 | elected_900s | 25.4% | 25.4% | 69.25 | 69.25 | 100.0% |

## How quickly concentration appears

| Mechanism | Original ≥50% by 15m | Original ≥70% by 15m | Any coin ≥70% by 15m | Median time to original 50%, among hits |
| --- | --- | --- | --- | --- |
| independent | 0.0% | 0.0% | 0.0% | 45.00 |
| original_first | 82.0% | 1.0% | 1.0% | 8.00 |
| elected_30s | 64.0% | 1.0% | 1.0% | 8.00 |
| elected_120s | 45.0% | 1.0% | 1.0% | 10.00 |
| elected_300s | 62.0% | 1.0% | 1.0% | 12.00 |
| elected_900s | 0.0% | 0.0% | 0.0% | 24.00 |

The timing benchmark requires two consecutive minute observations of five-minute flow, at least five fills and 100 quote in each, and starts only after a full copy-exposure window. Non-reached cases are censored; the median among hits must not be read as the median across all worlds. Fifty/seventy percent are descriptive research benchmarks, not promises or empirically chosen adoption targets.

## Early versus delayed selection

| Checkpoint | Mechanism | Original buy share | Largest buy share | Original depth | Mean fills in trailing 5m |
| --- | --- | --- | --- | --- | --- |
| 5m | independent | 28.5% | 28.8% | 56.42 | 143.18 |
| 5m | original_first | 53.1% | 53.1% | 109.29 | 143.18 |
| 5m | elected_120s | 35.1% | 41.0% | 73.52 | 143.18 |
| 5m | elected_300s | 28.6% | 28.8% | 56.74 | 143.18 |
| 15m | independent | 25.3% | 25.5% | 69.21 | 72.31 |
| 15m | original_first | 51.1% | 51.1% | 137.27 | 72.31 |
| 15m | elected_120s | 35.9% | 46.4% | 95.75 | 72.31 |
| 15m | elected_300s | 47.3% | 50.1% | 112.99 | 72.31 |
| 30m | independent | 26.1% | 29.2% | 72.05 | 25.69 |
| 30m | original_first | 53.0% | 53.0% | 142.77 | 25.69 |
| 30m | elected_120s | 38.6% | 48.1% | 100.73 | 25.69 |
| 30m | elected_300s | 48.8% | 51.6% | 119.05 | 25.69 |
| 60m | independent | 26.9% | 64.5% | 73.86 | 2.94 |
| 60m | original_first | 54.6% | 72.2% | 146.72 | 2.94 |
| 60m | elected_120s | 37.8% | 71.5% | 103.02 | 2.94 |
| 60m | elected_300s | 49.9% | 71.5% | 122.30 | 2.94 |

Late low-volume intervals can have unstable shares; the early 5–15 minute checkpoints and minimum-volume timing tests are the main evidence. There is no requirement that activity or money survive indefinitely.

| Election delay | Common latent buy budget still scheduled afterward |
| --- | --- |
| 0.5 minutes | 96.5% |
| 2 minutes | 86.7% |
| 5 minutes | 70.1% |
| 15 minutes | 34.0% |

These budget fractions quantify how much demand a fresh-order router can still affect under the primary hype curve. They are opportunities, not guaranteed funded fills or new deposits.

## Reach and willingness

| Reach | Consent ceiling | Original share at 15m | Original depth | Realized reachable-order consent, quote weighted |
| --- | --- | --- | --- | --- |
| 30% | 30% | 31.8% | 86.36 | 28.5% |
| 30% | 60% | 38.2% | 103.79 | 57.6% |
| 30% | 100% | 47.3% | 126.06 | 95.2% |
| 60% | 30% | 38.5% | 103.51 | 28.9% |
| 60% | 60% | 51.1% | 137.27 | 57.6% |
| 60% | 100% | 68.0% | 181.62 | 95.0% |
| 100% | 30% | 47.8% | 125.99 | 28.7% |
| 100% | 60% | 68.5% | 181.47 | 57.0% |
| 100% | 100% | 96.4% | 254.57 | 95.0% |

With direct fallback and comparable fills, the accounting intuition is original share ≈ s+(1−s)×reach×actual consent. With original share s=.25, reaching .70 requires the product of reach and actual consent to be about .60. This is a mechanism constraint under the simplified split, not a measured real-user threshold. A shared group-buy button may reach a different self-selected audience than persuading people already intending a particular copy; that behavioral distinction is not calibrated here.

## Copy-led capture versus ordinary early-original trading

The policy grid includes abstention, targets original (0) or the first copy (1), budgets 500/2,000, fixed public start times, and exits at 5/15/30 minutes. Each actor has only its funded 5,000. The actor is a trader and does not receive creator fees; pooled creator control and arbitrary attacker programs are outside this search.

The overall profit-maximizing policy and the best copy-only policy are selected separately on training seeds, with abstention eligible. Exact same size/timing/target/exit policies are run against independent markets. Total profit alone is not an exploit finding: buying the original early is normal memecoin speculation. A funded copy winning the recommendation and receiving additional redirected demand is the contest-capture case.

| Base cell | Policy family | Bought mint | Budget | Actor profit | Same policy A | Extra vs A | Selected mint equals bought mint at 15m | 95% interval for extra |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| copies9__independent | overall | 0 | 2000 | 925.05 | 0.00 | 925.05 | 0.0% | [905.38, 945.67] |
| copies9__original_first | overall | 0 | 2000 | 1,652.54 | 925.05 | 727.48 | 100.0% | [709.44, 745.71] |
| copies9__elected_120s | overall | 0 | 2000 | 1,574.43 | 925.05 | 649.38 | 100.0% | [633.68, 665.92] |
| copies9__elected_300s | overall | 0 | 2000 | 1,462.25 | 925.05 | 537.20 | 100.0% | [519.91, 554.10] |
| copies99__original_first | overall | 0 | 2000 | 1,652.54 | 925.05 | 727.48 | 100.0% | [709.46, 745.15] |
| copies99__elected_120s | overall | 0 | 2000 | 1,574.43 | 925.05 | 649.38 | 100.0% | [632.61, 665.66] |
| copies9__independent | copy_only | 1 | 2000 | 318.25 | 0.00 | 318.25 | 0.0% | [279.48, 354.80] |
| copies9__original_first | copy_only | 1 | 500 | 212.26 | 293.93 | -81.67 | 0.0% | [-94.49, -67.88] |
| copies9__elected_120s | copy_only | 1 | 2000 | 1,183.59 | 318.25 | 865.35 | 100.0% | [843.98, 889.20] |
| copies9__elected_300s | copy_only | 1 | 2000 | 1,042.11 | 318.25 | 723.86 | 100.0% | [700.48, 745.78] |
| copies99__original_first | copy_only | 1 | 500 | 20.49 | 29.26 | -8.77 | 0.0% | [-17.45, 0.55] |
| copies99__elected_120s | copy_only | 1 | 2000 | 992.26 | -34.48 | 1,026.74 | 100.0% | [1,003.49, 1,050.23] |

For original-first with correct registration, buying a copy cannot replace the recipient. It can still be profitable to speculate on that independently traded copy. Likewise, stronger demand for the original can benefit its early holders without violating the anti-vamp goal. Inspect policy target and recipient, not just the profit column.

## First registration is not authenticity

This stress has a lookalike register one second before the true original. It is a conditional identity/coordination failure case, not an estimate of how often preclaiming occurs.

| Mechanism | True-original buy share at 15m | Selected-lead buy share | True-original depth |
| --- | --- | --- | --- |
| independent | 25.3% | N/A | 67.10 |
| original_first | 16.0% | 40.8% | 44.00 |
| elected_120s | 24.8% | 43.2% | 67.01 |
| elected_300s | 44.7% | 49.3% | 105.77 |

An original-first product needs a clearly disclosed canonical mint and a way for buyers to judge that assignment. A name, ticker, semantic group, or first timestamp alone cannot prove authorship. Disputes cannot rewrite previously authorized assets or seize backing.

## Evidence and reproduction

The bundle contains the predeclared plan, both pre-confirmation revisions, frozen policies/source hashes, full primary and policy controls, minute flow, checkpoints, timing distributions, financial traces, raw training outcomes, tests, exact replays, and preservation inventory.

Copy `source/anti_vamp` to `work/anti_vamp` and `source/select_anti_vamp_copy_families.py` to `work/select_anti_vamp_copy_families.py` in a fresh directory. Run `python -B -m unittest discover -s work/anti_vamp -p test_model.py -v`. Then run `study.py init`, `pilot`, and `train` using `python -B work/anti_vamp/study.py <stage>`. Before confirmation, run `python -B work/select_anti_vamp_copy_families.py` to freeze the separate copy-only selections from the completed training grid. Finally run `study.py confirm` and `study.py analyze`. Do not overwrite this completed directory. No live chain, user accounts, or real funds are required.

Sampling intervals use paired seeds; wallets, minute observations, policy copies, and duplicate aliases are not additional independent samples. Most sensitivity comparisons are exploratory. The study evaluates liquidity concentration given assumed visits and consent; it does not measure human attention growth, grouping accuracy, platform adoption, creator equilibrium, or production security.


---

## Appendix 2: Open-launch C findings, including selling-policy audit

Source: `C_PERMISSIONLESS_FINDINGS.md`. Original document follows.

# C on an open launchpad: completed follow-up

30 October 2026. Synthetic, off-chain research. No deployment, wallet use, real funds, or empirical adoption calibration.


**Updated assessment after the selling-policy audit:** The basic routing benefit reverses under lot-based sales. The favorable primary base result is not robust to this holding-policy change. C retains less backing than matched A in the 90-spam environment under both tested selling rules. That remains a model-conditional stress result. The tested capture policies remain a separate reason to withhold a launch recommendation. See the final appendix before interpreting the primary table.

## Decision in plain English

Permissionless creation and optional consolidation can be separate layers. Anyone can create an independent coin; one narrative page gathers discovery, and a fresh buyer may explicitly choose its current lead. The platform cannot redirect third-party purchases or move existing holder collateral without authorization.

The fresh-seed base comparison changes seven-day whole-narrative backing from 800.61 in A to 858.07 in C: 57.46 (+7.2%), with a 95% paired seed-bootstrap interval [37.50, 77.00]. This is routing only: holder migration is disabled throughout this extension. It is a conditional model result, not a real-market forecast.

The safeguards and open-entry stresses below test both the possible benefit and the capture costs. Interpret attack profits against independently trained A and the same-policy A controls; ordinary early trading can also be profitable in A.

## What actually ran

- 21 matched environments, each with A and C: 4,200 no-active-trading-attack confirmation worlds.
- Eight independently selected policy targets: 800 trained-policy confirmation worlds.
- Six additional A controls receiving the exact frozen C policy: 600 worlds.
- Total: **5,600 confirmation worlds**, **100 fresh paired seeds 30000–30099**, and **22,400 checkpoint/terminal rows**.
- Development: 40 pilot worlds on seeds 2000–2004. Attack training: 3,200 worlds on separate seeds 200–219, using 20 candidate strategies per target. Development and training do not increase the confirmation sample size.
- All settings and the policy class were written before confirmation. Attack choices were frozen after training. Confirmation source hashes are enforced. There was no outcome-dependent early stopping or retuning.
- Eighteen new implementation tests passed. An expiry-boundary bug was found and corrected before predeclaration; the development record identifies it. The existing repository suite was not rerun because its code was copied read-only and never changed.
- Three arbitrary stored worlds replay with exact output hashes. Integer conservation and ownership assertions run at every observation and terminal checkpoint.

The primary prespecified contrast is base C versus matched A for seven-day backing. All other intervals are exploratory; there is no multiple-comparison-adjusted claim that every favorable cell will generalize. Sampling intervals omit uncertainty about real human behavior.

## Model and permissionless boundaries

The experiment uses an isolated copy of the previous integer independent-curve ledger, not modifications to the original repository. The curve remains a=.01 and b=.0001, quote quantum 10^-6, claim quantum 10^-4. It does not reproduce Pump's virtual-reserve formula or graduation into an AMM.

Every world has 39,100 quote units: 32,000 across 64 traders, 2,000 across ten original creators, 5,000 for the coordinated actor, and 100 for a sponsor. There are 480 common latent opportunities and the same original trader budgets across matched worlds. Extra mints create no additional money or opportunities. Sales and refunds reuse owned cash; no external replenishment occurs.

There is no platform launch fee in the base case and no mandatory creator purchase. Each launch incurs a synthetic .01 network payment and .02 account deposit, paid by the creator or attacker. The sponsorship sensitivity pays those costs from the same finite 100-unit sponsor. Deposits remain separately named cash accounts; no recoverability or token-market backing is assumed within the observation horizon. Cash P&L excludes them. These are abstract research costs, not current SOL conversions.

Ten original creators can launch externally in the outside-creator stress. Whole-narrative backing includes their markets, preventing an apparent gain from simply dropping refused creators from the denominator. Platform-only and all-market backing, including the separate outside alternative, are also exported. Fees earned by attacker-created mints are credited to the same real actor, including self-payments; they are not new capital.

The 10/90-spam settings have 20/100 total possible mints. The spam count is an exogenously declared stress; it is not an estimate of equilibrium launch supply. Creating more mints uses the actor's existing budget. Half the arrivals in the raw-feed stress receive equal per-live-mint discovery exposure; this is an explicit naive-feed assumption. The grouped-intentions setting removes that per-mint discovery lottery and preserves incoming preferences, without minting more demand. It does not validate a semantic classifier or prove a real grouped interface raises attention.

Late mints can launch and trade after close. They cannot reopen the fixed thirty-minute election. A fresh buyer can still explicitly choose the incumbent from a late entrant's native entry point. No existing position is converted. Multi-round leader changes, legitimate new entrants bringing fresh audiences, classifier false positives, and a creator participation equilibrium remain unimplemented.

The base acceptance ceiling is .6 and reach is .6. Loyalty and price reduce actual synthetic consent. Rejected buyers choose the preferred asset with probability .5, the outside alternative with probability .25, or retain cash otherwise. These are assumptions, not measured preferences. Directly choosing a mint and accepting a recommendation are different orders. Zero-reach and zero-acceptance-with-direct-fallback controls are covered by implementation tests.

The `active` count includes funded organic fills in any modeled market, including the outside alternative, over trailing 1h/6h/24h windows. It is not platform-only activity. Seven-day timestamps do not establish seven-day real-market survival.

## Retained backing at seven days

| Environment | A backing | C backing | C−A | 95% paired interval | Relative mean change |
| --- | --- | --- | --- | --- | --- |
| Free launch; routing only | 800.61 | 858.07 | 57.46 | [37.50, 77.00] | +7.2% |
| 10 additional spam mints | 1,620.37 | 1,455.74 | -164.64 | [-191.89, -139.13] | -10.2% |
| 90 additional spam mints | 2,519.72 | 2,094.48 | -425.24 | [-457.26, -394.32] | -16.9% |
| 90 late spam mints | 1,384.17 | 1,180.78 | -203.39 | [-229.37, -178.80] | -14.7% |
| 20% router reach | 800.61 | 833.54 | 32.93 | [21.01, 43.74] | +4.1% |
| 50% creator outside probability | 800.61 | 834.72 | 34.11 | [19.46, 50.50] | +4.3% |
| Low acceptance ceiling | 800.61 | 776.86 | -23.75 | [-39.64, -7.09] | -3.0% |
| 90 spam; grouped incoming intentions | 800.61 | 858.07 | 57.46 | [37.57, 77.96] | +7.2% |
| 1.25% underlying trading fees | 794.03 | 850.77 | 56.75 | [36.87, 78.17] | +7.1% |
| Additional 0.45% router fee | 800.61 | 857.29 | 56.68 | [36.75, 75.86] | +7.1% |
| Daily routing budget | 800.61 | 793.04 | -7.57 | [-23.41, 7.52] | -0.9% |
| Six-hour expiry | 800.61 | 888.95 | 88.34 | [74.70, 101.84] | +11.0% |
| Time-weighted cap and minimum age | 800.61 | 854.93 | 54.32 | [33.02, 74.77] | +6.8% |
| Relative-price limit | 800.61 | 815.99 | 15.38 | [-2.07, 32.84] | +1.9% |
| Combined safeguards | 800.61 | 824.63 | 24.02 | [16.32, 32.07] | +3.0% |
| Combined safeguards with 90 spam | 2,519.72 | 2,396.75 | -122.97 | [-139.13, -106.28] | -4.9% |

Relative changes are ratios of mean differences to mean A backing. Confidence intervals are in quote units. The curve shape is identical within every matched pair. All results are after normal scheduled sells and before forced diagnostic terminal exits.

In the base case, 5%-impact winner sell depth changes from 16.81 to 36.34. Its paired difference is 19.53 [17.57, 21.68]. Funded active-trader count across all modeled markets changes from 15.62 to 14.73. These measures answer different questions from whole-narrative backing.

## Strategic capture

Policies vary an actor-funded purchase budget of 250/1,000/3,000, purchase at 5%/85% of the contest window, and exit at finalization/one hour/six hours after finalization. Abstention and a 32-wallet split are included, for 20 candidates per target. The actor has 5,000 total across all aliases. In spam settings the same actor also pays launch costs and collects its mints' actual creator fees.

Training maximizes terminal cash P&L within this disclosed class; selected policies must fully exit token inventory in training. Both A and C are optimized separately for the base and 90-spam environments. Guarded C policies are also evaluated against A with the very same settings, size, timing, and exits. This is a bounded search, not a proof of a globally optimal attack.

| Environment | Model | Total actor cash P&L | Idle actor P&L | Added P&L vs idle | 95% interval for added P&L | Positive cash P&L | Peak deployed cash |
| --- | --- | --- | --- | --- | --- | --- | --- |
| base | A | 260.25 | 0.00 | 260.25 | [207.85, 311.34] | 85% | 1,000.00 |
| base | C | 767.91 | 0.00 | 767.91 | [686.48, 844.45] | 95% | 3,000.00 |
| spam90 | A | 49.18 | 46.48 | 2.70 | [-2.46, 8.01] | 99% | 110.25 |
| spam90 | C | 675.89 | 32.01 | 643.87 | [593.91, 695.01] | 99% | 2,986.43 |
| daily_cap | C | 626.55 | 0.00 | 626.55 | [544.74, 705.10] | 93% | 3,000.00 |
| timecap | C | 767.91 | 0.00 | 767.91 | [683.66, 848.22] | 95% | 3,000.00 |
| combined | C | 369.65 | 0.00 | 369.65 | [319.86, 420.24] | 93% | 1,000.00 |
| combined90 | C | 59.52 | 41.79 | 17.73 | [6.62, 30.22] | 99% | 110.25 |

“Idle” in a spam environment means no active trading attack, but the exogenous spam launches still occur and can earn creator fees. Thus total actor profit alone is not the incremental benefit of a capture trade. The added-P&L column controls for that income and launch expense. All token-exit residuals are exported; an inaccessible account deposit is not counted as realized cash or a market reserve.

### Exact C-policy comparison against A

| C environment | C actor P&L | A with identical policy | Additional P&L in C | 95% paired interval |
| --- | --- | --- | --- | --- |
| base | 767.91 | 218.29 | 549.62 | [513.99, 586.02] |
| spam90 | 675.89 | 9.28 | 666.60 | [625.44, 704.61] |
| daily_cap | 626.55 | 218.29 | 408.26 | [382.58, 435.19] |
| timecap | 767.91 | 218.29 | 549.62 | [509.83, 586.18] |
| combined | 369.65 | 260.25 | 109.40 | [93.80, 125.96] |
| combined90 | 59.52 | 49.18 | 10.34 | [1.70, 20.31] |

These are the appropriate within-policy comparisons for routing-amplified profit. An independently optimized A result remains a complementary check. Participant cash outcomes and attacker-induced trader losses are in `attacks.csv`; profit frequencies describe synthetic seeds, not the probability of an exploit on a real platform.

## Safeguards evaluated

- **Time-weighted cap:** integrate observable cap over the common pre-close window and require 300 seconds of age. Funding earlier remains allowed; the attacker is retrained.
- **Daily routing budget:** at most 25% of winner backing at close may be spent through recommendations per day. This is a whole-order limit; blocked orders fall back to the preferred mint without a failed-transaction cost. It is a flow limit, not an escrow fund. An attacker can increase the reference backing by purchasing before close.
- **Six-hour expiry:** after expiry, new orders return to ordinary direct choice. There is no forced sale or automatic re-election.
- **Relative-price limit:** offer the direct asset if the winner's marginal price exceeds 1.5 times the preferred asset's. Integer comparisons enforce this decision. It is meaningful only for this study's identical curve calibration, not arbitrary differently denominated real tokens.
- **Combined:** apply all four, including under 90 extra spam launches. Reducing attack returns by nearly disabling routing must not be confused with preserving the full economic benefit.

Extra 45-basis-point router fees apply only to routed purchases in their sensitivity and are paid from the same all-in budget. This is a generic execution-cost stress, not a replica of Pump's complete interface fee policy.

## Product implication

The concrete product is a shared narrative feed and an optional execution router over independent markets. A creator can launch without joining a fee pot. A coin page can offer the current lead while preserving direct purchase. Every purchase names the received mint and quote limits; a label change never changes old rights. External interfaces remain able to trade the original mint.

Pump's official documentation currently describes no platform creation fee, with network transaction costs and required account deposits still payable, and curve trading without a creator liquidity seed. That supports the launch-access analogy, not an assertion that Pump already implements this narrative mechanism. [Official fee page](https://pump.fun/docs/fees), [official program description](https://github.com/pump-fun/pump-public-docs/blob/main/docs/PUMP_PROGRAM_README.md).

See `PERMISSIONLESS_C_PRODUCT_DESIGN.md` for entry flows, rights, late launches, costs, and incentives. The in-conversation concept contains illustrative coins and sends no orders.

## Evidence and reproduction

`c_permissionless_study/` contains the predeclared plan, frozen policies/source hashes, training/pilot/confirmation manifests, raw compressed runs, paired effects, summaries, attack and same-policy controls, representative traces, exact-hash replays, new test output, and repository preservation check. The bundle records 5600 completed confirmation worlds with no run exception.

To reproduce without overwriting this bundle, copy the supplied `source/c_followup` directory into `work/c_followup` under a new empty working directory. Use Python with numpy and pandas. Run the following in sequence, keeping the existing research folder read-only:

```text
python -B -m unittest discover -s work/c_followup -p test_open_model.py -v
python -B work/c_followup/run_study.py init
python -B work/c_followup/run_study.py pilot
python -B work/c_followup/run_study.py train
python -B work/c_followup/run_study.py confirm
python -B work/c_followup/run_study.py analyze
```

On another machine adjust only the repository path used for its read-only preservation inventory before initializing the new study; the new plan will capture that source change. Do not overwrite or pool the existing confirmation bundle. The saved original repository and the isolated upstream source copy remain byte-identical to their captured hashes.

## Limits on the decision

This study can falsify a particular synthetic routing design and quantify behavior within its assumed model. It cannot establish user willingness, honest creator entry, a production identity/grouping system, an equilibrium spam rate, bot competition, optimal ordering protection, Pump-equivalent markets, or production permissionlessness. A go decision for real deployment would require those additional kinds of evidence. A better discovery interface is a testable product hypothesis even if electing a permanent financial winner is not supported.


## Additional sell-lot audit: 1,200 exploratory worlds

After primary confirmation, review identified another uncalibrated assumption: each scheduled sale in the primary model sells a fraction of the wallet's entire current position in that mint. Repeated purchases can therefore generate repeated whole-position sale events. Spreading acquisitions across many mints changes those interactions. This is an explicit behavioral policy, not a conservation error; it should not silently establish a general liquidity claim.

The additional audit sells a fraction of the quantity associated with the particular purchase that generated the sale intention. Independent lots remain separately owned; their sum must equal trader inventory before terminal liquidation. There is still no holder migration. The audit runs base, 90-spam, and combined-safeguard/90-spam environments using the same 100 tapes. Each has A/C without an active attack and the already frozen C policy in both A and C: 12 cells, 1,200 worlds, 4,800 observations. No policy is retrained. These are not 100 new independent seeds or replacement primary results.

| Environment | Primary C−A | Lot A backing | Lot C backing | Lot C−A | 95% lot paired interval |
| --- | --- | --- | --- | --- | --- |
| base | 57.46 | 3,468.13 | 3,086.43 | -381.69 | [-406.18, -357.15] |
| spam90 | -425.24 | 3,941.34 | 3,374.74 | -566.59 | [-600.00, -534.82] |
| combined90 | -122.97 | 3,941.34 | 3,677.46 | -263.88 | [-280.98, -246.38] |

The basic routing benefit reverses under lot-based sales. The favorable primary base result is not robust to this holding-policy change.

C retains less backing than matched A in the 90-spam environment under both tested selling rules. That remains a model-conditional stress result.

The unchanged C policy produces the following terminal actor cash outcomes, with the exact same policy in A:

| Environment | C actor cash P&L | Same policy in A | Extra P&L in C | 95% paired interval |
| --- | --- | --- | --- | --- |
| base | 1,079.41 | 458.29 | 621.12 | [582.49, 658.42] |
| spam90 | 763.39 | 9.23 | 754.16 | [722.36, 790.98] |
| combined90 | 60.55 | 49.13 | 11.42 | [2.21, 22.45] |

These contrasts remain conditional on the assumed policy class and synthetic demand. Where a tested policy is profitable, it is a funded counterexample; where it is not, the absence of retraining is not evidence of safety. In spam environments the actor also receives its mints' creator fees, so total profit must be distinguished from trading-attack income.

The audit adds two deterministic smoke checks: an exit attached to one purchase cannot sell another purchase's quantity, and repeated runs reproduce the same observations. Lot ownership coverage and the original integer money/claim invariants are checked during every world. See `lot_sensitivity/plan.json`, `runs.csv.gz`, `effects.csv`, `attacks.csv`, and `manifest.json`. To reproduce after the main study, copy `source/lot_sensitivity.py` to `work/lot_sensitivity.py` in the new study directory and run `python -B work/lot_sensitivity.py` once.

The decision is **no-go for a claimed durable or manipulation-resistant winner-routing launchpad on this evidence**. A shared discovery page with transparent direct coin choice remains a product hypothesis. Further routing research should treat sale behavior, repeat purchases, direct fallback, real consent/reach, and creator entry jointly rather than choosing whichever holding rule produces the best backing chart. The visual concept illustrates rights and choices, not a validated safe mechanism.


---

## Appendix 3: Earlier interface and mechanism design

Source: `PERMISSIONLESS_C_PRODUCT_DESIGN.md`. Original document follows.

# Open-launch narrative consolidation: product and mechanism

30 October 2026. Concept design accompanying a synthetic follow-up study. This is not a deployment specification or an audited on-chain implementation.

## The product in one sentence

Anyone can launch an independent coin; related coins share a discovery page, and a buyer can explicitly choose the group's current lead when placing a fresh order.

The grouping joins attention. Only an authorized purchase moves money into another mint. Existing holders, collateral, and creator fees do not move because a label or ranking changes.

## What “free to launch” means

Pump's official fee page, last updated 17 October 2026, says creating a coin has no platform fee; the creator still pays the Solana network transaction fee and required account deposit. Its program documentation describes immediate curve trading without creator-provided liquidity. These are separate ideas: zero platform launch fee, who pays network/account costs, and no mandatory liquidity seed. [Official fees](https://pump.fun/docs/fees), [program description](https://github.com/pump-fun/pump-public-docs/blob/main/docs/PUMP_PROGRAM_README.md).

Our proposed default follows those three distinctions. A creator can start without buying their own token. The first actual buyer funds issuance. Each mint has independent backing; ten launches do not receive ten subsidized reserves. Optional network sponsorship has an identified payer, finite budget, and measured costs. All costs in the simulation are abstract synthetic amounts, not conversions from current SOL prices.

## Two useful entry points

**Narrative first.** A person opens a single “Moon dog” page instead of ten repetitive feed cards. The page lists each independent coin and its actual mint, plus a temporary lead recommendation. “Buy the lead” names the received mint before confirmation. “Choose a coin” leads to its ordinary direct market. The recommendation has a published rule, timestamp, and expiry; it is not a claim of authenticity or future returns.

**Coin first.** A person opens ORBITDOG's page. Its direct purchase remains available. A separate offer says “This coin belongs to the Moon dog group. Review the current lead instead.” Only taking that offer changes the received asset. A copied ticker, URL visit, or existing token balance never grants routing permission.

The accompanying interactive concept uses fictional coins and illustrates both entry points. It sends no orders.

## Layers and authority

| Layer | Proposed behavior | What it does not confer |
| --- | --- | --- |
| Launch program | Anyone may create an ordinary funded-issuance market, subject to network execution and costs | Creation of other holders' money or a free redeemable allocation |
| Narrative index | Group related entries on one page; show disputed and late entries; permit alternative indexes | Ownership rights over any coin, power to seize backing, or proof that two creators are the same person |
| Public ranking | Compute a temporary lead from published observations and a frozen cohort | A guarantee of genuine demand, Sybil resistance, or a permanent canonical coin |
| Optional router | Honor an order binding the actual received mint, budget, fees, output limit, expiry, and fallback | Control over purchases on unrelated interfaces or external venues |
| Ordinary direct market | Continue buying and selling the selected mint independently | A mandatory contribution to the lead or surrender of losing holders' rights |

Permissionless creation can coexist with a curated interface. A production design must state which parts can be used without its operator. Alternative interfaces can use different narrative indexes and recommendations. The simulation is a model of open entry and optional routing, not a proof that an implemented chain service is permissionless.

## Open entry and cheap spam

A token may be created after the contest closes and still trade immediately. It can appear in the group with “late entrant” status, but cannot rewrite an already signed order or reopen the finalized cohort. A later contest would need a new public cohort/rule version and new user consent; the present study has one election only.

Do not hand each new mint an extra guaranteed slot in the main attention feed. One narrative card can represent many mints. Within it, users can inspect all entries. Grouping errors and ranking manipulation still require explicit handling; displaying one group does not establish that a classifier or score is correct.

No launch-count, per-wallet-holder, or per-wallet contribution bonus is presumed Sybil-safe. An attacker can create many mints or wallets. Any costly restriction must charge the actual actor-funded resource or identify a funded sponsor; it cannot assume known human identities.

## What could make creators join?

Ordinary coin creators retain their mint and its normal creator fee. Group discovery and optional referrals may be useful, but the study has not measured that value or creator willingness to participate. Redirecting traffic can also reduce a losing creator's expected income. They may launch through another venue, reject the interface, or encourage followers to use direct purchases.

Possible referral compensation would have to come from disclosed execution revenue or a named acquisition budget. Do not manufacture a reward per copy launched or promise losing creators a share of nonexistent winner revenue. The tested creator-outside setting is an exogenous stress, not a solved entry equilibrium.

## Safeguards under test, not assumed solutions

1. Time-weight the observed cap across the common contest window and require minimum age. An attacker can respond by funding earlier, so this needs retrained attacks.
2. Limit recommended purchase flow per day relative to the lead's actual backing at close. This limits a predictable buy wall, but can reduce useful routing and favor early orders. An attacker can also increase the reference backing. The simulation tests these responses.
3. Expire the recommendation after six hours, then return to ordinary direct choice. This is an expiry, not a forced sale or a silent new election.
4. Offer the direct coin when the lead exceeds a declared relative-price limit. This comparative rule is meaningful only within the simulation's identical curve calibration; real assets need actual asset-specific quotes and signed output limits.

Combining safeguards can suppress both gains and attacks. A positive result must distinguish that tradeoff from merely disabling the mechanism.

## Boundaries of the follow-up

The experiment uses the prior independent linear curve's integer ledger, 64 funded traders, fixed total endowments, and a fixed seven-day opportunity tape. It tests no mandatory seed, free creation, 0/10/90 extra spam mints, late launches, outside creators, reach/consent, a raw token-feed stress, grouped incoming intentions, fee costs, and a bounded attack search. It does not reproduce Pump's virtual-reserve formula, graduation/AMM migration, real content moderation, historical demand, user attention growth, creator entry equilibrium, or unrestricted attacker programs.

The proposed interface is therefore best understood as a discovery and execution layer over independent markets. Whether it creates a better market remains the empirical and adversarial question.


---

## Appendix 4: Completed four-mechanism study

Source: `NARRATIVE_RESEARCH_FINDINGS.md`. Original document follows.

# Narrative consolidation: completed bounded findings

This is an off-chain synthetic study. All behavioral parameters are assumptions;
no real-market validation, demand calibration, contracts, wallets or funds are
involved. The four earlier Phase 1 documents and all preexisting research are
preserved. Results below come from completed runs, not supported CLI flags.







<!-- reviewed-summary -->
The central result is conditional, rather than a blanket rejection of consolidation.
Without attacks, C retained 1223.33 versus A's 1074.57 quote units at seven days
(+13.8%) and improved the selected winner's private depth. It also
had fewer active traders. A frozen C capture policy earned 669.83
after full exit (95% interval 557.78–772.58); a D commitment/first-exit
policy earned 1382.31 and profited in all 100 confirmation seeds.
D retained 575.05, 46.5% less than A, with no statistically resolved
retention advantage over the matched single-token batch. B's protocol-fee and
creator-fee support variants slightly reduced seven-day cohort backing.

The migration-free routing grid first has a positive lower capital interval at
assumed propensity .4, corresponding to **26.5% realized quote-weighted consent**
among reachable eligible orders. At .3 the capital interval includes zero.
That is a conditional grid result, not a universal adoption requirement or a
joint improvement in survival/activity. The full model/holding-policy uncertainty
below is larger than these seed intervals suggest.
<!-- end-reviewed-summary -->

## What actually ran

The study completed 88 distinct no-attack settings and
12 trained-policy settings on **100 paired
confirmation seeds, 10000–10099**: **10,000 worlds**,
each with 480 common latent opportunities, ten candidate identities, a 30-minute
primary election and seven days of follow-up. Operational close/delay stresses
are separately named. There were 0 confirmation exceptions.
Development used seeds 0–19 (180 pilot worlds); bounded policy search
used independent seeds 100–149 (6650 worlds). These stages are not
pooled into the confirmation sample. The exact planned/completed cells, policy
parameters and seed counts are in `analysis/completed_matrix.csv` and the frozen
plan. This is not the full earlier factorial research program. The pre-confirmation
review also preserved 4600 exported rows from an interrupted initial
policy search; those rows are not used for final selection or confirmation.

An earlier 10,000-world run is preserved separately. Review found an ownership error only in D_REFUSAL: refusing creators still committed seed cash to the platform auction. The corrected run repeats all frozen settings and the same 100 seeds. Economic parameters and policies were not retuned. The earlier runs are not additional independent observations; see correction_record.json and correction_audit.json.

| Mechanism | Implemented and executed |
| --- | --- |
| A | Ten funded independent curves; diagnostic election does not move purchases; cap, funded commitment overlays, holder and concentration comparisons |
| B | Half of protocol fees supports winner; separate authorized creator-fee 60/30/10 alternative; each has lock and literal-destruction variants, real costs and +72h unlock observations |
| C | Explicit mint authorization; reach, acceptance, rejection alternatives and voluntary net-proceeds migration; independently funded overlays and strategic policies |
| D | Uniform-price curve-batch from compatible conditional escrow; no prelaunch loser tokens; net/time-weighted commitments, lock willingness, authorization and refund stresses |
| Controls | Voluntary single-token spot, single-token batch, independent candidate batches with the same cash waiting, and spot holdings locked to close |

## Mechanical evidence and implementation limits

The high-precision reference reuses the original ledger at zero coupling; economic
runs use integer quote/claim settlement, never float permission to overspend.
Tests cover ownership, full/partial redemption, separate fees, aliases, consent,
atomic rollback, repeated claims/refunds, cancellation, expiry, no winner and
deterministic replay. Test artifacts include development failures as well as
passing gates:

| gate | tests | failures |
| --- | --- | --- |
| gate10_refusal_correction | 196 | 0 |
| gate1_mechanics | 26 | 1 |
| gate1_pass | 164 | 0 |
| gate2_behavior | 46 | 0 |
| gate2_namespace_pass | 184 | 0 |
| gate2_pass | 1 | 1 |
| gate3_attacks | 190 | 0 |
| gate4_study_ready | 192 | 0 |
| gate5_pre_pilot | 193 | 0 |
| gate6_metrics | 55 | 0 |
| gate7_batch_attribution | 194 | 0 |
| gate8_final_model | 57 | 0 |
| gate9_frozen_ready | 195 | 0 |

Arithmetic witnesses, distinct from Monte Carlo estimates: 1,000 claims have
reserve 60 and cap 110. Equal D subscribers paying 30 each receive 500 claims;
first exit pays 42.50 and leaves 17.50. A funded B purchase of 30 acquires
245.3624 claims; original holders can redeem about 84.5362 and leave only 5.4638
backing support inventory. The zero-fee ordering witness earns 100 on outlay 160.
Tight limits correctly refuse atomic conversions. Different fixed-budget paths
leave different claim-quantum dust with owners; exact world conservation still
holds. A failed initial dust assertion and a test-module namespace collision were
repaired only in new files and preserved in gate artifacts.

## Main observed outcomes

Quote values are abstract units; depth is gross privately executable sell proceeds
at 5% marginal impact. Organic activity counts funded actors in the trailing 1h,
6h and 24h windows at the respective checkpoints. Curves can retain a positive
quote while no one trades. A winner is diagnostic in A, so also inspect cohort
depth and the neutral candidate benchmark in raw results.

| name | checkpoint | cohort | winner | depth5 | active | executed | outside | unexecuted |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | plus_1h | 3523.764 | 751.721 | 73.342 | 58.550 | 13175.309 | 0.000 | 1277.591 |
| A | plus_24h | 1390.346 | 274.784 | 26.840 | 12.390 | 15780.909 | 0.000 | 1384.605 |
| A | plus_7d | 1074.571 | 205.728 | 20.107 | 15.010 | 17574.219 | 0.000 | 1387.358 |
| B | plus_1h | 3533.921 | 761.661 | 74.311 | 58.550 | 13173.866 | 0.000 | 1279.035 |
| B | plus_24h | 1398.058 | 283.058 | 27.647 | 12.390 | 15777.085 | 0.000 | 1388.429 |
| B | plus_7d | 1073.974 | 205.332 | 20.069 | 15.010 | 17570.394 | 0.000 | 1391.183 |
| B_CREATOR | plus_1h | 3559.340 | 787.080 | 76.789 | 58.540 | 13171.664 | 0.000 | 1281.236 |
| B_CREATOR | plus_24h | 1419.965 | 304.759 | 29.763 | 12.370 | 15770.692 | 0.000 | 1394.822 |
| B_CREATOR | plus_7d | 1072.163 | 203.858 | 19.925 | 15.010 | 17563.466 | 0.000 | 1398.111 |
| B_DESTROY | plus_1h | 3523.764 | 751.721 | 73.342 | 58.550 | 13175.309 | 0.000 | 1277.591 |
| B_DESTROY | plus_24h | 1390.346 | 274.784 | 26.840 | 12.390 | 15780.909 | 0.000 | 1384.605 |
| B_DESTROY | plus_7d | 1074.571 | 205.728 | 20.107 | 15.010 | 17574.219 | 0.000 | 1387.358 |
| B_CREATOR_DESTROY | plus_1h | 3523.764 | 751.721 | 73.342 | 58.550 | 13175.309 | 0.000 | 1277.591 |
| B_CREATOR_DESTROY | plus_24h | 1390.346 | 274.784 | 26.840 | 12.390 | 15780.909 | 0.000 | 1384.605 |
| B_CREATOR_DESTROY | plus_7d | 1074.571 | 205.728 | 20.107 | 15.010 | 17574.219 | 0.000 | 1387.358 |
| C | plus_1h | 3824.475 | 1548.786 | 151.055 | 56.440 | 11886.634 | 604.587 | 1962.045 |
| C | plus_24h | 1677.070 | 700.933 | 68.390 | 11.000 | 13977.005 | 786.201 | 2399.047 |
| C | plus_7d | 1223.334 | 530.682 | 51.790 | 13.780 | 15471.944 | 905.128 | 2581.148 |
| D | plus_1h | 2304.175 | 2304.175 | 224.706 | 46.180 | 6479.426 | 1231.942 | 6763.505 |
| D | plus_24h | 812.448 | 812.448 | 79.262 | 7.820 | 7832.292 | 1479.993 | 7872.704 |
| D | plus_7d | 575.053 | 575.053 | 56.116 | 10.280 | 8925.730 | 1626.889 | 8428.651 |
| SINGLE_SPOT | plus_1h | 1859.301 | 1859.301 | 181.331 | 45.900 | 6294.001 | 1552.558 | 6648.359 |
| SINGLE_SPOT | plus_24h | 708.092 | 708.092 | 69.088 | 7.570 | 7552.872 | 1843.403 | 7814.158 |
| SINGLE_SPOT | plus_7d | 514.601 | 514.601 | 50.222 | 10.100 | 8555.159 | 2034.095 | 8417.460 |
| SINGLE_BATCH | plus_1h | 2264.060 | 2264.060 | 220.795 | 45.100 | 5954.746 | 1363.486 | 7161.104 |
| SINGLE_BATCH | plus_24h | 847.140 | 847.140 | 82.645 | 7.360 | 7170.739 | 1652.035 | 8368.941 |
| SINGLE_BATCH | plus_7d | 568.758 | 568.758 | 55.503 | 9.710 | 8148.658 | 1842.727 | 8996.611 |
| INDEPENDENT_BATCH | plus_1h | 3630.336 | 790.935 | 77.165 | 57.950 | 11284.638 | 476.964 | 2649.461 |
| INDEPENDENT_BATCH | plus_24h | 1299.610 | 271.922 | 26.561 | 11.930 | 13886.006 | 476.964 | 2755.706 |
| INDEPENDENT_BATCH | plus_7d | 938.907 | 205.143 | 20.050 | 14.760 | 15677.915 | 476.964 | 2759.817 |
| SPOT_LOCK | plus_1h | 4234.844 | 984.434 | 96.031 | 58.000 | 12680.065 | 0.000 | 1702.680 |
| SPOT_LOCK | plus_24h | 1604.035 | 344.143 | 33.603 | 12.120 | 15245.368 | 0.000 | 1843.288 |
| SPOT_LOCK | plus_7d | 1182.219 | 241.262 | 23.572 | 14.890 | 17031.221 | 0.000 | 1853.153 |

Seven-day paired differences versus A, with seed-bootstrap 95% intervals:

| name | metric | mean_delta | low | high |
| --- | --- | --- | --- | --- |
| B | cohort_reserve | -0.597 | -0.909 | -0.198 |
| B | winner_depth_500 | -0.039 | -0.091 | 0.032 |
| B | organic_active | 0.000 | 0.000 | 0.000 |
| C | cohort_reserve | 148.763 | 118.257 | 180.014 |
| C | winner_depth_500 | 31.683 | 28.966 | 34.724 |
| C | organic_active | -1.230 | -1.450 | -1.020 |
| D | cohort_reserve | -499.518 | -528.814 | -470.563 |
| D | winner_depth_500 | 36.009 | 32.769 | 39.258 |
| D | organic_active | -4.730 | -5.120 | -4.360 |
| B_CREATOR | cohort_reserve | -2.408 | -3.051 | -1.750 |
| B_CREATOR | winner_depth_500 | -0.182 | -0.266 | -0.092 |
| B_CREATOR | organic_active | 0.000 | 0.000 | 0.000 |
| B_DESTROY | cohort_reserve | 0.000 | 0.000 | 0.000 |
| B_DESTROY | winner_depth_500 | 0.000 | 0.000 | 0.000 |
| B_DESTROY | organic_active | 0.000 | 0.000 | 0.000 |
| B_CREATOR_DESTROY | cohort_reserve | 0.000 | 0.000 | 0.000 |
| B_CREATOR_DESTROY | winner_depth_500 | 0.000 | 0.000 | 0.000 |
| B_CREATOR_DESTROY | organic_active | 0.000 | 0.000 | 0.000 |
| SINGLE_SPOT | cohort_reserve | -559.970 | -588.952 | -531.886 |
| SINGLE_SPOT | winner_depth_500 | 30.115 | 27.131 | 33.172 |
| SINGLE_SPOT | organic_active | -4.910 | -5.330 | -4.510 |
| SINGLE_BATCH | cohort_reserve | -505.813 | -537.139 | -474.030 |
| SINGLE_BATCH | winner_depth_500 | 35.395 | 32.279 | 38.614 |
| SINGLE_BATCH | organic_active | -5.300 | -5.770 | -4.830 |
| INDEPENDENT_BATCH | cohort_reserve | -135.665 | -151.143 | -119.195 |
| INDEPENDENT_BATCH | winner_depth_500 | -0.057 | -1.965 | 2.134 |
| INDEPENDENT_BATCH | organic_active | -0.250 | -0.390 | -0.120 |
| SPOT_LOCK | cohort_reserve | 107.648 | 88.031 | 128.662 |
| SPOT_LOCK | winner_depth_500 | 3.465 | 1.776 | 5.452 |
| SPOT_LOCK | organic_active | -0.120 | -0.200 | -0.050 |

The key retention comparisons, including matched batch controls, are:

- B versus A: seven-day cohort reserve difference -0.597, 95% interval [-0.909, -0.198].
- C versus A: seven-day cohort reserve difference +148.763, 95% interval [+118.257, +180.014].
- D versus A: seven-day cohort reserve difference -499.518, 95% interval [-528.814, -470.563].
- D versus INDEPENDENT_BATCH: seven-day cohort reserve difference -363.854, 95% interval [-394.393, -333.396].
- D versus SINGLE_BATCH: seven-day cohort reserve difference +6.295, 95% interval [-9.473, +21.802].

The strongest favorable evidence is any positive absolute winner depth/retention
entry in these tables. The strongest contrary evidence is loss of whole-cohort
capital or activity, loss of an effect against the batch/lock controls, or gains
that disappear after support unlock. These quantities are shown together so an
increased winner share cannot substitute for a capital gain.

Election accuracy against the evaluator-only latent-offer benchmark (a limited
synthetic benchmark, not knowledge of genuine people) is:

| name | correct_future_choice | winner_undefined | organic_mean_events | creator_cash_change |
| --- | --- | --- | --- | --- |
| A | 0.340 | 0.000 | 24.920 | -57.622 |
| A_COMMIT | 0.350 | 0.270 | 24.920 | -57.622 |
| A_HHI | 0.220 | 0.000 | 24.920 | -57.622 |
| A_HOLDERS | 0.250 | 0.020 | 24.920 | -57.622 |
| A_TIMECOMMIT | 0.350 | 0.270 | 24.920 | -57.622 |
| B | 0.340 | 0.000 | 24.920 | -57.549 |
| B_CREATOR | 0.340 | 0.000 | 24.920 | -125.349 |
| B_CREATOR_DESTROY | 0.340 | 0.000 | 24.920 | -125.441 |
| B_DESTROY | 0.340 | 0.000 | 24.920 | -57.575 |
| C | 0.340 | 0.000 | 22.230 | -65.486 |
| C_COMMIT | 0.350 | 0.270 | 22.380 | -62.924 |
| C_HHI | 0.220 | 0.000 | 22.350 | -65.370 |
| C_HOLDERS | 0.250 | 0.020 | 22.450 | -65.212 |
| C_TIMECOMMIT | 0.350 | 0.270 | 22.380 | -62.924 |
| D | 0.310 | 0.000 | 16.010 | -107.793 |
| D_TIME | 0.320 | 0.000 | 15.820 | -108.216 |
| INDEPENDENT_BATCH | 0.310 | 0.000 | 24.550 | -66.253 |
| SINGLE_BATCH | 0.100 | 0.000 | 14.770 | -112.418 |
| SINGLE_SPOT | 0.100 | 0.000 | 15.370 | -20.367 |
| SPOT_LOCK | 0.290 | 0.000 | 24.740 | -61.189 |

The primary variants have zero extra attention from winning. Positive and negative
attention sensitivities are separate cells, not evidence that an election creates
organic attention. All starting quote is 39,100 in each world, including the
funded attacker, unused capital and sponsor. No rejected budget regenerates cash.
Outside reserves remain accounted but are excluded from platform/cohort retention.

## Conditional acceptance and participation

In the migration-free routing grid, the smallest tested assumed propensity with a strictly positive lower interval for cohort retention is 0.4. This is conditional on reach=.6 and the stated rejection behavior; it is not a universal threshold. The second grid includes migration=.25 and cannot attribute its effect solely to routing.

| grid | assumed_acceptance | realized_quote_acceptance | capital_delta | low | high |
| --- | --- | --- | --- | --- | --- |
| with_migration | 0.000 | 0.000 | 116.242 | 77.667 | 153.098 |
| routing_only | 0.000 | 0.000 | -98.688 | -120.655 | -77.667 |
| routing_only | 0.100 | 0.063 | -60.761 | -83.517 | -38.402 |
| with_migration | 0.100 | 0.061 | 123.157 | 87.264 | 162.238 |
| with_migration | 0.200 | 0.128 | 131.309 | 97.414 | 166.725 |
| routing_only | 0.200 | 0.132 | -29.588 | -52.152 | -7.237 |
| routing_only | 0.300 | 0.202 | 4.834 | -18.331 | 27.862 |
| with_migration | 0.300 | 0.197 | 139.477 | 105.731 | 172.220 |
| with_migration | 0.400 | 0.261 | 143.439 | 112.264 | 175.919 |
| routing_only | 0.400 | 0.265 | 28.626 | 4.579 | 50.776 |
| routing_only | 0.500 | 0.328 | 46.247 | 22.055 | 68.614 |
| with_migration | 0.500 | 0.322 | 148.336 | 117.184 | 179.325 |
| routing_only | 0.600 | 0.390 | 66.268 | 43.279 | 88.355 |
| with_migration | 0.600 | 0.383 | 148.763 | 118.257 | 180.014 |
| with_migration | 0.700 | 0.446 | 150.297 | 119.591 | 180.738 |
| routing_only | 0.700 | 0.453 | 81.437 | 57.049 | 103.920 |
| with_migration | 0.800 | 0.511 | 151.186 | 122.857 | 179.076 |
| routing_only | 0.800 | 0.519 | 96.377 | 72.259 | 119.911 |
| routing_only | 0.900 | 0.583 | 106.477 | 82.816 | 129.445 |
| with_migration | 0.900 | 0.575 | 150.065 | 122.729 | 177.113 |
| with_migration | 1.000 | 0.640 | 152.448 | 124.051 | 180.125 |
| routing_only | 1.000 | 0.648 | 117.126 | 93.895 | 140.258 |

Assumed propensity is reduced by loyalty and price, so 1 does not mean universal
consent. Reach controls whether a loser-page order encounters the router at all.
`C_REACH_*`, `C_REJECT_*`, `C_MIGRATE_*`, `D_BROAD_*` and `D_LOCK_*` cells isolate
those assumptions. D's cash-lock willingness and allowed-winner choice are
different decisions from C's post-election consent. One-factor sweeps do not
establish a universal joint adoption threshold. All distributions and paired
differences, including no-benefit settings, are exported rather than selected
only for favorable averages.

## Unlocks, controls and interpretation

| name | label | cohort_reserve | winner_reserve | support_claims | support_cash | support_unlock_proceeds |
| --- | --- | --- | --- | --- | --- | --- |
| B | after_unlock | 1044.683 | 197.439 | 0.000 | 9.389 | 9.064 |
| B | before_unlock | 1053.794 | 206.550 | 48.696 | 0.324 | 0.000 |
| B_CREATOR | after_unlock | 1039.674 | 192.998 | 0.000 | 34.749 | 32.793 |
| B_CREATOR | before_unlock | 1072.609 | 225.933 | 171.825 | 1.956 | 0.000 |
| B_CREATOR_DESTROY | after_unlock | 1046.213 | 198.896 | 0.000 | 1.949 | 0.000 |
| B_CREATOR_DESTROY | before_unlock | 1046.213 | 198.896 | 0.000 | 1.949 | 0.000 |
| B_DESTROY | after_unlock | 1046.213 | 198.896 | 0.000 | 0.324 | 0.000 |
| B_DESTROY | before_unlock | 1046.213 | 198.896 | 0.000 | 0.324 | 0.000 |

B's purchased claims and actual fee cash have explicit owners. Locking is a
temporary restriction on selling; destruction leaves a separately reported
inaccessible buffer. Neither is permanent LP capital. The before/after-unlock
drop measures the withdrawal option that a locked snapshot conceals. Fee support
can pay earlier holders, as the exact witness demonstrates.

D is compared to independent batches and a voluntary single-token batch in the
paired table, holding the batch curve and pre-close cash waiting explicit. Any
gain against ten spot markets must survive those controls before it can be
attributed to narrative selection. Choosing a more popular candidate, restricting
available assets, batching entry prices and forcing cash to wait are distinct
causal changes. The controls do not identify a real-world equilibrium.

## Strategic attacks

Every macro policy has one 5,000-unit actor endowment across aliases. The bounded
search includes abstention, funded capture/dump sizes and exit times, wallet splits,
wash rounds, and predictable B-epoch frontruns. D searches funded commitments and
immediate/one-hour exits. Policies were optimized independently against A and the
other selected architectures; abstaining families create no duplicate confirmation
samples. Actor identities aggregate evaluation budgets only; public elections see
addresses. Fee/holder/concentration metrics can therefore be misleading.

| name | mean_profit | low | high | profit_frequency | mean_peak | mean_fees | mean_other_trader_loss | complete_exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ATTACK_A_capture | -11.351 | -25.654 | 2.509 | 0.390 | 250.000 | 1.974 | -9.598 | 100 |
| ATTACK_B_capture | -11.290 | -25.326 | 2.075 | 0.390 | 250.000 | 1.975 | -9.683 | 100 |
| ATTACK_C_capture | 669.832 | 557.781 | 772.576 | 0.890 | 3000.000 | 26.710 | 696.972 | 100 |
| ATTACK_C_split | 673.904 | 570.415 | 775.331 | 0.890 | 2999.998 | 27.987 | 701.669 | 100 |
| ATTACK_D_capture | 1382.313 | 1358.752 | 1405.293 | 1.000 | 3000.000 | 29.562 | 1390.364 | 100 |
| ATTACK_B_CREATOR_capture | -11.025 | -24.546 | 3.866 | 0.390 | 250.000 | 1.976 | -9.790 | 100 |
| ATTACK_D_TIME_capture | 1006.110 | 882.117 | 1122.781 | 0.730 | 3000.000 | 21.568 | 1012.548 | 100 |
| ATTACK_A_HOLDERS_capture | -11.351 | -25.340 | 3.166 | 0.390 | 250.000 | 1.974 | -9.598 | 100 |
| ATTACK_C_HOLDERS_capture | -25.099 | -37.869 | -12.433 | 0.340 | 250.000 | 1.919 | -23.677 | 100 |
| ATTACK_C_HOLDERS_split | 673.904 | 569.570 | 775.862 | 0.890 | 2999.998 | 27.987 | 706.357 | 100 |
| ATTACK_C_HHI_capture | 8.079 | 2.154 | 13.876 | 0.590 | 250.000 | 2.052 | 9.686 | 100 |
| ATTACK_C_HHI_split | 663.878 | 557.136 | 768.873 | 0.890 | 2999.998 | 27.947 | 695.065 | 100 |

Profit frequency counts positive cash P&L with zero residual inventory. The full
table includes Wilson intervals, extrema, capital-days and a separately reported
10% annual opportunity-cost diagnostic. Peak recoverable funding is distinct from
irreversible fees. Other-trader losses are paired against the same mechanism
without that policy; a profitable trade also available in A is not automatically
a new consolidation exploit. A failure to find profit is only a finite search
result. Search spaces omit strategic borrowing, coalitions among unrelated actors,
creator-side bribes and general equilibrium entry.

Separately, the 56-cell known-order grid optimizes funded migration frontruns
against output limits and actual fee costs. Selected fee-bearing profitable cases:

| slippage_bps | budget | peak_funding | irreversible_fees | complete_exit_profit | filled |
| --- | --- | --- | --- | --- | --- |
| 5000 | 1000 | 1000.000 | 12.454 | 1104.069 | True |
| 5000 | 500 | 500.000 | 7.395 | 840.290 | True |
| 5000 | 250 | 250.000 | 4.387 | 589.332 | True |
| 5000 | 100 | 100.000 | 2.128 | 325.601 | True |

Identical known purchases in the A control produce the same ordering profit.
Routing and visible migrations concentrate opportunities; independent curves do
not remove same-token MEV. Tight zero-slippage cases refuse/roll back both
conversion legs, and the attacker still pays its own round trip. Primary D has no
prelaunch secondary winner market: such price manipulation is N/A before issuance;
its relevant attack is capital capture followed by first exit.

## Honest recommendation and plain English

**A: go as the research control.** It preserves asset choice and isolates the
costs and benefits of consolidation. This is not a recommendation to launch or
invest in memecoins. Its independent markets still have adverse selection and
ordering risk.

**B: no-go as a claimed durable liquidity innovation.** It recycles already paid
fees and changes who can sell into them. A larger winner position during a lock
does not establish improved cohort retention, private depth or organic survival.
The creator-fee variant also redirects losing creators' income; adoption is
unproven. It could be studied as an explicitly priced promotional expense, with
ownership/unlock disclosure and the measured costs accepted.

**C: conditional research only; no-go for an established superiority claim.**
It implements voluntary routing without confiscating loser reserves, but retention
depends on reach, actual acceptance, abandonment, prices and later selling.
Changing the token received creates no external capital. No universal acceptance
threshold or creator adoption estimate follows from these synthetic runs.

**D: no-go in this initial form without addressing allocation/exit incentives.**
Its batch allocation is mechanically funded, but equal average-price entry into
an increasing redeemable curve rewards the first seller at other subscribers'
expense. Cash waiting and concentration must be distinguished from better
organic demand. The adverse arithmetic and trained commitment/exit strategies
cannot be rescued by a high initial market cap.

In simple English: putting money behind one name can make that name look stronger.
It does not create more money or guarantee that buyers want it. Some buyers leave;
early holders can sell into the redirected purchases; batch subscribers can race
to withdraw before one another. The useful product hypothesis left open is better
discovery and voluntary execution, with costs and refusal visible—not a demonstrated
economic gain from electing a canonical coin.

## Reproduction and evidence

Run from the repository root using the existing environment. Choose a **new study
directory** for reruns and capture a new preservation inventory before starting.
The supplied completed bundle is `research/narrative_consolidation/bounded_study/corrected_v2`.
First run `python -m bonding_lab.narrative init --root <new-study-directory>` to
capture the new preservation inventory. Reports are saved inside the study;
an existing top-level findings report is never overwritten by a reproduction.

```powershell
.\.venv\Scripts\python.exe -m bonding_lab.narrative pilot --root <new-study-directory>
.\.venv\Scripts\python.exe -m bonding_lab.narrative train --root <new-study-directory>
.\.venv\Scripts\python.exe -m bonding_lab.narrative freeze --root <new-study-directory>
.\.venv\Scripts\python.exe -m bonding_lab.narrative confirm --root <new-study-directory>
.\.venv\Scripts\python.exe -m bonding_lab.narrative report --root <new-study-directory>
.\.venv\Scripts\python.exe -m bonding_lab.narrative verify --root <study-directory>
```

The frozen plan hashes source and configurations before confirmation. Confirmation
stores all 100 common tapes, every seed/checkpoint result, representative complete
financial traces and terminal wallets for seed 10000 in every treatment, ranking
records, source snapshots, progress/failure records and completion manifests.
Other traces are reproducible with `python -m bonding_lab.narrative replay
--root <study-directory> --name C --seed 10037 --out <new-replay-directory>`;
replay verifies the exact stored outcome hash. They are not claimed already
exported. Bootstrap intervals describe seed variation
inside this model, not uncertainty about human behavior or real adoption. The
current API discovery snapshots from Phase 1 are not a calibration dataset.

<!-- supplemental-findings -->
## Additional holding-policy audit: exploratory, 200 worlds

The primary agent policy attaches sell intentions to the mint actually purchased.
After voluntary migration, an original loser-mint sell intention can therefore
become ineffective; winner inventory can be sold on later winner-mint intentions
or terminal exit. This is an uncalibrated holding-policy assumption, not a legal
lock or permanent LP capital. It can inflate the apparent persistence of migrated
backing. The migration-free acceptance grid avoids that particular channel.

An additional, explicitly exploratory check carries those existing sell intentions
forward to the received winner after conversion. It uses the same 100 tapes and
frozen economic settings for C without attack and with its already-trained capture
policy: 200 extra worlds, no retraining or replacement of the preregistered matrix.
It is model-sensitivity evidence, not another independent confirmation sample.

| name | metric | original_mean | continuity_mean | mean_delta | low | high |
| --- | --- | --- | --- | --- | --- | --- |
| C | cohort_reserve | 1223.334 | 1118.814 | -104.520 | -121.321 | -87.996 |
| C | winner_depth_500 | 51.790 | 39.890 | -11.901 | -13.629 | -10.288 |
| C | organic_active | 13.780 | 13.960 | 0.180 | 0.100 | 0.260 |
| C | attacker_cash_pnl | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| ATTACK_C_capture | cohort_reserve | 1260.374 | 1159.265 | -101.109 | -115.944 | -86.657 |
| ATTACK_C_capture | winner_depth_500 | 46.481 | 34.719 | -11.761 | -13.274 | -10.274 |
| ATTACK_C_capture | organic_active | 13.540 | 13.740 | 0.200 | 0.110 | 0.300 |
| ATTACK_C_capture | attacker_cash_pnl | 669.832 | 398.572 | -271.260 | -304.309 | -238.802 |

Under sell-intent continuity, C's cohort gain versus A falls to 44.24
(95% paired interval [19.75, 70.11]), from the primary gain of 148.76.
The unchanged capture policy still earns 398.57 on average after complete exit
(interval [299.08, 499.01]). Thus the favorable capital result is sensitive
to agent holding rules, while profitable capture survives this alternative.
This materially limits a favorable interpretation of C's primary reserve result.

Reproduce the extra check and appendix, after generating the main report:

```powershell
.\.venv\Scripts\python.exe research/narrative_consolidation/bounded_study/corrected_v2/migration_exit_sensitivity.py
.\.venv\Scripts\python.exe research/narrative_consolidation/bounded_study/corrected_v2/augment_findings.py
```

The sensitivity script requires a new output directory if it has already run;
its saved `runs.csv.gz`, `paired_effects.csv` and manifest are the completed evidence.
All 196 main implementation tests pass; all 9,900 worlds outside the repaired
D refusal case match the preserved first run exactly. The earlier 10,000 worlds
are retained, not pooled to claim 200 independent confirmation seeds.

## Revenue and participant cash after feasible exits

| name | protocol_and_support_quote | gross_protocol_fees | gross_creator_fees | trader_cash_change | creator_cash_change | network_quote |
| --- | --- | --- | --- | --- | --- | --- |
| A | 45.201 | 35.201 | 105.602 | -303.657 | 200.599 | 7.852 |
| B | 38.585 | 35.225 | 105.673 | -297.089 | 200.589 | 7.910 |
| B_CREATOR | 89.477 | 35.292 | 105.876 | -279.959 | 132.569 | 7.908 |
| C | 44.531 | 34.531 | 103.593 | -305.886 | 198.220 | 7.723 |
| D | 31.218 | 21.218 | 63.652 | -31.795 | -63.300 | 4.166 |

Protocol/support cash includes launch receipts and cash remaining in the named
fund; gross fee accrual counts each actual trade, including support trades, and
is not additional external capital. Creator and trader cash changes use their
own funded initial balances. Network and outside-market accounts remain in world
conservation. Residual unprofitable-to-redeem claim dust is exported separately.
The table is a cash distribution, not a proof that fee revenue benefits traders.

There is favorable counterevidence to a blanket negative judgment: without an
attacker, D's mean trader cash loss is only 31.80
versus A's 303.66. B also
reduces trader cash losses modestly by transferring fee value away from its
other beneficiaries. These outcomes coexist with lower D trading/participation
and different creator cash outcomes; they are not proof of improved total welfare
or permanent liquidity. D's trained attack imposes roughly 1390.36
additional trader loss relative to its no-attack world. No architecture is best
on every measured dimension under equal starting money.

## Decision and open questions

Retain A as the experimental control. Reject B as a demonstrated durable-liquidity
improvement and D's current allocation/exit design. C merits further controlled
research only: there is a measured conditional reserve/depth benefit, but lower
activity, profitable strategic capture and sensitivity to holding behavior prevent
a launch recommendation. Net commitment and time weighting both permit profitable
D capture; time weighting reduces the measured reward in this policy class but
does not establish a manipulation-resistant winner rule. Address concentration
penalties remain vulnerable to actor-controlled splits.

Losing C holders keep their original claims unless they authorize conversion;
D's incompatible subscribers refund. Creator adoption remains unknown: refusal
is an exogenous stress here, not an equilibrium participation estimate. The study
does not establish an added organic-attention effect, real human acceptance,
permanent liquidity, seven-day real-market survival, or a defensible moat.
Reject a broad production claim if it relies on ignoring abandonment, locked or
unclaimed money, the migration holding-policy effect, or attacks funded within
the tested 5,000-unit budget.


---

## Appendix 5: Phase 1 review and go/no-go assessment

Source: `PHASE2_GO_NO_GO_REVIEW.md`. Original document follows.

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


---

## Appendix 6: Original Phase 2 implementation brief

Source: `CODEX_PHASE2_IMPLEMENTATION_BRIEF.md`. Original document follows.

# Codex brief: narrative consolidation Phase 2

This is a specification for a future, separately authorized implementation session. The review session that produced this brief does not authorize or perform repository changes. Date: 30 October 2026.

## Objective and completion boundary

Implement the accounting and settlement **Phase 2 defined in RESEARCH_PLAN.md**, under a new `bonding_lab/narrative/` namespace. Produce mechanically validated A–D architectures and S1/S2/S3 settlement, reproducible financial traces, integer/reference parity evidence, and a completion report. Economic advantage is an open hypothesis.

Read the four Phase 1 documents and the accompanying go/no-go review. Treat the review's extra witnesses as falsification requirements. Preserve the specified initial D curve-batch mechanism even if it fails an economic test; alternatives receive new identifiers.

Do not implement Phase 3 behavior, Phase 4 optimized attackers, Phase 5 Monte Carlo, Phase 6 dashboard, blockchain contracts, wallet integration, deployment, or historical calibration in this milestone. Deterministic scripted adverse traces are in scope. Do not rename the existing `bonding_lab/phase2/` project or overwrite its findings.

## Preservation and working boundaries

The source repository is `C:\Users\moadl\OneDrive\Documents\ChatGPT\bonding curve research`. Inspect current instructions and state before work; Phase 1 recorded an unborn Git branch and untracked project files. Recheck that fact rather than relying on it. A normal worktree cannot recover an uncommitted untracked project. Use an authorized separate working copy if isolation is required, preserving its full source; never initialize, commit, reset, or clean the original to manufacture a baseline.

1. Capture a fresh SHA-256 inventory of all durable preexisting files, including the four Phase 1 documents and evidence. Retain the original 445-file inventory as a second check. Do not use `git diff` alone.
2. Add only `bonding_lab/narrative/**`, `tests/narrative/**`, `research/narrative_consolidation/phase2/**`, and the final `NARRATIVE_PHASE2_IMPLEMENTATION_REPORT.md`. Keep old source, tests, dashboard, dependencies, old results, and Phase 1 evidence byte-identical. Avoid shared utility extraction in this milestone.
3. Use the existing Python environment and libraries. Test reports/temp directories and generated bytecode/caches must be configured so old durable files are not overwritten. Keep run bundles unique; retain failures before repair. Record any execution environment limitation honestly.

## Resolve these decisions first in DESIGN_DECISIONS.md

Record these defaults before writing architecture code. Change a default only as a named sensitivity with rationale and tests.

| Decision | Required initial contract |
| --- | --- |
| Units | Quote quantum epsilon=10^-6 and token quantum tau=10^-6 for initial integer fixtures; decimal strings/rational parameters, never float input conversion. Record supported bounds. These are research units, not chain configuration. |
| Continuous reference | Independent `p_i=a_i+b_i*q`, `R_i=a_i*q+b_i*q²/2`; Decimal context at least 60 digits with precision-convergence checks. Per-market parameters and backing; no cross-price terms. |
| Integer reserve | Use a published integer reserve potential, e.g. `Phi_i(n)=ceil(R_i(n*tau)/epsilon)`, with `Phi_i(0)=0`. Buy/sell gross cash is the corresponding difference in Phi. Then actual backing equals `epsilon*Phi_i(n)` plus a separately owned buffer. Treat this as a quantized market, not exact equality to unrounded R. Record its bounded quantization error. |
| Fees | Protocol and creator fee liabilities distinct. Round each nonnegative execution fee upward to quote quanta; cap no unauthorized debit by rejecting infeasible orders. A zero-principal execution charges no success fee. Network costs have an explicit owner and funded payer. |
| Costs | Pre-submission refusal costs zero. Submitted failure can debit only an independently authorized cost. Abort/finalization sponsorship defaults to a funded sponsor account, included equally in control endowments. |
| B support | Spend only a published fraction eta of actual protocol fee receipts. Creator-fee pooling is a separate opt-in variant. At most one support purchase per epoch using cash available at the epoch boundary; returned support-buy fees become eligible next epoch. No recursive same-epoch loop. |
| B lock | Locked claims remain in pricing supply, have an identified owner, and unlock on an explicit timestamp. Distinguish standard-horizon results from post-unlock diagnostics. |
| C reach | Only an authorized eligible order submitted to this router can change received mint. Other venue/direct orders remain direct orders. Script reach as an input now; estimate behavior only later. |
| C migration | Primary S1 is all-or-nothing for the signed conversion. For the first engine, if any member of a proposed multi-owner batch violates a limit, reject the whole batch. Per-receipt exclusion/reclearing is a separate extension; never silently accept a partially incompatible batch. |
| S2 terminal costs | Default terminal distribution charges no additional success/trading fee; any funded network cost is separately disclosed. Early redemptions retain normal trading fees. Publish this difference and include it in matched comparisons; a fee-bearing terminal instrument is a named sensitivity. |
| D cap | Production-observable cap scope is wallet/receipt as explicitly configured; no actor-ID enforcement. An actor-level cap is evaluator-only counterfactual. Preferred candidate must be in the receipt's allowed set. |
| D limits | Selection-counted receipts are irrevocable after the cutoff, valid through the deadline, and cover worst-case average price and fees. Reject lower-limit contributions from this initial instrument. Require a positive minimum settlement principal. |
| D rounding | Deterministically maximize feasible integer supply within compatible all-in budgets and Qmax using Phi and rounded fees. Allocate token quanta by largest remainder with receipt-ID tie order. If positive-spend receipts obtain zero output or violate a limit, abort/refund the batch in primary D. No silent donation, discretionary reallocation, or unbounded exclusion loop. |
| D spend/refund | Compute net principal and named fees from actual integer fills, never from unrounded target spend. Refund all unspent owner cash. Document the bounded deviation from ideal proportional spend; each receipt must stay within its all-in budget and limits. A deterministic proportional floor plus largest-remainder cash allocation is acceptable if these properties hold. |
| Close ordering | Fixed-close primary: admit scoring events strictly before T; close precedes events at T. Define total event order `(timestamp, priority, event_id)`, including cancel/expiry/reveal/timeout at equal timestamps. |
| Finalization | Separate scoring close T, announcement tF, settlement/handoff, and timeout. Winner immutable after valid finalization. Delayed/rejected reveal never changes old scores or reverses completed trades. |
| No winner | Ties within scoring quantum, no eligible candidate, invalid/late finalization, incompatible or insufficient D raise follow explicit no-winner/abort paths. No runner-up reselection in primary D. |

Cap fixtures apply only where a spot market exists. Commitment fixtures require actual irrevocable quote escrow: they apply to D, or to a separately funded overlay introduced symmetrically in its matched controls. Never score token purchases as locked quote capital, and never fabricate D prelaunch cap/volume/holder inputs. A's election result remains diagnostic and cannot redirect funds.

The integer D allocator is a required design artifact: give pseudocode, termination/bounds, fee placement, dust/refund ownership, and witnesses for over-cap, tiny receipts, and near-minimum raises before calling it complete. Reject a rounded allocation that cannot satisfy its contract. This is a specified conservative failure mode, not permission to pretend an unimplemented allocator works.

## Components and interfaces

Use immutable records and a single validated ledger commit. The exact names can vary; the contracts cannot.

| New module | Responsibility |
| --- | --- |
| `types.py` | Actor, wallet, account, market, group version, receipt, authorization, order, transaction result, event, election result. Versioned schemas. |
| `ledger.py` | Double-entry quote transfers, inventory ownership, escrow/refund liabilities, fees, locks, cost basis, snapshots, invariant checks. Actor ownership lives in evaluator metadata. |
| `markets.py` | Pure Decimal and quantized curve quote/execute functions, per-market backing, funded creation, full/partial redemption, inventory-limited depth. |
| `consent.py` | Validate owner, nonce/idempotence, group/rule hash, allowed mint(s), budget, fee bound, expiry, minimum output, cancellation cutoff, and fallback. Simulated authorizations only; no real keys. |
| `election.py` | Frozen election-result contract, eligibility validation, timestamp replay and deterministic minimal cap/commitment fixtures. Inapplicable metrics return N/A or validation error. General behavioral election study remains Phase 3. |
| `settlement.py` | S1 voluntary migration, S2 distinct terminal instruments, S3 D receipts, atomic plans, claims/refunds, state transitions and integer allocation. |
| `architectures.py` | A independent; B funded support; C authorized winner routing; D conditional auction. Shared primitives, explicit architecture policy. |
| `metrics.py` | Reserves/fees/escrow separately; offered/authorized/executed quote; depth; locked/private inventory; actor cash P&L and residual executable value. No marked-cap substitute for collateral. |
| `replay.py` | Canonical serialization and event replay; state hashes excluding runtime metadata. |
| `fast.py` | Optional implementation order is last, but declared float/reference parity is required to claim the full Phase 2 gate in the plan. Otherwise mark fast parity and Phase 2 incomplete. |
| `__main__.py` | Validation, fixture execution, and replay with a named output bundle. No broad study CLI or dashboard. |

Core operations: `quote(state, order) -> plan`, `validate(state, plan) -> result`, `commit(state, plan) -> events`, `finalize(group, observation_cutoff) -> immutable election_result`, `claim(receipt_id)`, `refund(receipt_id)`, `replay(events) -> state`, `assert_invariants(state)`. Planning must not mutate state. A failed commit cannot leave either migration leg applied. Separate authorized submitted-failure costs into an explicit event.

An authorization binds actual received mint or a fixed eligible winner rule and group version. Add nonce/cumulative spend tracking so replay or multiple fills cannot spend an authorization twice. Do not authorize from page visits or token ownership. Terminal rights travel with an S2 claim; ordinary A/C claims cannot be converted into S2 by vote.

Every event must include event/transaction ID, timestamp/order, initiating wallet, authorization reference, actual mint and quantity, principal, each fee/cost, resulting balances or deltas, rejection reason when applicable, and before/after state hashes. Rejected actions and delayed finalization belong in the tape. Keep evaluator-only actor aliases and future labels outside election/agent observations.

## Implementation sequence

1. Ledger, pure curve math, quantized reserve potential, account ownership, and A. Verify full redemption and conservation before adding policies.
2. C direct/authorized/rejected purchases, no-winner behavior, and atomic S1 individual/batch conversion. Use scripted intents and election outcomes; do not invent acceptance estimates.
3. B fee provenance, funded epoch execution, fund inventory/locks, exhaustion, no-winner beneficiary repayment, and post-unlock diagnostic.
4. D receipt lifecycle, close/finalization, compatible budget, cap/minimum raise, issuance, fees, refunds, and post-handoff trading. Add S2 redeemable-before-T and locked-until-T as separate instruments, not architecture defaults.
5. Metrics, adverse fixtures, replay, boundary/property tests, then bounded float parity. Export source/config/tape hashes and a status manifest. Run the existing regression suite after each code-changing gate as required by the plan; account for its documented local-loopback requirement without editing tests to hide an environment failure.

## Mandatory deterministic fixtures

All use funded genesis and explicit fee/network accounts. Primary arithmetic witnesses use zero fees/costs; include fee-bearing counterparts. Expected adverse behavior should pass a correctness test while being marked an economic failure.

| ID | Fixture and expected result |
| --- | --- |
| F01 | a=.01, b=.0001, q=1000: reserve 60, cap 110, gross 5%-impact depth 5.89875 when private inventory permits. |
| F02 | Full/partial redemption and donation buffer: no negative backing; ordinary claims never access somebody else's buffer. |
| F03 | C consent accepted: actual winner inventory belongs to buyer. Missing/expired/wrong-group consent: no substituted mint and no unauthorised debit. |
| F04 | C rejection policies: direct preferred-token trade, explicit outside trade, or cash retained; no budget disappearance or regeneration. |
| F05 | C atomic migration output breach: both legs unchanged; independently authorized submitted-failure cost may be posted once. Include one failing member of a multi-owner batch. |
| F06 | S1 partial escrow redemption uses reserve difference; nonparticipants retain their claims/backing. S2 split 500/500 gives terminal 30/30, versus early/late redemptions 42.5/17.5. |
| F07 | B funded support 30 into q=1000/reserve60 buys ~245.3624 claims. Original holders sell all: receive ~84.5362; ~5.4638 remains. Exact identity `remaining reserve + private redemption = 90`; no outside buyer assumed. |
| F08 | B no-winner and no-cash paths: named conditional beneficiaries paid correctly; skipped purchases preserve cash; no double-counted fee income or recursive spending. |
| F09 | D compatible successful batch, over-cap pro-rata case, incompatible preferred-only refunds, exact fee owners, and refunds of all unused cash. |
| F10 | D empty/tied/under-minimum/timeout/withheld-reveal/cancelled cases: no unintended winner issuance, no success fees, refund liability fully funded. Include minimum-raise crossing after quantization/fees. |
| F11 | D two equal subscribers each pay30 for500 at Q1000: first exit42.5, last17.5, first cash profit12.5. Reversing exit order swaps beneficiaries. Single-candidate batch control reproduces this. |
| F12 | Documented migration frontrun: attacker outlay160, proceeds260, profit100 at zero fees with permissive limits; tighter victim output limits trigger refusal/rollback rather than an assumed fill. |
| F13 | Repeated finalize/claim/refund and reused authorization: no double execution. Invalid interleavings cannot both settle and refund a receipt. |
| F14 | Same-time events at cancellation, close, reveal deadline and timeout; announcement delay blocks C routing until valid finalization. Deterministic replay of honest/withheld-close cases. |
| F15 | Split one funded actor across wallets: no extra total endowment; cap/holder-HHI rules see only permitted wallet data. Record per-wallet-cap circumvention rather than pretending actor-ID enforcement. |
| F16 | Change denomination q'=kq, a'=a/k, b'=b/k² with scaled caps/thresholds/quanta: identical quote economics and consent outcomes. |
| F17 | Locked B inventory and unclaimed D refunds: they appear in custody with ownership/liabilities and cannot masquerade as active private demand or unencumbered capital. |
| F18 | Disabled policy controls: C zero reach or zero authorized routing equals A under matched scripted inputs; B eta=0 equals its fee-matched A control. D compared with same-subscriber single-token batch, not instant spot only. |
| F19 | Near-quantum budgets, zero-output receipts, near-Qmax, near-total redemption, largest-remainder ties and receipt splitting: no creation of quote/tokens, limit breach, hidden dust donation, or profitable rounding cycle. |
| F20 | Replay from serialized tape yields identical owners, liabilities, winner, refunds, and final state hash. Truncated or inconsistent input is rejected explicitly. |

Property tests must generate multi-event funded sequences, not just restate formulas. Require zero unexplained quote residual in the integer ledger, exact supply=sum owned claims, bounded documented Decimal errors, no negative balances, and atomic rejection. Every invariant failure halts the run and saves the last valid state, offending event, seed, and source snapshot.

## Float acceptance contract

Publish numeric bounds and tolerances before differential testing. For supported states, total absolute cash/depth error must be below epsilon/10 and quantity error below tau/10; publish price tolerances separately. If the float domain cannot meet these tolerances, narrow and document it or use the reference path. Near funding/output/rounding/election boundaries, fall back to authoritative integer/Decimal validation. Monetary tolerances must never authorize an underfunded fill, change a winner, waive a limit, or create a refund mismatch. Record fallback counts. A small average error does not excuse different financial branches.

## Outputs and proposed CLI contract

New run bundles belong under `research/narrative_consolidation/phase2/runs/<unique-id>/`. Each contains `manifest.json`, `events.jsonl`, `balances.csv`, `receipts.csv`, `metrics.csv`, `invariants.json`, fixture expectations/results, replay hashes, and any failure state. Manifest fields include schema/source/Phase-1-document hashes, configuration, arithmetic mode/quanta, environment, event count, fixture IDs, completed/incomplete status, test command/results, and elapsed wall time. CSV monetary values are decimal strings or explicit integer quanta.

Implement and document these commands before citing them as runnable:

```text
python -m bonding_lab.narrative validate --config <fixture-config>
python -m bonding_lab.narrative fixtures --output <new-run-directory>
python -m bonding_lab.narrative replay --events <events.jsonl> --check <manifest.json>
```

Final `NARRATIVE_PHASE2_IMPLEMENTATION_REPORT.md` lists implemented architectures/instruments, frozen decisions, expected adverse outcomes, actual new/existing test results, parity scope and fallbacks, all failed/incomplete fixtures, and preservation hashes. Distinguish analytical witnesses, completed synthetic execution, empirical observation, and unresolved behavior. Do not write the later economic findings report as though Phases 3–5 ran.

## Definition of done and stop conditions

Phase 2 passes only when all listed architecture/settlement paths and mandatory fixtures are implemented, conservation/ownership/consent/refund properties pass, replay is deterministic, declared float parity passes, the existing regression suite passes in a suitable environment, and all protected durable preexisting files match their hashes. A reference-only subset is useful but must be labeled incomplete against the plan's full Phase 2 gate.

Stop at this milestone and report the concrete evidence. Report a correct engine's negative economic witnesses as findings. Halt and preserve evidence for conservation failure, implicit mint substitution, unsupported identity enforcement, unbacked costs, or unrecoverable refunds. Do not silently change the instrument to improve results, weaken tests, claim a safety proof from finite attack search, or proceed to deployment.


---

## Appendix 7: Phase 1 prior art

Source: `PRIOR_ART.md`. Original document follows.

# Narrative consolidation: prior art and evidence boundary

Phase 1, 30 October 2026. This is an off-chain research specification. No new
economic simulation, deployment or historical calibration has been completed.
Protocol documentation describes mechanisms; it does not establish their
economic success. Sources below were consulted on this date. Mutable documentation
and indexed pages are not pinned deployed-code audits.

## 1. Existing research in this repository

| Material inspected | Finding relevant to the new study | Reuse boundary |
| --- | --- | --- |
| `bonding_lab/engine.py`, `fast.py`, `MATHEMATICS.md`, `RESEARCH_FINDINGS.md`, `PHASE1_AUDIT.md` | Exact funded reference accounting; independent control at coupling zero; positive quadratic coupling leaves own absolute slope unchanged and permits cross-token ordering transfers. | Reuse accounting concepts and independent execution only. No new positive cross-price terms. |
| `bonding_lab/phase2/`, `PHASE2_DESIGN.md`, `PHASE2_FINDINGS.md` | Shared AMM depth involves paid inventories and LP risk; equal capital alone does not align price, inventory or risk. | Reuse finite-dealer, capital-matching and depth diagnostics after separate validation. Do not import its differently numbered four architectures. |
| `bonding_lab/copycat/`, `research/copycat_diversion/DESIGN.md`, `FINDINGS.md`, `WINNER_REANALYSIS.md` | Already studies independent curves, buyer-owned principal splits, alternative fee/treasury/holder interpretations, grouping, leader rules and funded attacks. | Reuse reference patterns, actor-level budgets, held-out policy search and provenance. Fixed diversion and synthetic badge steering do not establish consent to a different token. |
| `bonding_lab/agents.py`, `experiments.py`, `simulation.py`, `dashboard.py`, `tests/` | Seeded intentions, distributions, exports, replay and accounting/property/application tests exist. | Adapt through new modules. Existing behavior is synthetic and its event horizons do not establish 24-hour or seven-day survival. |

The copycat reanalysis explicitly changes the objective from original-token
survival to concentration on whichever token wins. That clarification is retained:
a copy winning is not inherently an attack. A financially captured winner that
repels subsequent voluntary demand can still be an economic failure. Historical
reported test counts are not the current baseline; see `RESEARCH_PLAN.md` and the
new Phase 1 evidence directory.

## 2. Independent launches: Pump

**Implementation documentation available.** Pump's official repository describes
per-mint bonding curves using virtual reserves alongside real reserves, followed
by migration into PumpSwap. Its newer documentation also describes multihop
routing. These operations do not select one narrative winner or authorize
replacement of a buyer's chosen mint. Our initial linear independent curve is a
controlled research instrument, not a replica of Pump's reserve formula.
[Pump program](https://github.com/pump-fun/pump-public-docs/blob/main/docs/PUMP_PROGRAM_README.md),
[official repository and updates](https://github.com/pump-fun/pump-public-docs).

An important accounting detail is version-dependent fee custody: newer trade
instructions can retain accrued protocol/creator fees in curve or pool custody
until swept. Physical vault balance therefore need not equal backing available
to traders. We separate fee liabilities from market reserves even when custody
is shared. We do not hard-code rates from old examples or third-party summaries.
[Fee sweep specification](https://github.com/pump-fun/pump-public-docs/blob/main/docs/instructions/SWEEP_FEES.md).

## 3. Prism: close comparison, with limited verification

**Published product specification; execution unverified here.** Prism's indexed
first-party page describes narrative grouping, a composite score, a committed
hidden close in a 28–32 minute range, and pooled creator fees split 60% to winner
buy-and-burn, 30% to its creator and 10% to the platform. Losing coins continue
trading. It also describes custodial baskets buying several ranked candidates.
[Prism mechanism page](https://prismlaunch.fun/how-it-works).

Direct fetches of that page failed; the search index exposed its text. No code
audit, fee transactions, operator behavior or reliable market history was verified.
Its anti-wash and probability language is a claim to test, not validation. A hash
binds a chosen close but alone proves neither unbiased sampling nor secrecy from
its operator. Ranking weights are not calibrated winning probabilities.

The comparison is therefore specific: B studies fee support; C studies authorized
post-election purchase principal; D studies conditional escrow funding one winner.
Prism's baskets already involve purchase principal, so broad novelty for principal
routing is not established. Our difference is elected-winner settlement and
explicit ownership/refund rules, subject to further prior-art review.

## 4. Auctions and launch settlement

**Public implementation.** Gnosis EasyAuction accepts collateralized limit orders
against a supplied token lot, computes a common clearing price, and provides
claims for tokens and unspent bid funds. Cancellation deadlines and funding
conditions are explicit. It supplies useful settlement precedents, not a
multi-candidate narrative election or proof of truthful bidding.
[EasyAuction source and mechanism](https://github.com/Gnosis-Auction/auction-contracts/blob/main/README.md).

**Public implementation and documentation.** Uniswap Continuous Clearing Auction
spreads token issuance through time, with budget/maximum-price bids. Its technical
specification includes graduation, failed-auction refunds, token claims and a
downstream liquidity handoff. Such issuance differs from both a one-shot auction
and our initial D batch subscription; we must compare timing and market-formation
effects separately from narrative selection.
[CCA concepts](https://developers.uniswap.org/docs/liquidity/liquidity-launchpad/concepts/cca),
[CCA technical source](https://github.com/Uniswap/continuous-clearing-auction/blob/main/docs/TechnicalDocumentation.md).

## 5. Shared infrastructure and intent routing

**Public implementation documentation.** Balancer separates Vault token accounting
from pool pricing logic. Shared custody or a shared router does not entitle every
candidate to the same cash. Our accounting keeps market ownership and liabilities
separate; a genuinely shared inventory pool would require a distinct risk-bearing
LP model, beyond the primary A–D comparison.
[Balancer Vault](https://docs.balancer.fi/concepts/vault/).

Balancer's weight-shifting liquidity bootstrapping pools provide another launch
control: scheduled weights affect sale pricing and some configurations restrict
project-token sales. Those restrictions change exit rights and must not be
credited to winner selection in a matched comparison.
[LBP documentation](https://docs.balancer.fi/concepts/explore-available-balancer-pools/liquidity-bootstrapping-pool/liquidity-bootstrapping-pool.html).

**Public protocol documentation.** CoW aggregates intents and compares solver
settlements; consistent directed clearing prices can reduce ordering dependence
within a batch. Signed order fields identify the sold and bought assets and an
expiry. We borrow the principle that changing the received mint requires new
authorization or an existing conditional authorization. Batching alone does not
prevent pre-batch inventory accumulation or capture of the election.
[CoW auctions](https://docs.cow.fi/cow-protocol/concepts/introduction/fair-combinatorial-auction),
[signed order fields](https://docs.cow.fi/cow-protocol/reference/core/signing-schemes).

## 6. Migrations, identity and market manipulation

**Public token migration implementation.** Polygon's Ethereum MATIC/POL migration
uses an explicitly defined conversion and user approval. That is a token upgrade
with specified rights, not permission to seize one speculative asset's reserve
and buy an unrelated winner. Pump's curve-to-AMM migration likewise changes the
venue without choosing another narrative mint. Our loser conversion must use
actual redemption proceeds and a separate authorized winner purchase.
[Polygon migration instructions](https://support.polygon.technology/support/solutions/articles/82000912953-how-can-i-migrate-to-pol-),
[migration source](https://github.com/0xPolygon/pol-token).

**Research evidence.** Douceur's Sybil analysis explains why addresses do not imply
independent identities. Capital-linear scoring avoids an automatic gain merely
from splitting the same capital, but remains plutocratic. Per-wallet bonuses,
concave weights and concentration penalties can restore splitting incentives;
actor ownership is simulation ground truth, not a production identity oracle.
[The Sybil Attack, 2002](https://www.microsoft.com/en-us/research/publication/the-sybil-attack/).

**Research evidence.** Flash Boys 2.0 documents transaction-order extraction in
DEX markets. A visible migration or scheduled fee buy creates a same-token
ordering opportunity even with independent candidate prices. A winner-take-all
reward can also make capital temporarily committed to capture the title rational.
These are hypotheses for funded attack optimization, not estimates of attack
frequency on the proposed platform.
[Flash Boys 2.0](https://arxiv.org/abs/1904.05234).

## 7. Historical data access and calibration status

Provider documentation exposes pair search/current metrics through DEX Screener
and transaction history through Solana RPC. Neither a keyword hit nor a pool's
creation time identifies the complete launch cohort. Rolling volume and buy/sell
counts cannot reconstruct quote net flow, beneficial ownership or decayed launches.
[DEX Screener API](https://docs.dexscreener.com/api/reference),
[Solana history/indexing limitations](https://solana.com/docs/payments/accept-payments/indexing),
[transaction response schema](https://solana.com/docs/rpc/json-structures).

Phase 1 attempts public keyword access for `PNUT` and `NEIRO` solely as discovery
probes. They are search terms, not verified historical clusters. Request status,
raw successful responses and limitations are recorded by
`research/narrative_consolidation/phase1/probe_public_data.py`. A browser-tool
request to the PNUT API URL was inaccessible; direct HTTP results are recorded
separately. No paid dataset, wallet signature, private API credential or real-fund
transaction is used. A successful snapshot is not historical calibration.

**Observed access result:** both initial sandboxed probes failed DNS resolution;
those results remain in `data_access_probe_sandbox.json`. An authorized network
retry succeeded with HTTP 200 for both terms, each returning 30 pair records and
17 distinct `(chain, base-token address)` keys. Raw JSON and hashes are preserved.
These are current keyword snapshots with overlapping venues and unverified
membership, not counts of launches competing in a historical event. No historical
cluster was verified and no behavioral parameter was calibrated. Later economic
experiments must remain explicitly synthetic unless a fuller collection succeeds.

Before any historical claim, enumerate mints and creation transactions, label
same-event candidates independently of later success, preserve failed/delisted
tokens, reconstruct curve and post-graduation flows without double-counting venue
transfers, and publish coverage gaps. Common-funding links may suggest coordinated
wallets; they neither prove shared control nor count humans. No empirical routing
acceptance, loyalty, retention or creator-participation estimate is available here.

## 8. What remains distinctive and what remains unproven

The testable combination is narrative membership plus a contest, economically
authorized winner principal, conditional settlement, and matched behavioral
counterfactuals. Every component has precedents. This review establishes neither
patent novelty nor a defensible business moat.

Fee recycling, a larger winner reserve, concentrated flow, a higher displayed cap
and longer organic survival are different claims. The research succeeds only if
the latter outcomes survive abandonment, strategic selling, creator refusal and
equal-capital comparisons. Existing documentation does not answer that question.


---

## Appendix 8: Phase 1 mechanism designs

Source: `MECHANISM_DESIGNS.md`. Original document follows.

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


---

## Appendix 9: Phase 1 economic invariants

Source: `ECONOMIC_INVARIANTS.md`. Original document follows.

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


---

## Appendix 10: Phase 1 research plan

Source: `RESEARCH_PLAN.md`. Original document follows.

# Narrative consolidation research plan

30 October 2026. **Current scope: Phase 1 only.** The four design documents are
research specifications. New A–D models, new Monte Carlo comparisons, dashboard
features and `NARRATIVE_RESEARCH_FINDINGS.md` are not claimed complete. The new
study is separate from the repository's earlier work also called Phase 2.

## 1. Repository audit and preservation

Inspected the original Decimal/float execution engines, agent tape, experiments,
independent-curve copycat routing/election/market/attack code, tests, dashboard
tests, mathematical audit, earlier Phase 2 design/findings and copycat findings
including the any-winner reanalysis. Reusable components and limits are mapped in
`PRIOR_ART.md`. Existing grouping and fixed behavioral assumptions are not silently
promoted to validated narrative identity or user consent.

The repository has an unborn `master` branch with no commits; its preexisting
project files are untracked. Consequently `git diff` alone cannot establish
preservation. Before adding documents, a SHA-256 inventory captured 445 original
files (173,107,085 bytes), including source, research, recorded results and ZIP
archives. It excludes environment, caches, temporary files and generated package
metadata. The final validation compares every inventoried file's bytes. No old
model, result, dependency or dashboard file is edited.

Evidence lives in `research/narrative_consolidation/phase1/`:

- `preservation_manifest.json`: original-file SHA-256 hashes and environment.
- `baseline_pytest.xml` and `baseline_summary.json`: actual existing-suite result.
- `run_baseline.py`, `baseline_run.json`, `baseline_pytest.log` and
  `baseline_progress.jsonl`: reproducible runner and per-test diagnostic evidence.
- `probe_public_data.py` and `data_access_probe.json`: reproducible read-only
  public-data access attempt, with raw successful responses and no calibration.
- `validate_phase1.py` and `phase1_validation.json`: exact arithmetic witnesses,
  documentation links, baseline gate and original-file preservation checks.

Baseline command from repository root, using the existing environment:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --junitxml=.tmp/narrative_baseline_pytest.xml
```

The initial default-temp attempt was interrupted after 102 tests completed and
did not produce a final XML. Collection separately found 138 tests. A diagnostic
retry with workspace-local temporary files localized the stall to Streamlit's
asyncio loopback socket creation. Its trace and completed-test log remain in
`sandbox_blocked_pytest.log` and `sandbox_blocked_progress.jsonl`. The unchanged
suite passed with local socket access: **138 passed, zero failures/errors/skips**
in 63.447 seconds according to the JUnit suite timer. XML/logs are saved directly
to this evidence directory. Phase 1 arithmetic, document and preservation checks
also pass; all 445 inventoried original files are unchanged. Historical README counts
refer to older stages. This baseline is not a rerun of all historical economic
batches or a deployed-protocol audit. Reproduction commands are:

```powershell
.\.venv\Scripts\python.exe research/narrative_consolidation/phase1/run_baseline.py
.\.venv\Scripts\python.exe research/narrative_consolidation/phase1/probe_public_data.py
.\.venv\Scripts\python.exe research/narrative_consolidation/phase1/validate_phase1.py
```

## 2. Unresolved assumptions and implementation decisions

These are uncertainties to expose, not reasons to assume success or require a
new round of user approval. The defaults in `MECHANISM_DESIGNS.md` let later
implementation proceed without pretending empirical questions are resolved.

| ID | Unresolved issue | Starting rule / required falsification |
| --- | --- | --- |
| U1 | Will B buyers voluntarily buy A? | Acceptance and outside options depend on type/price; sweep zero to one. No universal threshold inferred from prior routing study. |
| U2 | Does the title attract extra attention? | Primary effect zero; test positive/negative feedback separately with finite budgets. |
| U3 | Will losers migrate? | Zero participation control; price-sensitive consent and actual proceeds, never market cap. |
| U4 | Can the group be defined fairly? | Frozen admitted cohort plus false-positive/negative contamination stress; operators have no right to seize funds. |
| U5 | Which score predicts future demand? | Highest score and evaluator-only future-demand benchmark separate; scores may choose wrong. |
| U6 | Is locked cash a costly signal? | Count elapsed capital-time and opportunity cost; compare refund-only support, compatible settlement and actor concentration. |
| U7 | Will losing creators participate? | Fund outside-option launches; model refusal, promotion costs and fee-sharing sensitivities. No free acquisition of their traffic. |
| U8 | Is reserve concentration durable? | Measure absolute winner and cohort reserves/depth after selling and through 7d. No permanent LP claim. |
| U9 | Is long-horizon behavior plausible? | Explicit attention decay/revival and finite remaining cash; no empirical calibration yet. |
| U10 | Does selection fit every instrument? | D cap/volume/holder scores N/A; commitment overlays in A–C must be funded in all comparison worlds. |
| U11 | Who knows the close? | Fixed, honest hidden, insider-known, biased draw and withheld reveal are separate cases. |
| U12 | Does D benefit only from lockup/batch launch? | Matched single-candidate batch and lockup controls; same post-handoff market, no prelaunch spot assets. |
| U13 | How much depends on curve shape? | Primary independent linear curves; price/capital/denomination controls and separate finite-inventory sensitivity. |

Defaults exclude leverage, arbitrary token transfer taxes/rebases, cross-chain
conversion and automatic irreversible loser conversion. They can be researched
only with explicit account/consent/debt extensions. No assumption here establishes
production feasibility or acceptance rates.

## 3. Separate implementation layout and stage gates

Future code belongs under `bonding_lab/narrative/`, with tests under
`tests/narrative/`, configurations and run artifacts under
`research/narrative_consolidation/`. Keep existing source unchanged unless a
separately tested shared utility extraction is necessary. Proposed modules:
`ledger`, `markets`, `architectures`, `settlement`, `election`, `demand`, `agents`,
`attacks`, `experiments` and CLI. A proposal is not an existing command.

| Phase | Work | Gate before following phase |
| --- | --- | --- |
| 1 | Audit, primary-source comparison, ownership/settlement specification, assumptions and baseline | Existing suite passes; preservation and arithmetic validation passes; data status explicit; four documents complete |
| 2 | Common reference ledger; A–D and S1/S2/S3; fee support, escrow, cancellation, timeout and refunds | Exact/quantized accounting properties; full liquidation; repeated/refused claims; no-winner tests; float parity; deterministic financial traces for every architecture |
| 3 | Finite funded agents, latent narrative opportunities, acceptance/outside choices, elections | Same pre-policy tape hash across models; sybil budget property; no future information; wrong-winner examples; zero-feedback/zero-acceptance controls; fixed and random close replay |
| 4 | All attack families below and constrained policy optimization | Complete-exit P&L/cost reconciliation; feasible oracle-information limits; held-out seeds; independent-control policy search; profitable counterexamples sought |
| 5 | Controlled Monte Carlo, uncertainty, acceptance thresholds and robustness | Completed manifests for declared matrix; invariant failures retained/repaired; no pooling repeated seeds/policies; main conclusions survive specified controls or are rejected |
| 6 | Dashboard/replay and findings report | Dashboard consumes validated ledger outputs; UI tests/replay parity; report tables reproduce from completed artifacts |

Re-run the existing suite at each code-changing gate. Do not mark later phases
complete based on design documents, smoke runs, successful UI rendering or
supported CLI flags. If a run fails, keep the failure and source snapshot before
repair; reruns use a fresh named bundle.

## 4. Threat matrix and required outputs

| Attack/scenario | Decision variables and comparison |
| --- | --- |
| 1 Whale wins then dumps | Candidate, buy size/timing, aliases, residual and exit schedule; compare title capture and ordinary early trading |
| 2 Coordinated metric capture | Wallet splits, thresholds, lock duration and concealed ownership; fixed actor capital |
| 3 Wash ranking | Round-trip count/size, rebates, fee beneficiary and funding reuse; actual unrecoverable costs |
| 4 Creator spam | Candidate count, launch cost, promotion allocation and recognition evasion; demand denominator includes all spam |
| 5 Cross-narrative contamination | False metadata/group assignment and entry timing; no access to unconsented reserve |
| 6 Legitimate creator misgrouped | Lost choice, refusal, refunds, outside venue and creator welfare |
| 7 Exit rush | Time to close, belief updates, S2 redeemable versus locked claims, synchronized and staggered exits |
| 8 Migration frontrun | Pending batch size, capital, victim output cap and execution order; include failed attacks and protected batches |
| 9 Price manipulation before conversion | Thin secondary venue, funded spot distortion, reference/TWAP bounds and fallback; primary D prelaunch venue N/A |
| 10 Losing creator refuses | Outside-option quality, expected fees, launch/promotional expense; count absent launches/traffic |
| 11 Winner popularity collapses | Common demand shock immediately after close; independent control and alternative true-demand winner |
| 12 No qualified candidate | Empty/tied/underfunded cohort, incompatible escrow, withheld reveal and timeout; exact refunds |

Each row exports actor peak capital at risk, acquisition principal, total fees,
realized/unrealized P&L, feasible complete-exit cash profit or residual inventory,
other-participant paired losses, per-market reserves and winner capital remaining.
Nonfinancial shocks have a no-attacker label and zero attack-profit statistics,
not a fabricated malicious P&L. Attack cost includes promotion, launch, network
and funded capital-time expense separately from recoverable principal.

Search time/size/exit/candidate/alias policies over feasible capital ranges; include
abstention, grid search and local refinement. Use finite shared funding, actual
countervenue depth and action costs. Freeze best policies after training, test on
unseen seeds and report the best found attack within the disclosed class. Tune
an attacker independently in A too. A finite failed search cannot prove safety.

## 5. Matched demand and experiment design

Counter-based or separately keyed random streams for narrative attention,
candidate quality/loyalty, actor endowments, execution ordering, acceptance and
attacker choices prevent additional rejected actions from shifting every later
draw. Keys include seed, actor, opportunity and stream name. Same opportunities
and outside budgets apply across worlds; realized fills and subsequent balances
can differ. Demand is not replenished when a trade is rejected or a whale exits.

Candidate choice uses frozen synthetic utility coefficients plus endogenous
prices/history. Export the coefficients. Future-demand oracle calculations are
evaluation-only and use untouched future opportunities under neutral exposure;
do not make the favored candidate win by construction. Creators influence
visibility only through a declared response to paid promotion, not free social
impressions converted to buyers.

Stage 5 matrix includes all candidate counts 2/5/10/25/50/100 and election windows
2/5/15/30 minutes, low/high total demand under **fixed total** funding, popularity
and decay, creator concentration, whale share, acceptance, migration participation,
fees, depth and creator incentives. Hold numerical event resolution constant in
economic time around elections; reducing events for speed is a separate study.
Use full 7-day simulated timestamps with fine close resolution and coarser
event-driven follow-up where validated; report events as well as elapsed time.

Proposed main factorial spine: six counts × four windows × two demand levels ×
eleven acceptance levels (0,.1,...,1) = 528 cells per applicable architecture/rule.
Acceptance is N/A in A/B rather than 11 duplicate independent observations.
Add one-factor sweeps, preregistered interactions and joint worst cases instead
of claiming a full cross-product of all knobs. Candidate counts and attention
increase separately: more tokens never automatically multiply total demand.
Report the actual executed cell count and seed count for every result.

Proposed seed partition: development 0–19; attack training 100–149; screening
1000–1099; final confirmation 10000–10499. These are planned ranges, not executed
runs. Pilot cost and variance before fixing confirmation budget. If a run is
too costly, narrow the declared question or report an incomplete matrix; do not
quietly replace 500-seed claims with smoke results. Preserve raw seed outcomes,
failed-run counts, full configurations, software versions, source/tape hashes,
wall time, search candidates and completion status.

Compute paired seed differences, medians, 5/25/75/95 percentiles, drawdowns and
worst observed tails. Bootstrap paired seeds for effect/threshold uncertainty;
use Wilson intervals for profit frequencies. Wallets in the same world are not
independent seeds; duplicate cached runs add no sample size. Treat extensive
ranking as exploratory and use untouched confirmation for selected claims.
Intervals describe the assumed model, not real-market parameter uncertainty.

## 6. Metrics and decision criteria

Primary endpoints are winner **and cohort** retained trading capital, executable
sell depth at 1/5/10% impact, organic funded activity and participating actors
at +1h/+24h/+7d. Report fee-inclusive buy/sell slippage, abandoned quote, accepted
routing by count and quote, voluntary migration by eligible claims and actual
recoverable collateral, creator participation/realized cash outcomes, trader
realized P&L distributions and separately marked positions. Include gross flow,
net deposits, reserves, fees, escrow and any LP claims as distinct columns.

For equal capital, compare A–D under the same endowments, launch costs, curve
parameters, promotion response and economic horizon; disclose where D's initial
state differs. Evaluate a common candidate identity using a frozen neutral
benchmark and the best realized token too, so selection-conditioned winner
comparisons do not overstate performance. A chooses no official winner.

Estimate acceptance break-even per setting using paired capital/depth outcomes.
Use the analytical decomposition in `ECONOMIC_INVARIANTS.md` as a check, then
refine the acceptance grid only on development data and confirm held out. A
positive effect at one acceptance rate is not a universal threshold; nonmonotonic
effects or no crossing must be reported. Separate reserve gains due to involuntary
lockup from gains after all voluntary exit windows.

Reject a proposed variant if its apparent gain requires double-counting capital,
incompatible ownership, unbounded external demand, hidden subsidized inventory,
unfunded creator cooperation or an unverifiable identity oracle. Reject a broad
economic advantage if plausible acceptance/loyalty/creator assumptions yield
inferior cohort retention or organic survival, if profitable capture overwhelms
any depth improvement, or if improvement disappears against a matched voluntary
single-token/batch control. A larger winner share alone cannot pass.

Later `NARRATIVE_RESEARCH_FINDINGS.md` must answer all ten questions in the brief:
retention, executable depth, survival versus cap, robust selection, acceptance
break-even, profitable capture, loser treatment, creator incentives, equal-capital
architecture ranking and rejection conditions. For every answer distinguish
proof/arithmetic, synthetic completed evidence, empirical observation and unknown.

## 7. Historical data work and dashboard prerequisites

The Phase 1 access probe is discovery only; collection methods, zero paid spend,
request failures and unavailable fields are documented with the raw responses.
The network retry obtained two 30-pair keyword snapshots after sandbox DNS
failures; neither establishes a complete historical cluster or unique people.
No historical behavioral estimates are imported. Further historical work requires
mint-level cluster labels, launch and pool-migration times, deduplicated reserves,
decoded quote flows, holder/creator concentration and survival windows with dead
tokens retained. Record provider pricing/access scope before any paid collection.
Fit only supported parameters, carry missingness/identity ambiguity, and keep a
synthetic path when reliable coverage is unavailable. Historical correlations
cannot show that this mechanism would have caused better outcomes.

Only after validated models, extend the existing dashboard with a separate
narrative tab: group/candidate creation; behavior/window/rule controls; replayed
rankings and finalization; explicit capital-flow and migration ledgers; attack
replay; A–D comparisons; seed distributions and depth/retention charts. Replay
must show actual timestamped authorization, refunds, no-winner and abandoned
orders. Display simulated time and assumptions; do not label replay as live
on-chain execution. Keep old dashboard tests and workflows passing.


---

