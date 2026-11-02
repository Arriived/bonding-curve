# Program review — 2 November 2026

Scope: the Anchor curve program, instruction account constraints, integer
math, token and native vault helpers, SBF test harness and build workflow.
The review followed fees and reserve movements, mint authorities, matcher
authorization, account aliases/substitution, slug routing, snapshot semantics,
trailing activity, donations/burns and creation resource limits. Graduation
and the off-chain matcher implementation are outside this review.

## Corrected: buy fees counted as liveness volume

`execute_trade` added the buy's curve input plus its fee to Room lifetime
volume and the trailing bucket. Detection section 8 requires the buy fee base
and gross sell proceeds, excluding program fees. A wallet spend at the volume
floor could therefore make a mature room eligible while actual curve volume
was below the floor. Door buy-volume accounting had the same inconsistency.

All these counters now use net curve input on a buy and gross curve proceeds
on a sell. Payments, fees, supply, quotes and the reserve are unchanged.
`buy_fees_do_not_make_a_below_threshold_room_live` checks that fee-inclusive
wallet spend at the threshold does not qualify; adding real curve volume
restores eligibility. It checks both routing rejection and the shared gate.

## Corrected: negative-test failures could be resource failures

The rejection helper previously treated any error as success, used the default
compute budget and checked rollback only for Room and ReserveVault. That could
hide a missing validation behind a compute-limit failure.

It now supplies the same explicit budget as successful tests, rejects compute
and instruction-trace exhaustion as substitutes for validation errors, and
checks rollback for every supplied account except the network fee payer.
Additional tests substitute valid but incorrect vaults, mints, doors, token
programs and user ATAs on both trade directions; same-door conversion is also
rejected. Separate holders trade, convert and redeem against shared backing,
while attempts to claim another holder's door or founder fees fail.

## Creation prefunding investigation

The regression prefunds every new writable launch account with real System
transfers, including future user ATAs, then creates a room and a door with
atomic first buys. It also exercises nonzero room and door launch fees.
This passed against the existing creation code; no prefunding denial of
service was reproduced, so that code was not changed.

## Integration note

`reserve_share_total` exists in the inherited layout but has no specified
update rule and remains zero. It is not a fee or solvency source. Integrations
must use the defined accrual counters, pending amounts and events. This review
does not assign new economics to that unused field.

Final build and execution results are recorded in `verification/ci.json` and
the generated CU evidence. This is an internal source and execution review;
it does not establish absence of all defects.
