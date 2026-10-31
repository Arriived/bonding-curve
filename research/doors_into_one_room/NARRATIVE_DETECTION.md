# Narrative detection: door or new room

31 October 2026. This document decides, for every launch, whether the coin becomes
a door in an existing live room or a new room. The launcher supplies a name, a
symbol and an image, and never chooses the outcome.

It is the routing step in front of `create_room` and `open_door` in
[PERMANENT_CURVE_SPEC.md](PERMANENT_CURVE_SPEC.md).

**Where every number comes from:**

- Each number below comes from a script under `scripts/narrative/`, whose output
  is in `outputs/narrative/`, or from an on-chain read with its slot recorded.
- The matcher is `scripts/narrative/matcher.py`. To run it:
  `scripts/narrative/run_matcher.sh [input.json]`. With no argument it runs the
  worked examples in `scripts/narrative/examples/` and checks each decision.
- The reproduction commands are in §12.

## 0. Corrections

These conflicts came up while verifying the brief. Each one is resolved below
as stated, or left as an open decision for the owner.

1. **Post-graduation liveness cannot come from pool liquidity.**
   - A DAMM v2 pool's `liquidity` changes only when liquidity is added or
     removed, never on a swap.
   - The doors graduation position is permanently locked (spec §5.4), so for a
     doors pool `liquidity` is effectively constant.
   - **Measured.** 18 live DAMM v2 pools were read twice, 300 s apart (slots
     463,772,510 and 463,773,913). In the 14 pools that traded in between,
     `liquidity` moved in 0, while `metrics.total_lp_b_fee` and
     `token_b_amount` moved in all 14 (`outputs/narrative/damm_pool_fields.json`).
   - The gate therefore uses `Pool.metrics.total_lp_b_fee`, the cumulative LP
     fee in token B, which is WSOL for a doors pool. A room-side checkpoint
     turns it into a per-window rate (§4.2).
2. **Real token images could not be fetched from this environment.**
   - The environment's network policy denied every image and metadata host
     tried: metadata.j7tracker.io, pump.mypinata.cloud, gateway.pinata.cloud,
     dweb.link, w3s.link, cloudflare-ipfs.com and frontend-api-v3.pump.fun.
     The proxy answered 403 to CONNECT.
   - ipfs.io answered HTTP 429, saying it is "switching to a service worker
     gateway only".
   - The image rule is therefore specified and tested for robustness on a real
     but different corpus: 1,870 Twemoji images.
   - Its precision on real vamps is **not measured**. Image signals ship in
     **shadow mode**: computed and logged, but not counted in the decision
     (§3.3).
   - Allowing those hosts would let the same scripts calibrate the rule on the
     2,956 sampled launches (§11).
3. **The spec lets the caller choose the room, which the settled rule
   forbids.**
   - `open_door(room, …)` takes the room as an argument, and
     `create_room(slug, …)` takes a launcher-chosen slug.
   - Both now require the matcher's co-signature over the decision, and the
     slug is derived from door 0's identity (§8).
4. **The exact-match floor collides with ruling 5's SlugLock expiry.** This is
   an owner decision.
   - The cheapest on-chain floor is SlugLock itself, keyed by door 0's folded
     identity instead of a launcher-chosen slug.
   - Under ruling 5, however, a slug is released only when reserve < 1 SOL
     and idle > 7 days, and never after graduation.
   - The hard liveness gate marks rooms dead much earlier (§4). A room that is
     dead to the gate but still holds the slug would block the fresh room the
     gate says the launcher should get.
   - **This design replaces the expiry rule.** A new room may take over a
     SlugLock whose holder fails the liveness gate, and `release_slug` uses
     the same test. This changes ruling 5 and needs the owner's sign-off.
   - If ruling 5 stands unchanged, the exact floor has to be dropped. Exact
     copies would then be routed by the matcher alone.
5. **The two fields the brief names make the gate cheap to fake for any room
   that already holds reserve.** This is an owner decision.
   - The brief says pre-graduation liveness comes from `room.reserve` and
     `room.last_trade_at`.
   - The reserve is held capital. `last_trade_at` is refreshed by any trade:
     0.00009 SOL per buy-and-sell through one's own door
     (`outputs/narrative/gate_costs.md`).
   - So an abandoned room with bagholders can be kept "live" for a fraction of
     a cent a day.
   - The gate below follows the brief.
   - §9.3 costs a stronger option that uses the existing `Room.volume_gross`
     field. It is recommended but not adopted silently.
6. **The sample is short, and was taken on Halloween.**
   - 2,956 launches from 15:27 to 17:10 UTC on 31 October 2026 (1.72 hours).
   - Collection stopped there because the public RPC throttled to about 50
     launches a minute.
   - That is enough to measure the strict text rule tightly. It is too short
     and too seasonal (Halloween-named coins are everywhere in it) for
     long-lived narratives and rare evasion patterns. See §11.
7. **Slots are not 0.4 s.**
   - Measured over the last 200,000 slots at read time: 0.215 s per slot
     (`outputs/narrative/liveness_reads.json`, `sec_per_slot_measured`).
   - Every threshold here is in unix seconds, not slots, so nothing depends on
     slot time.

## 1. The design in one table

| part | rule |
|---|---|
| who decides | A protocol-operated matcher computes the route off-chain and **co-signs** the launch transaction. The program accepts `create_room` / `open_door` only with the `Config.matcher_authority` signature (§2). |
| what the program enforces itself | (a) the target room passes the liveness gate at execution; (b) the **exact-identity floor**: a launch whose folded name and symbol equal a live room's door 0 must become a door of that room; (c) the launcher signs the transaction they previewed. |
| text | NFKC, homoglyph and confusable folding, then exact equality on folded keys at the top tiers, plus three fuzzy signals below them (§3.1). |
| image | 64-bit DCT pHash, Hamming ≤ 10 strong, ≤ 16 weak (§3.2). Shadow mode in v1. |
| combination | Points: route at ≥ 3. Text: identity equal 3, name equal 3, symbol equal 2, fuzzy 1. Image: strong +2, weak +1, when image routing is on (§3.3). |
| v1 operating point | Route only on equal folded identity, or equal folded name. Measured **precision 99.8%** (pessimistic 99.6%), **recall 87%** of text-findable vamps before the gate and **about 39% after it** (§4.1, §7, §10). |
| liveness | Before graduation: `reserve ≥ 1 SOL` and a trade within 6 h. After graduation: LP fee ≥ 0.08 SOL in the last 24 h window, from `Pool.metrics.total_lp_b_fee` via a room checkpoint (§4). |
| ties | Floor room first, then score, text tier, image distance, SOL depth, lowest `room_id` (§5). |
| preview | The launcher sees the exact decision and the room's state, then confirms or backs out. Backing out costs nothing (§6). |

## 2. Trust model

### 2.1 What was chosen

There are three layers. Each one is checkable by someone other than the
matcher.

1. **Protocol-operated matcher, co-signing.**
   - `Config` gains `matcher_authority: Option<Pubkey>`.
   - The launcher's frontend sends the candidate (name, symbol, URI) to the
     matcher. The matcher returns the decision and partially signs the
     transaction that executes it.
   - The launcher adds their own signature and submits.
   - The decision cannot be replayed or altered: the matcher's signature
     covers the whole message, including the decision argument and the recent
     blockhash, so it expires with the blockhash.
   - Cost to the launcher: one more signature fee (agave
     `fee/src/lib.rs` L42–56 @ `aec3b701`: the fee is the signature count ×
     `lamports_per_signature`). This is a transaction fee, not a protocol
     fee; launching still costs rent only.
   - An Ed25519-precompile signature over a decision message would work too,
     and is billed the same way (the same function counts precompile
     signatures). Co-signing is simpler and needs no instruction
     introspection.
2. **On-chain exact-identity floor.**
   - The program folds door 0's name and symbol itself (ASCII-only folding,
     §3.1) and keys `SlugLock` by `sha256(folded_symbol ‖ 0x00 ‖ folded_name)`.
   - If a live room holds that lock, the launch must be a door of that room,
     whatever the matcher signed.
   - This catches 98.7% of certain vamps on its own (§10). The matcher cannot
     hand an exact copy its own room while a live room has that identity.
3. **Program-enforced liveness.**
   - The program re-checks the gate (§4) on the target room at execution.
   - The matcher cannot route anyone into a dead room.

**A propose-and-challenge window was rejected, for three reasons:**

- **A route cannot be undone once money moves.** The door mint exists, the
  launcher's first buy has moved the room's curve, and other traders have
  traded against it within seconds. Unwinding a wrong route would mean
  reversing third parties' trades in a shared curve.
- **Holding launches pending would delay every launch by the window.**
- **Disputes need an adjudicator, which moves the trust rather than removing
  it.**

What replaces the window is after-the-fact verifiability (§2.3) and the
launcher's consent at preview (§6).

### 2.2 How centralised this is, and what a bad matcher can do

**v1 is centralised: the protocol decides every fuzzy route.** The program
enforces only the floor, the gate and the launcher's signature.

A malicious or compromised matcher key can:

| it can | bounded by |
|---|---|
| **Refuse to sign**, so launches stop. | No funds are at risk. It is visible at once. `admin` can set `matcher_authority = None`, which switches the program to **floor-only mode**: the exact floor plus the gate route everything, and every other launch gets a new room. |
| **Route a launch into a live room it prefers** (a false positive), e.g. a room whose tokens the operator holds. | The launcher sees the room in the preview and signs it (§6). A third-party frontend shows the room id from the transaction itself. The room must pass the gate. The decision is public and re-computable (§2.3), so a route the published rules do not produce is provable misbehaviour. |
| **Give a vamp its own room** (a false negative). | Not for exact copies: the floor catches them. Otherwise it only weakens anti-vamp routing, and re-running the matcher detects it. |
| **Favour one of several matching rooms.** | The tie-break is published and deterministic (§5). A deviation is detectable the same way. |

It cannot:

- move funds;
- route into a dead room;
- override the floor;
- execute a launch without the launcher's signature;
- change a past route.

**Key rotation:** `admin` calls `set_matcher_authority(new)`, a single
instruction. A compromise is limited to the routes signed before rotation, and
each of those was accepted by its launcher.

### 2.3 Verifying routes after the fact

- **The matcher is deterministic, published and versioned.** This repository's
  `matcher.py` is the reference.
- **Each route records its evidence on-chain.** `create_room` and `open_door`
  emit, and store in the new door's reserved bytes:
  - `matcher_version: u16`;
  - `rule: u8`, the tier that fired;
  - `face: u8`, the door index matched;
  - `phash: u64`;
  - `image_sha256: [u8; 32]` in the event only.
- **Every input except the image bytes is on-chain.** Names, symbols and URIs
  are in mint metadata. Room state at the slot is in account history.
- **Images:**
  - For content-addressed URIs (IPFS CIDs), anyone can refetch the exact
    bytes.
  - For mutable hosts, the event's `image_sha256` shows whether the bytes
    fetched later are the bytes the matcher saw.
  - The pHash is fully specified, including tie-breaking (§3.2), so two
    implementations agree bit for bit.
- **Re-running the matcher over the event log reproduces every decision.** Any
  mismatch is evidence against the operator.

## 3. Matching rules

### 3.1 Text

**Normalisation** (`matcher.py`, `_base` / `_fold`), applied in this order:

1. Unicode NFKC. This folds full-width letters and compatibility forms.
2. Drop invisible characters: Unicode format characters (category Cf,
   including zero-width joiners), Hangul fillers U+115F, U+1160, U+3164,
   U+FFA0, and braille blank U+2800.
   - These occur in the sample: `ㅤㅤ` symbols, which `str.isalnum()`
     otherwise accepts.
3. Homoglyph table: Cyrillic and Greek letters that render as Latin, e.g.
   `Р→P`, `Е→E`, `о→o`, `Ι→I`.
4. Strip combining marks (accents), then lower-case.
5. Multi-letter confusables in lower case: `rn→m`, `vv→w`.
6. Upper-case, then fold digits: `0→O`, `1→I`, `3→E`, `4→A`, `5→S`,
   `7→T`, `8→B`.
7. Keep alphanumerics of any script. CJK and Hangul names survive.

**Keys:**

- **Symbol key:** every alphanumeric character of the symbol after
  normalisation. `$EL0N` → `ELON`, `РЕРЕ` (Cyrillic) → `PEPE`.
- **Name tokens:**
  - split on camelCase, then on non-alphanumerics;
  - fold each token;
  - split a trailing `COIN` or `TOKEN` off a token (`MarvinCoin` → `MARVIN`,
    `COIN`);
  - drop the stopwords `THE A AN OF ON AND COIN TOKEN OFFICIAL SOL SOLANA
    MEME CTO`.
- **Name key:** the tokens concatenated. `random walk` and `randomwalk` both
  give `RANDOMWALK`.

**Signals, strongest first.** Measured precision is on different-identity
pairs (§10.2).

| tier | signal | precision S/(S+D) | routes alone? |
|---|---|---|---|
| T3 | symbol key and name key equal | 100% by the label rule (§10.2) | yes |
| T2n | name key equal, name key ≥ 4 characters | **98%** (55 S, 1 D; 95% CI 91–100%) | yes |
| T2s | symbol key equal, name differs | **61%** (27 S, 17 D, 16 U; CI 47–74%) | no |
| T1 | containment: one side's symbol key is a token (or the whole name key) of the other's name, ≥ 3 characters | **34%** (16 S, 31 D, 15 U; CI 22–48%) | no |
| T1 | name-token Jaccard ≥ 0.5, sharing a token of ≥ 4 characters | **62%** (26 S, 16 D, 18 U; CI 47–75%) | no |
| T1 | symbol keys one Damerau–Levenshtein edit apart, both ≥ 5 characters | **50%** (27 S, 27 D, 6 U; CI 37–63%) | no |

**Why equality rather than a graded similarity score:**

- On real launches, **exact equality of folded keys is where the precision
  is.** Name equality is right 98% of the time. Every graded signal measured
  is at 34–62%.
- Tickers are 3–10 characters. At that length a one-edit neighbour is as
  often a different coin as a typo-squat: `BILLY`/`PILLY`/`MILLY` and
  `SPOOKY`/`SPOOKS` are in the sample's D labels.
- A continuous score (Jaro–Winkler or Levenshtein ratio) would only rename
  those same collisions as "0.8 similar".
- Damerau–Levenshtein is used where a graded measure is needed because it
  counts a transposition as one edit, which is the cheapest typo-squat.

**The brief's two cases:**

- **`$ELON` vs `$EL0N`.** Both symbol keys fold to `ELON`, a symbol-equal
  signal. If the names also match after folding, it is T3 and routes. This is
  worked example `01` (`El0n`/`$EL0N` → room `Elon`/`ELON`).
  - Even a symbol-only match is caught as T2s; in v1, T2s routes only with an
    image match (`13_symbol_only_is_not_enough`).
- **`Elon Musk Coin` vs `ELON`.** The name tokens are `ELON`, `MUSK`.
  `ELON` is a token, so this is a T1 containment match. **It does not route on
  text alone, on purpose.**
  - In the sample, containment is right a third of the time. Its D labels
    include `Elon ETF` vs `Extremely Large Oversized Nuts` (both `$ELON`),
    `Just a cat` vs `SPIDER CAT`, and `Hallo BTC PostCode` vs `BALLS TINGLE
    COIN / BTC`.
  - With an image match (pHash ≤ 10) it scores 1 + 2 = 3 and routes, once
    image routing is on (example `04`). In v1 shadow mode it gets a new room
    and the log records "would route with image" (`04b`).

**On-chain floor folding** (`calibrate_text.py`, `floor_fold`):

- The program folds raw UTF-8 bytes ASCII-only: lower-case, `rn→m`, `vv→w`,
  upper-case, drop ASCII punctuation, the same digit fold.
- Non-ASCII bytes pass through unchanged. There is no NFKC on-chain, so
  homoglyph copies evade the floor and are left to the matcher.
- In the sample, the floor catches 1,653 routes against the full fold's 1,665
  (§10.3).

### 3.2 Image

**Algorithm** (`phash.py`):

1. Composite any alpha channel onto white. Token images are often transparent
   PNGs, and `imagehash`'s plain `convert("L")` reads whatever RGB lies under
   transparent pixels.
2. Convert to 8-bit grayscale and resize to 32×32 with Lanczos.
3. Apply a 2-D DCT-II (unnormalised, the scipy convention).
4. Round the coefficients to 6 decimals.
5. Take the top-left 8×8 block, DC included. A bit is set where the
   coefficient is greater than the block's median.
6. Pack row-major with the first bit most significant: 16 hex characters.
7. The distance is the Hamming distance.

**Checked against the reference implementation:**

- The result equals `imagehash.phash` 4.3.2 bit for bit on 500 of 500 images
  (`outputs/narrative/phash_reference_check.txt`).
- The rounding in step 4 is ours, and it matters for re-computability.
  Symmetric images have coefficients exactly at the median in real arithmetic.
  Unrounded floating point turns them into ±1e-10 noise, which can differ
  across machines.
- 66 of the 500 images contain such ties, 2,192 tie bits in all.

**Thresholds:** strong (I2) Hamming ≤ 10; weak (I1) ≤ 16.

The measurements are on 400 Twemoji images: 64 px sources, upscaled to 256 px
and edited. Negatives are all 1,747,515 pairs of 1,870 distinct images
(`outputs/narrative/image_robustness.md`).

| edit | copies within ≤ 10 | within ≤ 16 |
|---|---|---|
| re-encode JPEG q85 / q40 | 95.2% / 93.8% | 99.0% / 98.5% |
| rescale to 128 px / 512 px | 97.5% / 99.5% | 99.2% / 99.8% |
| hue rotate 60° / 180° | 83.0% / 70.8% | 95.5% / 88.5% |
| grayscale | 100% | 100% |
| brightness ×1.2, contrast ×1.3, blur | 95.8–98.2% | 99.0–99.8% |
| centre crop 5% / 10% / 20% | 90.8% / 57.2% / 9.2% | 98.5% / 89.8% / 37.0% |
| 8 px border | 86.0% | 99.0% |
| caption bar over the bottom 15% | 39.2% | 67.0% |
| sticker over 1/16 of the area | 34.0% | 62.7% |
| rotate 5° | 50.2% | 83.0% |
| mirror / colour invert | 7.5% / 0% | 9.5% / 4.5% |
| crop 10% + hue 60° + caption + JPEG q60 | 6.0% | 34.5% |

| distinct-image pairs within | rate per pair | images with any other image within |
|---|---|---|
| ≤ 10 | 1.05×10⁻³ | 28.8% |
| ≤ 16 | 4.74×10⁻³ | 81.1% |

**What this shows:**

- **pHash survives what lazy copies do**: re-encoding, rescaling, recolouring,
  mild crops, borders and blur.
- **It does not survive** a caption or sticker over part of the image, crops
  of 10% or more, rotation, or mirroring.
- Mirroring could be covered by also hashing the mirrored candidate and
  taking the smaller distance. That doubles the false-match rate. It is not in
  v1.
- **Image alone never routes.**
  - At ≤ 10, about one unrelated pair in a thousand collides. Against
    thousands of live rooms, a random image would almost surely be "close" to
    some room's image.
  - The Twemoji corpus overstates this somewhat: it holds families of
    near-identical yellow faces.
  - The image only corroborates a text signal. That restricts the comparison
    to the few rooms text already selected.

### 3.3 Combination

**Scoring:** `score = text_points + image_points`. A room matches when
`score ≥ 3` and the room passes the gate.

| text | points | | image | points |
|---|---|---|---|---|
| T3 identity equal | 3 | | I2 (≤ 10) | +2 |
| T2n name equal | 3 | | I1 (≤ 16) | +1 |
| T2s symbol equal | 2 | | none or far | 0 |
| T1 fuzzy | 1 | | | |

**Routes with image routing on:**

- T3 or T2n route on text alone.
- T2s routes with I1 or I2.
- T1 routes with I2.
- An image never routes alone.

**v1 ships `image_routing = "shadow"`.**

- Image points are computed and reported (`would_route_with_image` in the
  matcher's output), but not counted.
- That makes the v1 decision text-only, T3 or T2n, which is the operating
  point measured in §10.
- Switch to `"on"` after the image-assisted routes have been labelled on real
  token images (§11).

**Matching scope inside a room:**

- **Fuzzy (T1) signals match door 0 only**, the room token's identity.
- **Exact signals (T3, T2n, T2s) match any door's face.**
  - So a later door `Marvin The Martian / MARVIN` in a room founded as
    `MarvinCoin / MARV` catches the next identical `Marvin The Martian`
    (example `10`).
  - This also stops fuzzy chains (A ~ B ~ C) from dragging unrelated launches
    in.

## 4. Liveness gate (hard rule)

The program checks the gate on every candidate room. A room that fails cannot
receive a door, whatever the matcher signed. The launch then gets a new room,
which may take over the dead room's SlugLock (§0.4).

### 4.1 Before graduation (status 0, 1)

`live ⇔ room.reserve ≥ R_min ∧ now − room.last_trade_at ≤ T_idle`

**Thresholds: `R_min` = 1 SOL, `T_idle` = 6 h** (`matcher.py` `DEFAULTS`).

**How they were chosen.** Real pump.fun curves were read on-chain (§10.4,
`outputs/narrative/liveness_table.md`). A pump.fun curve stands in for a doors
room: both have 30 SOL of virtual reserve. In a pump.fun `TradeEvent` read here,
`virtual_sol_reserves − real_sol_reserves` = 30,000,000,000 lamports, against
doors' V_sol of 30.0009 SOL. Two
measurements matter:

- **Recall kept.** 94 real copies were sampled: certain vamps, by a different
  creator, all SOL-quoted. Each copy's room was rebuilt from the earlier
  cluster members' curves, as the room it would join: reserve summed, latest
  trade taken.
  - With no reserve floor, 93% of those rooms had a trade within 1 h of the
    copy. Copies arrive fast: median idle 1 s, p90 547 s.
  - With a 1 SOL floor, 45% pass. The median room held 0.56 SOL at copy time,
    and a quarter held nothing.
- **Namespace retired.** Random SOL-quoted launches were read at slots
  463,785,921–463,789,180.
  - **Without a reserve floor**, 31% of day-old coins had a trade in the last
    hour. Bots keep trading dead coins, so idle time alone leaves about a
    third of yesterday's namespace "live".
  - **With a 1 SOL floor**, 2.4% of 1–3-hour-old coins are live, and 0% of
    day-old and of week-old coins.

**So:**

- **A reserve floor is necessary.** Without one, idle time alone marks too
  much dead namespace live, and liveness costs only refresh trades (§9.2).
- **The floor costs half the recall, and the copies it drops are copies of
  rooms holding under 1 SOL.**
  - Those are mostly clusters with no money in them: the 25th percentile
    reserve is 0.
  - Splitting them costs little, because there is little to split.
  - The copies it keeps target rooms with real reserve (75th percentile
    21.4 SOL). Those are the splits that matter.
- **Between 0.5 and 2 SOL, recall barely moves:** 47%, 45%, 43%.
  - 1 SOL is chosen. It matches the 1 SOL already in DESIGN.md §6, and it
    puts 1 SOL of capital per room in a poisoner's way (§9.2).
- **`T_idle` cannot be pinned down by this data.** Every column from 10 min
  to 24 h gives the same pass rates once `R_min` ≥ 0.5 SOL.
  - 6 h is chosen as slack for live rooms with quiet hours.
  - A shorter window retires dead rooms faster, at no measured recall cost.
  - It needs doors' own data.
- **Combined with the text rule**, recall is about 87.4% × 45% ≈ 39% of
  text-findable vamps. That assumes the gate's effect on the sampled copies
  holds for all vamps. It is still above the owner's 20–30% bar.

**Status 1** (complete, awaiting the permissionless `graduate` crank) passes
the reserve test by construction, since its reserve is at least the trigger.
It stays live until `T_idle` after its last trade.

### 4.2 After graduation (status 2)

**The field: `Pool.metrics.total_lp_b_fee: u128`.**

- Source: MeteoraAg/damm-v2 @ `5398b5c7c534de014091132da37c6478cce671a8`,
  `programs/cp-amm/src/state/pool.rs`, PoolMetrics L189–197.
- Byte offset **584** in the 1,112-byte Pool account:
  - 8-byte discriminator;
  - `pool_fees` 160 bytes;
  - the fields to `permanent_lock_liquidity` at 552;
  - `metrics` at 568, `total_lp_a_fee` at 568, `total_lp_b_fee` at 584.

**Why it measures trading:**

- `apply_swap_result` (pool.rs L811–848) calls
  `metrics.accumulate_fee(trading_fee, protocol_fee, fees_on_token_a)` on
  every swap.
- With the spec's `collect_fee_mode = OnlyB`, `fees_on_token_a` is false in
  both directions (`state/fee.rs` L415–416). So every swap, buy or sell, adds
  its LP fee in WSOL to `total_lp_b_fee` (pool.rs L214).
- Measured on live pools, 300 s apart: it moved in every pool that traded,
  and liquidity moved in none (§0.1).

**Turning a cumulative counter into a rate.** The program cannot see trade
times on the pool, so it keeps a checkpoint in `Room`, carved from the
existing `reserved: [u8; 64]`:

- `fee_ckpt: u128`
- `fee_ckpt_ts: i64`
- `last_window_fee: u64`

**How the checkpoint is kept:**

- **At `graduate`:** `fee_ckpt = 0` (a new pool), `fee_ckpt_ts =
  graduated_at`.
- **Permissionless crank `checkpoint_pool(room)`.** It reads the pool
  (checking key = `room.damm_pool`, owner = DAMM v2, data length 1,112). If
  `now − fee_ckpt_ts ≥ W`:
  - `last_window_fee = total_lp_b_fee − fee_ckpt`, saturating;
  - `fee_ckpt = total_lp_b_fee`;
  - `fee_ckpt_ts = now`.
- `open_door` and `create_room` run the same update whenever they read the
  pool.

**The gate**, with `F = total_lp_b_fee − fee_ckpt` and
`age = now − fee_ckpt_ts`:

- **`age > 2W` → not live.** The checkpoint is stale. A cumulative counter
  cannot say whether old fees are recent, so the gate fails closed and
  protects the new coin.
- **`F ≥ F_min` → live.** Fees in the current, partial window are enough.
- **`age ≤ W` and `last_window_fee ≥ F_min` → live.** The last full window was
  enough.
- **Otherwise → not live.**

**Thresholds: `W` = 24 h, `F_min` = 0.08 SOL of LP fee per window.** That
is 10 SOL of pool volume a day, at the spec's assumed 100 bps base fee with
80% to positions.

**This number is not calibrated.** No doors pool exists, and 18 random DAMM v2
pools read twice are no basis for a memecoin threshold. It is set as a modest
"someone still trades it" bar: faking it costs 0.1 SOL per room per day
(§9.3).

Graduated rooms are poor poisoning vehicles anyway, since each one took 85 SOL
to graduate. The threat after graduation is a long-dead room swallowing a new
coin. The data that would set it is in §11.

**`token_b_amount`** (offset 688, also updated on every swap, pool.rs
L861/L863) is read but not gated. A doors pool's WSOL cannot fall far: the pool
was seeded with 85 SOL and holds every room token sold back. A floor on it
would pass every graduated room, live or dead.

**Fail closed on layout drift.** DAMM v2 is upgradeable, and the
`total_lp_b_fee` accumulation carries an upstream `TODO should metrics store
trading fee or claiming fee?` (pool.rs L840). The program checks the
discriminator and the 1,112-byte length. On any mismatch the room is not live.
Meteora changing these semantics is a dependency to watch.

## 5. Tie-breaking

Among live rooms that match, the program and the matcher both apply, in order:

1. **The floor room.** If the candidate's exact-identity SlugLock is held by a
   live room, that room wins. The program enforces it.
2. **Higher score.**
3. **Stronger text tier:** T3 > T2n > T2s > T1. This is the measured
   precision order (§3.1). Text outranks image because text precision is
   measured and image precision is not.
4. **Smaller pHash distance**, when image routing is on.
5. **Greater SOL depth:** `reserve` before graduation, pool `token_b_amount`
   after. The deeper room is the established market for the narrative, the one
   a launcher gains most from joining, and the one most expensive to fake
   (§9.3).
6. **Lowest `room_id`:** the oldest room. Deterministic and publishable.

Worked examples: `06_tie_stronger_text_wins` and `07_tie_deeper_room_wins`.

## 6. Preview and back-out

Before signing, the launcher sees the matcher's decision and everything that
determines it.

**For a door:**

- "This launches as **door #N** in the **$ELON** room", with the room token's
  name, symbol and image (door 0's face);
- the rule that fired, with its normalised keys. For example: "same name and
  ticker after normalisation: `$EL0N` → `ELON`";
- the room's state at the decision slot:
  - reserve (or pool depth);
  - time since last trade (or LP fees in the last window);
  - number of doors;
  - age;
  - graduated or not;
  - share of supply held by the top 10 holders;
- what the launcher gets: 60% of the fees on trades through their door;
- what their first buy does: it buys at the room's current price, not at a
  floor;
- what it costs: rent of 0.012584 SOL for a door.

**For a new room:**

- "This launches as a **new room**";
- the closest rooms that matched but failed the gate, with the reason. For
  example: "the $ELON room matched by name and ticker, but has had no trade
  for 3 days, so you get a new room";
- the rent: 0.033213 SOL.

**What happens on each path:**

| action | result |
|---|---|
| **Confirm** | The launcher signs the co-signed transaction. The program re-checks the gate and the floor at execution. If the room died or a floor room appeared in between, the transaction fails and the frontend asks the matcher again. |
| **Back out** | Nothing is sent. No transaction, no rent, no record. |

There is no "launch as a new room anyway" option. The launcher never chooses.
Editing the name, symbol or image and asking again is possible, and is
evasion (§9.1).

**Backing out costs nothing.** Anyone who backs out was going to launch
elsewhere anyway, so the preview loses the platform nothing it would otherwise
have had. And it is the launcher's protection against a bad route: no launch
is swallowed into a room its launcher did not see.

## 7. Error asymmetry and the operating point

**The two errors cost different amounts:**

- **A false negative** gives a vamp its own room. That is today's status quo.
  The cost is a split market that a door would have consolidated.
- **A false positive** puts a genuinely new coin into someone else's market
  permanently. Its first buy moves another room's curve, and its door can
  never leave.

So a false positive is weighted far heavier, and the operating point is chosen
by precision first. Measured on the sample, text only, every room live
(§10.3):

| operating point | precision (est.) | pessimistic | recall of vamps (est.) |
|---|---|---|---|
| floor only (on-chain) | 100% | 100% | 83.5% |
| T3 | 100% | 100% | 84.1% |
| **T3 + T2n (v1)** | **99.8%** | **99.6%** | **87.4%** |
| T3 + T2s | 91.2% | 87.5% | 85.0% |
| T3 + T2n + T2s | 90.8% | 87.1% | 87.2% |
| + all T1 | 75.9% | 70.2% | 81.5% |

**Chosen: T3 + T2n.**

- Adding symbol-only routing buys no recall: 87.2% against 87.4%. It costs
  about nine points of precision, since one symbol-only route in ten would
  swallow a different coin.
- Adding fuzzy routing loses both. Wrong rooms then absorb the copies that
  follow them, so recall falls too.
- **The liveness gate then keeps about 45% of routes** (§4.1). Overall recall
  is therefore about 39% of text-findable vamps, above the owner's 20–30% bar.
  The copies the gate drops are copies of rooms holding under 1 SOL.
- **The headroom is thinner than the text numbers suggest.** Measured recall
  counts only copies that text can find (§10.1). Deliberate evasion will lower
  it (§9.1).
- If recall falls under the bar in production, **lower `R_min` before
  loosening the text rule.** The text rule's errors are permanent; a lower
  reserve floor only makes poisoning cheaper.

## 8. Program changes for the engineer

| change | detail |
|---|---|
| `Config` | `+ matcher_authority: Option<Pubkey>` (33 bytes from `reserved[64]`). Admin instruction `set_matcher_authority(Option<Pubkey>)`; `None` = floor-only mode. |
| `create_room` | Drop the `slug` argument; derive it: `identity = sha256(fold(symbol) ‖ 0x00 ‖ fold(name))`, SlugLock seeds `["slug", identity]` (32-byte seed). Require the `matcher_authority` signer when set. If the SlugLock exists and its room **passes** the gate, fail: this must be a door. If it exists and the room **fails** the gate, take it over (re-point `room_id`). If it is absent, create it. Takeover needs the holder `Room` (and its pool when graduated) as read-only accounts. |
| `open_door(room, …)` | Require the matcher signer. Check the gate on `room`. Derive the candidate's identity SlugLock; if it is held by a live room other than `room`, fail (the floor wins). Accounts: `+ matcher_authority` (signer), `+ slug_lock` (read; may be uninitialised), `+ damm_pool` (read, status 2 only). The count goes from 13 to 16, within the 64-lock limit. |
| `Room` | `+ fee_ckpt: u128, fee_ckpt_ts: i64, last_window_fee: u64, identity: [u8; 32]`: 64 bytes, exactly `reserved[64]`. Size unchanged at 684 bytes; `reserved` is used up. |
| `Door` | `+ matcher_version: u16, rule: u8, face: u8, phash: u64` (12 of `reserved[32]`). |
| new crank | `checkpoint_pool(room)`, permissionless (§4.2). |
| `release_slug` | Its condition becomes "the room fails the liveness gate", for every status (§0.4). |
| events | `DoorOpened` and `RoomCreated` carry `matcher_version`, `rule`, `face`, `phash`, `image_sha256`. |
| gate constants | `R_min`, `T_idle`, `W`, `F_min` in `Config`; changing them is an admin action logged on-chain. |

The matcher service:

- fetches the image from the URI and computes the pHash;
- reads candidate rooms from an index of the program's accounts (the Room,
  Door and mint metadata it already needs for the frontend);
- runs `decide`;
- partially signs.

The fuzzy candidate search uses the inverted index from `calibrate_text.py`
(symbol key, name key, name tokens, single-deletion variants). All 2,956
launches replay through it in under a second.

## 9. Adversarial

### 9.1 Evading the matcher deliberately

**Cost: zero.**

- Change both the ticker and the name beyond what folding undoes:
  `ELON`/`Elon` → `ELONN`/`Elonn`. That drops below T2n, and even below T1
  (`ELONN` vs `ELON`: one edit, but `ELON` is shorter than 5).
- Backing out is free (§6), so a launcher can iterate on the preview until it
  says "new room".

**How common it already is, without anyone trying:**

- The sample holds an estimated 1,979 vamps, of which 1,674 are certain
  (identical identity or metadata).
- About 300 (15%) already differ in name or ticker. The v1 rule misses most
  of those, and the 87% recall reflects that.

**Is an evaded launch still worth launching?** It no longer carries the exact
ticker that made the copy worth making. Pump.fun discovery runs through ticker
search and trending lists, and a ticker variant does not inherit the
original's.

Nothing here measures how much volume a variant ticker loses, so whether
evasion pays is **not measured**. Images would catch some of it: a variant
name with a re-encoded copy of the original image is T1 + I2 or T2s + I1, and
routes once image routing is on.

### 9.2 Namespace poisoning

**The attack:** register rooms under the 500 commonest words so every later
launch lands in junk.

**What stops it:**

- **A junk room fails the gate.** It needs `reserve ≥ R_min` and a recent
  trade. A launch matching a dead junk room gets a new room and takes over
  the SlugLock.
- **To keep K rooms live, the attacker must hold `R_min` of capital in every
  one**, plus refresh trades:

  From `outputs/narrative/gate_costs.md`, at `R_min` = 1 SOL:

  | K rooms | rent, once (SOL) | capital locked (SOL) | refresh cost per day (SOL) |
  |---|---|---|---|
  | 10 | 0.33 | 10 | 0.0036 |
  | 100 | 3.32 | 100 | 0.0360 |
  | 500 | 16.61 | 500 | 0.1800 |

- **The capital is not lost.** It is a long position in K illiquid rooms, so
  the real cost is its risk and its opportunity cost.
- **What the gate does is turn a free attack into a capital-bound one.** It
  does not make poisoning impossible.
- **What a poisoner gains:** routed launches buy into rooms where the poisoner
  holds early supply. The preview shows that concentration (§6), and the
  launcher can back out.

### 9.3 Wash-trading a dead room back to "live"

**Before graduation, with the brief's two fields:**

- **Refreshing `last_trade_at`** costs one buy and sell of any size through a
  door the attacker owns. The fee is 1% each side, and 60% of it comes back to
  the attacker's own door: net 0.4% of notional each side, plus transaction
  fees.
  - At a 0.01 SOL trade that is 0.00009 SOL per refresh
    (`outputs/narrative/gate_costs.md`).
  - **This is effectively free.**
- **The reserve is the only real barrier.** A dead room with no reserve needs
  `R_min` bought in, which is capital at risk. Putting it in and taking it
  out costs 0.8% net.
- **The weak case is a dead room that already holds reserve**, with
  bagholders who never sold. Any holder can keep it "live" for a fraction of a
  cent a day.

**Recommended hardening (an owner decision, §0.5):**

- Replace "a trade within `T_idle`" with "gross volume in the last window ≥
  `V_min`", checkpointing the existing `Room.volume_gross` the same way the
  pool fee is checkpointed after graduation.
- Faking it then costs `V_min × 0.8%` per window, paid to the protocol and
  not recoverable. At `V_min` = 5 SOL a day: 0.04 SOL per room per day, or
  20 SOL a day for 500 rooms.
- This also makes the pre- and post-graduation gates the same shape.

**After graduation:**

- To lift `total_lp_b_fee` by `F_min`, the attacker must trade `F_min / 0.8%`
  of volume on the pool and pay 1% of it, all lost.
  - 80% goes to the protocol's locked position, 20% to Meteora.
  - Routing through the program's door route costs more: it adds the program
    fee.
- Per window, faking costs `1.25 × F_min`.

- **At `F_min` = 0.08 SOL**, that is 10 SOL of volume and 0.1 SOL lost per
  room per day (`outputs/narrative/gate_costs.md`).

### 9.4 A compromised or malicious matcher

See §2.2 for what it can and cannot do.

**Detection:** an independent re-runner replays every `DoorOpened` and
`RoomCreated` event through the published matcher. A matcher route into a room
the rules do not select is caught within one indexing cycle.

**Response:**

- `set_matcher_authority(new_key)`; or
- `None`, for floor-only mode, until a new key is deployed.

### 9.5 Smaller attacks

- **Front-running the launcher's first buy into the room.** `open_door`'s
  first buy carries `min_tokens_out`, the same slippage guard as any buy.
- **A race between the decision and execution.** The room can die, or a floor
  room can appear, in the ~32 s a blockhash stays valid (`MAX_PROCESSING_AGE`
  = 150 slots, `solana-clock` 4.0.0 `src/lib.rs` L153–155, the version agave
  pins; at the measured 0.215 s per slot). The program re-checks both; the transaction fails, and
  the frontend asks again.
- **Spam on the preview endpoint.** This is off-chain rate limiting, and
  costs the protocol compute only.

## 10. Calibration

### 10.1 Data

**The sample:**

- **2,956 pump.fun launches**: every `create` / `create_v2` of
  `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P` in **slots 463,738,720 to
  463,767,697**;
- block times 2026-10-31 15:27:29 to 17:10:52 UTC (1.72 hours, contiguous);
- from public mainnet RPC.

**How it was collected:**

- **Listing:** `getSignaturesForAddress` on the pump.fun mint-authority PDA
  (`TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM`, seeds `["mint-authority"]`),
  which every launch passes as account 1.
- **Decoding:** each transaction's create instruction yields name, symbol, URI
  and creator (IDL: pump-fun/pump-public-docs @ `639b87fb`).
- **Output:** `outputs/narrative/pump_launches.jsonl`, one row per launch with
  signature and slot.

**Ground truth:**

- **Certain vamps** (no judgement needed): a launch whose folded name and
  symbol both equal an earlier launch's, or whose metadata URI is
  byte-identical to an earlier launch's.
  - 1,674 launches (56.6%) qualify.
  - 1,201 of them are by a different creator.
  - 1,034 have an identical URI, meaning identical metadata JSON and
    therefore an identical image.
- **Different-identity pairs** that any rule links: 1,707.
  - A stratified random sample of 300 (60 per signal, seed 20261031) was
    labelled S (same narrative), D (different) or U (unsure).
  - **The labels are the assistant's (Claude's), from name and symbol only,
    without images. No human has reviewed them.** They are in
    `scripts/narrative/labels_assistant.csv`; overriding any row and
    re-running the calibration updates every table.
- **The label rule:**
  - **S** when both refer to the same specific subject and one differs only
    by decoration: Baby, Faucet, Coin, Official, spelling, or a typo.
    Identical names, even generic ones, are S.
  - **D** when they share only a generic word (cat, pumpkin, sol, bear) or
    mean different things (`The Boring Company` vs `Thick Booty Coin`, both
    `$TBC`).
  - **U** when the subject is shared but the concept differs (`Elon ETF` vs
    `Santa Elon`).

**Recall here is an upper bound.** A copy that changes name and ticker and
keeps only the image is invisible to this ground truth.

### 10.2 Per-signal precision

From `outputs/narrative/text_calibration.md`. A pair is counted in its strongest signal's row.

| signal (strongest between the two) | pairs in sample window | labelled | S | D | U | precision S/(S+D) | 95% CI |
|---|---|---|---|---|---|---|---|
| symbol equal | 332 | 60 | 27 | 17 | 16 | 61% | 47%–74% |
| name equal | 79 | 56 | 55 | 1 | 0 | 98% | 91%–100% |
| containment | 1,034 | 62 | 16 | 31 | 15 | 34% | 22%–48% |
| jaccard | 180 | 60 | 26 | 16 | 18 | 62% | 47%–75% |
| symbol edit 1 | 82 | 60 | 27 | 27 | 6 | 50% | 37%–63% |

### 10.3 Routing replay

The launches are replayed in order. Each is routed against the rooms formed
so far, with every room treated as live; the gate is calibrated separately in
§4.

A route is correct when the launch is the same narrative as the room's door 0.
Unlabelled routes count at their stratum's measured rate.

From `outputs/narrative/text_calibration.md`.

| operating point | rule | rooms formed | launches routed | precision (est.) | precision, pessimistic | recall of vamps (est.) | recall of certain vamps | of different-creator certain vamps | of identical-URI vamps |
|---|---|---|---|---|---|---|---|---|---|
| floor | on-chain floor: ASCII-folded symbol and name both equal | 1,303 | 1,653 | 100.0% | 100.0% | 83.5% | 98.7% | 99.0% | 99.2% |
| T3 | symbol and name equal after full folding | 1,291 | 1,665 | 100.0% | 100.0% | 84.1% | 99.5% | 99.9% | 99.1% |
| T3+name | T3, or name equal after folding (name key >= 4 chars): the v1 text operating point | 1,224 | 1,732 | 99.8% | 99.6% | 87.4% | 99.4% | 99.8% | 99.1% |
| T2-symbol | T3, or symbol equal after folding | 1,112 | 1,844 | 91.2% | 87.5% | 85.0% | 93.9% | 93.3% | 93.8% |
| T2 | T3, or symbol equal, or name equal, after folding | 1,056 | 1,900 | 90.8% | 87.1% | 87.2% | 93.7% | 93.1% | 94.2% |
| T1 | T2, or fuzzy: containment, name-word Jaccard >= 0.5, symbols one edit apart (len >= 5) | 831 | 2,125 | 75.9% | 70.2% | 81.5% | 83.4% | 82.2% | 86.9% |
| raw-symbol | baseline: symbol equal, case-insensitive, no folding | 1,123 | 1,833 | 91.6% | 88.0% | 84.8% | 94.0% | 93.3% | 94.1% |

- **precision (est.):** certain and labelled routes count as 1 or 0. An unlabelled route counts at its stratum's S/(S+D).
- **pessimistic:** unlabelled routes are counted at the stratum's Wilson lower bound, and U labels count as wrong.
- **last three columns:** the denominator is restricted to certain vamps, which need no labels to identify.

**Is the sample big enough?**

- **For the v1 point, yes.** Its precision rests on 1,665 identity routes,
  which need no labels, plus 67 name-equal routes. The name-equal rate has a
  95% interval of 91–100% from 56 labelled pairs. Even at the lower bound,
  overall precision stays above 99%.
- **For the rejected points, no.** The T2s and T1 rates are known only to
  ±13 points. That is enough to reject them, not enough to tune them.

### 10.4 Liveness calibration

From `outputs/narrative/liveness_table.md`, program
`6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`.

**Method:**

- **Copies (A).** 100 certain, different-creator vamps were sampled (seed
  20261031). For each one, and each of up to 8 earlier members of its
  cluster:
  - `getSignaturesForAddress(bonding_curve, before = the copy's signature)`
    gives the member's last transaction before the copy;
  - its pump `TradeEvent` (self-CPI event, IDL @ `639b87fb`) gives
    `real_sol_reserves` after that trade.
- **Random launches (B).** Bonding-curve accounts (`real_quote_reserves` at
  offset 32, `complete` at 48) plus each curve's latest signature were read
  for three groups:
  - 300 launches from the sample;
  - 100 from about a day earlier (anchor slot 463,382,303);
  - 100 from about a week earlier (anchor slot 460,960,575).

**Correction found while measuring: about 29% of pump.fun curves are quoted in
a token other than SOL** (`BondingCurve.quote_mint`; 240 of 820 curves read,
`outputs/narrative/liveness_quote_mints.json`, slots 463,794,996–463,795,004).
Their reserves are not lamports: one read as 4,982 "SOL". Only SOL-quoted
curves are used. Six copies with no SOL-quoted member were dropped, leaving 94.

**A. Copies whose room passes the gate at the copy's launch** (share of 94):

| reserve >= (SOL) | idle <= 10 min | idle <= 1 h | idle <= 6 h | idle <= 24 h |
|---|---|---|---|---|
| 0 | 85% | 93% | 93% | 93% |
| 0.5 | 47% | 47% | 47% | 47% |
| 1 | 45% | 45% | 45% | 45% |
| 2 | 43% | 43% | 43% | 43% |
| 3 | 43% | 43% | 43% | 43% |
| 5 | 41% | 41% | 41% | 41% |
| 10 | 38% | 38% | 38% | 38% |

**B. Random SOL-quoted launches passing the gate at read time:**

| launched | n (not complete) | reserve ≥ 0, idle ≤ 1 h | reserve ≥ 1 SOL, idle ≤ 6 h |
|---|---|---|---|
| in the sample window (1.3–3.0 h old) | 209 | 12.4% | 2.4% |
| about 1 day earlier | 71 | 31.0% | 0.0% |
| about 7 days earlier | 73 | 0.0% | 0.0% |

**Caveats:**

- The day-old group shows more idle-only activity than the younger one. That
  is bots trading the dead coins.
- The samples are small. 0 of 71 has a 95% upper bound of about 5%.
- A cluster member that later completed on pump.fun is included in A with its
  curve trades only.

## 11. Limits, and the data that would fix them

| limit | what fixes it |
|---|---|
| Image precision on real vamps is not measured; image routing is shadow-only. | Allow the metadata and image hosts in §0.2 (or use a pump.fun data export). Then compute pHashes for the 2,956 sampled launches, label the image-assisted routes (T2s + I1, T1 + I2), and enable `image_routing = "on"` if their precision is at T2n's level. Production can log the same in shadow mode for two weeks. |
| Labels are the assistant's, from text only. | A human pass over the 300 rows of `labels_assistant.csv` (about half an hour); re-run `run_calibrate_text.sh`. |
| 1.72 hours on Halloween afternoon. | A week of launches from a non-rate-limited RPC or an indexer export. The collector resumes, so `run_collect_launches.sh N` with a larger N extends the same file. |
| Pre-graduation liveness is calibrated on pump.fun curves as a proxy for doors rooms. | Doors' own room histories once live. pump.fun's curve has the same 30 SOL virtual reserve as doors' (V_sol 30.0009 SOL), which is why it is used. |
| Post-graduation `F_min` has no doors-pool data behind it. | 30 days of `total_lp_b_fee` growth on graduated memecoin pools, read with `run_damm_pool_fields.sh` at intervals. |
| Recall ignores image-only copies. | The same image data as the first row. |

## 12. Reproduce

Run each command on its own, in this order:

```bash
scripts/narrative/run_collect_launches.sh 2956
```

```bash
scripts/narrative/run_calibrate_text.sh
```

```bash
scripts/narrative/run_liveness_reads.sh 100 300
```

```bash
scripts/narrative/run_damm_pool_fields.sh 300
```

```bash
scripts/narrative/run_image_robustness.sh 400
```

```bash
scripts/narrative/run_gate_costs.sh
```

```bash
scripts/narrative/run_matcher.sh
```

**Notes:**

- `run_image_robustness.sh` needs `pip install imagehash==4.3.2` for its
  reference check.
- On-chain reads depend on chain state at read time. The slots read are
  recorded in each output.
