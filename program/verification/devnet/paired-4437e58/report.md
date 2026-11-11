# Paired doors devnet: deployed; qualification stopped and recovered

11 November 2026. Program source `4437e58`; only the 0 and 10 SOL cases were authorized. One of six scenarios completed. The 0-SOL rotation case stopped at its first swap because the runner underfunded lazy-vault rent. The four 10-SOL cases and the program smoke were not run. The 50-SOL cases remain VM-only. Recovery completed; no scenario inputs were reduced.

## Deployment and production Config

| Item | Result |
|---|---|
| Program | `8tPd1ZUEGxrj5zYu8aeg95cU92nmKWKYKoSaKPqFuZAZ` |
| Deploy signature | `23b2XfG4xXhyZ6uhxNiJ7Qm1os3b67W2jYKRSJfq9m9iik3Na9Bw5NToLMYBDyuijhwj9P5SqH15GnSF7qoEmtwp` |
| Deploy slot | 520,996,477 |
| Final hash-read slot | 521,005,365 |
| ELF SHA-256 | `fc2d615e37c63710326e18a29d157b50b0ad678ef9083e3161007bf43e8e9002` |
| ProgramData | `Edv3YGm1FGZfjcHCAhMGYsffvGRoPYnkToeq5bVg2hJm` |
| Upgrade authority | `8AjgpyhTB5NnLx5ojzXbeTpcJjHjf7t71GRQZnJqmhdx` |
| Production Config | `J2bC431hNTQqtbQ3fcrLw5vHL6YcEqGnW72nyoyBHxZg`; 0 mismatches across 22 checked fields, read slot 520,996,551 |
| Initialize signature / slot | `4izewk4svpn6cwAcaSU7Wc4WXDrKhDSy5yJ1CBq9k4jGMoZgUe3XESiCm6EEhgcgPY32JcqXBxuaGtijuGTJxD3z` / 520,996,544 |
| Production graduation ceiling | 85,018,013,680 lamports |
| 120-SOL refusal signature / slot | `s7ddCKxNreRxddtKRMEfhk8YkVZfcSiw4yXmZh9Vxu7Wa34k25xKs5dPaX1U5yXvbEXG5um85sPYRdLNC1th6ah` / 520,996,578 |
| Config after refusal | Unchanged, read slot 520,996,589; `BadConfig` |

The deployed bytes are exactly the 611,752-byte pinned ELF. ProgramData has 45 bytes of loader metadata. The final read confirms the same deploy slot and upgrade authority after recovery. Config uses the production profile, including 100-bps fees, 60% door share, zero founder share and zero flat launch fees. The test-only stress feature is absent.

The official Windows Agave 4.3.2 CLI performed deployment; the cluster reports 4.4.0. Its release archive matched SHA-256 `ce29128589045fe1964e9d5c064ea5f2a58151f707bae4d5bab345a3725e0f09`. Bulk RPC writes were stopped after rate limiting/timeouts. The same named buffer was completed using paced acknowledged writes, hash-checked, then consumed by deployment. No buffer rent was stranded. All signing stayed local.

## Scenario outcome

| Room SOL | Dump | Follower exit | Result | VM A payout | Live A payout | Gap |
|---:|---|---|---|---:|---:|---:|
| 0 | False | Cash-out | Completed | 8.097503855 | 8.097503855 | 0 lamports |
| 0 | False | Rotation | Stopped at first swap; recovered | — | — | — |
| 10 | Both authorized dump settings | Both exits | All four unrun | — | — | — |

Every integer room and door state in the completed case matches the VM snapshots. Price multiples and FDVs also match. A payout is after the program fee and before transaction fees and rent. Its sale was signature `57EZQqcPWgXNfSBi5HTCPVFDowAuqn2EpVcJinnvLJ9d2MnkcTyGtXorMa2xRPe3kxzEcr2oBgYwtX26GrLwBA1x`, slot 520,997,473.

The first rotation wallet had 1,563,998 lamports after its two ATAs and 1-SOL buy. After reserving the 5,001-lamport transaction fee, its first 1,488,440-lamport vault left 70,557 lamports; the second needed another 1,488,440. It was short **1,417,883 lamports for the swap alone**. RPC preflight refused the transaction; it was not broadcast or charged. `interrupted-signatures.json` records its signature with no landed slot.

The executing client was built from `6b41df5` (SHA-256 `f5e3f102db2351aa3bcbf0131309544bf63252ba86a675e75815835146a3d29f`). Its allowance formula was inherited from `4437e58`. The runner allowance omitted both lazy vaults. The live failure supplied the failing integration test. Runner-only fix `78ddb1b` adds their rent before each scenario: the allowance rises from 4,601,680 to 7,578,560 lamports per follower at the measured tariff. This adds 0.059537600 SOL of temporary prefunding across 20 followers. Its permanent regression covers two user ATAs, two lazy vaults, seven transaction fees and the native rent floor. All three client tests pass. The fix has not been used to resume live scenarios under the owner's stop rule. The program ELF and rent-saving design are unchanged.

## CU comparison

Devnet Token-2022, classic SPL Token and ATA bytes all match the pinned VM binaries (read slot 520,994,003). Each measured transaction uses a 500,000-CU limit and a price of 1 micro-lamport/CU. Program CU includes CPIs; transaction CU also includes both compute-budget instructions.

| Creation | Live program CU | VM program CU | Measured gap | Modeled bump-search gap | Residual |
|---|---:|---:|---:|---:|---:|
| Slot 520,996,795 | 239,177 | 225,246 | +13,931 | +13,500 | +431 |
| Slot 520,999,363 | 218,163 | 225,246 | -7,083 | -7,500 | +417 |

The model counts repeated PDA searches, including identity locks and lazy-account validation, and charges 1,500 CU per additional bump try. Its per-derivation evidence is in `live-vm-comparison.json`. Residuals also include metadata, arithmetic, liveness-bucket and runtime differences; they are not a pure feature-cost measurement. These are ordinary zero-first-buy creations, not the maximum-metadata first-buy stress fixture.

| Shape | VM ordinary priority CU range | Live priority CU range | Live peak − VM peak | Peak live slot | Trace at peak |
|---|---:|---:|---:|---:|---:|
| create_room | 225,546–337,994 | 218,463–239,477 | -98,517 | 520,996,795 | 30 |
| open_door | 150,510–273,681 | 140,734–247,432 | -26,249 | 520,999,402 | 31 |
| buy_door | 92,012–92,012 | 69,278–78,543 | -13,469 | 520,999,469 | 7 |
| sell_door | 58,378–58,378 | 64,564–69,401 | +11,023 | 520,997,532 | 5 |
| swap_doors | 109,430–109,430 | Unmeasured live | — | — | — |

The ranges contain different fixture inputs; the per-creation bump table above compares the matching zero-first-buy shape.

Observed peak transaction CU was 247,432, leaving 252,568 CU against 500,000 for the successfully observed shapes. Full live coverage is incomplete. The separate pinned-VM worst-launch stress remains 402,166 CU / 97,834 CU margin; no rent saving or price/reserve guard was removed.

## NameLock, smoke and verification

The 12 offline NameLock vectors passed, and both live NameLocks were read back against the service's exact key calculation (2/2 matched). The full program smoke and negative-case sequence were not started after the stop.

[Verification run 42967648576](https://github.com/Arriived/bonding-curve/actions/runs/42967648576) passed all 73 SBF tests, 10,000 property iterations, isolated stress-feature checks, heap probe, 400,000 curve-fuzz cases and three client tests. [Windows client run 42967648571](https://github.com/Arriived/bonding-curve/actions/runs/42967648571) is also green. Service end-to-end, graduation design and M-7 work were not performed. M-7 remains a pre-mainnet blocker.

## Recovery and actual cost

`paired-cleanup` sold the interrupted case's positions, closed its empty ATAs and swept its wallets. The final recovery claimed entitled fees, closed the remaining test token accounts and swept the admin wallet. All 24 test, admin and matcher wallets are at zero and all 50 classic/Token-2022 ownership scans are empty. Both rooms have no native balance above their account rent. The deployed program remains open.

| Item | SOL |
|---|---:|
| Opening balance, slot 520,987,644 | 46.544000361 |
| Closing balance, finalized slot 521,004,319 | **43.344866003** |
| Net balance decrease | **3.199134358** |
| Persistent account rent | 3.190453360 |
| Native reserve/fees above rent | 0.000000000 |
| Network-fee residual from reconciliation | 0.008680998 |
| Deployment rent, included above | 3.109412120 |
| Deployment/upload fees, included above | 0.007265726 |

The six-case budget helper quoted 41.446756899 SOL using stale deployment rent. Fresh rent for the pinned ELF raised that conservative estimate to 41.583591779 SOL, within the 46.544000361-SOL opening funds. The observed stop was the runner's individual wallet allowance. Recovery did not reduce a scenario's follower count, buy size or initial reserve.

[signatures.csv](signatures.csv) lists all 998 finalized transaction signatures and slots, plus the one preflight-rejected request with no slot. The on-chain 120-SOL refusal is the sole expected failed transaction. [final-receipts.json](final-receipts.json) records finalization status and source reports; [accounting.json](accounting.json) contains every closing wallet balance and retained account rent. No signing material is included.
