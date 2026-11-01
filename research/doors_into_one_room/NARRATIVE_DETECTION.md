# Narrative detection: door or new room

## Current revision corrections

<!-- BEGIN GENERATED RENT CORRECTION -->
**Approved rent correction.** The old `(128 + bytes) × 6,960` model is stale. The owner approved `(128 + bytes) × 5,080` after direct rent-exemption RPC confirmation. These are `getMinimumBalanceForRentExemption` results, not account balances. The method has no context slot; finalized slot reads bracket each request.

| data bytes | raw minimum (lamports) | finalized slot before | finalized slot after |
|---|---|---|---|
| 0 | 650,240 | 464,037,171 | 464,037,172 |
| 165 | 1,488,440 | 464,037,175 | 464,037,178 |

Additional size checks are recorded at slots 464,036,284–464,036,304 in `outputs/narrative/current_rent.json`; the confirmation is in `rent_confirmation.json`. The current schema's derived totals are:

| quantity | old rate on revised schema | verified rate on revised schema |
|---|---|---|
| launch rent, lamports | 37,256,880 | 27,193,240 |
| graduation rent, lamports | 24,680,160 | 18,013,680 |

All current rent-dependent spec figures are regenerated. The trigger remains a Config value snapshotted into each Room; a later rent/default change does not rewrite an old room's curve or graduation trigger. Runtime graduation uses the rent sysvar, not this calibration coefficient.
<!-- END GENERATED RENT CORRECTION -->

<!-- BEGIN GENERATED BRIEF CORRECTION -->
Source: stored liveness_reads.json, liveness_quote_mints.json and copies.json; no new on-chain values are introduced. Recorded source slots remain in those files.

SOL-quoted copy population: 94; with an activity timestamp: 87.

| metric | median seconds |
|---|---|
| room age, earliest earlier SOL-quoted member's launch | 187.5 |
| room age, earliest earlier member's launch regardless of quote | 202.5 |
| idle, latest recorded member activity | 1 |

The brief's claim that the median target room is one second old confuses last-activity idle time with room age. The recorded idle statistic also includes non-trade signatures; it is the original calibration's activity proxy, not a verified last-trade timestamp.

The owner acknowledged this correction and explicitly authorized continuing with the measured age distribution. The stored copy window alone cannot establish long-run recall; the age-window sweep is in liveness_table.md.
<!-- END GENERATED BRIEF CORRECTION -->

1 November 2026 revision. This document decides, for every launch, whether the coin becomes
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
2. **Real-image calibration rejects enabling the proposed rule.** The
   original environment could not fetch token images. The current fetch uses
   the original sample and same-CID gateways, records byte hashes and failures,
   and measures real-image precision, recall, edits and entropy (§3.2).
   No unfiltered Hamming threshold preserves the strict text point's precision.
   The owner explicitly approved retaining shadow mode and requested the
   entropy test. A stringent filter shows a small in-sample improvement that
   needs new validation; it is not enabled. Historical Twemoji measurements
   are archived outputs and are not evidence for this revision.
3. **The spec lets the caller choose the room, which the settled rule
   forbids.**
   - `open_door(room, …)` takes the room as an argument, and
     `create_room(slug, …)` takes a launcher-chosen slug.
   - Both now require the matcher's co-signature over the decision, and the
     slug is derived from door 0's identity (§8).
4. **SlugLock now uses the routing gate.** The owner explicitly adopted this
   change. A lock is releasable exactly when its holder fails §4, including
   after graduation; there is no independent expiry policy.
5. **The existing idle-only refresh was too cheap, and the proposed wash-cost
   calculation doubled gross volume.** The trailing-volume floor is now
   adopted. Both legs contribute to `volume_gross`; net protocol cost is the
   fee rate times the protocol share times total gross volume. The regenerated
   costs are in §9. A cumulative counter needs bounded history to establish a
   trailing window: this revision uses tagged hourly buckets and fails
   conservatively where timing is unknown. The old previous-window fallback
   could count activity older than the advertised window and is removed.
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
| v1 operating point | Route only on equal folded identity, or equal folded name. Measured **precision 99.8%** (pessimistic 99.6%), **recall 87%** before the gate; sampled gate retention with age is 100%, with full-gate no-age bounds in §4.1. The product across populations is an extrapolation. |
| liveness | New rooms: age < 2 h. Mature curve: reserve ≥ 0.5 SOL, idle ≤ 6 h, trailing gross volume ≥ 5 SOL/24 h. Mature pool: trailing LP fee ≥ 0.08 SOL/24 h, from the cumulative pool counter via conservative room checkpoints (§4). |
| ties | Floor room first, then score, text tier, image distance, SOL depth, lowest `room_id` (§5). |
| preview | The launcher sees the exact decision and the room's state, then confirms or backs out. Backing out costs nothing (§6). |

## 2. Trust model

### 2.1 What was chosen

There are three layers. Each one is checkable by someone other than the
matcher.

1. **Protocol-operated matcher, co-signing.**
   - `Config` gains `matcher_authority: Pubkey`.
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
| **Refuse to sign**, so launches stop. | No funds are moved. Rotate the matcher key through the admin instruction; every launch continues to require the configured authority. |
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
  - `face: u32`, the door index matched (same width as the door index);
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

**Real-token reference check:**

<!-- BEGIN GENERATED REAL PHASH CHECK -->
imagehash 4.3.2, 500 images: 500 identical 64-bit hashes; 0 images differ on a non-tie bit; 1 images have exact median ties (64 tie bits in total), where imagehash's bit is floating-point noise
<!-- END GENERATED REAL PHASH CHECK -->

**Real-image calibration:**

The complete original launch population is retained. Downloads and failures,
metadata/image URIs, SHA-256 values and hashes are in `token_images.jsonl`;
coverage is in `image_fetch_summary.json`. Images stay in the ignored local
cache. The same IPFS CID can be fetched from another gateway; another corpus
is never substituted. SHA-256 pins what was inspected even for mutable hosts.

<!-- BEGIN GENERATED IMAGE CALIBRATION -->
<!-- generated by scripts/narrative/calibrate_images.py -->

Original sample: 2956 launches; 2692 have decoded images. Same fixed expected-vamp denominator as the text calibration: 1979.010; certain-vamp denominator 1674. Missing images score zero. Additional image-aware pair judgements are by the assistant, not a human; the CSV records the inspected root/candidate image hashes and rationale. The original text population stays fixed for comparisons.

| strong / weak Hamming | routed | precision (est.) | pessimistic | recall (est.) | certain recall | image-assisted routes | assisted precision (est.) | assisted pessimistic | assisted labelled/certain |
|---|---|---|---|---|---|---|---|---|---|
| text only | 1732 | 99.83% | 99.58% | 87.37% | 99.42% | 0 | 0.00% | 0.00% | 0 |
| 0 / 0 | 1797 | 99.10% | 98.58% | 89.99% | 98.90% | 68 | 96.20% | 94.12% | 68 |
| 2 / 2 | 1803 | 99.05% | 98.53% | 90.24% | 98.90% | 74 | 95.15% | 93.24% | 74 |
| 4 / 4 | 1805 | 99.01% | 98.53% | 90.30% | 98.90% | 77 | 94.42% | 93.51% | 77 |
| 6 / 6 | 1807 | 99.01% | 98.53% | 90.40% | 98.90% | 79 | 94.57% | 93.67% | 79 |
| 8 / 8 | 1807 | 99.01% | 98.53% | 90.40% | 98.90% | 79 | 94.57% | 93.67% | 79 |
| 10 / 10 | 1808 | 99.01% | 98.53% | 90.46% | 98.90% | 81 | 94.70% | 93.83% | 81 |
| 12 / 12 | 1810 | 99.01% | 98.53% | 90.56% | 98.90% | 84 | 94.89% | 94.05% | 84 |
| 14 / 14 | 1816 | 98.98% | 98.43% | 90.83% | 98.90% | 89 | 94.45% | 92.13% | 89 |
| 16 / 16 | 1821 | 98.77% | 98.10% | 90.88% | 98.82% | 94 | 93.06% | 89.36% | 94 |
| 10 / 16 | 1817 | 98.90% | 98.27% | 90.80% | 98.88% | 89 | 94.19% | 91.01% | 89 |

| strong / weak | assisted S | D | U | unlabelled | assisted S/(S+D) |
|---|---|---|---|---|---|
| 0 / 0 | 64 | 2 | 2 | 0 | 96.97% |
| 2 / 2 | 69 | 3 | 2 | 0 | 95.83% |
| 4 / 4 | 72 | 4 | 1 | 0 | 94.74% |
| 6 / 6 | 74 | 4 | 1 | 0 | 94.87% |
| 8 / 8 | 74 | 4 | 1 | 0 | 94.87% |
| 10 / 10 | 76 | 4 | 1 | 0 | 95.00% |
| 12 / 12 | 79 | 4 | 1 | 0 | 95.18% |
| 14 / 14 | 82 | 4 | 3 | 0 | 95.35% |
| 16 / 16 | 84 | 5 | 5 | 0 | 94.38% |
| 10 / 16 | 81 | 4 | 4 | 0 | 95.29% |

Replayed in launch order through matcher.decide, including multi-face scoring and ties. All rooms formed inside this short sample are younger than the chosen grace window; no pre-window rooms are assumed. Ground truth follows the text calibration: identical folded identity/metadata URI is certain; assistant S/D/U narrative labels judge other pairs. Unlabelled routes take their text-stratum rate; pessimistic uses its Wilson lower bound and counts U as wrong. These are estimates, with selection bias possible for image-assisted unlabelled pairs. Image labels were collected from a union of assisted routes, not a held-out validation set. Estimates remain in-sample. Incremental assisted precision is reported separately so existing exact routes cannot conceal poor image precision. The review CSV exposes every assisted narrative pair.

At Hamming 0/0, combined recall is 89.99% versus text-only 87.37%, a 2.62 percentage-point gain; precision falls from 99.83% to 99.10%. No tested threshold reaches the text point's precision. The justified production choice is to retain shadow mode; its active image-recall gain is zero. Enabling the measured points would require accepting more permanent false-positive routes or revising the image rule.
<!-- END GENERATED IMAGE CALIBRATION -->

**Robustness on real token images:**

These edited positives are separate from semantic narrative labels. The
experiment replaces the Twemoji robustness claims rather than carrying them
over. Full threshold sweeps and per-edit distances are in
`real_image_robustness.md` and `.json`.

<!-- BEGIN GENERATED REAL ROBUSTNESS -->
Real-image corpus: 1206 distinct byte hashes; 400 edit-positive sources; seed 20261031. Images decoded for 2692/2956 launches; 262 metadata failures and 2 image failures.

| edit | within Hamming 10 | within Hamming 16 |
|---|---|---|
| re-encode JPEG q85 | 99.2% | 99.5% |
| JPEG q40 | 99.5% | 99.5% |
| rescale to 128 px | 99.5% | 99.5% |
| rescale to 512 px | 99.5% | 99.8% |
| hue rotate 60 deg | 93.5% | 99.0% |
| hue rotate 180 deg | 82.2% | 94.5% |
| grayscale | 100.0% | 100.0% |
| centre crop 5% | 97.0% | 99.5% |
| centre crop 10% | 63.5% | 95.8% |
| centre crop 20% | 3.5% | 27.3% |
| caption bar (bottom 15%) | 69.5% | 94.0% |
| sticker in corner (1/16 area) | 49.8% | 85.0% |
| mirror (left-right) | 0.0% | 0.0% |
<!-- END GENERATED REAL ROBUSTNESS -->

**Low-detail filtering, requested after the initial result:**

<!-- BEGIN GENERATED IMAGE ENTROPY -->
<!-- generated by scripts/narrative/calibrate_image_entropy.py -->

Entropy is Shannon bits on the alpha-flattened 32x32 grayscale pHash input. Both candidate and matching face must pass the cutoff. Fixed original text vamp denominator; same assistant labels as image calibration. No threshold is enabled by this experiment.

| Hamming | minimum entropy (bits) | eligible launch images | routed | precision (est.) | recall (est.) | assisted | assisted precision (est.) | unlabelled assisted |
|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 2692 | 1797 | 99.10% | 89.99% | 68 | 96.20% | 0 |
| 0 | 2 | 2648 | 1796 | 99.10% | 89.94% | 67 | 96.14% | 0 |
| 0 | 3 | 2557 | 1794 | 99.10% | 89.83% | 65 | 96.02% | 0 |
| 0 | 4 | 2391 | 1789 | 99.10% | 89.58% | 60 | 95.69% | 0 |
| 0 | 5 | 2201 | 1785 | 99.07% | 89.36% | 56 | 95.38% | 0 |
| 0 | 6 | 1900 | 1779 | 99.07% | 89.05% | 50 | 94.83% | 0 |
| 0 | 7 | 947 | 1757 | 99.38% | 88.23% | 28 | 95.38% | 0 |
| 0 | 7.25 | 593 | 1752 | 99.72% | 88.28% | 21 | 100.00% | 0 |
| 0 | 7.5 | 152 | 1741 | 99.83% | 87.82% | 9 | 100.00% | 0 |
| 0 | 7.75 | 1 | 1732 | 99.83% | 87.37% | 0 | 0.00% | 0 |
| 0 | 8 | 0 | 1732 | 99.83% | 87.37% | 0 | 0.00% | 0 |
| 10 | 0 | 2692 | 1808 | 99.01% | 90.46% | 81 | 94.70% | 0 |
| 10 | 2 | 2648 | 1807 | 99.01% | 90.40% | 80 | 94.63% | 0 |
| 10 | 3 | 2557 | 1805 | 99.01% | 90.30% | 78 | 94.50% | 0 |
| 10 | 4 | 2391 | 1800 | 99.01% | 90.05% | 73 | 94.12% | 0 |
| 10 | 5 | 2201 | 1795 | 98.98% | 89.78% | 68 | 93.69% | 0 |
| 10 | 6 | 1900 | 1788 | 99.03% | 89.47% | 61 | 94.60% | 0 |
| 10 | 7 | 947 | 1758 | 99.38% | 88.28% | 30 | 95.69% | 0 |
| 10 | 7.25 | 593 | 1752 | 99.72% | 88.28% | 21 | 100.00% | 0 |
| 10 | 7.5 | 152 | 1741 | 99.83% | 87.82% | 9 | 100.00% | 0 |
| 10 | 7.75 | 1 | 1732 | 99.83% | 87.37% | 0 | 0.00% | 0 |
| 10 | 8 | 0 | 1732 | 99.83% | 87.37% | 0 | 0.00% | 0 |

| unfiltered Hamming | known wrong root | candidate | root entropy | candidate entropy | matched-face entropy | matched door index | matched distance |
|---|---|---|---|---|---|---|---|
| 0 | HALLOWEEN COIN  | Happy Halloween | 7.14 | 7.18 | 7.18 | 4 | 0 |
| 0 | Pizza Coin | Dobriks Pizza Coin | 7.53 | 6.83 | 6.83 | 3 | 0 |
| 10 | The Kong | The Llama | 6.68 | 6.81 | 6.68 | 0 | 4 |
| 10 | Golden Dragon Coin | Golden Doge | 6.51 | 5.89 | 6.51 | 0 | 2 |
| 10 | HALLOWEEN COIN  | Happy Halloween | 7.14 | 7.18 | 7.18 | 4 | 0 |
| 10 | Pizza Coin | Dobriks Pizza Coin | 7.53 | 6.83 | 6.83 | 3 | 0 |

Root-image entropy is diagnostic; the runtime filter applies to the matched face, which can be a later door. Equal hashes at a later face do not establish narrative identity with the root. Image labels are in-sample assistant judgements; a labelled false pair is evidence of a concrete failure, not a population-level error guarantee.

The strict 7.5-bit filter at Hamming 0 leaves 152 eligible launch images and 9 assisted routes, with estimated assisted precision 100.00% and 0 unlabelled. Combined recall is 87.82%, a 0.45 percentage-point gain over the same text baseline; overall precision is 99.83%. This is a small, post-selection result without held-out or human validation. It motivates validation on a new sample rather than switching on the rule. The approved production choice remains shadow mode.

Among known unfiltered Hamming-0 errors, 2/2 matched later doors. The lowest matched-face entropy is 6.83 bits. These observed failures are not explained by plain-colour images; mild entropy cutoffs do not solve identity drift through later faces.
<!-- END GENERATED IMAGE ENTROPY -->

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
- Retain shadow mode after the real-image result above. The narrow entropy
  candidate needs a new held-out sample and human label review before adoption.
- Shadow image hashes do not influence tie-breaking or face selection; the
  previous prototype used image distance in ties even when scoring was off.
  A regression check now enforces the text-only shadow decision.

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

### 4.1 One gate, for routing and slug release

```
live(room) = age(room) < T_new
          OR (status < 2 AND reserve >= R_min AND idle <= T_idle
                          AND trailing_volume_lower_bound >= V_min)
          OR (status == 2 AND trailing_lp_fee_lower_bound >= F_min)
slug_releasable(room) = NOT live(room)
```

Age is `now - room.created_at`, with the program clock and immutable creation
stamp. Missing or future creation stamps fail closed. This applies to status
0 (curve), 1 (complete), and 2 (graduated). The target is checked at execution;
being complete does not confer permanent liveness. Trading and opening a door
do not reset creation time. A released room keeps trading by id and its doors
remain open for its life.

Defaults are in `matcher.py`: `T_new` = 2 h, `R_min` = 0.5 SOL, `T_idle` = 6 h,
`V_min` = 5 SOL gross per 24 h, `F_min` = 0.08 SOL LP fee per 24 h.
The reserve floor rejects every sampled day-old and week-old curve at the
lowest tested positive floor. The age sweep below chooses the smallest tested
whole-hour grace window retaining all sampled copies. It achieves the same
sample retention as the brief's 6 h starting point, with less rent-only
poisoning time. The short collection window limits this conclusion.

The original reserve/idle calibration remains a baseline. Its activity times
include non-trade signatures, and it lacks historical trailing volume. We
therefore report bounds for the full gate without age. Every sampled target
is young under the chosen window, so retention with age is known even without
volume history. These are copy-population retention figures, not an end-to-end
text+image routing replay.

<!-- BEGIN GENERATED SELECTED GATE -->
Defaults from matcher.py: reserve >= 0.5 SOL; idle <= 6 h.

| population | passing | total | share |
|---|---|---|---|
| sampled copies, selected floor | 44 | 94 | 46.8% |
| sampled copies, previous 1 SOL floor | 42 | 94 | 44.7% |
| launched in the sample window | 6 | 209 | 2.9% |
| launched about 1d before the read (anchor slot 463,382,303) | 0 | 71 | 0.0% |
| launched about 7d before the read (anchor slot 460,960,575) | 0 | 73 | 0.0% |

Approximate text-findable-vamp recall: 87.4% (rounded all-live text replay) x 44/94 (sampled gate retention) = 40.9%; previous floor: 39.1%. This is a proxy product across different populations, not an end-to-end routing replay.

### D. Age-aware gate calibration

Recorded SOL-member age at copy time: median 187.5 s; p90 3119 s; p99 5560 s; maximum 5560 s. Quantiles use sorted[min(n-1, floor(p*n))]. Age is measured from the earliest earlier member with a recorded SOL quote; it is a proxy for room creation.

| T_new | young copies | copies live, reserve+idle+age | with volume floor, lower–upper bound |
|---|---|---|---|
| 0 h | 0/94 | 44/94 (46.8%) | 0.0%–46.8% |
| 0.0166667 h | 34/94 | 58/94 (61.7%) | 36.2%–61.7% |
| 0.0833333 h | 54/94 | 62/94 (66.0%) | 57.4%–66.0% |
| 0.166667 h | 60/94 | 67/94 (71.3%) | 63.8%–71.3% |
| 0.25 h | 65/94 | 72/94 (76.6%) | 69.1%–76.6% |
| 0.5 h | 74/94 | 78/94 (83.0%) | 78.7%–83.0% |
| 1 h | 86/94 | 86/94 (91.5%) | 91.5%–91.5% |
| 1.5 h | 93/94 | 93/94 (98.9%) | 98.9%–98.9% |
| 2 h | 94/94 | 94/94 (100.0%) | 100.0%–100.0% |
| 6 h | 94/94 | 94/94 (100.0%) | 100.0%–100.0% |

Selected T_new = 2 h: the smallest tested whole-hour window keeping every sampled copy, with the same sample retention as the brief's starting window. This short collection window cannot establish long-run recall; all its targets are young.

| population at read time | young | age+reserve+idle passing | with volume floor, lower–upper bound |
|---|---|---|---|
| launched in the sample window | 93/209 | 95/209 | 44.5%–45.5% |
| launched about 1d before the read (anchor slot 463,382,303) | 0/71 | 0/71 | 0.0%–0.0% |
| launched about 7d before the read (anchor slot 460,960,575) | 0/73 | 0/73 | 0.0%–0.0% |

Same 94-copy population, with volume floor: without age, retention is only bounded at 0–46.8%; with the chosen age clause it is 100.0%. Gain is at least 53.2 percentage points. Historical trailing volume was not collected, so the no-age value is an upper bound, not a measured full-gate recall.

The old text-recall product would become 87.4% with age, but remains an extrapolation across populations. No combined text+image end-to-end result is implied.
<!-- END GENERATED SELECTED GATE -->

### 4.2 Conservative trailing accounting

`Room.volume_gross` remains cumulative. Every curve trade records its exact
increment in a tagged hourly bucket. Both buy and sell legs count toward gross
volume. Program-tracked volume is used before graduation; pool LP fees are
used after it. They have separate units and the history is cleared on
`graduate`.

The room stores a bounded ring of timestamped counters. The gate sums only
buckets whose **start** lies within the trailing window. The oldest partially
overlapping hour is discarded. Thus counted curve volume is a lower bound on
actual trailing volume, with less than one hour of conservative loss. There
is no previous-window fallback that can carry old activity forward.

For graduated rooms the source is DAMM v2
`Pool.metrics.total_lp_b_fee`, a cumulative WSOL LP-fee counter (the verified
pool field at offset 584 in its 1,112-byte account). Pool liquidity cannot
measure swaps (§0.1). `checkpoint_pool(room)` is permissionless and validates
pool address = `room.damm_pool`, owner = DAMM v2, discriminator, length and
WSOL token-B identity. The checkpoint contains the counter value and the
observation time.

An unread counter increment occurred somewhere between the previous
observation and now. Conservatively assign it to the hour containing the
**previous observation time**, then update the checkpoint. If that hour is
already outside the trailing window, discard the increment. Reading a stale
counter must never turn old fees into a new full window. The read-only gate
also includes a valid unread increment using this same dating rule, so its
result agrees immediately before and after checkpointing. Counter regression
or a future checkpoint fails closed. Frequent cranking reduces conservative
loss; a missing long interval cannot establish when fees were earned.

The same helper is used by routing, lock takeover and `release_slug`.
Checkpointing is independent of whether a room currently passes. Initial pool
checkpoint = the actual counter at graduation, with empty fee buckets.

The LP-fee floor remains a policy assumption, not a calibrated doors-pool
threshold. No such pools exist yet. Gate costs use the spec's explicitly
assumed pool fee configuration; no fresh mainnet rent or fee reading is
claimed. Account layouts and rent are generated by `account_sizes.py`.

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
- what it costs: the current per-door rent in the generated build-spec tables.

**For a new room:**

- "This launches as a **new room**";
- the closest rooms that matched but failed the gate, with the reason. For
  example: "the $ELON room matched by name and ticker, but has had no trade
  for 3 days, so you get a new room";
- the current rent from the generated build-spec tables and recorded rent RPC check.

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
- **The age clause keeps every sampled target** (§4.1). The reserve-only
  baseline and full-gate no-age bounds are generated there. Applying that
  retention to the all-live text result is a cross-population extrapolation;
  it does not measure full routing recall.
- **The headroom is thinner than the text numbers suggest.** Measured recall
  counts only copies that text can find (§10.1). Deliberate evasion will lower
  it (§9.1).
- If recall falls under the bar in production, **lower `R_min` before
  loosening the text rule.** The text rule's errors are permanent; a lower
  reserve floor only makes poisoning cheaper.

## 8. Program changes for the engineer

The account schemas and instruction variants are generated in
`outputs/account_sizes.md` and `outputs/instruction_accounts.md`, and included
in the build spec. The schemas now include the activity history rather than
claiming it fits in old reserve bytes.

| change | required behavior |
|---|---|
| `Config` | Mandatory matcher public key and one shared set of liveness thresholds. Admin may rotate the key; there is no unsigned fallback. |
| `create_room` | No supplied slug. Derive the identity from door 0's name and symbol. Require the matcher signature. A live lock holder forces a door; a dead holder can be replaced atomically. Validate/read the former holder and its pool when required. |
| `open_door` | Target room is a matcher-selected account covered by the transaction signature. Recheck liveness and the candidate identity's floor. A distinct identity holder and its pool must also be checked; the earlier account-count estimate omitted these. |
| `Room` | Immutable creation timestamp, identity hash, tagged activity history and cumulative pool checkpoint. Curve gross volume counts the buy fee base and gross sell proceeds, excluding the program fee; both legs count. |
| `Door` | Store version, rule, matched door index and pHash in reserve bytes. Use the full door-index width for `face`; the earlier byte-sized field could not address all doors. |
| `checkpoint_pool` | Permissionless conservative accumulation from the validated DAMM v2 counter. |
| `release_slug` | Exactly the complement of the routing gate; validate the lock's current holder. Works before and after graduation. |
| events | Version, rule, face, pHash and image byte digest make the signed decision auditable. |

The matcher service reads configuration and candidate state, fetches the image,
computes its hash, runs the published decision rule, then partially signs the
previewed transaction. Image evidence is logged in shadow mode. The program
checks the floor and gate independently at execution. The reference here is
an executable matcher and a build specification; no on-chain program has yet
been built or benchmarked.

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

### 9.2 Namespace poisoning and gate costs

Registering common identities once no longer poisons the namespace forever.
An unfunded room ages out; its SlugLock can be released or taken over only
when the same routing gate fails. A poisoner must recreate rooms repeatedly
or fund mature rooms and keep paying the volume floor. The matcher still
controls every creation; launches cannot reset the old room's timestamp.
This closes persistent poisoning from one registration, while recurring
poisoning remains possible at the measured cost below.

This is a **defacement attack**: door 0 fixes the room token's name and image.
There is no founder share. Merely owning the squatted room's door 0 earns
nothing from later doors' trades. These rent-only estimates do not assume a
position that profits from later buyers. SlugLock rent can be reclaimed by
the cleanup caller; room and door rent remains locked.

<!-- BEGIN GENERATED POISONING COSTS -->
<!-- generated by scripts/narrative/gate_costs.py -->
New-room grace 2 h; mature reserve >= 0.5 SOL, idle <= 6 h; gross trailing volume >= 5 SOL per 24 h. Mature pool LP-fee floor 0.08 SOL per window.

| item | lamports | SOL |
|---|---|---|
| launch room and door 0, max-metadata rent | 27,193,240 | 0.027193 |
| only reclaimable rent: SlugLock, if attacker wins cleanup | 736,600 | 0.000737 |
| mature curve: reserve held as capital | 500,000,000 | 0.500000 |
| mature curve: gross volume per day, both legs counted | 5,000,000,000 | 5.000000 |
| mature curve: protocol fees lost per day, own-door rebate claimed | 20,000,000 | 0.020000 |
| illustrative two-transaction round trip signature fees (additional) | 10,000 | 0.000010 |
| mature pool: volume per window to generate LP-fee floor | 10,000,000,000 | 10.000000 |
| mature pool: pool fees lost per window (no LP ownership) | 100,000,000 | 0.100000 |

**Namespace poisoning by repeated young-room creation** (unfunded rent-only defacement):

| K identities | rooms created per day | rent/day if each lock recreated (SOL) | steady-state rent/day reusing the lock (SOL) |
|---|---|---|---|
| 10 | 120 | 3.263189 | 3.174797 |
| 100 | 1200 | 32.631888 | 31.747968 |
| 500 | 6000 | 163.159440 | 158.739840 |

**Namespace poisoning by mature rooms held live**:

| K rooms | rent once (SOL) | reserve capital (SOL) | protocol fees lost per day at volume floor (SOL) |
|---|---|---|---|
| 10 | 0.271932 | 5 | 0.200000 |
| 100 | 2.719324 | 50 | 2.000000 |
| 500 | 13.596620 | 250 | 10.000000 |

**Grace-window sensitivity at the verified rent**:

| grace (h) | copies covered by grace | rent/day for 500 identities with new locks (SOL) | recurring rent/day reusing locks (SOL) |
|---|---|---|---|
| 0.5 | 74/94 | 652.637760 | 634.959360 |
| 1 | 86/94 | 326.318880 | 317.479680 |
| 1.5 | 93/94 | 217.545920 | 211.653120 |
| 2 | 94/94 | 163.159440 | 158.739840 |
| 6 | 94/94 | 54.386480 | 52.913280 |

Keep the measured 2 h default: it is the shortest tested whole-hour window covering every copy. The reduced rent still makes unfunded repeated creation materially more expensive than the mature funded strategy in the table. A tighter window would drop measured copies without raising the mature strategy cost; it is not justified by this sample. Small targeted squats remain affordable; this is not an economic guarantee.

No founder share exists. Merely owning door 0 earns nothing; later launches use their own doors. The rent-only attacker controls the room token name and image: defacement. Wash costs assume ownership of the trading door and its fee rebate; exclude transaction fees unless shown, integer rounding, capital opportunity cost and third-party trading. The attacker does not own the protocol LP. Atomic takeover reuses the same SlugLock: the steady-state recurring creation cost excludes its rent, which is paid once per identity. Closing and reclaiming a lock before recreating it has the same net rent if the attacker wins cleanup, with extra transaction work. One registration stops working after grace; recurring rent or volume fees can sustain poisoning. Hourly trailing lower bounds may require more volume than this optimistic attack-cost floor. Signature fees and pool fee configuration are assumptions, not current on-chain readings.
<!-- END GENERATED POISONING COSTS -->

### 9.3 Penny refreshes and trailing volume

A mature room with old bagholders may retain reserve. A tiny fresh trade
satisfies idle time but cannot satisfy the trailing-volume floor; cumulative
lifetime volume does not qualify. Wash-cost arithmetic counts both trade
legs in gross volume, then applies the fee and protocol share once. Owning
the trading door permits its fee rebate, and the cost table includes that
optimistic attacker case. Transaction fees, external trading and rounding
can increase cost.

After graduation the protocol owns the locked LP position; an attacker
cannot reclaim its fee merely by owning door 0. Direct pool trades contribute
through the pool counter, even when they never pass through this program.
A stale checkpoint discards unknown-age growth rather than accepting it as
recent activity.

### 9.4 A compromised or malicious matcher

See §2.2 for what it can and cannot do.

**Detection:** an independent re-runner replays every `DoorOpened` and
`RoomCreated` event through the published matcher. A matcher route into a room
the rules do not select is caught within one indexing cycle.

**Response:**

- `set_matcher_authority(new_key)`. Launching continues to require the
  configured matcher; an outage cannot bypass the signature requirement.

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

**B. Random SOL-quoted launches passing the selected gate at read time:**

The generated selected-gate table in §4.1 includes the sample-window, day-old
and week-old populations. The complete reserve/idle sweep is in
`outputs/narrative/liveness_table.md`; its comparison rows are retained.

**Caveats:**

- The day-old group shows more idle-only activity than the younger one. That
  is bots trading the dead coins.
- The samples are small. 0 of 71 has a 95% upper bound of about 5%.
- A cluster member that later completed on pump.fun is included in A with its
  curve trades only.

## 11. Limits, and the data that would fix them

| limit | what fixes it |
|---|---|
| Real images show permanent false-positive routes; image routing stays in shadow. | Validate the strict entropy candidate on a new sample with human labels; the present small in-sample gain is not an enablement decision. |
| Text and image-aware labels are the assistant's; neither is human-reviewed. | A human pass over the 300 rows of `labels_assistant.csv` (about half an hour); re-run `run_calibrate_text.sh`. |
| 1.72 hours on Halloween afternoon. | A week of launches from a non-rate-limited RPC or an indexer export. The collector resumes, so `run_collect_launches.sh N` with a larger N extends the same file. |
| Pre-graduation liveness is calibrated on pump.fun curves as a proxy for doors rooms. | Doors' own room histories once live. pump.fun's curve has the same 30 SOL virtual reserve as doors' (V_sol 30.0009 SOL), which is why it is used. |
| Mature-room volume and pool-fee defaults lack doors-specific trailing-history calibration. | 30 days of `total_lp_b_fee` growth on graduated memecoin pools, read with `run_damm_pool_fields.sh` at intervals. |
| The fixed vamp denominator was built from text/URI evidence; renamed image-only copies can be absent. | A separately labelled image-only population, reported independently of the fixed comparison here. |
| Missing images and mutable metadata can bias coverage. | The fetch manifest records every failure and byte hash; bytes were fetched at the recorded time, and mutable URIs may differ from their launch-time contents or on re-fetch. |

## 12. Reproduce

From this directory, using Python with the pinned image dependencies:

```bash
python3 -m pip install -r scripts/narrative/requirements_images.txt
python3 scripts/narrative/run_revision.py
```

The default command regenerates curve, rent, fee, gate and documentation tables
from checked-in evidence, and runs the gate tests and worked examples. It
makes no RPC requests. To fetch original-sample image bytes and repeat the
image replay, entropy experiment, edits and reference check:

```bash
python3 scripts/narrative/run_revision.py --fetch
```

For existing local byte caches, use `--images` instead. Downloads are cached
by requested URL in the repository's ignored `.tmp/narrative_images`; the
manifest records byte SHA-256 values. The image-aware labels are pinned to
those bytes: changed mutable images require label review, and calibration
rejects a hash mismatch. Re-fetches can fail for dead metadata or missing CIDs;
coverage and errors must remain visible.

To repeat the direct rent confirmation or the full size check:

```bash
python3 scripts/narrative/read_current_rent.py --confirm
python3 scripts/narrative/read_current_rent.py
```

These make fresh reads, record slot brackets and intentionally stop on a
model conflict. Adopting a new rent model requires updating the calibration
and rerunning all derived figures; it never rewrites existing Room snapshots.

Original collectors remain available when extending the evidence: launch
collection, text labels/replay, historical liveness reads and DAMM v2 field
sampling. For the unchanged text replay:

```bash
scripts/narrative/run_calibrate_text.sh
```

The Twemoji image outputs remain historical only; the active image runner now
uses the real token sample. The image route labels and all threshold/entropy
measurements are assistant-reviewed and in-sample, with the limitations
recorded alongside their outputs.
