# Positioning: we built two instruments where everyone else has one

Status: **positioning and a proposed experiment. No code change.** The behaviour described is already live in
`doors_v1`; what is missing is naming it and measuring whether anyone wants it.

## 1. The claim

On every other launchpad there is exactly one sentence a buyer can express: *"this coin goes up."*

On ours there are two, because `TradeAccounts.door` is an `Option` — trading the room with no door is a
first-class path, not a side effect:

| instrument | what holding it says |
|---|---|
| **Room token** | "this narrative survives." No view on which coin wins. |
| **Door token** | "this specific coin wins", leveraged on the room beneath it. |

Holding the room while skipping every door is a position **nobody can take anywhere else**. It is long the
narrative and flat the individual bet.

## 2. Why that matters commercially

The scarce input in this market is not supply, liquidity or creators. Supply is free and infinite: 25 wallets
produced 761,000 coins (`program/docs/FEE_DESIGN.md` §1). Liquidity is manufactured by the curve. The scarce
input is **buyers with fresh capital**, and every tool the incumbent built to win them — callout rewards, more
launches, faster flips — consumes that pool faster.

Buyers are scarce **because the only available position requires belief in a specific token**. You have to be
right about *which* coin. That is a high bar, and it is why the buyer pool is small and exhausts.

Room exposure is a lower-conviction product. It asks only "does this narrative have legs", which is a question
far more capital is willing to answer. That is the same structural move Variational made in perps: stop
competing for the scarce input, and change where the input comes from.

We have been describing the room as anti-vamp plumbing. It is also a different instrument, and we have never
pitched it that way.

## 3. Honest status

This is a **hypothesis, not a finding**. The two-instrument structure is a fact of the code. That anyone wants
the room-only position is unproven, and more thinking will not settle it.

## 4. The experiment that settles it

Cheap, and it needs no new code beyond a counter.

**Measure, from the first day of devnet and every day after:**

1. **Room-only holders.** Wallets holding room tokens with no door token in that room, as a share of all holders.
   This is the number. If it is near zero, the instrument is not real and the room is just plumbing.
2. **Room-only capital.** The same split by value, not wallet count. A handful of large room-only holders is a
   more interesting signal than many dust wallets.
3. **Holding period.** Median hold time for room-only positions against door positions. The claim is that room
   holders are lower-conviction *per coin* but **longer-horizon**, which is exactly the "pay for holding"
   behaviour the external research says the market has lost.
4. **Direction of travel.** Do door holders sell the door and keep the room when their coin fades? That
   transition is the product working: the narrative keeps the capital even when the specific bet fails. On any
   other launchpad that capital leaves entirely.

**Who measures it:** the launch watcher (`services/matcher/watcher/`) already decodes launches and trades. The
room-vs-door holder split is a small addition to it, not a new system.

**Decision rule, set in advance so the result cannot be rationalised afterwards:**
- Room-only holders **under 5%** of holders: the instrument is not real. Keep the room as plumbing, drop this
  positioning, and do not build anything on it.
- **5–20%**: real but niche. Worth naming in the product; not worth reorienting around.
- **Over 20%**, or room-only capital over 20% by value: this is the headline product, and the anti-vamp
  mechanism is the feature that makes it possible rather than the pitch itself.

## 5. What not to claim

- Do not call the room an index fund. It is not diversified across narratives, it has no manager, and the word
  invites a securities argument we do not need.
- Do not claim room holders are protected from loss. A room can fall to its floor like anything else.
- Do not lead with the runner statistics from the external research. The fee-asymmetry argument is structural
  and checkable; the runners-per-launch collapse is correlation across two different market regimes
  (`program/docs/FEE_DESIGN.md` §1).
