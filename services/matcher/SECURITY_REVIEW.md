# Paired matcher review, 7 November 2026

This is the authors' own review, starting at service `9750e03` and program
`2bf6f40`. Tests use synthetic identities, mocked HTTP/RPC and offline SBF
evidence. No deployment or production signing material is used.

| Rank | Severity | Finding | Status | Cost and payoff |
|---|---|---|---|---|
| 1 | High, release blocker | First-buy minimum used room tokens instead of door tokens | Fixed | Ordinary launch; can refuse legitimate fills or leave a weaker minimum. Exact SBF parity now tested |
| 2 | Medium | New-door anchoring bypasses a token-only launch slippage limit | Fixed with owner approval | Recorded 20 SOL front-run earned 0.217061544 SOL and reduced victim exit by 0.549648652 SOL |
| 3 | Medium | RPC failure text disclosed endpoint credentials or provider text | Fixed | Unauthenticated failure-triggering request; possible RPC quota or billing abuse |
| 4 | Medium | Revived former holder can regain text flow despite a successor's live NameLock | Owner decision | Requires a funded room and revival volume; greater depth can regain later launches |
| 5 | Low | Paid liveness permits long-term name carrying | Owner decision | 0.02002 SOL/day with the measured four-transaction pattern, plus setup and recoverable capital |
| 6 | Low | Mixed-script and 32-byte truncation variants evade existing name keys | Owner decision; rules unchanged | New-room rent and ongoing carrying cost; possible routing diversion |
| 7 | Low | Authorized admin can choose the 120 SOL stress cap | Owner decision | One authorized config transaction; no demonstrated direct extraction |
| 8 | Info | Request replay and alteration | Existing M-3 protection confirmed | Concurrent replay accepts exactly one of 32 requests; every changed signed field is refused |

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
lengths are Room 1,331 and Door 360. Historical deployed interface pins remain
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

## Open owner decisions

Revival options are (a) retain depth preference, (b) prefer the live current
NameLock holder for text matches, or (c) add irreversible narrative succession.
Recommendation: (b), preserving exits, after explicitly resolving precedence
against a live exact-identity SlugLock holder. No routing rule is changed.
The passing regression records that the revived deeper former holder currently
wins; it is not an xfail or a deliberately failing desired-policy assertion.

Stress-cap options are (a) retain authorized admin flexibility, (b) enforce an
owner-selected production economic envelope in Config validation, or (c) use a
separate stress build alongside that envelope. Recommendation: (b) and (c).
The current program permits 120 SOL for future rooms and leaves existing room
caps unchanged; no cap restriction is implemented here.

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
