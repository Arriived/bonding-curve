# A maker role for the room

Status: **engineering design. Nothing implemented.** Legal questions are the owner's and are deliberately out of
scope here. This is about what is mechanically possible on `doors_v1`'s curve, and what the arithmetic rules out.

## 1. The gap

| structure | roles it admits |
|---|---|
| Order book | makers **and** takers |
| AMM | LPs **and** traders |
| **Bonding curve** | **traders only** |

A bonding curve has no maker side. The curve *is* the liquidity, it is owned by nobody, and no outside capital
can deepen it and be paid for doing so. Capital that would happily be a counterparty for a fee — without ever
wanting to hold the asset — is structurally locked out of primary issuance and can only appear after graduation.

## 2. What the room actually is

The room is a constant-product AMM with virtual reserves:

```
x = v_sol + reserve          y = v_tok - sold          x·y = k = v_sol·v_tok
reserve(q) = v_sol·q/(v_tok − q)        price p(q) = v_sol·v_tok/(v_tok − q)²
```

Defaults: `v_sol` 30,000,852,995, `v_tok` 1,073,025,606,000,000, `k ≈ 3.219e25`, supply `U` = 1e15.

**Price impact depends only on `x`, not on `k`.** For a buy of Δ, impact ≈ 2Δ/x. Measured on the live curve:

| buy | at reserve 0 | at 10 SOL | at 50 SOL |
|---|---:|---:|---:|
| 1 SOL | 6.78% | 5.06% | 2.52% |
| 10 SOL | 77.78% | 56.25% | 26.56% |

A 10 SOL buy into a fresh room costs 78% in impact. That is the problem a maker would solve, and it is why size
cannot execute on a launchpad today.

## 3. Design A: parallel maker pool (recommended)

The curve is untouched. A room may additionally have a standard constant-product pool, seeded by makers with SOL
and room tokens at the room's current price. Every room trade is routed: filled from the curve, the pool, or
split between them, whichever is better for the taker. Makers earn a fee on what they fill and bear impermanent
loss.

**Why this one.** It changes no curve maths, no graduation trigger and no supply bound, so nothing already
measured has to be re-derived. Makers get a position they already price daily (LP with IL). The curve remains the
guaranteed quote of last resort, which is the whole reason bonding curves exist.

**The part that is ours alone.** A maker in the room earns from **every door's flow**, because every door trade
settles through the room. LPing one memecoin elsewhere earns from one coin; making a room earns from the whole
narrative — every copy, every vamp, every door that opens later. The aggregation that protects users is also what
makes the maker position worth taking. No competitor can offer this, because no competitor aggregates a narrative
into one pool.

**What has to be got right:**
- **Routing must not be sandwichable.** A router choosing between two venues creates an ordering the searcher can
  exploit. The split must be deterministic from on-chain state and committed in the same instruction.
- **Arbitrage between pool and curve is a feature, not a leak.** It keeps the two aligned, and the arbitrageur's
  profit is simply the maker's impermanent loss made explicit. It should be measured, not prevented.
- **A pool priced worse than the curve never gets routed to.** That is correct behaviour and means a careless
  maker loses nothing except opportunity.
- **Graduation.** The pool position must migrate with the room or be withdrawable before it. Decide alongside the
  Meteora graduation design, not separately.

## 3a. Prior art, and the failure it demonstrates

The maker role already exists commercially, owned by the venue rather than by the market. Axiom, a Solana
trading terminal, is reported to route SOL↔USDC legs through its own proprietary AMMs at roughly 0.6% worse than
public routes, inside an advertised 1% fee ([@bencirc, 10 Nov 2026](https://x.com/bencirc), using
[Circular Replay](https://github.com/Circular-fi/circular-replay-api-usage)).

**Verified from chain** (tx `4fckb2Lp…FXtn`, slot 467,760,261): the signer spent 12.002 SOL for 14.8M of a
pump.fun token, routed as `SwapV2` through `FLASHX8DrLbgeR8FcfNV1F5krxYcYMUdBkrP1EPBtxB9` for the SOL→quote leg,
then `BuyExactQuoteInV2` on PumpSwap. The two-hop structure is exactly as described. **Not verified:** who owns
`FLASHX8…`, and whether the fill was worse than the best route at that slot — that is the actual claim and it
needs a historical-state replay against alternatives.

**What it proves:** the maker role is worth real money. ~0.64% on a ~$1,000 trade, at terminal volume, is a large
business.

**What it warns:** if we run both the maker pool and the router, we face precisely this temptation — route to
ourselves slightly worse and keep the difference, invisibly, because a quote is just a number. This is the same
failure as the incumbent's inverted fee schedule (`program/docs/FEE_DESIGN.md` §1), moved from a fee table nobody
reads into a route nobody can see. Both work only because the user cannot check.

**Therefore, a hard requirement on Design A, not a promise:**

1. The route split is **deterministic from on-chain state** and computed in the same instruction that settles,
   so it cannot depend on anything off-chain or operator-chosen.
2. Every routed trade emits the quote it compared against, so the decision is reconstructible from the
   transaction alone.
3. **Design so that a third-party replay exonerates us.** Circular Replay is the tool that caught this; our
   routing should be something it clears. A verifiable claim beats any marketing claim, because it needs no
   trust in us.

Permissionless making plus verifiable routing is the whole counter-position: same machine, inverted ownership.

## 4. Design B: makers deepen the curve itself — the arithmetic rules it out

The capital-efficient version: a maker's deposit scales both virtual reserves by λ, which leaves the starting
price unchanged and divides price impact by λ. Elegant, and it does not work at our parameters.

Scaling both reserves changes what the curve raises when all supply is sold:

| λ | SOL raised at full supply sale | graduation trigger |
|---:|---:|---:|
| 1 (today) | 410.83 | 85.02 |
| 2 | **52.36** | 85.02 |
| 4 | **36.45** | 85.02 |

**At λ = 2 the room can never graduate.** Selling the entire supply raises 52.4 SOL against an 85 SOL trigger, so
supply exhausts first. Codex already measured the related bound: 98.26% sold under defaults.

So deepening the curve forces the graduation trigger down in step, which changes the economics every simulation
in `PAIRED_DOORS_REPORT.md` rests on. **Not worth it for a depth improvement Design A delivers without touching
the curve.** Recorded here so it is not re-proposed.

## 5. Design C: underwriting the floor — does not exist

The intuitive idea is a maker who takes first loss on the room's floor for a fee. On a bonding curve there is
nothing to underwrite: the invariant is that the reserve exactly equals `curve(sold)` at all times, so if every
holder sells, the reserve drains to exactly zero with no shortfall. The underwriter's capital would sit idle.

It only becomes a real instrument if the room offers a floor **above** the curve, which is writing a put option
against the narrative. Priceable, but a different and much harder product. Not now.

## 6. What a maker is actually paid

Under Design A, from one source only: trade fees on the flow they fill. Three knobs, all owner decisions:

- Whether makers take a share of the existing 1%, or whether routed-to-pool trades carry their own fee.
- Whether the door creator's 60% is diluted (it should not be; that is a separate promise).
- Whether making is permissionless or allowlisted at first.

## 7. What to measure before building

1. **Is there flow worth making?** Distribution of trade sizes per room from the watcher. If almost every trade is
   under 1 SOL, impact is already tolerable and no maker is needed.
2. **What does a maker earn?** Replay real pump.fun flow through a curve-plus-pool router and compute fees earned
   against impermanent loss. If IL exceeds fees at realistic volatility, no rational maker participates and the
   design is dead on arrival.
3. **Does the aggregation advantage survive contact?** The pitch is that room flow is many doors' flow combined.
   Measure actual aggregated volume per room from the devnet run before claiming it.

## 8. Order

After graduation design, and after the fee mechanisms in `program/docs/FEE_DESIGN.md`. Design A shares its
routing and migration questions with graduation, so doing graduation first costs nothing and informs this.
