# Program-v1 preflight corrections

Status: implementation paused on the invariant policy below, as required by
the brief's “stop and record” rule. No Anchor program or CU figures are claimed.
The authoritative build spec has not been silently weakened.

## Blocking: permissionless transfers and burns

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

Owner decision needed:

- Surplus-tolerant accounting: retain sold/backing as accounting liabilities;
  require vault balances to cover them, rather than equal them. Leave
  unsolicited excess locked. Mint supply is initially exact, then at most
  the initial supply after holder burns. Quotes ignore unsolicited balances.
- Alternatively, retire unsolicited token surplus before checking the exact
  vault equalities. This needs additional accounts/logic on affected paths;
  mint supply still needs to permit holder burns.

Neither policy is implemented pending the owner's choice. Both preserve
one room token of redemption per door token; neither adds a transfer hook.
Phase-2 graduation must also specify how any vault surplus is retired.

## Missing allocation rule: room identifiers

Room and SlugLock use a room identifier, but create_room has no identifier
argument and Config has no identifier allocator. A matcher-selected nonce
argument, covered by both transaction signatures, preserves the current
account layout. An on-chain counter would instead add a Config field and a
global creation write lock. This choice needs to be made explicit in the IDL.

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

The current Windows environment has no Rust, Solana or Anchor command on PATH,
and WSL reports that it is not installed. Official Windows release artifacts
exist; absence of WSL is not yet treated as a build impossibility. Exact
release metadata is being retained before selecting/installing a toolchain.

The research measurement remains in the original worktree and is not modified
by this isolated program branch.
