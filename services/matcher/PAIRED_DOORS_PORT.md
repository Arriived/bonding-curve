# Porting the matcher service to the paired-doors program

Target: `claude/paired-doors` at `2374807`, program `8tPd1ZUEGxrj5zYu8aeg95cU92nmKWKYKoSaKPqFuZAZ`, IDL
`program/idl/doors_v1.json` (committed IDL equals the built one; CI checks it). The service today targets
`D7YsLsiJXoAF38vCUhFqYStepvSz6goG7EddHDe5NVJG` with `idl/doors_v1.deployed.json`.

Measured by diffing the two IDLs field by field (7 November 2026).

## What does not change

- `create_room` and `open_door`: same accounts, same arguments, same discriminators. (The swap-fee vault moved out
  of `create_room` in `3a3a6fd`.)
- `Config`, `Settings`, `SlugLock` and `NameLock` layouts. Launch gains the approved field in item 8.
- The liveness rule and its Room fields. The new Room and Door fields are appended, so every existing offset in
  `idl/layouts.deployed.json` is unchanged.
- The name key, NameLock key and SlugLock identity.

## Required changes

1. **First-buy quote (blocking).** The program now checks a launch's `min_tokens_out` against **door tokens**: the
   first buy runs SOL to room tokens on the room curve, then room tokens to door tokens on the new door's curve.
   This applies to door 0 at `create_room` too. `quote.first_buy_tokens` returns **room tokens**, so the service's
   default minimum (quote less 2%) is in the wrong unit: launches would be refused or unprotected.
   - Port to `quote.py`, in exact integer arithmetic, from `programs/doors_v1/src/math.rs`:
     - `door_virtual_quote(price_num, price_den)`, with the 30 SOL anchor and `DOOR_VIRTUAL_BASE`;
     - `door_integral`;
     - `door_advance`.
   - The door's virtual quote is set in `initialize_door` from the room spot price (`Room::price`) **before** the
     first buy runs (`lib.rs`: `initialize_door` at lines 300 and 423, the first buy at 329 and 441, in
     create_room and open_door). The quote must price the room leg first, then the door leg on a virtual quote
     taken from the pre-buy room price.
   - Add a parity test against SBF output: `program/verification/review_door_open_front_run.json` records 1.01 SOL
     on a room with 10.1 SOL seeded buying 33,699,309,828,108 door tokens.
2. **`scripts/verify_decision.py`.** Its recomputation of `first_buy_quote` needs the same door-curve port, written
   independently of `quote.py` as the rest of the verifier is.
3. **Layouts.**
   - `layouts.py`: change `ROOM_LEN` from 1315 to 1331 and `DOOR_LEN` from 328 to 360.
   - Regenerate `idl/layouts.deployed.json` from the paired program's `verification/layouts.json`.
   - Optionally decode the new fields: Room `protocol_accrued_room` and `swap_fees_unclaimed`; Door `virtual_quote`
     (u128), `sold` and `accrued_room`.
   - `tests/test_rules.py::test_layouts_*` compares against the JSON and will catch a mismatch.
4. **IDL pin.** Replace `idl/doors_v1.deployed.json` with the paired program's IDL once it is deployed (the file
   name means "deployed"; pin the IDL of the deployed ELF, `DEPLOY_ELF.sha256` `928c4815...` or its successor).
5. **Program ID**, in:
   - `matcher_service/config.py` (default for `MATCHER_PROGRAM_ID`);
   - `tests/conftest.py` and `tests/e2e/e2e.py` (`PROGRAM`);
   - `scripts/max_uri.py` and `scripts/sweep_test_positions.py` (`PROGRAM`);
   - `README.md`.

   Better: one constant read from the pinned IDL's `address`.
6. **`scripts/sweep_test_positions.py`.** It sells door tokens with the `sell` instruction plus door accounts. The
   paired program sells door tokens with `sell_door` (same accounts). Room tokens still use `sell`.
7. **Events.** `convert` and `Converted` are gone. The new events are `DoorsSwapped` and `SwapFeesClaimed`, and
   `Trade` gains `room_tokens`. The verifier's event table (`EVENTS` in `verify_decision.py`) should list the new
   names. Nothing in the decision path reads them.
8. **Room-price limit (approved in the review brief).** The optional room-price field on Launch is approved (0 = no
   limit, filled from the user's slippage choice); `Launch` gains a field. The builder, quote, verifier and NameLock
   key code must then follow the new layout. Nothing else in this list depends on it.

## Not needed

- No change to `rules.py`, `decide.py`, routing, the liveness computation, NameLock handling or signing.
- The launch watcher (`watcher/`) reads pump.fun and LaunchLab, not this program.

## Port implemented in this review

Items 1-8 are implemented for offline paired-program verification. The owner approved
item 8 in the review brief: Launch appends `max_room_price: u128` (16 bytes), scale
10^18 lamports per room base unit; zero disables it. Both create and open check the
pre-buy spot. The service defaults it from the user's slippage independently of a
custom token minimum. Authentication, builder, record and independent verifier
include it. NameLock keys are unchanged because their inputs remain the metadata.

The active pins are `doors_v1.paired.json` and `layouts.paired.json`; the deployed pins
remain historical, avoiding a false deployment claim. `program_id.py` reads the IDL
address for config, tests and utilities. The reference SBF quote is tested exactly.
The independent verifier includes both quote legs, pending settlement, the updated
Trade event and the two new swap events. Door sweeps select `sell_door`.
