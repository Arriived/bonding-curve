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

**Throughput headroom.** The per-room count at the observed maximum (not a ceiling; see the 5 November follow-up below) for the heaviest trade moved from 279 (convert)
to 306 (convert) per room per block. buy_door went from 336 to 317, buy_room from 520 to 435, and
open_door from 197 to 184. The binding trade ceiling did not fall, so headroom did not materially
change. The ceilings carry the same bump-search caveat.

## Pre-audit loose ends and self-review (5 November 2026, later)

Program source commit `1558b2e`, test commit `805bae3` (same program source), deploy ELF
`34d4ce91…d9e`. Evidence and docs follow in a separate commit that changes no source. The findings and coverage are in `SECURITY_REVIEW.md`;
this section records what differed from what earlier documents said.

**1. Door mints were not self-describing.**
- **What was wrong:** after the nonce change, `("door", index)` no longer located the Door.
- **Change:** door mints now also carry `("door_nonce", <u64 decimal>)` and
  `("program", <program id>)`. Room, nonce and program derive the Door PDA from the mint
  alone. This is a locator, not a proof (spec §3, Mints).
- **Rent:** +97 bytes per door mint at a 20-digit nonce, which is +492,760 lamports
  (`scripts/account_sizes.py`). Per door, maximum metadata, it goes from 9,184,640 to
  9,677,400 lamports. A launch goes from 27,447,240 to 27,940,000. Every downstream figure is
  regenerated by its script: spec rent tables, `fee_model.md`, `gate_costs.md`,
  `rent_correction.md`, `NARRATIVE_DETECTION.md` blocks.
- **Rent formula: no new RPC read.** It is the one already confirmed by RPC
  (`rent_confirmation.json`). The SBF audit now asserts that every door mint's on-chain size
  equals the formula.

**2. The `buy_room` CU rise is traced, and inherent.**
- **Measurement:** `buy_cu_attribution_with_and_without_pending_settlement` runs the same
  room, the same route and the same input, with and without pending fees
  (`verification/cu_buy_attribution.json`):

  | case | CU | token CPIs |
  |---|---|---|
  | room buy, nothing to settle | 45,882 / 46,109 | 1 |
  | room buy, settling 6,000 lamports | 55,060 / 55,063 | 2 |
  | door buy, step from settlement | +8,950 | +1 |

- **Breakdown of the ~9,000 CU:**
  - the Token-2022 `transfer_checked` itself: 2,307 CU, measured;
  - CPI overhead in the program (signer-seed PDA derivation, account serialisation, the
    helper's four token-account reads, the `inverse` division, the event): the remaining
    ~6,700 CU, not split further.
- **Cause:** `8ce373f`'s settle-before-buy. A buy must retire the pending backlog before
  taking a position, or a temporary buyer captures it
  (`verification/sweep_retirement_mev.json`). The cost is inherent to that fix. It is paid
  only when pending is non-zero, and every room-route trade makes it non-zero.
- **Possible saving:** counting retired tokens without moving them would avoid the CPI, but
  changes the spec's RetiredVault design. Not done.

**3. Heap exhaustion on the launch path (M-1, M-7).**
- **What happened:** the new metadata made the existing prefunded-launch test run out of the
  32 KiB SBF heap.
- **Measured** with the new `scripts/heap_probe.py`: at `e9bd2aa` the worst-case
  `create_room` had only **≥ 800 bytes** free at its end.
- **Fix:** `mint_check` stopped deserialising `TokenMetadata` (it now reads two fixed fields
  in place).
- **Margin after the fix** (`verification/heap_headroom.json`): ≥ 688 bytes for the
  worst-case `create_room` (it was ≥ 800 before the metadata change), and ≥ 496 bytes for a
  takeover at the largest size the service signs. It is not a comfortable fix.
- **A second, pre-existing failure, also at `e9bd2aa`:** a prefunded `create_room`
  **takeover** at maximum metadata exhausts the heap. That size needs a v0 transaction.
  - **Not reachable through the matcher service,** which signs only legacy transactions: a
    takeover create fits at most a 70-byte URI there, and passes.
  - **Open as M-7,** with an ignored reproduction test.
- **Before v0 support:** the matcher service must not add v0 launch transactions until M-7 is
  fixed (services `README.md`).

**4. `claim` edited lamports before a CPI.** It was balanced, but it was the `8ce373f` class.
The edit now follows the CPI (I-1). That WSOL branch is dormant in v1.

**5. Dependency audit re-run, by another route.**
- **Why another route:** `api.osv.dev` is unreachable here (connection refused, not 403).
- **What ran instead:** `scripts/audit_dependencies.py --bulk` uses OSV's official bulk export
  (`osv-vulnerabilities.storage.googleapis.com/crates.io/all.zip`: GCS generation
  `1793774894013088`, Last-Modified 4 Nov 2026 06:48 GMT, SHA-256 `dea150c5…`). It evaluates
  each exact lockfile version locally.
- **Result:** 427 versions; the same five reviewed maintenance notices; no vulnerabilities.
- **Validation of the method:** it reproduces the 2 November API scan exactly, and flags the
  vulnerable `ctutils 0.4.3` and `crypto-bigint 0.7.5`.
- **CI unchanged:** CI still uses the API.

**6. `verification/build.json` records the code commit.** It records `805bae3`, the commit
whose source it hashes (program and tests; the program source is unchanged since `1558b2e`). The evidence commit after it changes no program source, the same
convention as `AUDIT_FIXES.md`.

**7. `verification/sweep_*.json` are now tracked.**
- **What they are:** deterministic outputs of the SBF regressions for the two `8ce373f` fixes
  (the Config-snapshot race, retirement MEV), the same kind of evidence as the tracked
  `audit_fee_race.json`.
- **Also tracked:** `cu_buy_attribution.json`, `heap_headroom*.json`.
- **Not tracked:** `sbf-build.log` (a CI artefact).

**8. Matcher key rotated.**
- **Old key:** `5Bb2…RrCN`, generated in a session and never in a deployed Config. Its secret
  is deleted.
- **New key:** the devnet/localnet key is now `AMUaQ4J1EJ4SWCwxc3fHYW4PNdyE432qNzitVdX9T3Bv`.
  **This key was also generated in a session.** The mainnet key must be created in KMS by the
  owner.
- **Procedure:** `DEPLOYMENT.md` §9.
- **Doc conflict:** `NARRATIVE_DETECTION.md` describes a `set_matcher_authority`
  instruction. No such instruction exists: rotation is `update_config` with the whole
  `Settings`, so a hand-built update can change other fields (I-8). The narrative document is
  not edited here.

**9. Two errors of mine from the previous task, now fixed.**
- **`devnet/e2e.sh` compared live CU with the wrong ELF.** After the repin it still compared
  against the old candidate's VM report (`deployed_elf_vm`, ELF `f2cfdb85…`). It now uses
  `verification/svm_report.json`, and refuses unless `build.json`'s ELF equals the pin.
- **`refresh_spec_tables.py` still wrote the index-based door seeds.** The spec had been
  edited by hand.

**10. `DEPLOYMENT.md` was stale.**
- **What was stale:** it still named `436c002` as the deploy source, quoted 34/34 tests, and
  had a localnet table from the old ELF.
- **What changed:** §1, §3, §4, §6 and §7 are updated. §7's tables are regenerated by
  `devnet/report.py` from this run.
- **New in this run:** live localnet CU exceeded the VM maximum for `convert` (+5,773) and
  `claim_door_fees` (+4,500). The validator is Agave 4.4.0; LiteSVM is 4.3.2.

**VM CU, `e9bd2aa` → `1558b2e` (`verification/cu.md`):**

| instruction | before | after | per room/block at the observed max |
|---|---|---|---|
| buy_door | 62,616–75,550 | 57,083–69,450 | 317 → 345 |
| sell_door | 59,704–63,530 | 54,171–57,430 | 377 → 417 |
| buy_room | 46,106–55,099 | 44,568–53,561 | 435 → 448 |
| sell_room | 43,285–43,785 | 41,747–42,041 | 548 → 570 |
| convert | 75,311–78,270 | 65,835–68,846 | 306 → 348 |
| open_door | 118,610–130,159 | 138,509–149,950 | 184 → 160 |

**What drives the changes:**
- **Trades fell 1,500–9,400 CU:** `mint_check` no longer deserialises metadata on every
  door/room check.
- **`open_door` rose ~20,000 CU:** two more metadata-field CPIs.
- **Heaviest trade:** the per-room count at the observed maximum rose (convert, 306 → 348).

## Security-review follow-up (5 November 2026)

The findings are worked through in `SECURITY_REVIEW.md`. This section records conflicts with the
brief, and with earlier documents.

**1. `RequestHeapFrame` does not resolve M-7, for two independent reasons.**
- **The allocator ignores the frame.** The program uses the stock entrypoint
  allocator, `BumpAllocator::with_fixed_address_range(HEAP_START_ADDRESS, HEAP_LENGTH)`
  with `HEAP_LENGTH = 32 * 1024` (`solana-program-entrypoint` 3.1.1, `custom_heap_default!`).
  A larger requested frame is mapped by the runtime, but this allocator never uses it.
  Measured (`heap_headroom.frame262144.json`): free heap at the end of `open_door` is ≥ 9,568
  bytes with and without a 256 KiB request, and of a URI-70 takeover ≥ 496 with and without it.
- **The trace has no room for the request.** One more top-level instruction does not fit:
  a prefunded `create_room` with a first buy uses 63 of the 64 instruction-trace entries,
  and 64 when the service adds its priority-fee instruction (`verification/trace_budget.json`).
  With `RequestHeapFrame` added, the launch fails with `Max instruction trace length exceeded`
  (heap probe, `--heap-frame 262144`).
- **Status:** M-7 stays open, and M-8 (the trace margin) is new. The brief excluded a custom
  allocator; it would also need the frame request, and so the same trace entry.

**2. The brief's slippage guidance is not in the spec.** "Frontend guidance in the spec": the
spec has none. The guidance is `DESIGN.md` §3 ("≤ 2–3% slippage"). The service default is 2%.

**3. Pause no longer blocks sells or `convert`.**
- **Spec change:** this changes spec-defined behaviour, by the owner's decision in the brief.
- **What earlier documents said:** `AUDIT_FIXES.md` (2 November) kept pause as a privileged
  control covering every trade; that is superseded.
- **Invariant review:** no invariant requires buys and sells to be paused together
  (`SECURITY_REVIEW.md` M-5).
- **New consequence:** an exploit in the sell path can now only be stopped by an upgrade.

**4. CU figures were presented as ceilings.**
- **What was wrong:** `report_cu.py` (and the spec block it generates), `cu.md`, `devnet/report.py`,
  `DEPLOYMENT.md`, `README.md`, `SECURITY_REVIEW.md` and this file labelled
  `floor(cap / VM max)` a "ceiling", and VM maxima as worst cases.
- **What they are:** observed values from LiteSVM's Agave 4.3.2 at fixed addresses. The live
  4.4.0 validator exceeded them in two runs: `claim_door_fees` by 4,500 and 10,500 CU, and
  `convert` by 5,773 and 1,273. The gap itself moves from run to run.
- **Change:** all of these now say so. The e2e comparison labels the VM column "observed", and a
  positive difference as expected.

**5. M-6 (liveness snapshot) evaluated, not implemented.** The cost is small (+32 bytes per Room,
+162,560 lamports). But the design defines one shared mutable gate, and changing the gate is the
only defence against cheap wash-traded liveness (I-3). Recommendation, in `SECURITY_REVIEW.md`:
delay threshold changes, rather than snapshot them.

## Devnet deployment (5 November 2026)

- **Deployed.** ELF `c36ba443…ed29` (commit `b6fe25d`) is on devnet: deploy slot 518,934,300,
  on-chain bytes equal to the pin. Config is initialised and read back at slot 518,934,315, with
  0 of 22 fields differing. The program e2e passes on devnet, 33/33, and so does the matcher
  service's. Evidence and tables: `DEPLOYMENT.md` §5 and §7, and `verification/devnet/devnet/`.
  `PENDING.md` is removed, and `devnet/e2e-target` is `devnet`.
- **`deploy.sh` could not write to devnet from this environment.**
  - **Why:** the CLI's default sends buffer writes to validator TPUs over QUIC, which an
    HTTPS-only network cannot reach. It failed with `Max retries exceeded` and left a funded
    buffer behind.
  - **Recovery:** the buffer was closed back to the deploy wallet (§5).
  - **Fix:** `deploy.sh` now uses `--use-rpc --max-sign-attempts 20`, and prints the
    buffer-recovery commands on failure.
- **Live devnet CU exceeded the VM observed maximum on five routes:**

  | route | above the VM maximum |
  |---|---|
  | `create_room` | +12,003 |
  | `claim_door_fees` | +4,500 |
  | `convert` | +2,781 |
  | `open_door` | +557 |
  | `retire_pending` | +430 |

  This is the real-cluster version of the localnet observation: VM figures are not ceilings.
- **The cost estimate in §5 was close.**
  - **What the doc said:** "about 3.5 SOL" for a 525,032-byte ELF.
  - **Actual:** ProgramData for the 522,776-byte ELF took 2,656,580,920 lamports, plus a
    0.05 SOL Config top-up and the e2e wallet top-ups (§5).

## M-8 fix, M-6 timelock, H-1 interim (5 November 2026)

Owner decisions in the brief: M-8 first, H-1 interim now with NameLock as a mainnet blocker, M-6 by
timelock.

**M-8: the creation path's trace.**
- **Root cause:** prefunding, not the CPI count as such. A PDA someone had already sent lamports to
  cost transfer + allocate + assign: three trace entries instead of one.
- **Fix:** `create_pda` now uses SIMD-0312 `CreateAccountAllowPrefund` for a prefunded PDA, one CPI.
  The feature is active on devnet (slot 454,464,000) and mainnet (slot 422,928,004),
  `solana feature status 6sPDzwyARRExKH52LECxcGoqziH8G7SZofwuxi8Ja331`. Anchor 1.2.2's `init` already
  did this for `Room` and `Door`.
- **Tried and reverted: merging a buy's two System transfers.** Merging them into one, plus a lamport
  edit, saved one trace entry but measurably *cost* heap: about 336 bytes on the worst `create_room`
  and 320 on `open_door` (`verification/heap_headroom.ab_merged_buy_deposits.json`). The mechanism
  is not identified. Heap is the tighter budget (M-7), so buys keep two transfers.
- **Result** (`launch_instruction_trace_budget`, `verification/trace_budget.json`):

  | launch | trace entries, before | after |
  |---|---|---|
  | prefunded `create_room` with a first buy | 63 | 47 |
  | same, with a priority fee | 64 | 48 |
  | prefunded `open_door` | 35 | 29 |
  | prefunded `open_door`, with a priority fee | 36 | 30 |

  The test now asserts at least 12 entries free on every shape. It also asserts that prefunding adds
  at most 2, both inside the Associated Token program, which handles a prefunded user ATA itself.
- **Correction, the library builder:** `system_instruction::create_account_allow_prefund` pushes the
  payer onto a one-element `Vec`. On the never-freed SBF heap that strands one buffer and
  over-allocates the next. Used as-is it cuts heap headroom (worst `create_room` ≥ 848 → ≥ 16 bytes; the
  service-size takeover fails; `heap_headroom.ab_library_allow_prefund_builder.json`). `vaults::allow_prefund_ix` builds the same bytes with exact
  allocations; a test asserts byte equality with the library builder.

**M-6: the liveness gate is timelocked.**
- **Change:** `update_config` refuses gate changes. `propose_gate`, `apply_gate` (permissionless,
  after 604,800 s) and `cancel_gate` replace them, with `GateChangeProposed` / `GateChangeApplied` /
  `GateChangeCancelled` events.
- **Layout:** the pending change lives in a new PDA `PendingGate` `["gate"]` (65 bytes). Config's
  layout is unchanged.
- **This changes spec-defined behaviour, by owner decision.** The spec (§3, Config) is updated.

**H-1:** the interim fix is in the service (`services/matcher/CORRECTIONS.md` §15). The NameLock is
recorded as a mainnet blocker in `SECURITY_REVIEW.md`.

**Heap and CU at `54215ae`** (`heap_probe.py`, `verification/heap_headroom.json`): worst
`create_room` ≥ 848 bytes free (was ≥ 688 at `b6fe25d`), `open_door` ≥ 9,568 (unchanged), the
service-size takeover ≥ 624 (was ≥ 496). The worst `create_room` uses 295,952 transaction CU (was
322,367). The v0 maximum takeover still fails: M-7 stays open.

**Correction, the A/B evidence.** The A/B heap figures were first measured on local throwaway commits
(`d20b94b`, `e87c692`, `56afc95`, `f3022c8`) that were never pushed, so nobody else could re-run
them. Each variant is now a patch against `54215ae` in `verification/ab/`. `heap_probe.py --patch`
applies it in the probe's worktree and records the patch's SHA-256. All three variants were
re-measured that way:

| variant (`verification/ab/*.patch`) | worst `create_room` | `open_door` | URI-70 takeover |
|---|---|---|---|
| none: `54215ae` as committed | ≥ 848 | ≥ 9,568 | ≥ 624 |
| `merged_buy_deposits` | ≥ 512 | ≥ 9,248 | ≥ 288 |
| `transfer_allocate_assign_create_pda` (the pre-M-8 prefunded path) | ≥ 688 | ≥ 9,568 | ≥ 496 |
| `library_allow_prefund_builder` | ≥ 16 | ≥ 9,568 | fails (0) |

The re-measurements agree with the throwaway-commit figures to the byte. The pre-M-8 prefunded path
on today's source gives exactly the `b6fe25d` figures, so the one-CPI path accounts for the whole
heap gain; M-6 adds nothing to the launch path.

**M-7 re-evaluated after M-8** (`heap_probe.py --heap-frame 262144` at `54215ae`,
`verification/heap_headroom.frame262144.json`; the `b6fe25d` file is in git history at `c433617`):
- **The trace objection is gone.** A 256 KiB `RequestHeapFrame` now fits on the worst prefunded
  `create_room` and the launch runs. It used to fail at 65 trace entries.
- **The allocator objection stands.** Free heap is identical with and without the request (848 /
  9,568 / 624), and the v0 maximum takeover still fails. The request costs 1,774 transaction CU on
  that `create_room`.
- **What is left for M-7** is a program change, so the owner's call: a custom allocator over the
  requested frame, or less heap on the takeover path (`SECURITY_REVIEW.md` M-7).

**Devnet upgrade to `54215ae`** (`devnet/upgrade.sh`, new; `DEPLOYMENT.md` §5):
- signature `qLdPHc7BqBBG2PtS21M2jAp6xoVKUSYkBkzwAP9e5bgx9jwqxa6o5YTrcTd1iD8CepGmsbnQUuysEkdC3Y9JHvw`,
  slot 519,010,828;
- ProgramData grew from 522,776 to 552,840 bytes; the CLI extended it, at 152,725,120 lamports of
  permanent rent;
- on-chain bytes equal the pinned ELF `b30c3462…83b9`. Config was read back at slot 519,010,873 with
  0 of 22 fields differing. Config's layout is unchanged.

**The program devnet e2e failed once after the upgrade, and the cause was the test.**
- **What happened:** `create_room` failed with `Holder` (6013).
- **Why:** the smoke launch used a fixed name and symbol. Its SlugLock from the first devnet run is
  still held by a live room, so the identity was taken. That is the program behaving as specified.
- **Fix:** `devnet/src/main.rs` derives a per-run name and symbol from the room's random id. The
  rerun passed 33/33, as did localnet.

**Correction, `DEPLOYMENT.md` §7.** As committed in `c433617`, the devnet half of §7 contained raw
Python template text (`'''+rep+'''`) instead of the generated tables: a generation step had failed
and was not caught. §7 is now regenerated from the evidence with `devnet/report.py` for both
clusters.

**Correction, `devnet/report.py`.** After an upgrade it paired the original deploy signature with
the upgrade's `lastDeploySlot`. It now prints the upgrade signature from `upgrade.json` beside the
deploy signature, labels the slot as the last upgrade's, and checks the upgrade's program ID.

**Live devnet CU after the upgrade** (`DEPLOYMENT.md` §7): `create_room` ran 25,610 CU above its VM
observed maximum (12,003 at `b6fe25d`), `claim_door_fees` 13,500, `sell_door` 6,858, `convert` 5,781,
`retire_pending` 430. The smoke launch's metadata and addresses now differ on every run, so these
are not directly comparable with the `b6fe25d` run. The worst tested VM launch, 303,780 CU, plus the
largest drift is still about 70,600 under the service's 400,000 limit.


## M-7 fixed, NameLock (H-1 closed), stack signer seeds (5 November 2026)

Owner decisions in the brief: M-7 by the targeted fix (less heap on the takeover path, no custom
allocator), then the matcher-keyed NameLock, in one pass.

**M-7: the old holder is read in place (`8f54026`).**
- **What was large:** a takeover's only extra deserialisation was `old_holder:
  Option<Box<Account<Room>>>`. That is a full 1,315-byte `Room` boxed on the heap to read six fields.
  Nothing else on the takeover path is takeover-specific; `read_slug` deserialises a 17-byte
  `SlugLock` on the stack.
- **Fix:** `old_holder` is an `UncheckedAccount`, read by `state::RoomBytes` at the layout's
  offsets. `vaults::holder_dead` checks owner, exact size, the `Room` discriminator and the
  canonical room PDA, which is what `Account<Room>` checked. Liveness goes through one function,
  `state::live_rule`, which `Room::live` also calls.
- **Tests:**
  - `takeover_holder_is_validated_in_place`: forged, foreign-owned, non-Room and wrong-holder
    accounts, plus `RoomBytes` against a serialised `Room` across statuses, clocks and gate settings;
  - the former ignored reproduction is now `prefunded_v0_maximum_takeover_fits_the_heap`, run
    every time.
- **Measured** (`heap_probe.py`, which now also searches the URI-200 and `open_door` takeovers):

  | path | `1de13c9` | `8f54026` |
  |---|---|---|
  | worst `create_room` | ≥ 848 | ≥ 848 |
  | `open_door` | ≥ 9,568 | ≥ 9,568 |
  | takeover, URI 70 | ≥ 624 | ≥ 1,936 |
  | takeover, URI 200 (v0) | **fails** | ≥ 1,280 |
  | `open_door` takeover | ≥ 8,256 | ≥ 9,568 |

  The boxed holder cost exactly 1,312 bytes. **M-7 is closed.**
- **Correction to the brief's premise.** "M-7 first, so the NameLock lands on recovered headroom":
  the recovered heap is on the *takeover* path only. A fresh launch never read an old holder, so
  the worst plain `create_room` gained nothing (848 before and after).

**NameLock (`f87f341`).**
- **Design:** see `SECURITY_REVIEW.md` H-1 and spec §0.G. Key: 16 bytes, signed by the matcher.
  Lock: `NameLock { room_id, key, bump }`, 33 bytes; it stores its key so that `release_name` can
  derive its address.
- **Cost:**
  - trace: +1 entry, so the worst launch uses 49 of 64 (`trace_budget.json`);
  - rent: 817,880 lamports per room;
  - CU: +6,290 on the worst `create_room` (295,753 → 302,043 VM CU);
  - URI length: the largest URI the service can sign in a legacy transaction falls from 102 to 51
    for a new room, and from 70 to 19 for a takeover (`services/matcher/scripts/max_uri.py`).
- **Heap: thinner than expected, and the reason.** At `f87f341` the worst `create_room` kept only
  **≥ 272 bytes** (848 before). The takeovers lost 160 (1,936 → 1,776; URI 200: 1,280 → 1,104).
  The cause was not the NameLock as such but `create_pda`, which every created account goes
  through:
  - `seeds.to_vec()` allocated an exact-size `Vec` and `push(bump)` then grew it, stranding the
    first buffer: 96–144 bytes per account;
  - the NameLock added one more call;
  - and on the takeover path the NameLock is overwritten in place, with no `create_pda`. That is
    why takeovers lost less.

**`create_pda` signer seeds on the stack (`71d32f3`).** A fixed `[&[u8]; 4]` (`MAX_SEEDS` = 3 plus the
bump): same seeds, same CPI, no allocation. Measured:

| path | `1de13c9` (before) | `8f54026` (M-7) | `f87f341` (+ NameLock) | `71d32f3` (+ stack seeds) |
|---|---|---|---|---|
| worst `create_room` (prefunded, max metadata, first buy) | ≥ 848 | ≥ 848 | ≥ 272 | **≥ 1,520** |
| `open_door`, same conditions | ≥ 9,568 | ≥ 9,568 | ≥ 9,568 | ≥ 9,920 |
| takeover, URI 70 (service maximum) | ≥ 624 | ≥ 1,936 | ≥ 1,776 | **≥ 2,816** |
| takeover, URI 200 (v0 maximum) | **fails** | ≥ 1,280 | ≥ 1,104 | **≥ 2,160** |
| `open_door` takeover | ≥ 8,256 | ≥ 9,568 | ≥ 9,568 | ≥ 9,920 |

Files: `verification/heap_headroom.1de13c9.json`, `.8f54026.json`, `.f87f341.json` and
`heap_headroom.json` (`71d32f3`). Every launch path now has more free heap than at any point since the
metadata change, and the worst one has more than twice its old 688-byte low. CU fell too: the worst
`create_room` uses 299,139 VM CU (302,043 at `f87f341`), and the worst service-signable takeover 306,064
(`cargo test --locked --test svm prefunded_maximum_metadata -- --nocapture`).

**Correction, `SECURITY_REVIEW.md` H-1:** the earlier NameLock estimate assumed a 32-byte key and a
17-byte lock (URI 37 / 5, rent 736,600). The implementation uses a 16-byte key and a 33-byte lock
(URI 51 / 19, rent 817,880).

**Correction, the verification script:** the first full SBF run of `8f54026` reported 2 failures. Both
were the script's: its clean worktree had not built the `launch_proxy` test fixture, which CI builds
separately and two tests load. With the fixture built, both pass. `program/scripts/verify_commit.sh` (new) builds it, runs the full suite and then the heap probe.

**Devnet upgrade to `71d32f3`** (`DEPLOYMENT.md` §5):
- signature `2tbUeyfjRfg1q9ujavtnW7hmpcVoH2s8T1NHXfE8pp6azpY62u6ekZ6QBhYPkQSkLUGHnhEdUnYP6YncqfVA9ecT`,
  slot 519,081,470;
- ProgramData grew from 552,840 to 571,264 bytes, costing 93,593,920 lamports of permanent rent plus
  6,260,000 in fees;
- on-chain bytes equal the pinned ELF `0f9c6dec…9434`. Config was read back at slot 519,081,523 with
  0 of 22 fields differing.

Results:
- program e2e: 34/34 on devnet and localnet;
- service e2e: PASS on devnet and localnet, including the live NameLock race (second `create_room`
  rejected with 6013 at slot 519,081,838);
- test positions sold back and swept: the deploy wallet holds 6,396,200,441 lamports at slot
  519,084,911.

**Correction, the live-versus-VM `create_room` gap.** This document and `DEPLOYMENT.md` attributed the
gap to "PDA bump searches or the runtime version, not separated". Now separated
(`scripts/bump_drift.py`, plus two new localnet variants of `e2e.sh`):
- **Bump search** is the moving part: −6,000 to +7,500 CU between runs.
- **The runtime version is not a cause:** devnet runs Agave 4.4.0-beta.1 and the local validator 4.4.0.
- **The constant part is the cluster's token programs.** Corrected for bumps, the three devnet runs
  sit at +18,003 / +21,110 / +16,610. Localnet matches it (+19,862) only with devnet's Token-2022,
  SPL Token and ATA programs loaded. Devnet's feature set adds about +3,000.
- **So the gap is not widening** (12,003 → 25,610 → 19,610 was bump luck).
- **Margin:** the service's 400,000 limit keeps about 49,000 CU above the worst case, allowing 15
  unlucky extra bump tries.
- **Recommendation:** run the SBF suite against the cluster's token programs.

**Correction, `DEPLOYMENT.md` §7 earlier text:** "the smoke launch's metadata and addresses differ"
was offered as a reason the runs were not comparable. Metadata differences are small: localnet with the
same names lands within 2,518 of the VM. The addresses matter only through the bump term above.


## Paired doors prototype completion is unreachable for early doors

The brief holds the room mint at 1,000,000,000.000000 room
tokens and revokes mint authority. The current curve phase releases at most
793,143,840.548785 of those tokens under its
default configuration. The proposed door uses a fixed virtual quote equal
to 30 SOL at the room spot price when the door is created, then requires a
real reserve of 85/30 of that virtual quote to complete.

Run `python program/scripts/check_paired_completion.py` from the repository
root to reproduce the check against the existing curve parameters. The
script uses the room's exact configured virtual SOL, which is
30,000,852,995 lamports. It rounds the door virtual
quote down to test the most favorable integer threshold.

| Room reserve at door creation (SOL) | Virtual quote (room tokens) | Completion reserve (room tokens) | Exceeds entire room mint |
|---:|---:|---:|---|
| 0 | 1,072,995,097.351564 | 3,040,152,775.829432 | yes |
| 10 | 603,568,322.634969 | 1,710,110,247.465746 | yes |
| 50 | 150,895,298.400118 | 427,536,678.800335 | no |

Door 0 takes the first row because the room starts empty. Even if it held
every room token, the vault would fall short. The door born at the 50 SOL
reference state passes the supply check. Its actual completion still
requires a reachable allocation through permitted trades and swaps.

Implementation paused at this finding pending an owner ruling. The next
section records the ruling that cleared the pause.

### Owner ruling and supply-exhaustion fixture

The owner rejected a completion cap based on room capacity at door
creation. The prototype has permanent doors and no completion rule.
Crossing-and-latch is recorded as a possible phase-2 migration trigger.

The supply-exhaustion guard is unreachable under the unchanged default
room parameters. Give a door the highest room spot price the default
curve could reach at creation and every room token the curve could
release at once. That is still only
793,143,840.548785 room tokens. The door would
require at least 999,658,368.049078
room tokens to sell its entire supply, and the generous upper bound is
982,588,530.503056 door tokens sold.
`python program/scripts/check_paired_completion.py` reproduces these
bounds.

A separate stress fixture can reach the guard through normal trades
using the existing Config validation. At a room cap of
120.000000000 SOL and a door born at
100.000000000 SOL,
an existing source door can deliver
817,144,907.490190 room tokens
after the swap fee, above the receiving door's
782,523,466.183039 room-token exhaustion cost.
The owner approved this isolated SBF fixture. The unchanged Config validator accepted it before implementation in the
[Config-only Linux run](https://github.com/Arriived/bonding-curve/actions/runs/42280400705).
The default room cap remains in use for regular measurements and devnet.

### Existing sell accounting

The room sell pays the fee vault directly from the reserve as part of the
gross curve payout. `execute_trade` asserts that the total reserve debit
equals that gross payout. The existing sell and the paired-door design
preserve this economic invariant.

### First prototype verification

The Config-only SBF run accepted and read back the stress cap through
unchanged validation. The first implementation build stopped in host
compile because the adversarial sweeps still referenced the prior
conversion helper. The sweeps now exercise the equivalent swap checks.

The first real prototype SBF run executed against the pinned deployed SPL
programs. Four older rollback or redemption fixtures still used room
tokens as a door minimum or a door sale input. The prototype now quotes
the room and door units separately in those fixtures, retaining their
slippage, retirement and conservation assertions. The first runtime run
also supplied the generated prototype IDL and compiled ELF hash.


### Paired doors review fixes before devnet

The prototype is rebased onto program-v1 `4b2d043`. Its smoke name-key
function and all twelve matcher vectors are retained byte-for-byte from
that base. The standalone devnet client tests run in CI.

The rebased baseline at `915b075` reproduced the creation heap finding.
The swap fee vault was being initialized during room creation. It is now
initialized at its canonical PDA by the first swapping user, including
when that PDA has been prefunded. Existing vaults retain the mint, owner,
initialization and canonical-address checks. Room creation omits the vault
account. The default heap probe enforces at least 1,500 bytes of creation
headroom. The report's comparison is generated from that probe and the
SBF rent fixture, with baseline source hashes retained in
`verification/paired_doors_before_review.json`.

Swap fees previously had accounting credits without a withdrawal path.
The new door and protocol claims require their respective current fee
recipient's signature and pay that recipient's existing room-token ATA.
The protocol claim is authorized by Config's protocol fee recipient.
Every swap and claim checks the vault against the room-wide total of
unclaimed swap fees. The property audit also checks that the total equals
the sum of every door's credit and the protocol credit. Tests cover
recipient changes, unauthorized signers, incorrect destination accounts,
partial and repeated claims, complete fee payout, and a deficit hidden by
the former protocol-plus-receiving-door check. The provisional fee and
receiving-door share are grouped as basis-point constants in `math.rs`.

The report had mixed transaction CU from priority-fee trace fixtures with
program CU from maximum-metadata takeover fixtures. The generated CU
table now names each fixture, records the transaction shape, and separates
program and transaction CU. Instrumented heap-probe CU is labelled in the
creation comparison. The first review build's IDL comparison caught an
extra trailing newline in the edited IDL. The committed IDL is copied from
the exact Anchor output, and comparison plus layout checks run before SBF
execution on this branch.


The first complete runtime pass accepted the new claim regressions and
all property iterations. Its rent helper then tried to trade through a
fixture whose direct rent-only launches had not populated the test
client's door list. First-swap vault rent now uses a normal trading
fixture. The rent-only room and door measurements retain their original
metadata and account-balance method.


The lazy vault alone raised maximum-metadata creation headroom from 64
to 640 bytes in [the first complete review run](https://github.com/Arriived/bonding-curve/actions/runs/42380227882).
All 59 SBF tests, property iterations and the standalone client test passed,
but the heap target failed. The 1,500-byte requirement remains enforced.
The metadata initializer's remaining allocations were then removed as
recorded below.


The pinned token-metadata initializer cloned the three launch strings,
serialized them into an intermediate Borsh buffer, then copied that data
into the instruction buffer. Creation now builds that same instruction
in one correctly sized buffer using the borrowed launch strings. A
regression compares its complete instruction bytes and account metas
with the pinned library for empty URIs, maximum lengths and multibyte
UTF-8. The mint metadata, instruction order and CPI count are preserved.
The heap probe writes its measured output before enforcing its target so
failed targets also retain their evidence.


The exact-size metadata initializer measured 3,184 bytes of creation
headroom in the next full run. All 60 SBF tests, 10,000 property iterations,
standalone client tests and the heap target passed. That run stopped at
the enabled binary-pin check because the initializer changed the compiled
ELF. The pin was updated from the artifact after every program source file
and the emitted IDL were compared with the working tree. The
[final Linux run](https://github.com/Arriived/bonding-curve/actions/runs/42384466860)
on `38e50d54c79b31d5798b2c60fd001b411547ff14` passed the binary-pin check,
all 60 SBF tests, 10,000 property iterations (12,488 executed transactions),
the standalone client test, IDL comparison, layout check and heap probe.
The deployed SPL binary hashes were verified again at finalized slot
519,699,373. The generated CU table includes the program-inclusive CU from
the launch trace fixture. Maximum measured transaction CU was 329,406;
maximum-metadata fresh creation retained at least 3,184 bytes of heap.
Room creation including door 0 used 26,959,560 lamports of rent. First swap
fee-vault rent was 1,488,440 lamports, paid by the swapping user. The final
artifact's source hashes, emitted IDL and pinned ELF match the reviewed
working tree, and the economic scenario output matches the rebased
baseline exactly. Devnet deployment remains held for the owner.


## Paired review continuation (7 November 2026)

The review starts from program `2bf6f40` and service `9750e03`. Preserved local
review drafts remain saved separately; owner decisions are represented by passing
current-behaviour assertions and review notes, without deliberately failing tests.

- The owner approved a separate launch room-price bound. A paired token minimum
  does not bound the room value of a newly anchored door: the original 20 SOL
  front-run case earns 0.217061544 SOL after transaction fees and cuts the victim's
  immediate exit by 0.549648652 SOL. Launch now appends `max_room_price: u128`,
  scale 10^18 lamports per room base unit, zero disabled. Both launch paths check
  the exact pre-buy spot. A temporary disabled-check negative control fails the
  regression before the protected SBF suite runs.
- The service's first-buy minimum was in room tokens. It now quotes both curves
  and returns door base units, with an independent verifier and exact SBF vector
  of 33,699,309,828,108 for the recorded 1.01 SOL buy. Layouts, IDL, event decoder,
  sweep instruction and program ID are ported. Active pins are named `paired`,
  avoiding a claim that this interface has been deployed. The unchanged NameLock
  key still depends only on metadata; its byte offset follows the appended field.
- The extra 16 bytes reduce the maximum legacy URI at maximum name/symbol length
  with priority fee from 51 to 35 for fresh creation and 19 to 3 for a one-holder
  takeover. Oversized requests still receive a refusal. v0 support is not added.
- The first continuation CI run stopped at the IDL pin because the manually
  serialized JSON retained one trailing newline that Anchor did not emit. The
  committed interface is now copied byte-for-byte from emitted output.
- The next run passed the price regression and 10,000 mixed operations, but the
  same-slot test expected Holder while its helper refreshed the former holder,
  producing Live. The fixture now supplies the shared earlier snapshot explicitly.
  This is a test correction; the program already allowed only one create.
- Pinned SPL executables were recovered from the local archived test fixture and
  checked against the existing hashes. CI uses those versioned bytes offline.
  It no longer fetches a live test-cluster snapshot for paired verification.
- The heap probe now includes both swap-fee claims and prefunded first-swap vault
  initialization. The resource fixture exercises late permanent doors, pending
  settlement and full exit/claim paths with priority and heap-frame instructions.
- The old 0.05 SOL/day liveness estimate omitted the self-owned door's 60% fee
  rebate. Ongoing unrecoverable protocol fees are approximately 0.02 SOL/day;
  final exact SBF measurements, network fees and startup capital are recorded in
  SECURITY_REVIEW.md. Thresholds remain an owner decision.
- Revival after NameLock succession and the ordinary admin's ability to set the
  120 SOL cap remain current behaviour. Options and recommendations are written
  in SECURITY_REVIEW.md; neither routing policy nor Config validation is changed.
- The first service parity regression failed at 19,628,248,343,287 room units
  versus the SBF door-unit vector. Signature alteration/concurrent replay tests
  already passed; no new replay vulnerability was found. The benchmark adds
  mixed-script composition and actual valid-UTF-8 32-byte truncation; rules stay
  byte-for-byte unchanged.


The offline-report step initially lacked the archived SPL manifest at the expected
verification path. Running the report on that artifact reproduced FileNotFoundError.
CI now copies the versioned manifest after verifying the executable hashes. Its
wording identifies an offline byte check and the historical capture slot, rather
than implying a new live-cluster read. The compiled binary pin was updated only
after every emitted program source and the IDL matched the working tree.

A preserved service draft also reproduced public RPC error leakage using synthetic
markers. Both HTTP exception text and JSON-RPC bodies could disclose authenticated
endpoint text. The service now retains safe diagnostic codes only; both tests and
the 163-test full suite pass. No production key or credential was read.


Final verification, 8 November 2026: run 42403905057 on `9ed04d7` is green.
All 71 SBF tests, 10,000 mixed iterations (12,488 transactions), offline SPL pins,
source/IDL/binary checks, client unit test, heap probe and 400,000-iteration curve
fuzz passed. Each of 33 doors in four resource states had a positive position and
fee credit, and every position and credit was fully discharged. The service
passes 163 tests and its repeated evasion JSON is identical. SECURITY_REVIEW.md
contains the exact resource table, cost assumptions and ranked owner decisions.


## Implemented owner rulings A, B and D (8 November 2026)

Supersedes the two open owner choices in the previous continuation. A routes
new doors only to the current live NameLock holder, with conflicting live
SlugLock/NameLock holders refused. A revived former holder still trades. The SBF
revival probe asserts successor door count increases and former count does not.
The service and independent verifier implement the precedence; finding 4 is Fixed.

Against control `816b38d`, B changes default Config validation from accepting
120 SOL to refusing anything above 85,018,013,680 lamports. The isolated
`test-stress` feature accepts 120 SOL. Both directions are permanent passing SBF
tests with corresponding binaries; finding 7 is Fixed. The owner authorized the
reviewer to run historical B/D controls independently against `816b38d`. No
intentionally failing historical test is committed on this branch.

D defers six unused birth vaults and stores liveness buckets sparsely, preserving
exact u128 values, old ring replacement and liveness behavior. Birth Room drops
from 1,331 to 735 bytes; first buy funds its complete 1,335-byte capacity. The
retirement instruction gains a payer/system account; legacy fee claims gain the
system account and a writable payer authority for first WSOL initialization.
The standalone client and service pins are ported. Birth rent falls from
26,959,560 to 17,515,840 lamports (35.0%). The 15 million target remains missed by
2,515,840: remaining birth state, immutable mint metadata and inventory are needed
by the current interface. Deferred rent is paid on first use rather than removed.

The first full candidate run passed the new rules but found ten eager-account
assumptions in old tests. Fixtures now initialize deferred token vaults through
real claims/retirement, model pre-upgrade native vaults explicitly in the legacy
backlog fixture, and make immutable-term changes within the normal envelope.
The CU attribution test warms first-use vaults so it still isolates settlement.
The prefunded first-swap rent includes both newly created token vaults. These
repairs do not alter expected economic outcomes or weaken exits/claim coverage.

RPC details remain available to operators via internal DEBUG logging in the
service, while public error strings and API responses stay redacted.


Measured production source `5ac41b9` passes all 71 SBF tests / 10,000 iterations,
the default-refusal and feature-acceptance cap tests, heap and 400,000 curve cases.
Worst launch heap improves 2,960 -> 4,080 bytes, while the matching launch CU rises
328,089 -> 351,341 (open 242,597 -> 284,233). First-use initialization and room
capacity funding cost compute. The matched economic scenario JSON is identical.
Every source hash and emitted IDL was checked before updating the production ELF
pin to `d1fb4975591a2453dbd80ea3671784e91dba753acd2653b4c823ff0c915b5f7e`.
Full before/after bounds, rent and two-sided cap evidence are in
verification/owner_rulings_after.json. Final pin verification follows below.


Final pinned verification is green: run 42526798488 on `86a0f44` passes every
step, including all 71 SBF tests / 10,000 iterations, both permanent stress-cap
directions, isolated supply-exhaustion exits, heap, 400,000 curve cases, client
compile/unit test and production ELF pin. Offline SPL bytes and every recorded
source hash were checked. The active program and service IDLs match emitted bytes.
Service `bf121dc` passes 170 tests; the evasion JSON is identical to the prior
review. Findings 4 and 7 are Fixed; room birth rent is 17,515,840 lamports,
9,443,720 below the control but 2,515,840 above the target. Historical B/D controls
remain assigned to the independent reviewer against `816b38d`, as authorized.


## Launch CU margin correction (8 November 2026)

The CU-seam row still quoted 306,979 at `71d32f3`; that was obsolete. Current
worst launch is 351,341 VM transaction CU. The old 400,000 service limit fails
the documented drift stress: 351,341 + 21,000 + 7,500 + 15*1,500 = 402,341.
The service default is raised to 500,000. SBF maximum-metadata and takeover
assertions and the heap probe add the full allowance; using exact historical
21,110 plus the missing 150-CU priority-price instruction gives 402,601, leaving
97,399 CU. Production program source, binary pin and rent savings are untouched.

At example cu_price 10,000 micro-lamports/CU, priority fee rises 4,000 -> 5,000
lamports (+0.000001 SOL); base signature fees are separate. Packet lengths are
identical at both limits. Maximum name/symbol legacy URI limits remain 35 for
creation, 3 for a one-holder takeover, 200 for open and 194 for open takeover.
Full 200-byte creation is still 1,397 bytes and refused; its service maximum is
1,232 bytes. The service regression first failed on `b86ae42`'s 400,000 default.


Final launch-budget verification: [CI 42536522731](https://github.com/Arriived/bonding-curve/actions/runs/42536522731)
is green on `0849033`: 71 SBF tests, 10,000 mixed iterations / 12,488 transactions,
pinned SPL binaries, both stress-feature checks, heap, 400,000 curve cases,
client compile/unit test and unchanged production binary pin. The maximum heap
fixture records 402,601 stressed CU / **97,399 margin**. Birth rent remains
17,515,840 lamports; creation heap remains at least 4,080 bytes. Every source hash
and emitted IDL matches the candidate. Service `6109176` passes 172 tests; the
1,223-target evasion benchmark repeats byte-identically. Full cross-branch data:
`verification/launch_cu_budget_checks.json` and `launch_cu_packet_sizes.json`.
