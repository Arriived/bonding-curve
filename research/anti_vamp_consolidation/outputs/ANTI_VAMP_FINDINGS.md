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
