# Doors v1: pre-audit security self-review

## Paired-program review continuation, 7 November 2026

Scope starts at program `2bf6f40` and service `9750e03`. This remains the
authors' own review. The current continuation uses offline SBF execution and
public CI evidence. It performs no deployment and reads no production keys.
The older sections below describe earlier program revisions and measurements.

### Launch spot manipulation: fixed with owner approval

The paired door anchors its room-token curve at the room spot at creation.
Consequently a room buy just before a launch can increase the number of door
tokens delivered while reducing their room-token value. The old token minimum
does not protect that value. The `816b38d` witness, preserved as
`review_door_open_front_run.before_owner_rulings.json`, records a
20 SOL front-run yielding 0.217061544 SOL attacker net and reducing the victim's
immediate exit by 0.549648652 SOL, despite its 2% token minimum.

The approved `Launch.max_room_price: u128` appends 16 signed bytes. Units are
lamports per room base unit times 10^18; zero disables the bound. Both launch
paths compare the exact pre-buy spot with it, before pending settlement and
door initialization. Fraction comparison uses Euclid's algorithm, avoiding
overflowing cross products. The service fills an omitted bound from the user's
slippage choice and quotes the two legs in door tokens. An explicit token
minimum leaves the room-price bound enabled. The independent verifier ports
both legs separately and reconstructs pending fees and sold amounts from events.

The runtime regression checks all three original front-run sizes: 5, 20 and
60 SOL. Each is refused at 2%; each is accepted at zero. Unmoved prices still
fill, and creation checks the same bound. A temporary CI negative control
disables only the two price checks and requires this regression to fail, then
restores the protected program before running the full suite. No deliberately
failing test is committed.

The blocking service quote previously returned room units: the reference
1.01 SOL first buy in the 10.1 SOL seeded room now matches SBF exactly at
33,699,309,828,108 door base units. Active IDL and layout pins are explicitly
named `paired`, preserving the historical deployed pins. Room/Door lengths are
735 at birth / 1,335 after the first buy, and 360 bytes respectively. The program ID comes from the active IDL. Door sweeps select
`sell_door`; Trade and swap events use the paired layouts. Name keys and
matching rules are unchanged. Legacy maximum-metadata creation now fits only
a 35-byte URI, or 3 bytes for a one-holder takeover, with a priority fee.
Oversized transactions are refused; v0 transactions remain an owner choice.

### Name-lock race and resource availability

The same-slot test uses equal name keys with different symbols and thus distinct
SlugLocks. Both decisions describe the earlier snapshot without a former name
holder. One create succeeds; the second fails atomically, leaves no room and
does not move the lock. No program change is needed for this existing guarantee.

The resource fixture exercises 33 permanent doors per room, maximum metadata,
1 and 80 SOL starting depth, pending retirement, a fresh or prefunded fee vault,
and an existing vault. Every held door is sold in full and every door/protocol
swap credit is claimed. It includes compute-limit, priority-fee and heap-frame
instructions when counting the 64-entry trace. `heap_probe.py` now also measures
both fee claims and the prefunded first swap, and requires nonzero headroom for
every measured instruction. Measurements and final run references follow below.

### Liveness: measured behaviour, thresholds remain an owner decision

An ordinary operator who owns its door and fee recipient can recover the 60%
door share of wash fees. Default ongoing volume is 5 SOL per rolling day; the
1% fee therefore leaves approximately 0.02 SOL/day to the protocol. Four trades
spaced six hours apart meet the idle gate. A day-end claim can share a sell
transaction. The SBF fixture bootstraps the initial volume window, retains the
0.5 SOL reserve floor, and measures two further days without changing a gate.
Setup rent, bootstrap fees and recoverable trading capital are separate from
ongoing cost. This replaces the old 0.05 SOL/day estimate, which omitted the
operator's own door-fee rebate. Final exact measured amounts follow below.

This is paid name squatting and routing influence, not a direct protocol fund
withdrawal. Raising volume/reserve thresholds, changing the idle window, adding
a minimum unrecoverable upkeep charge, or accepting current economics are owner
options. Recommendation: document the measured price first and decide acceptable
name-lock carrying cost explicitly. No threshold or fee rule is changed here.

### Revived former NameLock holder: Fixed (owner ruling A)

Control service `f2f8451` let a deeper revived former room regain text flow while
the live successor held the NameLock. The service now routes text only to the
current live name holder, regardless of another room's depth or tier. A live
SlugLock is an on-chain restriction, not permission to bypass that holder:
conflicting live identity/name locks refuse the launch. Without a name key the
identity floor remains. Ordinary service regressions failed before this fix.

The SBF revival probe now revives the former holder through ordinary trading,
keeps its exit open, sends the next eligible door into the successor, and checks
that the former room receives no new door. This implements the ruling; it is no
longer an open policy choice. The service's independent verifier agrees.

### Admin-selectable 120 SOL stress cap: Fixed (owner ruling B)

Control program `816b38d` accepted a normal admin's 120 SOL setting. Production
Config validation now refuses triggers above 85,018,013,680 lamports. Only the
`test-stress` cargo feature removes that ceiling. Existing room caps remain
immutable. The permanent `adversarial_normal_admin_can_select_the_stress_cap`
test asserts default refusal and feature-build acceptance, each against its own
SBF binary. CI also runs the supply-exhaustion case in the isolated feature build,
without overwriting the production ELF. No intentionally failing test is committed.

The owner authorized independent historical B/D controls against `816b38d` on
the reviewer's Linux runner; those historical controls were not executed locally. That commit accepted 120 SOL and allocated the old
birth accounts and fixed volume array. Candidate tests all assert their own
build's correct behavior; no historical failure harness is on this branch.

### Room birth rent: reduced (owner ruling D)

Birth rent is 17,515,840 lamports, down from 26,959,560 at `816b38d`: 9,443,720
lamports saved (35.0%). For a zero-first-buy launch under the default Config,
no reserve, native fee, graduation payer,
retirement, WSOL fee or door-backing vault is created. Each is created only when
needed; graduation remains unimplemented. Liveness uses exact sparse u128 hourly
buckets with the same 25-slot ring and 24-hour checks. Birth Room is 735 bytes;
the first buy funds all 1,335 bytes of capacity, so sells never require storage
rent. This changes the Room wire layout; the measurements use freshly created
paired rooms, with no migration of existing 1,331-byte accounts performed. A 1,000-record differential test includes backward clocks and u64-maximum
volumes and compares exact values and live decisions with the old ring.

The 15,000,000 target is not reached: the gap is 2,515,840 lamports. The remaining
birth accounts are needed for the existing launch: Room, Door, both immutable
metadata mints, both inventory vaults, SlugLock and NameLock. Reaching the target
with these accounts requires further state/metadata compaction or an interface
change; first-use deferral alone cannot remove their rent. Deferred rent moves
to the first user of a vault; it is not eliminated. Final before/after heap and
CU measurements are recorded below after verification.

### RPC failure text: unambiguous service defect fixed

The preserved draft reproduction failed for both HTTP and JSON-RPC failures:
transport exceptions included a synthetic authenticated endpoint URL, and provider
error bodies could echo it. The service returned these strings in public errors
and refresh logs. RpcError now contains method/class/status or a numeric RPC code
only; provider message/data and chained transport text are suppressed. Both
reproductions pass; the final service suite passes 163 tests. Trigger cost is an
unauthenticated request during an RPC failure; potential payoff is access to RPC
quota or billing credentials, not program funds. No real credential was accessed.

### M-3 and evasion coverage

Existing authentication already refuses replayed requests. Added tests alter
every signed field, including the new price field, and check concurrent replay:
exactly one of 32 attempts is accepted. Alteration does not consume the genuine
signature. The HTTP replay and victim-rate-limit regressions remain passing.

The evasion benchmark now composes mixed alphabets inside single words and
across words, and reports a separate class for actual UTF-8 truncation at the
32-byte boundary. It never splits a code point into invalid UTF-8. The unchanged
rules are checked against the independent candidate implementation. These are
recall measurements, not intent labels or matching-precision guarantees.


5 November 2026. Branches `claude/program-v1` (program) and `claude/matcher-service`
(off-chain matcher). Deployed to devnet only (5 November 2026, slot 518,934,300; `DEPLOYMENT.md` §5); nothing on mainnet.

**This is the authors' own review, written for the external audit.** The code
under review was largely written by the reviewer. Read every "clean" verdict as
"checked by the author, no defect found", not as a proof. Uncertain items are
reported as uncertain.

Every number below comes from a re-runnable script or test, named where it is
used. Unless a finding says otherwise, they refer to program ELF `c36ba443…ed29`,
commit `b6fe25d` (`verification/build.json`). This review was first written
against ELF `34d4ce91…` (`1558b2e`/`805bae3`) and updated in the follow-up of
5 November.

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
| H-1 | High | **fixed on-chain** (NameLock, `f87f341`); the service reservation is removed | Free name reservations let anyone block any name. SlugLock does not cover 9 of 16 routed-together pairs, so the reservation was load-bearing; the NameLock covers all 16 |
| H-2 | High | **fixed in the matcher** (`claude/matcher-service`, CORRECTIONS §17) | Face laundering: a floor door with the same program identity but another name key gave a room a second narrative's face; it captured that narrative's launches and beat the genuine room on reserve depth, defeating the NameLock |
| M-1 | Medium | fixed | Launch heap nearly exhausted: the metadata change overflowed it; after the fix, worst-case `create_room` kept 688 bytes, a service-signable takeover 496. At `71d32f3` (stack signer seeds), ≥ 1,520 and ≥ 2,816 |
| M-2 | Medium | fixed | Matcher in-flight check and reservation were not atomic: concurrent requests could both get "new room" |
| M-3 | Medium | fixed | Per-launcher rate limit keyed on an unauthenticated field. Requests are now launcher-signed |
| M-4 | Medium | fixed | Launch first buys defaulted to no slippage limit. The default is now the quote less 2% |
| M-5 | Medium | fixed (spec updated) | Pause stopped sells. Pause now stops only new positions; sells and `convert` stay open |
| M-6 | Medium | fixed (7-day timelock) | Liveness thresholds were global and changeable at once: the admin could make every room dead in one transaction |
| M-7 | Medium | **fixed** (`8f54026`: old holder read in place) | A prefunded maximum-metadata `create_room` takeover exhausted the heap (pre-existing; v0-only size). It now keeps ≥ 1,280 bytes |
| M-8 | Medium | fixed | A prefunded `create_room` with a first buy and a priority fee used 64 of the 64 allowed instruction-trace entries; 48 after the fix, 49 with the NameLock |
| L-1 | Low | fixed | X-Forwarded-For: the client-supplied leftmost entry was the rate-limit key |
| L-2 | Low | fixed | `/route` body size unbounded; any string became a rate-limiter key |
| L-3 | Low | fixed | Lone UTF-16 surrogates in metadata caused a 500, not a refusal |
| L-4 | Low | fixed | The program e2e compared live CU against a different ELF |
| L-5 | Low | fixed | The spec table generator still wrote the old index-based door seeds |
| L-6 | Low | fixed | The decision verifier took a transaction's block time as the program's Clock; on devnet they differ |
| I-1 | Info | fixed | `claim` edited lamports before its last CPI, the class that broke `8ce373f` |
| I-2 | Info | open | The design's door-fee rebate lowers the cost of sandwiching every trade in a room |
| I-3 | Info | known | Keeping a dead room live costs about 0.02 SOL a day |
| I-4 | Info | known | The on-chain identity floor is ASCII-oriented; non-ASCII look-alikes rely on the matcher |
| I-5 | Info | open | No decision reserves anything now; only deterministic routing keeps a door decision safe |
| I-6 | Info | open | Claiming SOL fees requires the recipient to hold a classic WSOL account |
| I-7 | Info | known | Fees accumulated near the cap can block buys until holders sell |
| I-8 | Info | open (partly mitigated) | Name evasion: look-alike letters, case and spacing, typos or an added word take a copy out of its room. With rules A, B, C and I (live since 7 November) the key survives 95.4% of disguised variants (84.0% before I and C); typos (5.6%) and added words (19.9%) still escape |
| I-9 | Info | open | Name squatting: a room created early for a likely narrative stays live for about 0.05 SOL a day of wash-volume fees plus 0.5 SOL of reserve, and every later copy routes into it |
| I-8 | Info | open (doc) | The narrative spec describes a `set_matcher_authority` instruction that does not exist |
| I-9 | Info | known | Decision log: the operator can rewrite it until its head is published |
| I-10 | Info | known | One room, one write lock: every door's trades serialise on the room |

### H-1 — Free name reservations block any name (fixed on-chain)

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

**Exploitable today?** Yes, against any running service. Requests are now signed
(M-3), but keys are free, so the attack costs one generated key per request.

**Is the reservation earning anything? Yes: SlugLock does not cover it.**

*How the slug is derived.*
- `SlugLock = PDA(["slug", identity])`, with
  `identity = sha256(fold(symbol) ‖ 0x00 ‖ fold(name))` (`Launch::identity`,
  `state.rs`).
- `fold` is ASCII-only. It uppercases, maps `0 1 3 4 5 7 8` to `O I E A S T B`,
  reads `rn` as `m` and `vv` as `w`, and drops non-alphanumeric ASCII. It keeps
  every non-ASCII byte.

*What the matcher routes together.*
- **T3:** equal folded symbol **and** folded name.
- **T2n:** equal folded name of at least 4 characters, **any** symbol.
- Its fold is broader than the program's: NFKC, homoglyph tables, stopwords
  (COIN, TOKEN, THE, OFFICIAL, …), camelCase splitting, invisible characters.

`services/matcher/scripts/slug_coverage.py` computes, for each class of
routed-together pair, whether both launches derive the same SlugLock:

| pair class | example | matcher | same SlugLock? |
|---|---|---|---|
| identical | `Pepe`/`PEPE` twice | T3 | yes |
| ASCII case, punctuation, `$` | `Pepe!`/`$PEPE` vs `Pepe`/`PEPE` | T3 | yes |
| ASCII digit look-alike, `rn`→`m`, spacing | `P3P3` vs `Pepe` | T3 | yes |
| stopword | `Pepe Coin` vs `Pepe`, same symbol | T3 | **no** |
| homoglyph (Cyrillic, Greek) | `Реpe` vs `Pepe` | T3 | **no** |
| NFKC full-width | `Ｐｅｐｅ` vs `Pepe` | T3 | **no** |
| zero-width character | `Pe\u200bpe` vs `Pepe` | T3 | **no** |
| **any T2n pair** | `Pepe`/`PEPE` vs `Pepe`/`FROG` | T2n | **no**: the symbol is part of the identity |

**9 of the 16 tested routed-together pairs derive different SlugLocks.** For
those, two concurrent new-room launches both land as live rooms. That is exactly
the duplicate the matcher's routing exists to prevent. SlugLock covers only pairs
whose ASCII folds are byte-identical, so **the reservation is load-bearing and
H-1 needs its own remedy.**

One fact makes an on-chain remedy possible: every routed-together pair shares the
matcher's folded name key `nk`. T3 and T2n both require name equality.

**Remedies, with their API cost (owner decision):**

| remedy | removes the DoS? | closes the duplicate gap? | cost |
|---|---|---|---|
| **A. On-chain NameLock.** `create_room` also takes a matcher-signed `name_key_hash = sha256(nk)` (with the symbol key added below the 4-character T2n minimum). It inits `PDA(["name", name_key_hash])`, with SlugLock's live/dead takeover rules. The second concurrent launch fails on-chain and re-requests as a door. The reservation can then be dropped. | yes | yes, for every routed-together pair | Program, IDL and service change. +1 account and +32 bytes of instruction data per `create_room`, 65 bytes of the legacy packet budget. The largest service-signable URI falls from 102 to 37, and from 70 to 5 for a takeover (computed with the service's own builder, with a cu-price instruction). Rent: one more 17-byte PDA, 736,600 lamports per room. **Trace: one more PDA creation is +1 CPI (+3 when prefunded), and a prefunded `create_room` with a priority fee is already at 64/64 entries, so A requires M-8 fixed first.** Trust: same as today, since the matcher already decides routing. |
| B. Signed requests (done) + one in-flight new-room reservation per launcher + a balance check (launcher holds rent + fees + first buy) at decision time | partly: each held name costs one funded wallet (~0.028 SOL, not spent) | yes (unchanged) | Service only. One `getBalance` RPC per new-room request. A determined squatter still holds N names with N funded wallets. |
| C. No hold: let concurrent same-narrative launches both land | yes | **no**: duplicate rooms under concurrency, i.e. during hype, when copycats launch within seconds | Service only. The tie-break later prefers the higher-reserve room. |

**Owner decision (5 November 2026): B now, and A as a mainnet blocker.**

**B, implemented in the service (`service.py`, `funds.py`).** A new-room decision
holds its name only if both of these hold:
- the launcher holds no other unexpired new-room decision (`409
  launcher_in_flight`, which names the held decision);
- the launcher's confirmed balance covers the launch. That is the rent for every
  account `create_room` makes (sized as the program sizes them, priced by the
  cluster's own rent RPC), plus the flat fees, the first buy and signature fees.
  Otherwise the request is refused with `422 insufficient_funds`.

Tests: `test_one_in_flight_new_room_decision_per_launcher` and
`test_new_room_needs_proof_of_funds`.

**What B leaves.** Holding a name now needs one funded wallet per name, about
0.028 SOL plus any first buy, none of it spent. A squatter with N funded wallets
can still hold N names.

**A (the on-chain NameLock): implemented (`f87f341`), and B removed.** Owner decision: the matcher puts
its folded-name key in the signed payload, and the program uses it as a PDA seed.

- **Key.** 16 bytes: `sha256("doors-v1:name-key:v1" 0 class 0 payload)[:16]`.
  - Class N: the folded name, when it has at least 4 characters.
  - Class P: the folded symbol and name, for shorter names with a symbol.
  - Otherwise none.
  - **Why it is exact.** T3 and T2n both need equal folded names, so two room-creating launches route
    together exactly when their keys are equal. `services/matcher/tests/test_rules.py` checks this
    both ways over every pair of the slug-coverage classes, the research examples and edge cases.
    The verifier derives the key independently from the research matcher.
  - **Why 16 bytes, not 32.** Each byte costs URI length in a legacy transaction (below). A second
    preimage still costs 2^128 work. The chance of an accidental collision among 10^9 names is about
    10^-21. A colliding key could only make the matcher's own routing consolidate two names, never
    take funds.
- **Alongside SlugLock, not instead of it.** The two give different guarantees.
  - SlugLock is a floor that trusts nothing: the program's own fold of the metadata.
  - NameLock covers what the matcher routes together, but trusts the matcher for the key.
  - Removing SlugLock would make the exact-identity floor depend on the matcher key.
- **One rule.**
  - Takeover in `create_room` and the new permissionless `release_name` both use `live_rule`.
  - `release_slug` and the SlugLock takeover use the same function.
  - The old holders are read in place (M-7).
- **Coverage.** `slug_coverage.py`: **0 of 16** routed-together pair classes are now without an
  on-chain floor (9 before).
- **The race is gone, and so is the reservation.** PDA creation is atomic: of two concurrent new-room
  launches under one key, the second fails (`Holder`, 6013) while the first room is live, and nothing
  is created. The service no longer holds anything:
  - the in-flight reservation, the per-launcher hold and the proof of funds are removed
    (`services/matcher/CORRECTIONS.md` §16);
  - H-1's reservation squatting no longer exists;
  - the service e2e (step 1b) shows the race on devnet: both decisions signed, the second rejected
    on-chain, and once re-requested it becomes a T2n door.
- **Not covered by the NameLock:**
  - **Founder position.** Without the reservation, the faster of two racing launchers becomes the
    room's founder. That matters only while `founder_share_bps > 0`.
  - **Faces from floor doors.** A room can gain a face whose key differs from its door 0's: a floor
    door is routed by identity, not text, so `the pepe`/X can join the room of `thepepe`/X. A new
    room under that second face's key is then not blocked on-chain, if the matcher's snapshot misses
    the door (a door landing in the same moment). The reservation never covered this either.
  - **Rooms from before the upgrade** (devnet only) hold no NameLock. The matcher still sees them as
    rooms.
- **Squatting is now paid and on-chain.** A squatter must actually create the room (about 0.0288 SOL
  of rent at maximum metadata) and keep it live: activity and reserve, or 1 hour. A blocked launcher
  is not refused: the matcher routes it as a door into the earlier room, which is the consolidation
  rule working.
- **Cost.**
  - Rent: 817,880 lamports per room (33-byte `NameLock`), +2.9% on a maximum-metadata launch.
  - Trace: +1 entry, so the worst launch uses 49 of 64.
  - Heap: the worst `create_room` fell from ≥ 848 to ≥ 272 bytes at `f87f341`. That traced to
    `create_pda` stranding a `Vec` per created account; with signer seeds on the stack (`71d32f3`) it
    keeps ≥ 1,520 (M-1).
  - CU: +6,290 on the worst `create_room` (295,753 → 302,043 VM CU). The stack-seed change (M-1) then
    saved 2,904, so 299,139 at `71d32f3`.
  - Transaction bytes, the significant cost: at name 32 and symbol 10 the largest URI the service
    can sign in a legacy transaction falls:

    | shape | before | now |
    |---|---|---|
    | new room | 102 | **51** |
    | takeover | 70 | **19** |
    | two locks held by different dead rooms | — | **does not fit** |

    Measured by `services/matcher/scripts/max_uri.py`. **Correction:** this review's earlier estimate
    (37 / 5, for a 32-byte key) assumed a 17-byte lock. The lock stores its key so that `release_name`
    can derive its address, which makes it 33 bytes.
  - With a v0 transaction and a lookup table of the six shared accounts, the same shapes fit 200,
    169 and 137 bytes. Moving the service to v0 is no longer blocked (M-7 is fixed), and is
    recommended (service README, "What remains" item 7).

M-2's regression test stays.

### H-2 — Face laundering through the floor (fixed in the matcher)

**Attack.** The floor routes by the program's ASCII fold, which keeps stopwords; the matcher's name key drops them.
1. Create room "solpepe"/PEPE. Its name key is SOLPEPE, so it matches nobody.
2. Open a door "Sol Pepe"/PEPE. Same program identity, so the floor routes it in. Its name key is PEPE.
3. The matcher matched any door face, so every later "Pepe" launch, any symbol, routed into this room.
4. Against a genuine live Pepe room, the deeper reserve won the tie. Reproduced in
   `test_face_laundering_through_the_floor_is_not_matchable`.

**Why it mattered.** Two live rooms matched one name key, which is the duplicate the NameLock (H-1) exists to prevent.
Under paired doors, the attacker's room would collect every copy's flow.

**Fix.** Routing is the matcher's decision, so the fix is there, not on-chain: a room is text-matched only through faces
carrying its own (door 0's) name key. Text-routed faces always do, so on the 2,956-launch calibration replay this
reproduces v1 exactly (1,224 rooms, 1,732 routed). The independent verifier applies the same rule.

### I-8 — Name evasion (open, partly mitigated)

A copier who wants their own room, not a door, changes the name slightly. Measured with
`services/matcher/scripts/evasion_benchmark.py`: 1,220 real names, dnstwist-derived fuzzers, about 81,600 variants.
`services/matcher/EVASION_BENCHMARK.md` and `services/matcher/CORRECTIONS.md` §§19–20 have the details.

**Disguises a person reads as the same name** (case, spacing, invisible characters, look-alike letters):

| rules | disguised variants that keep the key |
|---|---|
| v1 | 74.7% |
| A + B | 84.0% |
| A + B + C + I (live since 7 November) | 95.4% |

Under the live rules, case and spacing keep the key 100% of the time. Earlier, per-token stopword removal let
"tHe rUnNeR" or "T R U M P" escape. The real-data cost of C and I is 3 routes out of 1,734.

**Still escaping:**
- Cyrillic look-alikes missing from Unicode's confusables data (п, и, ш, ь, ԍ).
- "cl" for "d".
- Every typo: 5.6% of one-edit variants keep the key.
- Most added words: 19.9% keep the key.

Catching typos was measured (phonetic keys, rule F) and costs precision (97.7%). Recall measured on pump.fun, where
nobody was evading a matcher, overstates recall under deliberate evasion. Only the economics can close the rest:
being a door must be nearly as good as owning the room.

### I-9 — Name squatting (open)

The first launch of a name on this launchpad creates its room. A squatter can create rooms for likely narratives early
(or copy pump.fun's trending names first) and keep them live cheaply: 0.5 SOL of reserve, 5 SOL a day of wash volume at
1% (about 0.05 SOL a day). Every later copy, including the genuine creator's launch, becomes a door in the squatter's
room. Inherent to first-come rooms. A higher room floor makes cornering the room's supply costlier; the liveness
thresholds are the other lever (timelocked, M-6).

### M-1 — Launch heap nearly exhausted (fixed)

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
| `1558b2e`, and `b6fe25d` after the pause change (after) | ≥ 688 bytes | ≥ 9,568 bytes |
| `54215ae`, after the M-8 change | ≥ 848 bytes | ≥ 9,568 bytes |
| `f87f341`, with the NameLock (`heap_headroom.f87f341.json`) | ≥ 272 bytes | ≥ 9,568 bytes |
| `71d32f3`, signer seeds on the stack (`verification/heap_headroom.json`) | **≥ 1,520 bytes** | ≥ 9,920 bytes |

On `1558b2e`, a `create_room` **takeover** at the largest size the matcher signs
(name 32, symbol 10, URI 70), prefunded with a first buy, ends with **≥ 496
bytes**, about 1.5% of the heap; ≥ 624 at `54215ae`, and **≥ 2,816** at `71d32f3`
(M-7 and the stack signer seeds).

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

**Remedies taken since,** without a custom allocator (owner decision):
- fewer CPIs on the creation path (M-8, `54215ae`): +160 bytes;
- the takeover's old holder read in place (M-7, `8f54026`): +1,312 on takeovers;
- `create_pda` signer seeds on a stack array instead of `to_vec()` + `push`, which
  stranded 96–144 bytes per created account, about 12 per `create_room` (`71d32f3`):
  +1,248 on the worst `create_room` measured against the NameLock commit.

The worst launch now keeps ≥ 1,520 bytes, about 4.6% of the heap. It is still the
budget every future addition to a launch spends, so `heap_probe.py` stays part of
the evidence for any program change (`scripts/verify_commit.sh`).

See also M-7.

**Regression.** `prefunded_maximum_metadata_launches_fit_the_heap` and
`prefunded_maximum_metadata_takeovers_fit_the_heap`. Both also assert the launch
stays under the matcher's 400,000 CU limit:

| case | `create_room`, `b6fe25d` | `create_room`, `54215ae` | `open_door`, `b6fe25d` | `open_door`, `54215ae` |
|---|---|---|---|---|
| prefunded | 322,161 CU | 295,746 CU | 218,275 CU | 208,417 CU |
| takeover | 326,893 CU | 303,780 CU | 268,677 CU | 258,819 CU |

(`cargo test --locked --test svm prefunded_maximum_metadata -- --nocapture` prints them.)
At `71d32f3` (M-7, NameLock, stack seeds): prefunded 299,139 / 207,696 CU; takeover 306,064
(URI 70) and 306,979 (URI 200, now passing) / 256,558 CU.

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

### M-3 — Per-launcher rate limit was unauthenticated (fixed)

**Attack (before).**
- **Evasion.** The per-launcher limit (6 a minute) keyed on the request's
  `launcher` field, which nothing authenticated. Naming a fresh pubkey evaded it.
- **Targeted DoS.** Naming a victim's wallet six times a minute kept the victim
  rate-limited.

**Fix (`services/matcher/matcher_service/auth.py`, `app.py`).**
- Every `/route` request must carry `issued_at` and the launcher's ed25519
  signature over a canonical message: a fixed prefix plus a JSON array of every
  request field.
- `issued_at` must be within ±120 s, and each signature is accepted once.
  Unknown fields are refused, so nothing unsigned can be smuggled in.
- The per-launcher limiter keys on the verified launcher. A request naming
  someone else's key without their signature is refused (401) before it reaches
  the limiter.

**Cost to the caller:** one `signMessage` by the launcher's wallet per request,
on top of signing the returned transaction. That is one extra wallet prompt in a
browser.

**Tests:** `test_route_requires_a_fresh_single_use_signature_by_the_launcher`
(unsigned, wrong key, altered after signing, stale, replayed, unknown field) and
`test_a_victims_launcher_limit_cannot_be_spent_by_someone_else`. The e2e now
signs every request.

**Not fixed by this:** keys are free, so this does not stop H-1.

### M-4 — Launch first buys defaulted to no slippage limit (fixed)

**Before.** `min_tokens_out` defaulted to 0. An `open_door` first buy into a
trading room could be sandwiched for its whole size.

**Fix (`services/matcher/matcher_service/quote.py`, `service.py`).** With
`first_buy_lamports > 0`:
- **Omitted `min_tokens_out`:** the service quotes the buy against the snapshot.
  The quote ports the program's integer math line for line, including the
  pending-backlog settlement a buy performs first. It signs
  `floor(quote × (10,000 − max_slippage_bps) / 10,000)`.
- **Default `max_slippage_bps`: 200 (2%),** per `DESIGN.md` §3 ("the frontend
  default should be ≤ 2–3%"); the spec itself gives no number (CORRECTIONS).
  Allowed range: 1–5,000.
- **An explicit `min_tokens_out`** is kept, and an explicit 0 is refused.
- **An unfillable buy** is refused, before signing.
- The rule applies to new rooms too, for uniformity. Their quote is exact,
  because nothing can trade before creation.

**Tests.**
- **Quote parity:** the program's reference vector (101 lamports → 3,612,416 base
  units).
- **Defaults:** the 2% default, explicit limits, refusal of 0 and of an unfillable
  buy.
- **On-chain, localnet e2e step 3b:**
  - an unmoved door first buy fills **exactly** the quoted tokens;
  - the same launch front-run by a 1 SOL buy is rejected with `Slippage`.

**Residual.** The verifier checks the signed minimum against the *recorded*
quote. It does not recompute the quote from history, because that needs every
fee split to rebuild the pending backlog.

### M-5 — Pause stopped sells (fixed; spec updated)

**Before.** `trade()` rejected every buy **and sell** while `Config.paused`, and
so did `convert`. Holders could not exit while the admin kept the program paused.

**Fix (`lib.rs`).**

| while `paused` | instructions |
|---|---|
| rejected | buys on both routes, `create_room`, `open_door`, `retire_pending` |
| open | sells on both routes, `convert`, claims, `set_fee_recipient`, `release_slug` |

**Invariant review: does anything need buys and sells paused together? No.**
- **I1, reserve ≥ R(sold).** The reserve leaves only by a sell, by exactly
  `R(q) − R(q − t)`, and sell proceeds telescope. Any sequence of sells from
  `sold = s` pays at most `R(s) ≤ reserve`. Buys are irrelevant to this bound.
- **B1, backing.** A door sell moves equal amounts in both directions; `convert`
  moves equal amounts between two doors. Both are asserted per instruction.
- **S1, room vault** and **fee coverage** are per-instruction assertions too.
- **Status.** A sell that takes a capped room below the trigger sets status 0,
  while paused as well. Buys stay blocked by the pause and resume on unpause.

**Two consequences, by design and stated in the spec:**
1. **No emergency stop for the sell path.** An exploit in the sell or convert path
   can no longer be stopped by pausing, only by an upgrade.
2. **Sellers forgo the pending backlog.** `retire_pending` stays paused, so a
   seller during a pause does not receive the unsettled backlog; it stays with the
   holders at settlement. Letting `retire_pending` run while paused would give
   sellers their share first. That is an owner choice; it was outside this change.

**Test:** `pause_blocks_new_positions_but_holders_can_still_exit`.
- While paused it checks:
  - buys, `open_door` and `retire_pending` fail with `Paused`;
  - a convert and complete exits from two doors and the room token succeed, with
    every invariant audited;
  - claims work.
- After unpausing, buys work again.

### M-6 — Liveness thresholds could be changed at once (fixed: 7-day timelock)

**Before.** The liveness thresholds live in Config and are read at execution by
`open_door`, by `create_room` takeover and by `release_slug`. The admin could set
`live_min_reserve_lamports` above every reserve in one `update_config`, which made
every mature room dead at once and freed every name for takeover.

**Owner decision: timelock, not snapshot.** Keep the shared gate, which is the
only lever against cheap wash-traded liveness (I-3), but delay every change by 7
days with an on-chain event.

**Fix (`lib.rs`, `state.rs`, `contexts.rs`).**
- **`update_config`** now refuses any change to the five gate thresholds
  (`GateTimelock`).
- **`propose_gate(gate)`** (admin) writes the PDA `PendingGate` `["gate"]` with
  `effective_at = now + GATE_DELAY_SECONDS` (604,800 s, a program constant the
  admin cannot shorten). It emits `GateChangeProposed { current, proposed,
  proposed_at, effective_at }`. A new proposal replaces the old one and restarts
  the clock.
- **`apply_gate()`** (anyone, only once `now >= effective_at`) copies the gate into
  Config and emits `ConfigChanged` (replayed by the decision verifier) and
  `GateChangeApplied`. It closes `PendingGate` back to the admin.
- **`cancel_gate()`** (admin) withdraws a proposal.
- **No migration needed.** Config's 248-byte layout is unchanged, so the devnet
  Config stays valid.

**Test:** `liveness_gate_changes_are_timelocked_for_seven_days`. It checks that:
- `update_config` cannot touch the gate;
- a non-admin cannot propose;
- applying at delay − 1 s fails, and cancel closes the proposal;
- a re-proposal restarts the clock;
- after the full delay a stranger can apply it;
- Config then holds exactly the new gate, with every other field unchanged.

**What remains.** The admin can still change the gate, with seven days' public
notice. Watchers, founders and the matcher service see `GateChangeProposed` the
moment it lands.

### M-7 — Prefunded maximum-metadata takeover exhausts the heap (fixed, pre-existing)

**Attack.**
1. A launch takes over a dead room's identity: `create_room` with `old_holder`.
   It deserialises a second `Room`, about 1.5 KB on the heap.
2. Add maximum metadata (name 32, symbol 10, URI 200) and a first buy.
3. Prefund the launch's new PDAs. Anyone can, by front-running the launch with
   plain System transfers.
4. The launch fails: `memory allocation failed, out of memory`.

**Affected code:** `create_room` (`lib.rs`) plus the allocation pattern in M-1.

**Exploitable before the fix?**
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

**Reproduction:** formerly `prefunded_v0_maximum_takeover_exhausts_the_heap`, marked
`#[ignore]`. It now passes as `prefunded_v0_maximum_takeover_fits_the_heap`, run with the suite.

**Fix (`8f54026`): the targeted option, by owner decision.**
- **What was large:** the only takeover-specific deserialisation, `old_holder:
  Option<Box<Account<Room>>>`. That is a full 1,315-byte `Room` boxed on the heap to read six
  fields (verified: `read_slug` reads a 17-byte `SlugLock` on the stack; nothing else on the path
  is takeover-specific).
- **Now:** an `UncheckedAccount` read in place (`state::RoomBytes`), with the checks
  `Account<Room>` made: owner, exact size, discriminator, canonical room PDA. Liveness comes from
  one function, `state::live_rule`, shared with `Room::live`.
- **Tested:** `takeover_holder_is_validated_in_place`. Same precedent as `mint_check` (M-1).
- **Measured** (`heap_probe.py`; `heap_headroom.1de13c9.json` → `heap_headroom.8f54026.json`): the
  holder cost 1,312 bytes.

  | path | before | after |
  |---|---|---|
  | takeover, URI 70 (service maximum) | ≥ 624 | ≥ 1,936 |
  | takeover, URI 200 (v0 maximum) | **fails** | ≥ 1,280 |
  | `open_door` takeover | ≥ 8,256 | ≥ 9,568 |

- **No custom allocator,** by owner decision. The evaluation below stands as the record of why
  it was considered.

**Evaluated: `ComputeBudgetInstruction::RequestHeapFrame`. On its own it does not
resolve M-7.** First evaluated at `b6fe25d`, re-measured at `54215ae` after the M-8
fix.

1. **The program's allocator never uses the extra frame.** The program uses the
   stock entrypoint allocator: `custom_heap_default!` in
   `solana-program-entrypoint` 3.1.1 builds
   `BumpAllocator::with_fixed_address_range(HEAP_START_ADDRESS, HEAP_LENGTH)`, with
   `HEAP_LENGTH = 32 * 1024` fixed at compile time. The runtime maps the larger
   frame, but this allocator still allocates only within the first 32 KiB.
   Measured with `heap_probe.py --heap-frame 262144` at `54215ae`
   (`verification/heap_headroom.frame262144.json`, against
   `verification/heap_headroom.json`):

   | path | free heap at end, no request | with a 256 KiB request |
   |---|---|---|
   | `open_door`, prefunded, maximum metadata, first buy | ≥ 9,568 bytes | ≥ 9,568 bytes |
   | `create_room` takeover, URI 70, prefunded | ≥ 624 bytes | ≥ 624 bytes |
   | `create_room`, prefunded, maximum metadata, first buy | ≥ 848 bytes | ≥ 848 bytes |
   | v0 maximum takeover (the ignored reproduction) | fails | **still fails** |

2. **Trace room: no longer a blocker.** At `b6fe25d` the prefunded `create_room`
   with a first buy used 63 of 64 trace entries, so the request (one more top-level
   instruction) broke it; that row read "cannot run". After M-8 the same launch
   uses 47, and it runs with the request (row 3 above).

**Cost of the request** (worst-case launches, same heap-probe runs at `54215ae`):
- **CU, `create_room`:** transaction 295,952 → 297,726 (+1,774), program
  295,802 → 297,370 (+1,568).
- **CU, `open_door`:** transaction 208,603 → 209,873 (+1,270), program
  208,453 → 209,517 (+1,064). At `b6fe25d` it was the same +1,270 / +1,064.
- **Lamports:** no charge of its own. The fee is per signature plus priority fee
  × requested CU limit.

**A launch built by a third party without the request** behaves exactly as today,
since the allocator is unchanged. If it runs out of heap, the program panics with
`memory allocation failed, out of memory`. That is a clean failure: the runtime
rolls back every account change atomically and charges only the network fee.

Even with a custom allocator sized above 32 KiB (excluded from this task), a
transaction without the frame request could not corrupt anything. The VM
bounds-checks every heap access, so going past the mapped frame is an access
violation, the same atomic, clean failure.

**Status: fixed.** With the NameLock and the stack signer seeds (H-1, M-1), the v0 maximum takeover
keeps ≥ 2,160 bytes at `71d32f3`. The matcher service may now sign v0 launches as far as the heap is
concerned (its README, "What remains" item 7).

### M-8 — Prefunded launches sat at the instruction-trace limit (fixed)

**What happened.** A transaction may contain at most 64 instruction entries
(`MAX_INSTRUCTION_TRACE_LENGTH`), counting every top-level instruction and every
CPI. Prefunding a PDA, which anyone can do, turned its single `create_account`
CPI into transfer + allocate + assign. A prefunded `create_room` with a first buy
used 63 entries, and 64 (the limit) with the matcher's priority-fee instruction.
Any added instruction (a heap request, a memo) or CPI made it fail.

**Fix (`vaults.rs`, `trading.rs`).**
- **Prefunded accounts.** `create_pda` creates a prefunded PDA with one SIMD-0312
  `CreateAccountAllowPrefund` CPI. The feature is active on devnet since slot
  454,464,000 and mainnet since slot 422,928,004 (`solana feature status
  6sPDzwyARRExKH52LECxcGoqziH8G7SZofwuxi8Ja331`). Anchor's `init` already did this
  for `Room` and `Door`.
- **The instruction itself is built with exact allocations** (`allow_prefund_ix`).
  The library builder's growing `Vec` alone cuts the worst `create_room` heap margin
  from ≥ 848 to ≥ 16 bytes and makes the service-size takeover fail, measured
  (`heap_headroom.ab_library_allow_prefund_builder.json`). Byte equality with the library builder is
  asserted.
- **Tried and reverted: merging a buy's two System transfers into one.** It saved
  one trace entry but cost about 330 bytes of heap (measured A/B). Heap is the
  tighter budget, so it was reverted.

**Trace entries after the fix** (`launch_instruction_trace_budget`,
`verification/trace_budget.json`):

| launch, with a first buy | `[cu_limit, launch]` | `[cu_limit, cu_price, launch]` |
|---|---|---|
| `create_room` | 46 | 47 |
| `create_room`, every new account prefunded | **47** (was 63) | **48** (was 64) |
| `open_door` | 27 | 28 |
| `open_door`, every new account prefunded | 29 (was 35) | 30 (was 36) |

**What the test now asserts.**
- Every shape keeps at least 12 entries free.
- Prefunding adds at most 2 entries. Both are the Associated Token program's own
  handling of a prefunded user ATA, which this program cannot change.

**Remaining budget.** 16 entries on the worst launch at this fix. The NameLock
(`f87f341`) then took one: every `create_room` row above is +1, so the worst
launch uses **49 of 64**, 15 free (`verification/trace_budget.json` at `71d32f3`).

**Heap and CU** (`heap_probe.py`, `verification/heap_headroom.json` at `54215ae`):

| path | free heap at end, `b6fe25d` | `54215ae` |
|---|---|---|
| worst `create_room` (prefunded, maximum metadata, first buy) | ≥ 688 bytes | **≥ 848** |
| `open_door`, same conditions | ≥ 9,568 | ≥ 9,568 |
| `create_room` takeover at the service's largest size (URI 70) | ≥ 496 | **≥ 624** |

The worst `create_room` uses 295,952 transaction CU, down from 322,367. A/B probes
isolate the changes. Each variant is a patch against `54215ae` in
`verification/ab/`, run with `heap_probe.py --patch`:

| variant | worst `create_room` | `open_door` | URI-70 takeover | worst `create_room` tx CU |
|---|---|---|---|---|
| none (`54215ae`) | ≥ 848 | ≥ 9,568 | ≥ 624 | 295,952 |
| pre-M-8 prefunded path (transfer + allocate + assign) | ≥ 688 | ≥ 9,568 | ≥ 496 | 322,405 |
| buys' two transfers merged into one | ≥ 512 | ≥ 9,248 | ≥ 288 | 295,129 |
| library `create_account_allow_prefund` builder instead of `allow_prefund_ix` | ≥ 16 | ≥ 9,568 | **fails** (0) | 301,664 |

So the one-CPI prefund path accounts for the whole heap gain since `b6fe25d`. Merging
the buy transfers would have given back more than all of it.

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

### L-6 — The verifier took block time for Clock (fixed)

**What happened.**
- `verify_decision.py` rebuilds room state from events and stamps each one with
  the transaction's block time. It assumed that block time equals the `Clock` the
  program read.
- **On localnet they are equal; on devnet they differ by a second.** The first
  devnet run reported DISAGREE on a correct decision:
  `created_at` and `last_trade_at` rebuilt as 1793880912, against 1793880911 on
  the account.
- A false DISAGREE undermines the verifier as much as a false AGREE would.

**Fix.**
- `created_at` is immutable, so it is read exactly from the Room account.
- `last_trade_at` and the bucket starts are compared within 5 s.
- The decision is recomputed at both ends of that tolerance. If the outcome
  depends on it, the verifier reports **INCONCLUSIVE** (exit 2), never AGREE or
  DISAGREE.
- A doctored time beyond the tolerance is still caught (e2e step 9, new case).

**Results.** All six recorded decisions from the failed devnet run now verify
AGREE, and so does every decision in the passing devnet and localnet runs.

**Exact replay** would need the program to emit its Clock in `RoomCreated` and
`Trade`. That is an IDL change, left for the owner.

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

**Counts at the observed maximum.** By observed maximum CU (LiteSVM, Agave 4.3.2;
not an upper bound) and the 24,000,000 CU writable-account cap, per room per block:

| route | observed max CU | per room/block at that CU |
|---|---|---|
| buy_door | 69,450 | 345 |
| sell_door | 57,430 | 417 |
| buy_room | 53,561 | 448 |
| sell_room | 42,041 | 570 |
| convert | 68,846 | 348 |
| open_door | 149,950 | 160 |

Source: `verification/cu.md`. These are not worst cases, and the live runtime has
exceeded the VM maxima: across two localnet runs, `claim_door_fees` by 4,500 and 10,500 CU, and
`convert` by 5,773 and 1,273.

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
- **Block names through the matcher, almost for free (H-1).** Requests are now
  signed, but keys cost nothing, so this is still the cheapest attack in the
  system. It is open, pending your choice of remedy.
- **Flood a popular room with clone doors.** Each costs about 0.0097 SOL of
  permanent rent.
- **Spam a room's write lock.** They pay every fee. It raises costs for
  everyone in that room while it lasts.

**Cannot:**
- freeze a room, drain it, or put it in a state that permanently breaks trading;
- stop holders selling. Nothing can now, not even the admin's pause (M-5);
- rate-limit someone else's wallet (fixed, M-3);
- break launches signed by the current service by prefunding their accounts.
  The margin is thin (M-1) but tested at every size the service signs.

**Can, but not through today's service:**
- make a maximum-metadata takeover launch fail by prefunding its accounts. That
  size needs a v0 transaction (M-7, open);
- make a prefunded launch fail by adding one instruction. Today's launches have
  no room for one: they sit at the 64-entry trace limit (M-8, open). A launch
  built by the matcher adds none.

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

**Launch first buys** now carry a minimum by default: the quoted amount less 2%
(M-4, fixed). A launch front-run past that limit fails, and the launcher spends
nothing but the network fee.

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
| **pause** | stops buys, launches and fee settlement in every room, for as long as it likes. **Sells and conversions keep working, so holders can always exit at the curve price** (M-5, changed 5 November). Claims still work. |
| change liveness thresholds | decides which rooms accept new doors and when a name can be released or taken over. **Every change is public for 7 days before it can take effect** (`propose_gate` → `apply_gate`, M-6); there is no instant change |
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

**Plainly, for users:**
- **The admin can stop new buying at any time**, for as long as it likes, but
  cannot stop you selling.
- **The admin can tighten the liveness rules**, which can free names, but only
  after a public 7-day notice on-chain (M-6). Anyone watching sees it coming;
  rooms keep trading either way.
- **Nothing the admin can do takes holders' money directly.**

### A compromised upgrade authority

**Everything.** The upgrade authority can replace the program. A replaced
program can sign as every vault, so it can:
- send every room's SOL reserve and fee balances anywhere;
- move every locked room token out of the door backings.

Door and room tokens would then be claims on nothing. The token authorities
are revoked, so it cannot mint or rename tokens, but that protects nothing once
the reserves are gone.

**Shown on devnet, not hypothetical.** The `54215ae` upgrade (`DEPLOYMENT.md` §5,
slot 519,010,828) replaced the live program with one key and one transaction,
with no on-chain notice to holders. The same holds for every timelock in the
program: an upgrade can remove M-6's 7-day gate notice outright. **The gate
timelock protects holders only as far as the upgrade authority is itself
constrained.**

**This is why the mainnet upgrade-authority decision (`DEPLOYMENT.md` §8)
matters more than any finding above.** The options:
- **Single hot key:** one theft takes everything.
- **Multisig:** needs several keys.
- **Timelock:** gives holders time to exit before a change lands. Pause can no
  longer stop them exiting (M-5).
- **Immutable:** removes the risk and the ability to fix bugs or add graduation.

Since pause no longer stops sells (M-5), **the upgrade authority is the only way
to stop an exploit in the sell or convert path.** An immutable program would have
no way at all.

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
| `/route` input validation | Types, integer ranges and UTF-8 byte limits equal `Launch::validate`. Body cap and surrogates fixed (L-2, L-3). Requests are launcher-signed with unknown fields refused (M-3). First buys always carry a price limit (M-4). Oversize transactions are refused before signing. |
| routing influence by crafted input | **By design, yes.** Matching a live room's name routes into it. Look-alikes the rules miss get their own room, at the measured recall. Only the current live NameLock holder receives text-routed doors; revived former holders cannot buy their way back into routing. Conflicting live SlugLock/NameLock holders cause a refusal. |
| rate-limit evasion | Per IP: proxy-correct (L-1). Per launcher: keyed on the signature-verified launcher (M-3, fixed); evasion needs a new key per request, which is free (H-1). |
| decision store rewrite / fork | No fork (process lock plus `BEGIN IMMEDIATE`). Rewrite is possible for the operator until the head is published (I-9). |
| concurrent identical launches, duplicates, retries | New-room: the second request is refused (M-2 fixed). Door: each request gets its own random nonce; both can land if the launcher signs both, each paying its own rent. Retries after a timeout see `409` until the first decision expires (about 60–90 s); there is no idempotency key. |
| service assumes, program does not enforce | Text rules (T2n, normalisation, tie-break); single-replica in-flight state; the decision log. |
| program enforces, service relies on | Exact-identity floor, room liveness at execution, launch expiry, door nonce rules, signed fee cap, terms hash. A stale snapshot can only make a launch fail on-chain, never route it wrongly past these checks. |
| expiry seam | `expires_at_slot = blockhash slot + 150`. Slots advance at least as fast as block height, so the program's expiry never outlives the blockhash. Durable nonces are caught by the program (localnet e2e step 6c). |
| CU seam | Current worst prefunded, maximum-metadata atomic-first-buy launch: 351,341 VM transaction CU (351,191 program-inclusive), production ELF `d1fb4975`. The matcher default is now 500,000 CU. Rounded review stress: 351,341 + 21,000 token drift + 7,500 bump variance + 15 x 1,500 extra bump tries = 402,341, leaving 97,659 CU. The enforced conservative check also includes the 150-CU priority-price instruction and exact historical 21,110 peak: 351,341 + 150 + 21,110 + 7,500 + 22,500 = 402,601, leaving **97,399 CU**. The SBF maximum-launch/takeover tests and heap probe enforce the allowance. Current SBF already loads pinned SPL binaries; historical drift is retained as additional stress headroom, not presented as a fresh live-runtime measurement. |
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
- **Mainnet, and load on devnet.** The program is deployed on devnet, and both
  e2e suites pass there (`DEPLOYMENT.md` §5, §7), but:
  - that is one sequential run, so scheduling, write-lock contention and
    priority-fee dynamics under load are unmeasured;
  - live devnet CU exceeded the VM maxima on several routes (`create_room` by
    12,003, 25,610 and 19,610 across three upgrades; a constant token-program offset
    plus per-launch bump search, `DEPLOYMENT.md` §7);
  - nothing has run on mainnet.
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

### Previous measured verification (8 November 2026, before A/B/D)

[Successful Linux verification](https://github.com/Arriived/bonding-curve/actions/runs/42403905057) tested program source `9ed04d7`: **71 SBF tests passed**, including 10,000 mixed iterations and 12,488 executed transactions. IDL, account layout, source hashes, offline SPL hashes, binary pin, standalone client unit test, heap probe and 400,000-iteration curve fuzz all passed. The service passed **163 pytest tests**. Repeating the full evasion benchmark reproduced its JSON exactly.

The source-verified ELF SHA-256 is `e3c9aa751d2745b6e89dee76dbf362556f460f42288421a55c57bae3b4ede6b4`. The matching program and service IDL pins were compared byte-for-byte with emitted Anchor output.

| Instruction | Maximum measured transaction CU | Maximum trace entries / 64 | Free heap, at least (bytes) |
|---|---:|---:|---:|
| buy_door | 75,579 | 9 | 17,440 |
| sell_door | 102,003 | 6 | 19,856 |
| swap_doors (new/prefunded vault) | 94,823 | 10 | 18,784 |
| swap_doors (existing vault) | 88,025 | 8 | 19,248 |
| claim_door_swap_fees | 60,387 | 5 | 25,632 |
| claim_protocol_swap_fees | 34,623 | 5 | 26,512 |

CU maxima combine the boundary resource fixture, paired trade-limit fixture and mixed-operation run. The latter records inclusive program CU; its single compute-budget instruction adds 150 transaction CU. Trace figures are measured successful instruction invocations, including the compute-budget instructions. The boundary fixture uses a 400,000-CU limit, priority fee and a 32 KiB heap request. Heap is measured separately by an appended allocation in 16-byte steps. These are tested bounds, not an exhaustive maximum over every possible public key or future Config.

Every one of the 33 doors in each of four resource scenarios had a positive token position and positive swap credit before its full sale and claim. All ended at zero position/credit; the room-wide unclaimed swap total also ended at zero. Creation retains at least **2,960 bytes** of the default 32 KiB heap, above the existing 1,500-byte target.

**Lowest measured ordinary-operator liveness construction:** 20,020,000 lamports (**0.02002 SOL**) per room per day; 2,002,000,000 lamports (**2.002 SOL**) for 100 rooms using the same per-room transaction pattern. It uses four signed transactions/day, zero priority fee, default thresholds, a self-owned door recipient and a distinct protocol recipient. The SBF test bootstraps the first rolling window and checks liveness before and after the maintenance trades over two further days. It spends 40,040,000 lamports for those two days.

The irrecoverable **program-fee floor** is 0.02 SOL/room/day, or **2 SOL/100 rooms/day**: 5 SOL curve volume times 1% fee times the 40% unrebatable protocol share. The remaining measured 0.00002 SOL/room/day is four 5,000-lamport signature fees. Cross-room transaction batching can reduce that network overhead; 2.002 SOL is the measured unbatched construction, not a proof of the globally cheapest 100-room packet schedule. Organic activity or protocol-fee ownership changes the operator economics.

The 0.5 SOL reserve floor per room (**50 SOL for 100 rooms**) is recoverable capital, not daily spend. The alternating buy temporarily needs another 1.2625 SOL gross per room. Creation rent, one-off bootstrap fees and account rent are excluded from upkeep. No liveness parameter was changed.

Evasion catch rates: mixed-script words **74.5%** with the symbol kept (**74.3%** with the symbol fuzzed); actual 32-byte UTF-8 truncations **5.5%** in both modes. The baseline disguise recall remains **95.4% / 95.1%**. Rules are unchanged.



### Ranked continuation findings

| Rank | Severity | Finding | Status | Cost | Payoff or protection |
|---|---|---|---|---|---|
| 1 | High, release blocker | Service quote used room units for a door-token minimum | Fixed | Ordinary launch | Correct first-buy fills and slippage minima |
| 2 | Medium | Room front-run changes a new door's birth anchor | Fixed, approved price bound | Recorded 5-20 SOL front-run capital | Up to 0.217061544 SOL attacker net in the supplied cases; refused at 2% now |
| 3 | Medium | Public RPC failure text can expose endpoint credentials | Fixed | Failure-triggering HTTP request | Prevents RPC quota/billing credential exposure |
| 4 | Medium | Revived former NameLock holder can regain text routing | Fixed | Funded revival no longer buys new launch eligibility | Current live NameLock holder exclusively receives text flow; conflicts refuse |
| 5 | Low | Default liveness is inexpensive to maintain | Owner decision | 0.02002 SOL/room/day; 2.002 SOL/100 rooms with the measured pattern | Continued name lock and routing eligibility |
| 6 | Low | Name evasion through mixed scripts and truncation | Owner decision; rules unchanged | Launch rent plus upkeep | Possible separate room/routing diversion; catch rates 74.5% and 5.5% |
| 7 | Low | Authorized admin can choose the 120 SOL stress cap | Fixed | Default build enforces 85,018,013,680-lamport ceiling | 120 SOL accepts only in isolated test-stress build |
| 8 | Info | Excess unused storage at room birth | Implemented; 15 million target not reached | Birth rent 26,959,560 -> 17,515,840 lamports; first-use costs deferred | Saves 9,443,720 lamports per room at birth; exact liveness preserved |

The same-slot NameLock race, request replay/alteration and resource exit/claim
checks found no additional defect. Their passing tests are retained as coverage.


### Owner-ruling measurements (8 November 2026)

Controlled baseline is program `816b38d` / service `f2f8451`. Production source
`5ac41b9` passed 71/71 SBF tests, 10,000 mixed iterations (12,488 transactions),
the isolated stress feature checks, heap probe, client compile/unit test and
400,000 curve-fuzz iterations in run 42526020048. That run stopped only at the
old binary hash. Every recorded source hash and the emitted IDL matched the
working tree before pinning the new production ELF. The final pinned run is
[42526798488](https://github.com/Arriived/bonding-curve/actions/runs/42526798488),
which passed every step on `86a0f44` with the same production source. Historical B/D negative controls are assigned to
the independent reviewer, as approved; they were not executed on this machine.

| Measurement | Before (`816b38d`) | After (`5ac41b9`) |
|---|---:|---:|
| Room with door 0 birth rent, lamports | 26,959,560 | 17,515,840 |
| Additional empty door rent, lamports | 8,839,200 | 7,350,760 |
| First swap-fee vault rent, lamports | 1,488,440 | 1,488,440 |
| Worst-case creation free heap, bytes at least | 2,960 | 4,080 |
| Worst-case open free heap, bytes at least | 10,096 | 10,640 |
| Worst-case creation CU, heap-probe fixture | 328,089 | 351,341 |
| Worst-case open CU, heap-probe fixture | 242,597 | 284,233 |

These CU rows compare the same maximum-metadata/prefunding/first-buy fixture.
Birth rent uses the same zero-first-buy/default-Config metadata fixture.
Birth-only initialization is cheaper; first-use initialization and Room growth
shift work into buys. The tested launches still fit 400,000 CU and the 64-entry
trace. Heap figures use the default 32 KiB allocator and 16-byte resolution.

| Instruction | Before free heap | After free heap | After maximum measured transaction CU | After trace entries / 64 |
|---|---:|---:|---:|---:|
| buy_door | 17,440 | 17,456 | 108,161 | 13 |
| sell_door | 19,856 | 20,416 | 100,121 | 6 |
| swap_doors | 18,784 | 19,072 | 109,434 | 11 |
| swap_doors_existing | 19,248 | 19,808 | 103,046 | 10 |
| claim_door_swap_fees | 25,632 | 26,192 | 57,968 | 5 |
| claim_protocol_swap_fees | 26,512 | 27,072 | 32,181 | 5 |

The economic scenario JSON is unchanged exactly. All 33
doors in each of four resource scenarios still fully sell and discharge their
fee credits. Sparse storage preserves exact hourly values; fees, curves, liveness
thresholds and name normalization are unchanged. The 15 million birth target is
unreached with the current required layouts. Data and full CU ranges are in
`verification/owner_rulings_before.json` and `owner_rulings_after.json`.

The service's final 170-test suite passes. Its IP spoofing burst test now uses a
fixed limiter timestamp: on a slower run, 31 request constructions had taken long
enough for a real token refill, which invalidated that test's burst assumption.
Production rate limiting is unchanged. The repeated evasion benchmark is
byte-identical, retaining 74.5% / 74.3% mixed-script and 5.5% truncation catch rates.


The current unbounded 20 SOL front-run still reduces victim exit by the same
549,648,652 lamports. Its attacker wallet net is now 215,573,104 lamports rather
than the baseline 217,061,544: the first fee claim pays the newly deferred
1,488,440-lamport WSOL vault rent. This is a first-use storage cost, not a fee or
curve change. The bounded launch remains refused at 2%, and zero remains accepted.
The historical witness is preserved separately so the original numbers stay
reproducible and distinguishable from current wallet-cost accounting.


First-use costs: a swap into an unused receiving door creates its backing as
well as the swap-fee vault (2,976,880 lamports total before prefunding offsets).
The first ordinary fee claim creates the WSOL vault (1,488,440 lamports), and the
first buy funds full Room capacity plus its necessary native/backing accounts.
These costs are paid by the respective first-use payer, not by later sellers.


### Final owner-ruling verification

[Run 42526798488](https://github.com/Arriived/bonding-curve/actions/runs/42526798488)
is green on `86a0f44`: 71 SBF tests, 10,000 mixed iterations / 12,488 transactions,
offline pinned SPL executables, both permanent cap-test directions, the isolated
supply-exhaustion exit test, heap probe, client compile/unit test, 400,000 curve
iterations, source/IDL checks and the updated production binary pin all pass.
Every emitted source hash matches this branch; program/service IDLs match emitted
bytes exactly. Findings 4 and 7 are Fixed. D is implemented with the documented
15 million target gap and first-use costs. Historical B/D control commit is
`816b38d`, assigned to the independent reviewer by the owner's instruction.
The local service run on `bf121dc` passed 170 tests. Its unchanged-rule benchmark
JSON repeated exactly. Machine-readable checks: `verification/owner_rulings_checks.json`.


### Launch CU margin blocker: Fixed (8 November 2026)

Control service `b86ae42` defaulted to 400,000 CU. The new default/message
regression failed with 400,000 versus 500,000 before changing config; the explicit
override still passed. `MATCHER_CU_LIMIT` now defaults to 500,000 and remains
configurable. The SBF maximum-metadata prefunded launch and takeover tests assert
the full drift allowance; launch trace transactions use the new limit. The heap
probe separately checks its measured maximum, including the priority-price
instruction and exact historical 21,110-CU token offset. No rent-saving code or
production program source changes.

The review's rounded arithmetic gives 97,659 CU margin. Counting the extra
priority-price instruction (150) and using the exact historical peak rather than
rounded 21,000 makes the enforced margin **97,399 CU**: 500,000 - 402,601.

Priority fee for these legacy transactions is
`ceil(cu_limit * cu_price_micro_lamports / 1,000,000)` lamports, based on requested
limit. At a representative price of 10,000 micro-lamports/CU, the new priority
fee is **5,000 lamports (0.000005 SOL)**, versus 4,000 at the old limit: an extra
1,000 lamports (0.000001 SOL). At price zero it stays zero. Base signature fees
are separate. Formula source: [Solana fee documentation](https://solana.com/docs/core/fees).

`max_uri.py` now reads the same default constant as service config. Comparing
400,000 and 500,000 yields identical packet sizes: the limit is a fixed-width
u32 in the existing instruction. At name 32/symbol 10 with a priority instruction:

| Shape | Largest legacy URI bytes | Wire bytes at that URI | Wire bytes at URI 200 |
|---|---:|---:|---:|
| create_room | 35 | 1,232 | 1,397 |
| create_room, one old holder | 3 | 1,232 | 1,429 |
| open_door | 200 | 1,206 | 1,206 |
| open_door takeover | 194 | 1,232 | 1,238 |
| create_room, two distinct old holders | Does not fit | Over limit even at URI 0 | 1,461 |

Thus full 200-byte creation metadata still does not fit legacy packets; the
service's existing size refusal remains. Raising the CU limit consumes no extra
packet bytes. No v0 signing support is introduced. Rent remains 17,515,840
lamports at birth, 35.0% below its earlier baseline.


Final launch-budget verification: [CI 42536522731](https://github.com/Arriived/bonding-curve/actions/runs/42536522731)
is green on `0849033`: 71 SBF tests, 10,000 mixed iterations / 12,488 transactions,
pinned SPL binaries, both stress-feature checks, heap, 400,000 curve cases,
client compile/unit test and unchanged production binary pin. The maximum heap
fixture records 402,601 stressed CU / **97,399 margin**. Birth rent remains
17,515,840 lamports; creation heap remains at least 4,080 bytes. Every source hash
and emitted IDL matches the candidate. Service `6109176` passes 172 tests; the
1,223-target evasion benchmark repeats byte-identically. Full cross-branch data:
`verification/launch_cu_budget_checks.json` and `launch_cu_packet_sizes.json`.
