# Doors v1 deployment

4 November 2026.

## 1. Status

| part | status |
|---|---|
| program ID, upgrade authority, matcher authority | generated; public keys in §2 |
| build of the deploy source | done; 34/34 SBF tests passing; ELF pinned in `devnet/DEPLOY_ELF.sha256` (§3) |
| **devnet deployment** | **PENDING.** The deploy wallet has no devnet SOL. The devnet RPC faucet is closed, the web faucet refused the owner's accounts, and every on-chain proof-of-work faucet was empty or paid less than its fee. See §5. |
| end-to-end test, localnet | **PASS**, 33 of 33 checks (§7) |
| **end-to-end test, devnet** | **PENDING.** It is built and switched by one line (§7); it exits 3 with a PENDING message until §5 is done. |
| upgrade-authority policy for mainnet | open owner decision (§8) |

## 2. Program ID and authorities

| role | public key | keypair file |
|---|---|---|
| **program ID** | `D7YsLsiJXoAF38vCUhFqYStepvSz6goG7EddHDe5NVJG` | `program.json` |
| **upgrade authority** (also the Config admin: `initialize_config` must be signed by it) | `HbvturaYqGpCVqrWV6StwJ3rJdBh2QQr26vyo2Q2nky` | `upgrade-authority.json` |
| **matcher authority**, set in `Config.matcher_authority` | `5Bb2HVR9XeTeNBeM28W2ecdKcwycwPMJqGXmcWtuRrCN` | `matcher-authority.json` |
| deploy wallet (fee payer; devnet protocol fee recipient) | `2eKSWypmuDsBtH6hsZa4u6CgABkdS8vHtNozWPBhB1a2` | `deploy-wallet.json` |
| e2e launcher (door 0 creator) | `3jyDH3Z5qLac28FKveDJF3Kp9Znkhu38QSv83SvBnX9k` | `smoke-launcher.json` |
| e2e trader (door 1 creator) | `vWDZPiFpy3rikaPdyuL7o9CkbCrvpkbiVuuUMrG3KEh` | `smoke-trader.json` |

The program ID comes from the keypair, so it is the same on every cluster.

**Where the keypairs are.**

- All six files are in one directory in the cloud session that generated them,
  outside every git work tree, with mode 600.
- They were generated with `solana-keygen new --silent`, so no seed phrase was
  printed.
- That directory is **not in this repository and will not survive the
  session**. The owner holds the only copies once they are copied off.
- `program/.gitignore` ignores `*-keypair.json`, `*.keypair.json`, `keys/` and
  `/devnet/target/` in addition to `/target/`. The `anchor keys sync` copy at
  `target/deploy/doors_v1-keypair.json` is covered by `/target/`.
- The deploy scripts pass a pre-generated buffer keypair, so the CLI never
  prints a recovery seed.
- No private key appears in any committed file. Every committed file was
  scanned for each key in base58, hex and JSON-array form.

**Losing `program.json` loses this program ID.** Losing
`upgrade-authority.json` makes the program unupgradeable and Config unchangeable.

## 3. What is deployed

| | |
|---|---|
| source | commit `436c002` plus the program-ID change only (`verification/devnet/deployed_source.patch`: `declare_id!`, `Anchor.toml`, IDL address) |
| why not the brief's `054be58` | it lacks 13 commits of audit fixes; `436c002` is the newest commit whose full SBF suite passes (34/34) |
| why not the tip `8ce373f` | 10 of 38 SBF tests fail with `UnbalancedInstruction` ([CORRECTIONS](CORRECTIONS.md), devnet preflight item 1) |
| ELF | 525,032 bytes, SHA-256 `f2cfdb853ba77f6783221a98963c54fcaa730575cf79567814d164045669b436`, pinned in `devnet/DEPLOY_ELF.sha256`. `deploy.sh` refuses any other binary. |
| IDL | byte-identical to `anchor idl build`, SHA-256 `f70a0c64873c68e109d41ae64404b7ccd47d61e80de591d541195902925ab8f1` |
| tests on this exact source | `cargo test --locked --test svm`: 34 passed, 0 failed; `cargo fmt --check` clean; `check_layouts.py` passes |

**`program/devnet` builds against the deploy source, not the tip.** The tip
adds `Launch.expected_terms_hash`. To build the client, check out `436c002` and
apply `deployed_source.patch`.

## 4. Toolchain and build verifiability

Exact versions, all matching the README's declared build target:

| tool | version | source |
|---|---|---|
| host Rust | `rustc 1.99.0 (b940084d7 2026-09-28)`, `cargo 1.99.0 (5f94df478 2026-08-27)` | rustup |
| cargo-build-sbf | 4.5.0, run with `--tools-version v1.58` | `cargo install cargo-build-sbf --version 4.5.0 --locked` |
| SBF compiler (platform-tools v1.58) | `rustc 1.95.0-dev (1e20dd0d5 2026-10-05)` | GitHub release download |
| Anchor CLI | 1.2.2 | `otter-sec/anchor` release binary, SHA-256 `e2c35a97…e741` |
| Solana / Agave CLI | `solana-cli 4.4.0 (src:9ef63128; feat:dddabd53, client:Agave)` | `anza-xyz/agave` v4.4.0 GitHub release tarball, SHA-256 `3363f472…c574` (release.anza.xyz is unreachable from this environment; the release's `.yml` names commit `9ef63128134af559561f6a91a641ec01e665c70d`) |
| SVM test runtime | LiteSVM 0.18.1 with Agave 4.3.2 | Cargo.lock |
| local validator for §7 | `solana-test-validator` from the same Agave 4.4.0 release | |

Neither release publishes a checksum file, so the hashes above are of what was
downloaded, not checked against a published value.

**Verifiable build: not available for this toolchain** (CORRECTIONS item 4).
No `solana-verifiable-build` image exists for Agave 4.4.0, and no Anchor 1.2.2
image exists. What stands in for it:

1. **The pinned build is reproducible.** `436c002` built here gives exactly
   the ELF hash CI recorded on GitHub's runner for the same program code
   (`a5bccfad…71af`), in a different directory on a different machine.
2. **The deployed bytes are compared with the pinned ELF.** `deploy.sh` dumps
   the deployed program and fails unless its hash equals the pinned ELF.

## 5. Devnet deployment — PENDING

The deploy wallet `2eKSWypmuDsBtH6hsZa4u6CgABkdS8vHtNozWPBhB1a2` needs about
3.5 devnet SOL. Every route tried has failed:

| route | result |
|---|---|
| `solana airdrop` / `requestAirdrop` | `410 "The RPC faucet is closed on this cluster"` |
| faucet.solana.com, by the owner | refused for three GitHub accounts: per-8-hour limit, or accounts too new or with too few public repos |
| on-chain proof-of-work faucet (`PoWSNH2hEZogtCg1Zgm51FnkmJperzYDgPK4fvs8taL`), owner-approved | 24 faucets at slot 518,709,929; 23 empty, and the one funded faucet pays 100 lamports per claim against a 5,000-lamport fee plus receipt rent |

**Once funded**, from `program/` on the deploy source:

```sh
devnet/deploy.sh https://api.devnet.solana.com <keys_dir> verification/devnet/devnet
```

`deploy.sh` records the program ID, deploy signature, deploy slot, ProgramData
account and the on-chain ELF hash. It also initialises Config and checks every
field. Then run the end-to-end test against devnet (§7).

**Cost on devnet** (Rent sysvar at slot 518,695,292: 5,080 lamports per byte):

| item | cost |
|---|---|
| ProgramData for the 525,032-byte ELF | 2.668 SOL |
| program account | 0.00083 SOL |
| upgrade-authority top-up for Config rent | 0.05 SOL |
| e2e wallet top-ups | 0.6 SOL each, two wallets |

## 6. Mainnet: what differs

1. **Keys.**
   - Generate the program and upgrade-authority keys on hardware the owner
     controls, not in a cloud session.
   - Store the upgrade authority offline, or as a multisig (§8).
   - The matcher key lives with the matcher service. It must not be the
     upgrade authority or the admin.
2. **Config admin.** `initialize_config` makes the current upgrade authority
   the Config admin. To separate them, hand admin to a distinct key with
   `update_config(settings, new_admin)`.
3. **Protocol fee recipient.** Devnet uses the deploy wallet. Mainnet needs the
   real treasury address.
4. **Cost.** ProgramData is 2.668 SOL at the current 5,080 lamports-per-byte
   rent, plus buffer-write fees, with a priority fee under load.
5. **Order.** Deploy only an ELF that has passed the devnet end-to-end test,
   from a fresh session.
6. **Do not deploy the tip `8ce373f`** until its regression is fixed.

## 7. End-to-end test

**What it is.** `devnet/e2e.sh <keys_dir>` runs against the deployed program:

- the smoke sequence: `create_room` with a matcher-signed decision and door 0;
  `open_door`; a buy through door 0; a buy through door 1; a sell; a
  `convert`; a direct room-token buy; `retire_pending`; `claim_door_fees`;
- the six failure cases;
- the 33 hard checks below (`devnet/report.py --check`).

It exits non-zero if any check fails. The checker was itself tested: tampering
four conditions in a copy of the outputs produced four FAILs and exit code 1.

**Which cluster it runs against: one line.** The file `devnet/e2e-target`
contains `localnet`.

| `devnet/e2e-target` | what `e2e.sh` does | status |
|---|---|---|
| `localnet` | Starts a fresh `solana-test-validator` and funds the wallets locally. Deploys the pinned ELF and initialises Config through `deploy.sh`, then runs the test. Outputs go to `verification/devnet/localnet/`. | **PASS**, 33/33 |
| `devnet` | Requires the §5 deployment. Tops up the two e2e wallets from the deploy wallet, then runs the same test against devnet. Outputs go to `verification/devnet/devnet/`. Until the program is deployed there, it prints `PENDING: … is not deployed on devnet yet` and exits 3; this was verified by flipping the line. | **PENDING** (`verification/devnet/devnet/PENDING.md`) |

**Switching to devnet once it is deployed:**

```sh
echo devnet > devnet/e2e-target
devnet/e2e.sh <keys_dir>
```

**Limits of the localnet result:**

- It uses the test validator's bundled Token-2022 and ATA binaries.
- It uses the test validator's default feature set.
- It uses the old 6,960 lamports-per-byte rent (ProgramData there costs
  3.63 SOL).
- Its slots are local.

The devnet run replaces all four, and its tables replace the ones below.

### Localnet run

| item | value |
|---|---|
| program ID | `D7YsLsiJXoAF38vCUhFqYStepvSz6goG7EddHDe5NVJG` |
| deploy signature | `zc7PNuBFuTT3n7fCRQ1K9e3ipW5PhnC2XBXQVHgFM7EbFfMCra6GvLbtQxXHJBjVQWToFftGG4buLycdaoapbpw` |
| deploy slot (`lastDeploySlot`) | 17 |
| ProgramData account | `4SbbsdYLxSgVP42JRpGj6DZVSBp9tVas8iTRQfiFjMNi` |
| upgrade authority | `HbvturaYqGpCVqrWV6StwJ3rJdBh2QQr26vyo2Q2nky` |
| ProgramData lamports | 3,630,482,160 |
| local ELF SHA-256 | `f2cfdb853ba77f6783221a98963c54fcaa730575cf79567814d164045669b436` |
| on-chain bytes SHA-256 (first ELF-length bytes of `solana program dump`) | `f2cfdb853ba77f6783221a98963c54fcaa730575cf79567814d164045669b436` |
| on-chain bytes equal local ELF | yes |
| Config account | `4jJfFvgAyPsnX6P95Wd4huf5BCyYaow771kdZpqbbpWw` (read at slot 23, 248 bytes) |
| Config fields differing from settings | 0 of 22 |

**Config read back against the generated settings:**

| field | on-chain | expected | match |
|---|---|---|---|
| `admin` | `HbvturaYqGpCVqrWV6StwJ3rJdBh2QQr26vyo2Q2nky` | `HbvturaYqGpCVqrWV6StwJ3rJdBh2QQr26vyo2Q2nky` | yes |
| `protocol_fee_recipient` | `2eKSWypmuDsBtH6hsZa4u6CgABkdS8vHtNozWPBhB1a2` | `2eKSWypmuDsBtH6hsZa4u6CgABkdS8vHtNozWPBhB1a2` | yes |
| `fee_bps` | `100` | `100` | yes |
| `door_share_bps` | `6000` | `6000` | yes |
| `founder_share_bps` | `0` | `0` | yes |
| `door_fee_lamports` | `0` | `0` | yes |
| `room_fee_lamports` | `0` | `0` | yes |
| `convert_fee_lamports` | `0` | `0` | yes |
| `v_sol_lamports` | `30000852995` | `30000852995` | yes |
| `v_tok` | `1073025606000000` | `1073025606000000` | yes |
| `supply` | `1000000000000000` | `1000000000000000` | yes |
| `r_star_lamports` | `85000000000` | `85000000000` | yes |
| `meteora_dynamic_config` | `11111111111111111111111111111111` | `11111111111111111111111111111111` | yes |
| `graduation_trigger_lamports` | `85018013680` | `85018013680` | yes |
| `paused` | `false` | `false` | yes |
| `matcher_authority` | `5Bb2HVR9XeTeNBeM28W2ecdKcwycwPMJqGXmcWtuRrCN` | `5Bb2HVR9XeTeNBeM28W2ecdKcwycwPMJqGXmcWtuRrCN` | yes |
| `live_min_reserve_lamports` | `500000000` | `500000000` | yes |
| `live_max_idle_seconds` | `21600` | `21600` | yes |
| `live_new_seconds` | `3600` | `3600` | yes |
| `live_min_volume_lamports` | `5000000000` | `5000000000` | yes |
| `pool_min_window_lp_fee` | `80000000` | `80000000` | yes |
| `bump` | `254` | `254` | yes |

**Transactions, live CU against the VM measurement of the same ELF:**

| step | signature | slot | live program CU | VM min–max CU (same ELF) | live − VM max |
|---|---|---|---|---|---|
| initialize_config | `3HexQQU9RKzcvHbC7Hcbo2BuAehT9qRGunmv7m4T2ScSwZibenEu5VnJ1avun9oFT4kKQV2Ay7acGrgTzoTnvNfa` | 22 | 13,347 | 13,347–13,347 (n=1) | +0 |
| create_room | `33SWLrA3vAPnneHgENmLhaQjWt4uhzfYkDuBkaueqHSu6DH6PUG3Zq168zf96XXNq8iQWLPpfA2pLhaZeakcCfPs` | 24 | 207,607 | 219,879–219,879 (n=1) | -12,272 |
| create_atas_launcher | `613Jae56eyLqQyNXz4RmLbgs9VTtG879HUarYtmHru18EMc4M7wsrbY4ck2qLAm5w3BRCdovuaaVgryfRZtfjqeK` | 27 | None | not measured | — |
| open_door | `5Tc9MTPaEL9pxCBdDG7QAANH8ba7kfF9wAmtedAY5xxMXSehohBua1qrxBE9TWFqKz4BXBqKDof8hh3VHiQ7Y6GP` | 29 | 123,445 | 118,833–121,715 (n=3) | +1,730 |
| create_atas_trader | `31JBJRnvTeKqgXE2w2ZrE38G8rLGFQQQs2vHpmDujLYkUkhtLWwp5wdmbgj8ojP6cjJHQKCSkLEvgLzFAKuzVkeo` | 32 | None | not measured | — |
| buy_door0 | `4KgbCFcnzjsQHHU41UqLzrFtYLbVHNg7hwNdPo9R8NRNHDnMq9BYPQA7ucNu2BAeREBB3ZHxVKgU7RJ6pqZsyKAH` | 34 | 62,327 | 66,677–71,380 (n=3,348) | -9,053 |
| buy_door1 | `63aDQSgbRNBTbTcWhiYmapUDYwr88Y2tLq6qsgEDmNyKskSYk9aKf6QDSTCFoU4i8MLTeTDkjYu2BmnsfLMVV4Ue` | 37 | 73,060 | 66,677–71,380 (n=3,348) | +1,680 |
| sell_door0 | `39dbgGaAxU7VTofhqfWfW4NzyGPmysMvEAteodkZ5gp78tp4m8poeNgpc9iwkJxziLfZdw8FqrnAtBX8xwPt5TyX` | 39 | 59,782 | 64,089–68,603 (n=1,673) | -8,821 |
| convert_door0_to_door1 | `KF3JMA3YjSxCzTuYM4e5WNyyK719SdAdupPjCL6NPu666Dd4srmm6SPGBGZaWmb5pJYDMhPn4WjcV68Euo3UeFN` | 42 | 82,981 | 81,205–85,715 (n=800) | -2,734 |
| buy_room_token | `3VfqJz5ShhA7w4iHP6LvzLqmYDDyCjoWzpjKf8k3EFuDam57MghRz2Y7wbtTNxzDyDMdtaTaerSWJ9Fa5BNEHat` | 44 | 48,780 | 45,722–45,753 (n=840) | +3,027 |
| retire_pending | `2tkGNvBLmAaM227zRgxdCr9uQfPGjj1SsYZpzz57QHbf6zUgeCUrxoevj6FFQPTX9JkbnSm7kkYh5oB9avyxjf9Z` | 47 | 31,331 | 22,585–31,295 (n=829) | +36 |
| claim_door_fees | `5pN2Z6mg9ATTtS37VUjKuvQ4NqfxkwjFgMXCPWDyKJ2gqzaSyYtbQqho2Sw3Tey8NijAfqi1F5iq5Sg9AkMPnWyQ` | 49 | 50,591 | 45,008–51,764 (n=808) | -1,173 |

ATA rows are client setup (Associated Token program), not doors program CU.

**Expected failures:**

| case | landed on-chain | signature | slot | error |
|---|---|---|---|---|
| create_room_without_matcher_signature | yes | `5459LSCJuGH8hP88gHKiwVo8BoRMLUUxezuGc2DoRSt1BV22QyfAx1TFafeVrsYAnryUFKEBeYbiM8uxx6KDU99T` | 52 | {"InstructionError":[1,{"Custom":3010}]}; `Program log: AnchorError caused by account: matcher. Error Code: AccountNotSigner. Error Number: 3010. Error Message: The given account did not sign.` |
| open_door_without_matcher_signature | yes | `3eCDshwbfTCiYHjoyGyvQWcHpU4eawndRmawjTMH7gpFxRnZUpDFFaWvwfR9z237fU3yT1ZbKVXQg64y5kfKhx2w` | 54 | {"InstructionError":[1,{"Custom":3010}]}; `Program log: AnchorError caused by account: matcher. Error Code: AccountNotSigner. Error Number: 3010. Error Message: The given account did not sign.` |
| create_room_signature_over_different_routing_data | no: rejected before execution | — | — | `SignatureFailure`: Transaction simulation failed: Transaction did not pass signature verification |
| open_door_signature_over_different_routing_data | no: rejected before execution | — | — | `SignatureFailure`: Transaction simulation failed: Transaction did not pass signature verification |
| sell_exceeding_balance | yes | `4Md9uRjWZS1iLiCnXLBxMxsN8cA1xC9aAQzLr1G85ER3SGW7C7bsPkipFuSGXuCXLpH6PK49xGZXMfCk2u7Yrrdb` | 57 | {"InstructionError":[1,{"Custom":1}]}; `Program TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb failed: custom program error: 0x1` |
| claim_door_fees_by_non_recipient | yes | `2SQ7t5veFzbZpxbqYfmG9SerD3qgsHsArpYczVpiJ8rSBdQyCi6MCwb21u87FDGfebvZgt9AVMiCzCVUCMxvGZPC` | 59 | {"InstructionError":[1,{"Custom":6006}]}; `Program log: AnchorError thrown in programs/doors_v1/src/lib.rs:750. Error Code: Authority. Error Number: 6006. Error Message: Unauthorized.` |

**On-chain state checks after the sequence:**

| check | result |
|---|---|
| room mint `AdetfjrniVDXtszQQADMBqUn1auJzbjVJfPCKBaeCpyj`: supply, mint/freeze/metadata authorities | 1000000000000000, None, None, None → ok |
| door 0 mint `3p5UATBQ2QNH1SmckZZcqKJy9ty2EpajtGUfXkHdUBRg`: supply, authorities | 1000000000000000, None, None, None → ok |
| door 0 backing vault vs circulating door supply | 882397366623 vs 882397366623 → equal |
| door 1 mint `BXyiwqF7LHfcCkdj2Dujz38iCCowm3DR16XfjoQkJKgX`: supply, authorities | 1000000000000000, None, None, None → ok |
| door 1 backing vault vs circulating door supply | 4388842602598 vs 4388842602598 → equal |
| reserve vs curve integral of `sold` | 197908792 vs 197908792 → covers |
| ReserveVault lamports − rent vs `reserve` | 197908792 vs 197908792 → covers |
| RoomVault vs unsold supply | 992967883781714 vs U − 7032116218286 → covers |
| fee counters vs 60/40 split of every Trade event's fee | expected {'door0': 893538, 'door1': 594060, 'fee_total': 2974380, 'founder': 0, 'pending_reserve': 297030, 'protocol': 1189752}; on-chain {'door0': 893538, 'door1': 594060, 'fee_total': 2974380, 'founder': 0, 'pending_reserve': 297030, 'protocol': 1189752} → match |
| retire_pending | pending 0, reserve +297030 |
| claim_door_fees (door 0) | accrued 0, claimed 893538 |

### Checks

```text
PASS  deployed bytes equal the pinned ELF
PASS  program ID matches the deploy output
PASS  upgrade authority is set (not the deploy wallet)
PASS  initialize_config succeeded
PASS  every Config field matches the settings
PASS  Config matcher_authority equals the smoke matcher
PASS  smoke step create_room landed and succeeded with program CU recorded
PASS  smoke step open_door landed and succeeded with program CU recorded
PASS  smoke step buy_door0 landed and succeeded with program CU recorded
PASS  smoke step buy_door1 landed and succeeded with program CU recorded
PASS  smoke step sell_door0 landed and succeeded with program CU recorded
PASS  smoke step convert_door0_to_door1 landed and succeeded with program CU recorded
PASS  smoke step buy_room_token landed and succeeded with program CU recorded
PASS  smoke step retire_pending landed and succeeded with program CU recorded
PASS  smoke step claim_door_fees landed and succeeded with program CU recorded
PASS  room mint: 1B supply, no mint/freeze/metadata authority
PASS  door 0 mint: 1B supply, no mint/freeze/metadata authority
PASS  door 0 backing vault covers circulating door supply
PASS  door 1 mint: 1B supply, no mint/freeze/metadata authority
PASS  door 1 backing vault covers circulating door supply
PASS  reserve covers the curve integral of sold
PASS  ReserveVault lamports minus rent cover reserve
PASS  RoomVault covers unsold supply
PASS  fee counters equal the 60/40 split of every Trade fee
PASS  FeeVault lamports minus rent cover all fee counters
PASS  retire_pending moved all pending into reserve
PASS  claim_door_fees paid door 0 exactly its accrued fees
PASS  failure case create_room_without_matcher_signature rejected with {"Custom":3010}
PASS  failure case open_door_without_matcher_signature rejected with {"Custom":3010}
PASS  failure case create_room_signature_over_different_routing_data rejected with SignatureFailure
PASS  failure case open_door_signature_over_different_routing_data rejected with SignatureFailure
PASS  failure case sell_exceeding_balance rejected with {"Custom":1}
PASS  failure case claim_door_fees_by_non_recipient rejected with {"Custom":6006}

33 of 33 checks passed
```

**Live CU against the VM.** The VM column is LiteSVM running the same ELF
(`verification/devnet/deployed_elf_vm/`). Live figures in this run range from
12,272 CU below the VM maximum to 3,027 above it:

- `buy_room_token` is 3,027 above the VM maximum;
- `open_door` is 1,730 above;
- `buy_door1` is 1,680 above.

The first localnet run had different per-step figures. The difference is
consistent with PDA bump searches, which vary by address: every run creates a
room at a fresh random nonce, while the VM suite measures one fixed room ID. Two
consequences:

1. **The VM maxima in `verification/cu.md` are not worst cases.** A room's
   nonce alone can push an instruction past them.
2. **Throughput headroom should carry margin above those maxima.** A
   per-instruction distribution over many random nonces would replace the
   single-ID figure. The devnet run gives live samples on the real cluster,
   but not that distribution.

## 8. Open owner decision: upgrade authority

**This is unresolved, and this document does not decide it.**

Every room and door mint has its mint, freeze and metadata-update authorities
revoked; the e2e test checks all three on-chain. But while the program has a
live upgrade authority, whoever holds that key can replace the program, and
with it every rule that guards the reserve, the backing and the fees. Scanners
and careful buyers check exactly this.

| option | what holders get | cost |
|---|---|---|
| keep a single upgrade key | nothing beyond trust in the key holder | the fastest response to bugs |
| multisig upgrade authority (e.g. Squads) | no single key can upgrade | slower fixes; the signer set is public |
| timelocked upgrades | time to exit before a change lands | needs a timelock program or multisig with delay; still upgradeable |
| immutable (`solana program set-upgrade-authority --final`) | the program can never change | no bug fix ever, and **graduation (phase 2) cannot be added to this program ID**: it would need a new program |

Phase 2 (graduation) does not exist in this version, so making v1 immutable
would freeze it at "curve only, graduation fails closed".
