# Program-v1 preflight corrections

Status: the owner approved surplus-tolerant accounting and signed random room
nonces on 1 November 2026. Those decisions are implemented in the Anchor program
and recorded in spec section 0.C. Build/test/CU results are recorded separately;
the algebraic examples below are not execution measurements.

## Approved: permissionless transfers and burns

The spec requires ordinary Token-2022 mints, without freeze authority or a
transfer hook. A holder can transfer into a program-controlled token vault
without its owner's signature. Returning a door token to DoorVault changes
one side of B1 without moving its room-token backing. Returning a room token
to RoomVault changes one side of S1 without changing the stored sold state.
An implementation that rejects these states can be denied service by a holder.

The spec explicitly permits holder burns in section 4, but M1 in section 8
requires mint supply to remain equal to the initial supply. A holder burn
reduces mint supply while leaving the vault-based backing invariant intact.

Reproduce the counterexamples with:

```text
python program/scripts/check_spec_conflicts.py
```

The generated [counterexamples](../verification/spec_conflicts.md) use the
spec's actual integer buy formula. They are algebra, not executed Token-2022
transactions or a replacement for the requested invariant/property tests.

Approved policy: retain sold/backing as accounting liabilities; vault balances
must be **greater than or equal to** those liabilities. Initial mint supply is
exactly U; subsequent supply is at most U. Prices, payouts, available inventory,
claims and retirement use only program counters. Token balances are used only
for validation, liability coverage and exact transfer deltas. Surplus remains
locked, including at the future graduation seam; there is no sweep or automatic
retirement of donations. The audit reconciles external donations and burns.
No CPI work is spent correcting these safe-direction differences.

## Approved allocation rule: room identifiers

Room and SlugLock use a room identifier, but create_room has no identifier
argument and Config has no identifier allocator. create_room now takes a
matcher-selected CSPRNG u64 nonce, covered by the whole signed transaction.
Config stays read-only; there is no global creation counter. The client must
request a new nonce and fresh signatures after an occupied-PDA failure. Never
derive the nonce from a slug, since dead slugs may be reused. Room IDs are not
enumerable; indexers use getProgramAccounts for rooms as well as doors.

## Resolved by the authoritative spec

- The brief's lamport-delta test names RoomVault. The spec identifies that
  account as a Token-2022 token account; I2's SOL equality is for ReserveVault.
  Test ReserveVault lamports and the room-token vault balance separately.
- The founder wording in the brief predates the approved present-but-zero
  update. Follow the current spec's founder fields, SOL/WSOL counters,
  immutable fee snapshot and zero default.
- retire_pending must compute its capped amount from the pre-transfer reserve,
  transfer only that amount, decrement pending by the same amount and mark
  the room complete if it reaches its copied trigger. This gives the stated
  cap and completion seam effect without debiting excess fees first.
- D1 must describe structural/identity immutability while allowing the fee,
  backing and volume updates explicitly required by the instruction sections.
  Its literal prohibition on all Door changes contradicts those instructions.

## Build environment

The Windows environment has no Rust, Solana or Anchor command on PATH, and WSL
is not installed. Current Agave no longer ships Windows prebuilts. The isolated
program branch therefore uses Linux GitHub Actions for compilation and SBF
execution. This does not deploy a program or send devnet/mainnet transactions.

## Implementation clarifications

- A first buy inside create_room/open_door needs its user ATA created after
  the new mint exists. The handler uses the canonical ATA program's idempotent
  creation CPI before that optional buy. This is atomic with metadata, premint,
  authority revocation and trade; a preceding instruction cannot create an ATA
  for a mint that does not exist yet.
- The fixed Room layout has no aggregate door-fee counter. Global fee backing
  is preserved inductively: every affected instruction asserts an exact match
  between FeeVault movement and its touched liability-counter changes, starting
  from zero. It also checks coverage for room liabilities and the touched doors.
  Execution tests enumerate all doors and assert the full global inequality.
- Phase 2 cannot be reached by v1. Status-2 pool operations and liveness checks
  fail closed pending the graduation/pool adapter, instead of inventing a pool
  activity rule. The future implementation must preserve the same gate.
- LiteSVM 0.18.1's loose dependency ranges select incompatible Agave 4.4
  APIs and fail to compile. Its official upstream lock at
  `aff262da627cbd6dfef24d24fb435fbaa5e61bc4` provides the supported 4.3.2 VM
  pairing. Cargo.lock retains that test runtime; the program's Solana build
  target/CLI stays at current stable 4.4.0. VM measurements identify the
  actual runtime rather than implying a 4.4 validator benchmark.
- Runtime tests caught a construction error: creating every fresh PDA with
  transfer + allocate + assign consumed the instruction-trace limit during
  an optional first buy. Fresh PDAs now use the single System create_account
  CPI. Prefunded PDAs retain the allocate/assign fallback, with redundant
  zero-byte allocation and same-owner assignment omitted. This is account
  initialization, not repair or redistribution of existing vault surplus.
- Test setup corrections: LiteSVM's airdrop payer cannot send its entire
  balance because the transfer also pays a transaction fee; fixture funding
  was reduced. LiteSVM loads token programs without creating the canonical
  native WSOL mint account; the fixture now supplies that initialized account.
  No production mint or economics was changed to accommodate a missing fixture.
- The final spec audit caught an implementation API mismatch: the draft emitted
  TradeEvent with sold and omitted price_after. The event is now the specified
  Trade with sold_after and an exact u128 numerator/denominator price. This
  adds no floating-point calculation and reads only room counters/constants.

The research measurement remains in the original worktree and is not modified
by this isolated program branch.

The follow-up [program review](BUG_SWEEP.md) records the buy-fee volume
correction, stronger rejection/rollback tests and CI source-integrity fix.

## Devnet deployment preflight (4 November 2026)

Found while preparing the devnet deployment. Details, signatures and hashes are
in [DEPLOYMENT.md](DEPLOYMENT.md).

1. **The branch tip does not pass its own tests.** At `8ce373f` ("Bind launch
   economics and settle retirement before new buys"), 10 of 38 SBF tests fail,
   on a pristine checkout with the original test program ID. Every failure is
   the runtime's `UnbalancedInstruction` ("sum of account balances before and
   after instruction do not match") inside `buy`/`open_door`, after the new
   `settle_pending` moves lamports from FeeVault to ReserveVault. Not fixed
   here: it is program logic, outside a deployment task.
2. **The brief's commit is not the newest passing commit.** The brief names
   `054be58` (16 SBF tests, passing here). `436c002`, the parent of the tip,
   passes all 34 tests and carries every audit fix between them. Its program
   code is identical to `f6eb007`: built here, its ELF SHA-256 equals the
   hash CI recorded for `f6eb007`. **Deployed: `436c002` plus only the
   program-ID change** (`verification/devnet/deployed_source.patch`). The
   program is upgradeable, so a fixed tip can replace it under the same ID.
3. **The deploy client targets the deployed source, not the tip.** The tip adds
   `Launch.expected_terms_hash`; `program/devnet` builds against `436c002`'s
   `Launch` and needs that field added when the tip is redeployed.
4. **No verifiable build image exists for the pinned toolchain.** As of
   4 November 2026 the newest `solanafoundation/solana-verifiable-build` tag is
   4.3.0 (not 4.4.0) and the newest `solanafoundation/anchor` tag is v1.0.2
   (not 1.2.2). A `solana-verify` build would use a different toolchain from
   the declared build target. Instead: the pinned build reproduces byte for
   byte across machines and directories (item 2), and the deployed bytes are
   compared with the local ELF by hash after deployment.
5. **The devnet RPC faucet is closed** (`requestAirdrop` returns
   `410 "The RPC faucet is closed on this cluster"`). The web faucet asks AI
   agents to use programmatic methods. The owner's three GitHub accounts were
   refused by the web faucet (per-8-hour limit, or accounts too new or with too
   few public repos). With the owner's approval the proof-of-work faucet was
   reviewed: its client (`devnet-pow` 0.1.4) does not compile on Rust 1.99, and
   on-chain at slot 518,709,929, 23 of the program's 24 faucets are empty. The
   one funded faucet pays 100 lamports per claim, below the 5,000-lamport fee.
   Devnet SOL has to come from a person; the devnet deployment and the devnet
   end-to-end test are pending until then.
6. **Cluster rent is now 5,080 lamports per byte** (Rent sysvar:
   `lamports_per_byte_year` 5,080, `exemption_threshold` 1.0, on devnet at slot
   518,695,292 and mainnet at slot 465,433,975), not 6,960. The program reads
   rent from the sysvar, and this branch's curve quantities already use the new
   rate (graduation rent 18,013,680; trigger 85,018,013,680). A local
   `solana-test-validator` still uses 6,960, so its rent figures differ.
7. **VM CU depends on the program ID.** Re-running the SVM suite on the same
   code with the deployment ID moved the measured maxima (buy_door
   75,189 → 71,380; convert 88,715 → 85,715), because PDA bump searches depend
   on the program address. The live comparison uses VM figures from the
   deployed ELF itself (`verification/devnet/deployed_elf_vm/`).
8. **An oversized sell is rejected by Token-2022, not by the program.** The sell
   fails atomically with Token-2022 `InsufficientFunds` (custom error 1) from the
   transfer CPI; the program has no balance check of its own first. Safe, but
   clients see a token-program error rather than a doors error code.
9. **The VM CU maxima are not worst cases.** Live localnet runs of the same
   ELF exceeded the VM maximum for some instructions: `buy_room` by 3,027 CU,
   and `open_door` and `buy_door` by about 1,700. Other instructions in the same
   run came in up to 12,272 CU below. Per-step figures differed between runs.
   This is consistent with PDA bump-search cost varying by address, since each
   run uses a fresh random room nonce, while the SVM suite measures one fixed
   room ID. The throughput headroom derived from `verification/cu.md` needs
   margin above those maxima.

## Pre-audit program changes (5 November 2026)

### The broken branch tip, and its fix

- **What was broken.** At `8ce373f`, 10 of 38 SBF tests failed with the runtime's
  `UnbalancedInstruction` ("sum of account balances before and after instruction do not match").
- **The cause.**
  1. The tip's new `settle_pending` debited FeeVault and credited ReserveVault by direct lamport
     edits.
  2. `buy` then made a System Program CPI depositing into ReserveVault.
  3. The runtime syncs a caller's lamport edits only for accounts passed to that CPI. ReserveVault
     was passed and FeeVault was not, so the CPI saw ReserveVault up by `n` with no matching
     decrease.
  4. The retirement token transfer inside `settle_pending` passes neither vault, which is why it
     succeeded.
- **The fix (`6385fdd`).** `settle_pending` does the accounting and the retirement transfer and
  returns the lamports to move. `execute_trade` applies FeeVault → ReserveVault after its last CPI,
  as the sell path already did for its own debits; `retire_pending` applies it directly, with no
  CPI after.
- **One stale test expectation.** `direct_donations_and_holder_burns_preserve_coverage_and_quotes`
  predated the tip's own settle-before-buy rule. It now expects settle, then advance. The tip
  author's `sweeps.rs` changes already encoded that rule.
- **Result:** 38 of 38 tests pass, including the 10,000-iteration property test. The IDL is
  unchanged by the fix.

### Door addresses from a signed nonce (matcher service correction 3)

- **The change.** `Launch.door_nonce: u64` seeds `["door", room, nonce]` and
  `["door_mint", room, nonce]`.
  - Door 0 uses nonce 0, and `create_room` rejects anything else (`DoorNonce`).
  - `open_door` requires a non-zero nonce. Nonce 0 resolves to door 0's existing address, so `init`
    fails first.
  - `Door.nonce` is stored in former reserved bytes (`Door` stays 328 bytes; `account_sizes.py` is
    updated), and `DoorOpened` appends `nonce`.
- **What still reads `door_count`:** only `initialize_door`, which records `Door.index`, increments
  the count, and writes the `("door", index)` metadata label.
  - Concurrent opens into one room still serialise on the room's write lock and get distinct
    indices.
  - No address depends on either.
- **The matcher service:** it reads a room's door count from `DoorOpened` events and orders faces by
  `Door.index`. Both still hold: every door, door 0 included, emits one `DoorOpened`, and indices
  stay contiguous.
- **Tested in SBF:**
  - two opens built against the same room state land in either order;
  - a dropped open blocks nothing;
  - a nonce collision fails with no state change;
  - nonce 0 cannot open a door;
  - `create_room` with a non-zero nonce fails with `DoorNonce`.
- **Correction to the spec's verification path.** The spec said a door is verified by checking its
  `("door", index)` metadata against `["door", room, index]`. That no longer holds, because the
  address comes from the nonce. Door mint metadata is unchanged in this task, since adding the nonce
  would change mint sizes and rent. Verification now goes through the `Door` account: find it by its
  `mint` field, then check `["door", room, door.nonce]` (spec §0.F and its verification bullet).
  **Owner decision:** whether door metadata should also carry the nonce.

### Explicit launch expiry (matcher service correction 1)

- **The change.** `Launch.expires_at_slot: u64`. `create_room` and `open_door` reject (`Expired`)
  in either of two cases:
  - the executing slot is past `expires_at_slot`;
  - `expires_at_slot` is more than `MAX_LAUNCH_WINDOW_SLOTS` = 150 slots ahead of it.
- **Why 150.** It is the runtime's recent-blockhash window (`MAX_PROCESSING_AGE`, `solana-clock`
  4.0.0). The matcher sets `expires_at_slot` = its blockhash's slot + 150. Slots advance at least as
  fast as block heights, so the explicit expiry is never later than the blockhash's. The upper cap
  makes a misconfigured, far-future expiry unusable rather than long-lived.
- **What it closes:** a co-signed launch kept alive by a durable nonce past its window. The matcher
  service's localnet e2e test demonstrates it: a durable-nonce launch, still valid to the runtime,
  is rejected on-chain with `Expired`.
- **What it does not close:** a compromised matcher key can still sign fresh launches, with any
  window, at any time it holds the key. The remedy for that is rotating `Config.matcher_authority`.
  Rotation invalidates every launch signed by the old key, held ones included, because the program
  checks the signer against Config at execution.
- **Tested in SBF:** inclusive at the current slot; one slot late fails; 151 slots ahead fails;
  exactly 150 ahead succeeds; a launch held past its expiry fails. All on both launch paths.

### Verification of this change set

- **Program tests:** SBF suite 41 of 41, including the 10,000-iteration property test. The IDL
  matches `anchor idl build` byte for byte, `check_layouts.py` passes, and `cargo fmt` is clean.
- **Dependency audit not re-run.** `scripts/audit_dependencies.py --check` needs `api.osv.dev`,
  which this environment's proxy refuses (403). The lockfiles are byte-identical to those the
  recorded audit covers: Cargo.lock `1f20992f…0a5`, launch_proxy `e98c1572…eba`. These changes add
  no dependency.
- **Program e2e (`devnet/e2e.sh`, localnet):** 33 of 33 checks, deploying the repinned ELF
  `36e22dab…3b31` through `deploy.sh`.
- **The pin check works both ways:** under the old pin, `deploy.sh` refused the new ELF and named
  both hashes.
- **Devnet:** still pending funding.

**VM CU, same suite, before (deployed `436c002` ELF) → after (this ELF),** in min–max CU per
instruction:

| instruction | before | after |
|---|---|---|
| buy_door | 66,677–71,380 | 62,616–75,550 |
| sell_door | 64,089–68,603 | 59,704–63,530 |
| buy_room | 45,722–46,147 | 46,106–55,099 |
| sell_room | 43,276–43,776 | 43,285–43,785 |
| convert | 81,205–85,715 | 75,311–78,270 |
| open_door | 118,833–121,715 | 118,610–130,159 |

**What drives the changes:**

- **The higher buy maxima** (buy_room +8,952, buy_door +4,170) come from the tip's own
  settle-before-buy: a buy with pending fees now performs the retirement transfer CPI. The two
  changes in this task add one Clock read and the nonce checks to the launch paths only.
- **The other movements** are consistent with PDA bump-search cost. It varies with every address,
  so it moves with any change to seeds, here the door nonce. The VM suite measures fixed fixture
  addresses, and live localnet runs earlier fell both above and below the VM maxima
  (`services/matcher/CORRECTIONS.md` §9 on that branch). **These maxima are not worst cases.**

**Throughput headroom.** The execution-only ceiling for the heaviest trade moved from 279 (convert)
to 306 (convert) per room per block. buy_door went from 336 to 317, buy_room from 520 to 435, and
open_door from 197 to 184. The binding trade ceiling did not fall, so headroom did not materially
change. The ceilings carry the same bump-search caveat.
