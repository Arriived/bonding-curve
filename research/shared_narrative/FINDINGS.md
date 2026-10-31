# Shared narrative curve vs independent launches — findings

31 October 2026. **Everything below is synthetic.** The agents follow assumed
rules and the attention process is assumed. No figure here is market evidence
or a forecast. Design, arm definitions and exact identities:
[DESIGN.md](DESIGN.md). Every number comes from `outputs/tables.md` and
`outputs/summary.json`.

## Verdict

**A shared curve does not recruit creators on its own economics, and it does
not produce the runner.**

1. **The "$5M runner" is curve convexity, not new money.** On a pump.fun-shaped
   curve, ten $50k memes hold exactly the net dollars of one $4.62M token
   (E2). The shared token is also *less* recoverable: $107.7k vs $110.4k,
   because graduation locks LP. The chart would exist only if nobody sold. With
   take-profit behaviour, the shared curve's median peak was **$464k**. The
   largest peak in 1,800 matched runs was $830k (Arm B) and $865k (Arm A). No
   run in either arm reached $1M.
2. **Creator fee income is identical in both arms.** Fees follow attention, and
   attention is where the lottery lives. A shared curve doesn't change where
   attention goes. What B does change is the first buy: it removes nine of ten
   launch-floor first buys. At the user's own premise (fragmented attention), a
   creator is better off in Arm A on every risk measure. A second-order
   stochastically dominates B. B improves median earnings only when attention
   is already concentrated, and even then it adds a loss tail that A does not
   have.
3. **The honest cost is real.** B cuts recoverable reserve by more than half
   at default concentration. It exposes every skin's holders to every other
   skin's panic: −20.1 points per bystander vs 0.0 in A. It roughly triples
   bundler profit at small budgets.

What B genuinely does better: it eliminates sniper profit on nine of ten
launches. Aggregate organic buyer losses are also smaller when attention is
fragmented (−$33.0k vs −$47.8k per seed at c = 0.25), though not when it is
concentrated. Both are side effects of having only one launch floor, not of
the "runner".

## 1. Does the narrative produce a runner?

Peak paper market cap of the largest single token. Arm A is the best of ten;
Arm B is the shared token. Values are medians with 95% CIs over 300 matched
seeds per row. HHI is the realised concentration of buy dollars.

| attention c | HHI | A best token | B shared token | B/A per seed (median [p10, p90]) | A summed narrative peak |
|---|---|---|---|---|---|
| 0 | 0.12 | $112.8k [$109.5k, $118.6k] | $463.7k [$457.4k, $471.6k] | 4.08× [2.71, 5.24] | $397.8k |
| **0.25 (default)** | 0.17 | $176.2k [$172.8k, $180.6k] | $463.7k [$457.4k, $471.6k] | 2.59× [1.98, 3.47] | $423.6k |
| 0.5 | 0.37 | $287.0k [$282.4k, $292.1k] | $463.7k | 1.60× [1.33, 1.96] | $454.0k |
| 0.75 | 0.65 | $384.2k [$376.2k, $390.5k] | $463.7k | 1.21× [1.00, 1.47] | $494.9k |
| 0.9 | 0.84 | $431.9k [$428.0k, $439.4k] | $463.7k | 1.07× [0.91, 1.27] | $510.8k |
| 1 | 0.98 | $464.9k [$456.3k, $469.0k] | $463.7k | 1.00× [0.85, 1.19] | $509.4k |

- P(peak ≥ $1M) = 0% in every cell of both arms. P(≥ $5M) = 0%.
- The B column does not depend on `c`. In Arm B every pick lands in the same
  reserve, so attention changes only which creator gets the fee (tested).
- **B's single token is about the size of A's *summed* narrative.** Sharing
  moved roughly the same paper value onto one chart. It did not create more.
- At full concentration (c = 1), A's winner *is* the shared curve (ratio 1.00).
  The comparison only matters to the extent that attention fragments.

**Paper vs recoverable.** "Recoverable" is the cash all holders would get if
everyone exited, net of fees (E1, exact).

| c | A top paper peak / recoverable then | B paper peak / recoverable then | peak total recoverable A | B | B − A (mean, CI) |
|---|---|---|---|---|---|
| 0.25 | $176.2k / $18.7k (9.4×) | $463.7k / $32.0k (14.5×) | $78.5k | $32.0k | −$46.6k [−$47.2k, −$46.0k] |
| 0.9 | $431.9k / $30.8k (14.0×) | $463.7k / $32.0k (14.5×) | $51.3k | $32.0k | −$19.2k [−$19.7k, −$18.8k] |

**Why the shared curve holds less money.** I diagnosed this by switching exit
rules off one at a time. The driver is take-profit selling. On a shared chart
every early holder of every skin is in profit at the same moment, and they
sell. In Arm A, money sits in nine quiet curves whose holders never hit their
targets.

- With all organic exits disabled, reserves are equal across arms, as they must
  be. The shared token then reaches a median paper peak of **$186.5M** on
  **$692k** recoverable (270×). That is the only setting in which a
  "$5M+ runner" exists.
- With patient holders (take-profit ×2), B's median peak is $745k.
- With demand ×2, it is $887k, and P(≥ $1M) = 10%.

In every finite-exit setting, B/A stays at 2.6–2.8×.

**Curve shape decides the paper result.** With the repository's linear curve
(the existing engine at coupling 0/1), paper/recoverable is about 2× in both
arms. B's token ($626k) equals A's summed narrative ($608–625k), and
recoverable differs by only 3%. On a non-convex curve, no runner appears even
on paper.

## 2. Depth (default c = 0.25)

| | 30 min, A | 30 min, B | 120 min, A | 120 min, B |
|---|---|---|---|---|
| reserve held, total | $53.7k | $15.8k | $75.2k | $21.7k |
| reserve held, largest curve | $12.3k | $15.8k | $14.9k | $21.7k |
| recoverable, total | $48.5k | $13.1k | $65.1k | $18.9k |
| cost to lift price 1% / 5% / 10% (A: top meme · median meme) | $70 / $345 / $681 · $43 / $211 / $417 | $80 / $395 / $781 | $77 / $382 / $753 · $51 / $254 / $502 | $110 / $542 / $1,072 |
| sale that drops price 1% / 5% / 10% (A: top meme) | $69 / $346 / $702 | $79 / $397 / $805 | $76 / $384 / $777 | $108 / $545 / $1,104 |

Arm B's single book is only **1.2× (30 min) to 1.4× (120 min)** deeper than
Arm A's best meme. The exact identity predicted 7× if all the money stayed
(E3). It does not stay. Per-token depth is about 1.9× A's median meme. But
across the narrative, B holds 70% less reserve than A at both checkpoints.

## 3. Creator earnings — the recruiting number

Per creator, pooled over 10 creators × 300 seeds, with seed-cluster bootstrap
CIs. Net = fee income + first-buy P&L. Launch cost is 0 here (spam section
below). Full per-creator rows are in `outputs/main_creators.csv.gz`.

**Default c = 0.25 (ten memes split the traders):**

| | Arm A | Arm B |
|---|---|---|
| mean net | $1,753 [$1,726, $1,778] | $1,567 [$1,530, $1,602] |
| median net | $1,526 [$1,493, $1,557] | $1,372 [$1,332, $1,408] |
| **P(net > 0)** | **100.0%** | **91.7%** [90.7%, 92.7%] |
| P(net ≥ $1,000) | 78.8% | 65.4% |
| mean / median fee income | $441 / $315 | $441 / $303 |
| first-buy P&L mean / P(>0) | $1,313 / 99.8% | $1,125 / 82.7% |
| net p1 / p5 / p10 / p25 | $430 / $675 / $788 / $1,073 | −$438 / −$106 / $45 / $761 |
| net p50 / p75 / p90 / p99 | $1,526 / $2,223 / $3,049 / $4,644 | $1,372 / $2,265 / $3,211 / $5,305 |
| worst / best observed | $34 / $6,512 | −$1,096 / $7,692 |
| certainty equivalent (CARA a = 1/$1,000 · 1/$300) | $1,442 · $1,100 | $997 · $360 |
| second-order stochastic dominance | **A ⪰ B** | — |

**Across concentration:**

| c | mean net A / B | median net A / B | P(net>0) A / B | P(fees ≥ $100) A / B | CE a=1/$300 A / B |
|---|---|---|---|---|---|
| 0 | $1,786 / $1,567 | $1,613 / $1,430 | 100% / 94.1% | 100% / 100% | $1,232 / $425 |
| 0.25 | $1,753 / $1,567 | $1,526 / $1,372 | 100% / 91.7% | 100% / 100% | $1,100 / $360 |
| 0.5 | $1,514 / $1,567 | $1,154 / $1,243 | 99.9% / 87.7% | 99.9% / 99.4% | $699 / $254 |
| 0.75 | $1,037 / $1,567 | $368 / $1,147 | 99.9% / 84.1% | 52.2% / 45.4% | $334 / $165 |
| 0.9 | $733 / $1,567 | $82 / $1,090 | 100% / 83.0% | 11.2% / 10.9% | $138 / $116 |
| 1 | $617 / $1,567 | −$0.64 / $1,058 | 42.7% / 82.7% | 10.0% / 10.0% | $38 / $84 |

**Reading this honestly:**

- **Fee income is lottery-shaped exactly to the degree attention is, and
  identically in both arms.** At c = 0.9 the top creator takes 90.5% (A) vs
  91.3% (B) of the ten creators' fees. The median creator earns $47 vs $41 in
  fees. Buy-side fees are arm-invariant by construction (E4), and a test
  verifies this. Sell-side fees differ by a few dollars. **A shared curve
  cannot flatten the fee lottery.**
- Every difference in net earnings comes from the creator's first buy. In
  Arm A every creator buys at a fresh floor (E5). In Arm B only the first
  launcher does. By launch order at c = 0.25, B's tenth creator has median net
  $938 vs $1,338 in A, and P(net > 0) of 79.7% vs 100%.
- The user's prediction ("A lottery-shaped, B flatter") holds only at high
  concentration (c ≥ 0.75). There, B lifts the median creator from ~$82 to
  ~$1,090, because losing creators' first buys ride the shared curve. But B is
  never risk-free. It has a 16–17% chance of losing money, a tail A does not
  have until c = 1. At c = 0.9 the certainty equivalent is already roughly
  equal at a = 1/$300 and worse in B at a = 1/$100 (−$645 vs $92). Neither arm
  dominates.
- **Which arm should a risk-averse creator prefer?** At low-to-moderate
  concentration (the premise of the question), **Arm A**: it dominates. At high
  concentration it depends on risk tolerance. A mildly risk-averse creator
  gains from B's higher median. A strongly risk-averse one (a ≥ 1/$100) still
  prefers A. **Most of this creator advantage is first-buy trading P&L, not
  fees.** That makes it a speculative position the creator funds and can lose,
  not an income stream the mechanism provides.

## 4. Trader outcomes (c = 0.25; same buyer, same dollars, both arms)

| buyer group | mean return A / B | paired B − A (CI) | $-weighted A / B | median A / B | win rate A / B | p5 A / B |
|---|---|---|---|---|---|---|
| all | 1.1% / 5.9% | +4.8 pt [4.4, 5.1] | −6.4% / −4.5% | −21.7% / −34.5% | 33.1% / 31.3% | −85.5% / −95.7% |
| early (first 10 min) | 33.1% / 69.6% | +36.5 pt [34.6, 38.3] | 16.2% / 37.6% | −20.8% / −34.9% | 39.2% / 37.8% | −85.3% / −90.3% |
| late (after 60 min) | −16.9% / −22.6% | −5.7 pt [−6.5, −4.9] | −20.9% / −23.2% | −28.0% / −38.9% | 28.8% / 26.8% | −86.6% / −97.8% |
| picked A's winner | 4.8% / 22.1% | +17.3 pt [15.8, 18.8] | −5.7% / 6.5% | −26.8% / −33.0% | 32.5% / 33.3% | −91.2% / −94.6% |
| **picked a meme that lost in A** | −0.5% / −2.6% | **−2.1 pt [−2.7, −1.5]** | −6.8% / −9.8% | −19.1% / −35.3% | 33.5% / 30.2% | −80.8% / −96.1% |
| picked a bottom-half meme in A | −1.3% / −8.2% | −6.9 pt [−7.7, −6.2] | −6.5% / −13.3% | −17.7% / −35.1% | 33.8% / 29.7% | −76.7% / −96.3% |

- **The "loser picker" does not get rescued in B.** At default concentration,
  the same buyer does *worse* in B (−2.1 points; −6.9 for bottom-half picks).
  In A, a quiet meme drifts and its buyer loses fees and a little price. In B,
  that buyer bought into a chart that the whole narrative had already pumped,
  and it later deflates. Only at c = 0.9, where A's losers are a small, very
  late minority, does B help them (+2.0 pt [0.9, 3.0]).
- B shifts outcomes toward early buyers. The mean improves (driven by a few
  large early wins), while the median, win rate and p5 all get worse. Paper
  returns at 240 min (A 16.9%, B 33.7%) overstate what holders realise after
  exit (A 1.1%, B 5.9%), especially in B.
- In dollar terms, organic buyers as a group lose less in B at default
  concentration: −$33.0k vs −$47.8k per seed. That is mostly because snipers
  make −$1.1k in B vs +$4.4k in A (only one launch floor), and one graduation
  locks $2.6k of LP vs $9.2k for A's several. The advantage disappears as
  attention concentrates. At c = 0.75 the loss is −$33.0k vs −$33.8k; at
  c = 0.9 it reverses, −$33.0k vs −$28.8k.
- Worst observed returns of about −104% are tiny buys where gas exceeded
  the budget.

## 5. The honest cost of Arm B: shared downside

| c = 0.25 | Arm A | Arm B |
|---|---|---|
| max drawdown of the meme a holder picked (mean) | 0.82 | 0.90 |
| hourly realised vol (1-min, first 2 h) of the picked meme | 2.05 | 4.20 |
| A's best token for comparison: drawdown / vol | 0.88 / 3.41 | — |

**Contagion test.** At 60 min, every holder of another meme (the
second-most-bought) panics and sells, and its creator dumps. The measure is
the change in a bystander's outcome vs the same seed without the shock.
Bystanders hold a different meme and stay open through the shock in both
arms: 636 per seed.

| | Arm A | Arm B |
|---|---|---|
| mean change in return | 0.0 pt [−0.3, 0.3] | **−20.1 pt [−22.1, −18.2]** |
| p5 change | −3.6 pt | −140.5 pt (includes forgone gains) |
| share of bystanders harmed by > 1 pt | 6.7% | 28.2% |
| total bystander dollar change per seed | +$32 | **−$11.0k** |

Arm A's small nonzero changes come from arbitrageurs re-routing after the
shock. In B, one skin's panic hits every skin, which is exactly the user's
concern. The worst-hit bystanders lose gains they would otherwise have
realised.

## Attacks (adaptive)

Each attack searched a policy grid on training seeds 0–39 and froze the best
response. That response was confirmed on held-out seeds 5000–5199. Profits are
incremental against the same seed without the attack.

### 1. Skin spam

| arm | best response | break-even launch cost per skin (CI) | spammer profit at $0 launch cost | honest creators' fee change |
|---|---|---|---|---|
| A | 1 copycat at 2 min, $50 first buy | $448 [$436, $461] | $448 | −$383 |
| B | 1 skin at 2 min, $50 first buy | $461 [$448, $474] | $461 | −$386 |
| A | 30 copycats (max total profit) | $130 [$129, $131] | $3,890 | −$2,194 |
| B | 30 skins (max total profit) | $120 [$117, $123] | $3,606 | −$2,161 |

- Spam pays at any launch cost below about **$450–460 per skin** (one skin).
  At 30 skins the break-even is $120–130 per skin. **B does not make spam
  harder or easier than copycat launches in A.**
- In B, spam without a first buy changes organic P&L by exactly $0: it is pure
  fee diversion. Honest creators lose almost dollar-for-dollar what the
  spammer takes.
- In A, organic buyers come out ahead with spam (+$14k at 30 copycats). The
  copycat curves are sniper-free fresh launches, which is a model artefact
  worth knowing about, not a reason to want spam.
- These break-evens depend on the assumed 30% random+confused attention share,
  which picks uniformly among visible skins. Curation would shrink them.

### 2. Wash trading for fee share

Within one phase, a round trip loses exactly `2fG(1−s) + 2·gas` (E6, tested).
This is negative at every s < 1. The best response found, confirmed on
held-out seeds:

| creator share s | best confirmed profit, A (by launch order 1 / 5 / 10) | B |
|---|---|---|
| **30% (default)** | −$1.85 / −$5.10 / +$4.06 (CI spans 0) | −$3.88 / −$6.40 / −$6.77 (all CIs < 0) |
| 50% | +$48 [+$14, +$88] / +$37 (CI spans 0) / −$32 | +$20 (CI spans 0) / −$3.74 / −$4.35 |
| 70% | +$161 / +$369 / +$320 (all CIs > 0) | +$146 / +$259 / +$197 (all CIs > 0) |
| 90%–100% | +$600 to +$2,560 | +$600 to +$2,340 |

- **At the 30% split, wash trading loses money.** The least-bad policy is the
  smallest wash, which roughly breaks even in A and loses in B.
- **It stops losing at about a 50% creator share** for the first launcher in
  Arm A, and is **reliably profitable from 70%** in both arms.
- That is far below the 100% that direct costs alone imply. In this model,
  wash volume enters the trending signal, so it buys real attention: $29k–$130k
  of organic buys diverted to the washer, taken from other creators.
- B is slightly *less* attractive to wash than A at every split. In B the
  diverted buyers' dollars land in the same reserve either way, so only the
  fee moves (E6).
- If trending signals ignored wash volume, the break-even would be 100%.

### 3. Bundling

| budget | arm | best response | profit [CI] | share of bundled supply at +1 min (same launch-block bundle) |
|---|---|---|---|---|
| $500 | A | launch-block bundle of meme 0, hold | $3,115 [$2,949, $3,283] | 12.4% |
| $500 | B | same | **$10.0k** [$9.5k, $10.5k] | 11.8% |
| $2,000 | A | spread over all ten launches, TP 6× | $8,512 [$8,425, $8,597] | 37.0% |
| $2,000 | B | launch-block bundle, hold | **$17.9k** [$17.2k, $18.6k] | 35.7% |
| $8,000 | A | spread, TP 6× | $25.8k [$25.6k, $26.1k] | 73.2% |
| $8,000 | B | launch-block bundle, hold | $25.6k [$24.8k, $26.4k] | 71.9% |

- **The share costs the same in both arms.** The first buyer on a fresh curve
  gets the same tokens in either arm (E7).
- **But in B that share is a claim on the whole narrative's flow.** Profit is
  3.2× (at $500) and 2.1× (at $2,000) higher than in A, equal at $8k.
- Organic buyers lose correspondingly more: −$10.3k vs −$3.2k at $500, and
  −$19.0k vs −$8.0k at $2,000.
- **Bundling is a side cost of Arm B, not a benefit.**

## Model limits (stated, not hedged away)

- **Synthetic agents.** Exit rules are fixed assumptions: take-profit
  1.5–20×, stop-loss, trailing stops, panic on 5-min drawdowns. The central
  "B drains" result is driven by take-profit selling. It disappears if holders
  never sell, so it is only as real as that behaviour.
- **Assumed attention process.** Momentum buyers follow buy-dollar volume, not
  price. That is required to keep picks identical across arms, and price can't
  distinguish B's skins anyway. There is no adoption model, no retention, no
  social amplification, and nothing in which a shared chart attracts *more*
  total demand. Total demand is identical by design. If a big shared chart
  pulled in new buyers, that would be outside this model, and it is the only
  route by which B could create value rather than relocate it.
- **No external markets.** SOL is fixed at $150. There are no CEX listings, no
  routing between venues and no MEV beyond explicit same-block ordering.
  Arbitrage has no riskless opportunity in either arm. In B it has none at all.
- **Pump.fun-like parameters, not a replica.** Virtual reserves, the 793.1M
  graduation and burned LP follow the public design. Fees (1%, 30% to the
  creator) and gas ($0.05) are parameters; a 50% creator share was checked.
- **Calibration** sets demand so that A's median meme peaks near $50k at
  c = 0.25. That is the user's premise, not data. Results are stable at
  demand ×0.5 and ×2.
- Creators follow fixed rules, apart from the attackers.

## Reproduction

`research/shared_narrative/reproduce.sh` reproduces everything: tests, all
stages and the report, in about 45 min on 4 cores. The tests (52 passing,
`outputs/tests.xml`) include the existing engine/parity suites. They also
cover parity of the new ledger with `FastBook` and the Decimal `engine.Curve`
at coupling 0 (A) and 1 (B), and float vs Decimal parity on the pump shape
across graduation. Every run asserts cash conservation and the E9 zero-sum
identity.
