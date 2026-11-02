# Contract audit remediation — 2 November 2026

This change remediates the outstanding findings from the prior contract review.
No program deployment is part of this work. The normal upgrade authority and
Config pause powers remain privileged controls.

## Completion preserves holder exits

Status 1 is a reversible reserve cap while the graduation adapter is absent.
New buys fail at the cap, but both room-token and door-token sells use the
same curve redemption and fee accounting as status 0. A sell that reduces
reserve below the copied trigger sets status 0 and permits buys again.
Converting between doors and claiming fees remain available at the cap.
Unsupported status-2 trades still fail closed. `retire_pending` retains its
existing cap and permanently retired inventory.

Regressions cover a crossing buy, conversion at the cap, door redemption,
reaching the cap again, room redemption, full holder exit and resumed buys.
A separate retirement test reaches the cap with pending fees, exits all held
tokens, preserves retired tokens and resumes buying. Rounding surplus remains
locked and is never credited to holders or fee claims.

This fixes the forced wait for an upgrade; it does not implement Meteora
graduation. A future adapter must account for reserve changes before migration.

## Flat fees require a signed ceiling

`Launch.max_fee_lamports` is part of both launchers' and matchers' signed bytes.
Creation compares the combined room and initial door fee against it; opening
compares the door fee. `convert` takes a separate `max_fee_lamports` argument.
The checks occur before handler-side mint/vault creation or token movement;
Anchor account initialization also rolls back on failure. Lower fees are
allowed and only the actual Config fee accrues. Default launch/conversion
fees remain zero.

The IDL and test clients are updated. Old payloads missing the ceiling fail
deserialization, including when fees are zero. Clients must rebuild against
the updated instruction interface. Config, Room, Door and SlugLock layouts
are unchanged. The new `FeeLimit` error is appended, preserving old codes.
The ceiling covers flat protocol fees only; separately signed first-buy
spend and min-out arguments constrain the trade, and rent/network fees remain
separate costs.

The regression signs each of create/open/convert with a zero ceiling, changes
Config using another admin signer, then submits the identical signed bytes.
It requires `FeeLimit`, verifies every other account is unchanged, and permits
only the normal network fee to debit the victim. Boundary cases cover combined
launch fees, exact ceilings, lower execution fees and missing legacy fields.

## Config and exact curve arithmetic

Config rejects a trigger that cannot purchase one base unit, a combined launch
fee that overflows u64, and a trading fee of 100% or more. Inverse and reachable
quote validation fail with `BadConfig` without writing settings. Both initial
Config creation and updates share this validation.

Reserve quotes now compute `floor(V_sol * q / (V_tok - q))` in u128, then narrow
the result. This equals `floor(V_sol * V_tok / (V_tok - q)) - V_sol` exactly,
but avoids narrowing the virtual-plus-real reserve before subtraction. A
previously overflowing intermediate with `V_sol = u64::MAX` now quotes, buys
and redeems successfully; genuinely unrepresentable results still fail.
Boundary arithmetic is compared with the original exact u128 reference.

## Dependency remediation and remaining maintenance notices

Cargo resolved `ctutils 0.4.7` and `solana-secp256k1-recover 3.3.1`, the latter
updating its host-side k256/elliptic-curve chain to `crypto-bigint 0.7.10`.
These resolve [RUSTSEC-2026-0385](https://rustsec.org/advisories/RUSTSEC-2026-0385.html)
and [RUSTSEC-2026-0387](https://rustsec.org/advisories/RUSTSEC-2026-0387.html).
The Agave VM remains pinned at 4.3.2; no unrelated runtime upgrade is included.

The fresh OSV scan covers exact versions in both lockfiles, including dev/host
dependencies. Five upstream maintenance notices remain:

| Package | Path / rationale |
|---|---|
| ansi_term 0.12.1 | LiteSVM test VM dependency; upstream replacement required. |
| bincode 1.3.3 | Anchor/Solana ABI and VM serialization dependency. No drop-in maintained version; changing serialization requires upstream coordination. |
| derivative 2.2.0 | arkworks 0.4 build/procedural-macro dependency. |
| libsecp256k1 0.7.2 | Agave test-runtime syscall implementation. |
| paste 1.0.15 | arkworks 0.4/0.5 build/procedural-macro dependency. |

They are disclosed maintenance risks, not claimed fixes or proof of exploitability.
`dependency-policy.json` accepts only these exact package/version/advisory
triples when OSV still labels them maintenance-only. CI runs the scanner with
`--check`, failing on vulnerabilities, newly reported notices or version drift.
The full refreshed report is `verification/dependency_audit.json`.

## Verification

The Linux CI workflow checks formatting, locked host compilation, both SBF
builds, generated IDL equality, account layouts, the SBF regression suite,
10,000 mixed-operation iterations and immutable build inputs. Execution evidence
is emitted to `verification/audit_fee_race.json`, `svm_report.json`, `packets.json`
and `build.json`; final run details are recorded after CI completes.
