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
- **Seam: v0 launches are blocked.** v0 support must wait for program finding M-7: a
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

## 17. Matcher review: face laundering fixed, Unicode pinned, candidate rules measured (7 November 2026)

**Face laundering through the floor (fixed).**
- **The hole:** the on-chain floor routes by the program's ASCII fold, which keeps stopwords. The text rule's fold drops
  them. So "solpepe"/PEPE (key SOLPEPE) and "Sol Pepe"/PEPE (key PEPE) share a program identity but not a name key.
- **The attack:**
  1. Create room "solpepe"/PEPE.
  2. Open a floor door "Sol Pepe"/PEPE in it.
  3. The room now has a Pepe face, and every later Pepe launch, any symbol, text-routed into it.
  4. With a genuine Pepe room live, the deeper reserve won the tie.

  It defeated the NameLock's one-key-one-room guarantee (two live rooms matched one key). Under paired doors it would
  hand an attacker every copy's flow.
- **The fix (`decide.py`, `rules.score_room_keyed`):** a room is text-matched only through faces carrying its own name
  key, door 0's. A text-routed face always shares door 0's key, because T3/T2n hold exactly when keys are equal. So this
  removes only the floor bridge.
- **Equivalence on real data:** the routing replay on the 2,956-launch calibration sample with door-0-key routing
  reproduces the published v1 row exactly: 1,224 rooms, 1,732 routed, 99.8% precision, 87.4% recall
  (`scripts/rule_candidates.py`, row v1).
- **The verifier** (`scripts/verify_decision.py`) applies the same restriction, with keys derived from the research
  matcher's own fold.
- **Tests:**
  - `test_face_laundering_through_the_floor_is_not_matchable`.
  - `test_match_on_a_later_door_face` now uses a reachable later face.
  - Research example 10 (a later face with another key) is unreachable in v1 and is marked as a deliberate divergence.

**Unicode tables pinned (fixed).** Name keys are NameLock seeds, permanent on-chain, and the fold uses the interpreter's
Unicode tables. A Python upgrade could have changed keys silently.
- `rules.PINNED_UNICODE_VERSION = "15.1.0"`. `Service` and `verify_decision.py` refuse to run on other tables.
- Test: `test_service_refuses_other_unicode_tables`.

**Candidate rules measured, none adopted** (`scripts/rule_candidates.py` → `RULE_CANDIDATES.md`; assistant labels, not
human-reviewed):

| rule | precision (est.) | recall of vamps (est.) | recall of certain vamps |
|---|---|---|---|
| v1 (current) | 99.8% | 87.4% | 99.4% |
| A: exact-name fix ("Bitcoin"/BTC vs "Bitcoin"/BITCOIN) | 99.8% | 87.4% | 99.4% |
| D: affix stopwords (BABY, FAUCET, INU, AI, …) | 98.3% | 87.3% | 98.3% |
| B: Unicode confusables + I/l/1/\| | 99.8% | 87.3% | 99.4% |
| E: same symbol + shared 4-character word | 97.2% | 88.5% | 98.1% |

- **Correction:** the earlier estimate from labelled pairs (55 → 90 of 153 same-narrative pairs for A+D+E) overstated
  the gain. In the sequential replay, D makes routing worse: "Baby X" rooms capture plain "X" copies. E gains 1.1
  points of recall for 2.6 of precision.
- **Adversarial value:** B catches 4 of 10 deliberate one-character evasions (capital I for l, a pipe, an Armenian o, a
  Cherokee P). It misses small capitals, Cyrillic п, l with middle dot, doubled letters and added words. The
  calibration sample comes from pump.fun, where nobody was evading a matcher, so recall under deliberate evasion is
  lower than measured, and text rules cannot close that gap.
- **Data:** B uses `data/confusables_ascii.json`, derived from the PyPI package `confusable_homoglyphs` 3.3.1 (Unicode
  `confusables.txt`). Provenance and hashes are in the file. unicode.org itself was not reachable from the build
  environment.

## 18. Rules A and B adopted (owner ruling, 7 November 2026)

**What changed** (`rules.py`):
- **Rule A.** A name keys by name alone (class N) when its folded name, *before* stopwords and the COIN/TOKEN suffix are
  removed, has at least 4 characters. "Bitcoin"/BTC and "Bitcoin"/BITCOIN now share a key; before, stripping left
  "BIT", under the minimum.
- **Rule B.** Names and symbols are mapped through Unicode's confusables (non-ASCII to ASCII,
  `data/confusables_ascii.json`) and `|` to `l`, after NFKC and before any split. After folding, L reads as I. This
  catches "EIon", "E|on", "Elօn" (Armenian o) and "Ꮲepe" (Cherokee P). It does not catch small capitals, Cyrillic п,
  doubled letters or added words.
- **The routing relation is now key equality by definition.** `text_tier` gives T3 when keys and folded symbols are
  equal, T2n when keys alone are equal. The NameLock key and the routing rule cannot drift apart.

**Measured** (`scripts/rule_candidates.py` → `RULE_CANDIDATES.md`, same replay as the calibration):

| | rooms | routed | precision (est.) | recall (est.) | recall of certain vamps |
|---|---|---|---|---|---|
| before | 1,224 | 1,732 | 99.8% | 87.4% | 99.4% |
| A + B, and the live service code | 1,222 | 1,734 | 99.8% | 87.4% | 99.4% |

The script recomputes the replay with `matcher_service.rules` itself; that row equals the A + B row.

**Correction, my own bug, caught by the existing tests:** folding L to I made "OFFICIAL", "SOL" and "SOLANA" miss the
stopword list ("OFFICIAI", "SOI"). Stopwords and suffixes are now compared in folded form. The same bug was in the
first B measurement (§17), which is corrected: B alone is identical to v1 on the sample, 1,224 rooms and 1,732 routed.

**Other changes:**
- **The verifier** (`verify_decision.py`) computes keys from the research matcher's own fold plus its own
  implementation of A and B, and routes by key. It no longer calls the research `decide()`, which matches any face
  under the old rule.
- **Research parity** is now "the research fold plus exactly rule B": `test_parity_with_research_normalisation`.
- **The confusables table is pinned by SHA-256**, like the Unicode version.
- **The devnet smoke's Rust key port** folds L to I and has two new vectors (program branch).

**Devnet consequence:** names containing an L, or with a short stripped name, now key differently from NameLocks created
earlier on devnet. Routing still finds those rooms, because it recomputes door 0's key under the current rules; a new
room for such a name orphans the old lock harmlessly. Nothing exists on mainnet.

**Results:** unit tests 119/119. Service e2e PASS on localnet; program e2e 34/34 on localnet. Devnet was not run: the
test wallets are empty since the devnet SOL moved to the owner's address.

## 19. Evasion benchmark; candidates C, F, G, I measured; the stopword split is an evasion (7 November 2026)

**New tooling:**
- `scripts/name_fuzz.py`: name fuzzers, partly derived from dnstwist (Apache-2.0; `THIRD_PARTY_NOTICES.md`).
  There are three classes. Disguise reads as the same name; typo is one edit; affix adds a memecoin word.
- `scripts/evasion_benchmark.py` → `EVASION_BENCHMARK.md`.
  - 1,220 targets, one per distinct key in the calibration sample.
  - Up to 4 variants per fuzzer per target, with a fixed seed.
  - Variants the program would reject (over 32 or 10 bytes) are dropped.
  - It measures dodge recall only. The cost of catching more is measured in the replay (`RULE_CANDIDATES.md`).
  - On every variant it checks that the service key equals `rule_candidates.py`'s A + B implementation.
- `tests/test_rules.py::test_evasion_floor`: per-fuzzer catch counts on 16 fixed names may rise, never fall.

**Finding, not fixed (it changes keys; owner's call):** stopwords are removed per token, and rn→m and vv→w fold per
token. So the key depends on where the name is split, and case and spacing control the split.
- "tHe rUnNeR" gives the camelCase split `t He r Un Ne R`. THE is no longer a token, so it is not removed.
- "T R U M P T H A D O N" loses the stopword A.
- "Bunkernet" folds rn→m; "BunkerNet" does not.

The service rule keeps only **89%** of case variants and **89%** of spacing variants.

**Measured** (disguise recall from the benchmark, vamp keeps the symbol; the rest from the real-data replay):

| rule | disguises caught | typos caught | rooms | routed | precision (est.) | recall (est.) | recall, certain |
|---|---|---|---|---|---|---|---|
| v1 | 74.7% | 3.4% | 1,224 | 1,732 | 99.8% | 87.4% | 99.4% |
| A + B (live) | 84.1% | 5.6% | 1,222 | 1,734 | 99.8% | 87.4% | 99.4% |
| + C transliteration | 92.7% | 5.6% | 1,222 | 1,734 | 99.8% | 87.4% | 99.4% |
| + F5 phonetic | 84.3% | 30.6% | 1,200 | 1,756 | 97.7% | 86.7% | 98.1% |
| + G no stopwords | 86.6% | 5.6% | 1,243 | 1,713 | 99.9% | 86.5% | 98.9% |
| + I split-invariant affixes | 86.6% | 5.6% | 1,225 | 1,731 | 99.8% | 87.3% | 99.4% |
| + I + C | **95.4%** | 5.6% | 1,225 | 1,731 | 99.8% | 87.3% | 99.4% |

**C (anyascii after B)**
- On the sample it changes nothing: same rooms, same routes.
- On the benchmark, small capitals go from 31% to 98.5%, and the Unicode homoglyphs from 83% to 95.5%.
- It is phonetic, not visual: Cyrillic п becomes p, so "Ruпner" still escapes.

**I**
- The key is every folded letter, joined and folded once. It then strips a leading THE or OFFICIAL (4+ characters must
  remain) and a trailing COIN, TOKEN, OFFICIAL, SOLANA or CTO.
- Case and spacing variants go to 100%.
- On real data it splits three A + B keys: "Baby the Black Bear" / "Baby Black Bear", "Swimming in the Money" /
  "Swimming in Money", "Solana Bat" / "Bat". That costs 3 routes.

**F (Metaphone)**
- It catches typos (vowel swaps 53%, doubled letters 54%).
- On real data it merges labelled-different names, with precision falling to 97.7%. F4 merges "MoonGoat" with
  "Moneycat" and "CUMBAL" with "GUMBALL".
- Its "recall of certain vamps" drop is mostly an artefact: it routes "David Dobrick" into the older, unlabelled
  "David Dobrik Coin" room, which the estimator counts as a miss. Even counting every unmeasured route as right,
  precision is 98.5%.
- Not recommended.

**Still escaping A + B + I + C:**
- Cyrillic look-alikes absent from the Unicode confusables data used: п, и, ш, ь, ԍ (about 1,300 of 43,146 disguised
  variants).
- "cl" for "d".
- A few Latin letters with hooks (ə, ŋ, ƿ).

Fixing the Cyrillic ones without breaking all-Cyrillic names needs a mixed-script rule: visual skeleton for a token
that mixes scripts, transliteration for a token in one script. That has not been built.

**H (drop invisibles before the camelCase split):** identical to A + B on the sample. It closes the 0.1% invisible
case ("Lost<ZWJ>ThePlot"), which I already closes.

The live rule is unchanged. Unit tests 120/120.

## 20. Rules I and C adopted (owner ruling, 7 November 2026); runtime image fix

**Ruling:** adopt I and C as measured in §19.

**Rule I (split-invariant affixes):**
- The name key is every letter and digit of the name, joined, then folded once (`rules.name_letters`).
- Then, repeatedly:
  - a trailing COIN, TOKEN, OFFICIAL, SOLANA or CTO is removed;
  - then a leading THE or OFFICIAL is removed, but only while 4 or more letters remain.
- Interior words stay: "Swimming in the Money" ≠ "Swimming in Money".
- Rule A is unchanged: the key class is decided on the joined name before stripping.
- Stopwords are no longer removed per token. `STOPWORDS`, `SUFFIXES` and `CAMEL` remain only for the replay of
  earlier rules.

**Rule C (transliteration):**
- After rule B, every remaining non-ASCII letter or digit becomes its anyascii 0.3.3 transliteration.
- anyascii is now a runtime dependency, pinned in `requirements.txt` (wheel SHA-256 `f5ab5e53…dee7a`).
- `check_unicode` refuses any other anyascii version, as it refuses other Unicode tables.

**Correction, my own bug, caught before push:** my first implementation of I stripped the leading THE before the
trailing COIN. So "Theory Coin" keyed ORY while "Theory" keyed THEORY. Trailing words now go first, in the service,
the verifier and the candidate replay. The §19 numbers were re-measured with the fix and did not change.

**Measured with the live code** (`RULE_CANDIDATES.md`, `EVASION_BENCHMARK.md`):
- The service row equals the A + B + I + C row: 1,225 rooms, 1,731 routed, precision 99.8%, recall 87.3%, recall of
  certain vamps 99.4%.
- Disguises keeping the key: 95.4%, against 84.0% under A + B. Case and spacing variants: 100%.
- The benchmark asserts that the service key equals `rule_candidates.py`'s A + B + I + C on all 81,579 variants, in both modes.
- `slug_coverage.py`: 0 of 16 routed pair classes lack an on-chain floor.

**Other changes:**
- **Verifier** (`verify_decision.py`): implements I and C independently on the research fold.
- **Tests:**
  - `test_parity_with_research_normalisation` is now "research fold plus B, C and I".
  - New: `test_rules_i_and_c_route_the_measured_cases`, including the measured costs and known escapes.
  - New: `test_service_refuses_other_anyascii_versions`.
  - The evasion floors were raised to the new counts.
- **Devnet smoke key port** (program branch): implements I for plain ASCII names. Four new vectors: "Bunker Net",
  "The Official Doors Coin", "Theory CTO Coin" and "tHe rUnNeR".

**Runtime image bug (found while checking packaging):**
- Since rule B (§18), `rules.py` reads `data/confusables_ascii.json` at import.
- The Dockerfile's runtime stage copied only `matcher_service/` and `idl/`, so the production image would have failed
  at import. The test stage copies the whole directory, so the image build passed and hid it.
- Fixed: the runtime stage copies `data/`.
- Verified by reproducing the runtime layout. Without `data/` the import raises FileNotFoundError; with it,
  `check_unicode()` passes. Docker itself could not run in this environment (no daemon), so the image was not built.

**Devnet consequence:** as in §18, NameLocks created earlier on devnet for names whose key changed are orphaned
harmlessly. The smoke names' keys did not change. Nothing exists on mainnet.

## 21. Launch watcher and first live measurement (7 November 2026)

**New:** `watcher/`, which streams pump.fun and Raydium LaunchLab launches over free RPC endpoints and runs the
matcher on each in shadow mode (README, "Launch watcher").

**First run:** 1,870 launches in 83 minutes.
- 55.3% would have been doors.
- 615 of those were copies by other wallets; the other 419 were the same wallet relaunching.
- 250 of the copies reused door 0's exact metadata URI.
- Copy platforms are visible: pump2, Float, and LaunchLab configs that declare StonkFun.
- Details and the raw log: `watcher/results/2026-11-07/`.

**Corrections to what I said earlier:**
- I quoted "27 launches in 30 s". That was one sample. The 83-minute run averaged 0.37 launches a second.
- "StonkFun" is not a program. It is a self-declared name in about 150 LaunchLab `PlatformConfig` accounts with
  distinct fee wallets, so a launch's StonkFun label cannot be verified on-chain.
- Mainnet now carries version-1 transactions, so `getTransaction` needs `maxSupportedTransactionVersion: 1`.


## 22. Paired program port and approved launch room-price limit (7 November 2026)

Starting point: service `9750e03`, paired program `2bf6f40`. The quote regression
first failed with 19,628,248,343,287 room units against the SBF door-unit vector
33,699,309,828,108. The service now prices SOL to room tokens, then room to door
tokens, using the birth anchor captured before pending settlement. The independent
verifier implements its own arithmetic and replays sold/pending state from events.

The owner approved the separate Launch room-price limit. `max_room_price` is a
16-byte u128, decimal string at the HTTP boundary, scaled by 10^18 lamports per
room base unit. Zero disables it. A first buy defaults to the pre-buy snapshot
spot plus the user's slippage. Both the request authentication and the co-signed
transaction cover it. Explicit token minima do not disable the default price bound.
Name-key normalization is unchanged; a regression checks its position after the
new field in create_room instruction bytes.

The active IDL and layout files are named `paired`, preserving deployed-history
pins and avoiding a false deployment claim. Room/Door are 1,331/360 bytes. Program
identity comes from that IDL; door sweeps use sell_door; the verifier decodes the
new Trade field and both swap events. Legacy URI limits with maximum name/symbol
and priority fee are 35 for creation and 3 for a one-holder takeover. Oversized
messages remain refusals. No v0 support or routing-rule change is introduced.

M-3 was already fixed. New tests alter every authenticated field, exercise 32
concurrent replays and preserve the original valid signature after tampering is
refused. Exactly one replay attempt succeeds. The current revival-routing decision
is recorded as a passing assertion instead of an expected failure. Its options
and the 120 SOL cap options are in SECURITY_REVIEW.md; neither is implemented.

The benchmark adds mixed scripts within and across words and a distinct class of
actual 32-byte UTF-8 truncations. Short untruncated names are excluded from that
boundary denominator. With the target symbol kept, mixed-script recall is
2,909/3,904 (74.5%); boundary recall is 14/255 (5.5%). Rules remain unchanged.
The full service suite passes 163 tests. This review performs no deployment or
production-key access. The Windows HTTP tests require ordinary local socket access;
inside the restricted sandbox their in-process test client hung, so they were run
outside it against mocks. No live service or RPC was used by pytest.


The preserved RPC redaction draft was restored and failed in both HTTP and
JSON-RPC cases before the fix. Raw transport exceptions included an authenticated
URL; provider error objects could echo it too. RpcError now retains only safe
method/class/status or numeric-code context, with transport exception chaining
suppressed. Both synthetic-marker regressions pass; no actual credentials were
accessed. The final full service run passes 163 tests.


Final verification on 8 November 2026: the program's green CI run 42403905057
passed 71 SBF tests and every required probe with the offline executable pins.
Program source `9ed04d7`, its emitted IDL, the service's paired IDL and the binary
pin were compared. The service passed 163 tests; the repeated full evasion JSON
matched exactly. Detailed identities and checks are in data/paired_review_checks.json.


## 23. Implemented owner rulings and retained RPC diagnostics (8 November 2026)

Supersedes the open routing and stress-cap choices in section 22. Against service
`f2f8451`, routing regressions first failed: a deeper revived former holder could
win and its live SlugLock could bypass the current NameLock holder. The service
now routes only to the current live name holder, or refuses conflicting live
identity/name locks. The independent verifier uses the same explicit precedence.
A former holder remains tradeable. Finding 4 is Fixed.

Program control `816b38d` accepted the admin's 120 SOL trigger and created unused
vaults plus 25 fixed liveness slots at birth. The candidate's normal build refuses
above 85,018,013,680 lamports; only `test-stress` accepts 120 SOL. Finding 7 is
Fixed. Its permanent two-sided test is run with each corresponding SBF build.
The owner authorized independent reviewer B/D controls against that historical
commit, with no deliberately failing tests committed on the candidate branch.

The paired port decodes 735-byte birth / 1,335-byte trading rooms and discovers
both by discriminator. Sparse buckets preserve exact u128 volume and hourly ring
semantics. Native, backing, retirement and WSOL vaults are created on first use;
IDL account ordering includes the required first-use payer/system accounts.

RPC exception/provider detail is retained in internal DEBUG records while public
errors remain redacted. Two new tests first failed against the old logger behavior,
then passed after the fix; a mocked API regression checks both health and route.
Current complete service suite: 170 passing tests. Evasion rules remain unchanged.


One repeated suite run exposed a timing-dependent IP spoofing regression: building
31 legitimate responses took long enough to refill the token bucket. The test now
passes a fixed timestamp through RateLimiter.allow's existing clock argument,
so it checks a single burst regardless of machine speed. The limiter and its
refill policy are unchanged. The stronger revival case also checks a former T3
text match loses to the current holder's T2n match after its old SlugLock release.


The final pinned program run 42526798488 on `86a0f44` is green: 71 SBF tests,
10,000 mixed iterations, both cap directions, stress exits, offline SPL pins,
heap probe, 400,000 curve cases, client checks and production binary pin.
Program/service emitted IDLs agree exactly. Findings 4 and 7 are Fixed. Birth
rent falls 26,959,560 -> 17,515,840 lamports, still 2,515,840 above the target;
creation heap improves 2,960 -> 4,080 bytes and its matched worst-case CU rises
328,089 -> 351,341. All source/test hashes in data/paired_review_checks.json
match the 170-test service run and the unchanged-rule benchmark repeat.


## 24. Launch CU budget and packet recheck (8 November 2026)

The 400,000 default had only been checked against VM use, while the documented
drift stress exceeds it. A new config/message regression first failed against
`b86ae42` (400,000 != 500,000). The default is now 500,000, overrides remain
supported, and SBF plus heap checks cover the complete drift allowance. Exact
historical drift plus the priority-price instruction gives a conservative
402,601 CU total and 97,399 margin (rounded review arithmetic: 402,341 / 97,659).
At cu_price 10,000, priority fee is 5,000 lamports, up 1,000; base fees separate.

max_uri.py imports the same default constant. Comparing 400,000 and 500,000
produced identical lengths: legacy URI limits 35 creation, 3 one-holder takeover,
200 open, 194 open takeover, at name 32/symbol 10 with priority instruction.
Full URI 200 creation remains 1,397 bytes and refused. The e2e launch fixture
also uses the default constant. No production program or rent behavior changed.


Final launch-budget CI [42536522731](https://github.com/Arriived/bonding-curve/actions/runs/42536522731)
is green on program `0849033`: 71 SBF tests, 10,000 mixed iterations, pinned SPL
binaries, cap feature checks, heap, 400,000 curve cases, client checks and unchanged
`d1fb4975` production binary pin. The maximum heap fixture confirms 402,601 stressed
CU, leaving **97,399 CU** under 500,000. Birth rent remains 17,515,840 lamports.
Service `6109176` passes 172/172 tests; the full evasion JSON repeats identically.
The config/message regression's pre-fix control is `b86ae42`; all committed
candidate tests pass. Data and hashes: `data/launch_cu_budget_checks.json`.

## 25. Door verification must replay the candidate NameLock (12 November 2026)

Preparing the paired devnet end-to-end check exposed a verifier omission:
`verify()` derived the candidate name key only for `create_room`. Consequently
`open_door` replay supplied no current name holder to the otherwise-correct
independent routing calculation. Floor routes could appear to conflict with
the NameLock, and name routes could appear to require a new room.

Two ordinary regressions, covering floor and T2n doors, failed against `584596a`
because no NameLock-history read occurred. The verifier now independently
derives the key for both instruction types; only creation requires a signed
name-key argument. Both regressions and all 180 service tests pass. Routing,
request authentication and normalization rules are unchanged. The fixed-seed
1,223-target evasion JSON repeats byte for byte (SHA-256
`2c09b97bb1b6e029b03b0b0eadce2023d62bd839d64d1be604a3fc71cea211a4`).

## Paired devnet qualification status (12 November 2026)

The deployed paired program completed the five remaining authorized scenarios,
matching VM exactly (26 snapshots including the earlier completed case). Full
program smoke and negatives pass 34/34 from saved receipts. The host report
renderer then hit a Windows cp1252 encoding error. The owner-required halt
prevented the service stage: **no real matcher launch, door request or
independent live verdict was submitted**. Those checks remain outstanding.

Program commit `9594aad` fixes the report output with a regression that first
failed on `db8d718`. Service `310e12a` fixes the independent verifier's missing
NameLock replay for doors; two regressions first failed on `584596a`. All 180
service tests pass. The signed devnet client is prepared at `a7aa8c0`, and the
full 1,223-target evasion JSON remains byte-identical. No routing or
normalization rule changed. A passing offline suite is not live E2E evidence.

All test positions, entitled fees and operating-wallet balances were swept.
Closing treasury balance is 53.089376282 SOL at finalized slot 521,596,121.
Whole qualification cost is 3.454624079 SOL; this resume cost 0.255489721 SOL.
The reconciliation includes the earlier deployment and recovery and two later
5-SOL funding transfers. All 24 other wallets and all 50 token-owner scans
are empty. [Program measurements and every signature/slot](https://github.com/Arriived/bonding-curve/blob/claude/paired-doors/program/verification/devnet/paired-4437e58-resume/report.md).

## Live matcher devnet E2E completed (19 November 2026)

All three signed matcher decisions finalized successfully against the pinned
`fc2d615e` deployment: new room at slot 523,854,267, identity-floor door at
523,854,322 and T2n name door at 523,854,377. Every fill equals the door-token
quote exactly. The prepared `a7aa8c0` client is unchanged and ran through a real
loopback HTTP matcher instance. The `310e12a` verifier ran in a separate
process, independently checked the decision-store hash chain, replayed 435
historical devnet transactions and returned **AGREE for every decision**.
Service and signer modules were absent from that verifier process. Mutable
reads were fresh; only finalized immutable transactions were reused.

The live HTTP service refused an altered signed request with **401
unauthenticated**, leaving zero decision rows and no transaction. The valid
original request was subsequently accepted. No unexpected refusal, verifier
disagreement or quote mismatch occurred. The existing service suite passed
180/180 before funding. The two new adapters change test transport and
verification orchestration; production matcher rules and code are unchanged.

The original signer files were located in app-local cache, read in place,
and their admin, treasury, matcher and test-wallet public keys verified before
signing. No keyfiles were copied into the repository or a synced folder.
The earlier unfunded missing-path preflight is separate and cost zero.

All test positions, entitled fees and remaining wallet balances were swept.
Closing treasury balance is **63.046940822 SOL at finalized slot 523,857,921**.
Incremental cost is **0.042435460 SOL**: 0.042255440 new-account rent and
0.000180020 network fees, with zero retained balances above rent. All 24 other
known operating wallets are zero; all six token-owner scans of the treasury
and used test wallets are empty. All 20 funding, service and recovery
transactions are finalized, and the reconciliation is exact. Program bytes
and the production Config still match; no redeployment was performed.

The matcher live-validation gap recorded after the 12 November halt is now
closed. Graduation design remains the next task and requires the owner's
DAMM v2 versus DLMM ruling. No graduation, lookup-table or maker implementation
was changed by this qualification.

[Full public evidence and every signature/slot](data/devnet/matcher-e2e-2026-11-19/report.md).

## 26. MULTI_FOLD was undocumented, mis-documented and untested (19 November 2026)

`name_letters` said "rn/vv cannot straddle a split". The code had never behaved that way: it joins every letter
*before* `MULTI_FOLD` runs, so the pair folds across separators. "Remember November" keys as REMEMBEMOVEMBER.
All 180 tests passed with that claim in place, because **nothing in the suite referenced `MULTI_FOLD` at all** —
no test, no fixture, no assertion. The docstring was free to drift from the code and did.

Measured on 61,388 real pump.fun launches collected over 31.4 hours (`scripts/shadow_replay.py`):

| | |
|---|---:|
| launches whose on-chain key `MULTI_FOLD` moves | 356 (0.58%) |
| rooms it merges that would otherwise be separate | **1** |
| rooms it splits that would otherwise be one | 0 |

The single false merge is `"BURN"` with `"bum"`, both class P. The fold also rewrites ordinary English inside the
NameLock key: BURN to BUM, TURN to TUM, Unicorn to UNICOM, Arnold to AMOID, Tournament to TOUMAMENT.

**The straddle is kept, deliberately.** Folding per token instead would let `"Pur npkin"` dodge `"Pumpkin"` by
splitting the homoglyph itself, which is a free and visually perfect evasion. One false merge per 61,000 launches
is the right price for closing it. What changed is the record, not the rule: the docstring now states that
straddling is intentional and names its cost, and `tests/test_multi_fold.py` pins all 15 cases, including the
`"BURN"`/`"bum"` collision and the `"Remember November"` artefact, so neither can drift again.

`MULTI_FOLD` is part of the NameLock key derivation. Changing that tuple is a breaking key change, not a tweak.

**Correction to an earlier claim.** The evasion benchmark credits `rn -> m` with +1,087 catches (55.22% to
56.04%). That figure should be discounted: the catches come almost entirely from `composed_lookalike`, the fuzzer
whose job is to substitute `rn` for `m`. The benchmark is scoring the rule against the attack the rule was
written for, at a frequency the fuzzer's author chose. On 61,388 real launches the fold caught no impersonation
and cost one false merge. Synthetic dodge recall and real-traffic value are different measurements and the
benchmark only ever produced the first.

### 26a. What the folds are worth on organic traffic

The same replay compared the full rule stack against the cheapest matcher anyone would write — NFKC, drop
non-alphanumerics, upper case, nothing else:

| matcher | doors | share of launches |
|---|---:|---:|
| live rule (A + B + I + C) | 45,526 | 74.2% |
| NFKC + alphanumerics + upper case | 45,043 | 73.4% |
| **difference** | **+483** | **+0.8pp (+1.1% relative)** |

Attributing each room's merge to the rule responsible: 91.5% of occupied rooms are byte-identical names needing
no fold at all, rule I accounts for 7.7%, rules B and C for 0.5%.

This does not make the folds worthless, and it is not an argument for removing them. It fixes what they are for.
The 74% door share — the figure the product rests on — is obtained by exact string matching. Launches are not
disguised today because nothing punishes an undisguised copy; the folds are insurance against adaptation, and
insurance pays nothing until the event. They cannot be added after an attack begins, because the NameLock key is
on-chain and changing it is breaking.

The honest statement of the moat is therefore **not** "our matcher is hard to replicate". On today's traffic a
fork with thirty lines of `upper()` and `isalnum()` captures 99% of the measured benefit. The defensible claims
are being first to hold the narrative rooms, and the folds mattering once copies adapt. The second is a bet. It
should be recorded as one.

### 26b. Impersonation against self-spam

Earlier door-share figures did not separate who opened the door. Over the 31.4-hour window:

| | launches | share |
|---|---:|---:|
| new room (an original) | 15,643 | 25.5% |
| routed into an existing room | 45,526 | 74.2% |
| ... by a **different** creator — impersonation | 32,942 | **53.7%** |
| ... by the **same** creator — one wallet spamming | 12,584 | 20.5% |
| refused, name folds to nothing | 219 | 0.4% |

A fifth of all launches are one wallet mass-producing the same name. That is spam, not vamping, and the anti-vamp
claim is the 53.7%, not the 74.2%. Door share also rises with the length of the window, because rooms stay live
for the whole replay: the earlier 55.3% came from an 83-minute run and is not comparable. **Never quote a door
share without its window.**

### 26c. One further over-merge, accepted

Ranking all 5,345 occupied rooms by how much their members' raw names differ and inspecting the worst found one
genuine over-merge in 61,388 launches: the Chinese character 婆 transliterates to "po" under rule C and shares a
key with the English name "po". It is class P, where symbol and name must both match, so the bar is already
higher than for ordinary names. Left as is.

## 27. Real-data rule audit: a missed-merge bug in rule A, and three bugs of my own in the backfill (19 November 2026)

Continuing section 26, I audited every remaining normalization rule against 63,082 real launches
(`scripts/shadow_replay.py --only refused,classes,multifold,merges,naive`). The matcher findings are below;
the collector findings are in 27d and were mine, not the matcher's.

### 27a. Rule A's class boundary scatters a narrative over several rooms — needs an owner ruling

`_key_string` puts a name in **class N** (routes on the name alone) when the folded name *before* affixes are
stripped reaches `NAME_EQUAL_MIN_LEN` = 4, and in **class P** (symbol must match too) otherwise. The pre-strip
length is deliberate, so that "Bitcoin"/BTC and "Bitcoin"/BITCOIN share the key BIT. The consequence on real
launches was not measured until now, and it is the first **missed-merge** defect found — the dangerous direction
for an anti-impersonation rule, since every other finding so far has been a wrong merge.

Two mechanisms, both visible in the data:

1. **The affix decides the class.** "GTA Coin" folds to GTACOIN (7) so it is class N with name key GTA.
   "GTA" folds to GTA (3) so it is class P. Identical narrative, different class, cannot route together.
2. **Within class P the symbol splits the room.** The same short name under a different symbol opens a new room:
   `P|GTA|GTA`, `P|SOI|GTA`, `P|MEMES|GTA`, `P|COUNTDOWN|GTA` and eight more.

Measured: **85 name keys scattered over more than one room; 260 launches (0.4%) outside the largest room for
their own name.** The percentage understates it, because the damage lands on exactly the short, high-value
tickers. **GTA — the hottest narrative in the sample — is shattered into 13 rooms.** So are INU (64 launches,
3 rooms), WAG (55, 2), DIP (25, 2), PS5 (17, 2), X (17, 4).

Lowering the minimum, measured on the same launches:

| `NAME_EQUAL_MIN_LEN` | doors | rooms | scattered names | launches misplaced |
|---:|---:|---:|---:|---:|
| **4 (today)** | 46,923 | 16,020 | 85 | 260 |
| **3** | 47,013 | 15,930 | **22** | **50** |
| 2 | 47,027 | 15,916 | 11 | 20 |
| 1 | 47,046 | 15,897 | 0 | 0 |

I inspected all 36 rooms that a minimum of 3 merges and a minimum of 4 keeps apart. **Every one is correct** —
a name joined to its own `coin` variant: GTA/GTA Coin/GTAcoin, Inu/InuCoin, wag/WAGCOIN, Dip/DipCoin,
PS5/ps5coin, LOL/LOLCOIN, CR7/CR7 COIN, 404/404 Coin, Ryu/Ryucoin, Six/SIXCOIN. No false merge appeared.
Synthetic dodge recall is unchanged (56.04% to 56.06%), so this is not a trade against evasion resistance.

**Recommendation: lower it to 3, not below.** It repairs 63 of the 85 scatterings and 210 of the 260 misplaced
launches at no observed cost. Below 3, one- and two-character names start routing without symbol confirmation,
and that is where confirmation earns its keep: ":3", "e" and "3" all fold to E and would merge into one room.

**Why this is an owner ruling and not a fix I can make.** `NAME_EQUAL_MIN_LEN` is marked "calibrated, not
configurable" and it is part of the NameLock key derivation, so changing it is a **breaking key change** of the
same class as `MULTI_FOLD` — possible now, impossible after mainnet. Four tests in `tests/test_rules.py` assert
the boundary explicitly and would need updating with it. Nothing is changed in this commit; the audit and the
numbers are recorded so the decision can be made on evidence.

### 27b. DIGIT_FOLD: keep, with a documented limitation

`DIGIT_FOLD` (0→O, 1→I, 3→E, 4→A, 5→S, 7→T, 8→B) moves the key of 2,446 launches (3.97%) and merges 20 rooms
that would otherwise be separate. Most are correct leet catches: N3ON COIN with Neon, Gh0st with GHOST, T4NK El
Yamen with Tank El Yamen, U0DF with UODF, BITCO1N with Bitcoin.

Three are wrong, and they share one cause — **digits colliding with roman numerals**:

- `N|GTAVII`: "GTA VII" (13 launches) merged with "GTAVI $1 Coin" (3), because GTAVI1COIN strips to GTAVI1 and
  1 folds to I.
- `N|GTAI`: "GTA 1" merged with "GTAI".
- `N|GTAS`: "GTA 5" merged with "GTA S".

Kept, because the leet catches are real and frequent while the collisions need a name mixing digits with roman
numerals. Recorded as a known limitation rather than fixed; any fix (suppressing the fold near roman numerals)
is more special-casing than the problem justifies.

### 27c. Refusals are correct

219 launches (0.36%) fold to nothing and our launchpad would turn them away. Every one is a name made only of
emoji, braille patterns, arrows, box-drawing characters or punctuation: "👌", "⠃⠇⠊⠝⠙⠁⠏⠑", "↑→↓←↑ ←↓→", "???",
"███", "$". These are genuinely unroutable and refusing them is right. Affix stripping was also checked: it moves
14.73% of keys and merges 433 rooms, and every room inspected was correct. Note that room count and door count
move very differently — the large rooms are dominated by byte-identical names, which is why rule I reshapes 433
rooms while adding little to the +1.1% door figure in section 26a.

### 27d. Three bugs in my own backfill, one of which was discarding most of the data

`watcher/backfill.py` as committed in `0a35ff3` had three defects. All three are fixed in this commit, and all
three were mine.

1. **Failed fetches advanced the cursor.** A signature whose transaction could not be fetched was counted and
   skipped, and the cursor moved past it, so the launch was lost permanently with no record of which one.
2. **A cumulative counter hid the failure rate.** The log printed total failures, not the rate for the page, so a
   run that had reached 100% failure still looked like it was working. It was found only by noticing that pages
   85, 86 and 87 each wrote zero launches while the counter climbed to 51,056. **Roughly 48,000 launches were
   silently skipped**, and because nothing recorded which signatures failed, they can only be recovered by
   walking the range again.
3. **A null result was treated as proof of absence.** `getTransaction` returning null means only that *this*
   endpoint has pruned the record. Measured 19 November 2026: publicnode had dropped transactions 2.37 days old
   that api.mainnet-beta still served in full, 10 of 10 on probe. The old code accepted the first null as
   authoritative, so everything older than the *shallowest* endpoint's retention was discarded as nonexistent.

Fixed: failures are appended to `failed.jsonl` and drained by `--retry`; the log reports the per-page failure
rate; concurrency halves above `--max-fail` and creeps back when clean; requests rotate over both endpoints with
a cooldown on 429; and a null is accepted as absent **only after every endpoint has answered and none has the
record**. Smoke-tested at 45 launches/s with a 0.0% page failure rate.

**The collection ceiling this exposed.** Past about 2.4 days, publicnode has pruned and only api.mainnet-beta
serves, and it rate-limits hard enough that throughput collapses (82 launches in several minutes against 45/s
inside the retained window). So roughly **2.4 days, about 105,000 launches, is the practical limit of free
historical collection**. Deeper history needs a paid archival endpoint. Collection beyond that limit has to come
from watching forward in real time, at roughly 1,750 launches an hour.

## 28. The fold order is load-bearing and was untested; how much disguise is actually live (19 November 2026)

Continuing the audit of section 27, on 63,401 launches.

### 28a. Appearance-folding must run before sound-folding, and nothing checked that it did

`_pre` applies the Unicode confusables table (rule B) and then transliterates whatever is left (rule C). Where
the two disagree, only the first is right for impersonation, because an impersonator exploits how a character
**looks**, not how it sounds:

| character | confusables (appearance) | anyascii (sound) |
|---|---|---|
| U+0420 CYRILLIC CAPITAL ER `Р` | `P` | `R` |
| U+0440 CYRILLIC SMALL ER `р` | `p` | `r` |
| U+0455 CYRILLIC SMALL DZE `ѕ` | `s` | `dz` |

**291 characters** in the pinned table disagree with their transliteration. The two lines in `_pre` were in the
right order, but nothing tested it: swapping them would have opened that whole attack class with no test failing,
exactly as with `MULTI_FOLD` in section 26.

This is not hypothetical. A live attack in the sample depends on it: `Реbu Thе Market Bull` (Cyrillic Р and е)
copying `Pebu The Market Bull`. It folds to PEBUTHEMARKETBUII and routes into the original's room. Under
transliteration alone it folds to **REBU**THEMARKETBUII and escapes.

`tests/test_fold_order.py` now pins the ordering, the three characters above, the live attack, cross-script kana
merges, and the generic property over all 291 disagreeing characters. Restricted to characters NFKC leaves alone,
since NFKC runs first and its answer stands where it decomposes — which is why U+017F LONG S keys as `s` rather
than the `f` the confusables table offers.

### 28b. A hypothesis of mine that was wrong

I expected rule C to be what makes non-Latin names usable at all, and that dropping it would make our launchpad
refuse every CJK-named launch. **It does not.** Refusals are identical at 229 (0.36%) with and without it, because
`_base` splits on `[^0-9a-zÀ-￿]+` and CJK characters fall inside that range, so they survive as letters either
way. Rule C only decides whether such a name keys as romanized text (`蝴蝶` to HUDIE) or as the raw codepoints.
Recorded because the claim was nearly written into the design notes as a justification for the rule.

### 28c. How much disguise is actually happening

Section 26a argued the folds are insurance against adaptation rather than a present need. The audit **confirms**
that, and now gives the number. Rooms each fold merges that would otherwise be separate:

| fold | rooms merged | launches pulled in |
|---|---:|---:|
| rule B, Unicode confusables | 2 | 2 |
| rule C, transliteration | 15 | 20 |
| `INVISIBLE`, blank-rendering alphanumerics | 0 | 0 |
| `MULTI_FOLD` (section 26) | 1 | 1, and it was a false merge |
| `DIGIT_FOLD` (section 27b) | 20 | 17 right, 3 wrong |

So roughly **22 live disguised impersonations in 63,401 launches, under 0.04%**. The attack families that do
appear are worth naming, because they are what adaptation will look like at scale: Cyrillic letter substitution
(`Реbu`, `Оversized`, `Cowbоys`, `Dеwiе Thе Turtlе`, `Finnеgan`, `Just а Memе`, `Stоrk`, `Tоken`), the turned-V
homoglyph for A (`ɅI` for `AI`, `GTA ɅI`, `Grand Theft ɅI`), and switching Japanese script (`毒うさぎ` against
`毒ウサギ`). In one family the disguised version is already **more numerous than the original** — `Dеwiе Thе
Turtlе` appears 7 times against 3 for the Latin spelling.

Rule B's 2 rooms look small only because rule C covers most of the same ground: anyascii also maps Cyrillic О, А,
Е, е, о, а, і to their Latin letters. The confusables table earns its place on precisely the characters where the
two disagree, which is why 28a matters more than the count of 2 suggests.

### 28d. `INVISIBLE` is complete over this sample

Every alphanumeric character in 63,401 real names and symbols that renders blank is already in `INVISIBLE`.
No gap was found. Recorded as a negative result so the check is not repeated blindly: the method was to look for
characters that `str.isalnum()` accepts (so `name_letters` keeps them) while being format, spacing or combining
category, or normalizing to whitespace. Characters that are not alphanumeric need no entry, since the separator
split discards them anyway.

### 28e. The class P escape hatch, measured

Following 27a: class P rooms require the **symbol** to match as well, so a copy that changes its symbol opens its
own room. This covers **157 of 5,468 occupied rooms (2.9%) and 1,313 of 52,566 routed launches (2.5%)** — narrow
in aggregate, but it is exactly the short, high-value tickers: `GTA` (132 launches), `VRL` (141), `657` (108),
`猫` (95), `67%` (94), `$wag` (32). Lowering `NAME_EQUAL_MIN_LEN` to 3 as recommended in 27a closes it for
three-character names, which is most of the value. It cannot be closed for one- and two-character names without
merging unrelated junk, and that remainder should be treated as an accepted limit rather than a bug.

## 29. The symbol key strips no affixes while the name key does (19 November 2026)

`name_letters` feeds `_strip_affixes`, so a trailing COIN, TOKEN, OFFICIAL, SOLANA or CTO leaves the **name** key.
`symbol_key` never calls it. For class N this is irrelevant, because the key is the name alone and the symbol does
not appear in it. For class P the key is (symbol, name), so the same short name splits across rooms purely by
whether the creator put COIN in the **ticker**:

```
name='gta' symbol='GTACOIN' -> P|GTACOIN|GTA
name='gta' symbol='GTA'     -> P|GTA|GTA
```

Measured on 65,630 launches: of 457 class P keys, this splits exactly **one** group — `P|GTA|GTA` with 149
launches against `P|GTACOIN|GTA` with 1.

**Not changed, and not worth changing on its own.** It is part of the on-chain NameLock derivation, so altering it
is a breaking key change, and the measured cost is one launch in 65,630. More to the point, the fix recommended in
section 27a subsumes it: at `NAME_EQUAL_MIN_LEN` 3 every affected name (GTA, INU, WAG, DIP, X) becomes class N,
where the symbol is not in the key at all. The asymmetry is also arguably correct rather than accidental — a name
is prose and a ticker is an identifier — but nothing in the code said so, which is why it is now documented and
pinned in `tests/test_symbol_affix.py`.

## 30. Narrative squatting: already bounded, now measured (19 November 2026)

`program/docs/SECURITY_REVIEW.md` records that the room **founder** position goes to whoever creates the room
first, that it pays a share of every later trade in the room including every door, that it matters only while
`founder_share_bps > 0` (it is 0 in both the devnet and mainnet config), and that squatting costs about 0.0288 SOL
of rent plus keeping the room live. That bound is correct and this is not a new finding. What was missing is
whether a squatter would have to **predict** which narratives take off, or could simply register broadly and wait.
It matters because turning the founder share on is a live option in `program/docs/FEE_DESIGN.md`.

Measured over 65,630 launches spanning 57.6 hours, for rooms whose first launch is at least 6 hours inside the
window so the fill time is not censored by the window edge:

| | median | 25th | 75th | within 5 min |
|---|---:|---:|---:|---:|
| 1st door after door 0 | 2.3 min | 0.1 | 62.1 | **56.9%** |
| 2nd door | 18.8 min | 0.9 | 279.8 | 40.7% |
| 4th door | 59.9 min | 2.6 | 427.3 | 31.0% |

**Rooms fill too fast to react to.** The first door arrives within five minutes in 57% of cases, so a squatter
cannot watch a narrative start and then race to register it. They would have to hold the key in advance.

Registering in advance looks cheap until you ask which keys:

| rooms registered | rent | launches sitting under them |
|---:|---:|---:|
| 100 | 2.9 SOL | 18,039 (27.6% of all flow) |
| 1,000 | 28.8 SOL | 38,696 (59.2%) |
| 5,000 | 144.0 SOL | 53,114 (81.2%) |

**That table is retrospective and must not be read as an attack cost.** It is the concentration of flow over the
*largest* rooms, chosen with hindsight. Picking them in advance is the whole difficulty: 65.9% of rooms never
receive a single door, and the biggest rooms in this sample are trend-specific names nobody could have
pre-registered — Dacity (1,128 launches), AudaCity (628), Apocry, Lucia, Mandy, dog wif cap. A squatter buying
breadth blindly would mostly be buying the two thirds of rooms that stay empty.

**Conclusion: the attack needs prediction, and prediction is hard on this traffic.** The residual worth watching
is not the trend names but the evergreen ones — DOG, CAT, AI, INU, GTA, PEPE recur across cycles and are cheap to
hold. If `founder_share_bps` is ever raised above 0, the mitigation that follows from these numbers is to cap or
taper the founder share rather than to add a reservation mechanism, since the earlier reservation was removed for
good reasons (section 16) and the rooms fill faster than any reservation window would help.

**Limit of this measurement.** 57.6 hours is one market episode, dominated by the GTA VI and Dacity/Audacity
waves. Fill times in a quiet week could be much slower, which would make breadth more viable. Re-measure before
acting on it.
