# Paired doors prototype report

The prototype runs each door on a constant-product curve quoted in room
tokens. The virtual quote is fixed at launch using 30 SOL at the room spot
price. Buys and sells use both curves in one instruction. Same-room swaps
use room tokens and leave room SOL reserves and the room's sold count
unchanged. Door 0 uses the same mechanism. The room and door mints retain
the room's launch metadata relationship.

## Default-room measurements

<!-- BEGIN GENERATED STATUS -->
Source commit `311d43ac63edfccb6e0003e90fe4fc215c8ed90a`. [Linux verification](https://github.com/Arriived/bonding-curve/actions/runs/42754852665).

The SBF suite passed 73 tests, including 10,000 property iterations and 12,488 executed transactions. The standalone devnet client tests also passed.

The deployed Token-2022, SPL Token and ATA binary hashes matched the pinned capture. Their verification read was at finalized slot 519,096,745.

Compiled ELF SHA-256 is `fc2d615e37c63710326e18a29d157b50b0ad678ef9083e3161007bf43e8e9002`.
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
Each row is the maximum CU sample for that fixture and instruction. Program CU includes CPIs.
Transaction CU also includes the compute-budget instructions. Property-run samples record program CU.

| SBF fixture | Instruction | Prefunded | Priority fee | Program CU | Transaction CU | Trace entries |
|---|---|---|---|---:|---:|---:|
| launch_instruction_trace_budget | create_room | True | True | 340,607 | 340,907 | 46 |
| launch_instruction_trace_budget | create_room_split_takeover | True | True | 321,800 | 322,100 | 44 |
| launch_instruction_trace_budget | create_room_takeover | True | True | 321,608 | 321,908 | 44 |
| launch_instruction_trace_budget | open_door | True | True | 276,313 | 276,613 | 33 |
| launch_instruction_trace_budget | open_door_takeover_with_retirement | True | True | 242,041 | 242,341 | 33 |
| mixed_10000_sbf_operations_and_cu_report | buy_door | False | False | 108,011 | — | — |
| mixed_10000_sbf_operations_and_cu_report | claim_door_swap_fees | False | False | 39,765 | — | — |
| mixed_10000_sbf_operations_and_cu_report | claim_protocol_swap_fees | False | False | 31,742 | — | — |
| mixed_10000_sbf_operations_and_cu_report | create_room | False | False | 228,246 | — | — |
| mixed_10000_sbf_operations_and_cu_report | open_door | False | False | 150,237 | — | — |
| mixed_10000_sbf_operations_and_cu_report | sell_door | False | False | 61,081 | — | — |
| mixed_10000_sbf_operations_and_cu_report | swap_doors | False | False | 92,330 | — | — |
| paired_door_trade_limits_and_launch_rent | buy_door | False | True | 91,712 | 92,012 | 9 |
| paired_door_trade_limits_and_launch_rent | buy_room | False | True | 52,518 | 52,818 | 6 |
| paired_door_trade_limits_and_launch_rent | claim_door_swap_fees | False | True | 39,765 | 40,065 | 4 |
| paired_door_trade_limits_and_launch_rent | claim_protocol_swap_fees | False | True | 31,742 | 32,042 | 4 |
| paired_door_trade_limits_and_launch_rent | sell_door | False | True | 58,078 | 58,378 | 5 |
| paired_door_trade_limits_and_launch_rent | sell_room | False | True | 38,911 | 39,211 | 4 |
| paired_door_trade_limits_and_launch_rent | swap_doors | False | True | 109,130 | 109,430 | 11 |
| paired_door_trade_limits_and_launch_rent | swap_doors_existing | False | True | 83,795 | 84,095 | 7 |
| takeover_heap_case / 200-byte URI | create_room | True | False | 331,718 | 331,868 | 44 |
| takeover_heap_case / 200-byte URI | open_door | True | False | 250,832 | 250,982 | 33 |
| takeover_heap_case / 70-byte URI | create_room | True | False | 330,706 | 330,856 | 44 |

Maximum measured transaction CU was 340,907.
Maximum measured program CU was 340,607.
<!-- END GENERATED CU -->

## Creation before and after the review

<!-- BEGIN GENERATED CREATION -->
Before is [915b075](https://github.com/Arriived/bonding-curve/actions/runs/42378291009). After is 311d43a.
The heap fixture uses maximum metadata and prefunded accounts. Rent uses the same rent-only metadata in both runs.

| Measurement | Fixture | Before | After | Change |
|---|---|---:|---:|---:|
| Additional heap bytes | heap_probe_worst_case_launches / create_room | 64 | 4,304 | +4,240 |
| Program CU | heap_probe_worst_case_launches / create_room, instrumented build | 337,430 | 350,756 | +13,326 |
| Transaction CU | heap_probe_worst_case_launches / create_room, instrumented build | 337,580 | 350,906 | +13,326 |
| Room creation including door 0 rent, lamports | paired_door_trade_limits_and_launch_rent | 28,407,360 | 17,515,840 | -10,891,520 |

An additional door uses 7,350,760 lamports of rent.
The first swapping user pays 1,488,440 lamports for the room-token fee vault.
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


## Compact reserve guard

`Launch.max_reserve_lamports` carries an eight-byte u64. Both launch paths check
accounted reserve before pending fee settlement and the first buy. Zero disables
this cap. For a first buy with an omitted cap, the matcher uses the snapshot's
pre-settlement reserve `R` and the chosen slippage `b` in basis points.

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


The service regression measured 1,240 bytes for an 85-byte creation payload on
`a76a35c`. The compact version measures 1,232 and refuses the next byte.
The pinned program passed 73 SBF tests and 10,000 mixed iterations using the
archived SPL binaries. The heap probe measured 4,304 bytes of creation headroom,
and curve fuzz passed 400,000 cases. Birth rent measured 17,515,840 lamports.
The paired IDLs and program source hashes match the verified `fc2d615e` ELF.
The service passed 178 tests on `d2e8f0e` and reproduced its 1,223-target evasion
reference byte for byte. [Pinned verification run 42754852665](https://github.com/Arriived/bonding-curve/actions/runs/42754852665)
