# Doors v1: pre-audit security self-review

5 November 2026. Branches `claude/program-v1` (program) and `claude/matcher-service`
(off-chain matcher). Nothing is deployed.

**This is the authors' own review, written for the external audit.** The code
under review was largely written by the reviewer. Read every "clean" verdict as
"checked by the author, no defect found", not as a proof. Uncertain items are
reported as uncertain.

Every number below comes from a re-runnable script or test, named where it is
used. Most refer to program ELF `34d4ce91…d9e`: program source `1558b2e`; tests and
`verification/build.json` at `805bae3`.

**Contents**

1. [Findings](#1-findings), ranked
2. [Who can do what: threat actors](#2-who-can-do-what-threat-actors), in plain language
3. [Checked and found clean](#3-checked-and-found-clean): the coverage
4. [Not checked, and why](#4-not-checked-and-why)

---

## 1. Findings

**Severity** reflects impact once deployed:
- **High:** breaks a core guarantee or availability for anyone, cheaply.
- **Medium:** needs conditions, or harms a narrower set of people.
- **Low:** limited harm.
- **Info:** a design property worth knowing.

**Status** is one of: fixed in this review; open (an owner or spec decision); or
known (already documented).

| # | severity | status | title |
|---|---|---|---|
| H-1 | High | open | Free, unauthenticated name reservations let anyone block any name from getting a room |
| M-1 | Medium | fixed (margin still thin) | Launch heap nearly exhausted: the metadata change overflowed it; after the fix, worst-case `create_room` keeps 688 bytes, a service-signable takeover 496 |
| M-2 | Medium | fixed | Matcher in-flight check and reservation were not atomic: concurrent requests could both get "new room" |
| M-3 | Medium | open | Per-launcher rate limit keys on an unauthenticated field |
| M-4 | Medium | open | The service signs door launches whose first buy has no slippage limit by default |
| M-5 | Medium | open (spec) | Pause stops sells: holders cannot exit while the admin keeps the program paused |
| M-6 | Medium | open (spec) | Liveness thresholds are global and mutable: the admin can make any room dead and free its identity |
| M-7 | Medium | open | A prefunded maximum-metadata `create_room` takeover exhausts the heap (pre-existing; v0-only size) |
| L-1 | Low | fixed | X-Forwarded-For: the client-supplied leftmost entry was the rate-limit key |
| L-2 | Low | fixed | `/route` body size unbounded; any string became a rate-limiter key |
| L-3 | Low | fixed | Lone UTF-16 surrogates in metadata caused a 500, not a refusal |
| L-4 | Low | fixed | The program e2e compared live CU against a different ELF |
| L-5 | Low | fixed | The spec table generator still wrote the old index-based door seeds |
| I-1 | Info | fixed | `claim` edited lamports before its last CPI, the class that broke `8ce373f` |
| I-2 | Info | open | The design's door-fee rebate lowers the cost of sandwiching every trade in a room |
| I-3 | Info | known | Keeping a dead room live costs about 0.02 SOL a day |
| I-4 | Info | known | The on-chain identity floor is ASCII-oriented; non-ASCII look-alikes rely on the matcher |
| I-5 | Info | open | Door decisions reserve nothing; only deterministic routing makes this safe |
| I-6 | Info | open | Claiming SOL fees requires the recipient to hold a classic WSOL account |
| I-7 | Info | known | Fees accumulated near the cap can block buys until holders sell |
| I-8 | Info | open (doc) | The narrative spec describes a `set_matcher_authority` instruction that does not exist |
| I-9 | Info | known | Decision log: the operator can rewrite it until its head is published |
| I-10 | Info | known | One room, one write lock: every door's trades serialise on the room |

### H-1 — Free name reservations block any name (open)

**Attack.**
1. Ask `/route` for a new-room decision for a target name. Any launcher pubkey
   will do: requests are unauthenticated.
2. Never submit it. The service holds the folded name and identity until the
   decision's `last_valid_block_height`, about 150 blocks or 60–90 s.
3. Anyone else asking for that name meanwhile gets `409 in_flight`.
4. Repeat every minute. The name can then never get a room.

The attacker needs only HTTP requests. Rate limits do not stop it:
- per launcher: the attacker picks a fresh pubkey each time;
- per IP: 30 a minute, and one request a minute is enough.

**Affected code:** `services/matcher/matcher_service/service.py` (`inflight.claim`),
`inflight.py`, `app.py`.

**Exploitable today?** Yes, against any running service. Nothing is deployed.

**Why it is not fixed here.** The reservation exists for a reason. Without it, two
same-name launches inside one window would both get "new room", silently
bypassing the T2n rule (M-2). Every remedy changes the API or the economics, so
this is the owner's decision:

| remedy | effect |
|---|---|
| launcher-signed requests (sign the request body with the launcher key) | binds a reservation to a key holder; Sybil keys are free, so add the next row |
| check the launcher can pay rent + fees at decision time; one in-flight new-room decision per launcher | makes each live reservation cost a funded wallet |
| shorter hold, e.g. release on the decision's `expires_at_slot` | same window today; shortening needs a shorter launch window |
| no hold, and let the second launch land as a duplicate-name room | removes the DoS, gives up T2n under concurrency |

### M-1 — Launch heap nearly exhausted (fixed; margin still thin)

**Background.** The SBF heap is 32 KiB and a bump allocator: nothing is ever
freed. `mint_check` deserialised the whole `TokenMetadata` (name, symbol, URI,
every metadata pair) on each call, and `door_check` / `room_check` call it several
times per instruction.

**What happened.**
- A third party can prefund a launch's PDAs, so creation takes the heavier
  transfer + allocate + assign path.
- Combined with maximum metadata and an atomic first buy, that used almost the
  whole heap.
- Adding `door_nonce` and `program` to the door-mint metadata (task 1.1) pushed
  the existing prefunding test over: `memory allocation failed, out of memory`.

**Measured** with `program/scripts/heap_probe.py`. The probe appends an
allocation in a throwaway worktree and binary-searches it, in 16-byte steps:

| commit | free heap at end, `create_room` | free heap at end, `open_door` |
|---|---|---|
| `e9bd2aa` (before; `verification/heap_headroom.e9bd2aa.json`) | ≥ 800 bytes | ≥ 10,256 bytes |
| `1558b2e` (after; `verification/heap_headroom.json`) | ≥ 688 bytes | ≥ 9,568 bytes |

On `1558b2e`, a `create_room` **takeover** at the largest size the matcher signs
(name 32, symbol 10, URI 70), prefunded with a first buy, ends with **≥ 496
bytes**, about 1.5% of the heap. That is the thinnest margin on any path reachable
today.

**Exploitable today?** On `e9bd2aa`, no. The worst case passed with 800 bytes to
spare (`prefunded_maximum_metadata_launches_fit_the_heap` passes there). With the
new metadata and no fix, yes: prefunding a maximum-metadata launch with a first
buy made it fail. Every later addition to a launch would have hit this.

**Fix.** `mint_check` now reads the two fixed-offset fields it needs from the raw
TLV bytes and allocates nothing. That recovered roughly what the new metadata
costs, and **no more.** The margin is about what it was before, and it remains the
binding constraint on every future addition to a launch.

**Why so little was recovered.** Each CPI allocates its `Instruction` twice:
`solana-cpi` 3.1.0 clones it into a `StableInstruction`. A prefunded launch makes
about 40 CPIs, and nothing is ever freed.

**The remedies are design changes,** left to the owner and audit:
- a custom upward-growing allocator plus `request_heap_frame` in launch
  transactions;
- or allocation-free CPI wrappers;
- or fewer CPIs on the creation path.

See also M-7.

**Regression.** `prefunded_maximum_metadata_launches_fit_the_heap` and
`prefunded_maximum_metadata_takeovers_fit_the_heap`. Both also assert the launch
stays under the matcher's 400,000 CU limit:

| case | `create_room` | `open_door` |
|---|---|---|
| prefunded | 322,161 CU | 218,275 CU |
| takeover | 326,893 CU | 268,677 CU |

### M-2 — In-flight check and reservation not atomic (fixed)

**Attack.**
1. `/route` runs on a thread pool. `conflict()` ran before signing, and
   `reserve_names()` only after the decision was stored.
2. Two same-name new-room requests arriving together both passed the check.
3. Both were signed "new room", with different symbols and so different
   SlugLocks. Both could land.
4. The result is two live rooms with one name: the T2n rule bypassed, which is
   what the reservation exists to stop.

**Affected code:** `services/matcher/matcher_service/service.py`, `inflight.py`.

**Exploitable today?** Yes, with two concurrent requests.
`test_concurrent_new_room_requests_cannot_both_pass_the_in_flight_check` holds one
request between check and signature and fails on the previous code.

**Fix.**
- `InFlight.claim` checks and reserves in one locked step, before signing.
- A claim that does not become a released decision (refusal, signer or store
  failure) is released. Test:
  `test_a_refused_new_room_decision_releases_its_in_flight_claim`.

**Not fixed: replicas.** Running more than one service replica still needs this
state shared (README, known).

### M-3 — Per-launcher rate limit is unauthenticated (open)

**Attack.**
- **Evasion.** The per-launcher limit (6 a minute) keys on the request's
  `launcher` field, which nothing authenticates. Any request can name any key,
  so the limit is evaded by naming a fresh pubkey each time.
- **Targeted DoS.** It can also be aimed. Six requests a minute naming a victim's
  wallet keep that wallet rate-limited, and the victim cannot launch through this
  service.

**Affected code:** `app.py`.

**Fix (owner decision; API change):** launcher-signed requests, as in H-1. Until
then, the per-launcher limit is a courtesy, not a control.

### M-4 — Door first buys default to no slippage limit (open)

**What happens.** `min_tokens_out` defaults to 0 in `/route`.
- **`create_room`:** the room does not exist before the transaction, so its first
  buy cannot be front-run.
- **`open_door`:** the room already trades, so a first buy with min 0 can be
  sandwiched for its whole size.

The program enforces whatever minimum is signed. The default is a service choice.

**Fix (owner decision; API change):** require `min_tokens_out` whenever
`first_buy_lamports > 0` on a door decision. Or have the service compute it from
the snapshot quote and a stated maximum slippage, and refuse when absent.

### M-5 — Pause stops sells (open: spec and audit decision)

**What happens.**
- `trade()` rejects every buy **and sell** while `Config.paused`.
- So do `convert`, `retire_pending` and both launch paths.
- Claims, `set_fee_recipient` and `release_slug` still work.

The 2 November remediation kept pause as a privileged control
(`AUDIT_FIXES.md`). For holders the effect is plain: **while paused, no one can
redeem door or room tokens for SOL.**

**Fix options (owner):**
- let sells and door sells run while paused;
- or bound the pause (an expiry slot in Config);
- or put pause behind the same multisig or timelock as upgrades.

Disclose it either way (§2, Config admin).

### M-6 — Global liveness thresholds can strip a room's identity (open: spec)

**What happens.** The liveness thresholds live in Config and are read at execution
by:
- `open_door` (is the room live?);
- `create_room` takeover (is the old holder dead?);
- `release_slug`.

The spec intends this: "Gate thresholds are shared by routing, takeover and
release" (§3, Config). It means the admin can:
- set `live_min_reserve_lamports` above every reserve, which makes every mature
  room dead at once;
- then let anyone release its SlugLock, or take over its exact identity with a
  new room.

The old room keeps trading, but its name now belongs to someone else.

**Fix options (owner):** snapshot thresholds per room like the curve parameters; or
timelock threshold changes; or disclose it as an admin power (§2).

### M-7 — Prefunded maximum-metadata takeover exhausts the heap (open, pre-existing)

**Attack.**
1. A launch takes over a dead room's identity: `create_room` with `old_holder`.
   It deserialises a second `Room`, about 1.5 KB on the heap.
2. Add maximum metadata (name 32, symbol 10, URI 200) and a first buy.
3. Prefund the launch's new PDAs. Anyone can, by front-running the launch with
   plain System transfers.
4. The launch fails: `memory allocation failed, out of memory`.

**Affected code:** `create_room` (`lib.rs`) plus the allocation pattern in M-1.

**Exploitable today?**
- **Through the matcher service, no.** It signs only legacy transactions, and
  their 1,232-byte limit caps a takeover `create_room` at a 70-byte URI with a
  32-byte name and 10-byte symbol. Computed with the service's own builder; at
  that size the prefunded takeover passes
  (`prefunded_maximum_metadata_takeovers_fit_the_heap`).
- **On-chain, yes.** The program accepts the maximum size in a v0 transaction,
  so:
  - a compromised matcher key can reach it;
  - a future v0-capable service can reach it (README "What remains").
- **Since when:** it also fails on `e9bd2aa`, so it predates this review.

**Reproduction:** `prefunded_v0_maximum_takeover_exhausts_the_heap`, marked
`#[ignore]` with this finding's ID. Run it with
`cargo test --test svm -- --ignored`.

**Fix (open):** one of the M-1 remedies.

**Until then:**
- the matcher service must not sign v0 launches (recorded in its README);
- the program could reject takeover metadata above the legacy-reachable size. That
  narrows a spec limit, so it is the owner's call.

### L-1 — X-Forwarded-For leftmost entry trusted (fixed)

**What happened.** With `MATCHER_TRUST_X_FORWARDED_FOR=1`, the client IP was the
first X-Forwarded-For entry. Proxies append to the header, so the first entry is
whatever the client sent. Any client could choose its own IP rate-limit key.

**Fix.** The key is now the entry `MATCHER_TRUSTED_PROXY_HOPS` from the right
(default 1; 2 behind a GCP HTTPS load balancer). Test:
`test_spoofed_forwarded_for_entries_do_not_evade_the_ip_limit`.

**Exploitable today?** Only with the option on (default off).

### L-2 — Unbounded body, unvalidated limiter key (fixed)

**What happened.** `/route` read the whole body. It then used
`str(req["launcher"])`, unvalidated, as a dictionary key: 30 requests a minute per
IP, each with a multi-megabyte `launcher`, grew memory without bound.

**Fix.**
- Bodies over 8 KiB are refused with 413, from either `Content-Length` or the
  streamed size.
- `launcher` is parsed as a pubkey before it is used as a key.

Test: `test_oversized_body_and_launcher_are_refused_before_use`.

### L-3 — Lone surrogates caused a 500 (fixed)

**What happened.** JSON admits `"\ud800"`, which has no UTF-8 encoding.
`validate_metadata` raised `UnicodeEncodeError`, a 500 with a traceback, not a
structured refusal.

**Fix.** Refused as `invalid_metadata`. Tests:
`test_lone_surrogate_metadata_is_refused_not_a_server_error` and its HTTP
counterpart.

### L-4 — E2E "same ELF" CU baseline was a different ELF (fixed)

**What happened.** `devnet/e2e.sh` compared live CU against
`verification/devnet/deployed_elf_vm/`, the VM report of the old deploy candidate
(ELF `f2cfdb85…`), after the pin had moved to the tip.

**Fix.** The script now uses `verification/svm_report.json`, and exits unless
`verification/build.json`'s ELF hash equals the pin.

The error was introduced in the previous task's repin. It made a CU comparison
wrong; it affected no on-chain behaviour.

### L-5 — Spec table generator wrote stale door seeds (fixed)

**What happened.** `research/doors_into_one_room/scripts/refresh_spec_tables.py`
still wrote `["door", room, index u32 LE]`. Re-running it would have reverted the
spec's door-seed row.

**Fix.** Corrected, and the per-door metadata sizes now come from one place
(`account_sizes.py`).

### I-1 — `claim` debited before its last CPI (fixed as hardening)

**What happened.** `claim` moved SOL with a direct lamport edit (FeeVault →
recipient), then made the WSOL `transfer_checked` CPI. This was balanced, because
neither edited account is in that CPI, but it was the same ordering that broke
`8ce373f`.

**Today.** No v1 path increments a WSOL counter, so that CPI never runs in v1.

**Fix.** The debit now follows the CPI. Every direct lamport edit in the program
now comes after its instruction's last CPI (§3, lamport edits).

### I-2 — The door rebate cheapens sandwiches (open: design)

**What happens.** Every door's trades move one shared price. A searcher can
sandwich any trade in a room through its own door. The door share (60% of the 1%
fee by default) then returns to the searcher, so each leg costs 0.4%, not 1%.

**What bounds it.** The victim's signed `min_tokens_out` / `min_lamports_out` is
enforced on every path (`execute_trade`; capped buys included), and bounds the
victim's loss to their own slippage tolerance. The rebate lowers the size of
trade worth attacking.

### I-3 — Keeping a dead room live (known)

**Cost.** `outputs/narrative/gate_costs.md`: a mature room stays live with:
- 0.5 SOL reserve, held as capital;
- one trade every 6 h;
- 5 SOL gross volume a day.

Wash-traded through one's own door, that loses 0.020 SOL a day in fees.

**Effect.** A live room can keep capturing doors for its identity and name. This
is the calibrated gate; it is not a new defect.

### I-4 — ASCII-oriented on-chain identity floor (known)

`Launch::identity` folds ASCII (case, `rn`→`m`, digit look-alikes) and keeps
non-ASCII bytes. `PEPE` and `PEPE` plus a zero-width space are therefore different
SlugLocks on-chain. Only the matcher's NFKC and invisible-character normalisation
routes them together (`services/matcher/CORRECTIONS.md` §6).

A compromised matcher key can create such look-alike rooms; the program cannot
tell them apart.

### I-5 — Door decisions reserve nothing (open: note)

**What happens.** Only new-room decisions hold the name. Could an attacker, while
a door decision for identity I into room R is in flight, get a new room for I
first and make the door open fail?

**Why it does not work.** The attacker's request has the same identity, so the
same rules over the same state route it to R as well, not to a new room. This is
safe only because routing is a deterministic function of state. A future
non-deterministic rule (randomised tie-break, A/B routing) would open it.

### I-6 — SOL claims need a WSOL account (open: usability)

`claim` validates the recipient's classic WSOL ATA even when `wsol == 0`. A door
creator or founder must create one (2,039,280 lamports of rent at 5,080/byte)
before claiming SOL. It is not a loss, but it is surprising.

### I-7 — Fees near the cap can block buys (known: designed cap)

**What happens.**
- A buy settles pending fees first. If the settlement alone reaches the trigger,
  the room enters status 1 and the buy is rejected.
- Buys resume only after sells take the reserve down by more than the pending
  backlog.
- Sells and conversions keep working throughout.

This is the reversible completion cap (`AUDIT_FIXES.md`), not a brick. It becomes
a real handoff only when graduation exists.

### I-8 — Rotation instruction described but absent (doc correction)

`NARRATIVE_DETECTION.md` §§ on the compromised matcher describe
`set_matcher_authority(new)`. **No such instruction exists:** rotation is
`update_config` with the whole `Settings`. Procedure: `DEPLOYMENT.md` §9. Recorded
in `CORRECTIONS.md`.

### I-9 — Decision log can be rewritten by its operator (known)

**What protects it.** The SQLite store is append-only by trigger and hash-chained.
Appends hold a process lock and `BEGIN IMMEDIATE`, so two writers cannot fork the
chain.

**What does not.** Anyone with the file can drop the triggers and rewrite it.
Outsiders can detect that only once the chain head is published (README, "What
remains").

### I-10 — One write lock per room (known)

**What happens.** Every trade, convert, retire and launch in a room writes the
Room, ReserveVault, FeeVault and RoomVault. All of a room's doors therefore
serialise on one account.

**Ceilings.** By measured maximum CU and the 24,000,000 CU writable-account cap,
the ceilings per room per block are:

| route | max CU | ceiling |
|---|---|---|
| buy_door | 69,450 | 345 |
| sell_door | 57,430 | 417 |
| buy_room | 53,561 | 448 |
| sell_room | 42,041 | 570 |
| convert | 68,846 | 348 |
| open_door | 149,950 | 160 |

Source: `verification/cu.md`. These are not worst cases.

**What it allows.** A spammer can raise the local fee market on one room by
write-locking it. They pay every signature and priority fee themselves. It does
not stall anyone permanently.

---

## 2. Who can do what: threat actors

For the owner, and for public disclosure. Each part says the most that actor can
do, and what stops them.

### An ordinary trader trying to extract value from the curve

**At most:** nothing beyond fair trading.
- **Fixed price formula.** Every buy and sell uses one formula, and selling in
  pieces pays exactly what selling at once pays. Rounding always leaves the
  remainder in the pool.
- **Reserve only pays sellers.** It pays out on a sell exactly the curve value
  of the tokens sold, and nothing else.
- **Settled fees cannot be gamed.** Fees waiting to be added to the pool are
  settled before anyone buys. A trader cannot buy cheaply just before they
  settle and sell just after. The SBF sweep measured the attacker losing money
  (`verification/sweep_retirement_mev.json`).
- **Donations are inert.** Sending SOL or tokens to the program's accounts
  changes no price and no payout; the donation is simply locked.

### A door creator trying to take other doors' or the protocol's fees

**At most:** collect fees on trades routed through their own door. They may
route their own trades through it to earn the 60% door share back.
- **Collection is restricted.** Only a door's fee recipient can collect that
  door's fees, and only the recipient can change who that is.
- **Other shares are fixed.** The founder share goes to the room's founder,
  fixed at creation. The protocol share goes only to the configured protocol
  address.
- **Clones are allowed.** A creator can open look-alike doors to compete for
  routing. Wallets and frontends must label doors (spec §7).

### A competitor trying to make rooms unusable rather than profit

**At most, today:**
- **Block names through the matcher, for free (H-1).** This is the cheapest
  attack in the system, and it is open.
- **Rate-limit a specific wallet (M-3).**
- **Flood a popular room with clone doors.** Each costs about 0.0097 SOL of
  permanent rent.
- **Spam a room's write lock.** They pay every fee. It raises costs for
  everyone in that room while it lasts.

**Cannot:**
- freeze a room, drain it, or put it in a state that permanently breaks trading;
- stop holders selling (only the admin's pause can, M-5);
- break launches signed by the current service by prefunding their accounts.
  The margin is thin (M-1) but tested at every size the service signs.

**Can, but not through today's service:** make a maximum-metadata takeover launch
fail by prefunding its accounts. That size needs a v0 transaction (M-7, open).

### An MEV searcher

**What they get.**
- **Every trade is reachable.** A room's doors all trade one price and all
  write-lock the same room account. A searcher watching one room sees, and can
  sandwich, every trade in it.
- **Attacks are cheaper (I-2).** Routing through their own door returns 60% of
  their fees.

**What stops them.**
- **Slippage limits hold.** The minimum each trader signs (`min_tokens_out`,
  `min_lamports_out`) is enforced on every buy and sell, including capped buys
  and launch first buys.
- **Bounded loss.** A trader's worst case is their own slippage setting, plus
  the fee.

**The weak spot** is a launch's first buy into an existing room, where the
service defaults the minimum to zero (M-4).

### A compromised matcher key

The matcher co-signs every launch.

**With the key, an attacker can:**
- create new rooms for any name the program's exact-identity lock does not
  already hold for a live room, bypassing every text rule (the name-only rule,
  normalisation);
- open doors with any metadata into any live room;
- write junk into the advisory `rule` / `face` fields.

**Every launch still needs a fee-paying launcher's signature,** so the attacker
spends their own SOL on rent.

**The program still prevents:**
- taking an identity held by a live room;
- touching any reserve, fee balance or backing;
- opening doors into dead rooms;
- charging more than the signed flat-fee cap;
- using a signed launch more than 150 slots after signing, even through a
  durable nonce;
- running a launch from inside another program.

**Rotation (`DEPLOYMENT.md` §9)** makes every launch signed by the old key fail
from the slot the Config update lands, including launches signed but not yet
landed.

**It does not undo** rooms and doors already created. Doors are permanent, and a
squatted identity stays locked while its room is live.

### The Config admin

The admin key is, on devnet, also the upgrade authority. Over **existing** rooms
it can:

| power | effect on existing holders |
|---|---|
| **pause** | **stops all buys and sells, conversions, fee settlement and launches, in every room, for as long as it likes. Holders cannot exit while paused (M-5).** Claims still work. |
| change liveness thresholds | decides which rooms accept new doors, and can make any room "dead" at once, so its name can be released or taken over (M-6) |
| change `protocol_fee_recipient` | redirects all future and **already accrued, unswept** protocol fees in every room |
| change `convert_fee_lamports` | applies to conversions in existing rooms, up to each user's signed cap |
| change `door_fee_lamports` | applies to new doors in existing rooms, up to each launch's signed cap |
| change `matcher_authority` | decides who routes launches |
| hand admin to another key | all of the above passes to that key |

**It cannot:**
- change an existing room's curve, trading fee, door share or founder share
  (copied into each room at creation);
- move reserves, backing or door and founder fees;
- mint or freeze any token (those authorities are revoked).

**Plainly, for users:** an admin can halt trading indefinitely and can strip a
room of its name. Nothing else the admin can do takes holders' money directly.

### A compromised upgrade authority

**Everything.** The upgrade authority can replace the program. A replaced
program can sign as every vault, so it can:
- send every room's SOL reserve and fee balances anywhere;
- move every locked room token out of the door backings.

Door and room tokens would then be claims on nothing. The token authorities
are revoked, so it cannot mint or rename tokens, but that protects nothing once
the reserves are gone.

**This is why the mainnet upgrade-authority decision (`DEPLOYMENT.md` §8)
matters more than any finding above.** The options:
- **Single hot key:** one theft takes everything.
- **Multisig:** needs several keys.
- **Timelock:** gives holders time to exit, provided pause cannot be used during
  that window to stop them (M-5).
- **Immutable:** removes the risk and the ability to fix bugs or add graduation.

---

## 3. Checked and found clean

What the audit can treat as covered by this review, and how. "Clean" means no
defect found. Program code: `program/programs/doors_v1/src/`.

### Solana vulnerability classes

| class | verdict and basis |
|---|---|
| missing signer checks | **Clean.** `initialize_config` admin must be the program's upgrade authority (ProgramData checked). `update_config` `has_one=admin`. `create_room` / `open_door` need user and `matcher == Config.matcher_authority` as signers. Trades and converts need the user (token CPI enforces ownership). Door and founder claims need `authority == recipient`. `set_fee_recipient` needs the current recipient. Permissionless by design: `retire_pending`; protocol sweep (pays only the configured recipient); `release_slug` (dead rooms only). |
| missing ownership checks | **Clean.** Program state via `Account<T>` (owner + discriminator). Vaults: `owner=crate::ID` plus seeds (reserve, fees), or fixed address plus `token()` owner, mint and authority checks. Mints: `mint_check` (Token-2022 owner, no authorities, exactly 2 extensions). SlugLock: owner checked in `read_slug`. `old_holder`: `Account<Room>` plus `room_address`. |
| account substitution | **Clean.** A door is accepted only if `door.room == room` and the account is the PDA of `door.nonce` (`door_check`). Its mint, vault and backing must equal the Door's stored keys. Room vaults are fixed by address. User token accounts must be the canonical ATA of the signer for the selected mint. Recipients are fixed. Tested by `substituted_trade_accounts_and_same_door_conversion_are_rejected_atomically` and the sweeps. |
| type confusion | **Clean.** Every typed account is an Anchor `Account<T>` with an 8-byte discriminator. Unchecked accounts are either fixed addresses or parsed as SPL token / mint state after an owner check. |
| PDA seed collisions | **Clean.** Seeds are concatenated without separators, so collisions were checked by total byte length. Each same-length pair has distinct literal prefixes of equal length: `reserve`/`retired` (39), `fees`/`slug` (36), `grad_payer`/`door_vault`/`room_vault` (42). Attacker influence: `room_id` and `door_nonce` are matcher-signed; `identity` is a SHA-256 output whose preimage separator (0x00) cannot occur in `fold` output. Door seeds include the room key, so no cross-room collision exists. |
| arbitrary CPI | **Clean.** Every CPI target is a fixed address: Token-2022, SPL Token, the ATA program (`address=… , executable`), System (`Program<System>`). Mints have no transfer hook (two-extension check), so no CPI reaches attacker code. |
| duplicate mutable accounts | **Clean.** `debit` rejects `from == to`; `convert` rejects `door_a == door_b`. User ATAs cannot alias program PDAs (different derivations). A fee recipient set to a program PDA can only make its own fees unclaimable (a PDA cannot sign). `Retire` passes RetiredVault twice by design, as one account. |
| integer overflow / underflow | **Clean.** `overflow-checks = true` in the release profile used for SBF. Host tests use the dev profile (checks on). Arithmetic on balances and counters is `checked_*` or `add`/`sub`. The unchecked expressions were each verified bounded: `bl - reserve.lamports()` after an exact debit; `(now - created_at)` behind `created_at > now`; `uri.len() as u8` after `≤ 200`. |
| rounding direction | **Clean.** `reserve(q)` floors. `inverse` returns the largest `q` with `floor R(q) ≤ r`. A buy credits its whole net input while advancing `sold` only to that `q`, so the surplus stays in the pool. Sell proceeds `floor R(s) − floor R(s−t)` telescope, so splitting sells gains nothing. The buy fee is `gross − floor(net)` (rounds up); a capped buy's fee rounds up, and the total never exceeds the input (checked algebraically). The sell fee rounds up. Door and founder shares floor, with the remainder to protocol. Settlement retires `inverse`-floored tokens, so the surplus stays in the pool. |
| reinitialisation / revival | **Clean.** Anchor `init` and `create_pda` both require a System-owned, empty account. The only close is `release_slug` (Anchor `close`: zeroes data, reassigns to System). A released lock reads as absent. A rewritten lock on takeover is serialised with its discriminator. |
| sysvar substitution | **Clean.** Clock and Rent come from syscalls (`Clock::get`, `Rent::get`). Stack height comes from a syscall. No sysvar account is taken. |
| lamport edits vs CPI boundaries | **Clean after I-1.** The five direct lamport edits are: buy settlement (`trading.rs`), the two sell debits, `retire_pending` and `claim`. Each now comes after its instruction's last CPI, and no caller makes a CPI after `execute_trade` returns (`create_room`, `open_door`, `trade`). Anchor `close` edits after the handler. |

### Protocol invariants: attacks tried

| attack | tried | result |
|---|---|---|
| drain the reserve | every path writing ReserveVault | Only `sell` debits it: `g − f` to the seller and `f` to FeeVault, total exactly `R(q) − R(q−t)`. Asserted per instruction (`bl − lamports == g`, `reserve_delta`). Buys, settlement and launches only credit it. |
| break 1:1 backing | every door-token movement | Door tokens leave a DoorVault only on a door buy (room tokens of the same amount into backing first) or a convert into that door (backing moved in first). Backing leaves only on a door sell (door tokens returned first) or a convert out (door tokens returned first). `transfer` asserts exact deltas; `door_check` asserts vault `≥ U − backing` and backing `≥ backing` before and after. No mint authority exists. |
| steal fees | claim, set recipient, accrual redirection | See §2. Accrual goes to the routed door, or to pending (holders) on room routes. Founder and protocol shares are fixed per room or Config. Tested by `independent_holders_share_backing_without_access_to_each_others_fees`. |
| donation attacks | every read of a lamport or token balance | **None prices, pays or decides.** Balances appear only in exact-delta assertions and `≥` coverage checks. The single balance-dependent branch is `create_pda` (`lamports == 0` picks the creation path). It changes only resource use (M-1), and is tested with every launch account prefunded. Liveness, quotes, payouts and claims read counters only. Donations of SOL, room tokens, door tokens and WSOL are tested locked (`direct_donations_and_holder_burns_preserve_coverage_and_quotes`, `wsol_fee_plumbing_claims_only_accounted_fees_and_leaves_donations_locked`). |
| abuse `retire_pending` | order, frequency, at the cap, while paused | Buys settle first, so a backlog cannot be captured (sweep: attacker loses). Repeated tiny retirements each leave under 1 lamport of surplus in the pool, against a 5,000-lamport fee each. Blocked at status 1 and while paused. It harms no one. |
| abuse `convert` | value, price, counters | Price, `sold` and reserve are unchanged (asserted). The amount is bounded by source backing and destination vault. It generates no fee rebate and no liveness volume. Self-conversion is rejected. |
| brick a room | coverage checks, counters, status, token-account state | Every check compares counters the program alone moves against balances only the program can lower: vault authorities are program PDAs, there is no freeze authority, and no close authority. Counters are `u64`/`u128` with checked math. Status 1 reverses on a sell; status 2 is unreachable in v1. User-side Token-2022 extensions (memo-required, CPI guard) can block only that user's own trades. |
| game the liveness gate | wash trading, timestamps, buckets | Cost is I-3. Volume counts net curve lamports, excluding fees (`buy_fees_do_not_make_a_below_threshold_room_live`). The bucket window is fixed. Future-dated buckets and timestamps are excluded. Making a live room look dead needs the attacker's own reserve share, or the admin (M-6). |
| front-run room creation | slug, `room_id`, signed transaction | `room_id` and the whole transaction are matcher-signed. A rival needs its own matcher decision, and the service refuses a concurrent same-name new room (M-2 fixed). Whoever lands first owns the room, and the loser is routed in as a door: this is the design. |
| grief door opening | nonce, prefunding, room death, slug | Nonces are signed and random. Prefunding is tested (M-1). An identity locked by a live room makes the open fail, but the same request then routes to that room (I-5). |
| launch-data tampering | each `Launch` field | Name, symbol and URI lengths are validated (UTF-8 via Borsh). `max_fee_lamports`, `expected_terms_hash` (`create_room`), `door_nonce` (0 iff `create_room`) and `expires_at_slot` (≤ 150 ahead) are enforced. `first_buy_lamports` and `min_tokens_out` are enforced as signed. **Not verified, by design:** `rule`, `face` and `matcher_version` are attestations recorded for audit. Text rules (T2n and normalisation) are off-chain, so this is matcher trust (§2). |

### Matcher service and the seam

| item | verdict |
|---|---|
| `/route` input validation | Types, integer ranges and UTF-8 byte limits equal `Launch::validate`. Body cap and surrogates are now fixed (L-2, L-3). Oversize transactions are refused before signing. |
| routing influence by crafted input | **By design, yes.** Matching a live room's name routes into it. Look-alikes the rules miss get their own room, at the measured recall. Among several matching rooms, the tie-break prefers the highest reserve, so a room's holders can buy their way to winning ties (capital at risk, fees paid). |
| rate-limit evasion | Per IP: now proxy-correct (L-1). Per launcher: not a control (M-3). |
| decision store rewrite / fork | No fork (process lock plus `BEGIN IMMEDIATE`). Rewrite is possible for the operator until the head is published (I-9). |
| concurrent identical launches, duplicates, retries | New-room: the second request is refused (M-2 fixed). Door: each request gets its own random nonce; both can land if the launcher signs both, each paying its own rent. Retries after a timeout see `409` until the first decision expires (about 60–90 s); there is no idempotency key. |
| service assumes, program does not enforce | Text rules (T2n, normalisation, tie-break); single-replica in-flight state; the decision log. |
| program enforces, service relies on | Exact-identity floor, room liveness at execution, launch expiry, door nonce rules, signed fee cap, terms hash. A stale snapshot can only make a launch fail on-chain, never route it wrongly past these checks. |
| expiry seam | `expires_at_slot = blockhash slot + 150`. Slots advance at least as fast as block height, so the program's expiry never outlives the blockhash. Durable nonces are caught by the program (localnet e2e step 6c). |
| CU seam | Worst tested launch 326,893 CU (prefunded takeover `create_room`), under the service's 400,000 limit (asserted in SBF). The VM is not an upper bound for the live runtime: on the Agave 4.4.0 local validator, `convert` and `claim_door_fees` ran 5,773 and 4,500 CU above their VM maxima (`DEPLOYMENT.md` §7). |
| key seam | The service refuses to sign unless its key equals `Config.matcher_authority` in the snapshot. A KMS signature is verified before use. |

### Supply chain

`program/scripts/audit_dependencies.py --bulk --check` scanned 427 exact crate
versions across both lockfiles:
- **Vulnerabilities:** none.
- **Maintenance notices:** the same five as 2 November, all on the reviewed
  list.

**Source:** the OSV bulk export, GCS generation `1793774894013088`, Last-Modified
4 Nov 2026 06:48 GMT, SHA-256 `dea150c5…`. Details are in
`verification/dependency_audit.json`.

**Checks on the method:**
- it reproduced the 2 November API scan exactly;
- it flags `ctutils 0.4.3` and `crypto-bigint 0.7.5`, the vulnerable versions
  removed then.

**Why not the API:** `api.osv.dev` was unreachable from this environment.

---

## 4. Not checked, and why

- **Token-2022, SPL Token, ATA and System program internals.** Assumed correct
  at the versions LiteSVM bundles (hashes in `verification/build.json`).
- **Anchor 1.2.2 generated validation code.** The constraints were read as
  written, not the macro expansion.
- **Real clusters.** Nothing is deployed, so no devnet or mainnet behaviour has
  been observed:
  - scheduling, write-lock contention and priority-fee dynamics are unmeasured;
  - CU figures are LiteSVM measurements.
- **Heap headroom on the live runtime and on future runtimes.** Measured on the
  bundled Agave 4.3.2 VM only. An Agave change to CPI or account serialisation
  could move it; the local 4.4.0 validator already differs in CU (§3, CU seam).
- **The worst case was not exhaustively searched.** The heap and CU worst cases
  are combinations chosen by reasoning: prefunding, maximum metadata, takeover,
  first buy, settlement. A combination not thought of could be heavier.
- **Exhaustive or formal verification.** Testing is the SBF suite plus a
  10,000-step randomised property run. There is no fuzzing beyond that, and no
  formal model of the curve arithmetic beyond boundary vectors.
- **Real KMS.** Both signers are tested against fakes only.
- **The frontend and indexers,** which must label door 0 against the room token
  and clone doors (spec §7). They are not in these branches.
- **Phase 2 (graduation).** It does not exist; status 2 fails closed. A future
  adapter must be reviewed on its own, including the WSOL fee paths that are
  dormant in v1 (I-1).
- **Dependency source code.** Only advisory databases were consulted.
