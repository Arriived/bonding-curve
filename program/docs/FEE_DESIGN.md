# Fee design: the external case, and two proposed mechanisms

Status: **research and design. Nothing here is implemented.** The live schedule is unchanged: 1% on room-curve
trades split 60% to the door creator and 40% to the protocol (`fee_bps` 100, `door_share_bps` 6000), a provisional
1% swap fee on the same split, `founder_share_bps` 0, and no decision yet on fees after graduation.

Two owner proposals are specified in §3 and §4. Each carries a failure mode that would make it worse than doing
nothing, written up beside it. Neither should be built before the graduation design, and both need measurement.

---

## 1. Why the fee schedule is the product decision

Two independent write-ups published 9–10 November 2026 argue that the decline of large memecoin runners is caused
by launchpad fee schedules rather than by market conditions. Both reach the same conclusion: the dominant platform
earns most from coins that die quickly, so every incentive it creates pushes toward more launches and shorter holds.

### Sources

| source | author / date | retrieved |
|---|---|---|
| ["How Pumpfun is killing the trenches"](https://sparsitydata.com/research/how-pumpfun-is-killing-the-trenches) | Kioto, Sparsity Research, 10 Nov 2026 | 11 Nov 2026 |
| [Thread on the same thesis](https://x.com/ftosol/status/2119792962032779544) | @ftosol, 9 Nov 2026 | supplied by the owner |

Both cite [@launchlytics on Dune](https://dune.com/launchlytics) and pump.fun's own
[fee table](https://pump.fun/docs/fees) for their figures. The figures below are theirs, not ours; we have not
reproduced them. Where the two sources disagree, both numbers are given.

### Their figures

**Revenue concentrates in the first hour of a coin's life.**

| claim | figure |
|---|---|
| Share of pump.fun protocol revenue from coins on the curve or under $250K | 95% |
| Share from coins less than one hour old | 75% |
| Share from coins less than one day old | 87% |
| Paid by the 15 biggest runners (worth $1.4B at their peaks), combined | ~$1.5M |
| Paid by coins on the curve or under $250K | $506M |

Sparsity's summary: *"a thousand coins dying at $20K earn it more than one coin running to $100M."*

**The fee schedule is inverted against size.** A $100 trade pays about $0.95 to the house on the curve and about
$0.05 after graduation: **19× more on the coin that never leaves the starting line.** On-curve trades pay 1.25%
total (0.95% platform, 0.30% creator), so a round trip costs 2.5% before the price moves.

**Supply held constant while runners collapsed.**

| | Q4 2024 | Q3 2026 |
|---|---:|---:|
| Launches | 3.16M | 3.05M |
| Coins reaching $10M | 207 | 24 |
| Runners per 100,000 launches | 6.5 | 0.8 |

Of 24.4M launches ever, 312 are above $100K today: **1 in 78,000**. Combined curve and PumpSwap volume fell from
$25–30B a month in Q1 2026 to $13.8B in October.

**Instant volume-based creator fees produced launch farms.** The top 25 deployers launched **761,000 coins**, fewer
than 1 in 100 graduated, and they earned **$128M**. The top wallet alone launched 171,195 coins at about $200 each.

**Paying for calls moved money to the smallest coins.** $29.6M paid to 51,115 wallets; ten wallets took 16%; the
median recipient got $13. The median called coin is +6% one minute after the call, **−48% after an hour and −74%
after a day**. Of fourteen tracked callers, one left followers ahead.

### What they prescribe, and where we stand

| prescription (Sparsity) | our position |
|---|---|
| "A higher starting market cap and deeper initial liquidity, with **compounding liquidity so the pool grows with volume**" | **This is the room.** Every door's buyers feed one shared reserve, so liquidity compounds across every copy of a narrative instead of fragmenting. Built and measured (`PAIRED_DOORS_REPORT.md`). |
| "Don't charge tiny coins the most" (@ftosol) | **Already true.** Our 1% is flat at every size: the protocol takes $0.40 of a $100 trade whether the room is new or at $100M. One runner doing $100M of volume pays the protocol about $400K; a room that dies after 2 SOL of volume pays about $1.80. We would need roughly **200,000 dead rooms to equal one runner** — the inverse of the incumbent's ratio. |
| "Make spam cost something" (@ftosol) | **Already true, and harder than asked.** A new room costs real rent, and the matcher routes a copy into an existing room instead of letting it split attention. |
| "**Fees shared with holders and LPs**, not only creators, and **creator fees that vest with how long the token survives**" | **Not done.** Our door creator's 60% is paid immediately on volume, with nothing to holders and no vesting — the same terms that produced the 761,000-coin launch farms. §3 and §4 address this. |
| "Callout rewards that pay for holders, not flippers" | Not applicable; we have no callout programme and should not add one. |

**Caution on citing these numbers.** The structural claims are checkable and strong: the fee table, the
revenue-by-age split, the deployer counts. The runners-per-launch collapse (6.5 → 0.8) spans two very different
market regimes and is correlation, not demonstrated causation. Lead with the fee asymmetry.

---

## 2. The gap these proposals close

The matcher stops a *narrative* fragmenting across many rooms. It does not stop a creator farming
*door-creation fees* inside a room, because the door creator's 60% is paid instantly on volume and is never
clawed back. That is the same incentive that produced the launch farms above, one level down.

---

## 3. Proposal A: creator-chosen holder share

**The owner's proposal.** At launch, the door creator chooses what fraction of their 60% goes to holders rather
than to themselves. A visible slider, from 0% to 100% of their own share. It becomes a public signal: a creator
offering 40% to holders is making a credible, on-chain commitment that a creator offering 0% is not.

This is market-driven rather than protocol-mandated, which is the right instinct — it does not require us to guess
the correct number, and it lets buyers price the difference.

### The failure mode that must be solved first

**Paid pro-rata to balance, the creator pays it to themselves.** A creator who holds most of the supply and sets a
100% holder share routes their own fee back to their own wallet while advertising maximum generosity. Worse, they
can wash-trade against themselves: each self-trade pays a fee that returns to them as the dominant holder, net of
only the protocol's 40%. The slider then becomes a *deception* surface rather than a signal — strictly worse than
not offering it.

Any design must therefore make the holder share unprofitable to capture by the creator. Three defences, which
should be combined:

1. **Exclude the creator's own balance** from the pro-rata calculation. Necessary but not sufficient: defeated by
   splitting supply across wallets.
2. **Weight by holding duration, not instantaneous balance.** A share earned per token-second held cannot be
   captured by a wallet that buys immediately before a trade and sells after. This also delivers Sparsity's
   "pay for holding, not volume" directly.
3. **Make the setting immutable, or adjustable only upward.** Otherwise a creator advertises 50% at launch and
   silently drops it to 0% once buyers arrive.

### The implementation question: how to pay holders at all

We do not control SPL token accounts, so there is no cheap way to know every holder's balance at the moment of a
trade. Three options, in increasing order of what they cost us:

| option | mechanism | cost |
|---|---|---|
| **Pay the room, not the holders** (recommended) | The holder share is added to the **room reserve** — the shared floor every holder's position is priced against. No per-holder accounting at all. | Nearly free. One extra deposit per trade. |
| Accumulator index | A fee-per-token-held index on the room, with a per-holder checkpoint updated when they claim. | One u128 on the room, one account per claiming holder, plus a claim instruction. |
| Token-2022 transfer hook | A hook updates holder checkpoints on every transfer. | CU on every transfer, and **many DEXes refuse tokens with transfer hooks**, which would break graduation. Not recommended. |

**Recommendation: pay the room.** Adding the holder share to the room reserve raises the floor for everyone
holding, in proportion to what they hold, with no bookkeeping, no claim transaction, and nothing to sybil — a
creator splitting across a hundred wallets gains nothing, because the payment is not divided per wallet. It is
also exactly Sparsity's "compounding liquidity so the pool grows with volume", applied to the fee stream.

It is a weaker promise than cash to holders, and the write-up should say so plainly rather than describing it as a
dividend. What a holder receives is a higher floor, not a payment.

### Also worth adopting: vesting the creator's own share

Independently of the slider, the creator's retained share could vest against how long their door survives, which
is Sparsity's second prescription and the direct answer to launch farming. Unvested fees would return to the room
reserve. This needs its own design: what "survives" means, and what happens on graduation.

---

## 4. Proposal B: protocol revenue into narratives, not buyback-and-burn

**The owner's proposal.** Rather than buying back and burning a protocol token (the incumbent's model, which
Sparsity notes made the platform's own token the cycle's biggest winner while active wallets fell from over 5
million to about 1.8 million), direct protocol revenue back into narratives that are working.

This is strong counter-positioning and it is consistent with everything above: it points money at coins that last
rather than at the first hour.

### The failure mode that must be solved first

**If we choose which coins to buy, we become a market participant trading ahead of our own flow.** We would hold
non-public knowledge of our own future purchases in specific tokens. That is insider dealing in substance whatever
the intent, it invites accusations of picking winners, and it exposes the company to market-manipulation claims in
most jurisdictions. Discretionary selection must be ruled out.

Two constraints make the idea safe:

1. **Rules-based, not discretionary.** Eligibility and amount follow published, objective, on-chain criteria
   (room age, distinct holders, volume consistency, survival past a threshold) computed by the program, with no
   human choosing a recipient. Publish the rule before it runs and change it only through the existing
   seven-day timelock (finding M-6).
2. **Add to the reserve; do not buy the token.** Depositing into a room's reserve deepens its floor without the
   protocol taking a position it could later sell. We never hold the asset, so there is nothing to dump, no
   trading intent to allege, and no inside position. Buying tokens on the open market would create all three.

With both constraints, the mechanism reads as a protocol-level liquidity programme rather than a trading desk.
**Legal review is required before this is built**, in the jurisdiction where the company operates.

### Open questions

- What fraction of protocol revenue, and is it capped per room?
- Does a room that later dies return the injected reserve, and to whom?
- Does injection interact with the graduation trigger? Adding reserve moves a room toward graduation, so an
  injection could force graduation — the rule must either exclude injected reserve from the trigger or stop
  short of it.
- How does this interact with the liveness rule, given that squatting already costs only about 0.02 SOL per room
  per day (`SECURITY_REVIEW.md`)? A reward for "surviving" rooms is a reward a squatter can farm. **This is the
  sharpest objection to Proposal B and must be answered before it is built.**

---

## 4a. Liquidity depth decays as a coin grows — and fee routing fixes it

Claim, [@the_smart_ape, 15 Nov 2026](https://x.com/the_smart_ape/status/2121921459614531607): a pump.fun pool
receives about 68 SOL at bonding and never grows, so the larger the coin gets the easier it is to crash.

**Verified independently.** For a constant-product pool holding fraction `f` of supply, selling fraction `s`
gives `p'/p = (f/(f+s))²`. Price goes as the square of the SOL in the pool, so `f` decays as `1/sqrt(mcap)`.
Reproducing their four figures exactly:

| mcap | pool holds | sell to halve the price |
|---|---:|---:|
| $1m | 3.20% | **1.33%** (their 1.3%) |
| $10m | 1.01% | **0.42%** (their 0.42%) |
| $100m | 0.32% | **0.13%** (their 0.13%) |
| $1b | 0.10% | **0.042%** (their 0.04%) |

At $1b, someone selling 0.04% of supply halves the coin. The maths is right and the cause is structural: fixed
liquidity, growing market cap.

**Our bonding curve is far more robust**, because the virtual reserve buys price-impact resistance with no real
capital:

| room reserve | effective pool as % of supply | sell to halve |
|---:|---:|---:|
| 0 SOL | 107.3% | 44.5% |
| 10 SOL | 80.5% | 33.3% |
| 50 SOL | 40.2% | 16.7% |
| 85 SOL (graduation) | 28.0% | **11.6%** |

**But that advantage ends at graduation, and this is the decision still open.** Our room graduates at 85 SOL
(~$7,600); pump.fun bonds at ~68 SOL (~$6,100). If we hand a pool a fixed amount and walk away, **we inherit
exactly the same 1/sqrt(mcap) decay.** Nothing about paired doors prevents it.

**Routing a share of the trade fee into the pool fixes it, and the fix is scale-invariant.** Because both the
pool and the market cap then grow with cumulative volume, `f` stops depending on size. Assuming lifetime volume
of 10× market cap:

| share of the 1% fee routed to the pool | pool at $100m mcap | pool at $1b mcap | f | sell to halve |
|---:|---:|---:|---:|---:|
| 0% (pump.fun's model) | $0.01m | $0.01m | ~0% | ~0.0% |
| **20%** | $2.0m | $20.0m | **2.0%** | **0.83%** |
| 40% | $4.0m | $40.0m | 4.0% | 1.66% |
| 100% | $10.0m | $100.0m | 10.0% | 4.15% |

Routing just **20% of the fee** makes a $1b coin roughly **20× harder to crash** than a pump.fun coin, and the
figure no longer degrades with size. This is precisely Sparsity's "compounding liquidity so the pool grows with
volume" (§1), achieved through fee routing rather than new mechanism.

**Consequences for decisions already on the table:**
- It raises the stakes on the **post-graduation fee**: that fee is the only thing that can fund compounding depth.
  Charging nothing after graduation forfeits the mechanism entirely.
- It is the same lever as **Proposal A** (§3): paying the room rather than individual holders. That proposal was
  justified on sybil-resistance grounds; this shows it also solves a structural liquidity defect.
- The accreted liquidity must be **permanently locked**, or it is not depth — it is a protocol position that
  could be withdrawn. Meteora DAMM v2's permanently-locked-position-that-still-earns-fees is a natural vehicle,
  which strengthens the case for DAMM v2 over DLMM at graduation.

**Caveats.** The 10× lifetime-volume assumption is illustrative, not measured; the conclusion is scale-invariance,
which holds at any multiple. Fee routed to the pool is fee not paid to the creator or protocol, so this is a real
cost, not free. And fee accretion is slow in practice: the cited post notes `$mihao` reached only 1.4% of supply
after weeks of heavy trading, so depth builds over a coin's life rather than at graduation.

## 4b. If the founder share is ever raised above 0, squatting needs prediction — measured

`founder_share_bps` is 0 in both the devnet and mainnet config. Raising it is an obvious-looking way to reward
whoever starts a narrative, and it is the one fee knob here that pays a party for *being first* rather than for
holding or trading. `SECURITY_REVIEW.md` already bounds the resulting attack: the founder position goes to
whichever launcher wins the race, it pays a share of every later trade in the room including every door, and
squatting costs about 0.0288 SOL of rent plus keeping the room live. What that note does not say is whether a
squatter would have to **predict** which narratives take off, or could register broadly and wait.

Measured on 65,630 real pump.fun launches over 57.6 hours
(`services/matcher/scripts/shadow_replay.py`, matcher `CORRECTIONS.md` §30):

- The **first door arrives within five minutes in 56.9% of rooms** (median 2.3 minutes). There is no window in
  which to notice a narrative starting and race to register its key. A squatter must hold the key in advance.
- **65.9% of rooms never receive a single door.** Breadth bought blindly is mostly spent on rooms that stay empty.
- The largest rooms in the sample are trend-specific names nobody could have pre-registered: Dacity (1,128
  launches), AudaCity (628), Apocry, Lucia, Mandy, dog wif cap.

So the attack needs prediction, and prediction is hard on this traffic. **The residual is the evergreen keys** —
DOG, CAT, AI, INU, GTA, PEPE recur across cycles and are cheap to hold indefinitely.

**What this implies for the decision.** If the founder share is raised, cap or taper it rather than adding a
reservation mechanism: the reservation was removed for good reasons (matcher `CORRECTIONS.md` §16) and rooms fill
faster than any reservation window would help. A taper that pays the founder only while the room is young, or
only up to a ceiling, keeps the intended reward for starting a narrative without making a pre-registered evergreen
key a perpetual annuity.

**Limit.** 57.6 hours is one market episode, dominated by the GTA VI and Dacity/Audacity waves. Fill times in a
quiet week could be far slower, which would make breadth more viable. Re-measure before acting.

## 5. See also

- `research/doors_into_one_room/POSITIONING.md` — the room as narrative exposure, and the experiment that tests it.
- `research/doors_into_one_room/MAKER_ROLE.md` — a maker role for the room; Design B ruled out by the graduation arithmetic.

## 6. What to do, in order

Tracked as finding I-10 in `SECURITY_REVIEW.md`.

1. **Nothing before devnet.** The deployment and the service end-to-end test come first.
2. **Graduation design** (Meteora DAMM v2) next. Both proposals touch what happens after a room completes, so
   designing them before graduation would be designing in the dark.
3. **Then, in this order:** vesting the creator's share (smallest change, directly targets launch farming);
   Proposal A paying the room; Proposal B rules-based reserve injection, after legal review and after the
   squatter-farming objection is answered.
4. **Measure each against the replay before adopting it**, the way every matcher rule has been measured. The
   simulations in `PAIRED_DOORS_REPORT.md` are the right harness: a fee change that improves holder outcomes on
   paper but reduces the late buyer's return is not an improvement.
