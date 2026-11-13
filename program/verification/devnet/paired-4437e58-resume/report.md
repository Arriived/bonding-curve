# Paired devnet resume: program checks complete, service halted

12 November 2026. All five remaining authorized scenarios completed, followed by the full on-chain program smoke and all six negative requests. The saved-receipt report process then exited with a Windows cp1252 `UnicodeEncodeError`. The owner's stop rule was honored: **no matcher end-to-end request or transaction was submitted**. The report-only encoding defect is fixed, but the live sequence was not resumed. Test funds and entitled fees were recovered.

Program `8tPd1ZUEGxrj5zYu8aeg95cU92nmKWKYKoSaKPqFuZAZ` remains the exact `4437e58` production ELF, deployed at slot 520,996,477. SHA-256: `fc2d615e37c63710326e18a29d157b50b0ad678ef9083e3161007bf43e8e9002`. Closing readback reconfirms the same ELF, deployment slot and production Config. No 50-SOL case or mainnet deployment was attempted. No scenario input was reduced.

[Every on-chain signature and slot, both runs](signatures.csv). The two forged-signature negative requests were refused before execution and have no on-chain slot. The previous allowance preflight refusal remains separately recorded in the CSV. [Prior deployment and stopped-run record](../paired-4437e58/report.md).

## Six completed 0/10-SOL cases against VM

| Initial SOL | Seed dump | Followers | VM A payout SOL | Live A payout SOL | Gap lamports | Integer snapshots matching | Sale signature | Slot |
|---:|---|---|---:|---:|---:|---:|---|---:|
| 0 | no | cash out | 8.097503855 | 8.097503855 | 0 | 4 | `57EZQqcPWgXNfSBi5HTCPVFDowAuqn2EpVcJinnvLJ9d2MnkcTyGtXorMa2xRPe3kxzEcr2oBgYwtX26GrLwBA1x` | 520997473 |
| 0 | no | rotate | 8.097503855 | 8.097503855 | 0 | 4 | `5fC4SmN5a77dbBHJuWSPS8ymG2pwYeewiQREvMuentnWPf3RQHxWaG79NkRvQJxHD4njVQVeJYH1E2CixepXPQQf` | 521580581 |
| 10 | no | cash out | 7.335805961 | 7.335805961 | 0 | 4 | `5GjQbT1cWSr9v3AHH2iJeu856dZ9wjSuCZnwqVgty14HH9HMCbe7N4MdbgKkhKDX11jMjcnjsBBLHdgQsVrNy2hi` | 521583418 |
| 10 | no | rotate | 7.335805961 | 7.335805961 | 0 | 4 | `2MPaTgmHH8EZnDxnTw1ce8syYg2zkT314F3s5uzXhivfni4PGPcz8bLg3QU7Xeso5rqssprwBZLyTQgNLtpKRLXG` | 521585862 |
| 10 | yes | cash out | 3.801439748 | 3.801439748 | 0 | 5 | `4hdLJ8FMaNW6qgAh2dfEgQ4W8vvz3kNLG4SPT8fW3Jn9xCf9igHtM5Ga2F2bahEVuoiY9p36pCJrQSY9MdQuTB5F` | 521588605 |
| 10 | yes | rotate | 3.801439748 | 3.801439748 | 0 | 5 | `3c52JFWHEhL5Hfh6MMfrg1XAhwqcPEvfzvLjBnQWz4MyQmyMUa28bTgauERXco2qy7wH3W4PhXvot6NiVNWt2Doo` | 521591025 |

All 26 recorded integer snapshots match: room sold/reserve and every door's sold/backing balance. Maximum room-price-multiple gap is 0.0; maximum FDV gap is 0.0 SOL. The 0-SOL cash-out row is the reviewed prior completion. The other five rows and 22 snapshots belong to this resume. The runner includes allowance fix `78ddb1b` and exact-five selector `db8d718`.

## Live CU and bump-search term

| Shape | Live program CU min | Live program CU max | Live transaction CU max | Peak slot | Trace at peak |
|---|---:|---:|---:|---:|---:|
| create_room | 218,163 | 368,602 | 368,902 | 521582793 | 44 |
| open_door | 134,309 | 263,677 | 263,977 | 521580048 | 31 |
| buy_door | 66,091 | 102,030 | 102,330 | 521593093 | 12 |
| sell_door | 55,783 | 75,099 | 75,399 | 521580581 | 5 |
| swap_doors | 79,495 | 123,059 | 123,359 | 521580621 | 11 |

There were 60 successful paired-scenario swaps plus the smoke swap. Peak `swap_doors`: 123,059 program / 123,359 transaction CU, `2x2MBNGzxZZiXoBfvxfEfviwMuVVzoekZQRb4BVUuYXU5jNcKpJ7tDq3e4hzivj6mkyPiYBdML2zrt44cG5LKwWc`, slot 521580621, trace 11. Peak observed transaction CU across launches and trades was 368,902, leaving 131,098 under the service's 500,000 limit. This is an observed margin, not a worst-case bound.

Live Token-2022, classic token and ATA binaries match the pinned VM hashes. The old 17–21k token-binary drift must not be added again to this measured comparison. As in `scripts/bump_drift.py`, each extra PDA search try is modelled at 1,500 CU; repeated derivations in the paired handler are included (17 searches without first buy, 29 with it). Residual includes metadata, trade-size, liveness and runtime effects; it is not a pure token-program delta.

| Creation slot | First buy | Live program CU | VM fixture CU | Measured gap | Tries live/VM | Bump term | Residual |
|---:|---|---:|---:|---:|---:|---:|---:|
| 521579995 | False | 225,631 | 225,246 | +385 | 32/32 | +0 | +385 |
| 521582793 | True | 368,602 | 337,694 | +30,908 | 83/63 | +30,000 | +908 |
| 521585335 | True | 307,114 | 337,694 | -30,580 | 42/63 | -31,500 | +920 |
| 521588009 | True | 332,588 | 337,694 | -5,106 | 59/63 | -6,000 | +894 |
| 521590427 | True | 328,236 | 337,694 | -9,458 | 56/63 | -10,500 | +1,042 |
| 521593045 | False | 239,285 | 225,246 | +14,039 | 41/32 | +13,500 | +539 |

## Program smoke, negative sequence and stop

Every on-chain smoke transaction succeeded: create/open, both door buys, sell, swap, room-token buy, pending retirement and fee claim. Mint authorities, supply, vault backing, curve reserve, the 60/40 fee split and NameLock readback pass. All 12 client NameLock key vectors pass, and all five fresh scenario locks match the service key independently.

All six negative cases produced their expected result: missing matcher signatures (two on-chain AccountNotSigner refusals), changed signed routing data (two RPC SignatureFailure refusals), overselling (Token-2022 InsufficientFunds) and wrong fee recipient (Authority). No unexpected program refusal or state mismatch occurred.

The report renderer crashed while printing U+2212 under cp1252, before its assertion summary. Rendering the same saved receipts offline with UTF-8 passed **34/34** checks without sending a transaction. A permanent regression failed on `db8d718` and passes with `9594aad`; both Linux and Windows CI now run it. The report explicitly emits UTF-8. This host-report defect did not change the deployed program or invalidate completed transactions. [Original error](smoke-check.stderr.txt); [offline 34/34 checks](smoke-check-offline.stdout.txt).

The matcher client is prepared and pushed as `a7aa8c0`, but has **not been run live**. During preparation, two ordinary regressions exposed a verifier omission on `584596a`: `open_door` did not replay candidate NameLock history. `310e12a` fixes the floor and T2n paths. Both tests and all 180 service tests pass. No routing, authentication or normalization rules changed. A real signed launch, door route and verifier agreement remain outstanding.

## Sweep and true whole-qualification cost

| Item | Lamports | SOL |
|---|---:|---:|
| Original opening | 46,544,000,361 | 46.544000361 |
| Additional funding since prior close | 10,000,000,000 | 10.000000000 |
| Resume opening | 53,344,866,003 | 53.344866003 |
| Closing treasury balance | 53,089,376,282 | 53.089376282 |
| Whole qualification cost | 3,454,624,079 | 3.454624079 |
| This resume cost | 255,489,721 | 0.255489721 |
| Retained account rent | 3,439,800,080 | 3.439800080 |
| Retained balances above rent | 1,867,201 | 0.001867201 |
| Network fees, both runs | 12,956,798 | 0.012956798 |

Closing balance is finalized at slot 521596121. All 24 other operating wallets are zero; all 50 Token-2022/classic-token owner scans are empty. Positions, entitled native/swap fees and wallet balances were recovered. Persistent rent and the reserve/pending balances enumerated in [accounting.json](accounting.json) remain on-chain; the program was not closed. Whole cost includes the prior deployment, completed case, stopped case and recovery. External funding is added before subtracting closing balance. The reconciliation is exact, and resumed network fees independently equal the sum of fee receipts.

The CSV includes 1,800 finalized signatures across both runs and external funding; 800 belong to this resume. Expected landed refusals across both runs: 5. The earlier allowance preflight refusal had no execution fee.

[Final program CI](https://github.com/Arriived/bonding-curve/actions/runs/43308113879) and [Windows CI](https://github.com/Arriived/bonding-curve/actions/runs/43308113918) passed on `9594aad`: 73 SBF tests with 10,000 property iterations against pinned SPL binaries, four client tests, the report regression, heap probe and 400,000 curve cases. Creation retained at least 4,304 heap bytes. The rebuilt ELF hash remains exactly pinned. The service passed 180 tests; its full 1,223-target evasion JSON repeats byte for byte. [Verification details](ci-verification.json). Graduation design, lookup tables and shelved maker work were not performed.

| Rank | Severity | Finding | Status | Cost and payoff |
|---|---|---|---|---|
| 1 | Low | Door verifier omitted candidate NameLock history | Fixed, 310e12a | Two regressions; restores independent verification of floor/name routes |
| 2 | Info | Windows report output could not encode mathematical symbols | Fixed, 9594aad | One regression, no ELF change; saved 34/34 report works in both environments |
| 3 | Info | Real matcher launch/door/verifier agreement | Not run after stop | Prepared client; requires the remaining live service qualification |
