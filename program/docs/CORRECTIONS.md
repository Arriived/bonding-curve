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
