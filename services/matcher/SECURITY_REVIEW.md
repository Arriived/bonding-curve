# Paired matcher review, 7 November 2026

This is the authors' own review, starting at service `9750e03` and program
`2bf6f40`. Tests use synthetic identities, mocked HTTP/RPC and offline SBF
evidence. No deployment or production signing material is used.

| Rank | Severity | Finding | Status | Cost and payoff |
|---|---|---|---|---|
| 1 | High, release blocker | First-buy minimum used room tokens instead of door tokens | Fixed | Ordinary launch; can refuse legitimate fills or leave a weaker minimum. Exact SBF parity now tested |
| 2 | Medium | New-door anchoring bypasses a token-only launch slippage limit | Fixed with owner approval | Recorded 20 SOL front-run earned 0.217061544 SOL and reduced victim exit by 0.549648652 SOL |
| 3 | Medium | RPC failure text disclosed endpoint credentials or provider text | Fixed | Unauthenticated failure-triggering request; possible RPC quota or billing abuse |
| 4 | Medium | Revived former holder can regain text flow despite a successor's live NameLock | Fixed | Current live NameLock holder exclusively receives new doors; conflicting live SlugLock refuses |
| 5 | Low | Paid liveness permits long-term name carrying | Owner decision | 0.02002 SOL/day with the measured four-transaction pattern, plus setup and recoverable capital |
| 6 | Low | Mixed-script and 32-byte truncation variants evade existing name keys | Owner decision; rules unchanged | New-room rent and ongoing carrying cost; possible routing diversion |
| 7 | Low | Authorized admin can choose the 120 SOL stress cap | Fixed in paired program | Default build refuses above the normal ceiling; isolated test-stress build accepts 120 SOL |
| 8 | Info | Excess unused room birth storage | Implemented; target not reached | Rent 26,959,560 -> 17,515,840 lamports, 35.0% saved; unused vault costs deferred |
| 9 | Info | Request replay and alteration | Existing M-3 protection confirmed | Concurrent replay accepts exactly one of 32 requests; every changed signed field is refused |

The first-buy regression failed before the port: 19,628,248,343,287 room base
units versus the recorded SBF output of 33,699,309,828,108 door base units.
The quote now anchors before settlement, settles pending fees, prices both legs
and signs the minimum in door units. The independent verifier rebuilds sold and
pending amounts from events and derives its own quote. Trade decoding includes
the added room-token amount; both new swap events are decoded.

The active paired Launch carries an eight-byte `max_reserve_lamports`. The
reserve guard runs at the original pre-settlement point. An omitted first-buy
cap is derived from the chosen slippage, and zero bypasses the reserve cap.
The program and service use the emitted paired IDL. Room accounts occupy 735
bytes at birth or 1,335 after the first buy. Doors occupy 360 bytes.

## Evasion measurements

The fixed-seed run uses 1,223 target keys from the same 2,956-launch sample.
Rules are unchanged and cross-checked against the independent candidate code.

| Variant | Symbol kept | Symbol also fuzzed |
|---|---|---|
| Existing disguise classes | 41,269/43,249 (95.4%) | 36,234/38,113 (95.1%) |
| Mixed-script words | 2,909/3,904 (74.5%) | 2,034/2,738 (74.3%) |
| All new composition cases | 9,974/12,096 (82.5%) | 6,994/8,809 (79.4%) |
| Actual names cut at 32 UTF-8 bytes | 14/255 (5.5%) | 14/255 (5.5%) |

The boundary class includes only candidates that exceeded 32 bytes before
truncation; it drops a partial final code point, never emits invalid UTF-8, and
does not attribute untruncated short names to that class. Truncation can remove
meaningful letters, so this recall figure does not prove all escapes are copies.
Recommendation: retain current rules pending an owner-approved precision study.
Full output is in `EVASION_BENCHMARK_REVIEW.md` and the corresponding data JSON.

## Implemented owner rulings, 8 November 2026

A is fixed. Text routing consults only the current live NameLock holder, never a
revived former holder's reserve or tier. The exact-identity SlugLock remains an
on-chain restriction: when a candidate has a name key, its live identity holder
must also be its current live name holder. Conflicting live locks refuse with
409 `slug_name_conflict`; the service does not sign a door into the former holder.
Names without a name key retain the identity floor. The independent decision
verifier follows the same precedence. Ordinary regressions failed on service
`f2f8451` before this change and pass with it.

B is fixed in the paired program. The default build refuses graduation triggers
above 85,018,013,680 lamports. Only the isolated `test-stress` feature accepts
120 SOL. A permanent two-sided SBF test asserts refusal in the default build and
acceptance in that feature build; existing room caps stay immutable.

D uses exact sparse u128 hourly volumes and deferred unused vaults. RPC scans
filter Room by discriminator, then strictly validate the two permitted lengths,
bucket count and layout. Active IDL/layout pins match the paired program.
Historical B/D control is program `816b38d`; the owner authorized independent
reviewer execution against that commit. No deliberately failing historical
control is committed on either candidate branch.

Liveness thresholds and evasion normalization remain owner decisions. They were
not changed by these rulings.

The complete program measurements and owner tradeoffs are in the paired branch's
[security review](https://github.com/Arriived/bonding-curve/blob/claude/paired-doors/program/docs/SECURITY_REVIEW.md).
Service validation: 163 pytest tests passed, zero failures or expected failures.


## RPC error redaction

A preserved draft test failed for HTTP failures and provider JSON-RPC errors:
exception text included a synthetic authenticated URL marker. Those RpcError
strings flow into public refusal/health messages and refresh logs. The fix keeps
the method, exception class, HTTP status or numeric RPC code, suppressing endpoint
text, provider messages/data and chained transport text. No real credential was
read or used. Both reproductions now pass. The complete service suite passes
163 tests after this fix.


Final program verification, 8 November 2026: [CI 42403905057](https://github.com/Arriived/bonding-curve/actions/runs/42403905057)
passed all 71 SBF tests, 10,000 mixed iterations / 12,488 transactions, offline
SPL and source/IDL/ELF pins, heap probe and curve fuzz. Each of 33 doors in four
resource scenarios had a positive position and fee credit and fully exited and
claimed. Measured upkeep is 0.02002 SOL per room/day; 2.002 SOL for 100 rooms
using the same unbatched transaction pattern. The program-fee floor is 0.02 SOL
per room/day (2 SOL for 100); cross-room batching can reduce network overhead.
The 0.5 SOL reserve floor per room is recoverable capital, separate from rent,
bootstrap fees and the temporary 1.2625 SOL gross maintenance buy. The program
and service IDL files match emitted output byte-for-byte. Final service tests:
163 passed. The repeated benchmark produced identical JSON.


## Operator diagnostics

Public RpcError text retains safe method, class, HTTP status or numeric RPC code.
Full transport exceptions and provider error details are emitted only at DEBUG
on `matcher.rpc.internal`. Operators can attach a private handler and enable that
logger when investigating a failure; DEBUG is disabled under the default INFO
configuration. Neither `/health` nor `/route` serializes those records. Synthetic
HTTP and JSON-RPC marker tests prove both internal availability and response
redaction. No real endpoint credential was accessed.

Current service validation: 170 tests pass, without xfail or skipped desired-policy
assertions. The final program run and updated benchmark are recorded below once
verification completes; earlier results above describe the previous candidate.


Repeated final benchmark: 1,223 targets, byte-identical JSON to the prior review
(SHA-256 `2c09b97bb1b6e029b03b0b0eadce2023d62bd839d64d1be604a3fc71cea211a4`).
Mixed-script catch rates remain 74.5% with the symbol kept and 74.3% fuzzed;
actual 32-byte truncations remain 5.5%. Rules are unchanged. Final mocked pytest
run passes 170/170. Service code under test is `028e57e`; data hashes identify it.


Final owner-ruling program verification is green:
[42526798488](https://github.com/Arriived/bonding-curve/actions/runs/42526798488)
on `86a0f44` passes 71 SBF tests / 10,000 iterations, both cap directions,
isolated stress exits, pinned SPL bytes, heap, 400,000 curve cases, client checks
and the production ELF pin. Every source hash and emitted IDL matches the
candidate; the service's paired IDL matches byte-for-byte. Findings 4 and 7 are
Fixed. Birth rent is 26,959,560 -> 17,515,840 lamports (35.0% saved), missing the
15 million target by 2,515,840. Creation heap rises 2,960 -> 4,080 bytes; its
matching worst-case CU rises 328,089 -> 351,341. First-use vault costs are deferred,
not eliminated. Remaining birth accounts and immutable metadata need further
compaction to reach the target. Program before/after evidence names control
`816b38d`; historical B/D negative controls are assigned to the reviewer, not
claimed as executed locally. Final service tests on `bf121dc`: 170 passing.


## Launch CU budget blocker: Fixed (8 November 2026)

Control `b86ae42` used 400,000 CU. The new config/message test first failed on
that default (the explicit override passed), then both passed after the default
became 500,000. Test fixtures, the e2e launch config and max_uri.py use the new
budget; deployment or signing material is not needed for these checks.

Current worst launch is 351,341 VM transaction CU, not the old 306,979 value.
Rounded drift arithmetic gives 402,341 and 97,659 margin. The enforced allowance
uses exact historical 21,110 plus 7,500 variance, 15*1,500 extra bump work and the
150-CU priority-price instruction: **402,601 total, 97,399 CU margin**. Both SBF
max-launch/takeover assertions and the heap probe check the allowance. The pinned
SPL suite already includes its token binaries; this historical allowance is
additional conservative headroom, not a new live-runtime measurement.

At example cu_price 10,000 micro-lamports/CU, the 500,000 limit charges 5,000
lamports of priority fee (0.000005 SOL), versus 4,000 previously. It uses requested
limit, per [Solana fee documentation](https://solana.com/docs/core/fees).

`data/launch_cu_packet_sizes.json` compares both budgets and records identical
packet lengths. Name 32/symbol 10 URI limits are 35/3/200/194 bytes for fresh
creation/one-holder creation takeover/open/open takeover. At their respective
boundaries wire size is 1,232 bytes except plain open (1,206). Full URI 200
creation remains 1,397 bytes and does not fit; two-distinct-holder creation also
does not fit even with URI zero. The service's packet refusal is retained.
Production program source and the 35% birth-rent saving are untouched.


Service candidate `6109176` passes 172/172 mocked pytest tests. The full repeated
benchmark has the same 1,223 targets and byte-identical JSON (SHA-256
`2c09b97bb1b6e029b03b0b0eadce2023d62bd839d64d1be604a3fc71cea211a4`).
The local 400,000-case curve run also passes. Rules and the birth rent are unchanged.
Final pinned-SPL SBF/heap evidence is linked below.


Final launch-budget CI [42536522731](https://github.com/Arriived/bonding-curve/actions/runs/42536522731)
is green on program `0849033`: 71 SBF tests, 10,000 mixed iterations, pinned SPL
binaries, cap feature checks, heap, 400,000 curve cases, client checks and unchanged
`d1fb4975` production binary pin. The maximum heap fixture confirms 402,601 stressed
CU, leaving **97,399 CU** under 500,000. Birth rent remains 17,515,840 lamports.
Service `6109176` passes 172/172 tests; the full evasion JSON repeats identically.
The config/message regression's pre-fix control is `b86ae42`; all committed
candidate tests pass. Data and hashes: `data/launch_cu_budget_checks.json`.


## Compact reserve guard

`Launch.max_reserve_lamports` carries an eight-byte u64. Both launch paths check
accounted reserve before pending fee settlement and the first buy. Zero disables
this cap. For a first buy with an omitted cap, the matcher uses the snapshot's
pre-settlement reserve `R` and the chosen slippage `b` in basis points:

`floor(sqrt((v_sol + R)^2 * (10_000 + b) / 10_000)) - v_sol`

The derived result is bounded by the configured graduation trigger and has a
one-lamport minimum to preserve the zero sentinel. An explicit cap, including
zero, passes through. The first-buy minimum remains in door tokens.

The nominal price `(v_sol + R)^2 / (v_sol * v_tok)` strictly increases for
positive virtual reserves. The exact on-chain spot uses sold tokens. The rounded
inverse can leave sold unchanged as reserve increases, and cash rounding can
leave surplus reserve. The guard enforces the chosen accounted-reserve policy.
Tests cover the nominal formula and quote boundaries, the exact spot's
nondecreasing behavior along the rounded inverse at validated Config extremes,
and pre-settlement ordering and front-run rejection in SBF.

The two eight-byte launch discriminators are versioned so earlier signed price
payloads cannot execute with reserve semantics. The independent verifier still
reads historical price-bound decisions. Requests that omit the cap preserve
the v1 signature domain and null slot. An explicit reserve cap uses the v2
signature domain so a previously signed absolute price cannot authorize it.


## Launch metadata packet budget

The 1,232-byte transaction limit gives name, symbol and URI a shared UTF-8 byte
budget. These measurements include both signatures, a 500,000-CU limit and the
priority-price instruction. The v0 column uses a static lookup table for Config,
Token-2022, classic SPL Token, the WSOL mint, ATA and System. The program's
individual metadata maxima sum to 242 bytes, so larger packet budgets still
have at most 242 usable metadata bytes.

| Shape | Legacy before | Legacy after | v0 before | v0 after |
|---|---:|---:|---:|---:|
| Creation | 77 | 85 | 227 | 235 |
| Creation with a SlugLock takeover | 45 | 53 | 195 | 203 |
| Open | 268 | 276 | 356 | 364 |
| Open with a SlugLock takeover | 236 | 244 | 324 | 332 |
| Creation with a NameLock takeover | 45 | 53 | 195 | 203 |
| Creation with two distinct holders | 13 | 21 | 163 | 171 |

A single old holder shared by both locks costs the same packet bytes as a
one-holder takeover. At name 32 and symbol 10, legacy creation allows URI 43,
a one-holder takeover allows 11, and both open shapes allow 200. Two distinct
old holders leave 21 bytes for all three metadata strings. The earlier legacy
creation budgets before the 16-byte price field were 93 and 61 bytes for plain
creation and one-holder takeover, respectively.

The 90-byte example `Pepe Wif Sword` / `SwordPepe` with a 67-byte URI is still
1,237 bytes with priority pricing and fails the legacy size check. Until v0
lands, the frontend must use short metadata URIs. Target about 25 bytes and
apply the combined limit for the actual shape. A one-holder takeover with a
25-byte URI leaves 28 bytes for name plus symbol. Two distinct holders need
shorter metadata.

**M-7 lookup-table integration is a pre-mainnet blocker.** At name 32 and symbol
10, the static v0 table allowed URI 185 for plain creation and 153 for a
one-holder takeover with the old field. The compact field raises those limits
to 193 and 161. This is the path for standard-length metadata URIs. The service
still signs legacy messages. Its `max_uri.py` measures both formats, and SBF
asserts the packet budget and the first overflowing byte for every shape.
