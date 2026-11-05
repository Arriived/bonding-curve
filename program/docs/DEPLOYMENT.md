# Doors v1 deployment

4 November 2026; devnet upgraded to `54215ae` on 5 November 2026 (§5).

## 1. Status

| part | status |
|---|---|
| program ID, upgrade authority, matcher authority | generated; public keys in §2 |
| build of the deploy source | done; 48 SBF tests passing and 1 ignored (the reproduction of open finding M-7), including the 10,000-iteration property run; ELF pinned in `devnet/DEPLOY_ELF.sha256` (§3) |
| **devnet deployment** | **DONE**, 5 November 2026: deployed at slot 518,934,300 (`b6fe25d`), upgraded at slot 519,010,828 to `54215ae` (M-8, M-6). On-chain bytes equal the pinned ELF; Config read back after the upgrade with 0 of 22 fields differing (§5) |
| end-to-end test, localnet | **PASS**, 33 of 33 checks (§7) |
| **end-to-end test, devnet** | **PASS**, 33 of 33 checks (§7). The matcher service's own e2e also passes on devnet (`services/matcher`, `claude/matcher-service`). |
| upgrade-authority policy for mainnet | open owner decision (§8) |

## 2. Program ID and authorities

| role | public key | keypair file |
|---|---|---|
| **program ID** | `D7YsLsiJXoAF38vCUhFqYStepvSz6goG7EddHDe5NVJG` | `program.json` |
| **upgrade authority** (also the Config admin: `initialize_config` must be signed by it) | `HbvturaYqGpCVqrWV6StwJ3rJdBh2QQr26vyo2Q2nky` | `upgrade-authority.json` |
| **matcher authority** (devnet/localnet only), set in `Config.matcher_authority` | `AMUaQ4J1EJ4SWCwxc3fHYW4PNdyE432qNzitVdX9T3Bv` | `matcher-authority.json` |
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

**Matcher key rotated, 5 November 2026.** The first matcher key,
`5Bb2HVR9XeTeNBeM28W2ecdKcwycwPMJqGXmcWtuRrCN`, was generated in a cloud session. It
was never set in any deployed Config. Its secret was deleted, and the key above
replaced it. **The replacement was also generated in a cloud session, so it is a
devnet/localnet key too.** No session-generated key may become the mainnet
matcher: the mainnet key is created inside KMS by the owner (§9).

**Losing `program.json` loses this program ID.** Losing
`upgrade-authority.json` makes the program unupgradeable and Config unchangeable.

## 3. What is deployed

| | |
|---|---|
| source | commit `54215ae` (`verification/build.json` records it with every source hash) |
| history | Until 5 November the deploy source was `436c002` plus the program-ID patch (ELF `f2cfdb85…b436`; `verification/devnet/deployed_source.patch`, `deployed_elf_vm/`), because the tip `8ce373f` failed 10 of 38 SBF tests. The tip was then fixed (`6385fdd`), extended (`e9bd2aa`, `1558b2e`) and repinned ([CORRECTIONS](CORRECTIONS.md)). `b6fe25d` (ELF `c36ba443…ed29`, 522,776 bytes) was deployed to devnet at slot 518,934,300 and replaced by `54215ae` at slot 519,010,828. |
| ELF | 552,840 bytes, SHA-256 `b30c3462ffdd13ceadd8d1144ac07cfd1e95e280547e01a692dadca8d8c783b9`, pinned in `devnet/DEPLOY_ELF.sha256`. `deploy.sh` and `upgrade.sh` refuse any other binary. |
| IDL | byte-identical to `anchor idl build`, SHA-256 `d037777da14bb121775cec48db1482c65d15397f6985794afe7d7deafab3c42d` |
| tests on this exact source | `cargo test --locked --test svm`: 48 passed, 0 failed, 1 ignored (the reproduction of open finding M-7 in `SECURITY_REVIEW.md`); `cargo fmt --check` clean; `check_layouts.py` passes |

**`program/devnet` builds against the tip** (it fills `expected_terms_hash`,
`door_nonce` and `expires_at_slot`).

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

1. **The build reproduced once, for the earlier pin.** `436c002` built here
   gave exactly the ELF hash CI recorded on GitHub's runner for the same program
   code (`a5bccfad…71af`), in a different directory on a different machine. The
   current pin has not been built by CI yet. The heap probe's clean-worktree build
   of `e9bd2aa` gave the same ELF as this tree (`36e22dab…`).
2. **The deployed bytes are compared with the pinned ELF.** `deploy.sh` dumps
   the deployed program and fails unless its hash equals the pinned ELF.

## 5. Devnet deployment — done, then upgraded

**Funding.** The owner funded the deploy wallet
`2eKSWypmuDsBtH6hsZa4u6CgABkdS8vHtNozWPBhB1a2` with 5 SOL. Read at finalized slot
518,932,847. Earlier, every free route had failed: the RPC faucet is closed, the
web faucet refused the owner's accounts, and the proof-of-work faucets were empty.

**First attempt: failed, and recovered.**
- **What failed:** `deploy.sh` stopped while writing the program buffer with
  `Data writes to account failed: Custom error: Max retries exceeded`.
- **Why:** by default the CLI sends buffer writes to validator TPUs over QUIC,
  which this HTTPS-only environment cannot reach. Localnet worked because the
  validator was local.
- **What it left behind:** a funded buffer, `HA3N7h9bMKAuLMhwUMPdvcZruB1U3vg6u1iLDLqroYfh`
  (2.65658092 SOL, owned by the upgrade authority).
- **Recovery:** the buffer was closed back to the deploy wallet (4.99998 SOL at
  slot 518,934,105).
- **Change to `deploy.sh`:** it now passes `--use-rpc --max-sign-attempts 20`, and
  prints the buffer-recovery commands on any failure.

**Second attempt: deployed.**

```sh
devnet/deploy.sh https://api.devnet.solana.com <keys_dir> verification/devnet/devnet
```

| item | value |
|---|---|
| program ID | `D7YsLsiJXoAF38vCUhFqYStepvSz6goG7EddHDe5NVJG` |
| deploy signature | `4stW8KGcsvMQmpxahMkFuzQCDhB71gtRNmtktK4suupD1jpBhX9793b4ozNT9C1KXF9AA8njRBvyW82Espn1E866` |
| deploy slot | 518,934,300 |
| ProgramData | `4SbbsdYLxSgVP42JRpGj6DZVSBp9tVas8iTRQfiFjMNi`, 2,656,580,920 lamports |
| upgrade authority | `HbvturaYqGpCVqrWV6StwJ3rJdBh2QQr26vyo2Q2nky` (session-generated; the mainnet decision is §8) |
| on-chain bytes | equal to the pinned ELF `c36ba443…ed29` |
| Config | `4jJfFvgAyPsnX6P95Wd4huf5BCyYaow771kdZpqbbpWw`, read back at slot 518,934,315: 0 of 22 fields differ |
| `Config.matcher_authority` | `AMUaQ4J1EJ4SWCwxc3fHYW4PNdyE432qNzitVdX9T3Bv` (the rotated dev key, §9) |

Full evidence is in `verification/devnet/devnet/`, and the tables are in §7.

**Spent.**
- ProgramData: 2.6566 SOL.
- Config top-up: 0.05 SOL.
- e2e wallet top-ups:
  - program e2e: 0.6 SOL each, two wallets;
  - service e2e: a further 0.95 SOL to the launcher.
- **Remaining,** at finalized slot 518,937,413 (`--lamports` reads):

  | wallet | balance |
  |---|---|
  | deploy wallet | 136,805,960 lamports |
  | launcher | 249,675,695 lamports |
  | trader | 186,579,080 lamports |

  The smoke wallets also hold the room and door tokens bought during the tests.

### Upgrade to `54215ae` (M-8, M-6)

```sh
devnet/upgrade.sh https://api.devnet.solana.com <keys_dir> verification/devnet/devnet
```

`upgrade.sh` checks the pin, records `program_show_before.json`, deploys with
`--use-rpc --max-sign-attempts 20` (the CLI extends ProgramData when the ELF has
grown), compares the on-chain bytes with the pin and reads Config back.

| item | value |
|---|---|
| before | `lastDeploySlot` 518,934,300, `dataLen` 522,776, 2,656,580,920 lamports (`program_show_before.json`) |
| upgrade signature | `qLdPHc7BqBBG2PtS21M2jAp6xoVKUSYkBkzwAP9e5bgx9jwqxa6o5YTrcTd1iD8CepGmsbnQUuysEkdC3Y9JHvw` (`upgrade.json`) |
| upgrade slot | 519,010,828 |
| after | `dataLen` 552,840, 2,809,306,040 lamports (`program_show.json`) |
| on-chain bytes | equal to the pinned ELF `b30c3462…83b9` |
| Config | read back at slot 519,010,873: 0 of 22 fields differ. The layout is unchanged; M-6's pending change lives in a new PDA. |

**Cost of the upgrade,** from the deploy wallet: 5,136,805,960 lamports at slot
519,010,713, 4,978,020,840 after the upgrade transaction (its post-balance). That is
158,785,120 lamports:
- 152,725,120 of permanent ProgramData rent for the 30,064 extra bytes;
- 6,060,000 of transaction fees (buffer writes, extend, upgrade). The buffer's rent
  came back to the deploy wallet in the upgrade transaction.

After the upgrade, the program e2e topped up its two wallets (0.6 SOL each) and the
service e2e the launcher (0.6 SOL).

**Remaining,** at finalized slot 519,014,251 (`solana balance --lamports`):

| wallet | balance |
|---|---|
| deploy wallet | 3,178,005,840 lamports |
| upgrade authority (Config admin) | 48,084,920 lamports |
| launcher | 1,314,303,550 lamports |
| trader | 503,271,200 lamports |
| matcher | 0 |

**Upgrade budget.** An upgrade holds a buffer as large as ProgramData while it runs:
2,809,306,040 lamports for today's ELF (`solana rent 552885`; devnet rent is
5,080 lamports per byte). That leaves 368,699,800 lamports on the deploy wallet.
Each extra ELF byte costs 5,080 more buffer (returned) and 5,080 of permanent
extension, so the next upgrade fits from the deploy wallet alone if the ELF grows by
less than about 35 KB, after fees like this upgrade's. The launcher and trader
balances can be swept back if more is needed.

## 6. Mainnet: what differs

1. **Keys.**
   - Generate the program and upgrade-authority keys on hardware the owner
     controls, not in a cloud session.
   - Store the upgrade authority offline, or as a multisig (§8).
   - The matcher key is created inside KMS (GCP `EC_SIGN_ED25519`, HSM protection
     level, or AWS `ECC_NIST_EDWARDS25519`), non-exportable, by the owner. It is
     never a file and never comes from a session. It must not be the upgrade
     authority or the admin. Installing it is a rotation (§9).
2. **Config admin.** `initialize_config` makes the current upgrade authority
   the Config admin. To separate them, hand admin to a distinct key with
   `update_config(settings, new_admin)`.
3. **Protocol fee recipient.** Devnet uses the deploy wallet. Mainnet needs the
   real treasury address.
4. **Cost.** ProgramData is 2.668 SOL at the current 5,080 lamports-per-byte
   rent, plus buffer-write fees, with a priority fee under load.
5. **Order.** Deploy only an ELF that has passed the devnet end-to-end test,
   from a fresh session.
6. **Deploy only the pinned ELF.** `deploy.sh` refuses any other; `e2e.sh` refuses a VM baseline from another ELF.

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
contains `devnet`.

| `devnet/e2e-target` | what `e2e.sh` does | status |
|---|---|---|
| `localnet` | Starts a fresh `solana-test-validator` and funds the wallets locally. Deploys the pinned ELF and initialises Config through `deploy.sh`, then runs the test. Outputs go to `verification/devnet/localnet/`. | **PASS**, 33/33 |
| `devnet` | Requires the §5 deployment. Tops up the two e2e wallets from the deploy wallet, then runs the same test against devnet. Outputs go to `verification/devnet/devnet/`. | **PASS**, 33/33 |

**Switching between them:** `echo localnet > devnet/e2e-target`, or `echo devnet`.

**Limits of the localnet result:**

- It uses the test validator's bundled Token-2022 and ATA binaries.
- It uses the test validator's default feature set.
- It uses the old 6,960 lamports-per-byte rent (ProgramData there costs
  3.85 SOL for this ELF).
- Its slots are local.

The devnet run below has none of these limits.

### Devnet run

After the upgrade to `54215ae`; evidence in `verification/devnet/devnet/`.

| item | value |
|---|---|
| program ID | `D7YsLsiJXoAF38vCUhFqYStepvSz6goG7EddHDe5NVJG` |
| deploy signature | `4stW8KGcsvMQmpxahMkFuzQCDhB71gtRNmtktK4suupD1jpBhX9793b4ozNT9C1KXF9AA8njRBvyW82Espn1E866` |
| upgrade signature (`devnet/upgrade.sh`) | `qLdPHc7BqBBG2PtS21M2jAp6xoVKUSYkBkzwAP9e5bgx9jwqxa6o5YTrcTd1iD8CepGmsbnQUuysEkdC3Y9JHvw` |
| last upgrade slot (`lastDeploySlot`) | 519,010,828 |
| ProgramData account | `4SbbsdYLxSgVP42JRpGj6DZVSBp9tVas8iTRQfiFjMNi` |
| upgrade authority | `HbvturaYqGpCVqrWV6StwJ3rJdBh2QQr26vyo2Q2nky` |
| ProgramData lamports | 2,809,306,040 |
| local ELF SHA-256 | `b30c3462ffdd13ceadd8d1144ac07cfd1e95e280547e01a692dadca8d8c783b9` |
| on-chain bytes SHA-256 (first ELF-length bytes of `solana program dump`) | `b30c3462ffdd13ceadd8d1144ac07cfd1e95e280547e01a692dadca8d8c783b9` |
| on-chain bytes equal local ELF | yes |
| Config account | `4jJfFvgAyPsnX6P95Wd4huf5BCyYaow771kdZpqbbpWw` (read at slot 519,010,873, 248 bytes) |
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
| `matcher_authority` | `AMUaQ4J1EJ4SWCwxc3fHYW4PNdyE432qNzitVdX9T3Bv` | `AMUaQ4J1EJ4SWCwxc3fHYW4PNdyE432qNzitVdX9T3Bv` | yes |
| `live_min_reserve_lamports` | `500000000` | `500000000` | yes |
| `live_max_idle_seconds` | `21600` | `21600` | yes |
| `live_new_seconds` | `3600` | `3600` | yes |
| `live_min_volume_lamports` | `5000000000` | `5000000000` | yes |
| `pool_min_window_lp_fee` | `80000000` | `80000000` | yes |
| `bump` | `254` | `254` | yes |

**Transactions, live CU against the VM observations of the same ELF** (VM figures are observed values from LiteSVM's Agave 4.3.2 at fixed addresses, not upper bounds; a positive last column is expected, not a failure):

| step | signature | slot | live program CU | VM observed min–max CU (same ELF) | live − VM observed max |
|---|---|---|---|---|---|
| initialize_config | `5N2gocHUhskmF4TFZooVQfvDfFY5p3iAKQmuXriqJNieT5wNU8vmuWoKn7qacQ2JzfcFxAUE5foj57NkywU4ndVD` | 518,934,313 | 13,347 | 13,349–13,349 (n=1) | -2 |
| create_room | `27NLFYwq8qJqsefs87e2zb5TYbQy8Sd5qKLVQtYAEu8eBYG3bfgQ3kf2whTtK5e6DLSTyy9MvxErEpczFrGHCVD3` | 519,011,563 | 256,432 | 230,822–230,822 (n=1) | +25,610 |
| create_atas_launcher | `4BhdyJhSeyTM8n2fWskZB3AKnCtWetAKuQLszXzSMX2x2UWD2FaF6yCiqdtre2mUsAn1fcMwo1Wq7NhxA8gaGT2Y` | 519,011,570 | None | not measured | — |
| open_door | `2cuiQY54XXJS4bvY6rhPnyqiUqMdsPiTAevp65H8y2FLpoWEs94qdwNe4bdajR7WqAmFK2uFZdMk1LPjpk1cBbvx` | 519,011,578 | 144,679 | 138,533–149,974 (n=3) | -5,295 |
| create_atas_trader | `4H1tcr9wPGJzsH6nFz7DcLwqjHKjTf4adESzvKAqGNyXVD9fCLfNd5iBFp4mY8eCbdhmfQpFXpvGMgwUzdYfcUj6` | 519,011,584 | None | not measured | — |
| buy_door0 | `5bTTxMYkxk3ZLtCAeWs89xnGQtCiTbXX2HwWztMbZQdzQVu44cB5M66EvgXz93UnpUDUtTx3neVsTeDYQ5uZDkct` | 519,011,592 | 67,004 | 57,124–69,345 (n=3,348) | -2,341 |
| buy_door1 | `63dDBf1TsrKamfwGRrNBy7yUtenHPzG2F1oLzVxCaQ3q8kBUNSGXvmXqM3CEUfnscL9LNJLstnXwnEnAYkQi9doS` | 519,011,598 | 58,237 | 57,124–69,345 (n=3,348) | -11,108 |
| sell_door0 | `94EQadnW5HX3NnNZurhmixYmsyz7iRr5u1Lzn2S6GWnxYj9tHuhizZasxi1ysHyQWnxTugjCDT7EGbpswTdZ11G` | 519,011,605 | 64,087 | 54,215–57,229 (n=1,673) | +6,858 |
| convert_door0_to_door1 | `3iYm5DmpCUMPACHW4RvzYnnMX1CN3VGHE9QGMSsou7Tufsxhw9ekyMuDeZe1Xp2U9bEmwoH1NKQ3ki6cpHtGQCt9` | 519,011,612 | 74,647 | 65,855–68,866 (n=800) | +5,781 |
| buy_room_token | `mc6tQJmn2TWksF4ekJ6AzEVxUA85XgA7isxo12XpwqAREWF2ub6jpFWa5fouqtG5QKTMq8GFkZfRH4tFNnqRY7t` | 519,011,619 | 42,052 | 44,601–53,602 (n=840) | -11,550 |
| retire_pending | `4HwYaTARkGJLryBiwvPHED2azPhU1WVde9nT1U7HhgmbMw3TBswzGK1hmasRWDkoBy89ktdwa2z23GgxgRYQjb72` | 519,011,628 | 30,237 | 20,829–29,807 (n=829) | +430 |
| claim_door_fees | `3KSaKVHnUVegTZaBHseKUXjWgGTLcwf65bz4zFtZuYAPszgNhUAREakYjT5nugmAJMhWnJuQpLKfF3y7BCSf8nJ9` | 519,011,636 | 53,853 | 36,594–40,353 (n=808) | +13,500 |

ATA rows are client setup (Associated Token program), not doors program CU.

**Expected failures:**

| case | landed on-chain | signature | slot | error |
|---|---|---|---|---|
| create_room_without_matcher_signature | yes | `2LiX37hKguUZnjjPvtiFuocREsEFY8pafzUM3pkDn47j243kuKLoLEm6ewccomaoziQSXh4RkHkarJGtFFFpQKfS` | 519,011,653 | {"InstructionError":[1,{"Custom":3010}]}; `Program log: AnchorError caused by account: matcher. Error Code: AccountNotSigner. Error Number: 3010. Error Message: The given account did not sign.` |
| open_door_without_matcher_signature | yes | `419x3kW1iBfBSLcLmpYVhk9FvamXuR6KeLmqxDQj9XYD7tvfeD1mngf6CSGQVydaESTj3LhwCpRYfD3Yt5JcTyk8` | 519,011,660 | {"InstructionError":[1,{"Custom":3010}]}; `Program log: AnchorError caused by account: matcher. Error Code: AccountNotSigner. Error Number: 3010. Error Message: The given account did not sign.` |
| create_room_signature_over_different_routing_data | no: rejected before execution | — | — | `SignatureFailure`: Transaction simulation failed: Transaction did not pass signature verification |
| open_door_signature_over_different_routing_data | no: rejected before execution | — | — | `SignatureFailure`: Transaction simulation failed: Transaction did not pass signature verification |
| sell_exceeding_balance | yes | `2ZihaCckjri3bhroiKZxcUiHRoSD7xFqScjY1LfR6kdCWsjgTH3fbfQDSmHVxMHrw39FBCcRc8RSGCgWXhdUdo8c` | 519,011,671 | {"InstructionError":[1,{"Custom":1}]}; `Program TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb failed: custom program error: 0x1` |
| claim_door_fees_by_non_recipient | yes | `DzQksm6m2igQRJR2RJycLaDS4X66WVqWtmoMz6HJHRLQ3NDT7F3Rzbw1SCHA8hn59tibpMyqFyTouKCz1aPbPhN` | 519,011,677 | {"InstructionError":[1,{"Custom":6006}]}; `Program log: AnchorError thrown in programs/doors_v1/src/lib.rs:820. Error Code: Authority. Error Number: 6006. Error Message: Unauthorized.` |

**On-chain state checks after the sequence:**

| check | result |
|---|---|
| room mint `59zPq4ktyq51mbhfsNtPn76x2U4sJmFwkpZK8WEQbbdH`: supply, mint/freeze/metadata authorities | 1000000000000000, None, None, None → ok |
| door 0 mint `HsqVoNXfnMxMYKQHELzcnaq112Vas7WE7U1JbbhGT3XA`: supply, authorities | 1000000000000000, None, None, None → ok |
| door 0 backing vault vs circulating door supply | 882397366623 vs 882397366623 → equal |
| door 1 mint `Vs7bpFzPH39QPLPSNxyMjoQNmhdU8G8bSyqJLf1KQ1C`: supply, authorities | 1000000000000000, None, None, None → ok |
| door 1 backing vault vs circulating door supply | 4388842602598 vs 4388842602598 → equal |
| reserve vs curve integral of `sold` | 197908792 vs 197908792 → covers |
| ReserveVault lamports − rent vs `reserve` | 197908792 vs 197908792 → covers |
| RoomVault vs unsold supply | 992967883781714 vs U − 7032116218286 → covers |
| fee counters vs 60/40 split of every Trade event's fee | expected {'door0': 893538, 'door1': 594060, 'fee_total': 2974380, 'founder': 0, 'pending_reserve': 297030, 'protocol': 1189752}; on-chain {'door0': 893538, 'door1': 594060, 'fee_total': 2974380, 'founder': 0, 'pending_reserve': 297030, 'protocol': 1189752} → match |
| retire_pending | pending 0, reserve +297030 |
| claim_door_fees (door 0) | accrued 0, claimed 893538 |

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

**Live devnet CU against the VM.** The VM column is what LiteSVM (Agave 4.3.2)
observed for this ELF at fixed fixture addresses. These are observations, not
upper bounds. Live devnet figures exceeded them for:

- `create_room`: +25,610 CU above the VM observed maximum;
- `sell_door0`: +6,858 CU above the VM observed maximum;
- `convert_door0_to_door1`: +5,781 CU above the VM observed maximum;
- `retire_pending`: +430 CU above the VM observed maximum;
- `claim_door_fees`: +13,500 CU above the VM observed maximum;

That is real-cluster confirmation that no VM figure is a ceiling. The smoke launch
now uses a fresh name and symbol on every run (its SlugLock persists on devnet), so
its metadata and its PDA addresses differ from the VM fixture's.

**Against the service's 400,000 CU limit.** The worst tested launch is 303,780 VM
CU at `54215ae` (a prefunded takeover `create_room`; `cargo test --locked --test svm
prefunded_maximum_metadata -- --nocapture`). Adding the largest drift seen here,
25,610, leaves about 70,600 CU of margin.

### Localnet run

Fresh `solana-test-validator`, same ELF; evidence in `verification/devnet/localnet/`.

| item | value |
|---|---|
| program ID | `D7YsLsiJXoAF38vCUhFqYStepvSz6goG7EddHDe5NVJG` |
| deploy signature | `2BxBbSRyRairQ4gXPEA5XuQUot7WUjegnPynMt7KzsdJymUajkCDZKDj6SRsxHF3CEDoztHeP6KxbybnaBjQLSbm` |
| deploy slot (`lastDeploySlot`) | 15 |
| ProgramData account | `4SbbsdYLxSgVP42JRpGj6DZVSBp9tVas8iTRQfiFjMNi` |
| upgrade authority | `HbvturaYqGpCVqrWV6StwJ3rJdBh2QQr26vyo2Q2nky` |
| ProgramData lamports | 3,848,970,480 |
| local ELF SHA-256 | `b30c3462ffdd13ceadd8d1144ac07cfd1e95e280547e01a692dadca8d8c783b9` |
| on-chain bytes SHA-256 (first ELF-length bytes of `solana program dump`) | `b30c3462ffdd13ceadd8d1144ac07cfd1e95e280547e01a692dadca8d8c783b9` |
| on-chain bytes equal local ELF | yes |
| Config account | `4jJfFvgAyPsnX6P95Wd4huf5BCyYaow771kdZpqbbpWw` (read at slot 22, 248 bytes) |
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
| `matcher_authority` | `AMUaQ4J1EJ4SWCwxc3fHYW4PNdyE432qNzitVdX9T3Bv` | `AMUaQ4J1EJ4SWCwxc3fHYW4PNdyE432qNzitVdX9T3Bv` | yes |
| `live_min_reserve_lamports` | `500000000` | `500000000` | yes |
| `live_max_idle_seconds` | `21600` | `21600` | yes |
| `live_new_seconds` | `3600` | `3600` | yes |
| `live_min_volume_lamports` | `5000000000` | `5000000000` | yes |
| `pool_min_window_lp_fee` | `80000000` | `80000000` | yes |
| `bump` | `254` | `254` | yes |

**Transactions, live CU against the VM observations of the same ELF** (VM figures are observed values from LiteSVM's Agave 4.3.2 at fixed addresses, not upper bounds; a positive last column is expected, not a failure):

| step | signature | slot | live program CU | VM observed min–max CU (same ELF) | live − VM observed max |
|---|---|---|---|---|---|
| initialize_config | `3vBBhu26ntpyNJPxZnLmi2XNyhom6peGBu6hu46TAbsAG6ff8unwrUut9LS82CFCnLwUWtd8jK9FRKRcAN5jqNS7` | 21 | 13,349 | 13,349–13,349 (n=1) | +0 |
| create_room | `fdCzXiUq4H1gu72LS9FJ9GijoNjPSGHXDLfyrbA6eqY4bVfxv2jmbc7oKrPB6qJdxHyTJEWdrF2CpgLaNcuBGx6` | 23 | 237,643 | 230,822–230,822 (n=1) | +6,821 |
| create_atas_launcher | `2X7cBLKh7f3byyLgKMCTz7Lo9QezUQ9MkLNJUQT56Z4AVn5nMZrJtBRH9Yw4VG6yEvFR4mDN4jko8hASijAj62So` | 26 | None | not measured | — |
| open_door | `4TZYPQJXS9HeNAkXX3YRmkQQJ1gXsAVquGJL7srPcwRaSjxugnJNvtE26QyGsdBA3cLeyeo9SeVuqPj6dqjpE7E6` | 28 | 136,668 | 138,533–149,974 (n=3) | -13,306 |
| create_atas_trader | `2dyyZpSHzunYxm6m3VkVf2txJdW7cN8woH1CqVKx1MkaYttAdRXC1CQkEpf8wj1z6u5gQDwkex45ZxsB2ePQV1az` | 31 | None | not measured | — |
| buy_door0 | `58pHGf8FBTW3Wbrw2gobajTS8gnn7q6EzhL4gawkwwV8v1nDejvdLRjH7rriPuKqvDhQathkFPcYyJeVvcGsuwoh` | 33 | 56,999 | 57,124–69,345 (n=3,348) | -12,346 |
| buy_door1 | `2mFV9aVtKgLtJLjaUghyfzUj5cqQUHAG8mugVHTQwhHTURgxfjcptDEeaW34NqZ85eP8frXrW4fwBzuGqxkUkD6j` | 36 | 63,232 | 57,124–69,345 (n=3,348) | -6,113 |
| sell_door0 | `54c4WNpnxEEHo5npswxJ79TGoJYF2pv59w5VxTJZZt9VSQ8s6HAHz4vfDUpKazoM4faq5a9STsDgyFFhU6zNaCjS` | 38 | 54,081 | 54,215–57,229 (n=1,673) | -3,148 |
| convert_door0_to_door1 | `65vcUvUFU2vSZgxDGRJGdzUdgiTTN6zr9G3u1MiuQhN2PB3fABXhtKZazoPLF98orWwwmza5hfkVyxY88mbj3RE3` | 40 | 67,139 | 65,855–68,866 (n=800) | -1,727 |
| buy_room_token | `4BH97BvmbgU7QnBAStYE1khCmr8p1WByxTGPewoMBGEAnopGjKuZLtHcsrYLVc8CwBiRGnq7DYRTViBtS7oQ8Tzf` | 43 | 43,050 | 44,601–53,602 (n=840) | -10,552 |
| retire_pending | `5Nfy1JMUbY1HDvUYLoyqwDBqEyfuWqTzDZ4ynsB6uKnMHTy8mGz3JrHSgzedY3ty2Zjbq1ECCzxJxssosN9PF7ZW` | 45 | 29,734 | 20,829–29,807 (n=829) | -73 |
| claim_door_fees | `5QE92DPC2DrhTqoL3sujC5YYHohVN7pgNxNJdgbd3f71bgf1Mp2r9HEBF2NpvjbMc5eYNLWQksvnmtBoYnGe1DJD` | 48 | 44,853 | 36,594–40,353 (n=808) | +4,500 |

ATA rows are client setup (Associated Token program), not doors program CU.

**Expected failures:**

| case | landed on-chain | signature | slot | error |
|---|---|---|---|---|
| create_room_without_matcher_signature | yes | `5g4TfNmQekmSi6nGM4a6JN4xSiLrjvayK3dL3Ehf6BaBsAQ8pShEgEo8QAh85EVqvH5XGGDAMWLK8iyyhFX1MLm1` | 51 | {"InstructionError":[1,{"Custom":3010}]}; `Program log: AnchorError caused by account: matcher. Error Code: AccountNotSigner. Error Number: 3010. Error Message: The given account did not sign.` |
| open_door_without_matcher_signature | yes | `4HMLCF3G2R49UappKvzwjbPubh8iY8UewsZGXScCo55HEAjxvoHB5e63VLs6qrtHP9Q3XZ2Aq9BtS8cBVmjYDyTv` | 53 | {"InstructionError":[1,{"Custom":3010}]}; `Program log: AnchorError caused by account: matcher. Error Code: AccountNotSigner. Error Number: 3010. Error Message: The given account did not sign.` |
| create_room_signature_over_different_routing_data | no: rejected before execution | — | — | `SignatureFailure`: Transaction simulation failed: Transaction did not pass signature verification |
| open_door_signature_over_different_routing_data | no: rejected before execution | — | — | `SignatureFailure`: Transaction simulation failed: Transaction did not pass signature verification |
| sell_exceeding_balance | yes | `a6WGSh4j6j4AM4eazmfSP9oPwbaVS3TGxR2XYJJ4TW3Bs4bwdC88ewhgazLccmdkHjAhuT3A7zGDeX8eowKhj9w` | 56 | {"InstructionError":[1,{"Custom":1}]}; `Program TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb failed: custom program error: 0x1` |
| claim_door_fees_by_non_recipient | yes | `4aQvDauAixuqNcyX5W6z1ijcnefn85mkfDZj2h9gj5hKwbPP11gWQGBP6WEDWAwAguK4Hu2B92cA7cqtK1iVQbhs` | 58 | {"InstructionError":[1,{"Custom":6006}]}; `Program log: AnchorError thrown in programs/doors_v1/src/lib.rs:820. Error Code: Authority. Error Number: 6006. Error Message: Unauthorized.` |

**On-chain state checks after the sequence:**

| check | result |
|---|---|
| room mint `8KjZenZMVDSibYyrKsG2Jsw6At3fB5pmmaN4hNaDgAMF`: supply, mint/freeze/metadata authorities | 1000000000000000, None, None, None → ok |
| door 0 mint `6rMy9MU2m1MZdCQpRFCLTkfG21jnpBM5g5YcuvsccurR`: supply, authorities | 1000000000000000, None, None, None → ok |
| door 0 backing vault vs circulating door supply | 882397366623 vs 882397366623 → equal |
| door 1 mint `8nSk4tPGkLXBGmqHf7VJYBDMsWv33EN5bgeM7BUSsWj6`: supply, authorities | 1000000000000000, None, None, None → ok |
| door 1 backing vault vs circulating door supply | 4388842602598 vs 4388842602598 → equal |
| reserve vs curve integral of `sold` | 197908792 vs 197908792 → covers |
| ReserveVault lamports − rent vs `reserve` | 197908792 vs 197908792 → covers |
| RoomVault vs unsold supply | 992967883781714 vs U − 7032116218286 → covers |
| fee counters vs 60/40 split of every Trade event's fee | expected {'door0': 893538, 'door1': 594060, 'fee_total': 2974380, 'founder': 0, 'pending_reserve': 297030, 'protocol': 1189752}; on-chain {'door0': 893538, 'door1': 594060, 'fee_total': 2974380, 'founder': 0, 'pending_reserve': 297030, 'protocol': 1189752} → match |
| retire_pending | pending 0, reserve +297030 |
| claim_door_fees (door 0) | accrued 0, claimed 893538 |

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

**Live CU against the VM.** The VM column is what LiteSVM (Agave 4.3.2) observed for
the pinned ELF itself, at fixed fixture addresses (`verification/svm_report.json`;
`e2e.sh` refuses a baseline from any other ELF). **These are observations, not upper
bounds.** Live figures exceeded the VM observed maximum for:

- `create_room`: +6,821 CU above the VM observed maximum;
- `claim_door_fees`: +4,500 CU above the VM observed maximum;

Two candidate causes, not separated here:
- **PDA bump searches.** Their cost varies by address, and every run creates a room at
  a fresh random nonce.
- **Runtime version.** The local validator is Agave 4.4.0; LiteSVM bundles 4.3.2.

**Consequence.** No VM figure in `verification/cu.md`, the spec or this document is a
ceiling. Budget compute with margin above them, and treat the live devnet run as the
better sample of the real runtime.

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

## 9. Matcher key rotation

**Use this for every change of matcher key:** the first mainnet key, a scheduled
rotation, or a suspected compromise.

**What changes on-chain.** There is no dedicated instruction. The admin calls
`update_config(settings, new_admin)` with the **whole** `Settings`. Only
`matcher_authority` may differ from the current Config; everything else must be
copied from a fresh read.
- `create_room` and `open_door` compare the matcher signer against
  `Config.matcher_authority` **at execution**. From the slot the update lands,
  every launch signed by the old key fails (`Matcher`), including signed launches
  not yet landed and durable-nonce transactions.
- Rooms and doors already created stay. Rotation does not undo them (see
  `SECURITY_REVIEW.md`, threat actors).

**Procedure.**
1. **Create the new key** in KMS, non-exportable (§6). Record its key-version
   resource name and base58 public key. Grant the service's identity sign-only
   permission on that version and nothing else.
2. **Start the new service instance** with the new key
   (`MATCHER_SIGNER=gcp-kms` or `aws-kms`). It reports `/health` 503
   `signer_mismatch` and signs nothing, because its key is not yet in Config.
3. **Read Config** at a recorded slot, and build `Settings` from it with only
   `matcher_authority` replaced. Diff old and new `Settings` field by field.
   Exactly one field may differ. A whole-`Settings` update written by hand can
   silently change fees, thresholds or the recipient.
4. **Send `update_config`** from the admin key (offline or multisig on mainnet).
   Record the signature and slot.
5. **Verify.**
   - Read Config again and record the slot; `matcher_authority` must equal the
     new key.
   - The new instance turns ready.
   - The old instances turn unready (`signer_mismatch`) on their next snapshot
     (2 s refresh).
   - A smoke launch through the new instance lands.
6. **Retire the old key.**
   - KMS: disable the old key version, then schedule its destruction.
   - Session key: delete the file.
   - Revoke the old service identity's sign permission.
7. **Record** both public keys, the Config slots and the signature in this
   section.

**During the switch,** launches fail for at most one snapshot refresh and one
blockhash window (about 60–90 s). Clients re-request, and get a decision from the
new key.

**Compromise response.** Do steps 1–5 at once, and pause (`paused = true` in the
same update) only if the attacker is actively creating rooms. Pausing also stops
every trade, sell included (`SECURITY_REVIEW.md`).

| date | old key | new key | Config slot | note |
|---|---|---|---|---|
| 5 Nov 2026 | `5Bb2HVR9XeTeNBeM28W2ecdKcwycwPMJqGXmcWtuRrCN` | `AMUaQ4J1EJ4SWCwxc3fHYW4PNdyE432qNzitVdX9T3Bv` | none: no deployed Config; the localnet e2e initialises with the new key | both session-generated, devnet/localnet only |
