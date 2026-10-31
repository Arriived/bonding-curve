# Permanent-curve room — build specification

31 October 2026. Build spec for the v1 doors program on Solana. It supersedes
these parts of [DESIGN.md](DESIGN.md):

- the curve (§2 here);
- pre-minted doors (now mint-on-demand, §4);
- `close_door` (removed);
- external graduation (removed).

The three rulings are settled:

- router fee capture is accepted;
- there is no external pool in v1;
- every door works for the life of the room.

**Generated inputs**, all reproducible:

| file | produced by |
| --- | --- |
| `outputs/curve_tables.md` | `scripts/run_curve_model.sh` |
| `outputs/account_sizes.md` | `scripts/run_account_sizes.sh` |
| `outputs/fee_model.md` | `scripts/run_fee_model.sh` |

**Primary sources:**

| source | commit / reading |
| --- | --- |
| solana-program/token-2022 | `986b3aa58cbcc40dea12b369912017a4066804e7` |
| solana-program/token-metadata | `685b8b66db23d4e4012a20553b8552af0812e3bc` |
| solana-program/associated-token-account | `5881eb14aaa794a85f78dc1fcd640cd89bd42cf3` |
| anza-xyz/agave | `aec3b701cfd1ab2c636675b0e30544c60068b08f` |
| Mainnet Token-2022 programdata `DoU57AYuPFu2QU514RktNPG22QhApEjnKxnBcu4BHDTY` | read at slot 463,687,011 |

**Units.** The quote unit is the lamport. Door tokens use 6 decimals, and every
quantity is in base units. Dollar figures use a fixed SOL = $150, for
readability only.

---

## 1. Account layout

All program accounts are PDAs with an 8-byte Anchor discriminator. Rent is
`(128 + data_bytes) × 6,960` lamports. Check: a classic 165-byte SPL token
account comes out at 2,039,280 lamports, the familiar figure. Exact field
offsets are in `outputs/account_sizes.md`.

| account | seeds | data bytes | rent (lamports) | rent (SOL) |
|---|---|---|---|---|
| `Config` | `["config"]` | 198 | 2,268,960 | 0.002269 |
| `Room` | `["room", room_id: u64 LE]` | 472 | 4,176,000 | 0.004176 |
| `RoomVault` (program-owned, holds reserve lamports) | `["vault", room]` | 0 | 890,880 | 0.000891 |
| `FeeVault` (program-owned, holds fee lamports) | `["fees", room]` | 0 | 890,880 | 0.000891 |
| `SlugLock` | `["slug", normalized_slug]` | 17 | 1,009,200 | 0.001009 |
| `Door` | `["door", room, index: u32 LE]` | 246 | 2,603,040 | 0.002603 |
| `DoorMint` (Token-2022), max metadata | `["door_mint", room, index: u32 LE]` | 674 | 5,581,920 | 0.005582 |
| `DoorMint`, minimum metadata | same | 434 | 3,911,520 | 0.003912 |
| `TickerLock` | `["ticker", room, normalized_symbol]` | 13 | 981,360 | 0.000981 |
| trader's Token-2022 ATA (ImmutableOwner), paid by the trader | ATA program | 170 | 2,074,080 | 0.002074 |

- **Per door** (Door + DoorMint at max metadata + TickerLock): **9,166,320
  lamports = 0.009166 SOL**.
- **Per room** (Room + RoomVault + FeeVault + SlugLock), excluding door 0:
  **6,966,960 lamports = 0.006967 SOL**.
- Under Ruling 3, door accounts are never closed, so door rent is locked
  permanently.

### `Room` (472 bytes)

`room_id u64 · founder Pubkey · bump, vault_bump, fee_vault_bump u8×3 ·
x0_lamports u64 · y0 u64 · s1 u64 · fee_bps, creator_share_bps,
founder_share_bps, reserve_share_bps u16×4 · reserve u64 · circulating u64 ·
retired u64 · door_count u32 · founder_accrued u64 · protocol_accrued u64 ·
reserve_share_total u64 · volume_gross u128 · trades u64 · created_at i64 ·
last_trade_at i64 · slug [u8;32] · uri_len u8 · uri [u8;200] · reserved [u8;64]`

- `reserve` holds the lamports the program has credited to RoomVault.
- `circulating` is the sum of door mint supplies.
- `retired` is curve position bought with reserve-share fees. It is never
  minted.
- **The curve position is `q = circulating + retired`.**
- Curve and fee parameters are copied from `Config` when the room is created
  and are **immutable for the room's life**.

### `Door` (246 bytes)

`room Pubkey · index u32 · mint Pubkey · creator Pubkey · fee_recipient Pubkey
· bump, mint_bump u8×2 · supply u64 · accrued u64 · claimed u64 · buy_volume
u128 · sell_volume u128 · trades u64 · created_at i64 · reserved [u8;32]`

- `supply` caches the door mint's supply. Volumes are gross lamports.
- `accrued` is owed to the door; `claimed` has been paid out.

### `DoorMint` (Token-2022)

Built from Token-2022 sources:

- 165-byte base, padded (`interface/src/extension/mod.rs`, `BASE_ACCOUNT_LENGTH = Account::LEN`);
- 1-byte AccountType;
- TLV entries, each with a 2-byte type and 2-byte length;
- MetadataPointer: 64 bytes;
- PermissionedBurnConfig: 32 bytes (`interface/src/extension/permissioned_burn/mod.rs`);
- TokenMetadata, Borsh-encoded: `update_authority 32, mint 32, name, symbol,
  uri, additional_metadata` (token-metadata `interface/src/state.rs`).

Configuration:

| field | value |
| --- | --- |
| decimals | 6 |
| `mint_authority` | Room PDA |
| `freeze_authority` | None |
| MetadataPointer | authority None, address = the mint itself |
| PermissionedBurn | authority = Room PDA |
| TokenMetadata `update_authority` | None after creation, so metadata is immutable |
| `additional_metadata` | `[("room", <room pubkey>), ("door", <index>)]` |

Limits: name ≤ 32 bytes, symbol ≤ 10 bytes, URI ≤ 200 bytes. There is no
MintCloseAuthority, so a mint can never be closed (Ruling 3).

### Fees in `Config`

`fee_bps`, the four share fields, `door_fee_lamports`,
`door_fee_reserve_bps`, `door_fee_founder_bps`, `room_fee_lamports`,
`convert_fee_lamports`, the curve defaults (`x0`, `y0`, `s1`), `paused`, and
`admin` / `protocol_fee_recipient`.

- Trade fee parameters affect **new rooms only**.
- The door, room and convert fees are read when the instruction runs.

---

## 2. Curve shape

### Candidates and calibration

All five candidates pass through the same two points, so the first 85 SOL
behaves comparably:

- the opening price of 4.1938e-6 $/token at reserve 0;
- pump.fun's graduation price of 6.1632e-5 at reserve $12,750.80.

The candidates:

- **A. Constant product with virtual reserves.** pump.fun parameters, then an
  internal constant-product pool after 85 SOL. This is the curve in
  DESIGN.md. With these parameters, price is **not**
  exactly continuous at the switch: the curve side gives `K0/YG² = 6.1632e-5`
  and the pool side `R1/206.9M = 6.1628e-5`, a −0.0068% step. DESIGN.md's
  "continuous" was rounded.
- **B1 and B2. Power curves.** `p = p0 + a·q^n` with n = 1 and n = 2.
- **C1. Piecewise: pump.fun curve to 85 SOL, then linear price.** The joint is
  C¹, meaning price and slope both match at 85 SOL.
- **C2. Piecewise flattening.** Like C1, but the slope is divided by 4 at $1M
  of reserve and again at $10M.

### Price impact

Marginal price after the trade vs before; fees excluded.

| reserve | A buy $100 / $1k / $10k / $100k | B1 | B2 | **C1** | C2 |
|---|---|---|---|---|---|
| $10k | 1.38% / 14.3% / 248% / 10,433% | 0.50% / 4.85% / 41.2% / 231% | 0.71% / 7.01% / 62.9% / 423% | 1.38% / 14.3% / 132% / 587% | same as C1 |
| $100k | 0.20% / 2.01% / 21.0% / 300% | 0.05% / 0.50% / 4.88% / 41.4% | 0.07% / 0.68% / 6.66% / 59.7% | 0.05% / 0.54% / 5.32% / 44.6% | same as C1 |
| $1M | 0.02% / 0.20% / 2.01% / 21.0% | 0.00% / 0.05% / 0.50% / 4.88% | 0.01% / 0.07% / 0.67% / 6.58% | 0.01% / 0.05% / 0.50% / 4.92% | 0.00% / 0.01% / 0.13% / 1.25% |
| $10M | 0.00% / 0.02% / 0.20% / 2.01% | 0.00% / 0.00% / 0.05% / 0.50% | 0.00% / 0.01% / 0.07% / 0.67% | 0.00% / 0.01% / 0.05% / 0.50% | 0.00% / 0.00% / 0.01% / 0.10% |
| $50M | 0.00% / 0.00% / 0.04% / 0.40% | 0.00% / 0.00% / 0.01% / 0.10% | 0.00% / 0.00% / 0.01% / 0.13% | 0.00% / 0.00% / 0.01% / 0.10% | 0.00% / 0.00% / 0.01% / 0.05% |

**Opening trades**, which decide the sniping profile:

| curve | $100 at reserve $0 | $1k at $0 | $10k at $0 |
|---|---|---|---|
| A, C1, C2 | 4.49% | 49.4% | 938% |
| B1 | **63.9%** | 323% | 1,202% |
| B2 | 2.57% | 128% | 1,137% |

### Price level, market cap and reserve ratio

Notional market cap is price × tokens outstanding.

| reserve | A: price × / mcap / mcap÷reserve | B1 | B2 | **C1** | C2 |
|---|---|---|---|---|---|
| $100k | 61.5× / $3.69M / 36.9× | 2.8× / $195k / 2.0× | 4.1× / $290k / 2.9× | 4.6× / $369k / 3.7× | same as C1 |
| $1M | 6,150× / $378M / 378× | 8.8× / $1.98M / 2.0× | 19.4× / $2.98M / 3.0× | 15.2× / $2.59M / 2.6× | same as C1 |
| $10M | 615,029× / $37.9B / 3,790× | 27.9× / $19.9M / 2.0× | 90× / $30.0M / 3.0× | 48.1× / $21.9M / 2.2× | 27.4× / $16.3M / 1.6× |
| $50M | 15.4M× / $948B / 18,952× | 62.5× / $99.9M / 2.0× | 264× / $150M / 3.0× | **108× / $104M / 2.1×** | 36.5× / $67.3M / 1.3× |

"Price ×" is relative to the price at $12.75k of reserve.

**Reserve held at a given notional mcap:**

| mcap | A | B1 | B2 | C1 | C2 |
|---|---|---|---|---|---|
| $1M | $52.7k (5.3%) | $505k (50.5%) | $338k (33.8%) | $334k (33.4%) | $334k (33.4%) |
| $100M | $515k (0.51%) | $50.0M (50.0%) | $33.4M (33.4%) | $47.9M (47.9%) | $73.3M (73.3%) |
| $1B | $1.63M (0.16%) | $500M (50.0%) | $333M (33.3%) | $493M (49.3%) | $614M (61.4%) |

### Can a seller always exit?

Yes, on every curve. The reserve equals the curve integral `R(q)`, so selling
all outstanding tokens returns `R(q)`. In curve A, $2,638 stays locked in the
internal pool. Average-price slippage for selling 10% of the reserve in one
trade:

| curve | slippage at 10% of reserve |
|---|---|
| A | 10.0% at every level from $100k up (constant product: slippage equals the fraction sold) |
| B1 | 2.6% |
| B2 | 3.4% |
| C1 | 2.6–2.8% (6.9% at $10k, where it is still the pump.fun curve) |
| C2 | 2.0% at $10M, 1.4% at $50M |

### Recommendation: C1

1. **The opening is identical to pump.fun.** A first $100 buy moves price
   4.5%, which is the same sniping profile as today. B1's first $100 buy moves
   it 64%.
2. **The reserve ratio stays bounded.** Notional mcap is 2.1–3.7× reserve from
   $100k up to $50M. The worst point anywhere is 4.48×, at about $23.7k of
   reserve just after the junction (a 4,000-point scan in reserve). Curve A
   reaches 18,952× at $50M, quoting $948B of market cap on $50M of money; that
   is the "absurd ratio" failure. In C1 at least 22% of notional mcap is
   backed everywhere, and at least 27% from $100k up.
3. **Price rises without going vertical.** From 85 SOL to $50M of reserve,
   price rises 108×; curve A rises 15.4 million×. A $100k buy moves C1 4.9% at
   $1M of reserve and 0.10% at $50M.
4. **Exits stay cheap.** Selling 10% of the reserve costs about 2.6% average
   slippage, against 10% on constant product.
5. **It is cheap on-chain.** Segment 1 needs one division. Segment 2 needs one
   integer square root. There is one junction and no third segment to test.

C2 trades upside for depth: price rises 36× instead of 108× from 85 SOL to
$50M. It adds two more junctions. If the product wants big rooms to feel
flatter, revisit it later; not in v1.

### Recommended curve, exact definition (C1)

Parameters (defaults, copied into `Room` at creation):

| parameter | value |
| --- | --- |
| `x0` | 30,000,000,000 lamports |
| `y0` | 1,073,000,000,000,000 base units |
| `s1` | 793,100,000,000,000 base units |
| `Y = y0 − s1` | 279,900,000,000,000 |
| `K0 = x0·y0` | 3.219×10²⁵ (fits u128) |

**Reserve function.** This *is* the curve; every amount the curve owes is a
difference of it:

```
R(q) = floor( K0 / (y0 − q) ) − x0                    for q ≤ s1
R(q) = floor( K0·(Y² + Y·d + d²) / Y³ ) − x0          for q > s1, d = q − s1
```

- Both branches equal `floor(K0/Y) − x0` at `q = s1`, so R is continuous.
- R is non-decreasing, and R(0) = 0 because `K0/y0 = x0` exactly.
- Segment 2 is the C¹ linear-price continuation:
  `p(q) = K0·(Y + 2d)/Y³` lamports per base unit, with slope `2·K0/Y³`, the
  constant-product slope at `s1`.
- Intermediates need U256: `K0·d²` reaches about 10⁶⁴ for d near the u64
  limit. Results are u64.

**Marginal price**, for display and events only. It is never used to settle:
`K0/(y0−q)²` in segment 1 and `K0·(Y+2d)/Y³` in segment 2.

**Inverse for buys.** For a target `T = R(q) + n`, find the largest `q'`
with `R(q') ≤ T`:

- **Segment 1** (if `T ≤ R(s1)`): `q' = y0 − floor(K0/(T + x0 + 1)) − 1`,
  capped at `s1`. This is exact, because
  `floor(K0/(y0−q')) ≤ T+x0` ⇔ `y0 − q' > K0/(T+x0+1)`.
- **Segment 2:**
  1. Let `A = (T + x0 + 1)·Y³`.
  2. Estimate `d̂ = floor((−Y + isqrt(4·A/K0 − 3·Y²))/2)`.
  3. Adjust: increment while `K0·(Y² + Y(d̂+1) + (d̂+1)²) < A`; decrement while
     `K0·(Y² + Yd̂ + d̂²) ≥ A`.
  4. Fail the instruction if more than 2 adjustments are needed. That
     indicates an arithmetic bug.
  5. Set `q' = s1 + d̂`.

The post-condition, which must be asserted, is `R(q') ≤ T < R(q'+1)`.

Hard limit: `R(q)` must fit in u64 lamports. That means q up to about
3.5×10¹⁸ base units (3.5×10¹² tokens), at about 1.8×10¹⁰ SOL of reserve. It
is unreachable in practice.

**Reserve outside the curve.** Lamports sent to RoomVault from outside the
program are ignored: `room.reserve` tracks only program-credited lamports, and
**price is computed from `q` only, never from any account balance.**

---

## 3. Buy and sell instruction flow

Notation:

- `q = room.circulating + room.retired`;
- `R` is the reserve function of §2;
- `b = fee_bps`; the shares are `c, f, r` = creator, founder and reserve bps
  of the fee, and the protocol takes the remainder.

### Fee split helper

`split(F)`:

- `cr = floor(F·c/10⁴)`
- `fo = floor(F·f/10⁴)`
- `rs = floor(F·r/10⁴)`
- `pr = F − cr − fo − rs` (the protocol absorbs rounding dust)

### Retirement helper

`retire(rs)`:

1. `q0 = room.circulating + room.retired`.
2. Find the largest `q1` with `R(q1) ≤ R(q0) + rs`, using the §2 inverse.
3. `room.retired += q1 − q0`.
4. `room.reserve += rs`.
5. `room.reserve_share_total += rs`.

It buys curve position with fee lamports and mints nothing. This is how the
reserve share raises the price for every holder. A plain donation would change
nothing, because price depends only on `q`.

### `buy(lamports_in: u64, min_tokens_out: u64)`

Accounts: user (signer, writable), config, room (w), room_vault (w),
fee_vault (w), door (w), door_mint (w), user_ata (w; created idempotently in a
preceding instruction), token_2022, system_program, event_authority, program.

1. **Validate.**
   - `!paused`;
   - `door.room == room` and `door.mint == door_mint`;
   - PDA seeds are correct;
   - `user_ata` belongs to the user and `door_mint`;
   - `lamports_in > 0`.
2. **Fee on top.**
   - `n = floor(lamports_in · 10⁴ / (10⁴ + b))` is the curve amount.
   - `F = lamports_in − n` is the fee.
   - This gives `F ≥ n·b/10⁴`, and the reserve receives only `n`.
3. **Price from state.** Read `q`. Find the largest `q'` with
   `R(q') ≤ R(q) + n`. Set `d = q' − q`.
   - Require `d ≥ min_tokens_out` and `d > 0`.
   - Price comes from `room.circulating + room.retired` *before* this trade.
4. **Move lamports in.** Two system-program CPIs, signed by the user:
   - user → RoomVault: `n + rs`;
   - user → FeeVault: `cr + fo + pr`.
   - Here `(cr, fo, rs, pr) = split(F)`.
5. **Credit the reserve.**
   - `room.reserve += n`;
   - `room.circulating += d`;
   - `door.supply += d`.
6. **Mint.** Token-2022 `MintTo(door_mint → user_ata, d)`, signed by the Room
   PDA.
7. **Retire** with `retire(rs)`. It is computed at the post-trade position, so
   the buyer's tokens were priced without it.
8. **Accrue fees.**
   - `door.accrued += cr`;
   - `room.founder_accrued += fo`;
   - `room.protocol_accrued += pr`;
   - `door.buy_volume += n`, `door.trades += 1`;
   - `room.volume_gross += n`, `room.trades += 1`, `room.last_trade_at = now`.
9. **Assert I1–I4** (§9) on the touched state.
10. **Emit** `Trade{room, door, user, side: Buy, lamports_in, net: n, fee: F,
    tokens: d, q_after, price_after, reserve_after}`.

### `sell(tokens_in: u64, min_lamports_out: u64)`

Same accounts.

1. **Validate** as for buy. Require `tokens_in > 0`.
2. **Price from state.** Read `q`. The curve owes `g = R(q) − R(q − tokens_in)`
   for these tokens. `q − tokens_in ≥ room.retired` always holds, because
   `tokens_in ≤ door.supply ≤ circulating`.
3. **Fee from the seller's proceeds.**
   - `F = ceil(g·b/10⁴)`; the seller receives `g − F`.
   - Require `g − F ≥ min_lamports_out`.
4. **Burn.** Token-2022 permissioned `BurnChecked(user_ata, door_mint,
   tokens_in)`. The signers are the Room PDA (permissioned-burn authority) and
   the user (token owner).
5. **Move lamports out.** RoomVault is debited directly; the program owns it.
   - user receives `g − F`;
   - FeeVault receives `cr + fo + pr`;
   - `rs` stays in RoomVault.
   - RoomVault's balance falls by exactly `g − rs`.
6. **Debit the reserve.**
   - `room.reserve −= g`;
   - `room.circulating −= tokens_in`;
   - `door.supply −= tokens_in`.
7. **Retire** with `retire(rs)`.
8. **Accrue fees** as for buy, with `door.sell_volume += g`.
9. **Assert I1–I4. Emit.**

### The reserve invariant and every fee path

**I1 (solvency):**

```
room.reserve ≥ R(room.circulating + room.retired)
lamports(RoomVault) − rent(RoomVault) ≥ room.reserve
```

So every circulating token can be sold. Sequential full exit pays
`R(q) − R(retired) ≤ R(q) ≤ room.reserve`.

**Proof by path.** Write `S = room.reserve − R(q)`; I1 is `S ≥ 0`.

| path | Δ room.reserve | Δ R(q) | Δ S |
|---|---|---|---|
| buy, curve part | +n | R(q+d) − R(q) ≤ n | ≥ 0 |
| buy, fee F (cr, fo, pr) | 0 (paid user → FeeVault) | 0 | 0 |
| reserve share `rs` (buy, sell, door fee) | +rs | R(q1) − R(q0) ≤ rs | ≥ 0 |
| sell, curve part | −g, where g = R(q) − R(q−t) | −g exactly | 0 |
| sell, fee F (cr, fo, pr) | 0: paid out of the seller's `g` after the curve has paid exactly `g` | 0 | 0 |
| convert | 0 | 0 (q unchanged) | 0 |
| claims and sweeps | 0 (debit FeeVault only) | 0 | 0 |
| outside lamport donation to RoomVault | 0 (not credited) | 0 | 0; the second clause of I1 gets looser |

The RoomVault balance changes by exactly the `room.reserve` delta in every
row, so the second clause is preserved too.

**The forbidden pattern**, which must fail review: any instruction that debits
RoomVault by anything other than exactly `R(q) − R(q − t)` on a sell. Two
examples: paying the seller `g` and then transferring `F` out of RoomVault, or
taking a buy fee out of `n` after `n` was credited.

Two unit tests enforce this:

- `RoomVault` Δlamports == `room.reserve` Δ for every instruction;
- I1 is checked after a randomised sequence of 10⁴ operations.

---

## 4. Shared supply accounting

**Decision: mint-on-demand, not pre-minted.** C1 has no natural supply cap. At
$50M of reserve, 1.57×10¹⁰ tokens are outstanding (`outputs/curve_tables.md`).
Pre-minting would force a cap per door. Every door would then display
price × cap, a meaningless FDV.

The cost of mint-on-demand: every door mint keeps a **live mint authority** (the
Room PDA). Token scanners flag that. The only credible mitigation is making
the program immutable, or putting upgrades behind a timelock. Ruling 3
requires doors to keep working, so upgrades must not be able to break minting
either.

**Invariant S1:** `Σ_doors door.supply == room.circulating`. Two invariants
support it:

- **S2:** `door.supply == DoorMint.supply`;
- **S3:** `room.door_count == number of Door PDAs`.

What enforces them:

1. **Only the program can mint.** `mint_authority` is the Room PDA, which only
   this program can sign for. There is no other mint path.
2. **Only the program can burn.** Every door mint carries
   **PermissionedBurn with authority = the Room PDA**:
   - a standard Token-2022 `Burn` fails on such a mint
     (`program/src/processor.rs`, `process_burn`: "Standard burns cannot be
     used when the permissioned burn extension is present");
   - a permissioned burn requires the Room PDA's signature.
   - The extension is in the deployed mainnet Token-2022 program: its error
     string `"Permissioned burn authority is None; use the standard burn"` is
     present in programdata `DoU57AYu…HDTY`, read at slot 463,687,011
     (ELF sha256 `5e888b294bd1941bfc47107a73d5e40bb24fde0d639f69099e7920ad8b6413d9`).
     It ships in release tags `program@v11.0.0` and later.
   - Without it, any holder could burn door tokens directly, and S1 would
     drift: `Σ mint.supply < circulating`.
3. **Every mint or burn updates the counters atomically.** It updates
   `door.supply` and `room.circulating` in the same instruction, by the same
   amount. Transfers between users change neither.
4. **No freeze authority, no close authority.** Supply can never become
   stranded in a frozen account outside the counters.

**What wallets and scanners may not handle.** PermissionedBurn is recent. A
wallet's "burn token" button will fail on door tokens. Which wallets render
the extension correctly could not be verified.

**Off-chain audit.** S1 cannot be checked on-chain per trade without loading
every door mint. An indexer recomputes `Σ DoorMint.supply` against
`room.circulating` from account state, and should alert on any difference.
Under the rules above, a difference means a program bug.

---

## 5. Door-to-door conversion

**Yes.** A token of door A and a token of door B are the same claim on the
same curve at the same price. Without conversion, holders of a door they no
longer want would have to sell and rebuy, paying two curve fees.

**`convert(amount: u64)`**

Accounts: user (signer), room, door_a (w), door_b (w), mint_a (w),
mint_b (w), user_ata_a (w), user_ata_b (w; created idempotently), fee_vault
(w), token_2022, system_program.

1. Validate both doors belong to `room`. Require `door_a ≠ door_b` and
   `amount > 0`.
2. Permissioned `BurnChecked(user_ata_a, mint_a, amount)`. The signers are the
   Room PDA and the user.
3. `MintTo(mint_b → user_ata_b, amount)`, signed by the Room PDA.
4. `door_a.supply −= amount` and `door_b.supply += amount`. `room.circulating`,
   `retired`, `reserve` and `q` are all unchanged, so the price is unchanged.
5. Charge `convert_fee_lamports` (default **0**) from user to FeeVault, credited
   to `protocol_accrued`. No door or founder fee is charged, so conversion
   cannot farm fees.
6. Emit `Convert{room, from, to, user, amount}`.

Conversion credits no door's volume. Under Ruling 1, this is how a terminal
user who holds the terminal's door can move into the meme's door at no cost.

---

## 6. Door creation

**`open_door(name, symbol, uri, dev_buy_lamports: u64, min_tokens_out: u64)`.**
Anyone may call it, in any room, at any time. It also works while the room is
empty.

**Checks:**

- `name`: 1–32 bytes of UTF-8.
- `symbol`: 1–10 bytes, normalised to `[A-Z0-9]`:
  - uppercase;
  - strip everything else;
  - map 0→O, 1→I, 5→S, 8→B.
  - It must be non-empty after normalisation.
  - `TickerLock` for (room, normalised symbol) must not exist, and is created
    here.
- `uri`: ≤ 200 bytes, with prefix `https://`, `ipfs://` or `ar://`.
- **The image cannot be checked on-chain.** Only the URI string is stored.
  Lookalike images and lookalike names beyond ticker normalisation are not
  enforceable by the program.
- The room is not paused, and `door_count < u32::MAX`.

**Cost to the opener:**

- rent: 0.009166 SOL at max metadata, or 0.007496 SOL at minimum (locked
  forever);
- `door_fee_lamports`, default **0.5 SOL**, split:
  - 50% to the room reserve via `retire`;
  - 10% to the founder;
  - 40% to the protocol.

**Order of operations.** Token-2022 requires the extensions to be initialised
before `InitializeMint2`. Metadata initialisation resizes the account without
transferring lamports (`interface/src/extension/mod.rs`,
`alloc_and_serialize_variable_len_extension`, which calls `resize`), so the
mint must be pre-funded for its final size.

1. Create the `DoorMint` PDA account with space for the fixed extensions and
   lamports for the final size.
2. `MetadataPointer::Initialize`, pointing to itself with authority None.
3. `PermissionedBurn::Initialize` with authority = Room PDA.
4. `InitializeMint2` with decimals 6, mint authority = Room PDA and freeze
   None.
5. `TokenMetadata::Initialize`. The mint authority, the Room PDA, signs.
6. `UpdateField` ×2: `room` and `door`.
7. `UpdateAuthority` → None.
8. Create `Door` and `TickerLock`.
9. Collect the door fee and run `retire` on its reserve share.
10. `room.door_count += 1`.
11. Optional `dev_buy` through the new door, in the same instruction, so
    nobody can buy in between.

**`create_room(slug, uri, door0 …, dev_buy)`** does the same for door 0. It
also creates `Room`, `RoomVault`, `FeeVault` and `SlugLock`, and pays
`room_fee_lamports` (default 1 SOL, to the protocol). The caller becomes
`room.founder`.

**What stops 10,000 doors in one room** (`outputs/fee_model.md`):

- **The spam model.** A door with no traffic of its own earns only from buyers
  who choose among doors uniformly: random, confused, or an unranked list.
  - That share of volume, ρ, is unknown and is swept here.
  - Income per spam door is `0.30% × ρ × V / (D + m)`, where V is room volume,
    D is the honest doors already there and m is the spam doors.
  - Spam dilutes itself.
- **10,000 spam doors in a room with 10 honest doors:**

  | V | ρ | spam income | rent alone | 0.5 SOL fee + rent |
  |---|---|---|---|---|
  | $50M | 0.3 | $45.0k | $13.7k | $763.7k |
  | $10M | 0.3 | $9.0k | $13.7k | $763.7k |

  - Rent alone (0.009166 SOL per door) already makes the attack unprofitable
    at V ≤ $10M.
  - At V = $50M and ρ = 0.3, a door fee of **0.0208 SOL** on top of rent is
    enough.
  - The default 0.5 SOL exceeds that by 24×.
- **What the fee does not stop: a few spam doors in a big room.** The
  break-even fee for one extra no-traffic door is `0.30% × ρ × V / (D + 1)`.
  At V = $50M, ρ = 0.3 and D = 10 that is **$4.1k (about 27 SOL)**. At
  ρ = 0.05 it is $682 (about 4.5 SOL).
  - A door fee high enough to stop that would also price out every legitimate
    small creator.
  - Under Ruling 1, router doors are expected anyway.
  - **So there is no fee that stops small-scale door squatting in large
    rooms.** The 0.5 SOL default stops automated mass-spam and nothing more.

---

## 7. Fee split

All parameters are in bps. Trade fee shares are snapshotted per room.

| parameter | default | rate on volume | per $1M of room volume |
|---|---|---|---|
| `fee_bps` (on every buy and sell, on top) | 100 | 1.00% | $10,000 |
| `creator_share_bps` → the door the volume went through | 3000 | 0.30% | $3,000 (split across doors by routed volume) |
| `founder_share_bps` → room founder | 1000 | 0.10% | $1,000 |
| `reserve_share_bps` → `retire` (all holders) | 2000 | 0.20% | $2,000 of curve position retired |
| protocol (remainder) | 4000 | 0.40% | $4,000 |

| door creation | default | per door opened |
|---|---|---|
| `door_fee_lamports` | 0.5 SOL ($75) | — |
| `door_fee_reserve_bps` | 5000 | 0.25 SOL retired |
| `door_fee_founder_bps` | 1000 | 0.05 SOL to founder |
| protocol (remainder) | 4000 | 0.20 SOL |
| `room_fee_lamports` | 1 SOL | protocol |
| `convert_fee_lamports` | 0 | — |

- **What retirement is worth to a holder.** Retired reserve share is not
  payable to anyone. It raises price for all holders pro rata to their
  holdings. A holder with fraction h of circulating supply gains about
  `h × rs` in exit value. Because retired position counts in `q`, selling
  everything leaves `R(retired)` stranded in the reserve, as a burned LP
  would.
- **Wash trading.** The washer pays 1% per side and recovers 0.30% (plus 0.10%
  if they are also the founder). *(sim, synthetic: wash trading lost money at
  a 30% creator share unless trending signals counted raw volume.)*
- **Router capture.** Under Ruling 1, the $3,000 creator line is shared with
  router doors in proportion to the flow they route. See
  `DOOR_CREATOR_EARNINGS.md`.

---

## 8. Limits

| constraint | value | binding? |
|---|---|---|
| `door_count: u32` / door PDA index | 4,294,967,295 doors per room | **yes, the only hard on-chain cap** |
| `TickerLock` namespace (normalised, 1–10 chars, 32-symbol alphabet after confusable folding) | about 1.16×10¹⁵ | no |
| accounts per trade | buy/sell 12, convert 11, open_door about 14. Constant in the number of doors: a trade touches one door (convert two). The transaction lock limit is 64 accounts, or `MAX_TX_ACCOUNT_LOCKS` with the `increase_tx_account_lock_limit` feature (agave `runtime/src/bank.rs:3847`). | no |
| compute per instruction | Independent of door count. No instruction iterates doors. | no |
| per-block writable-account compute | `MAX_WRITABLE_ACCOUNT_UNITS = 24,000,000` CU per account per block (agave `cost-model/src/block_cost_limits.rs:33`). Every buy, sell, convert and open_door writes `Room`. | **binds throughput, not count** |
| per-block account data growth | `MAX_BLOCK_ACCOUNTS_DATA_SIZE_DELTA = 100,000,000` bytes (same file, line 37). A door adds 933 data bytes, so about 107,000 door creations per block network-wide. | no |

Room throughput is `24,000,000 / CU per instruction` trades per block.
**Instruction CU has not been measured**; no program has been built. At an
assumed 60k CU per buy, it would be 400 per block. Measure before quoting.

**Answer:** about **4.29 billion doors** per room. The binding constraint is
the u32 door index. In practice the binding constraints are economic (§6) and
off-chain: indexers enumerate doors per room by `getProgramAccounts` with a
`room` memcmp, whose cost grows with door count. Neither account size,
compute nor transaction size limits door count, because no instruction
touches more than two doors.

---

## 9. Invariants

Each one is checked in unit and property tests. I1–I4 and P1 are also
asserted at the end of every instruction that touches them.

1. **I1, solvency.** `room.reserve ≥ R(room.circulating + room.retired)`.
2. **I2, vault backing.** `lamports(RoomVault) − rent_min(RoomVault) ≥ room.reserve`.
3. **I3, exact vault movement.** For every instruction,
   `Δlamports(RoomVault) == Δroom.reserve`.
4. **I4, sell payout.** A sell of t debits `room.reserve` by exactly
   `R(q) − R(q − t)`, then credits it with `rs`.
5. **S1, supply conservation.** `Σ_doors door.supply == room.circulating`.
6. **S2.** `door.supply == DoorMint.supply` for every door.
7. **S3, no external supply change.** Every door mint has
   `mint_authority == Room PDA`, `freeze_authority == None`,
   PermissionedBurn authority == Room PDA, and no MintCloseAuthority.
8. **S4.** `room.retired` is non-decreasing.
9. **P1, price equality.** The price used for any trade through any door is
   a function of `(room params, q)` only. Test: the same trade through door A
   and door B from identical state gives identical `d` (buy) or `g` (sell).
10. **P2, conversion neutrality.** `convert` leaves `q`, `room.reserve`,
    `room.circulating` and all prices unchanged.
11. **P3, monotone price.** `R` is non-decreasing. A buy never lowers the
    price; a sell never raises it.
12. **P4, rounding direction.** A buy gets the largest `d` with
    `R(q+d) − R(q) ≤ n`, and never more. Property test against an
    arbitrary-precision rational reference: `R(q+d) ≤ R(q)+n < R(q+d+1)`.
13. **F1, fee conservation.** Per trade, `F == cr + fo + rs + pr`.
14. **F2, fee vault backing.**
    `lamports(FeeVault) − rent_min(FeeVault) ≥ Σ_doors door.accrued + room.founder_accrued + room.protocol_accrued`.
15. **F3, fee totals.** Lifetime fees charged == Σ claimed (doors, founder) +
    Σ accrued + protocol swept + protocol accrued + `room.reserve_share_total`.
16. **F4, fees on top.** On a buy, `room.reserve` increases by exactly `n + rs`,
    and `F = lamports_in − n ≥ n·b/10⁴`.
17. **D1, doors work for the life of the room** (Ruling 3). No instruction
    can close a `Door`, `DoorMint` or `TickerLock`, or change a door mint's
    authorities.
18. **D2, unique tickers.** At most one door per room per normalised symbol.

---

## 10. What a trader sees

**Price.** One price per room: the marginal price at `q`. It is identical
through every door. Every `Trade` event carries `price_after` and `q_after`,
so any indexer reconstructs the same series from any door.

**Chart.** The room chart: price from the events of all doors, in one series.
A door's page shows the room chart, plus that door's own volume, buyer count
and fees. Third-party charting needs program integration, because door
tokens have no pool. Without integration DexScreener-style sites show
nothing.

**In a wallet or terminal**, a door looks like an ordinary Token-2022 token:
name, ticker and image from metadata. It differs in these ways:

- **Mint authority is set.** It is the Room PDA, so scanners flag "can mint".
- **The PermissionedBurn extension is present.** Burn buttons fail.
- **Metadata `additional_metadata` holds `room` and `door`.** Anyone can verify
  a door by deriving `["door", room, index]` and checking `Door.mint` equals
  the mint.
- **No pool or price** until terminals and price APIs integrate the program.
- **Displayed market cap is misleading without integration.** A terminal
  computing price × mint supply shows only *this door's share* of the room.
  The room's notional mcap is `price × room.circulating`, 2.1–4.5× reserve
  on C1.
- **Holding two doors of one room shows as two lines.** Wallets don't group
  them. The first-party frontend groups them by room and offers `convert`.

**Exit value.** The first-party UI should show "sell all now: X SOL",
computed from `R`, next to the mark. On C1 the gap between the two is bounded:
notional mcap is at most 4.48× reserve. That does not hold on constant
product.
