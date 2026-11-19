# Follow-up security sweeps — 2 November 2026

Two economic security findings were reproduced against the compiled SBF at
`436c002`, in [CI run 41476291249](https://github.com/Arriived/bonding-curve/actions/runs/41476291249).
Passing witness tests in that run confirmed vulnerable behavior; they did not
mean the findings were fixed. The witnesses are now rejection/loss regressions.
No deployment is part of this work.

## High: permissionless capture of delayed retirement fees

The original witness accumulated 12 SOL of reserve-directed fees through 100
ordinary room-token round trips. An independent user then bought temporarily,
retired those pending fees, and sold all acquired tokens in one transaction.
The transaction earned 9,790,783,910 lamports after its network fee and ended
with zero tokens. No admin, matcher signature, forged balance, or accounting
invariant violation was needed in that attack.

Every buy now settles the existing pending reserve fees **before** computing
the buyer's quote and acquiring tokens. This shared execution path includes
room-token buys, door-token buys and an `open_door` optional first buy.
`create_room` also uses the same path, with an initially empty pending counter.
Settlement uses only accounted fees, respects the room's immutable cap, and
transfers tokens to the canonical retired vault. Claims and donations remain
outside its funding source. A buyer's own fee is still split after the trade.

Regressions exercise the same 12 SOL legacy backlog on both buy routes and
require the atomic temporary position to lose money and finish with no tokens.
The legacy state is explicitly seeded and reconciled: the fixed trade ordering
prevents the old round-trip setup from accumulating that backlog. Separate
tests execute 100 new round trips, optional first buys, exact quotes and failed
slippage limits. Failed buys must roll back settlement and token movement too.

If settlement consumes the entire remaining cap, the buy fails atomically;
permissionless `retire_pending` can commit settlement separately. Holders can
still sell at the cap. Existing-holder gains from intended retirement and
ordinary trade ordering remain part of the economics; this fix removes buying
a new position at a price that excludes already-accounted retirement fees.

## High, privileged: signed launch economic snapshot race

A Config admin could change the immutable economics copied into a new room
after both launcher and matcher signed. The prior flat-fee ceiling and minimum
token output did not bind future redemption fees or the curve. The unchanged
signed witness still met its minimum token output after the admin halved the
virtual SOL reserve and raised the trading fee from 100 to 9,999 bps. The
victim's 1.01 SOL first buy redeemed for only 50,502 lamports before its network
fee. The configured recipient collected 1,009,949,498 lamports of protocol fees.
This required Config admin authority, but no program upgrade.

`create_room` now checks `Launch.expected_terms_hash` against the current Config
before handler-side mint creation or first-buy execution. A mismatch returns
the appended `LaunchTerms` error, preserving old error codes. The commitment
binds every copied economic field: virtual SOL, virtual tokens, supply, R-star,
graduation trigger, trading fee, door share and founder share. A refreshed
instruction and both new signatures are required after a change.

Regressions verify the original transaction bytes and signatures stay unchanged,
require `LaunchTerms`, and compare every non-payer account to its prior state.
Each independently mutable economic term is tested for rejection and successful
creation with refreshed terms. Supply is fixed by Config validation. The
existing flat-fee rejection and equal/lower-fee tests remain applicable.

The commitment intentionally excludes flat fees, which have a separate signed
maximum, and operational settings such as pause, matcher, liveness thresholds
and protocol recipient. Those remain privileged, mutable controls. Existing
rooms retain their economics; `open_door` uses that immutable room snapshot.

## Client migration

Use the updated IDL. Account data layouts remain unchanged. The shared Core
context now marks `retired` writable, so rebuild instruction account metas.
`Launch` appends a 32-byte `expected_terms_hash`. For creation it is required,
including a zero-spend launch. Zero or missing bytes do not disable the check.
Opening a door must encode the appended field, but it is unused because room
economics are already immutable; zero bytes are suitable there.

Compute SHA-256 over the concatenation of the ASCII domain
`doors-v1:launch-terms:v1` and these unsigned, little-endian fields in order:

| Fields | Width each |
|---|---:|
| `v_sol_lamports`, `v_tok`, `supply`, `r_star_lamports`, `graduation_trigger_lamports` | 8 bytes |
| `fee_bps`, `door_share_bps`, `founder_share_bps` | 2 bytes |

`scripts/launch_terms_hash.py decoded_config.json` computes the instruction's
byte array without dependencies. Use exact integers or decimal strings.
Quotes for existing rooms must simulate pending retirement before computing
buy output, and keep the user's minimum output in the signed instruction.

## Additional review passes

The regression suite retains 36 cross-room conversion/claim substitutions,
unauthorized Config and recipient changes, open-door CPI rejection, atomic
rollback of a buy/conversion/failed-sell sequence, repeated completion/retirement/
conversion/exits and 20,000 independent inverse/fee arithmetic comparisons.
These passes have not identified an additional confirmed custody bypass.
Graduation and pool execution remain unimplemented. This is focused internal
review and regression coverage, not certification that every bug is absent.
