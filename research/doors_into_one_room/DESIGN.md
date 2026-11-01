# Doors into one room — Solana design

> **Superseded in part — the build spec is [PERMANENT_CURVE_SPEC.md](PERMANENT_CURVE_SPEC.md).**
> Where this document and the spec disagree, the spec wins. Sections now
> contradicted:
>
> - **§0 and §1, the curve and graduation.** The spec uses a pump.fun-shape
>   constant-product curve with V_tok = 1,073,025,606 and a derived V_sol. It
>   graduates at 85 SOL of reserve into a **Meteora DAMM v2** pool with a
>   permanently locked position whose NFT is held by the protocol. This
>   document's internal "phase 1 pool" and its "no external migration"
>   recommendation in §7 are replaced.
> - **§0 and §2, doors.** Doors are still pre-minted (1B each, no mint
>   authority), but each is **backed 1:1 by room tokens** held in its own
>   room-token vault. There is a new per-room **room token**, 1B pre-minted,
>   tradeable through the program at the same fee as a door. `convert` moves
>   the backing between door vaults.
> - **§3, flows.** The buy and sell account lists and steps are replaced by
>   spec §3. Post-graduation trades route through the DAMM v2 pool.
> - **§4 and §5, fees.** The split is now **60% to the door, 40% to the
>   protocol, with founder share defaulted to 0 bps**. On the room token the 60% goes to the
>   reserve via retirement. Launching is free: the door and room fees default
>   to 0, and graduation rent comes out of the reserve. The 30% creator share
>   is gone.
> - **§5, `close_door` is removed.** Doors are never closed. Ticker locks are
>   removed: doors may share names, symbols and images.
> - **§6, room identity.** SlugLock is keyed by the derived door-0 identity.
>   Release and takeover use exactly the narrative routing liveness gate,
>   including after graduation (spec `release_slug`). The room token takes
>   door 0's name, symbol and image permanently.
> - **§8–9, display.** Every door and the room token show the room FDV, because
>   every mint has 1B supply (spec §7).


31 October 2026. Design only; no code. Target: a single Solana program,
written in Anchor or native Rust (a later choice).

Numbers marked *(sim)* come from this repository's shared-narrative study
([../shared_narrative/FINDINGS.md](../shared_narrative/FINDINGS.md)). That study
used synthetic agents, so those numbers show mechanism directions, not market
forecasts. Its Arm B *is* this design: one curve, many doors, fees attributed
per door.

## 0. Summary of decisions

| Question | Decision |
| --- | --- |
| Room curve | Constant product with virtual reserves (pump.fun shape). It opens with zero backing. |
| Doors | **One Token-2022 mint per door.** Each mint has a fixed 1B supply minted once into a room-owned vault, and its mint authority is then revoked. The room's curve tracks one shared "outstanding" number. |
| Interchangeability | Every door's price is computed from room state only. A door's tokens enter or leave circulation only through the program's buy/sell/convert. `convert` swaps door A for door B 1:1. |
| Fee attribution | Attribution follows the **mint**: a buy that delivers door-N tokens, or a sell that returns door-N tokens, credits door N. Conversions credit nobody. |
| Graduation | **No external DEX migration.** At the threshold the room switches phase *inside the program* to a real-reserve constant-product pool with permanently locked liquidity. Doors keep working and new doors can still open. |
| Room identity | A room has a short slug registered on-chain (unique while the room is alive) and a description URI. It is discovered through a ranked feed. |
| Opening doors | Permissionless. The opener pays rent plus a door fee; part of the fee is added to the room reserve. There is no hard cap. Tickers are unique within a room. |

## 1. The room

### Curve

A constant product with virtual reserves, run in two phases. All math uses u128
integers. Lamports are the quote unit and the room token uses 6 decimals.
Every rounding favours the pool.

**Phase 0, the virtual curve:**

- State: `x = V_sol + real_sol` and `y = V_tok − sold`, with `k0 = V_sol·V_tok`.
- Price is `x/y`. Defaults are `V_sol = 30 SOL`, `V_tok = 1,073,000,000` and
  `supply = 1,000,000,000`. The room opens at about 28 SOL FDV and needs no
  backing.
- **Buy with net lamports n:** `tokens_out = y − ceil(k0/(x+n))`.
- **Sell t tokens:** `lamports_out = x − ceil(k0/(y+t))`.

**Phase 1, the room pool:** this starts once `sold` reaches 793,100,000, which
takes about 85 SOL of real reserve.

- State: `x = real_sol` and `y = supply − sold`, with `k1 = x·y` fixed at the
  switch.
- The curves are continuous: price at the switch is about 4.109e-7 SOL per token
  on both sides, using the pump.fun parameters.
- Same swap formulas, using k1. Price can now rise without bound as `y → 0`.
- There are no LP tokens. Liquidity belongs to the room forever, which is the
  equivalent of pump.fun's burned LP.

A buy that crosses the switch is split into two segments inside one
instruction, as `research/shared_narrative/curves.py` does.

### Why this shape

- It opens with no backing.
- Every holder's exit value is path-independent, because fees are charged
  outside the reserve.
- It is the shape terminals and users already understand.

Be clear about what this shape does: paper market cap is **quadratic** in the
reserve, while recoverable value is linear (E1/E2 in the study). Fifty doors
feeding one room produce a much larger chart for the same money. That makes
the room good marketing. It does not create any extra exit liquidity.

The premise "$50k with $200 of liquidity" is wrong for this curve shape. A
pump-shaped meme at $50k holds about $11k (about 74 SOL) of real reserve, and
moving its price 10% costs about $760. Thin, but not $200.

### Accounts

**`Config`**, PDA `["config"]`, one per program:
`admin`, `protocol_fee_recipient`, `fee_bps` (default 100),
`creator_share_bps` (default 3000 of the fee),
`door_fee_lamports`, `room_fee_lamports`, `door_fee_reserve_share_bps`,
the default curve parameters, and `paused`.

**`Room`**, PDA `["room", room_id_le_u64]`, about 200 bytes:

| field | meaning |
| --- | --- |
| `room_id: u64`, `bump` | identity |
| `phase: u8` | 0 = curve, 1 = pool |
| `v_sol, v_tok: u64` | virtual reserves (phase 0) |
| `real_sol: u64` | lamports backing the curve, excluding fees and rent |
| `sold: u64` | outstanding room tokens = Σ over doors of (1B − vault balance) |
| `k: u128` | k0 or k1 |
| `door_count: u32` | doors ever opened (indexes door PDAs) |
| `protocol_accrued: u64` | unswept protocol fees |
| `slug: [u8; 32]`, `uri: String(≤128)` | identity (§6) |
| `creator: Pubkey`, `created_at: i64` | who opened the room / first door |
| `last_trade_at: i64`, `peak_real_sol: u64` | used to expire the slug (§6) |

**`RoomVault`**, PDA `["vault", room]`: an account *owned by the program* with
zero data, holding `real_sol` plus rent. Program ownership lets sells debit
lamports directly, with no system-program CPI.

**`FeeVault`**, PDA `["fees", room]`: also program-owned and holding lamports.
Its invariant is that its lamports cover
`Σ door.accrued + room.protocol_accrued + rent`. Fees never mix with the
reserve.

## 2. The doors

### Separate mints vs one mint with labels

| | One mint per room, doors as labels | **One mint per door (chosen)** |
| --- | --- | --- |
| Wallet display | One line with the room name. Door identity is invisible: your $DOGHAT is just "ROOM-17". | Each door shows its own name, ticker and image from Token-2022 metadata. |
| DexScreener / terminals | One token, which is easy to integrate. The door is a field in trade logs that only a custom UI shows. | N tokens, each needing a price. Every door's chart is the same room chart. They need the program integrated as a venue (§8). |
| Fee attribution | By an instruction argument. Anyone trading the mint elsewhere (an OTC pool, a transfer-and-sell) bypasses it. Frontends simply set `door = mine`. | By the mint the user buys or returns. Jupiter-style routing to a door's mint attributes correctly *because the user asked for that mint*. |
| Graduation | Trivial, since it is one token. | Needs a canonical token for any external venue. This design avoids external venues (§7). |
| "Being a meme" | Lost: the door has no asset of its own. | Kept. The door is a token people hold and post. |

**Separate mints are the only version where a door is a meme.** Labels reduce
doors to referral codes. The cost is integration work and the
interchangeability machinery below.

### How separate mints stay interchangeable at one price

Each door is fully pre-minted and the mint authority is revoked, so supply is
fixed from the start:

- **`open_door`** creates a Token-2022 mint with the MetadataPointer and
  TokenMetadata extensions and no freeze authority. It mints **1,000,000,000**
  door tokens into `DoorVault` (the room PDA's associated token account for
  that mint), then **sets the mint authority to None**.
- **A buy through door N** moves tokens *out of* `DoorVault[N]` to the user.
  **A sell** moves them back in. Each changes `room.sold` by the amount moved.
- **`convert(A→B, t)`**: the user sends t A-tokens to `DoorVault[A]` and
  receives t B-tokens from `DoorVault[B]`. `room.sold` is unchanged and the
  price does not move.
- **The vaults can never run dry.** Any door's outstanding amount is at most
  `room.sold`, which is at most 1B, and each vault starts with 1B.
- **Price is identical at every door** by construction. The swap math reads
  only `Room`; the door supplies no state to it.

Why pre-mint instead of mint-on-demand:

1. Revoked mint authority and fixed supply are what wallets, Blowfish-style
   scanners and terminals check first. A live mint authority held by a program
   PDA reads as "can mint, rug risk" everywhere.
2. Terminals compute mcap as price × supply. With pre-minting **every door
   shows the room's FDV**, which is the honest number for the price, rather
   than a tiny per-door supply.

The cost: naive aggregators that sum mcaps across a room's doors will report
N× the room. Explorers will also show the vault balance as "supply" unless the
vault is labelled.

**External pools for a door mint.** Anyone can create a Meteora or Raydium
pool for door N against SOL. Its price will drift from the room's, and
arbitrageurs close the gap by buying from or selling into the room through
door N. That is fine. It cannot break the room, and it generates door-N fees.

### Accounts per door

**`Door`**, PDA `["door", room, door_index_le_u32]`, about 180 bytes:
`room`, `index`, `mint`, `vault`, `creator`, `fee_recipient` (transferable, so
it can point to a Squads multisig or a splitter for teams), `accrued: u64`,
`claimed: u64`, `buy_volume: u128`, `sell_volume: u128`, `trades: u64`,
`created_at`, `bump`.

**`DoorMint`**, PDA `["door_mint", room, index]`: Token-2022 with metadata
(name ≤ 32, symbol ≤ 10, uri ≤ 200) and the MintCloseAuthority unset.

**`DoorVault`**: the room PDA's associated token account for that mint.

**`TickerLock`**, PDA `["ticker", room, normalized_symbol]`: empty. Its
existence enforces unique tickers within a room. Normalisation is uppercase,
strip non-alphanumerics and map confusables (0→O, 1→I).

Rent per door is roughly 0.004–0.006 SOL for the mint plus metadata, about
0.0021 SOL for the vault, about 0.0021 SOL for `Door` and about 0.001 SOL for
`TickerLock`. That is **~0.01 SOL**, paid by the opener. Measure before
fixing the fee.

## 3. Buying and selling through door N

### `buy(sol_in: u64, min_tokens_out: u64)`

The transaction is
`[ComputeBudget, ATA::create_idempotent(user, door_mint_N, token_2022), program::buy]`.

| # | account | flags |
| --- | --- | --- |
| 0 | user | signer, writable |
| 1 | config | |
| 2 | room | writable |
| 3 | room_vault | writable |
| 4 | fee_vault | writable |
| 5 | door_N | writable |
| 6 | door_mint_N | |
| 7 | door_vault_N | writable |
| 8 | user_ata_N | writable |
| 9 | token_2022_program, system_program | |
| 10 | event_authority, program (for `emit_cpi`) | |

Steps:

1. Check `door_N.room == room`, `door_vault_N == door_N.vault` and
   `!config.paused`.
2. `fee = ceil(sol_in·fee_bps/10⁴)` and `net = sol_in − fee`.
3. Compute `tokens_out` from the room curve, splitting the crossing at the
   phase switch.
4. Require `tokens_out ≥ min_tokens_out`.
5. Make two system transfers from the user: `net` to `room_vault` and `fee` to
   `fee_vault`. The user signs, so this is a plain CPI.
6. `transfer_checked` tokens_out from `door_vault_N` to `user_ata_N`, signed by
   the room PDA.
7. Update state:
   - `room.real_sol += net` and `room.sold += tokens_out`, plus `x`/`y`, and
     the phase if it switched;
   - `door_N.accrued += fee·creator_share`;
   - `room.protocol_accrued += fee − creator part`;
   - `door_N.buy_volume += net` and `door_N.trades += 1`;
   - `room.last_trade_at`.
8. Emit `Trade{room, door, user, side, sol, tokens, fee, price_after, sold_after, phase}`.

There is also a `buy_exact_out(tokens, max_sol_in)` variant.

**The user ends up with** door-N tokens in their Token-2022 associated token
account. They hold "$DOGHAT", priced at the room.

### `sell(tokens_in: u64, min_sol_out: u64)`

Same accounts.

1. `transfer_checked` tokens_in from `user_ata_N` to `door_vault_N`, with the
   user as authority.
2. Compute `gross` from the room curve.
3. `fee = ceil(gross·fee_bps/10⁴)` and `net = gross − fee`.
4. Require `net ≥ min_sol_out`.
5. Debit `room_vault` by gross and credit the user `net` and `fee_vault` `fee`.
   The program can do this directly because both vaults are program-owned.
6. Update state: `room.real_sol −= gross`, `room.sold −= tokens_in`, door
   accrual and `sell_volume`, then emit the event.

Phase 1 never reverts to phase 0, even if the room drains. The room can drain
toward the locked floor and refill. That is the casino working as intended.

**The user ends up with** SOL. If they held door A and want to "sell through
door B", they convert first. Attribution still goes to the mint they return.

### `convert(from: A, to: B, amount)`

Accounts: user, room, door_A, door_B, both mints, both vaults, both user ATAs
and the token program. It makes two `transfer_checked` calls.

There is no curve change and no creator fee, only a flat protocol fee (e.g.
0.0005 SOL) to stop spam. Without convert, holders of a dead door would have
no way to move to the door they now prefer. With convert, door identity
becomes a matter of choice.

### Throughput

Every trade on every door write-locks the same `Room` account. A hot room
therefore concentrates fifty memes' order flow on one writable account. Solana
caps the compute any single writable account can consume per block. Check the
current limit; it is on the order of 10M CU.

A buy with Token-2022 transfer and ATA creation should cost tens of thousands
of CU. Measure it. That allows a few hundred trades per room per block. It is
enough, but priority fees and sandwiching concentrate on hot rooms. Always set
min-out limits; the frontend default should be ≤ 2–3% slippage.

## 4. Fee accounting

**Where fees go.** Every trade's fee goes to `FeeVault[room]`. The split is
recorded in counters, not in separate accounts:

- `door.accrued` holds the creator share;
- `room.protocol_accrued` holds the rest.

There is one vault per room. That avoids one more writable account per trade,
and per-door vaults would add rent across 50,000 doors.

**Instructions:**

- **`claim_door_fees(door)`**: the signer must be `door.fee_recipient`. It
  sends `door.accrued` lamports from `fee_vault` to the recipient (the program
  debits directly), sets `claimed += accrued` and `accrued = 0`, and emits
  `FeesClaimed`. The recipient can be a Squads vault or a splitter program,
  which covers teams.
- **`set_fee_recipient(door, new)`**: signed by the current recipient.
- **`sweep_protocol_fees(room)`**: permissionless. It sends
  `room.protocol_accrued` to `config.protocol_fee_recipient`. Making it
  permissionless means it cannot be withheld.

**Volume tracking.** `door.buy_volume` and `door.sell_volume` (net lamports),
`door.trades` and the events. Indexers reconstruct everything from events;
the counters are the on-chain source of truth for fees.

**Fee split.** Keep the creator share at **≤ ~30–50% of the fee**. *(sim)*
At a 30% share, wash trading through your own door lost money under every
policy found. It started paying at about 50% for some doors and reliably from
70%, because wash volume buys trending attention. Frontends should rank doors
by unique buyers and net inflow, not raw volume. Raw-volume ranking is what
makes wash trading pay.

**Attribution is the hardest problem in this design (see §9).** All doors are
the same asset at the same price, so whoever controls order flow can route it
through a door they own. That includes trading bots, terminals and sniper
tools. Attribution-by-mint limits this, because the user then holds the
router's door token rather than the meme they wanted. It does not stop it.

## 5. Opening a door

**`create_room(slug, uri, curve_preset, first_door{name, symbol, uri}, dev_buy_lamports)`.**
Anyone can call it. It pays `room_fee_lamports` plus rent and creates, in one
transaction: `Room`, `RoomVault`, `FeeVault`, the `SlugLock`, door 0 (mint,
vault, `Door`, `TickerLock`), and an optional atomic first buy. Making the
first buy atomic means nobody can buy in between.

**`open_door(room, name, symbol, uri, dev_buy_lamports)`.**

- Permissionless and allowed in either phase. It pays:
  - rent, about 0.01 SOL;
  - `door_fee_lamports`, of which `door_fee_reserve_share_bps` goes **into
    the room reserve**. In phase 1 that means `x += fee` and `k` is
    recomputed. In phase 0, add it as a buffer that raises `v_sol` by the same
    amount.
- The rest goes to the protocol.
- It optionally includes an atomic first buy through the new door.
- It fails if a `TickerLock` for the normalised symbol already exists.

**Why part of the fee goes into the reserve.** It makes a new door *strictly
good for existing holders* even if it brings no new buyer. *(sim)* Without
it, a door that brings no new demand is pure fee diversion. It has zero effect
on price, and honest doors lose fees almost one for one. Spam then subsidises
holders instead of only taxing creators.

**What the door fee should be.** *(sim)* The break-even launch cost for door
spam was about $450–460 per door for a single spam door, and $120–130 per door
when spamming 30. That rests on the assumption that 30% of buyers pick doors
at random or by confusion. Real attention data should set the number, and
curation shrinks it. Start around **0.5–1 SOL** and tune it from observed
door-level fee income. A fee that low will not stop well-capitalised
spammers. It stops the zero-cost "open a door in every hot room" script.

**Cap per room.** Don't set a hard cap: it creates a land-grab and a resale
market for door slots. Instead:

- Optionally raise the fee with the number of live doors, e.g.
  `door_fee × (1 + live_doors/100)`.
- Let `close_door` reclaim rent once a door's outstanding is zero (vault
  balance = 1B) and it has been idle for N days. Token-2022 mints can only be
  closed with a close authority at zero supply, but this supply is never zero,
  so close only the `Door`, `TickerLock` and vault records and leave the mint
  inert. If full mint reclamation matters, consider mint-on-demand instead and
  accept its §2 costs.

**Who opens the first door?** Whoever creates the room. They get the only
fresh-curve floor in the room. See §9 for why that becomes a problem.

## 6. The room's identity

The room token carries door 0's fixed name, symbol and image. `SlugLock`
is keyed by the hash of the program-folded name and symbol, derived rather
than launcher-chosen. A lock is released or taken over exactly when its room
fails the routing liveness gate, including after graduation. See
[NARRATIVE_DETECTION.md §4](NARRATIVE_DETECTION.md#4-liveness-gate-hard-rule)
and `release_slug` in the build spec. The old room keeps trading by id.

**How a launch is routed.** The protocol matcher chooses the target from
the candidate metadata and co-signs the decision. The frontend previews that
exact room, its activity, holder concentration and rent. The launcher can
confirm the preview or back out. They cannot select a room or override the
routing decision. See the narrative detector and build-spec launch checks.

## 7. Graduation

### What the user described cannot work as stated

If the room's liquidity moves into a Raydium pool the program doesn't own, the
program no longer prices trades. From then on:

- buys and sells happen in Raydium against one canonical mint;
- doors cannot mint against it;
- Jupiter routes around any door fee;
- "new doors after graduation" can only be **wrappers**, i.e. lock ROOM and
  issue door-N 1:1 (detail below).

Door attribution then covers only flow that deliberately uses the program, and
aggregators will avoid that flow because the door fee is an extra cost.

### Recommendation: graduate inside the program

When `sold` reaches the threshold, the room switches to phase 1, its own
constant-product pool (§1), in the same instruction:

- Nothing migrates and no door collapses.
- New doors keep opening on the same instruction, and fees stay attributable.
- Liquidity is locked by construction; there is no LP token to pull. This is
  what PumpSwap is to pump.fun: the venue is the launchpad's own AMM.
- Optionally lower `fee_bps` in phase 1 to stay competitive with external AMMs.

What you give up is a "real DEX" listing as a graduation signal. That signal
has to come from integrations instead (§8): DexScreener, Birdeye, GMGN, Axiom
and Photon indexing the program, and **Jupiter routing to door mints** through
an AMM-interface adapter. Jupiter routing is the important one. Each door is a
mint, so Jupiter can quote SOL→door-N, and attribution comes out right on its
own.

### If an external pool is non-negotiable

1. Create a canonical **ROOM** mint, also pre-minted with revoked authority.
2. At the threshold, seed an external pool (for example Raydium CPMM or
   Meteora) with `real_sol` and the remaining ROOM tokens, and burn the LP.
3. Door tokens become **1:1 wrappers**: `unwrap(door N)` returns ROOM from a
   wrapper vault, and `wrap(ROOM → door N)` locks ROOM.
4. Post-graduation buys through door N:
   - the program CPIs the swap SOL→ROOM into the external pool, then wraps to
     door N and charges a door fee on top;
   - sells reverse that path;
   - new doors are new wrappers.
5. The consequences:
   - most volume trades ROOM directly with no attribution;
   - door creators earn only on flow from their own community that uses the
     door UI;
   - every door's terminal page needs a pointer to the ROOM pool.

It works, but the core value — creators paid on room volume — mostly ends at
graduation.

## 8. What a trader sees

**Wallet.**

- Each door token is its own line with its own name, ticker and image.
- The price comes from Jupiter or Birdeye, so both need to index the program
  (see Distribution below). Until then, wallets show no USD value.
- Holding two doors of one room shows as two lines. Wallets will not combine
  them.

**Chart.**

- Every door's chart *is* the room chart, built from `Trade` events across all
  doors. Its price series is identical for all doors.
- The door page overlays that door's own volume, buyers and fees.
- DexScreener-style sites need a custom adapter. Otherwise each door mint
  appears as a separate "pair" with the same price and split volume.
  Recommended: one room page, door tabs, room volume as the headline and door
  volume beneath it.

**Position.**

- The frontend groups the wallet's token accounts by room. That needs a
  mint → `Door` → `Room` lookup, served from an indexer or from
  `getProgramAccounts` filtered on `mint`.
- It shows the room position (the total of all doors at the room price) and
  the per-door breakdown.

**P&L.**

- Cost basis comes from `Trade` events: lamports in, including fees.
- `convert` carries basis across doors.
- Always show the **exact exit quote**, "sell all now: X SOL", computed from
  the curve, not just balance × price. *(sim)* In a shared room the paper mark
  overstated realisable value 9–15× at the peak. That figure is room-wide, not
  per wallet, but large holders see it most.
- Show room-level warnings. Bystanders in a shared room take other doors'
  dumps: *(sim)* when another meme's holders panicked, bystanders lost about
  20 points in the shared room vs 0 in independent markets.

**Market cap shown.** Show the room FDV (price × 1B) as the main figure, plus
"this door's share of the room's outstanding supply".

**Distribution.** None of the above shows up in third-party tools until they
integrate the program. That is a business-development dependency, not an
engineering one, and it is probably the critical path.

## 9. Hardest parts, and what won't work as described

1. **Fee attribution follows order flow, not attention.** The doors are
   identical assets at an identical price. Any terminal, Telegram bot or
   sniper suite can open a door in every room and default its users' buys
   through it. Users lose nothing by it, so they won't object.
   - Attribution-by-mint makes this visible: the user ends up holding
     "$AXIOMDOOR" rather than "$DOGHAT". That helps where memes carry
     identity.
   - It is not a mechanism you can fully defend. Expect a large share of fees
     to go to order-flow owners, not meme creators.
   - Nothing on-chain can tell "the creator made this demand" apart from "the
     router routed it".
2. **Vamping is only good if the vamp brings new buyers.** A copy door that
   just relabels existing buyers moves the price by exactly zero *(sim:
   spam in the shared curve changed organic P&L by $0.00)*. It takes fees from
   the original door one for one. For holders, a vamp is good if it brings
   incremental demand. For the original creator's fees, it is bad unless it
   expands the pie.
   - The door-fee-to-reserve rule (§5) is what makes every new door at least
     mildly good for holders.
   - Lookalike doors (`D0GHAT`, the same image) can't be stopped on-chain
     beyond ticker normalisation.
3. **Fragmentation moves up a level, to rooms.** Creating a room gives you the
   only fresh floor. Joining an existing room means buying at its current
   price.
   - A creator maximising their first-buy profit therefore prefers to **open
     a new room**, for the same reason people launch new coins today.
   - *(sim)* At fragmented attention, creators earned more, more reliably, in
     independent markets than in a shared curve. Every risk measure favoured
     the independent markets, entirely because of that floor. Creator fee
     income was identical in both.
   - Expect fifty rooms per narrative unless something makes joining better
     than founding. Raising the room fee above the door fee helps.
     Slug uniqueness helps a little.
   - The real lever is distribution: frontends and KOLs pointing to one room.
     That is coordination outside the program.
4. **"Creators stop spraying" is likely backwards.** Opening a door is cheaper
   than launching a coin and inherits a live chart. Sprayers will spray doors
   into every hot room. The door fee and its reserve share are the only
   defence, and their right level depends on attention data nobody has yet.
5. **KOL incentives are smaller than they look.** At a 0.3% creator fee, $100k
   of follower volume through a KOL's door pays $300. KOLs currently earn from
   early allocations, and in a room they can't get the floor. Some will open
   doors; many will keep launching their own coins.
6. **Shared downside is the mirror image of "vamping is good".**
   - One door's creator dumping a first-buy bag, or one community panicking,
     hits every door's holders.
   - *(sim)* The shared room also drained faster. Everyone is in profit at
     the same moment and takes it, so the room held well under half the
     money that ten independent curves held.
   - That fits "the casino fills and drains", but it caps the runner. The
     study's shared curve never reached $1M paper in 1,800 runs, and a $5M
     chart required holders who never sold.
7. **External graduation is incompatible with doors** (§7). Keep the
   liquidity in the program, or accept that door economics end at graduation.
8. **Distribution.**
   - DexScreener, Birdeye, Jupiter, GMGN, Axiom, Photon and Phantom pricing
     all need to integrate the program, plus a grouped-by-room view.
   - Until they do, a door has no chart, no USD price and no route on the
     tools where memecoin trading happens.
   - This is the single biggest risk to launching, and none of it is solved
     on-chain.
9. **Display quirks of pre-minted doors.**
   - Every door shows the room's FDV; sum-across-doors aggregators will
     overcount.
   - Vault balances look like supply unless labelled.
   - Dead doors' mints can't be fully closed. Mint-on-demand avoids all of
     this, but trades it for a live mint authority, which scanners flag as a
     rug risk.
10. **Hot-account contention and MEV.** One room account carries every door's
    flow. Blocks containing a hot room fill with sandwiches and priority
    fees. That is the cost of a single shared book. Mitigate with enforced
    min-out limits and frontend slippage defaults, and consider rate limits
    in the first seconds after a room or door opens.

### Smallest version worth building first

Build phase 0 and phase 1 inside the program, Token-2022 pre-minted doors,
attribution by mint, `convert`, the door fee with its reserve share, expiring
slugs and a first-party frontend with grouped positions and exact exit quotes.
Skip external graduation.

Then measure three things on real rooms:

- what share of door fees go to order-flow owners vs meme creators;
- whether creators join rooms or found them;
- how much volume new doors bring that wasn't already in the room.

Those three numbers decide whether the idea works. None of them can be
settled by design.
