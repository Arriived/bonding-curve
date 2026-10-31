# Room and doors: pre-minted supply, constant-product curve, DAMM v2 graduation — build spec

31 October 2026, revised the same day for five owner rulings:

- launching is free;
- graduation rent comes out of the curve;
- there are no ticker locks;
- the room token inherits door 0's identity;
- SlugLock is kept.

The earlier mint-on-demand design, its linear-tail curve and PermissionedBurn
are dead.

**Settled and not reopened here:**

- router and terminal fee capture is accepted;
- doors work for the life of the room and are never closed;
- there is no founder share;
- the trade fee is 100 bps, split 60% to the door and 40% to the protocol;
- the room token's 60% goes to the reserve.

**Generated inputs.** Every number below comes from these scripts or on-chain
reads; none is from memory.

| file | produced by |
|---|---|
| `outputs/curve_identities.md` | `scripts/run_curve_identities.sh` (exact rational arithmetic) |
| `outputs/account_sizes.md` | `scripts/run_account_sizes.sh` |
| `outputs/fee_model.md` | `scripts/run_fee_model.sh` |
| `outputs/instruction_accounts.md` | `scripts/run_instruction_accounts.sh` |
| `outputs/onchain/damm_v2_program.json` | `scripts/onchain/run_damm_v2_checks.sh` (deployed program, live pool size) |
| `outputs/onchain/damm_v2_configs.json` | same script (DAMM v2 config census) |

**Primary sources:**

| source | commit or reading |
|---|---|
| solana-program/token-2022 | `986b3aa58cbcc40dea12b369912017a4066804e7` |
| solana-program/token-metadata | `685b8b66db23d4e4012a20553b8552af0812e3bc` |
| solana-program/associated-token-account | `5881eb14aaa794a85f78dc1fcd640cd89bd42cf3` |
| anza-xyz/agave | `aec3b701cfd1ab2c636675b0e30544c60068b08f` |
| MeteoraAg/damm-v2 (program `cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG`) | `5398b5c7c534de014091132da37c6478cce671a8` (2026-10-15) |
| DAMM v2 deployed program | programdata `AUh8bm2XsMfex3KjYGcM3G4uBqUNSDw6HEhWaWMYnyPH`, read at slot 463,751,285. Last deployed at slot 457,080,014; ELF sha256 `0712ca6d…a59b`. |

Meteora's documentation (`docs.meteora.ag`) did not resolve from this
environment. **No DAMM v2 statement here is taken from Meteora's docs.** All
come from program source at the commit above and on-chain reads. Whether the
deployed binary was built from that exact commit could not be verified; there
is no verified-build check here. The deployed binary does contain every
instruction this spec uses (§5).

## 0. Corrections

### 0.A Conflicts found in this revision's rulings

Rulings 1 (free launch), 3 (no ticker locks) and 4 (room token inherits
door 0) conflict with nothing verified. Two rulings needed an explicit
choice.

1. **Ruling 2 as literally written reintroduces a price step at the handoff:
   −0.013883%, twice pump.fun's −0.0068%.**
   - The trigger is raised to T = R* + graduation rent =
     85,024,680,160 lamports. At T the curve has sold 793,160,061.522864
     tokens, leaving 206,839,938.477136 in `RoomVault`.
   - Seeding the pool with exactly R* and all of those tokens prices it at
     `R*/(U − q_g)`. That is below the curve's closing price
     `K/(V_tok − q_g)²`.
   - The continuity identity behind V_tok = 1,073,025,606 holds only at the
     reserve level V_sol was derived for (R*), not at T.
   - **This spec keeps every stated requirement:** no step, a seed of exactly
     R*, T as a `Config` value, and rent from the reserve. It does so by
     seeding the pool with only the room tokens that match the closing price,
     `N = floor(R* · (V_tok − q_g)² / K)` = 206,811,223.802753 tokens, and
     retiring the remaining 28,714.674383 unsold tokens into `RetiredVault`.
   - The measured step is +2.755×10⁻¹³ %: the pool opens at or above the
     curve's closing price by less than one base unit. V_sol, V_tok and the
     curve are unchanged.
   - **Alternative, not adopted:** re-derive V_sol so that all remaining tokens
     can be seeded. That gives V_sol = 29,992,871,855 lamports, a seed of
     206,784,900.6 tokens and a step of +4.6×10⁻¹¹ %. It makes the curve depend
     on DAMM v2's rent, which can change.
   - All figures: `outputs/curve_identities.md`.
2. **Ruling 5 says "with the existing expiry rule", but the previous revision
   of this spec had no SlugLock expiry rule.** The rule lived only in
   DESIGN.md §6: release the slug when the room's real reserve is below 1 SOL
   and it has had no trade for 7 days. This revision adds it as
   `release_slug` (§3), with one adaptation:
   - it applies only before graduation (status 0 and 1);
   - after graduation the program cannot see direct DAMM v2 trades, so
     `last_trade_at` would misreport an actively traded room as idle.
   - The 1 SOL and 7-day thresholds are DESIGN.md's values, carried over
     unchanged as program constants.

### 0.B Corrections to the original brief (previous revision, still in force)

These were found while verifying the original brief. The spec follows the
brief everywhere else.

1. **The `V_sol` identity is inverted.** `V_sol = R*(2f−1)/(1−f)` gives
   240.826 SOL. The form that reproduces about 30 SOL is
   `V_sol = R*(1−f)/(2f−1)` = 30.000853 SOL.
2. **`V_sol = 30` and `R* = 85` cannot both hold exactly once `V_tok` is set
   for continuity.**
   - With V_sol = 30 SOL, V_tok = 1,073,025,606 and the 85 SOL reserve
     trigger, the switch happens at 793,105,882.696 tokens sold. Only
     206,894,117.304 tokens remain, not the 206,900,000 the pool seed
     requires. The price step is +0.0014836%.
   - **This spec keeps R* = 85 SOL, f = 0.7931, V_tok = 1,073,025,606 and the
     206.9M seed. It derives V_sol = 30,000,852,995 lamports**
     (30.000852995 SOL, +0.0028% from 30). Then the switch lands at s = fS
     and the step is +0.0000001068%, caused only by rounding V_tok up by
     0.4046 tokens.
   - If the owner prefers V_sol = exactly 30 SOL, that is a one-parameter
     change. The seed then becomes "all remaining room tokens", 206,894,117.3.
   - **Updated by 0.A.1:** the trigger is now T = R* + graduation rent. The
     pool seed is R* plus N = 206,811,223.802753 tokens, matched to the
     closing price, rather than 206.9M. V_sol and V_tok are unchanged.
3. **After graduation the room token is cheaper than any door, on the pool
   itself.**
   - Through the program, the room token and every door pay the same 100 bps,
     as required.
   - But once the DAMM v2 pool exists, anyone can trade the room token
     directly on it, paying only the pool fee.
   - A door trade after graduation pays the program fee *plus* the pool fee,
     because it routes through the pool.
   - So direct pool trades are cheaper than any door by exactly the program
     fee, 100 bps. Nothing in this architecture closes that gap (§5.6, §7).
4. **The protected graduation route needs Meteora's cooperation.**
   - A DAMM v2 *customizable* pool's address is seeded only by the two mints
     (`ix_initialize_customizable_pool.rs`, seeds
     `[CUSTOMIZABLE_POOL_PREFIX, max(mint), min(mint)]`). So it can exist at
     most once per room-token/WSOL pair, and any room-token holder can create
     it before graduation, which makes `graduate` fail.
   - The protected route is `initialize_pool_with_dynamic_config` with a
     config whose `pool_creator_authority` is this program's PDA. Only a
     Meteora operator can create such a config (`create_dynamic_config`
     requires the `CreateConfigKey` permission; `lib.rs` L95–97).
   - At slot 463,751,288 there were 74 dynamic configs on mainnet, all
     restricted to a named authority. Meteora issues these, but this program
     needs one issued to it.
   - The permanent-lock-with-fee-owner path itself does exist (§5).

---

## 1. Account layout

Rent is `(128 + data_bytes) × 6,960` lamports. Check: a classic 165-byte SPL
token account comes out at 2,039,280 lamports. Field offsets are in
`outputs/account_sizes.md`.

**Accounts created with each room:**

| account | owner / type | seeds | data bytes | rent (lamports) |
|---|---|---|---|---|
| `Config` | program | `["config"]` | 238 | 2,547,360 |
| `Room` | program | `["room", room_id u64 LE]` | 684 | 5,651,520 |
| `ReserveVault` | program, holds reserve lamports | `["reserve", room]` | 0 | 890,880 |
| `FeeVault` | program, holds SOL fees | `["fees", room]` | 0 | 890,880 |
| `GradPayer` | **System Program** (lamport-only PDA the program signs for; receives the graduation rent from the reserve at `graduate`) | `["grad_payer", room]` | 0 | 890,880 |
| `SlugLock` | program | `["slug", normalized_slug]` | 17 | 1,009,200 |
| `RoomMint` | Token-2022: MetadataPointer + TokenMetadata (name 32 / symbol 10 / uri 200) | `["room_mint", room]` | 616 | 5,178,240 |
| `RoomVault` | Token-2022 account, authority Room PDA; **1B room tokens pre-minted here** | `["room_vault", room]` | 165 | 2,039,280 |
| `RetiredVault` | Token-2022 account, authority Room PDA | `["retired", room]` | 165 | 2,039,280 |
| `FeeWsol` | SPL Token WSOL account, authority Room PDA | `["fee_wsol", room]` | 165 | 2,039,280 |

**Accounts created with each door:**

| account | owner / type | seeds | data bytes | rent (lamports) |
|---|---|---|---|---|
| `Door` | program | `["door", room, index u32 LE]` | 328 | 3,173,760 |
| `DoorMint` | Token-2022: MetadataPointer + TokenMetadata, max metadata | `["door_mint", room, index]` | 638 | 5,331,360 (minimum metadata 389 bytes: 3,598,320) |
| `DoorVault` | Token-2022 account for the door mint, authority Door PDA; **1B door tokens pre-minted here** | `["door_vault", door]` | 165 | 2,039,280 |
| `DoorRoomVault` | Token-2022 account for the room mint, authority Door PDA; **the backing** | `["door_room_vault", door]` | 165 | 2,039,280 |
| trader's ATA (door or room token) | Token-2022 + ImmutableOwner, paid by the trader | ATA program | 170 | 2,074,080 |

**Totals** (USD at an assumed SOL = $150, for quoting only):

| item | lamports | SOL | USD |
|---|---|---|---|
| per room, excluding door accounts | 20,629,440 | 0.020629 | $3.09 |
| per door, max metadata (Door + DoorMint + DoorVault + DoorRoomVault) | 12,583,680 | 0.012584 | $1.89 |
| per door, minimum metadata | 10,850,640 | 0.010851 | $1.63 |
| **launching a room** (room accounts + door 0, max metadata; no fees) | **33,213,120** | **0.033213** | **$4.98** |
| graduation rent for the DAMM v2 accounts (§5), paid from the reserve | 24,680,160 | 0.024680 | — |

Launching is free: `room_fee_lamports` and `door_fee_lamports` default to 0.
The launcher pays rent and transaction fees and nothing else. Doors are never
closed, so their rent is permanent.

**Mints.** Room and door mints are created as follows:

- decimals 6;
- 1,000,000,000 tokens (10¹⁵ base units) minted once into the mint's vault;
- `mint_authority` set to None in the same instruction;
- `freeze_authority` None;
- MetadataPointer pointing to itself, with authority None;
- TokenMetadata `update_authority` set to None after initialisation.

**Nothing else.** No PermissionedBurn, transfer fee, hook or close authority.
To wallets and scanners they look like ordinary fixed-supply memecoin mints.

- Door mints carry `additional_metadata = [("room", <room pubkey>), ("door", <index>)]`.
- **The room mint carries door 0's name, symbol and URI**, which the launcher
  supplies in `create_room`, plus `[("room", <room pubkey>)]`. Its
  `update_authority` is None, so the room's face is fixed permanently by the
  first launcher.
  - There is deliberately no mutable authority that could later re-point the
    room token at whichever door becomes dominant. A mutable authority would
    be a scanner flag and a real rug vector.
- **The room token and door 0 are identical twins:** same metadata, different
  mints, same asset, same price. Economically harmless; the frontend must
  label which is which (§9).
- **Names, symbols and images need not be unique.** There is no ticker lock;
  any number of doors in a room may share them (§7, clones). The slug remains
  unique among live rooms through `SlugLock`.

**Why `GradPayer` is system-owned.** DAMM v2 creates its accounts with a
`payer` signer through `system_program::create_account`. The system program
only debits accounts it owns, so a program-owned vault cannot pay. `GradPayer`
holds no data and is owned by the System Program. The doors program signs for
it with its seeds.

**The pool-creator PDA.** `pool_creator_authority` is a single global PDA,
`["pool_creator"]`, with no account data. It signs DAMM v2 pool creation and
its address is what the Meteora dynamic config names.

**`Config`** (238 bytes). Field order:

`admin, protocol_fee_recipient, fee_bps, door_share_bps, door_fee_lamports
(default 0), room_fee_lamports (default 0), convert_fee_lamports,
v_sol_lamports, v_tok, supply, r_star_lamports (the pool seed),
meteora_dynamic_config, graduation_trigger_lamports (R* + graduation rent;
default 85,024,680,160), paused, bump, reserved[64]`.

A non-zero door or room fee, if ever configured, goes entirely to the
protocol; there is no reserve split.

Curve and fee fields are copied into `Room` at creation and are immutable for
that room.

**`Room`** (684 bytes):

- identity, bumps and `status` (0 curve, 1 complete, 2 graduated);
- `room_mint`, `room_vault`, `retired_vault`, `fee_wsol`;
- curve parameters, including `graduation_trigger_lamports` copied from
  `Config`;
- `fee_bps`, `door_share_bps`;
- **`reserve`**: lamports credited to `ReserveVault` by the program;
- **`sold`**: curve position q;
- `retired`, `door_count`;
- `protocol_accrued_sol/_wsol`;
- `pending_reserve_sol/_wsol`: the room-token route's 60% share, not yet
  retired. This is its only source now that door fees are zero.
- `reserve_share_total`, `volume_gross`, `trades`, timestamps;
- `damm_pool`, `damm_position`, `position_nft_mint`;
- slug, URI, reserved.

**`Door`** (328 bytes):

- `room`, `index`, `mint`, `door_vault`, `room_token_vault`, `creator`,
  `fee_recipient`, bumps;
- **`backing`**: room tokens in `DoorRoomVault`;
- `accrued_sol/_wsol`, `claimed_sol/_wsol`;
- `buy_volume`, `sell_volume`, `trades`, `created_at`, reserved.

## 2. Curve

### Parameters

| parameter | value |
|---|---|
| total supply `S` | 1,000,000,000 tokens = 10¹⁵ base units |
| fraction sold on the curve `f` | 0.7931: the calibration point used to derive V_sol (R = R* at s = fS = 793,100,000 tokens). With the raised trigger the curve actually sells 793,160,061.522864 tokens by T. |
| virtual tokens `V_tok` | 1,073,025,606 tokens = 1,073,025,606,000,000 base units |
| virtual SOL `V_sol` | **30,000,852,995 lamports** (derived; see §0.2) |
| `K = V_sol · V_tok` | 32,191,683,465,476,789,970,000,000 (fits u128) |
| pool seed SOL `R*` | 85,000,000,000 lamports |
| graduation rent (DAMM v2 accounts) | 24,680,160 lamports (`outputs/account_sizes.md`) |
| graduation trigger `T = R* + rent` (`Config.graduation_trigger_lamports`) | **85,024,680,160 lamports** |
| pool seed tokens `N` | 206,811,223,802,753 base units (206,811,223.802753 tokens), matched to the curve's closing price |
| unsold room tokens retired at graduation | 28,714,674,383 base units (28,714.674383 tokens) |

### Identities

All checked in exact rational arithmetic:

| identity | value | status |
|---|---|---|
| `V_tok = f²S/(2f−1)` | 1,073,025,605.5954 | holds; the brief's 1,073,025,606 is this rounded up by 0.4046 |
| `V_sol = R*(2f−1)/(1−f)` (as written in the brief) | 240.826486 SOL | **wrong: inverted** |
| `V_sol = R*(1−f)/(2f−1)` | 30.000853 SOL | correct form |
| `FDV at graduation = R*/(1−f)` | 410.8265 SOL | holds |
| `market cap / reserve at graduation = 1/(1−f)` | 4.8333× | holds |
| opening → graduation price multiple `= (f/(1−f))²` | 14.6938× | holds when both closed forms hold |
| cost to lift the graduated pool's price +10% `= (√1.1 − 1)·x` | 4.8809% of the pool's SOL side | holds for any constant-product pool; independent of f |

### Continuity at the junction

| parameter set | tokens sold at switch | reserve at switch | tokens left for the pool | price step |
|---|---|---|---|---|
| pump.fun published: V_sol 30, V_tok 1,073,000,000, switch at s = fS | 793,100,000 | 85.005359 SOL | 206,900,000 | **−0.0067611%** |
| V_sol 30, V_tok 1,073,025,606, switch at R = 85 SOL | 793,105,882.696 | 85 SOL | 206,894,117.304 | +0.0014836% |
| **chosen:** V_sol 30.000852995, V_tok 1,073,025,606, switch at R = 85 SOL | 793,100,000 | 85 SOL | 206,900,000 | +0.0000001068% |
| exact closed forms for both V_sol and V_tok | 793,100,000 | 85 SOL | 206,900,000 | **0 exactly** |

**pump.fun's rounding of V_tok to 1,073,000,000 is the whole source of the
−0.0068% step** that the previous version of this spec measured. With V_tok at
its closed form the step is exactly zero. With the brief's rounded
1,073,025,606 it is +1.07×10⁻⁷ %. These rows describe a switch at R = R*; the
raised trigger is handled next.

### Graduation trigger raised by the graduation rent (ruling 2)

| quantity | value |
|---|---|
| trigger T = R* + 24,680,160 | 85,024,680,160 lamports |
| q_g (largest q with R(q) ≤ T) | 793,160,061,522,864 base units; R(q_g) = T exactly |
| room tokens left in `RoomVault`, U − q_g | 206,839,938,477,136 base units |
| **literal reading:** seed R* with all remaining tokens | price step **−0.013883%** |
| **chosen:** seed R* with N = floor(R*·(V_tok − q_g)²/K) | N = 206,811,223,802,753 base units; step **+2.755×10⁻¹³ %** |
| unsold tokens retired, U − q_g − N | 28,714,674,383 base units |
| alternative: re-derive V_sol to seed all remaining tokens | V_sol 29,992,871,855; seed 206,784,900,603,504; step +4.6×10⁻¹¹ % |

**Why seeding all remaining tokens fails.** The reserve holds T at the switch,
but only R* goes to the pool, so the SOL side shrinks by the rent while the
token side stays the same. The price drops.

**Why seeding N tokens works.** Giving the pool only the tokens that the
curve's closing price buys with R* keeps the price, and the unsold remainder
is locked. It holds no claim on any SOL: those tokens were never sold.

### Exact integer definition (phase 0, the curve)

Units are lamports and base units. The reserve owed for curve position q is:

```
R(q) = floor( K / (V_tok − q) ) − V_sol
```

- R(0) = 0 exactly, because K/V_tok = V_sol.
- R is non-decreasing.
- **Price is computed from `room.sold` only**, never from any account balance.
- **Buy of net lamports n:** find the largest q′ with R(q′) ≤ R(q) + n:
  `q′ = V_tok − floor(K/(R(q) + n + V_sol + 1)) − 1`.
  This is exact, because `floor(K/(V_tok−q′)) ≤ T + V_sol` ⇔
  `V_tok − q′ > K/(T + V_sol + 1)`. Then d = q′ − q tokens.
- **Sell of t tokens:** pays `g = R(q) − R(q − t)`.
- **Graduation point.** q_g is the largest q with R(q) ≤ T. With these
  parameters:
  - q_g = 793,160,061,522,864 base units;
  - R(q_g) = T = 85,024,680,160 lamports exactly;
  - N = 206,811,223,802,753 base units go to the pool with R*;
  - U − q_g − N go to `RetiredVault`.
- **Marginal price**, used for display and events only:
  `K/(V_tok − q)²` lamports per base unit.

### Phase 1, the pool

After graduation the price is set by the DAMM v2 pool. It is seeded at the
curve's closing price (step above) with full-range liquidity, which behaves as
constant product with K′ = R* × N = 85 SOL × 206,811,223.802753 tokens.

**Price impact of a buy** (marginal price after vs before; program and pool
fees excluded):

Rows below 85 SOL are curve phase. A buy that crosses T fills the curve to T;
then R* goes to the pool and the rent to `GradPayer`, so the pool's SOL side
ends at the buy's reserve level minus the rent. Rows from 85 SOL up are pool
phase, where x is the pool's SOL side.

| reserve / pool SOL side | buy 0.5 SOL | 5 SOL | 50 SOL | 500 SOL | FDV (SOL) | FDV / reserve |
|---|---|---|---|---|---|---|
| 1 SOL | 3.25% | 34.86% | 582.70% | 47,722.91% | 30 | 29.9× |
| 10 SOL | 2.52% | 26.56% | 406.24% | 29,665.31% | 50 | 5.0× |
| 50 SOL | 1.25% | 12.89% | 185.99% | 8,554.62% | 199 | 4.0× |
| 84 SOL | 0.88% | 11.55% | 152.92% | 4,705.33% | 404 | 4.8× |
| 85 SOL (pool) | 1.18% | 12.11% | 152.25% | 4,636.68% | 411 | 4.8× |
| 500 SOL | 0.20% | 2.01% | 21.00% | 300.00% | 14,222 | 28.4× |
| 5,000 SOL | 0.02% | 0.20% | 2.01% | 21.00% | 1,422,155 | 284.4× |
| 50,000 SOL | 0.00% | 0.02% | 0.20% | 2.01% | 142,215,515 | 2,844.3× |

**Depth is not continuous at graduation, even though price is.** A 0.5 SOL buy
moves price 0.88% at 84 SOL of reserve, but 1.18% just after graduation,
because the 30 virtual SOL disappear.

**Depth** (SOL needed to move the price; fees excluded):

| reserve / pool SOL side | +1% | +5% | +10% | −1% sale | −5% sale | −10% sale |
|---|---|---|---|---|---|---|
| 10 SOL | 0.200 | 0.988 | 1.952 | 0.201 | 1.013 | 2.053 |
| 50 SOL | 0.399 | 1.976 | 3.905 | 0.401 | 2.026 | 4.105 |
| 85 SOL | 0.424 | 2.099 | 4.149 | 0.426 | 2.152 | 4.362 |
| 500 SOL | 2.494 | 12.348 | 24.404 | 2.506 | 12.660 | 25.658 |
| 5,000 SOL | 24.938 | 123.475 | 244.044 | 25.063 | 126.603 | 256.584 |

In the curve phase, depth includes the 30 virtual SOL, which are not backed.

---

## 3. Instructions

**Common rules.**

- `b = fee_bps` (default 100); `d = door_share_bps` (default 6000).
- Fees are always charged on top. On a buy the user pays `lamports_in`; the
  curve or pool receives `n = floor(lamports_in · 10⁴ / (10⁴ + b))`, and
  `F = lamports_in − n` is the fee.
- On a sell, `F = ceil(g · b / 10⁴)` comes out of the seller's gross proceeds
  `g`, after the curve or pool has paid exactly `g`.
- **Fee split** `split(F, route)`:
  - `door = floor(F · d / 10⁴)`;
  - `protocol = F − door`;
  - on the room-token route, `door` goes to `pending_reserve` instead of a
    door.
- **Asserting the backing invariant.** Every instruction that touches a door
  ends by asserting B1 (§4) for each door it touched. It reads the two vault
  balances from the token accounts, not from cached fields.

### `create_room(slug, door0_name, door0_symbol, door0_uri, first_buy_lamports, min_tokens_out)`

**Signer:** launcher. By default they pay rent only: 0.033213 SOL ($4.98) for
the room accounts and door 0. `room_fee_lamports` defaults to 0; if it is ever
set, it goes to the protocol.

**Creates:**

- `Room`, `ReserveVault`, `FeeVault`;
- `GradPayer`, funded with its own rent-exempt minimum only;
- `SlugLock` (fails if the normalised slug is held by a live room);
- `RoomMint`, `RoomVault`, `RetiredVault`, `FeeWsol`;
- **door 0**, which is always created.

1. **Room mint**, with door 0's metadata:
   1. Create `RoomMint` with space for MetadataPointer, funded for its final
      size; Token-2022 metadata initialisation resizes the account without
      adding lamports (`interface/src/extension/mod.rs`,
      `alloc_and_serialize_variable_len_extension`).
   2. `MetadataPointer::Initialize` (self, authority None).
   3. `InitializeMint2` with decimals 6, mint authority the Room PDA, freeze
      None.
   4. `TokenMetadata::Initialize(door0_name, door0_symbol, door0_uri)`, then
      `UpdateField("room", …)`.
   5. Create `RoomVault` and `MintTo(RoomVault, 10¹⁵)`.
   6. `SetAuthority(MintTokens → None)`, then metadata
      `UpdateAuthority → None`.
2. **Room fee:** default 0; if non-zero, to the protocol. The graduation rent
   is *not* collected here; it comes out of the reserve at `graduate` (§5.1).
3. **Initialise `Room`:**
   - status 0, `sold = 0`, `reserve = 0`;
   - curve and fee parameters copied from `Config`, including
     `graduation_trigger_lamports`.
4. **Door 0:** the `open_door` steps below, with the same name, symbol and
   URI. The room token and door 0 are twins.
5. **Optional first buy** through door 0.

There is no founder share or other founder privilege. The launcher's only
lasting distinction is that their metadata is the room token's.

### `open_door(room, name, symbol, uri, first_buy_lamports, min_tokens_out)`

**Allowed:** any status: before graduation, while complete, and after
graduation.

**Checks:** name 1–32 bytes, symbol 1–10 bytes, URI ≤ 200 bytes. **There
is no uniqueness check:** names, symbols and images may repeat freely within a
room.

**Signer:** opener, who pays rent only: 0.012584 SOL ($1.89).
`door_fee_lamports` defaults to 0; if it is ever set, it goes to the
protocol.

1. **Door mint.**
   1. Create `DoorMint`, the same sequence as the room mint, with metadata
      `("room", …), ("door", index)`.
   2. Create `DoorVault` and mint 10¹⁵ into it.
   3. Mint authority → None, metadata update authority → None.
2. **Accounts.** Create `DoorRoomVault` (empty) and `Door` (`backing = 0`).
   `room.door_count += 1`.
3. **Door fee:** default 0; if non-zero, to `room.protocol_accrued_sol`.
4. **Optional first buy.** Run `buy` through the new door in the same
   instruction.
5. **Assert** B1 for the new door: 0 room tokens backing 0 circulating door
   tokens.

### `buy(route = Door(N) | RoomToken, lamports_in, min_tokens_out)`, status 0 (curve)

**Accounts:** user (signer, writable), config, room (w), ReserveVault (w),
FeeVault (w), RoomVault (w), room_mint, and the user's destination ATA (w;
created idempotently in a preceding instruction). For the door route, add
door N (w), DoorMint N, DoorVault N (w) and DoorRoomVault N (w). Also the
token-2022 and system programs, and event authority.

1. **Validate:**
   - not paused, status 0;
   - PDA seeds;
   - for the door route, `door.room == room` and the vaults match `Door`;
   - `lamports_in > 0`.
2. **Fee on top:** `n`, `F` as above.
3. **Price from state.** q = `room.sold`.
   - If `room.reserve + n > T` (`room.graduation_trigger_lamports`), cap on
     the **reserve**: `n := T − room.reserve`, and recompute `F` on the capped
     amount. The unspent lamports are never taken (the capped transfer amounts
     are used in step 4).
   - Capping on the reserve, not on `R(q)`, makes the room complete with
     `room.reserve == T` exactly. Any rounding slack from earlier buys sits
     inside T rather than leaving the reserve short of R* + rent.
   - Compute `q′` (the largest with `R(q′) ≤ R(q) + n`), `d = q′ − q`; require
     `d ≥ min_tokens_out`.
4. **Lamports in** (system-program CPIs, signed by the user):
   - user → `ReserveVault`: `n`;
   - user → `FeeVault`: `F`.
5. **Tokens.** Room PDA signs `TransferChecked(RoomVault → dest, d)`:
   - room-token route: `dest` is the user's room-token ATA;
   - door route: `dest` is `DoorRoomVault N`, and then the Door PDA signs
     `TransferChecked(DoorVault N → user's door-N ATA, d)`.
6. **State:**
   - `room.reserve += n`, `room.sold = q′`;
   - door route: `door.backing += d`, `door.accrued_sol += door share`;
   - room-token route: `room.pending_reserve_sol += door share`;
   - `room.protocol_accrued_sol += protocol share`;
   - volumes and timestamps.
7. If `room.reserve == T`: `room.status = 1` (complete). With the chosen
   parameters `R(q_g) = T` exactly, so the slack is zero.
8. **Assert:** I1, I2, S1, and B1 for door N. **Emit** `Trade`.

### `sell(route, tokens_in, min_lamports_out)`, status 0

Same accounts.

1. **Validate.**
2. `g = R(q) − R(q − tokens_in)`; `F = ceil(g·b/10⁴)`; require
   `g − F ≥ min_lamports_out`.
3. **Tokens:**
   - door route: the user signs `TransferChecked(user door-N ATA → DoorVault N,
     tokens_in)`, then the Door PDA signs
     `TransferChecked(DoorRoomVault N → RoomVault, tokens_in)`;
   - room-token route: the user signs
     `TransferChecked(user room ATA → RoomVault, tokens_in)`.
4. **Lamports out.** The program debits `ReserveVault` by exactly `g` (it
   owns the account): `g − F` to the user, `F` to `FeeVault`.
5. **State:**
   - `room.reserve −= g`, `room.sold −= tokens_in`;
   - door route: `door.backing −= tokens_in`;
   - split F as for buy.
6. **Assert:** I1, I2, S1, and B1 for door N. **Emit.**

**While complete (status 1),** `buy` and `sell` refuse. The reserve must stay
at T until `graduate` runs. `open_door`, `convert` and the claim
instructions stay available.

### `buy` / `sell`, status 2 (graduated)

**Extra accounts:** DAMM v2 program, pool authority, pool, token A vault
(room token), token B vault (WSOL), room mint, WSOL mint, the user's WSOL ATA
(w), SPL Token program, DAMM v2 event authority, and `FeeWsol` (w, for
sells).

**Buy:**

1. Fee on top: `n`, `F`.
2. user → `FeeVault`: `F` (system CPI).
3. user → user's WSOL ATA: `n`, then `SyncNative`.
4. CPI DAMM v2 `swap(amount_in = n, minimum_amount_out = min_tokens_out)`:
   - payer = user (signer);
   - input = the user's WSOL ATA;
   - output = `DoorRoomVault N` (door route) or the user's room-token ATA
     (room route).
5. `d` = the increase in the output account's balance, read before and after.
6. Door route: the Door PDA signs `TransferChecked(DoorVault N → user door-N
   ATA, d)`. `door.backing += d`.
7. Split `F` (SOL counters). Assert B1. Emit.

**Sell:**

1. Door route: the user transfers `tokens_in` door-N tokens to `DoorVault N`.
   Then CPI DAMM v2 `swap(amount_in = tokens_in, minimum_amount_out = 0)` with
   payer = the Door PDA (signs via seeds) and input = `DoorRoomVault N`.
   Room-token route: the input is the user's room-token ATA and the user pays.
2. Output = the user's WSOL ATA. `g` = the increase in its balance.
3. `F = ceil(g·b/10⁴)`. The user signs `TransferChecked(user WSOL ATA →
   FeeWsol, F)`.
4. Require `g − F ≥ min_lamports_out`.
5. Door route: `door.backing −= tokens_in`.
6. Split `F` into the `_wsol` counters. Assert B1. Emit.
7. The client appends `CloseAccount(user WSOL ATA)` to unwrap.

**Notes on the post-graduation flows:**

- **The pool also charges its own fee** inside the swap: `pool_base_fee_bps`
  (§5.3), on the SOL side because the collect-fee mode is OnlyB.
- **No reserve exists after graduation.** The program never debits anything
  for a fee: buy fees are paid by the user on top, and sell fees come out of
  the user's own proceeds.

### `convert(door_a, door_b, amount)`, any status

1. Validate both doors are in `room`, `door_a ≠ door_b`, `amount > 0`.
2. The user signs `TransferChecked(user A ATA → DoorVault A, amount)`.
3. The Door A PDA signs `TransferChecked(DoorRoomVault A → DoorRoomVault B,
   amount)`.
4. The Door B PDA signs `TransferChecked(DoorVault B → user B ATA, amount)`.
5. `door_a.backing −= amount`, `door_b.backing += amount`.
6. `convert_fee_lamports` (default 0) goes to the protocol. No door share.
7. `room.sold`, `room.reserve` and the price are unchanged. Assert B1 for both
   doors.

**There is deliberately no conversion between a door and the room token.**
After graduation, a door → room-token conversion followed by a direct pool
sale would skip the door's sell fee.

### `retire_pending(room)`, permissionless crank

It turns `pending_reserve_*`, the room-token route's 60% share, into retired
supply. Door fees no longer feed it.

**Status 0:**

1. Move `pending_reserve_sol` lamports `FeeVault → ReserveVault` (direct
   debit).
2. `room.reserve += r`.
3. Buy curve position: `q′` = the largest with `R(q′) ≤ R(q) + r`, with `r`
   capped so that `room.reserve + r ≤ T`.
4. Transfer `q′ − q` room tokens `RoomVault → RetiredVault`.
5. `room.sold = q′`, `room.retired += q′ − q`.
6. Any part that would take the reserve above T stays pending. It is retired
   on the pool after graduation.

**Status 2:**

1. Move `pending_reserve_sol` into `FeeWsol` and `SyncNative`.
2. CPI DAMM v2 `swap` with input `FeeWsol` (payer = Room PDA) for the pending
   total, output `RetiredVault`.
3. `room.retired +=` the amount received.

**Retired room tokens are never moved again.** This is how the "reserve" share
raises the price for every holder.

### `graduate(room)`, permissionless, status 1

Transaction: a v0 transaction with an address lookup table (the account count
is in §7).

1. **Entry check.** Status 1, so `room.reserve == T` (§3 buy step 7). The
   pending reserve share stays pending and is retired on the pool afterwards.
2. **Split the reserve.** Three debits of `ReserveVault`, which sum to exactly
   `room.reserve`:
   - **seed:** exactly R* = 85,000,000,000 lamports into a temporary WSOL
     account owned by `GradPayer`, then `SyncNative`;
   - **graduation rent:** `T − R*` = 24,680,160 lamports to `GradPayer`, a
     direct credit, which the runtime allows to any writable account;
   - **slack:** `room.reserve − T` to `FeeVault` as `protocol_accrued_sol`.
     It is zero by construction (the cap in buy step 3); the term is kept so
     the identity holds under any future change.
   - `room.reserve = 0`.
3. **Check rent sufficiency.** `GradPayer` must hold the rent-exempt minimums
   of the accounts DAMM v2 will create, from the rent sysvar at call time.
   - If DAMM v2 account sizes have grown since this room's
     `graduation_trigger_lamports` was snapshotted, the shortfall is taken
     from `room.protocol_accrued_sol`.
   - If that is not enough, `graduate` fails and can be retried after the
     protocol tops it up. The reserve is never touched for it.
4. **Prepare the tokens.**
   - Compute `N = floor(R* · (V_tok − room.sold)² / K)` (206,811,223,802,753
     base units with the chosen parameters).
   - Transfer N room tokens `RoomVault → GradPayer`'s room-token account.
   - Transfer the rest, `U − room.sold − N` (28,714,674,383 base units),
     `RoomVault → RetiredVault`, and add it to `room.retired`.
   - The seed of exactly R* and N opens the pool at the curve's closing
     price (§2).
5. **Create the pool and position.** CPI DAMM v2
   `initialize_pool_with_dynamic_config(params)`:
   - signers: `pool_creator_authority` = the `["pool_creator"]` PDA, and
     payer = `GradPayer`;
   - `creator` = the Room PDA;
   - `position_nft_mint` = PDA `["position_nft", room]`, signed via seeds;
   - token A = the room mint, token B = WSOL;
   - payer token accounts = `GradPayer`'s room-token and WSOL accounts;
   - parameters in §5.3.
6. **Lock.** CPI `permanent_lock_position(position.unlocked_liquidity)`, with
   signer = the Room PDA (the NFT holder).
7. **Hand the NFT to the protocol.** The Room PDA signs
   `TransferChecked(position NFT → protocol_fee_recipient's NFT ATA, 1)`.
8. **Dust.**
   - Close the temporary WSOL account into `GradPayer`, then send `GradPayer`'s
     lamports above its own rent-exempt minimum to the protocol.
   - Leftover room tokens in `GradPayer`'s account go to `RetiredVault`.
9. **State:** `room.status = 2`; store `damm_pool`, `damm_position`,
   `position_nft_mint`, `graduated_at`.
10. **Emit** `Graduated`.

### `release_slug(room)`, permissionless

Ruling 5 keeps SlugLock with the expiry rule from DESIGN.md §6.

- **Allowed when all hold:**
  - `room.status < 2`;
  - `room.reserve < 1,000,000,000` lamports (1 SOL);
  - `now − room.last_trade_at > 604,800` seconds (7 days).
- **Effect:** closes `SlugLock`, with its rent going to the caller as a cleanup
  incentive. A new room may then register the slug.
- **Nothing else changes for the released room.** It keeps trading by
  `room_id`. Its room token's metadata does not depend on the slug, its doors
  are untouched, and it is not closed.
- **Graduated rooms never release their slug.** Their direct pool trading is
  invisible to `last_trade_at` (§0.A.2).

### Fee instructions

- **`claim_door_fees(door)`.** The signer must be `door.fee_recipient`. It
  pays `accrued_sol` from `FeeVault` (direct debit) and `accrued_wsol` from
  `FeeWsol` (Room PDA signs a transfer to the recipient's WSOL ATA). Then it
  zeroes both and adds them to the claimed totals.
- **`set_fee_recipient(door, new)`.** Signed by the current recipient.
- **`sweep_protocol_fees(room)`.** Permissionless. It pays
  `protocol_accrued_sol/_wsol` to `config.protocol_fee_recipient` and zeroes
  them.
- **Pool LP fees go nowhere near the program.** The protocol fee recipient
  holds the position NFT and calls DAMM v2 `claim_position_fee` directly.

---

## 4. Invariants and proof by path

Notation:

- `bal(X)` is a token account balance; `L(X)` is an account's lamports.
- `U = 10¹⁵`, one billion tokens in base units.

**B1, 1:1 backing.** For every door N:

```
bal(DoorRoomVault_N) == U − bal(DoorVault_N) == door_N.backing
```

Asserted at the end of every instruction that touches door N. Holders can
still burn their own door tokens with a standard Token-2022 `Burn`, since
there is no PermissionedBurn. That lowers the mint's supply but changes
neither vault, so B1, defined on vault balances, still holds. The room tokens
backing a burned door token stay in `DoorRoomVault_N` forever.

**S1, curve position** (status 0 and 1): `room.sold == U − bal(RoomVault)`.

**I1, solvency** (status 0 and 1): `room.reserve ≥ R(room.sold)`.

**I2, vault backing:**

```
L(ReserveVault) − rent_min ≥ room.reserve
L(FeeVault) − rent_min ≥ Σ_N door_N.accrued_sol + room.protocol_accrued_sol + room.pending_reserve_sol
bal(FeeWsol) ≥ Σ_N door_N.accrued_wsol + room.protocol_accrued_wsol + room.pending_reserve_wsol
```

**Proof by path.** Each row lists the changes; every invariant is preserved.

| path | B1 (door N) | S1 / I1 | I2 / fees |
|---|---|---|---|
| `open_door` / door 0 in `create_room` | new door: 0 == U − U == 0 | — | no fee by default; a non-zero door fee goes to `protocol_accrued_sol`, and `FeeVault` += the same |
| buy, door N, curve | DoorRoomVault +d, DoorVault −d, backing +d | RoomVault −d, sold +d; reserve +n with `R(q+d) − R(q) ≤ n` | `F` into `FeeVault` and counters; reserve untouched by `F` |
| sell, door N, curve | DoorVault +t, DoorRoomVault −t, backing −t | RoomVault +t, sold −t; reserve −g with `g = R(q) − R(q−t)` exactly | `F` taken from `g` after the curve paid `g`; `ReserveVault` debited by exactly `g` |
| buy / sell, room token, curve | no door | as above, with the user's room-token ATA in place of the door vaults | door share → `pending_reserve_sol` (in `FeeVault`) |
| `convert` A→B | A: both sides −amount; B: both sides +amount | unchanged | `convert_fee` → protocol |
| `retire_pending`, status 0 | no door | RoomVault −d → RetiredVault, sold +d; reserve +r with `R(q+d) − R(q) ≤ r` and `reserve + r ≤ T` | `FeeVault` −r, `pending_reserve_sol` −r |
| `graduate` | no door touched | three debits of `ReserveVault` summing to `room.reserve` (below); RoomVault −N to the pool and −(U − sold − N) to `RetiredVault`; I1 and S1 retire at status 2 | slack → `protocol_accrued_sol`; `GradPayer` pays DAMM v2 rent; dust to the protocol / `RetiredVault` |
| buy, door N, pool | DoorRoomVault +d (measured), DoorVault −d, backing +d | — | `F` paid by the user on top into `FeeVault` |
| sell, door N, pool | DoorVault +t, DoorRoomVault −t (into the pool), backing −t | — | `F` from the user's WSOL proceeds into `FeeWsol` |
| `retire_pending`, status 2 | no door | — | `FeeWsol` −pending, `RetiredVault` +received |
| claims, sweeps | — | — | debit `FeeVault`/`FeeWsol` and zero the matching counters |

**`graduate`, step by step.** On entry status is 1, so `room.reserve = T` and
I1 holds: `T ≥ R(room.sold)`, with equality for the chosen parameters. Each
debit lowers `room.reserve` by exactly the lamports moved, so I2
(`ΔL(ReserveVault) == Δroom.reserve`) holds after every debit.

| step | lamports moved out of `ReserveVault` | `room.reserve` after | where they go |
|---|---|---|---|
| entry | — | T = 85,024,680,160 | — |
| a. seed | R* = 85,000,000,000 | T − R* = 24,680,160 | temporary WSOL → DAMM v2 token B vault |
| b. graduation rent | T − R* = 24,680,160 | 0 + slack | `GradPayer` → DAMM v2 account rent |
| c. slack | `room.reserve − T` (0 by construction) | 0 | `FeeVault`, `protocol_accrued_sol` |
| exit | total = `room.reserve` at entry | 0 | status 2: I1 and S1 retire |

**What happens to holders' claims at the handoff.** Before graduation the
reserve covers `R(sold)`, the curve's obligation to every outstanding room
token. After graduation that obligation is carried by the pool. It holds R*
and N tokens at the curve's closing price, and every outstanding room token
(in users' wallets, in `DoorRoomVault`s and in `RetiredVault`) can sell into
it.

**The rent is paid by the curve, not by holders.** It came from buyers who
lifted the reserve from R* to T. Those 24,680,160 lamports bought tokens at
the curve price (q went from 793,099,999,999,525 to 793,160,061,522,864 base
units) and leave as rent. That is the cost ruling 2 chose to place on the
curve.

**Review rule.** Any instruction that debits `ReserveVault` by anything other
than exactly `R(q) − R(q − t)` on a sell, or by the three `graduate` debits
summing to `room.reserve`, fails review.
That includes paying the seller `g` and then taking `F` out of
`ReserveVault`, or crediting `n + F` to the reserve and taking `F` back.

**Unit tests** must assert, for every instruction:

- `ΔL(ReserveVault) == Δroom.reserve`;
- B1 holds for every door touched.

There must also be a property test of I1 over random operation sequences.

---

## 5. Graduation

### 5.1 Trigger

Graduation triggers on the **reserve reaching
`T = room.graduation_trigger_lamports`**, never on market cap.

- T is R* plus the DAMM v2 graduation rent: 85,000,000,000 + 24,680,160 =
  **85,024,680,160 lamports**.
- It is a `Config` value, because the rent depends on DAMM v2's account sizes.
  `Config` changes affect new rooms only, since each room snapshots T. A room
  whose snapshotted rent falls short at graduation tops up from
  `protocol_accrued_sol` (§3 `graduate` step 3).
- The crossing buy is capped so the reserve ends at exactly T.
- The room becomes complete (status 1); trading pauses until `graduate`.
- `graduate` is permissionless, so the protocol's crank or anyone can call it.

### 5.2 What the program calls

`initialize_pool_with_dynamic_config` is defined in
`programs/cp-amm/src/instructions/initialize_pool/ix_initialize_pool_with_dynamic_config.rs`.

Accounts:

- `creator`, `position_nft_mint` (signer), `position_nft_account`;
- `payer` (signer), `pool_creator_authority` (signer), `config`;
- `pool_authority`, `pool`, `position`;
- token A and B mints, token A and B vaults, `payer_token_a`, `payer_token_b`;
- token A and B programs, `token_2022_program`, `system_program`.

The pool address is `[POOL_PREFIX, config, max(mint), min(mint)]`. Because the
config is private to this program, nobody else can pre-create the pool.

The parameters use the same struct as the customizable pool,
`InitializeCustomizablePoolParameters`: `pool_fees`, `sqrt_min_price`,
`sqrt_max_price`, `has_alpha_vault`, `liquidity`, `sqrt_price`,
`activation_type`, `collect_fee_mode`, `activation_point`.

### 5.3 Parameters

| parameter | value | source / reason |
|---|---|---|
| `sqrt_min_price`, `sqrt_max_price` | `MIN_SQRT_PRICE = 4295048016`, `MAX_SQRT_PRICE = 79226673521066979257578248091` | `constants.rs` L4, L10: full range, so the pool behaves as constant product |
| `sqrt_price` | Q64.64 square root of `R* / N`, in lamports per base unit; equals the curve's closing price `K/(V_tok − q_g)²` to under one base unit | continuity with the curve |
| `liquidity` | the largest L whose required amounts (`liquidity_handler/concentrated_liquidity.rs` L19, `get_delta_amount_a/b_unsigned` L288, L324) fit within N = 206,811,223,802,753 base units and R* = 85,000,000,000 lamports | rounding dust per graduate step 8; dust size not computed here (needs the Q64 math implemented) |
| `collect_fee_mode` | `OnlyB`, so fees are collected in WSOL | `state/pool.rs` L49–57. `Compounding` must **not** be used: it folds fees into liquidity and leaves nothing to claim. |
| `pool_fees` base fee | `pool_base_fee_bps`, **a parameter (assumed default 100 bps)** | Lower bound `MIN_FEE_BPS = 1`. The upper bound depends on the fee version: `MAX_FEE_BPS_V0 = 5000` or `MAX_FEE_BPS_V1 = 9900` (`constants.rs` L112–127); 100 bps is within both. Meteora keeps `PROTOCOL_FEE_PERCENT = 20` (L146), so 80% goes to positions. |
| `has_alpha_vault`, `activation_point` | false, none (activate immediately) | — |

### 5.4 The locked position and the fee owner

**Permanent lock.** `permanent_lock_position(permanent_lock_liquidity)`
(`instructions/ix_permanent_lock_position.rs`) moves liquidity from
`unlocked_liquidity` to `permanent_locked_liquidity`. The signer must be the
NFT holder or a delegate with `LockPosition` permission (`state/position.rs`
L544–562).

**Locked principal cannot come out:**

- `remove_liquidity` can only take `unlocked_liquidity`
  (`ix_remove_liquidity.rs` L122–124);
- `close_position` requires an empty position (`ix_close_position.rs` L56).

**DAMM v2 has no separate "fee owner" field.** Fee rights follow the position
NFT. `claim_position_fee` accepts the NFT holder as signer, sending to any
destination, or a delegate with `ClaimPositionFee` /
`ClaimPositionFeeToOwner` permission (`ix_claim_position_fee.rs` L75–79). So
**the fee owner is whoever holds the NFT.**

The spec achieves "permanently locked, fee owner = protocol fee recipient" in
three steps:

1. The Room PDA holds the NFT and locks the position.
2. It transfers the NFT to the protocol fee recipient.
3. The protocol then claims LP fees indefinitely with `claim_position_fee`.

The NFT is a Token-2022 mint with MetadataPointer and close authority
(`ix_create_position.rs` L20–34) and no non-transferable extension, so it can
be transferred. Its freeze authority is the pool account. DAMM v2 source at
this commit contains no freeze or thaw call (searched for `freeze_account`,
`FreezeAccount`, `thaw`).

**On-chain confirmation**, from slot 463,751,285 against the deployed DAMM v2
binary: it contains the Anchor log strings `Instruction:
InitializePoolWithDynamicConfig`, `PermanentLockPosition`,
`ClaimPositionFee`, `CreatePosition`, `Swap`, `Swap2` and `AddLiquidity`.
Raw discriminator bytes are not reliably present in compiled code, so they are
not used as evidence. A live DAMM v2 pool account
(`AeaMYByFeRW6qkAMyiujgU2RY6qMSLtGN8kx4PbemBke`) is 1,112 bytes, matching
`8 + Pool::INIT_SPACE`.

**Dependency.** Meteora must create a dynamic config with
`pool_creator_authority = ["pool_creator"]` PDA, and its address is stored in
`Config.meteora_dynamic_config`. 74 such private dynamic configs existed at
slot 463,751,288. The fallback, `initialize_customizable_pool`, works without
Meteora but can be squatted (§0.4).

### 5.5 Doors are untouched

Graduation moves only:

- the reserve lamports: R* to the pool, the rent to `GradPayer`, any slack to
  `FeeVault`;
- the room tokens still in `RoomVault`: N to the pool, the rest to
  `RetiredVault`;
- `GradPayer`'s lamports, to DAMM v2 account rent.

It does not touch any `Door`, `DoorMint`, `DoorVault` or `DoorRoomVault`.
After graduation, a door buy gets its room tokens from the pool instead of the
curve, using the same vaults and the same B1. There is no migration event and
no wrapper, and `open_door` is unchanged.

### 5.6 What graduation changes for fees

| route after graduation | program fee | pool fee (assumed 100 bps) | total |
|---|---|---|---|
| through door N | 100 bps (60 door / 40 protocol) | 100 bps (80 to the protocol's locked position / 20 Meteora) | 200 bps |
| room token through the program | 100 bps (60 → reserve buyback / 40 protocol) | 100 bps | 200 bps |
| **room token directly on the DAMM v2 pool** | **0** | 100 bps | **100 bps** |

**The brief's rule "never cheaper than a door" holds for every route through
the program, and fails for direct pool trades by exactly the program fee.**
Lowering or raising `pool_base_fee_bps` does not change the gap, because the
door route pays the pool fee too.

Routing aggregators will send post-graduation room-token flow to the direct
pool route. Door holders still exit through the program, because there is no
door → room-token conversion.

---

## 6. Fees

`outputs/fee_model.md`:

| route (pre- or post-graduation, program fee only) | door | reserve | protocol | total, per $1M |
|---|---|---|---|---|
| through door N | $6,000 | $0 | $4,000 | $10,000 |
| room token through the program | $0 | $6,000 | $4,000 | $10,000 |

**Where the room token's 60% goes.** It goes to `pending_reserve` and is
retired by `retire_pending`: bought on the curve, or on the pool after
graduation, into `RetiredVault`. That raises the price for every holder.

**Launch fees are zero.** `door_fee_lamports = room_fee_lamports = 0` is the
intended configuration.

| what the launcher pays | SOL | USD at $150 |
|---|---|---|
| a door (rent only, max metadata) | 0.012584 | $1.89 |
| a room with door 0 (rent only) | 0.033213 | $4.98 |
| graduation rent | 0, paid from the reserve at `graduate` | — |

If either fee is ever set above zero, it goes entirely to the protocol.
`pending_reserve_*` now receives only the room-token route's 60% share.

**Spam.** The spam model is an assumption: a door with no traffic of its own
earns only from the share ρ of volume that picks doors uniformly, at 0.60% of
that volume. The only cost of a door is its 0.012584 SOL ($1.89) of rent,
which is never refunded.

One more no-traffic door repays its rent once the room's lifetime volume
reaches `V = rent × (D + 1) / (0.60% × ρ)`:

| ρ | D = 10 | D = 100 | D = 1,000 | D = 10,000 |
|---|---|---|---|---|
| 0.01 | $346.1k | $3.18M | $31.49M | $314.62M |
| 0.05 | $69.2k | $635.5k | $6.30M | $62.92M |
| 0.3 | $11.5k | $105.9k | $1.05M | $10.49M |

10,000 spam doors in a room with 10 doors already (rent cost $18.9k):

| V | ρ = 0.05 | ρ = 0.3 |
|---|---|---|
| $1M | net −$18.6k | net −$17.1k |
| $10M | net −$15.9k | net −$893.50 |
| $50M | net −$3.9k | **net +$71.0k** |

**No fee defends this any more.** With free doors, a no-traffic door is
profitable in any room whose volume clears the threshold above. A mass spam
attack is profitable in large rooms where enough flow picks doors uniformly.

**The defence moves to frontend ranking.** Rank by unique buyers and net
inflow, never by door count or raw volume, so uniform-picking flow shrinks
toward zero (§7, clones). This is a frontend requirement; the program does not
enforce it.

---

## 7. Limits

**Display.**

- Every door mint and the room mint has a fixed 1,000,000,000 supply, so
  every door displays the **room's FDV** (price × 1B).
- An aggregator that sums market caps across a room's mints will overcount by
  the number of mints, which is the door count plus one for the room token.
- Explorers show door-vault balances as "supply" unless the vault is
  labelled. Holders of more than one door see one wallet line per mint.

**Compute per instruction.** Not measured; no program has been built.

**Accounts touched per instruction** (`outputs/instruction_accounts.md`;
constant in the number of doors):

| instruction | accounts |
|---|---|
| curve-phase buy or sell, door route | 16 |
| curve-phase buy or sell, room-token route | 12 |
| pool-phase buy or sell, door route | 26 |
| pool-phase buy or sell, room-token route | 22 |
| convert | 17 |
| `open_door` (without first buy) | 13 |
| `create_room` (with door 0, without first buy) | 21 |
| `release_slug` | 4 |
| `graduate` | 31 |

All are under the 64-account lock limit. `graduate`'s 31 keys (992 bytes) fit
a legacy 1,232-byte packet with only 36 bytes to spare, under assumed
overheads, so it uses a v0 transaction with an address lookup table.

Account lock limit: 64 per transaction, or `MAX_TX_ACCOUNT_LOCKS` behind
`increase_tx_account_lock_limit` (agave `runtime/src/bank.rs` L3847). Measure
CU on a build before quoting throughput.

**Room write lock.** Every buy, sell, retire and `open_door` writes `Room`,
and each door trade also writes its `Door`. Agave caps compute per writable
account per block at `MAX_WRITABLE_ACCOUNT_UNITS = 24,000,000`
(`cost-model/src/block_cost_limits.rs` L33). So room throughput is
`24,000,000 / CU per instruction` trades per block, before graduation and
after. After graduation the DAMM v2 `pool` account is write-locked by every
swap, from the program and direct, under the same cap.

**Door count.** `door_count: u32` gives about 4.29 billion doors per room. No
instruction touches more than two doors. Indexers enumerate doors with
`getProgramAccounts` on a `room` memcmp, whose cost grows with door count.

**Data growth.** `MAX_BLOCK_ACCOUNTS_DATA_SIZE_DELTA = 100,000,000` bytes per
block (same file, L37). A door allocates 1,296 data bytes: Door 328 + DoorMint
638 + two vaults of 165 each.

**Clones and twins: frontend requirements, not on-chain ones.**

- **Clones.** With free doors and no ticker uniqueness, a top-performing door
  can be cloned exactly (same name, symbol and image), and the clone will
  appear beside it in any list.
  - It cannot intercept flow from a direct link, because a link names a mint
    and a buy credits the door whose mint it delivers.
  - A buyer on the "wrong" door loses nothing: it is the same asset at the
    same price. Only fee attribution differs.
  - Frontends must rank doors by unique buyers and net inflow, never by door
    count or raw volume. They should show the mint address and creation time
    so that exact clones are distinguishable.
- **Twins.** The room token and door 0 always carry identical metadata (§1).
  Frontends must label which mint is the room token and which is door 0.

**External venues.**

- Room and door tokens are ordinary SPL Token-2022 tokens, so anyone can seed
  an external pool for them at any time, before or after graduation.
- An external room-token pool before graduation is a cheaper route than a
  door, for the same reason as §5.6.
- An external door pool is arbitraged back against the program through that
  door, which generates door fees.

## 8. Invariants, testable list

1. **B1:** `bal(DoorRoomVault_N) == U − bal(DoorVault_N) == door_N.backing`, for
   every door N, after every instruction that touches N.
2. **S1:** `room.sold == U − bal(RoomVault)` while status < 2.
3. **I1:** `room.reserve ≥ R(room.sold)` while status < 2.
4. **I2:** `L(ReserveVault) − rent_min ≥ room.reserve`, and
   `ΔL(ReserveVault) == Δroom.reserve` for every instruction.
5. **I3:** a curve sell debits `ReserveVault` by exactly `R(q) − R(q−t)`.
   `graduate` debits exactly `room.reserve` (= T at entry): R* to the pool
   seed, `T − R*` to `GradPayer`, and slack `room.reserve − T` (0 by
   construction) to the protocol. No other instruction debits
   `ReserveVault`.
6. **F1:** per trade, `F == door share + protocol share`, and the door share
   lands in exactly one of `door.accrued_*` or `room.pending_reserve_*`.
7. **F2:** both fee vaults cover their counters (I2 above).
8. **F3:** on a buy, the curve or pool receives exactly `n`, and
   `F = lamports_in − n ≥ n·b/10⁴`.
9. **P1:** a curve-phase buy of the same `lamports_in` through any door, or
   through the room-token route, from identical state yields identical `d`.
10. **P2:** `convert` leaves `room.sold`, `room.reserve` and the price
    unchanged.
11. **P3:** the pool opens at or above the curve's closing price, by less than
    one base unit: `R*/N ≥ K/(V_tok − q_g)²` and
    `R*/(N + 1) < K/(V_tok − q_g)²` (measured step +2.755×10⁻¹⁵ relative).
12. **M1:** every room and door mint has `mint_authority == None`,
    `freeze_authority == None`, `update_authority == None`, supply `U`, and no
    extensions beyond MetadataPointer and TokenMetadata. The room mint's name,
    symbol and URI equal door 0's.
13. **D1:** no instruction closes or changes a `Door`, `DoorMint`,
    `DoorVault` or `DoorRoomVault`, except balance moves under B1.
14. **G1:** after `graduate`:
    - the DAMM v2 position's `permanent_locked_liquidity` equals its total
      liquidity;
    - the position NFT is held by `protocol_fee_recipient`;
    - `room.reserve == 0` and `bal(RoomVault) == 0`;
    - the pool was seeded with exactly R* lamports and N room tokens;
    - `RetiredVault` gained `U − sold − N`.
15. **G2:** `graduate` debits `ReserveVault` by exactly `room.reserve` at
    entry: R* + (T − R*) + slack.
16. **S2:** `release_slug` succeeds only if `status < 2`,
    `reserve < 1 SOL` and the room has been idle for more than 7 days. It
    closes only the `SlugLock`.

## 9. What a trader sees

- **Before graduation:** one price per room, from `room.sold`, identical
  through every door and through the room token. `Trade` events carry
  `price_after` and `sold_after`.
- **After graduation:** the price is the DAMM v2 pool's. Doors and the room
  token trade through the program at that price plus fees, and the room token
  also trades directly on the pool.
- **Door tokens look like normal memecoins:**
  - fixed 1B supply, no mint or freeze authority, metadata with name, ticker
    and image;
  - a door is verified by checking its `("room", "door")` metadata against
    the PDA `["door", room, index]`.
- **The room token** carries door 0's name, symbol and image, permanently.
  It and door 0 are twins: same metadata, different mints, same asset, same
  price. The frontend must label which is which.
- **Doors in a room may share names, symbols and images.** Exact clones are
  possible and harmless to buyers. Frontends rank by unique buyers and net
  inflow, and show mint addresses.
- **The first-party UI** should group holdings by room, offer `convert`, and
  show an exact exit quote from `R` (before graduation) or the pool (after),
  next to the mark.
