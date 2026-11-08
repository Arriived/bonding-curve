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

Launch appends `max_room_price: u128`, scaled by 10^18 lamports per room base
unit. Zero disables it. Otherwise both program launch paths reject a pre-buy
spot above it. Omission on a first buy fills it from the user's slippage choice,
independently of a custom token minimum. The field is authenticated in the
launcher request, encoded in the transaction, and checked by the verifier.
The NameLock key remains a function of the actual name and symbol only.

The active program ID is read from `idl/doors_v1.paired.json`; active account
lengths are Room 735 at birth / 1,335 after its first buy, and Door 360. Historical deployed interface pins remain
untouched. This is an offline port, not a deployment claim. The added field
costs 16 transaction bytes: at name 32/symbol 10 with priority fee, creation
allows URI 35 bytes, and a one-holder takeover URI 3. Oversized launches are
refused. v0 support remains a separate owner choice.

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
