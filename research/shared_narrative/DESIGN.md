# Shared narrative curve vs independent launches — design

31 October 2026. Off-chain synthetic research. This document fixes the two arms,
the attention model, the matching scheme and the exact results that hold
before any simulation. It was written before the Monte Carlo runs. The
implementation is in `bonding_lab/shared_narrative/`.

## 0. What is reused from the repository

| Existing component | How it is used here |
| --- | --- |
| `bonding_lab.engine` (`Curve`, `Parameters`, `precise`, `decimal`, `RejectedTrade`) | The Decimal reference for the linear-shape arms is `engine.Curve` itself, at coupling 0 (Arm A) and coupling 1 (Arm B). The new pump-shape Decimal reference reuses `precise` (160-digit context), `decimal` input validation and `RejectedTrade`. |
| `bonding_lab.fast.FastBook` | The float64 oracle for the linear shape. The new skin ledger runs in linear mode and must match `FastBook` fill by fill at coupling 0 (A) and coupling 1 (B). |
| `tests/test_fast.py` parity pattern | The same random-sequence parity check is applied to the new pump-shape float ledger against its Decimal reference, and to the skin ledger against `FastBook` and `engine.Curve`. |
| `bonding_lab.agents.KINDS` | Agent vocabulary: retail, whale, momentum, holder, creator, sniper, bundler, cross_mev (arbitrage), adversary. |
| `bonding_lab.narrative.model.stream` | Named, SHA-256-seeded random streams. Each random input (launch times, arrivals, budgets, attention, exits, liquidation order) has its own stream, so changing one input never moves another. |

What I had to add, and why: **the engine has no pump.fun-shaped curve.**
`engine.Curve` is a linear-price, quadratic-reserve surface. `PRIOR_ART.md` already
notes it is "not a replica of Pump's reserve formula". The question is about
pump.fun-shaped launches, and shape decides the answer (§3), so a
constant-product curve with virtual reserves and graduation was added as a
second curve function. The existing linear engine is kept as a shape-robustness
arm. Nothing in the existing engine, agents or tests was modified.

## 1. The two arms

Both arms use the same ledger (`SkinBook`). Each *skin* is a mint that users buy,
hold and sell. Each skin maps to a *curve* that holds the reserve. The one and only
difference between arms is that map:

- **Arm A (control):** `curve_of_skin = [0, 1, ..., 9]`. Ten independent curves.
- **Arm B (shared):** `curve_of_skin = [0, 0, ..., 0]`. One curve, one reserve, one
  supply. Ten mints, each with its own name, ticker and image. All are priced
  identically and are fungible 1:1 against the shared reserve.

Selling skin *i* needs skin-*i* holdings (separate mints), but every skin is
priced and redeemed against the same reserve. In the linear shape, Arm B is
exactly `engine.Curve(coupling=1)`. With coupling 1, every token's price is
`p0 + k·Q`, and the reserve is `p0·Q + k·Q²/2`. A test proves this equivalence.

### Curve shape (pump.fun-like; parameters, not a quote of current rates)

Pump's public docs describe virtual reserves on a constant-product curve, then
migration to an AMM. Defaults, all in USD at a fixed SOL = $150 (no external
markets):

- Virtual quote `x0 = $4,500` (30 SOL) and virtual tokens `y0 = 1.073e9`;
  `K0 = x0·y0`. Total supply `N = 1e9`.
- The curve phase holds `x = x0 + R` and `y = K0/x`. Tokens sold are `s = y0 − y`.
- Graduation happens when `s = 793.1M`, which is real reserve `R_g = $12,750.80`.
  Then the reserve and the remaining 206.9M tokens move into a constant-product
  pool, `K' = R_g·206.9M`. The LP is burned (locked forever), as in pump.fun.
  The graduation mcap is $61.6k on the curve and $61.6k in the pool (continuous).
- Fees: total `f = 1%` on gross, charged outside the reserve. The creator share
  is `s = 30%` (0.30%); the rest goes to the protocol. Gas is $0.05 per
  transaction. All are swept.
- Paper market cap = price × N (pump.fun's FDV convention).

The linear robustness shape is `p = p0 + k·q`, with `p0 = x0/y0`. `k` is set so
the reserve at 793.1M tokens equals `R_g`. Its paper mcap is circulating `p·q`,
the engine's `quoted_market_cap` convention. It has no graduation.

## 2. Matching scheme and attention model

One seed produces one **tape**. The tape is generated once and then executed in
both arms. It contains:

- Launch times for the ten memes (meme 0 at t = 0; the others uniform over the
  first 15 min).
- Organic arrivals, a Poisson process with decaying intensity
  `λ(t) ∝ exp(−t/45 min)`, over a 240-minute horizon. Each arrival has a type
  (retail 55%, momentum 20%, whale 5%, holder 20%) and a dollar budget (lognormal,
  median $50, σ = 1, cap $2,000, whales ×10). It also has its exit parameters
  (take-profit, stop-loss, trailing stop, max hold, panic threshold).
- **The meme each arrival picks.**
- Scheduled, arm-invariant buys: creator first buys, sniper entries, bundler
  entries, adversary entries and (in attack runs) wash round-trips and spam launches.
- The terminal liquidation order.

**Each organic arrival is a fresh wallet funded with exactly its budget plus gas.**
So its buy, in dollars, is feasible and identical in both arms. Wallet
constraints are enforced by the ledger: no negative cash, and no selling
tokens you don't own.

**Attention process.** Picks are generated sequentially, before either arm
runs. A buyer at time t chooses among the memes launched by t:

- *Momentum-following* (probability `c`): picks meme j with probability
  ∝ `(V_j(t) + v0)^β`. `V_j` is the exponentially decayed (10-min half-life)
  **buy-dollar volume** shown on meme j's trending ticker. `v0 = $100` and `β = 2`.
- *Random* (probability `0.7·(1−c)`): uniform over launched memes.
- *Confused* (probability `0.3·(1−c)`): forms a momentum intent, then with
  probability 0.5 lands on a uniformly random *other* meme (a lookalike ticker).

`c` is the **attention concentration** knob. It is swept over
{0, .25, .5, .75, .9, 1}. The default is .25, which matches the user's premise
that ten memes split the traders. The realised Herfindahl index (HHI) of buy
dollars is reported next to it.

`V_j` counts only buys whose dollars are identical in both arms: organic buys,
creator first buys, sniper/bundler/adversary entries and scheduled wash buys.
It ignores price. **In Arm B all skins have the same price chart, so price
cannot be the per-skin signal anyway.** Momentum on prices would make the pick
sequence arm-dependent and break matching. Strategic, state-dependent trades
(arbitrage, every sell) are excluded from `V`. A test asserts that the pick
sequence and per-meme organic buy dollars are identical across arms.

What legitimately differs between arms is state-dependent behaviour:
take-profit, stop-loss, trailing stop and panic exits (these see that arm's
prices), creator take-profit, sniper/bundler/adversary exits and arbitrage.
That is the mechanism under test, not a matching failure.

**Agents.** retail / momentum / whale / holder are organic types: they differ in
budget and exit rule, not in attention. Creators (10) make a first buy (median
$300, lognormal) at launch and take profit at a drawn multiple, or else hold.
Snipers (3) buy each launch 2 s after the creator, for $150 each, and exit at
2×, at −40% or at 10 min. One bundler buys $1,500 of meme 0 in the launch block.
One adversary makes three $1,000 entries (at 3, 6 and 9 min) into the meme with
the highest `V`, and dumps at 2× or at 60 min. Two arbitrageurs (cross_mev)
place relative-value rotation bets: they buy the hottest meme whose curve
differs from the leader's. **In Arm B no such meme exists; arbitrage has no
opportunity and stays idle.** There is no riskless arbitrage in either arm.

**Terminal accounting.** At 240 min every remaining holder sells in a
seed-fixed random order. This is the same order in both arms. The paper mark
(tokens × spot) before liquidation and the realised cash after it are both
reported. Terminal-liquidation fees are not counted as creator income.

## 3. Exact results before simulation

All of these follow from the formulas. None is a Monte Carlo estimate.

**E1. Paper market cap is quadratic in the reserve; recoverable value is linear.**
On the pump-shape curve, price = `x/y = x²/K`, in both phases. So:

- Curve phase: `mcap = N·(x0+R)²/K0`, and recoverable = `R`.
- Pool phase: `mcap = N·x²/K'`, and recoverable = `x − K'/N`.

Recoverable means the collective exit value: the cash all holders get if
everyone sells, net of sell fees `(1−f)` and gas. It is path-independent,
because fees are charged outside the reserve. `K'/N = 0.2069·R_g = $2,638.14`
is locked forever by the burned LP.

**E2. The headline arithmetic.** A pump-shape meme at $50k paper mcap holds
`R = $11,037.86`. Ten of them hold `D = $110,378.57`, and their summed paper mcap
is $500k. The same `D` in one shared curve graduates and sits in the pool at
`x = D`. That is a paper mcap of **$4,618,187**, with recoverable value of
**$107,740**. So, holding net dollars fixed and with no fees:

| | Paper mcap | Recoverable |
| --- | --- | --- |
| Arm A, ten × $50k | $500,000 | $110,379 |
| Arm B, one shared curve | $4,618,187 (9.2×) | $107,740 (−2.4%) |

**"Ten $50k memes = one $5M runner" is exactly the curve's convexity.** Not one
extra recoverable dollar comes with it. The shared runner is *less* recoverable,
because graduation locks part of the reserve. With the linear shape the same
`D` gives 10 × $19.0k = $190k versus one $209.9k. Paper mcap is almost additive,
and no "runner" appears. A shared curve does not create a runner. A convex
curve plus concentration does.

For general allocations in the curve phase,
`mcap_shared − Σ mcap_i = (N/K0)·[D² − Σ R_i² − 9·x0²]`. Each independent curve
also carries $4,500 of *virtual* quote that is never recoverable. Arm A has ten
of them; Arm B has one.

**E3. Depth.** Raising the price by a factor `1+u` costs
`x·(√(1+u) − 1)` gross (plus fee), where `x` is the quote-side reserve,
*including virtual reserve in the curve phase*. Selling `x·(1 − √(1−u))` drops
it by `u`. Depth is linear in `x`. One fresh curve costs $22.44 / $111.13 /
$219.64 to move 1% / 5% / 10%. An A meme at $50k costs $77.50 / $383.71 /
$758.38. The shared curve holding `D` costs $550.52 / $2,725.81 / $5,387.45.
Per-token depth in B is about 7× a single A winner. But depth is not additive
across A's ten curves, because nobody can trade across them.

**E4. Creator buy-side fee income is identical across arms.** Picks and dollar
budgets are matched, and the fee is ad valorem on gross dollars. So creator j's
fee on buys is `s·f·Σ gross` over the buys that picked j, in both arms.
**A shared curve cannot flatten creator fee income on the buy side; fee income
follows attention, and attention is the lottery.** Any difference comes only
from (i) sell-side volume, which is larger in B for skins whose holders ride the
shared price up, and (ii) the creator's first-buy P&L.

**E5. The first buy loses its floor in B.** In Arm A every creator's first buy is
the first buy on a fresh curve, at floor price `x0/y0`. In Arm B only the first
skin's creator gets the floor. Creator j buys at the shared price at time `τ_j`,
after everyone before them has bought. The same holds for snipers: A offers ten
fresh floors, B offers one.

**E6. Wash trading loses directly at any split below 100%.** An immediate round
trip of gross `G` with no intervening trade returns exactly `G` (constant
product, fees outside the reserve). It pays `2fG + 2·gas` and rebates `2sfG`
to the creator. Net = `−2fG(1−s) − 2·gas`. That is negative for every `s < 1`,
and still negative at `s = 1` while gas > 0. Wash can only pay through the
attention it buys (`V_j`). In Arm B, diverted attention does not move the
curve: the same dollars land in the same reserve whichever skin they pick. So
the only payoff is fee share taken from other skin creators. In Arm A it also
pumps the washer's own curve, which raises their first-buy P&L.

*Caveat found in testing:* a round trip that crosses graduation is not
path-independent, because the pool's K differs from the curve's. It loses
exactly the value left locked in the LP.

**E7. Bundling at launch.** The first buyer of budget `b` on a fresh curve gets
`T(b) = y0 − K0/(x0 + (b−gas)/(1+f))` tokens in either arm. Arm A has ten
fresh launches, Arm B one. Share at minute 1 is `T(b)/circulating(1 min)`. In B
the denominator includes every skin's buyers.

**E8. Skin spam break-even.** For a spammer with m skins, no first buy and no
wash, the gross profit is `s·f·(gross volume on spam skins) − m·L − gas`. Under
uniform random/confused attention, the volume share of m spam skins among n+m
is at most `m/(n+m)` of the `(1−c)` non-momentum flow. The break-even launch
cost is `L* = s·f·E[volume per spam skin]`. The simulation measures it with the
best spam policy found.

**E9. Zero sum.** After terminal liquidation, the sum of every participant's P&L
(including creator fee income) equals
`−(protocol fees + gas + launch costs + LP value left locked)`.
Paper market cap adds nothing to this sum. The simulation asserts this identity
on every run.

## 4. Statistics and protocol

- Matched seeds. The paired difference B−A is computed seed by seed.
  Percentile-bootstrap 95% intervals resample seeds (2,000 resamples). Means,
  medians, quantiles and the worst observed outcome are reported.
- Main study: confirmation seeds 1000–1299 per attention level. The
  shape-robustness check uses fewer seeds.
- Attacks are adaptive. A policy grid is searched on training seeds 0–39. The
  best response is frozen and then evaluated on held-out seeds 5000–5199. Its
  profit is incremental against the same seed without the attack.
- Calibration is not evidence. The demand scale is 6,200 expected organic
  arrivals over 4 hours. It was set on 16 development seeds, using only Arm A
  meme peaks, so that at the default `c = .25` the median Arm A meme peaks near
  the user's premise of $50k (measured: $48.9k). It is also swept ×0.5 and ×2.

## 5. Limits fixed in advance

These are synthetic agents with an assumed attention process. There are no
external markets, no real adoption or retention model and no calibration to
on-chain data. The SOL price is fixed. There is no MEV ordering model beyond
explicit same-block sequencing. Creator behaviour is a fixed rule, not an
optimised strategy (except in the attack searches). Nothing here is market
evidence.
