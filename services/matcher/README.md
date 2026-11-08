# Doors matcher service

**What it is.** The off-chain matcher that decides, for every launch, whether the coin becomes a door
in an existing live room or a new room. The launcher never chooses. The deployed doors program accepts
`create_room` and `open_door` only when the transaction is also signed by `Config.matcher_authority`.

**It is a hard dependency of every launch.** If it is down, or refuses, nobody can launch. That is
intentional: it refuses rather than guesses.

- **Rules:** ported from `research/doors_into_one_room/scripts/narrative/matcher.py`, with the
  calibration in `research/doors_into_one_room/NARRATIVE_DETECTION.md`.
- **Program:** the paired-doors prototype, ID `8tPd1ZUEGxrj5zYu8aeg95cU92nmKWKYKoSaKPqFuZAZ`.
  This branch targets its offline interface, pinned in `idl/doors_v1.paired.json` and
  `idl/layouts.paired.json`. The older `*.deployed.json` pins are historical.
  This port does not deploy or claim a deployment.
- **Conflicts with the brief:** [CORRECTIONS.md](CORRECTIONS.md).

## What a decision is

The program has no separate decision message, so **the matcher co-signs the launch transaction
itself**. `POST /route` returns that transaction with the matcher's signature in place and the
launcher's signature slot empty. The launcher's wallet signs as fee payer and submits.

Changing anything invalidates the matcher signature:

- metadata, amounts, fee cap;
- the room, the door nonce (and so the door address), SlugLock or old-holder accounts;
- the compute budget, the blockhash, `expires_at_slot`.

**Expiry is enforced twice.**

- The program rejects the launch after `Launch.expires_at_slot`. The service sets it to the blockhash's
  slot + 150, and the program refuses any value more than 150 slots ahead. This holds even for a
  transaction on a durable nonce.
- The runtime rejects the transaction after its blockhash's `last_valid_block_height`.

Either way, a decision lives about 150 slots, roughly 32 s (CORRECTIONS §1).

**Door addresses** come from a random, non-zero 64-bit nonce, which is signed in `Launch.door_nonce`.
Concurrent door launches into one room do not contend, and a dropped one blocks nothing
(CORRECTIONS §3).

### Rules

| stage | rule |
|---|---|
| metadata | `Launch::validate` limits, in bytes: name 1–32, symbol 1–10, uri ≤ 200 |
| floor | The candidate's SlugLock, keyed by the program's own fold. A live holder means a door into it (rule `floor`); the program enforces this. A dead holder is passed as `old_holder`. A graduated holder is refused (409). |
| text | Research normalisation (NFKC, homoglyphs, digit and rn/vv folds, stopwords, suffixes). A match is **T3**, folded symbol and name both equal, or **T2n**, folded name equal with at least 4 characters. Since CORRECTIONS §17 a room is matched only through faces carrying its own name key (door 0's): equivalent to the calibrated rule, without the floor bridge that let one room absorb another narrative. Since CORRECTIONS §18 and §20, four rules are live. A: the 4-character minimum is measured on the whole name. B: Unicode confusables, and I/l/1/| read alike. C: other non-ASCII letters are transliterated (anyascii). I: the name's letters are joined and folded once, so case and spacing cannot change the key; a trailing COIN/TOKEN/OFFICIAL/SOLANA/CTO and a leading THE/OFFICIAL are stripped. Two launches route together exactly when their name keys are equal. Name keys are pinned to Unicode 15.1.0, to the hash of `data/confusables_ascii.json` and to anyascii 0.3.3; the service and verifier refuse anything else. Symbol-only, fuzzy, image and social-link matching are not implemented; measured candidates are in `RULE_CANDIDATES.md`, and dodge recall per rule is in `EVASION_BENCHMARK.md` (`scripts/evasion_benchmark.py`; the phonetic candidate needs `requirements-research.txt`). |
| liveness | The program's `Room::live` with thresholds read from Config: `age < live_new_seconds OR (reserve ≥ live_min_reserve AND idle ≤ live_max_idle AND 24 h hourly-bucket volume ≥ live_min_volume)`. Defaults: 1 h, 0.5 SOL, 6 h, 5 SOL. |
| ties | floor; then T3 over T2n; then greater reserve; then lowest room id |
| graduated rooms | Never a target in v1. The program fails closed with `PhaseTwo` (CORRECTIONS §8). |
| otherwise | A new room with a CSPRNG u64 room-id nonce. |

## API

**`POST /route`.** Body:

```json
{"launcher": "<base58>", "name": "...", "symbol": "...", "uri": "...",
 "first_buy_lamports": 0, "min_tokens_out": null, "max_slippage_bps": 200,
 "max_fee_lamports": 0, "cu_price_micro_lamports": 0,
 "issued_at": 1793900000, "signature": "<base58 ed25519 by launcher>"}
```

**Every request is signed by the launcher** (`matcher_service/auth.py`).
- **What is signed:** `signature` is the launcher's ed25519 signature (a wallet's
  `signMessage`) over:

  ```
  doors-matcher:route:v1\n
  ```

  followed by the JSON array of the ten fields above, in this order:

  ```
  [launcher, name, symbol, uri, first_buy_lamports, min_tokens_out,
   max_slippage_bps, max_fee_lamports, cu_price_micro_lamports, issued_at]
  ```

  Integers are sent as decimal strings, an absent optional field as `null`, with
  no whitespace. `JSON.stringify` produces exactly these bytes.
- **Freshness:** `issued_at` must be within 120 s of the server clock, and each
  signature is accepted once. A retry or a new request identical to an earlier one
  must therefore advance `issued_at`. ed25519 is deterministic, so identical bytes
  give an identical, already-used signature.
- **Strict fields:** unknown fields are refused.
- **What it costs the caller:** one `signMessage` per request, in addition to
  signing the returned transaction.
- **What it buys:** the per-launcher rate limit keys on a key the caller proved
  control of. It cannot be evaded with made-up pubkeys, or spent by someone else
  against a victim's wallet (`program/docs/SECURITY_REVIEW.md` M-3).

**First-buy price limit** (M-4). With `first_buy_lamports > 0`:
- **Omitted `min_tokens_out`:** the service quotes the buy against the snapshot,
  exactly as the program will execute it, settling any pending backlog first. It
  signs `min_tokens_out = floor(quote × (10,000 − max_slippage_bps) / 10,000)`.
  `max_slippage_bps` defaults to **200 (2%)**, within `DESIGN.md` §3's "frontend
  default should be ≤ 2–3%", and must be 1–5,000.
- **An explicit `min_tokens_out`** is used as given.
- **An explicit 0** is refused.
- **What it guarantees:** no launch buy is signed without a price limit. A price
  that moves further than the tolerance before the launch lands makes the program
  reject it (`Slippage`, e2e step 3b).
- **Recorded:** the quote is stored in the decision record (`first_buy_quote`).

`200` returns:

- `id`, which is the matcher signature;
- `decision`: kind, rule, room id and address, door nonce and address, SlugLock, old holder, the evaluated
  rooms;
- `transaction_base64`;
- `last_valid_block_height`;
- `expires_at_slot`;
- `state_slot`;
- `record_sha256`.

Refusals return `{"error": code, "message": ...}`:

| HTTP | codes |
|---|---|
| 401 | `unauthenticated` (missing, wrong, stale or reused launcher signature) |
| 422 | `invalid_request`, `invalid_metadata`, `fee_limit`, `first_buy_unfillable`, `insufficient_funds` (new room only: the launcher's balance does not cover the launch) |
| 409 | `in_flight` (a new-room decision for the same folded name or identity is unexpired); `launcher_in_flight` (this launcher already holds an unexpired new-room decision; the message names it); `graduated_identity` |
| 413 | `tx_too_large` |
| 429 | `rate_limited` |
| 503 | `rpc_unavailable`, `stale_state`, `inconsistent_state`, `signer_unavailable`, `signer_mismatch`, `store_unavailable`, `program_paused`, `nonce_exhausted` |

409, 429 and 503 carry `Retry-After`.

**Other endpoints:**

| endpoint | returns |
|---|---|
| `GET /decision/{id}` | the stored record: inputs, the room state it saw with slots and clock, the rule, the signed message, and its hash-chain fields |
| `GET /health` | `200` only when a snapshot inside the freshness budget exists **and** the signer's public key equals `Config.matcher_authority`; `503` with a reason otherwise. Use it as the readiness probe. |
| `GET /metrics` | Prometheus text, below |

**Metrics:**

- `matcher_requests_total`;
- `matcher_decisions_total{kind,rule}`, the door versus new-room mix;
- `matcher_refusals_total{code}`;
- `matcher_route_seconds` histogram;
- `matcher_rpc_errors_total`, `matcher_rpc_errors_cumulative`;
- `matcher_snapshot_slot`, `matcher_snapshot_age_seconds`.

**Logs:** one JSON object per line on stdout. They include every decision (id, kind, rule, room, slot,
launcher) and every refusal (code, message, IP).

## Configuration

Environment variables only. **No secret is ever read from the environment.** The service exits at
start if `MATCHER_PRIVATE_KEY`, `MATCHER_SECRET_KEY` or `MATCHER_KEYPAIR` is set.

| variable | default | meaning |
|---|---|---|
| `MATCHER_ENV` | `development` | `production` refuses the keyfile signer |
| `MATCHER_RPC_URL` | required | Solana JSON-RPC endpoint (`confirmed` commitment) |
| `MATCHER_PROGRAM_ID` | `D7Ys…NVJG` | must equal the pinned IDL's address |
| `MATCHER_SIGNER` | `gcp-kms` in production, else `keyfile` | `gcp-kms`, `aws-kms` or `keyfile` |
| `MATCHER_GCP_KEY_VERSION` | — | `projects/*/locations/*/keyRings/*/cryptoKeys/*/cryptoKeyVersions/*` |
| `MATCHER_AWS_KEY_ID` | — | key ID, ARN or alias |
| `MATCHER_KEYFILE` | — | development only: path to a Solana keypair JSON |
| `MATCHER_DB` | `decisions.sqlite3` (`/data/…` in the image) | decision store |
| `MATCHER_VERSION` | 1 | written into `Launch.matcher_version` |
| `MATCHER_COHERENCE_SLOTS` | 30 | all reads of one snapshot within this many slots of each other |
| `MATCHER_MAX_LAG_SLOTS` | 30 | snapshot at most this many slots behind the cluster when signing (about 6.5 s at 0.215 s/slot) |
| `MATCHER_MAX_AGE_SECONDS` | 8 | snapshot read at most this long ago |
| `MATCHER_REFRESH_SECONDS` | 2 | background snapshot refresh interval |
| `MATCHER_CU_LIMIT` | 400000 | compute-unit limit in the launch transaction |
| `MATCHER_MAX_CU_PRICE` | 1000000 | highest priority fee a request may ask for (micro-lamports) |
| `MATCHER_RATE_IP_PER_MIN` | 30 | per-IP limit on `/route` |
| `MATCHER_RATE_LAUNCHER_PER_MIN` | 6 | per-launcher limit on `/route`, keyed on the signature-verified launcher |
| `MATCHER_TRUST_X_FORWARDED_FOR` | 0 | `1` only behind a proxy that appends to it |
| `MATCHER_TRUSTED_PROXY_HOPS` | 1 | with the above: the client IP is the X-Forwarded-For entry this many places from the right (1 for nginx `$proxy_add_x_forwarded_for`, 2 behind a GCP HTTPS load balancer). Entries further left are client-supplied and ignored |

**The freshness budget** (`MATCHER_COHERENCE_SLOTS`, `MATCHER_MAX_LAG_SLOTS`,
`MATCHER_MAX_AGE_SECONDS`) is enforced at signing time:

- outside it, the service attempts one synchronous refresh, then refuses with 503 `stale_state` or
  `rpc_unavailable`;
- the decision record stores every read's slot, the cluster slot at decision time, and the clock used
  as "now";
- the program re-checks liveness and the floor at execution, so a room that dies between decision and
  landing makes the transaction fail. It does not misroute.

## Secrets: the matcher authority key

**The key decides where money goes.** Handle it accordingly:

- **Production: a KMS.** The private key never exists outside the KMS, and the service only calls its
  sign API.
  - **Google Cloud KMS:** a key with purpose `ASYMMETRIC_SIGN` and algorithm `EC_SIGN_ED25519`. The
    service account needs only `roles/cloudkms.signerVerifier` on that key. Credentials come from
    Application Default Credentials, i.e. workload identity or the metadata server, never a JSON key
    in the image.
  - **AWS KMS:** key spec `ECC_NIST_EDWARDS25519`, usage `SIGN_VERIFY`. The role needs `kms:Sign` and
    `kms:GetPublicKey` on that key only. Credentials come from the instance or task role.
- **Development: a keyfile.** A Solana keypair JSON path in `MATCHER_KEYFILE`, refused when
  `MATCHER_ENV=production`. Never commit it; the repository's `.gitignore` covers `*-keypair.json`.
- **Every signature is verified** against the configured public key before it is used.
- **The service will not sign** unless that public key equals `Config.matcher_authority` on-chain.
- **Rotation:**
  1. Create a new KMS key.
  2. The program admin sets `Config.matcher_authority` to its public key with `update_config`.
  3. Point `MATCHER_GCP_KEY_VERSION` or `MATCHER_AWS_KEY_ID` at the new key.

  Until steps 2 and 3 agree, `/health` stays unready and `/route` refuses. The full procedure,
  including the whole-`Settings` diff check, is `program/docs/DEPLOYMENT.md` §9.

## Deployment

**Build from the repository root.** The test stage runs the unit suite, and the runtime image is built
only if it passes:

```bash
docker build -f services/matcher/Dockerfile -t doors-matcher .
```

Behind a TLS-intercepting proxy, also pass `--secret id=pipca,src=<ca-bundle.crt>`. It is used by pip
only and is not stored in any layer.

**Run:**

```bash
docker run -d --name matcher -p 8080:8080 -v matcher-data:/data \
  -e MATCHER_RPC_URL=https://<your-rpc> \
  -e MATCHER_GCP_KEY_VERSION=projects/<p>/locations/<l>/keyRings/<r>/cryptoKeys/<k>/cryptoKeyVersions/1 \
  doors-matcher
```

**About the image:**

- It runs as uid 10001.
- It defaults to `MATCHER_ENV=production` and `MATCHER_SIGNER=gcp-kms`.
- It persists decisions to `/data`. **Back up that volume:** the decision store is the audit trail.
- It has a container `HEALTHCHECK` on `/health`.
- **Run exactly one replica.** Rate limits and the request-replay cache are per process (see "What
  remains").
- Put a TLS-terminating proxy in front of it, and set `MATCHER_TRUST_X_FORWARDED_FOR=1` only there.

## Failure modes: each one refuses

| condition | behaviour |
|---|---|
| RPC unreachable or erroring | `/route` → 503 `rpc_unavailable`; `/health` → 503; nothing signed, nothing stored |
| state outside the freshness budget, after one refresh attempt | 503 `stale_state` |
| an account fails validation (layout, PDA, mutable mint) | 503 `inconsistent_state` |
| KMS unreachable, erroring or returning a bad signature | 503 `signer_unavailable` |
| signer key ≠ `Config.matcher_authority` | 503 `signer_mismatch`; `/health` unready |
| decision store unwritable | 503 `store_unavailable`; the signature is discarded, because an unrecorded decision is never released |
| program paused | 503 `program_paused` |
| concurrent new-room launches for one name | both are signed under one `NameLock`; the program lets the first land and rejects the other (`Holder`, 6013) with nothing created. Re-requested, it routes as a door |
| new room whose name is held by a graduated room | 409 `graduated_name` (the program has no graduation adapter in v1) |
| `NameLock` held by a live room the text rule did not match | 503 `inconsistent_state` (only possible under other Unicode tables); fail closed |
| body over 8 KiB | 413 `request_too_large`, before parsing |
| metadata with lone surrogates | 422 `invalid_metadata` |

There is no default routing on any path. The unit tests (`tests/test_failures.py`) assert for each
case that nothing is signed or recorded.

## Tests

```bash
pip install -r requirements-dev.txt
```

```bash
python -m pytest -q tests
```

The unit tests (108) cover:

- **the research matcher's 14 worked examples**, through the research module and through the
  service;
- **normalisation:** confusables, homoglyphs, NFKC, emoji, punctuation, casing, invisible
  characters, camelCase, stopwords, the 4-character name minimum, and parity with the research
  module;
- **the program fold** against the SBF suite's reference vectors;
- **liveness boundaries,** just inside and outside each of the four thresholds plus the bucket
  window edges;
- **each tie-break tier, and floor handling** for live, dead and graduated holders;
- **failure cases:** stale state, incoherent reads, RPC down, blockhash unavailable, signer
  unavailable or mismatched, store down, concurrent new rooms signed under one NameLock, independent random door
  nonces, and the expiry, terms hash, door nonce and name key carried in the signed launch;
- **the NameLock key:** equal for two launches exactly when T3 or T2n routes them together, over every pair of the
  slug-coverage classes, the research examples and edge cases; the verifier's independent derivation from the
  research matcher gives the same key; dead, graduated and inconsistent name holders;
- **signers:** keyfile refused in production, a bad signature rejected, GCP and AWS KMS against fakes,
  the CRC32C check value;
- **store:** append-only, tamper detection;
- **HTTP:** launcher-signed requests (unsigned, wrong key, altered, stale, replayed, unknown fields), a victim's
  limit not spendable by others, rate limits per IP and per launcher, health, metrics, decision lookup;
- **first-buy price limit:** the quote against the program's reference vector, the 2% default, explicit
  limits, refusal of an explicit 0 and of an unfillable buy;
- **layout:** the decoder offsets equal the deployed layout file.

**End to end:** `python3 tests/e2e/e2e.py <keys_dir>`. Its target is the single line in
`tests/e2e/target`:

| target | what it does | status |
|---|---|---|
| `localnet` | Starts `solana-test-validator` with the pinned deploy ELF as an upgradeable program, owned by the real upgrade-authority key, and initialises Config with the real matcher key. | **PASS** |
| `devnet` | The same test against the program deployed on devnet (`program/docs/DEPLOYMENT.md` §5), using the smoke wallets' own devnet balances. Step 6 (blockhash expiry) runs on localnet only. | **PASS**, 5 November 2026: every on-chain step, and all four decisions verify AGREE. `tests/e2e/target` is `devnet`. |

The test runs these steps:

1. A new identity gets a new room, and the program accepts it.
2. The same identity from another wallet gets a floor door.
3. A buy through door 0.
4. The same name with a different symbol gets a T2n door.
   - A door launch with a first buy and the default 2% limit fills exactly the quoted tokens when nothing
     moves, and is rejected on-chain with `Slippage` when a 1 SOL buy lands first.
5. A decision tampered after signing is rejected at signature verification.
6. A decision with the matcher signature stripped is rejected on-chain with `AccountNotSigner` (3010).
7. Replaying an accepted decision is rejected with `AlreadyProcessed`.
8. A decision submitted after its blockhash expired is rejected with `BlockhashNotFound`.
   - A matcher-signed launch past its `expires_at_slot` is rejected on-chain with `Expired`, while
     its blockhash is still valid.
   - A launch on a durable nonce, held past `expires_at_slot`, is rejected on-chain with `Expired`.
9. Records are served by `/decision/{id}`, and the hash chain verifies.
10. `verify_decision.py` agrees with every accepted decision.
11. The verifier reports DISAGREE on three doctored records.

## Launch watcher (shadow mode over pump.fun and LaunchLab)

`watcher/` streams launches from other launchpads and runs our matcher on each one. Nothing is signed or sent. It
answers one question: how many of these launches would have become a door in an existing room on our launchpad?

**What it watches:**
- pump.fun (program `6EF8…F6P`).
- Raydium LaunchLab (`LanMV9…J3uj`), which hosts bonk.fun, StonkFun and about 5,000 other platform configs.
- A LaunchLab launch is labelled with the declared name and website in its `PlatformConfig` account. Those fields
  are self-declared: anyone can create a config called "StonkFun". The label therefore groups by declared site:
  `stonkfun.xyz` as StonkFun, `letsbonk.fun`/`bonk.fun` as bonk.fun, otherwise the declared name.

**How it reads the chain:**
- One websocket `logsSubscribe` per program.
- pump.fun launches decode from the `CreateEvent` in the logs.
- LaunchLab launches, and pump.fun launches whose logs lack the event, are fetched with `getTransaction` and decoded
  from the create instruction's own arguments.
- Layouts come from each program's on-chain Anchor IDL, saved in `watcher/idl/` and checked by
  `tests/test_watcher.py`.

**Free endpoints**, as tested from the build environment on 7 November 2026:

| endpoint | HTTP | websocket | notes |
|---|---|---|---|
| `api.mainnet-beta.solana.com` (Solana Foundation) | yes | **yes** | the websocket carries all pump.fun traffic (about 1,250 notifications per 5 s); `getSignaturesForAddress` on busy programs returned 429 |
| `solana-rpc.publicnode.com` (PublicNode) | **yes**, including `getTransaction` | timed out | `getProgramAccounts` refused (403); needs a User-Agent header |
| OnFinality, dRPC, Ankr, NodeFlare, Omniatech, LeoRPC public URLs | not reachable from the build environment's network policy | | untested, not known to fail |

The defaults are the Foundation websocket and the PublicNode HTTP endpoint, with Foundation HTTP as fallback. Free
endpoints are shared and rate-limited and can drop subscriptions. The watcher reconnects with backoff, but a dropped
minute is a missed minute. For complete coverage, use a provider's websocket (Helius, Triton, QuickNode and others
have free or cheap plans). Pass it as `WATCHER_WS` / `WATCHER_HTTP` (comma-separated) rather than on the command
line; logs and the summary show only each endpoint's host.

**Run** (from `services/matcher`, with `requirements.txt` and `requirements-watcher.txt` installed):

    python3 -m watcher.watch --out /var/lib/doors-watch            # until stopped; resumes from launches.jsonl

**Outputs:**
- `launches.jsonl`: one line per launch with the shadow decision.
- `summary.md`: rewritten every minute.
- `events.log`: connection events.

It must run on a machine that stays up. A cloud session's container is temporary.

**Read the numbers with these limits:**
- Rooms are only those formed during the watch, all treated as live. Early in a run, launches cannot match older
  narratives.
- "Would be a door" counts the same wallet relaunching separately from copies by other wallets.
- The matcher's precision on these launches has not been measured: the routes are unlabelled.

## Verifying a decision

```bash
python3 scripts/verify_decision.py <decision_id> --rpc <archival-rpc> --service https://matcher.example
```

Use `--db decisions.sqlite3` in place of `--service` to read the store directly; that also verifies
the hash chain.

**What it does:**

- **State:** it rebuilds the state of every room that could have matched, and the SlugLock holder, at
  the decision slot. It replays the program's events from transaction history; RPC cannot serve past
  state (CORRECTIONS §9).
- **Decision:** it recomputes the decision with the *research* matcher, not the service's port.
- **Signature:** it checks the matcher signature against the matcher authority in force at that slot.
- **Transaction:** it decodes the instruction and compares it to the record.
- **Outcome:** it reports whether the transaction landed.

Exit 0 means agree; 1 means disagree; 2 means it could not complete.

## What remains before this can run unattended

1. ~~Devnet~~: done. The program is deployed, and this e2e passes there.
2. **Real KMS.** Create the key, run the service against it on devnet, and set
   `Config.matcher_authority` to the KMS public key. Both signers are tested only against fakes.
3. **More than one replica.** Move rate limits and the request-replay cache to shared storage (for
   example Redis), and the decision store to a managed database with point-in-time backups. SQLite
   with one writer is a single-instance design.
4. **Publish the store's hash-chain head**, for example periodically as an on-chain memo. Without it,
   the operator could rewrite history undetected by outsiders.
5. **Scale the state source.** Every snapshot does `getProgramAccounts` for all rooms and doors. That
   is fine at devnet scale; production needs an indexer (Geyser or websocket) feeding the snapshot,
   with the same freshness checks.
6. ~~Program changes recommended in CORRECTIONS~~: done in the program (`e9bd2aa`). There is now an
   explicit `expires_at_slot` (§1), and door addresses are not tied to `door_count` (§3).
7. **v0 transactions with a lookup table** for longer metadata (§10). **Recommended next, and no longer
   blocked:** finding M-7 is closed (the v0 maximum takeover fits the heap with 1,280 bytes to spare), and
   a launch uses at most 49 of its 64 instruction-trace entries (M-8). The NameLock (item 8) made it
   pressing: at name 32 and symbol 10, legacy transactions now cap the URI at 51 bytes for a new room and
   19 for a takeover, and a takeover of two locks held by different dead rooms does not fit at all. With
   a lookup table of the six accounts every launch shares, the same shapes take 200, 169 and 137
   (`scripts/max_uri.py`, which prints both). Today a longer launch is refused with 413 `tx_too_large`.
8. ~~H-1~~: **closed on-chain.** `create_room` creates a `NameLock` PDA keyed by the name key this
   service signs (`rules.name_lock_key`), atomically with the room, so two rooms can never hold one key
   while the first is live. The key is equal for two launches exactly when the text rule routes them
   together (T3 or T2n), tested over every pair (`tests/test_rules.py`). The service is still trusted to
   compute the key, but no longer to serialise concurrent decisions: the in-flight reservation, the
   one-hold-per-launcher limit and the proof of funds are gone, and with them the reservation squatting
   of H-1. What the reservation still did, and nothing does now: when two launchers race one new name,
   the faster transaction becomes the room's founder and the other fails on-chain (it pays only its
   transaction fee and, re-requested, becomes a door). That matters only while `founder_share_bps > 0`.
9. **Alerting.** On `/health` unready, refusal-rate spikes by code, snapshot age, RPC errors and the
   decision mix. Plus an on-call runbook for key rotation and RPC failover.
10. **An archival RPC** for the verifier, and a public, independently operated verifier run over the
   decision feed.
11. **The branch tip** is fixed, and the service targets it (CORRECTIONS §4). On any later program
    change, update `idl/`, `txbuild.encode_launch` and `program/devnet/DEPLOY_ELF.sha256` together,
    and rerun both test suites.

## Paired launch price protection (7 November 2026)

`first_buy_quote.tokens` and `min_tokens_out` are door base units (six decimals).
The quote anchors the new door at the room spot before pending settlement, settles
pending room fees, quotes SOL to room tokens, then quotes room tokens to door tokens.
The independent verifier rebuilds the room's sold amount and pending fees from events.

`max_room_price` is an optional decimal u128 string, in lamports per room base unit
multiplied by 10^18. With a first buy, omission fills it from the snapshot spot
multiplied by (10000 + max_slippage_bps)/10000, rounded down. `"0"` disables this
additional bound. An explicit `min_tokens_out` does not disable room-price protection.
The token minimum and room-price bound are both included in the co-signed Launch.
The canonical launcher request appends `max_room_price` after `issued_at`; clients
must sign the updated `auth.FIELDS` sequence, including null when omitted.

The paired Launch appends this 16-byte field. Room creation NameLock derivation
still reads name and symbol only; no matching or normalization rule changed.
Run `scripts/max_uri.py --json` for the resulting transaction-size limits.
The offline program ID is read once from the paired IDL by `program_id.py`.
