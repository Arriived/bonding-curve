# Matcher service: corrections

These are conflicts between the brief and what the deployed program, the research code or this
environment actually do, each verified before building on it. Item 1 is the expiry question the brief
asked about.

## 1. The program verifies no expiry; the runtime does, through the blockhash

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

## 2. Single use: what the program enforces, and what the service only tracks

**Enforced on-chain:**

| replay | stopped by |
|---|---|
| the same signed transaction twice | runtime signature de-duplication within the blockhash window (`AlreadyProcessed`, e2e step 5), then blockhash expiry |
| the same room-id nonce twice | `init` on the Room PDA `["room", room_id]` |
| the same door index twice | `init` on the Door PDA `["door", room, door_count]` |

**Tracked by the service only (per process, `matcher_service/inflight.py`):**

- **Two different launches decided against the same snapshot.** If two launchers ask for the same new
  name within one blockhash window, both would get "new room". The second would bypass the T2n rule.
  The service refuses the second with 409 and `retry-after` until the first lands or expires.
- **Door index allocation.** Concurrent door decisions into one room take consecutive indices.

Running more than one replica requires moving this state to shared storage (README, "What remains").

## 3. The door index is `room.door_count` at execution: concurrent doors into one room serialise

`OpenDoor` derives the new door's address from `core.room.door_count` (`contexts.rs`). Consequences:

- Two launches into the same room in the same window need different indices.
- If the earlier one is dropped and never lands, every later one fails on-chain, and must re-request
  after the earlier decision expires (at most about 32 s).
- A popular room therefore admits roughly one door per landing slot, and a dropped transaction stalls
  the others.

**A program change would remove the coupling:** derive the Door PDA from the launcher and a
matcher-chosen nonce, as `create_room` already does for rooms.

## 4. The deployed program is not the branch tip

This service targets the program actually deployed: `436c002` plus the program-ID patch, pinned ELF
`f2cfdb85…b436`. It pins that program's IDL in `idl/doors_v1.deployed.json`.

The branch tip `8ce373f` differs in two ways:

- It fails 10 of 38 of its own SBF tests (`program/docs/CORRECTIONS.md`, devnet preflight item 1).
- It changes the instruction layout: it adds `Launch.expected_terms_hash`.

When a fixed tip is deployed, `idl/` and `txbuild.encode_launch` must be updated together, and the
layout test re-run.

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
