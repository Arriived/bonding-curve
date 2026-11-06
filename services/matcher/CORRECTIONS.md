# Matcher service: corrections

These are conflicts between the brief and what the deployed program, the research code or this
environment actually do, each verified before building on it. Item 1 is the expiry question the brief
asked about.

**Status, 5 November 2026.** Items 1 and 3 are resolved in the program (`claude/program-v1` `e9bd2aa`,
deploy ELF `36e22dab…3b31`), and the service now targets that program (item 4). The original findings
are kept below as recorded; each resolved item ends with what changed.

## 1. The program verified no expiry; the runtime did, through the blockhash (resolved)

**What the program checks.** The deployed program
(`436c002` plus the program-ID patch; `program/verification/devnet/deployed_source.patch`) has no
expiry field and checks no time or slot bound on a routing decision. It requires two things:

- the matcher authority is a **signer of the launch transaction** (`matcher: Signer` in `CreateRoom` /
  `OpenDoor`, `programs/doors_v1/src/contexts.rs`);
- the launch instruction is **top level** (`require_top_level_launch`, `lib.rs`).

There is no detached "decision message". **The thing the matcher signs is the whole transaction
message**, which includes the recent blockhash. The runtime rejects a transaction whose blockhash is
older than `MAX_PROCESSING_AGE` = 150 slots (`solana-clock` 4.0.0 `src/lib.rs` L153–155). That is
about 32 s at the 0.215 s per slot measured on devnet.

**So the expiry exists, and it is enforced by the runtime, not the program.** The localnet end-to-end
test demonstrates it. A decision submitted after its `last_valid_block_height` was rejected with
`BlockhashNotFound` (`tests/e2e/e2e.py`, step 6).

**The gap that remains: durable nonces.**

- A transaction that starts with `AdvanceNonceAccount` uses a nonce instead of a blockhash, and never
  expires.
- This service builds every message itself, from a fresh blockhash, and never adds a nonce
  instruction. A client cannot supply its own message for signing.
- But the program would accept a nonce-based launch signed by the matcher key. A buggy or compromised
  matcher could therefore issue a decision that can be held indefinitely and replayed later.
- **Example:** a "new room" for an identity, obtained before a live room for that identity existed and
  used after. The program's SlugLock floor would stop that exact case, because it fails `create_room`
  while a live room holds the identity. It would not stop the name-only (T2n) equivalent.

**What the program would need**, either of:

- `Launch.expires_at_slot: u64` and `require!(Clock::get()?.slot <= launch.expires_at_slot)`. The
  service would set it to the blockhash's last valid slot. This bounds a decision whatever the
  transaction looks like. **Recommended.**
- Instruction-sysvar introspection that rejects a launch transaction whose first instruction is a
  System `AdvanceNonceAccount`.

**Resolved (program `e9bd2aa`).** The first option was taken, with an upper bound added:

- `Launch` carries `expires_at_slot: u64`, inside the matcher-signed instruction data.
- `create_room` and `open_door` fail with `Expired` (6045) unless
  `slot <= expires_at_slot <= slot + 150` (`MAX_LAUNCH_WINDOW_SLOTS`, equal to `MAX_PROCESSING_AGE`).
  The upper bound stops a matcher bug or a compromised matcher key from signing a far-future expiry
  that a durable nonce could then hold.
- The service sets `expires_at_slot` to the blockhash's slot + 150 (`service.py`; `txbuild.py`
  `MAX_LAUNCH_WINDOW_SLOTS`). For a blockhash-based transaction, the program bound and the runtime bound
  coincide to within the slot-vs-block-height difference, so a decision never outlives its blockhash
  by more than skipped slots. The bound is recorded in the decision (`transaction.expires_at_slot`) and
  checked by `scripts/verify_decision.py`.
- Localnet e2e, this branch:
  - step 6b: a matcher-signed launch with `expires_at_slot` one slot in the past, on a valid blockhash,
    is rejected on-chain with `Expired`;
  - step 6c: a launch on a durable nonce, held past `expires_at_slot`, is rejected on-chain with
    `Expired` (slot 190 in the recorded run), although the nonce kept the transaction itself valid;
  - steps 1–3: launches inside the window land.

## 2. Single use: what the program enforces, and what the service only tracks

**Enforced on-chain:**

| replay | stopped by |
|---|---|
| the same signed transaction twice | runtime signature de-duplication within the blockhash window (`AlreadyProcessed`, e2e step 5), then blockhash expiry |
| the same room-id nonce twice | `init` on the Room PDA `["room", room_id]` |
| the same door nonce twice | `init` on the Door PDA `["door", room, door_nonce]` (door 0 is nonce 0, created by `create_room`) |
| a held decision | `Launch.expires_at_slot`, at most 150 slots ahead (item 1) |

**Tracked by the service only (per process, `matcher_service/inflight.py`):**

- **Two different launches decided against the same snapshot.** If two launchers ask for the same new
  name within one blockhash window, both would get "new room". The second would bypass the T2n rule.
  The service refuses the second with 409 and `retry-after` until the first lands or expires.
- ~~Door index allocation.~~ No longer needed: each door decision carries a random signed nonce
  (item 3).

Running more than one replica requires moving this state to shared storage (README, "What remains").

## 3. The door index was `room.door_count` at execution: concurrent doors into one room serialised (resolved)

`OpenDoor` derives the new door's address from `core.room.door_count` (`contexts.rs`). Consequences:

- Two launches into the same room in the same window need different indices.
- If the earlier one is dropped and never lands, every later one fails on-chain, and must re-request
  after the earlier decision expires (at most about 32 s).
- A popular room therefore admits roughly one door per landing slot, and a dropped transaction stalls
  the others.

**A program change would remove the coupling:** derive the Door PDA from the launcher and a
matcher-chosen nonce, as `create_room` already does for rooms.

**Resolved (program `e9bd2aa`).**

- The Door PDA is `["door", room, door_nonce]` and the door mint is `["door_mint", room, door_nonce]`.
  `door_nonce` is a `u64` in the matcher-signed `Launch` and is stored on the `Door` account (`nonce`,
  offset 303) and in the `DoorOpened` event.
- `create_room` requires nonce 0; `open_door` requires a non-zero nonce.
- The service draws the nonce from `secrets.randbits(64)`, retrying on 0 (`service._door_nonce`).
  Concurrent door launches into one room therefore have independent addresses, and a dropped one blocks
  nothing. The in-flight index allocation is removed.
- A collision fails cleanly: `init` on an existing Door PDA aborts the transaction, nothing moves, and
  the client re-requests. With 64 random bits, the chance of a collision is about n²/2⁶⁵ for n doors in
  one room.
- `room.door_count` is still incremented and is still the `index` in `DoorOpened`. The service's
  door count from `DoorOpened` events still holds, because every door, door 0 included, emits exactly
  one. It no longer determines any address.

## 4. The deploy candidate was not the branch tip (resolved)

This service originally targeted the deploy candidate: `436c002` plus the program-ID patch, pinned ELF
`f2cfdb85…b436`.

The branch tip `8ce373f` differed in two ways:

- It failed 10 of 38 of its own SBF tests (`program/docs/CORRECTIONS.md`, devnet preflight item 1).
- It changed the instruction layout: it added `Launch.expected_terms_hash`.

**Resolved.** The tip is fixed (`6385fdd`; cause and fix are in `program/docs/CORRECTIONS.md`,
"Pre-audit program changes"). The door-nonce and expiry changes are on top (`e9bd2aa`), and the deploy
pin is `36e22dab…3b31`. The service now targets that program:

- `idl/doors_v1.deployed.json` and `idl/layouts.deployed.json` are copied from
  `program/idl/doors_v1.json` and `program/verification/layouts.json` at `e9bd2aa`.
- `txbuild.encode_launch` appends `expected_terms_hash`, `door_nonce` and `expires_at_slot`. The terms
  hash is recomputed from Config (`layouts.decode_config`, the program's `launch_terms_hash`
  preimage).
- The layout test passes against the new files, and so do 96 of 96 unit tests and the localnet e2e.

Nothing is on devnet yet: the deploy is still pending funding.

## 5. The brief's normalisation list is a subset of the calibrated one

The brief lists "uppercase, strip whitespace, punctuation and emoji, fold 0→O, 1→I, 5→S, 8→B, rn→m,
vv→w". The research matcher that was calibrated, and which the brief says to port without
redesigning, does more:

- NFKC;
- invisible-character removal;
- a Cyrillic/Greek homoglyph table;
- accent stripping;
- the additional digit folds 3→E, 4→A, 7→T;
- name stopwords;
- COIN/TOKEN suffix splitting;
- camelCase splitting.

**The service ports the research matcher exactly** (`matcher_service/rules.py`, with a parity test
against the research module on sample strings). It does not use the shorter list.

## 6. The program's floor uses a different fold from the text rule

The SlugLock exact-identity floor is keyed by the program's own fold (`state.rs` `fold`):

- ASCII only, no NFKC, no homoglyphs;
- rn→m, vv→w and the same seven digit folds;
- non-ASCII bytes kept.

The text rule uses the research fold. They are not interchangeable, so the service computes both. The
program fold is ported byte for byte and tested against the SBF suite's reference vectors.

**The floor comes first,** because the program enforces it:

- a live holder of the candidate's identity must receive the door;
- a dead holder must be passed as `old_holder`.

## 7. Liveness thresholds come from Config, and match the brief

The brief's gate is

```
age < 1 h OR (reserve >= 0.5 SOL AND idle <= 6 h AND trailing volume >= 5 SOL/day)
```

That is the program's `Room::live`: trailing volume is the sum of hourly buckets that start in
`[now − 86400, now]`.

The service does not hardcode it. It reads `live_*` from the on-chain Config in every snapshot,
because the program re-checks with those values. On localnet the generated Config defaults are
exactly the brief's values.

## 8. Graduated rooms: explicit refusal, not undefined behaviour

v1 has no graduation instruction, so status 2 cannot occur. If it did, the program's `Room::live`
fails with `PhaseTwo` for it. Both `open_door` into such a room and `create_room` over its SlugLock
would fail on-chain. The service therefore:

- **refuses with 409 `graduated_identity`** when the candidate's SlugLock holder is graduated, since
  no launch of that identity can succeed in v1;
- **excludes graduated rooms as routing targets** otherwise, so a T2n match to one gives a new room.

The research matcher's worked examples 08 and 09 exercise a post-graduation pool path. The service's
test suite asserts this v1 behaviour for them explicitly, rather than skipping them.

## 9. "Recompute from chain state at that slot" needs history, not state

**Standard RPC cannot return account state as of a past slot.** So the verifier
(`scripts/verify_decision.py`) rebuilds each relevant room's state at the decision slot by replaying
the program's own events from its transaction history:

| event | gives |
|---|---|
| `RoomCreated` | `created_at` |
| `DoorOpened` | faces, door count |
| `Trade` | reserve, status, `Room::record` buckets |
| `PendingRetired` | reserve |
| `ConfigChanged` | thresholds and the matcher key |

Two requirements follow:

1. **It needs an RPC with full transaction history**, an archival node, for rooms older than the
   node's retention.
2. **It relies on a transaction's block time equalling `Clock.unix_timestamp` in that slot.** The
   e2e test checks that equality on every verified decision.

While replaying it found that `create_room` emits door 0's `DoorOpened` *before* `RoomCreated`. The
replay applies `RoomCreated` first.

## 10. Very long metadata does not fit a legacy transaction

A `create_room` with maximum-length metadata is 1,270 bytes as a legacy transaction
(`program/verification/cu.md`), over the 1,232-byte packet limit. The service refuses such requests
with 413 `tx_too_large`. Supporting them needs v0 messages with an address lookup table, which v1
does not implement.

## 11. KMS facts were taken from the vendors' client libraries, not their docs sites

`docs.cloud.google.com` and `docs.aws.amazon.com` are not reachable from this environment. The KMS
capabilities were read from each vendor's published API definitions:

- **Google:** `google-cloud-kms` 3.18.0, wheel SHA-256 `475d3d8f…5f6`. `EC_SIGN_ED25519` is "EdDSA on
  the Curve25519 in pure mode (taking data as input)"; `AsymmetricSignRequest.data`.
- **AWS:** `botocore` 1.43.124, wheel SHA-256 `4651bac6…07965`. Key spec `ECC_NIST_EDWARDS25519`;
  `ED25519_SHA_512` requires `MessageType: RAW`; messages are 0–4,096 bytes.

Neither backend has been exercised against a real KMS. Both are tested against fakes:

- the GCP signer against a fake endpoint that checks the request shape and CRC32C;
- the AWS signer against a fake client that checks `RAW` / `ED25519_SHA_512` and the key spec.

Whatever the backend, every returned signature is verified against the key before use.

## 12. Self-review, 5 November 2026: what the service did not do as documented

The full findings are in `program/docs/SECURITY_REVIEW.md`. Service-side corrections:

- **"While a new-room decision for name N is in flight, another launch with name N is refused"
  was not true under concurrency** (M-2).
  - **What was wrong:** the check ran before signing and the reservation after storing, on a
    thread pool, so two simultaneous requests could both be signed "new room".
  - **Fix:** `InFlight.claim` is now one atomic step before signing, released if no decision
    is issued.
  - **Regression test:** it holds a request between claim and signature, and fails on the old
    code.
- **The reservation itself is a free denial of service on any name** (H-1, open).
  Requests are unauthenticated, so anyone can keep a name reserved indefinitely by never
  submitting. Remedies need an API decision.
- **The per-launcher rate limit keys on an unauthenticated field** (M-3, open). It can be
  evaded, and it can be aimed at a victim's wallet.
- **`min_tokens_out` defaults to 0** (M-4, open). That is harmless for a new room's first buy,
  which cannot be front-run, but leaves a door's first buy into a live room unprotected.
- **Smaller input-handling bugs, fixed:**
  - `MATCHER_TRUST_X_FORWARDED_FOR` used the client-supplied leftmost entry; it now uses
    `MATCHER_TRUSTED_PROXY_HOPS`;
  - the body size was unbounded, and any string became a rate-limiter key;
  - lone surrogates in metadata caused a 500.
- **Historical v0 seam, superseded by §17.** At the time, v0 support waited for program finding M-7: a
  prefunded maximum-metadata takeover exhausts the program heap. The legacy size cap is what
  keeps it unreachable today (README "What remains" 7).
- **The matcher key used by tests and the e2e is rotated** (`program/docs/DEPLOYMENT.md` §9).
  The new key is also session-generated: devnet/localnet only.

## 13. Security-review follow-up, 5 November 2026

- **The reservation is load-bearing (H-1).**
  - **What earlier text implied:** that SlugLock might already stop the
    duplicates.
  - **What `scripts/slug_coverage.py` shows:** SlugLock covers only pairs whose
    ASCII folds are byte-identical. Every T2n pair escapes it, and so does every
    T3 pair that differs by a stopword, a homoglyph, NFKC or an invisible
    character: 9 of 16 tested.
  - **Status:** the reservation stays, and H-1 stays open pending the owner's
    choice of remedy (`program/docs/SECURITY_REVIEW.md`).
- **Requests are signed (M-3).** `/route` now requires the launcher's signature
  over the canonical request (`matcher_service/auth.py`, README "API"). This is an
  API break for every client: each request costs one `signMessage`.
- **Launch first buys carry a price limit by default (M-4).**
  - **Default:** the quote less 2%.
  - **Where the guidance lives:** the brief asked for a default "consistent with
    the frontend guidance in the spec". The spec has none; the guidance is in
    `research/doors_into_one_room/DESIGN.md` §3 ("≤ 2–3%"). Recorded here rather
    than invented.
  - **New refusals:** `min_tokens_out: 0` together with a first buy, and an
    unfillable first buy.
- **Verifier.** `verify_decision.py` accepts a signed `min_tokens_out` equal to
  either the request's value, or the recorded quote less its slippage. It does not
  recompute the quote from history.

## 14. Devnet, 5 November 2026

- **The program is deployed on devnet, and this service's e2e passes there**
  (`program/docs/DEPLOYMENT.md` §5, §7). `tests/e2e/target` is now `devnet`.
- **The verifier's timestamp assumption was false on a real cluster.**
  - **What it assumed:** that a transaction's block time equals the program's
    `Clock` ("time = block time = Clock").
  - **What devnet showed:** a 1 s difference, and a false DISAGREE.
  - **Fix:** `created_at` is read exactly from the Room account. `last_trade_at`
    and bucket starts are compared within 5 s, and the decision is recomputed at
    both ends of that window. A result that depends on the window is reported as
    INCONCLUSIVE (exit 2).
  - **Detail:** `program/docs/SECURITY_REVIEW.md` L-6.
- **Public devnet RPC rate-limits `getProgramAccounts` (HTTP 429).** A snapshot
  makes three such calls. `RpcClient.call` now retries 429 only, up to 4 times,
  honouring `Retry-After` (at most 4 s per wait). The snapshot's slot-coherence and
  age checks still refuse anything the delay makes stale. Production should use a
  dedicated RPC either way.
- **e2e step 3b front-runs with 1 SOL, not 5,** to fit the devnet budget. It now
  asserts, from the moved state, that the same first buy would fall below the
  signed limit, rather than assuming a large buy is enough.

## 15. H-1 interim (5 November 2026)

- **What the owner decided:** take the interim fix now, and treat the on-chain NameLock as a mainnet
  blocker.
- **Implemented (`service.py`, `funds.py`):**
  - one in-flight new-room decision per launcher (`409 launcher_in_flight`, naming the held
    decision so a lost response can be recovered from `/decision/{id}`);
  - proof of funds at decision time (`422 insufficient_funds`). The required amount is computed
    from the program's own account sizes, with rent priced by the cluster's rent RPC.
- **Tests:** `test_one_in_flight_new_room_decision_per_launcher`, `test_new_room_needs_proof_of_funds`.
- **What it does not do:** stop a squatter with N funded wallets holding N names. That needs the
  NameLock, recorded as a mainnet blocker in `program/docs/SECURITY_REVIEW.md`.

## 16. H-1 closed on-chain: NameLock; the reservation is removed (5 November 2026)

- **What the owner decided:** the matcher signs its folded-name key, and the program uses it as a PDA seed
  for a `NameLock`. The program never computes the fold.
- **The key** (`rules.name_lock_key`): 16 bytes, `sha256("doors-v1:name-key:v1" 0 class 0 payload)[:16]`.
  - Class `N`, over the folded name, when the folded name has at least 4 characters.
  - Class `P`, over the folded symbol and folded name, when the name is shorter and both are non-empty.
  - Otherwise no key, and no NameLock.
  - **Why one key per launch is enough:** T3 and T2n both require equal folded names, so the
    matcher's relation between two room-creating launches reduces to "same key".
    `test_name_lock_key_equals_exactly_when_the_matcher_routes_together` checks this both ways over
    every pair of the slug-coverage classes, the research examples and edge cases.
  - **Why 16 bytes:** each byte costs URI length in a legacy transaction. Finding a second
    preimage of a 128-bit key costs 2^128 work, and the chance of an accidental collision among
    10^9 names is about 10^-21.
- **Correction, the old reservation was narrower than documented:** it reserved `name:` only for
  names of 4 or more characters, plus the exact identity. A short-name T3 pair with different program
  identities (a 3-letter homoglyph name, for example) was not reserved. The `P` class of the
  NameLock covers it.
- **Removed:** `inflight.py`, the one-hold-per-launcher limit, `funds.py` and the proof of funds.
  - Each existed only to stop two concurrent new-room decisions for one name. The program now
    enforces that atomically: `slug_coverage.py` shows 0 of 16 routed pair classes without an on-chain
    floor (9 before).
  - With the holds gone, H-1's reservation squatting is gone too.
  - Tests replaced: `test_concurrent_new_rooms_for_one_name_are_both_signed_under_one_name_lock`.
  - The e2e test, step 1b: two decisions under one NameLock, the second rejected on-chain (`Holder`,
    6013), and once re-requested it becomes a T2n door.
- **What the reservation did that nothing does now:** when two launchers race one new name, the faster
  transaction becomes the room's founder. The other loses only its transaction fee. This matters only
  while `founder_share_bps > 0`.
- **Snapshot and decision:**
  - The snapshot now reads every `NameLock`, checking that each is the PDA of its stored key.
  - A dead holder is passed as `old_name_holder`.
  - A graduated holder is refused with 409 `graduated_name`.
  - A live holder that the text rule did not match is refused with 503 `inconsistent_state`. Only a
    lock keyed under other Unicode tables can produce one, so the service fails closed.
- **Verifier:** recomputes the key from the research matcher's `ident()`, not from `rules.py`, and replays
  the NameLock holder from `RoomCreated.name_key` and `NameReleased`.
- **Cost, URI length** (`scripts/max_uri.py`, name 32, symbol 10, with a priority fee):

  | shape | legacy before | legacy now | v0 + lookup table (comparison) |
  |---|---|---|---|
  | `create_room` | 102 | **51** | 200 |
  | takeover | 70 | **19** | 169 |
  | NameLock takeover only | — | **19** | 169 |
  | both locks held by different dead rooms | — | **does not fit** | 137 |

  Shorter names and symbols leave more room, byte for byte. Moving to v0 is README "What remains" item 7.
- **Correction, README item 7** still said a launch uses 64 of 64 trace entries and that v0 was blocked
  by M-7. Neither was true after the M-8 change. It now gives the current figures.
- **Results:**
  - unit tests 116/116;
  - service e2e PASS on localnet and on devnet against `71d32f3`, which was upgraded at slot
    519,081,470;
  - on devnet, step 1b rejected the second `create_room` under one NameLock with 6013 at slot
    519,081,838; re-requested, it became a T2n door.
- **Correction, the verifier:** the floor-door path of `recompute()` lacked the new `old_name_holder`
  field, so the first localnet run reported DISAGREE on a correct decision. Fixed, with a unit test
  over every path.
- **New: `scripts/sweep_test_positions.py`.** It sells every test position back to its curve and
  sweeps a test wallet's SOL to the deploy wallet, keeping the devnet balance usable as upgrade budget.
  On 5 November it returned 3,918,053,521 lamports (program `DEPLOYMENT.md` §5). Never point it at a
  wallet with real holdings.

## 17. v0 lookup-table membership and URI limits

Measured on `claude/matcher-service` at `9c976d9` using the pinned NameLock IDL, the
service's instruction builder, and its `scripts/max_uri.py` wire-size functions.
The six-address comparison in §16 and the README includes two addresses used only
by `create_room`. Classic SPL Token and its wrapped SOL mint are absent from
`open_door`, including the takeover path. Only four lookup-eligible addresses
appear on every launch path.

| Address | Base58 | Marginal bytes saved on `create_room` | Marginal bytes saved on `open_door` |
|---|---|---:|---:|
| Config PDA | `4jJfFvgAyPsnX6P95Wd4huf5BCyYaow771kdZpqbbpWw` | 31 | 31 |
| Token-2022 | `TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb` | 31 | 31 |
| ATA program | `ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL` | 31 | 31 |
| System program | `11111111111111111111111111111111` | 31 | 31 |
| Classic SPL Token | `TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA` | 31 | 0 |
| Wrapped SOL mint | `So11111111111111111111111111111111111111112` | 31 | 0 |
| Doors program | `D7YsLsiJXoAF38vCUhFqYStepvSz6goG7EddHDe5NVJG` | 0 | 0 |
| Compute Budget program | `ComputeBudget111111111111111111111111111111` | 0 | 0 |
| Configured matcher authority | Read from Config | 0 | 0 |

The Doors and Compute Budget program IDs are top-level instruction targets, so
v0 keeps them in the static keys. The matcher authority is a required signer
and is also static. The launch instructions get Clock and Rent through syscalls,
so there are no sysvar account metas to move. The MetadataPointer initializer
and the metadata interface instructions both target Token-2022 in `vaults.rs`.
The ALT program appears only in table provisioning. Launcher and destination
accounts, room and door PDAs, mints and vaults, both locks, and their optional
old holders depend on the launch. [Solana v0 message rules](https://docs.rs/solana-message/latest/solana_message/v0/struct.Message.html)

| Launch shape, with max name and symbol lengths and a priority fee | Legacy URI bytes | v0 URI bytes, four shared addresses | v0 URI bytes, six fixed addresses |
|---|---:|---:|---:|
| New room | 51 | 139 | 200 |
| One dead holder, for either lock | 19 | 107 | 169 |
| Two different dead holders | Empty URI exceeds packet limit | 75 | 137 |

The measured saving for six loaded keys is 186 bytes before the 36-byte
v0 lookup overhead, or 150 bytes net. With four keys the net saving is
88 bytes. The builder comparison caps the URI at the program's 200-byte limit.

The owner clarified that the table may contain fixed addresses used by a
subset of launch paths. That resolves the initial membership discrepancy.
The provisioning script uses the six eligible addresses in the original comparison,
ordered as Config, Token-2022, classic SPL Token, wrapped SOL, ATA and System.

For a new room, the builder can serialize 201 URI bytes in a 1,232-byte
packet. The program metadata validation caps the accepted URI at 200 bytes.
The boundary tests check metadata rejection at 201 bytes and packet rejection
at 202 bytes. For both takeover shapes, packet size is the first limit.

The verifier decodes the signed v0 message, resolves the frozen table indexes
and compares the landed wire message and loaded addresses with the signed
record. It also reads historical legacy records.

To reproduce, run the following from `services/matcher` with its Python dependencies installed.

```python
import sys

from solders.compute_budget import set_compute_unit_limit

sys.path.insert(0, "scripts")
import max_uri as m

builder = m.txbuild.Builder(m.PROGRAM)
payer, matcher = m.Keypair().pubkey(), m.Keypair().pubkey()
shapes, _ = m.shapes(builder, payer, matcher)
reference = m.static_alt(builder)
budget = set_compute_unit_limit(400_000).program_id
all_keys = [*reference.addresses, builder.program, budget, matcher]
shared = [
    key for key in reference.addresses
    if all(any(a.pubkey == key for a in build("").accounts) for build in shapes.values())
]

def v0_size(keys):
    table = m.AddressLookupTableAccount(reference.key, keys)
    return lambda ix, signer: m.wire_len_v0(ix, signer, table)

for name, build in shapes.items():
    ix = build("")
    sizes = [m.wire_len, v0_size(shared), v0_size(all_keys)]
    print(name, "URI maxima", [m.largest(build, payer, size) for size in sizes])
    print("Empty-URI packet bytes", [size(ix, payer) for size in sizes])
    print("Marginal savings", [
        v0_size([other for other in all_keys if other != key])(ix, payer)
        - sizes[-1](ix, payer)
        for key in all_keys
    ])
print("Key order", *all_keys)
```

### Verification status

The matcher unit suite passed 128 tests. The deployed Doors ELF matched
`program/devnet/DEPLOY_ELF.sha256` at finalized devnet slot 519,099,815.
`program/scripts/fetch_cluster_programs.py` captured the deployed SPL programs
at finalized slot 519,096,745. The SBF rerun and compute comparison are pending.

A read-only devnet simulation of create, extend and freeze passed at slot
519,100,215. The simulated table had all six entries in order, with no
authority. An initial simulation at finalized commitment rejected the
derivation slot, 519,100,105, as missing from SlotHashes. The successful
simulation used the provisioning script's confirmed preflight commitment.
The public RPC returned HTTP 410 for the dedicated test payer's airdrop.
A funded devnet signer is needed to send the freeze transaction and record
the finalized table. The existing matcher and smoke-wallet key files are
needed for the devnet end-to-end runs.

## 18. Devnet key loss requires a new program ID

The initial instruction assumed the existing keyfiles were available. The owner
confirmed they had been lost and directed a replacement deployment. The old
deploy wallet held 16,396,200,441 lamports at finalized slot 519,109,075. That
wallet's balance cannot fund the new deployment without its key.

The new program ID changes the Config PDA in the table to
`54G2WXbMrW6LozcWXCAUh9YAFS7UsBXRwxdQQouUbL6N`. The other five entries are
unchanged. `scripts/max_uri.py --json` reproduced the packet limits for the
new program ID. The previous devnet simulation applied to the old program.
The Linux workflow checks the three SPL binaries against
`program/devnet/SPL_PROGRAMS.sha256`, pinned to the capture at slot 519,096,745.

The first replacement build in CI run 42132979503 produced ELF SHA-256
`159247c974e24c5b19698bb827c580fcf8ee846213ab950f3bcc4c3683566a0d`. The localnet suite stopped when
the old program's hash did not match. The generated IDL, ELF hash, and
compiled source hash were verified against the downloaded build evidence
before updating the pin. The complete suites run again with the new pin.
