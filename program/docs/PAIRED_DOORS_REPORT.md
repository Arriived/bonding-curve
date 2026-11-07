# Paired doors prototype report

The prototype runs each door on a constant-product curve quoted in room
tokens. The virtual quote is fixed at launch using 30 SOL at the room spot
price. Buys and sells use both curves in one instruction. Same-room swaps
use room tokens and leave room SOL reserves and the room's sold count
unchanged. Door 0 uses the same mechanism. The room and door mints retain
the room's launch metadata relationship.

## Default-room measurements

<!-- BEGIN GENERATED STATUS -->
Awaiting the full review-fix verification run.
<!-- END GENERATED STATUS -->

| Initial room reserve | A receives after 20 buys | Supplied reference | After a 50% room dump | Dump reference |
|---:|---:|---:|---:|---:|
| 0 SOL | 8.097503855 SOL | 8.10 SOL | | |
| 10 SOL | 7.335805961 SOL | 7.33 SOL | 3.801439748 SOL | |
| 50 SOL | 6.153969291 SOL | 6.15 SOL | 3.133027240 SOL | 3.12 SOL |

A spent 2 SOL. The supplied single-curve vamp comparison is 4.95 SOL
out. All supplied paired-door payout and room-multiple references were
within 1% of the SBF run.

| Initial room reserve | After the follower buys | After A exits | Cash-out | Rotation |
|---:|---:|---:|---:|---:|
| 0 SOL | 2.979255× | 2.112419× | 1.000000× | 2.112419× |
| 10 SOL | 2.385613× | 1.847694× | 1.000000× | 1.847694× |
| 50 SOL | 1.618682× | 1.427006× | 1.000000× | 1.427006× |

The artifact includes the FDV of each door at each step, and the
additional buy, sell and first-swap slippage in basis points against the
single-curve quote. The renderer reads the scenario, limits, trace and
heap files directly.

```sh
python3 program/scripts/report_paired_doors.py <verification_dir>
```

## Compute and trace by SBF fixture

The generated table records program CU and transaction CU separately and
identifies the fixture, prefunding and priority-fee shape. Maximum-metadata
takeover measurements and the mixed-operation samples retain their own rows.
The heap probe compiles temporary instrumentation and its CU appears only in
the creation comparison.

<!-- BEGIN GENERATED CU -->
Awaiting the full review-fix verification run.
<!-- END GENERATED CU -->

## Creation before and after the review

<!-- BEGIN GENERATED CREATION -->
Awaiting the full review-fix verification run.
<!-- END GENERATED CREATION -->

## Supply guard and isolated stress configuration

Under defaults, a generous upper bound puts any door at 98.258853% sold.
The regular suite asserts that bound and reached 97.998907% sold in its
near-exhaustion fixture. The bound derives from the highest permitted
room spot price at birth and the entire room-token output available
before the room cap. Run `python3 program/scripts/check_paired_completion.py`
to reproduce the bound.

The separate SBF stress test owns its Config. The unchanged validator
accepted a 120 SOL cap. The test opens a door at a 100 SOL room reserve.
A 2,477,641,271-lamport buy fit with 7 door-token base units left.
Adding one lamport to that buy from the same starting state failed with
the supply error and preserved state. The nearly sold-out door still
accepted a sell and a swap-out. This configuration is exclusive to the
stress test.

## Devnet status

The prototype's public program ID is
`8tPd1ZUEGxrj5zYu8aeg95cU92nmKWKYKoSaKPqFuZAZ`.
The deploy wallet is
`J57cz21ZzDpcGf7XdF2hQv1NE26NpE4BrGys18EX9QGD`.
The last recorded balance was 26,544,000,361 lamports at finalized slot
519,671,497 after the owner funding and wallet recovery. Devnet rollout
is held pending owner funding. This review pass runs Linux SBF and client
verification.

After a fresh deploy and default Config read-back, the Linux runner's
`paired <keys_dir> <report.json>` command measures the default-room
matrix, sells outstanding test positions, reclaims empty wallet ATAs
and sweeps the test wallets. It expects the smoke launcher, smoke
trader and a separate follower keypair per follower. It writes public
transaction evidence and a recovery checkpoint. The
`paired-cleanup <keys_dir> <interrupted-report.json> <cleanup-report.json>`
command recovers the active case after checking landed transactions
and resolving the interruption. Pass the live report to
`report_paired_doors.py --live` for the VM comparison.

## Decisions and corrections

- The swap fee is provisionally 100 bps of the source curve payout,
  with 60% credited to the receiving door and 40% to the protocol in
  room tokens. The fee policy remains open. The two basis-point constants
  are grouped in `src/math.rs`.
- The first swap creates the canonical room-token fee vault at the swapping
  user's expense. Room creation omits that account.
- `claim_door_swap_fees` pays a door's current `fee_recipient`.
  `claim_protocol_swap_fees` pays the current Config protocol fee recipient.
  Both require that recipient's signature and an existing room-token ATA.
  Claims reduce the room-wide unclaimed total and preserve the vault's
  coverage of every remaining door and protocol liability.
- The owner ruled out a completion threshold in this prototype. The
  [feasibility check](CORRECTIONS.md#paired-doors-prototype-completion-is-unreachable-for-early-doors)
  records why the original threshold exceeded the available room supply.
- Phase 2 still needs a graduation metric and migration design. The
  spec records the crossing trade filling before a migration trigger
  is latched. Trading would continue in a door/room pool.
- Regression fixtures that formerly used room-token amounts as door
  token minimums or redemption inputs now use the paired quote. The
  room reserve debits only the gross curve payout on sale and the fee
  is allocated from that amount.
