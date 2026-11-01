# Room and doors: pre-minted supply, constant-product curve, DAMM v2 graduation — build spec

1 November 2026 revision: age-aware liveness, conservative trailing activity,
unified SlugLock release, mandatory matcher authorization and founder-share
plumbing defaulted to zero. The earlier
31 October owner rulings remain:

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
- founder-share plumbing is present but defaults to **0 bps**, so no founder fees accrue in v1;
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

### 0.C Program-v1 owner-approved corrections

Ordinary Token-2022 transfers can donate tokens into a vault without its
owner signing; holder burns can reduce mint supply. Exact raw-balance
equalities would therefore permit denial of service. The owner approved
surplus-tolerant accounting: balances cover program-tracked liabilities;
initial mint supply is exactly U and later supply may be below U. The
counterexamples and decision record are in `program/docs/CORRECTIONS.md`.

Only program counters determine prices, payouts and available inventory.
Token balances are read only for account validation, liability coverage and
exact movement checks. Unaccounted vault surplus stays locked: no instruction
sweeps, credits, retires or redistributes it. Audits reconcile external burns
and donations rather than calling every balance mismatch a program bug.

Room identifiers are high-entropy random u64 nonces chosen by the matcher,
included in the whole transaction signed by matcher and launcher. They are
not sequential and not derived from the slug hash. A collision fails atomically;
the client requests a fresh routing decision/signature with a new nonce.
Config stays read-only during creation. Room IDs are not enumerable;
indexers discover Rooms with `getProgramAccounts`, as they enumerate Doors.

The brief's lamport-delta test means ReserveVault, not the room-token
RoomVault. For an initialized reserve, exact lamport movement equals the
reserve-counter change; creation separately accounts for its initial rent
funding. `retire_pending` caps the amount before any transfer and marks
completion when the copied trigger is reached.

<!-- BEGIN GENERATED RENT CORRECTION -->
**Approved rent correction.** The old `(128 + bytes) × 6,960` model is stale. The owner approved `(128 + bytes) × 5,080` after direct rent-exemption RPC confirmation. These are `getMinimumBalanceForRentExemption` results, not account balances. The method has no context slot; finalized slot reads bracket each request.

| data bytes | raw minimum (lamports) | finalized slot before | finalized slot after |
|---|---|---|---|
| 0 | 650,240 | 464,037,171 | 464,037,172 |
| 165 | 1,488,440 | 464,037,175 | 464,037,178 |

Additional size checks are recorded at slots 464,036,284–464,036,304 in `outputs/narrative/current_rent.json`; the confirmation is in `rent_confirmation.json`. The current schema's derived totals are:

| quantity | old rate on revised schema | verified rate on revised schema |
|---|---|---|
| launch rent, lamports | 37,604,880 | 27,447,240 |
| graduation rent, lamports | 24,680,160 | 18,013,680 |

All current rent-dependent spec figures are regenerated. The trigger remains a Config value snapshotted into each Room; a later rent/default change does not rewrite an old room's curve or graduation trigger. Runtime graduation uses the rent sysvar, not this calibration coefficient.
<!-- END GENERATED RENT CORRECTION -->

### 0.A Conflicts found in this revision's rulings

Rulings 1 (free launch), 3 (no ticker locks) and 4 (room token inherits
door 0) conflict with nothing verified. Two rulings needed an explicit
choice.

1. **Rent-funded graduation changes the handoff reserve.** Seeding R* with
   every unsold token after taking out rent creates a price drop. Preserve
   continuity by seeding only `N = floor(R* · (V_tok − room.sold)² / K)` and
   retiring the remaining unsold tokens. The curve parameters stay unchanged.
   Current figures, including the rejected all-remaining-tokens alternative,
   are generated in §2. Trigger and seed quantities are room-specific.
2. **SlugLock expiry is unified with narrative routing.** A room's lock can
   be released or taken over exactly when the holder fails the gate in
   [NARRATIVE_DETECTION.md §4](NARRATIVE_DETECTION.md#4-liveness-gate-hard-rule).
   This applies in every room status, including graduated pools; direct pool
   trading is observed through the cumulative LP-fee counter. There is no
   independent SlugLock timer or reserve threshold.
3. **Trailing activity needs history.** Lifetime `volume_gross` and a single
   last-trade timestamp cannot establish a trailing window. The previous
   current/previous-window fallback could retain activity beyond the window.
   The gate now uses a conservative hourly history and dates pool increments
   to the start of their observation interval. The generated account sizes
   include this bounded history; it does not fit in the original reserve bytes.

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
   - **Updated by 0.A.1:** the trigger is a room snapshot of the Config
     graduation budget. The current default and matched seed are generated
     in §2; older rooms retain the old trigger and use their own sold state.
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

<!-- BEGIN GENERATED RENT FORMULA -->
Rent model verified in `outputs/narrative/rent_confirmation.json`: `(128 + data_bytes) × 5,080` lamports. Runtime instructions use the rent sysvar; this coefficient is a recorded calibration.
<!-- END GENERATED RENT FORMULA -->

Exact packed field offsets are in `outputs/account_sizes.md`.

**Accounts created with each room** (except the shared `Config`):

<!-- BEGIN GENERATED ROOM ACCOUNTS -->
| account | seeds / derivation | data bytes | rent (lamports) |
|---|---|---|---|
| Config | `["config"]` | 248 | 1,910,080 |
| Room | `["room", room_id u64 LE]` | 1315 | 7,330,440 |
| ReserveVault | `["reserve", room]` | 0 | 650,240 |
| FeeVault | `["fees", room]` | 0 | 650,240 |
| GradPayer (System-owned) | `["grad_payer", room]` | 0 | 650,240 |
| SlugLock | `["slug", derived_identity_hash]` | 17 | 736,600 |
| RoomMint | `["room_mint", room]` | 616 | 3,779,520 |
| RoomVault | `["room_vault", room]` | 165 | 1,488,440 |
| RetiredVault | `["retired", room]` | 165 | 1,488,440 |
| FeeWsol | `["fee_wsol", room]` | 165 | 1,488,440 |
<!-- END GENERATED ROOM ACCOUNTS -->

**Accounts created with each door:**

<!-- BEGIN GENERATED DOOR ACCOUNTS -->
| account | seeds / derivation | data bytes | rent (lamports) |
|---|---|---|---|
| Door | `["door", room, index u32 LE]` | 328 | 2,316,480 |
| DoorMint (max metadata) | `["door_mint", room, index]` | 638 | 3,891,280 |
| DoorVault | `["door_vault", door]` | 165 | 1,488,440 |
| DoorRoomVault | `["door_room_vault", door]` | 165 | 1,488,440 |
| trader's Token-2022 ATA | `ATA program` | 170 | 1,513,840 |
<!-- END GENERATED DOOR ACCOUNTS -->

**Generated totals** (USD uses an explicit quoting assumption):

<!-- BEGIN GENERATED RENT TOTALS -->
| item | lamports | SOL | USD at assumed $150/SOL |
|---|---|---|---|
| per room, excluding door accounts | 18,262,600 | 0.018263 | $2.74 |
| per door, max metadata | 9,184,640 | 0.009185 | $1.38 |
| per door, minimum metadata | 7,919,720 | 0.007920 | $1.19 |
| launch room + door 0, max metadata | 27,447,240 | 0.027447 | $4.12 |
| graduation rent, paid from reserve | 18,013,680 | 0.018014 | $2.70 |
<!-- END GENERATED RENT TOTALS -->

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

**`Config`** (packed Borsh; generated size and rent above). Existing curve and fee
fields retain their order. Replace the old reserve bytes with
`matcher_authority: Pubkey` and the gate thresholds
`live_min_reserve_lamports`, `live_max_idle_seconds`, `live_new_seconds`,
`live_min_volume_lamports`, `pool_min_window_lp_fee` (all u64).
The matcher key is mandatory; there is no unsigned or `None` bypass.
Admin key rotation is recorded on-chain. Gate thresholds are shared by
routing, takeover and release, and changes are admin actions logged on-chain.
The trailing window and bucket size are fixed by the versioned schema.
Curve and trade-fee parameters are copied into each room and remain immutable.
Append `founder_share_bps: u16`, default **0**, without moving existing fields.
Validate `door_share_bps + founder_share_bps <= 10,000` and each share in
`0..=10,000`. Changes to these Config values affect newly created rooms only.
The Config update instruction accepts `founder_share_bps` alongside the
other fee parameters, requires the admin signature, validates the bounds and
logs the change on-chain. `create_room` checks the share bounds before
creating accounts or executing an optional first buy.

**`Room`** (packed Borsh; generated size and rent above). Keep the existing curve, vault,
fee, volume and timestamp fields. Replace launcher slug storage with the
identity hash. Store `fee_ckpt: u128`, `fee_ckpt_ts: i64` and the tagged
hourly `liveness_buckets` ring described in detection §4. The bucket amount
is u128 and start is i64; account_sizes.py gives the exact packed offsets.
There is no last-window fallback. Curve trades increment both `volume_gross`
and the current bucket; on graduation clear volume buckets and initialize
fee history from the pool's actual cumulative counter. Live checks use
read-only virtual checkpoint evaluation; the permissionless checkpoint
instruction persists the same result. A stale interval is discarded rather
than moved into a recent bucket.

Append `founder: Pubkey`, `founder_accrued: u64` (SOL lamports),
`founder_accrued_wsol: u64` (WSOL base units), and `founder_share_bps: u16`.
The founder is the immutable `create_room` launcher; both accrued counters
start at zero, and the share is an immutable snapshot of Config at creation.
The separate WSOL counter mirrors door fee accounting because graduated
sells collect program fees into `FeeWsol`; it avoids unwrapping a shared vault.
All earlier field offsets remain unchanged; exact appended offsets and the
additional launch rent are regenerated in `outputs/account_sizes.md`.

**`Door`** (328 bytes). Backing, vaults and fee fields are unchanged.
Use its reserve bytes for `matcher_version: u16`, `rule: u8`, `face: u32`,
leaving the remainder reserved. `RoomCreated` and `DoorOpened` include these
text-routing fields. V1 neither computes nor transmits image hashes/digests,
including shadow evidence. The matcher signs these instruction arguments
along with the whole routing transaction. The user-supplied metadata URI
still defines the mint image; the routing service never fetches it.

## 2. Curve

The following is the **current default calibration**, regenerated from the
verified rent model. `Config.graduation_trigger_lamports` is configurable;
`create_room` copies it and the curve constants into the new Room. Updating
Config affects future rooms only. No running instruction substitutes the
newest default for a room's copied trigger.

<!-- BEGIN GENERATED CURVE FIGURES -->
<!-- generated by scripts/curve_identities.py -->

### Identities (exact rational arithmetic)

| identity | value | check |
|---|---|---|
| V_tok = f²S/(2f−1) | 1,073,025,605.5954 | brief's 1,073,025,606 is this rounded up by 0.4046 |
| V_sol = R*(2f−1)/(1−f) (as written in the brief) | 240.826486 SOL | **does not give 30 SOL: inverted** |
| V_sol = R*(1−f)/(2f−1) (correct form) | 30.000853 SOL | gives 30.0009 SOL |
| FDV at graduation = R*/(1−f) | 410.8265 SOL | holds |
| market cap / reserve at graduation = 1/(1−f) | 4.8333× | holds |
| opening → graduation price multiple = (f/(1−f))² | 14.6938× | holds when V_sol and V_tok satisfy both closed forms |
| cost to lift the pool price +10% = (√1.1 − 1)·x | 4.8809% of the pool's SOL side x | holds for any constant-product pool; independent of f |

### Junction between curve and pool, by parameter set

| parameters | tokens sold at switch | reserve at switch (SOL) | tokens left for the pool | price step |
|---|---|---|---|---|
| pump.fun published: V_sol 30, V_tok 1,073,000,000, switch at s = fS | 793,100,000.000 | 85.005359 | 206,900,000.000 | -0.0067611486% |
| V_sol 30, V_tok 1,073,025,606, switch at s = fS | 793,100,000.000 | 84.997583 | 206,900,000.000 | +0.0000001068% |
| V_sol 30, V_tok 1,073,025,606, switch at R = 85 SOL (brief's trigger) | 793,105,882.696 | 85.000000 | 206,894,117.304 | +0.0014836023% |
| V_sol 30.000852995 (derived so R = 85 at s = fS), V_tok 1,073,025,606, switch at R = 85 | 793,100,000.000 | 85.000000 | 206,900,000.000 | +0.0000001068% |
| exact closed forms (V_sol, V_tok both exact), switch at R = 85 | 793,100,000.000 | 85.000000 | 206,900,000.000 | +0.0000000000% |

### Chosen integer parameters (program units)

| parameter | value |
|---|---|
| V_sol | 30,000,852,995 lamports (30.000852995 SOL) |
| V_tok | 1,073,025,606,000,000 base units (1,073,025,606 tokens, 6 decimals) |
| K = V_sol·V_tok | 32,191,683,465,476,789,970,000,000 (fits u128: True) |
| R* | 85,000,000,000 lamports |
| q_g (largest q with R(q) ≤ R*) | 793,099,999,999,525 base units = 793,099,999.999525 tokens |
| R(q_g) | 85,000,000,000 lamports (R* − R(q_g) = 0 lamports) |
| room tokens left to seed the pool, S − q_g | 206,900,000,000,475 base units = 206,900,000.000475 tokens |
| price step at the switch (integer rounding) | +0.000000105546% |

### Graduation trigger raised to R* + graduation rent

| quantity | value |
|---|---|
| graduation rent (DAMM v2 accounts, from account_sizes.py) | 18,013,680 lamports |
| trigger T = R* + rent | 85,018,013,680 lamports (85.018013680 SOL) |
| q_g at T (largest q with R(q) ≤ T) | 793,143,840,548,785 base units = 793,143,840.548785 tokens |
| R(q_g) | 85,018,013,680 lamports (T − R(q_g) = 0) |
| room tokens left in RoomVault, U − q_g | 206,856,159,451,215 base units |
| literal reading: seed R* with all remaining tokens, price step | -0.010133% |
| chosen: seed R* with N = floor(R*·(V_tok − q_g)²/K) tokens | N = 206,835,198,005,974 base units = 206,835,198.005974 tokens |
| chosen: unsold tokens retired, U − q_g − N | 20,961,445,241 base units = 20,961.445241 tokens |
| chosen: price step (pool opens at or above the curve's closing price by < 1 base unit) | +4.146e-13% |
| alternative: re-derive V_sol (V_tok fixed) to seed all remaining tokens | V_sol = 29,995,027,020 lamports; seed 206,815,982,822,911 base units; step -0.000000000342% |

### Price impact of a buy (marginal price after vs before; fees excluded)

Curve phase below 85 SOL of reserve; pool phase from 85 SOL (the pool's SOL side x starts at R* = 85 and grows with net buying; K' = R* x N). Rows at and above 85 SOL are pool-phase. Pool fee excluded.

| reserve / pool SOL side | buy 0.5 SOL | 5 SOL | 50 SOL | 500 SOL | FDV (SOL) | FDV / reserve |
|---|---|---|---|---|---|---|
| 1 SOL | 3.25% | 34.86% | 582.70% | 47,718.64% | 30 | 29.9× |
| 10 SOL | 2.52% | 26.56% | 406.24% | 29,662.64% | 50 | 5.0× |
| 50 SOL | 1.25% | 12.89% | 185.99% | 8,553.82% | 199 | 4.0× |
| 84 SOL | 0.88% | 11.55% | 152.92% | 4,704.89% | 404 | 4.8× |
| 85 SOL | 1.18% | 12.11% | 152.25% | 4,636.68% | 411 | 4.8× |
| 500 SOL | 0.20% | 2.01% | 21.00% | 300.00% | 14,220 | 28.4× |
| 5,000 SOL | 0.02% | 0.20% | 2.01% | 21.00% | 1,421,990 | 284.4× |
| 50,000 SOL | 0.00% | 0.02% | 0.20% | 2.01% | 142,199,031 | 2,844.0× |

### Depth: SOL needed to move the price (fees excluded)

| reserve / pool SOL side | +1% | +5% | +10% | −1% sale | −5% sale | −10% sale |
|---|---|---|---|---|---|---|
| 10 SOL | 0.200 | 0.988 | 1.952 | 0.201 | 1.013 | 2.053 |
| 50 SOL | 0.399 | 1.976 | 3.905 | 0.401 | 2.026 | 4.105 |
| 85 SOL | 0.424 | 2.099 | 4.149 | 0.426 | 2.152 | 4.362 |
| 500 SOL | 2.494 | 12.348 | 24.404 | 2.506 | 12.660 | 25.658 |
| 5,000 SOL | 24.938 | 123.475 | 244.044 | 25.063 | 126.603 | 256.584 |
| 50,000 SOL | 249.378 | 1,234.754 | 2,440.442 | 250.628 | 1,266.028 | 2,565.835 |

In the curve phase x = V_sol + R includes the virtual SOL, so depth there is not backed by real SOL beyond R.
<!-- END GENERATED CURVE FIGURES -->

### Exact integer definition and the per-room handoff

Units are lamports and base units. With the room's copied constants:

```
K = room.v_sol_lamports * room.v_tok
R(q) = floor(K / (room.v_tok - q)) - room.v_sol_lamports
T = room.graduation_trigger_lamports
```

- `R(0) = 0`; R is non-decreasing. Price is computed from sold state, never
  an account's raw balance.
- A buy of net fee-base lamports n computes the largest q' with
  `R(q') <= R(q) + n`:
  `q' = V_tok - floor(K / (R(q) + n + V_sol + 1)) - 1`.
- A sell of t tokens pays `g = R(q) - R(q-t)` before program fees.
- The crossing buy caps at the room's T. At completion the room stops curve
  trading until its permissionless graduation.
- Compute the matched pool token amount from **that room's actual sold
  state**: `N = floor(room.r_star * (room.v_tok - room.sold)^2 / K)`.
  Seed the pool with `room.r_star` and N; retire `U - room.sold - N`.
- The pool price matches the closing curve price to integer rounding. Depth
  changes because virtual SOL disappears. The generated tables show the
  current example; none of their default quantities are program constants.

<!-- BEGIN GENERATED GRADUATION SNAPSHOTS -->
<!-- generated by scripts/graduation_scenarios.py -->
# Config trigger snapshots survive a rent/default change

| room snapshot | trigger (lamports) | sold base units | pool seed base units | retired base units | rent budget | current rent | budget left after rent |
|---|---|---|---|---|---|---|---|
| old room, old trigger | 85,024,680,160 | 793,160,061,522,864 | 206,811,223,802,753 | 28,714,674,383 | 24,680,160 | 18,013,680 | 6,666,480 |
| new room, current default | 85,018,013,680 | 793,143,840,548,785 | 206,835,198,005,974 | 20,961,445,241 | 18,013,680 | 18,013,680 | 0 |

Existing rooms retain their copied trigger, curve constants and sold state. The seed is computed from that state, never from the newest Config default. Lower runtime rent leaves budget dust for the existing graduation dust path. If future rent exceeds a room's budget, protocol-accrued fees/top-up cover the shortfall or the transaction fails atomically for retry; no trigger rewrite or extra reserve debit is allowed. These are exact model checks, not program execution tests.
<!-- END GENERATED GRADUATION SNAPSHOTS -->

## 3. Instructions

**Common rules.**

- Use the room's snapshots: `b = fee_bps` (default 100),
  `d = door_share_bps` (default 6000), `f = founder_share_bps` (default **0**).
- Fees are always charged on top. On a buy the user pays `lamports_in`; the
  curve or pool receives `n = floor(lamports_in · 10⁴ / (10⁴ + b))`, and
  `F = lamports_in − n` is the fee.
- On a sell, `F = ceil(g · b / 10⁴)` comes out of the seller's gross proceeds
  `g`, after the curve or pool has paid exactly `g`.
- **Fee split** `split(F, route)`:
  - `door = floor(F · d / 10⁴)`;
  - `founder = floor(F · f / 10⁴)`;
  - `protocol = F − door − founder` (including all rounding remainder);
  - on the room-token route, `door` goes to `pending_reserve` instead of a
    door; the founder share applies to both program routes and both trade directions.
  - Credit founder SOL fees to `room.founder_accrued`, and founder WSOL fees
    to `room.founder_accrued_wsol`. Widen multiplication to u128 and use
    checked u64 accruals; an overflow fails atomically.
  - This partitions the existing program fee; it adds no surcharge and takes
    nothing from the reserve or DAMM LP fees. With `f = 0`, the split is
    exactly the existing 60/40, including its integer rounding.
- **Asserting the backing invariant.** Every instruction that touches a door
  ends by asserting B1 (§4) for each door it touched. It reads the two vault
  balances from the token accounts, not from cached fields.

### `create_room(room_id, door0_name, door0_symbol, door0_uri, first_buy_lamports, min_tokens_out, matcher_evidence)`

**Signers:** launcher and the exact `Config.matcher_authority`. The matcher
co-signs the whole transaction message: instruction choice, target accounts,
metadata, first-buy and slippage limits, evidence and recent blockhash. Changing
any of these invalidates authorization; blockhash expiry bounds replay. The
launcher signs the same previewed transaction. Launching charges rent and
transaction fees, with room and door fees defaulting to zero.

Both launch instructions execute at transaction level, not through a CPI
proxy. This makes the on-chain routing accounts and arguments the exact
instruction payload co-signed by the matcher, rather than letting another
program reinterpret a propagated signer.

`room_id` is a matcher-chosen CSPRNG u64 nonce included in that signed
message, never a slug-derived value or a sequential counter. Config is
read-only. An occupied Room PDA is a clean atomic collision failure; a retry
uses a fresh matcher decision/signature and new nonce, not a modified signed
transaction. Indexers discover room accounts rather than walking an ID range.

**Identity and routing checks, before account creation:**

- There is no slug argument. Derive
  `identity = sha256(floor_fold(symbol) || 0x00 || floor_fold(name))` from
  door 0's raw metadata, using the deterministic ASCII byte fold in detection
  §3.1. `SlugLock` seeds are `["slug", identity]`.
- Validate an existing lock and its holder `Room` from the stored id/PDA.
  If the holder passes the single liveness gate, reject creation: the launch
  must be a door of that holder. If the holder fails, take over atomically.
  Read and validate its DAMM pool when graduated. If no lock exists, create it.
- Initialize a genuinely new room with the execution clock; never reset the
  previous holder's `created_at`. A failed creation rolls back lock changes.

**Creates:**

- `Room`, `ReserveVault`, `FeeVault`;
- `GradPayer`, funded with its own rent-exempt minimum only;
- `SlugLock` (derived identity; create if absent, otherwise re-point only from a dead holder);
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
     `graduation_trigger_lamports` and `founder_share_bps`;
   - `founder = launcher`, `founder_accrued = founder_accrued_wsol = 0`.
     Founder is not a caller-selected instruction argument. Emit the founder
     and snapshotted share in `RoomCreated` before the optional first buy.
4. **Door 0:** the `open_door` steps below, with the same name, symbol and
   URI. The room token and door 0 are twins.
5. **Optional first buy** through door 0.

Founder fees are present but zero by default. This grants no mint, freeze,
metadata, matcher, routing or pool-LP authority. The room token still carries
the launcher's immutable metadata. Door 0's fee recipient may change under
the existing door instruction without changing the room's founder.

### `open_door(name, symbol, uri, first_buy_lamports, min_tokens_out, matcher_evidence)`

**Allowed:** any status: before graduation, while complete, and after
graduation.

**Checks:** name 1–32 bytes, symbol 1–10 bytes, URI ≤ 200 bytes. **There
is no uniqueness check:** names, symbols and images may repeat freely within a
room.

**Signers:** opener and the exact `Config.matcher_authority`, co-signing
its routing decision in the transaction message. The target `Room` is an
instruction account selected by that signed decision; the opener cannot choose
or substitute another room. The opener pays rent and transaction fees; the
door fee defaults to zero.

**Routing checks:** evaluate the shared liveness gate on the target at
execution. Derive the candidate identity and read its SlugLock. If a distinct
holder is live, reject the route: exact floor wins. Verify and read a distinct
holder's room, and each corresponding DAMM pool when graduated. All metadata
may repeat within the selected room. These checks precede the optional first
buy and roll back atomically if it fails. `create_room`'s internal door-0
initialization uses the already verified creation decision, rather than
recursively requiring the new lock to have an older holder.

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
    - `room.founder_accrued += founder share`;
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
7. Split `F` (SOL counters, including `room.founder_accrued`). Assert B1. Emit.

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
6. Split `F` into the `_wsol` counters, including
   `room.founder_accrued_wsol`. Assert B1. Emit.
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

1. Before transferring, compute `r = min(pending_reserve_sol, T - room.reserve)`.
   Move exactly r lamports `FeeVault → ReserveVault` (direct debit), and
   decrement `pending_reserve_sol` by r. A zero pending amount is a no-op.
2. `room.reserve += r`.
3. Buy curve position: `q′` = the largest with `R(q′) ≤ R(q) + r`, using
   the pre-increment q and the capped r. Prices read counters only.
4. Transfer `q′ − q` room tokens `RoomVault → RetiredVault`.
5. `room.sold = q′`, `room.retired += q′ − q`.
6. Any part that would take the reserve above T stays pending. It is retired
   on the pool after graduation. If reserve reaches T, set status 1. This
   internal retirement does not count as external trading volume.

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
   - **graduation budget:** the room's `T − R*` lamports to `GradPayer`, a
     direct credit, which the runtime allows to any writable account;
   - **slack:** `room.reserve − T` to `FeeVault` as `protocol_accrued_sol`.
     It is zero by construction (the cap in buy step 3); the term is kept so
     the identity holds under any future change.
   - `room.reserve = 0`.
3. **Check rent sufficiency.** `GradPayer` must hold the rent-exempt minimums
   of the accounts DAMM v2 will create, from the rent sysvar at call time.
   - If runtime rent or DAMM v2 account sizes have grown since this room's
     `graduation_trigger_lamports` was snapshotted, the shortfall is taken
     from `room.protocol_accrued_sol`.
   - If that is not enough, the transaction fails atomically and can be
     retried after a protocol top-up. Do not rewrite the room trigger or
     take extra from its reserve. If current rent is lower, unused budget
     follows the existing GradPayer dust path in step 8.
4. **Prepare the tokens.**
   - Compute `N = floor(R* · (V_tok − room.sold)² / K)` from this room's
     copied constants and actual sold state, including for older triggers.
   - Transfer N room tokens `RoomVault → GradPayer`'s room-token account.
   - Transfer the rest, `U − room.sold − N`,
     `RoomVault → RetiredVault`, and add it to `room.retired`.
   - Only accounted inventory is moved. Any donated excess in RoomVault
     stays locked there; it is not included in the seed or retirement.
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
   - Close the temporary WSOL account into `GradPayer`, then send only the
     tracked unused graduation budget to the protocol. Any donated excess
     remains locked; never sweep the raw balance above rent.
   - Only tracked pool-seeding room-token leftovers in `GradPayer`'s account
     go to `RetiredVault`. Unaccounted donations remain locked.
9. **State:** `room.status = 2`; store `damm_pool`, `damm_position`,
   `position_nft_mint`, `graduated_at`.
   Clear curve-volume buckets; initialize `fee_ckpt` from the new pool's
   actual `total_lp_b_fee` and `fee_ckpt_ts` from the execution clock. Curve
   volume must never be interpreted as LP fees.
10. **Emit** `Graduated`.

### `checkpoint_pool(room)`, permissionless

Read the validated DAMM v2 pool and update the room's tagged fee history using
the conservative interval-start rule in detection §4. This may run for a dead
room too; stale growth is discarded, and fresh subsequent observed activity
can revive it. It never changes room creation time or the lock holder.

### `release_slug(room)`, permissionless

- Load `Config`, `Room` and the room's identity-derived `SlugLock`. Verify
  the lock still names this exact room; a former holder cannot close a lock
  already transferred to a replacement room.
- **Allowed exactly when `NOT live(room)`**, using the same function as launch
  routing and takeover (detection §4), at the execution clock. No separate
  status restriction, reserve rule or idle timer applies.
- For a graduated room, validate its DAMM v2 pool and evaluate the cumulative
  LP-fee increment with the same conservative checkpoint history. Unknown-age
  counter growth is never refreshed into a new recent window. The result
  agrees before and after checkpointing.
- Close only `SlugLock`; its rent goes to the cleanup caller. The room keeps
  trading by id, its metadata and every door remain unchanged.
- An existing dead holder may instead be replaced atomically by `create_room`;
  re-point the same lock without closing it. Check the previous holder and its
  pool (when graduated) before takeover. Creation time belongs to the newly
  created room and cannot be reset on the old holder.

### Fee instructions

- **`claim_door_fees(door)`.** The signer must be `door.fee_recipient`. It
  pays `accrued_sol` from `FeeVault` (direct debit) and `accrued_wsol` from
  `FeeWsol` (Room PDA signs a transfer to the recipient's WSOL ATA). Then it
  zeroes both and adds them to the claimed totals.
- **`claim_founder_fees(room)`.** Mirrors door claims: the signer must equal
  the immutable `room.founder`. Validate the Room PDA, its `FeeVault` and
  `FeeWsol`, the WSOL mint and the founder's canonical WSOL ATA. The ATA
  already exists or is created in a preceding client instruction. Pay
  `founder_accrued` SOL by directly debiting `FeeVault`, and transfer
  `founder_accrued_wsol` from `FeeWsol` to that ATA with the Room PDA signing.
  Zero both counters atomically with the transfers and emit
  `FounderFeesClaimed(room, founder, sol, wsol)`. A failed transfer rolls back
  the counters and the other transfer; a repeated empty claim pays zero.
  Available in every room status, including complete and graduated. It
  preserves fee-vault rent and all door/protocol/pending-reserve liabilities,
  never touches `ReserveVault`, and has no authority to change founder or
  fee snapshots. No extra founder account is required on trading paths.
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

**B1, 1:1 redemption with surplus-tolerant backing.** For every door N:

```
0 <= door_N.backing <= U
bal(DoorRoomVault_N) >= door_N.backing
bal(DoorVault_N) >= U - door_N.backing
```

Asserted at the end of every instruction that touches door N. The backing
counter tracks program issuance minus program redemption; it is never
recomputed from either token account or live mint supply. One door unit
still redeems for one room-token unit. Donations leave the corresponding
surplus locked and do not credit any counter or change a quote. Holders can
still burn their own door tokens with a standard Token-2022 `Burn`, since
there is no PermissionedBurn. That lowers the mint's supply but changes
neither vault, so B1, defined on vault balances, still holds. The room tokens
backing a burned door token stay in `DoorRoomVault_N` forever.

**S1, curve position** (status 0 and 1): `0 <= room.sold <= U` and
`bal(RoomVault) >= U - room.sold`. Also `bal(RetiredVault) >= room.retired`.
Sold and retired are program counters, never inferred from token balances.

**I1, solvency** (status 0 and 1): `room.reserve ≥ R(room.sold)`.

**I2, vault backing:**

```
L(ReserveVault) − rent_min ≥ room.reserve
L(FeeVault) − rent_min ≥ Σ_N door_N.accrued_sol + room.founder_accrued + room.protocol_accrued_sol + room.pending_reserve_sol
bal(FeeWsol) ≥ Σ_N door_N.accrued_wsol + room.founder_accrued_wsol + room.protocol_accrued_wsol + room.pending_reserve_wsol
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
| entry | — | room snapshot T | — |
| a. seed | room pool seed R* | T − R* | temporary WSOL → DAMM v2 token B vault |
| b. graduation budget | T − R* | 0 + slack | `GradPayer` → DAMM v2 account rent |
| c. slack | `room.reserve − T` (0 by construction) | 0 | `FeeVault`, `protocol_accrued_sol` |
| exit | total = `room.reserve` at entry | 0 | status 2: I1 and S1 retire |

**What happens to holders' claims at the handoff.** Before graduation the
reserve covers `R(sold)`, the curve's obligation to every outstanding room
token. After graduation that obligation is carried by the pool. It holds R*
and N tokens at the curve's closing price, and every outstanding room token
(in users' wallets, in `DoorRoomVault`s and in `RetiredVault`) can sell into
it.

**The graduation budget comes from the curve's reserve.** Buyers lift it
from the pool seed R* to the room's T, buying additional curve tokens. The
budget leaves through GradPayer and any unused portion follows the existing
dust rule. The copied trigger remains valid across later rent changes; the
old/new snapshot scenario above checks both handoffs.

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

<!-- BEGIN GENERATED DEFAULT TRIGGER -->
Current **Config default**: `85,018,013,680` lamports, pool seed `85,000,000,000` plus graduation rent `18,013,680`. Existing rooms retain their copied trigger and calculate the seed from their own sold state.
<!-- END GENERATED DEFAULT TRIGGER -->

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
| `liquidity` | the largest L whose required amounts (`liquidity_handler/concentrated_liquidity.rs` L19, `get_delta_amount_a/b_unsigned` L288, L324) fit within the N computed from this room's sold state and its copied R* | rounding dust per graduate step 8; dust size not computed here (needs the Q64 math implemented) |
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

The room-token route's door share goes to `pending_reserve` and is retired by
`retire_pending`. **Founder-share plumbing is present but zero:**
`Config.founder_share_bps` defaults to **0 bps**, preserving the exact v1
60/40 program-fee split and the room-token route's existing reserve share.
It is a share of the program fee, not an additional fee on trade volume.
If only the founder share changes, it comes out of the protocol remainder;
the door share changes only if its own Config parameter changes. All current
spam and poisoning tables use the zero-founder v1 defaults.

The reason to include it now is that the measurement in flight may show the
original creator loses about two-thirds of their narrative's volume to
copies. Such a result could justify a founder share; it is not yet an
aggregate finding or a decision to enable one. Including founder identity,
accruals, the snapshotted share and `claim_founder_fees` in v1 means a future
admin Config change can reopen the split for **new rooms**, without a program
rewrite. Existing rooms retain their immutable fee snapshots, including zero;
there is no retroactive accrual or founder-share override instruction.

The founder receives only the configured slice of program trade fees on
door and room-token routes. Room/door opening fees, conversion fees,
graduation slack and rent dust remain protocol-only; direct DAMM swaps and
LP fees generate no founder accrual. Founder status provides no additional
control over the room. The intended launch fees remain zero. Launchers pay
rent and transaction fees; the extra stored fields increase launch rent as
shown in §1, while the graduation account set, rent budget and trigger are
unchanged. The graduation budget still comes from the room's reserve.

The spam income model below assumes some buyers choose doors uniformly. It
is an assumption, not measured behavior. Frontend ranking and actual routed
traffic determine whether that assumption holds.

<!-- BEGIN GENERATED FEE FIGURES -->
<!-- generated by scripts/fee_model.py -->
Trade fee 100 bps on every buy and sell, charged on top of the trade.

Founder share is present but defaults to 0 bps of the program fee; door and founder shares are snapshotted per room. All spam figures below use these v1 defaults.

| route | to the door | to the reserve | to the founder | to the protocol | total |
|---|---|---|---|---|---|
| through door N, per $1M | $6.0k | $0 | $0.00 | $4.0k | $10.0k |
| room token through the program, per $1M | $0 | $6.0k | $0.00 | $4.0k | $10.0k |

Door fee 0.0 SOL and room fee 0.0 SOL (defaults). A door costs its rent only: 0.009185 SOL = $1.38. Graduation rent (0.018014 SOL) is paid from the reserve at graduate, not by the launcher.

Room lifetime volume at which one more no-traffic door repays its rent, V = rent × (D + 1) / (door_rate × rho):

| rho | D = 10 | D = 100 | D = 1,000 | D = 10,000 |
|---|---|---|---|---|
| 0.01 | $252.6k | $2.32M | $22.98M | $229.64M |
| 0.05 | $50.5k | $463.8k | $4.60M | $45.93M |
| 0.3 | $8.4k | $77.3k | $766.2k | $7.65M |

Income of one more no-traffic door over the room's life, net of its rent, door_rate × rho × V / (D + 1) − rent:

| room lifetime volume V | rho | D = 10 | D = 100 | D = 1,000 | D = 10,000 |
|---|---|---|---|---|---|
| $1.00M | 0.05 | $25.90 | $1.59 | $-1.08 | $-1.35 |
| $1.00M | 0.3 | $162.26 | $16.44 | $0.42 | $-1.20 |
| $10.00M | 0.05 | $271.35 | $28.33 | $1.62 | $-1.08 |
| $10.00M | 0.3 | $1.6k | $176.84 | $16.60 | $0.42 |
| $50.00M | 0.05 | $1.4k | $147.14 | $13.61 | $0.12 |
| $50.00M | 0.3 | $8.2k | $889.71 | $88.53 | $7.62 |

10,000 spam doors in a room with 10 doors already (cost = rent only):

| V | rho | spam income | spam cost (rent) | net |
|---|---|---|---|---|
| $1.00M | 0.05 | $299.70 | $13.8k | $-13.5k |
| $1.00M | 0.3 | $1.8k | $13.8k | $-12.0k |
| $10.00M | 0.05 | $3.0k | $13.8k | $-10.8k |
| $10.00M | 0.3 | $18.0k | $13.8k | $4.2k |
| $50.00M | 0.05 | $15.0k | $13.8k | $1.2k |
| $50.00M | 0.3 | $89.9k | $13.8k | $76.1k |
<!-- END GENERATED FEE FIGURES -->

## 7. Limits

**Display.**

- Every door mint and the room mint has a fixed 1,000,000,000 supply, so
  every door displays the **room's FDV** (price × 1B).
- An aggregator that sums market caps across a room's mints will overcount by
  the number of mints, which is the door count plus one for the room token.
- Explorers show door-vault balances as "supply" unless the vault is
  labelled. Holders of more than one door see one wallet line per mint.

**Compute per instruction.** Not measured; no program has been built.

**Accounts touched and packet model** (generated; each variant includes the
pool/holder accounts it may require):

<!-- BEGIN GENERATED INSTRUCTION ACCOUNTS -->
<!-- generated by scripts/instruction_accounts.py -->
| instruction | accounts | signatures | under 64-lock limit | modelled legacy bytes | packet margin (bytes) |
|---|---|---|---|---|---|
| buy/sell, door route, curve | 16 | 1 | yes | 641 | 591 |
| buy/sell, room-token route, curve | 12 | 1 | yes | 509 | 723 |
| buy/sell, door route, pool | 26 | 1 | yes | 971 | 261 |
| buy/sell, room-token route, pool | 22 | 1 | yes | 839 | 393 |
| convert | 17 | 1 | yes | 674 | 558 |
| open_door (curve, distinct identity holder; no first buy) | 16 | 2 | yes | 983 | 249 |
| open_door (both pools, distinct identity holder; no first buy) | 18 | 2 | yes | 1049 | 183 |
| create_room (fresh identity, door 0; no first buy) | 22 | 2 | yes | 1189 | 43 |
| create_room (graduated dead-holder takeover; no first buy) | 24 | 2 | yes | 1255 | -23 |
| release_slug (curve) | 5 | 1 | yes | 278 | 954 |
| release_slug (pool) | 6 | 1 | yes | 311 | 921 |
| checkpoint_pool | 4 | 1 | yes | 245 | 987 |
| claim_door_fees | 8 | 1 | yes | 377 | 855 |
| claim_founder_fees | 7 | 1 | yes | 344 | 888 |
| graduate | 31 | 1 | yes | 1136 | 96 |

`graduate`: 31 keys, one signature, 8-byte discriminator, one instruction: 1136 bytes, 96 bytes spare. With one ComputeBudget key and limit/price instructions: 1188 bytes, 44 spare.

These are serialized-size models, not a compiled-program measurement. Each root instruction passes every listed key; aliases are deduplicated in a real message. Launches have two distinct signers and max metadata/evidence. Other instructions use an assumed 8-byte discriminator only. Optional first-buy account unions, ATA creation and extra instructions require a new packet check. Negative margins require a v0 message and lookup table (or instruction splitting where atomicity permits). Use v0/ALT for launch and graduation transactions to leave compute-budget and composition margin.

Account metas (R read, W write, S signer):

| launch/release addition | role |
|---|---|
| matcher_authority | R,S; mandatory for both launch instructions |
| slug_lock | R for open_door; W for create_room/release_slug |
| identity_holder_room / previous_holder_room | R; verify key/id from lock, optional only if no distinct holder |
| damm_pool / identity_holder_damm_pool / previous_holder_damm_pool | R; required for the corresponding graduated room |
| config | R; authority and the single set of liveness constants |
| room | W for trades, launch and checkpoints; R for release_slug |

`claim_founder_fees`: founder W,S (must equal Room.founder), Room W, FeeVault W, FeeWsol W, founder's canonical WSOL ATA W, WSOL mint R, SPL Token program R. The ATA must already exist (or be created in a preceding client instruction). No founder account is added to trading account lists: trades accrue counters, and claims perform the payout. The same currency/vault checks apply to door claims.
<!-- END GENERATED INSTRUCTION ACCOUNTS -->

Account lock limit: 64 per transaction, or `MAX_TX_ACCOUNT_LOCKS` behind
`increase_tx_account_lock_limit` (agave `runtime/src/bank.rs` L3847). Measure
CU on a build before quoting throughput.

<!-- BEGIN GENERATED PROGRAM CONTEXTS -->
<!-- generated by program/scripts/check_layouts.py from the emitted Anchor IDL -->
Actual curve-phase instruction contexts include vaults needed for the
end-of-instruction assertions. Counts include all optional account metas;
an absent optional uses the program-ID sentinel, reducing unique keys.
These are meta counts, not legacy/v0 packet-size measurements.

| instruction | metas with optionals | writable metas | signers |
|---|---:|---:|---:|
| buy | 15 | 9 | 1 |
| claim_door_fees | 17 | 8 | 1 |
| claim_founder_fees | 17 | 8 | 1 |
| convert | 20 | 13 | 1 |
| create_room | 23 | 15 | 2 |
| initialize_config | 5 | 2 | 1 |
| open_door | 19 | 10 | 2 |
| release_slug | 4 | 2 | 1 |
| retire_pending | 9 | 5 | 0 |
| sell | 15 | 9 | 1 |
| set_fee_recipient | 12 | 5 | 1 |
| sweep_protocol_fees | 17 | 8 | 1 |
| update_config | 2 | 1 | 1 |
<!-- END GENERATED PROGRAM CONTEXTS -->

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

1. **B1:** `bal(DoorRoomVault_N) >= door_N.backing` and
   `bal(DoorVault_N) >= U - door_N.backing`, with backing in `[0,U]`, after
   every instruction that touches N. Quotes and transfers use the counter.
2. **S1:** `bal(RoomVault) >= U - room.sold`, sold in `[0,U]`, while status < 2;
   `bal(RetiredVault) >= room.retired`. Surplus is never credited or moved.
3. **I1:** `room.reserve ≥ R(room.sold)` while status < 2.
4. **I2:** `L(ReserveVault) − rent_min ≥ room.reserve`, and
   `ΔL(ReserveVault) == Δroom.reserve` for every post-initialization instruction.
   Creation additionally accounts for the exact rent-funding credit.
5. **I3:** a curve sell debits `ReserveVault` by exactly `R(q) − R(q−t)`.
   `graduate` debits exactly `room.reserve` (= T at entry): R* to the pool
   seed, `T − R*` to `GradPayer`, and slack `room.reserve − T` (0 by
   construction) to the protocol. No other instruction debits
   `ReserveVault`.
6. **F1:** per trade, `F == door share + founder share + protocol share`.
    The door share lands in exactly one of `door.accrued_*` or
    `room.pending_reserve_*`; founder share lands in the matching SOL/WSOL
    founder counter. A zero founder share reproduces every legacy 60/40 split.
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
    `freeze_authority == None`, `update_authority == None`, initial supply `U`
    and subsequent supply `<= U`, and no
    extensions beyond MetadataPointer and TokenMetadata. The room mint's name,
    symbol and URI equal door 0's.
13. **D1:** no instruction closes/reallocates these door accounts or changes
    their identity, vault addresses or revoked mint/metadata authorities.
    Declared backing, fee, recipient, volume and timestamp updates remain
    permitted; vault movements must match the corresponding counter changes.
14. **G1:** after `graduate`:
    - the DAMM v2 position's `permanent_locked_liquidity` equals its total
      liquidity;
    - the position NFT is held by `protocol_fee_recipient`;
    - `room.reserve == 0` and all accounted RoomVault inventory is consumed;
      any unaccounted token or SOL vault surplus remains locked;
    - the pool was seeded with exactly R* lamports and N room tokens;
    - `RetiredVault` gained `U − sold − N`.
15. **G2:** `graduate` debits `ReserveVault` by exactly `room.reserve` at
    entry: R* + (T − R*) + slack.
16. **S2:** `release_slug` succeeds exactly when the current holder fails
    the routing liveness gate, in any status, and closes only its `SlugLock`.
    It rejects a stale former holder after takeover. Boundary and stale-pool
    tests use the same `is_live` helper as routing.
17. **F4:** founder and fee snapshots are immutable after room creation.
    Updating Config affects new rooms only. Only the founder signs its claim;
    a claim pays and zeroes exactly its two counters atomically, preserves
    all other liabilities and vault rent, and never debits the reserve.
    Failed claims roll back, and repeated empty claims pay zero.

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
