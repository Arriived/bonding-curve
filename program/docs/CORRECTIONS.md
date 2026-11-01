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

The research measurement remains in the original worktree and is not modified
by this isolated program branch.
