# Doors v1 deployment

4 November 2026.

**Status: devnet deployment is not done yet.** The devnet deploy wallet has no
SOL, because the devnet RPC faucet is closed (see
[CORRECTIONS](CORRECTIONS.md), devnet preflight item 5). Everything else is in
place:

- the build;
- the keys;
- a full rehearsal on a local Agave 4.4.0 validator: deploy, initialise, smoke
  sequence and failure cases.

Running the same script against devnet once the wallet holds about 3.5 SOL
completes the deployment:

```sh
devnet/run_deploy.sh https://api.devnet.solana.com <keys_dir> verification/devnet/devnet
```

## Program ID and authorities

| role | public key | keypair file |
|---|---|---|
| **program ID** | `D7YsLsiJXoAF38vCUhFqYStepvSz6goG7EddHDe5NVJG` | `program.json` |
| **upgrade authority** (also the Config admin: `initialize_config` must be signed by it) | `HbvturaYqGpCVqrWV6StwJ3rJdBh2QQr26vyo2Q2nky` | `upgrade-authority.json` |
| **matcher authority**, set in `Config.matcher_authority` | `5Bb2HVR9XeTeNBeM28W2ecdKcwycwPMJqGXmcWtuRrCN` | `matcher-authority.json` |
| deploy wallet (fee payer; devnet protocol fee recipient) | `2eKSWypmuDsBtH6hsZa4u6CgABkdS8vHtNozWPBhB1a2` | `deploy-wallet.json` |
| smoke-test launcher (door 0 creator) | `3jyDH3Z5qLac28FKveDJF3Kp9Znkhu38QSv83SvBnX9k` | `smoke-launcher.json` |
| smoke-test trader (door 1 creator) | `vWDZPiFpy3rikaPdyuL7o9CkbCrvpkbiVuuUMrG3KEh` | `smoke-trader.json` |

**Where the keypairs are.**

- All six files are in one directory in the cloud session that generated them,
  outside every git work tree, with mode 600.
- They were generated with `solana-keygen new --silent`, so no seed phrase was
  printed.
- That directory is **not in this repository and will not survive the
  session**. The owner holds the only copies once they are copied off.
- `program/.gitignore` ignores `*-keypair.json`, `*.keypair.json` and `keys/`
  in addition to `target/`. The `anchor keys sync` copy at
  `target/deploy/doors_v1-keypair.json` is covered by `/target/`.
- No private key appears in any committed file. Every output was scanned for
  each key in base58, hex and JSON-array form.

**Losing `program.json` loses this program ID.** Losing
`upgrade-authority.json` makes the program unupgradeable and Config unchangeable.

## What is deployed

| | |
|---|---|
| source | commit `436c002` plus the program-ID change only (`verification/devnet/deployed_source.patch`: `declare_id!`, `Anchor.toml`, IDL address) |
| why not the brief's `054be58` | it lacks 13 commits of audit fixes; `436c002` is the newest commit whose full SBF suite passes (34/34) |
| why not the tip `8ce373f` | 10 of 38 SBF tests fail with `UnbalancedInstruction` (CORRECTIONS, devnet preflight item 1) |
| ELF | `target/deploy/doors_v1.so`, 525,032 bytes, SHA-256 `f2cfdb853ba77f6783221a98963c54fcaa730575cf79567814d164045669b436` |
| IDL | byte-identical to `anchor idl build`, SHA-256 `f70a0c64873c68e109d41ae64404b7ccd47d61e80de591d541195902925ab8f1` |
| tests on this exact source | `cargo test --locked --test svm`: 34 passed, 0 failed; `cargo fmt --check` clean; `check_layouts.py` passes |

## Toolchain

Exact versions, all matching the README's declared build target:

| tool | version | source |
|---|---|---|
| host Rust | `rustc 1.99.0 (b940084d7 2026-09-28)`, `cargo 1.99.0 (5f94df478 2026-08-27)` | rustup |
| cargo-build-sbf | 4.5.0, run with `--tools-version v1.58` | `cargo install cargo-build-sbf --version 4.5.0 --locked` |
| SBF compiler (platform-tools v1.58) | `rustc 1.95.0-dev (1e20dd0d5 2026-10-05)` | GitHub release download |
| Anchor CLI | 1.2.2 | `otter-sec/anchor` release binary, SHA-256 `e2c35a97…e741` |
| Solana / Agave CLI | `solana-cli 4.4.0 (src:9ef63128; feat:dddabd53, client:Agave)` | `anza-xyz/agave` v4.4.0 GitHub release tarball, SHA-256 `3363f472…c574` (release.anza.xyz is unreachable from this environment; the release's `.yml` names commit `9ef63128134af559561f6a91a641ec01e665c70d`) |
| SVM test runtime | LiteSVM 0.18.1 with Agave 4.3.2 | Cargo.lock |

Neither release publishes a checksum file, so the hashes above are of what was
downloaded, not checked against a published value.

**Verifiable build: not available for this toolchain** (CORRECTIONS item 4).
No `solana-verifiable-build` image exists for Agave 4.4.0, and no Anchor 1.2.2
image exists. What stands in for it:

1. **The pinned build is reproducible.** `436c002` built here gives exactly
   the ELF hash CI recorded on GitHub's runner for the same program code
   (`a5bccfad…71af`), in a different directory on a different machine.
2. **The deployed bytes are compared with the local ELF.** After deploying,
   `run_deploy.sh` dumps the program and hashes it.

So anyone with the pinned toolchain can rebuild the patched source and compare
hashes. It is not a `solana-verify` attestation.

## Localnet rehearsal

`solana-test-validator` 4.4.0 ran the exact deploy ELF, deployed by the same
script with the same program, upgrade and matcher keys. Every number in the
tables below is generated by `devnet/report.py` from
`verification/devnet/localnet/`. These are real validator transactions, but on
a local cluster.

Limits of the rehearsal:

- Its Token-2022 and ATA binaries are the ones the test validator bundles.
- Its feature set is the test-validator default.
- It uses the old 6,960 lamports-per-byte rent.
- Its slots are local.

Devnet replaces all four.

| item | value |
|---|---|
| program ID | `D7YsLsiJXoAF38vCUhFqYStepvSz6goG7EddHDe5NVJG` |
| deploy signature | `2AqEBDxBJ2V32cF3kCjHvHj4WFsGVcTSK2wUmzbUoYEVQA5SZQdxLv8vb3dCRcjJ5bLMfb63xvWoAXt6gzWBvGmm` |
| deploy slot (`lastDeploySlot`) | 33 |
| ProgramData account | `4SbbsdYLxSgVP42JRpGj6DZVSBp9tVas8iTRQfiFjMNi` |
| upgrade authority | `HbvturaYqGpCVqrWV6StwJ3rJdBh2QQr26vyo2Q2nky` |
| ProgramData lamports | 3,630,482,160 |
| local ELF SHA-256 | `f2cfdb853ba77f6783221a98963c54fcaa730575cf79567814d164045669b436` |
| on-chain bytes SHA-256 (first ELF-length bytes of `solana program dump`) | `f2cfdb853ba77f6783221a98963c54fcaa730575cf79567814d164045669b436` |
| on-chain bytes equal local ELF | yes |
| Config account | `4jJfFvgAyPsnX6P95Wd4huf5BCyYaow771kdZpqbbpWw` (read at slot 38, 248 bytes) |
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
| initialize_config | `5UAoS6gcB6Ewvds94Y9pwh9Zv6HiJkHEZqXGLxXGgbYj6NttUVogfP829wdCL4h5Us43UUgVBWg1ouFgZ6JQZsCp` | 37 | 13,347 | 13,347–13,347 (n=1) | +0 |
| create_room | `4btafdkYb9rKGA2m37EgRczwE1Q4fYRynwsrXG1PVeWKwqAYT8nwAeaGNZ7RG4jEBPurTEf7Pg4qVTyWHSNTSC3f` | 39 | 222,607 | 219,879–219,879 (n=1) | +2,728 |
| create_atas_launcher | `4vqgyeykARYdTbvUkZ2Wmu8TZK1Z2BTcAkUENxT6b5fpxbJ1tsda2to8e2Uh72J4DSExYaNC69t8NvmajkyUeYVW` | 42 | None | not measured | — |
| open_door | `2d6pXcjXr9RgdBdmZq4ZHzndaqiujiuyxaEx9QK643yin8U15TdGamgszqQ6KLhXsCQjp6vvQ8JfXwLfJsnTtiLz` | 44 | 109,945 | 118,833–121,715 (n=3) | -11,770 |
| create_atas_trader | `3fvp4SQULqsWgHNiX5jxr6qPe5He199AGT9p9z1QQUgJbbtsRC6irYvpWyB64cpAYAcgzMT9V2YsnED6HiWqkUPb` | 47 | None | not measured | — |
| buy_door0 | `2wecUvivMNMh5XfiBAdM7cvi9jYz1MrMNkW6hhCtPWstMU65oFGmjcg6RhLwfdxjN1DPvXQRYdLgMv3rDixBvvv5` | 49 | 68,327 | 66,677–71,380 (n=3,348) | -3,053 |
| buy_door1 | `Z3EaGfytGKqPbTzbpF1k3rHLNhsoKYTxjjwDqZbDQrg828dmMWHXtwbfFdRaGXqgAM8YnDv65EkJiGuSqARBZnk` | 52 | 62,560 | 66,677–71,380 (n=3,348) | -8,820 |
| sell_door0 | `52NuzdFjLLoZ9UnYg5bMS22GXkGvqtXoVMz2pB9D4MQtkSfRAVvt7zNNRS2GZcjhKcARLAcw5piFrHdw6YzbjN7Z` | 54 | 65,782 | 64,089–68,603 (n=1,673) | -2,821 |
| convert_door0_to_door1 | `kSahtzairaGD87RuEpE83ijXb7cuZ8UYqhpu5CeGFXhJDfDtXaqA1wrzhdTsdSFfJUusyixcuxdnKhbfQ1QULqM` | 57 | 79,981 | 81,205–85,715 (n=800) | -5,734 |
| buy_room_token | `3ZDYR4NqPotH6NZxKWTf1Pr2KRmD7UxLDuGxZ3sPs7VjhYJ2R2WSJ14JAjqWxXVEE7ubB6FaFRrqXBEsvcmj2YhJ` | 59 | 44,280 | 45,722–45,753 (n=840) | -1,473 |
| retire_pending | `5i2NEqDg6DgkWPu2NwuRyVddHiFbLDRWzd83YejjS7X6fehabxHphvJ8wa6j5kGQ5RYQbmEaSE3FfFsmRfVsG8W9` | 62 | 31,331 | 22,585–31,295 (n=829) | +36 |
| claim_door_fees | `3kovo9nLW4r9tXZ9VFXvZRvmjPXpuKp5nPbdoWsp9VbQiHaL8nhYuU9wKKWMDdr4sfFCCVLVvnWPHFyK32vjUwn3` | 64 | 56,591 | 45,008–51,764 (n=808) | +4,827 |

ATA rows are client setup (Associated Token program), not doors program CU.

**Expected failures:**

| case | landed on-chain | signature | slot | error |
|---|---|---|---|---|
| create_room_without_matcher_signature | yes | `4LZiNQGz26Pw8uuqebZx8uAuU6jdZkKd17p7DVmgVQaenauNNghmPmgDc1niZjkn3wSyGpf78AgBm9tSDfwLnbSa` | 627 | {"InstructionError":[1,{"Custom":3010}]}; `Program log: AnchorError caused by account: matcher. Error Code: AccountNotSigner. Error Number: 3010. Error Message: The given account did not sign.` |
| open_door_without_matcher_signature | yes | `4tmyoJpBpZY2zMqRXAcUMPP5zoHY5A5nkua97ma3o4edPtMLo76NVY6WFZR6UzQnT2ZtCASEUhAiZBcvrktUj1aj` | 629 | {"InstructionError":[1,{"Custom":3010}]}; `Program log: AnchorError caused by account: matcher. Error Code: AccountNotSigner. Error Number: 3010. Error Message: The given account did not sign.` |
| create_room_signature_over_different_routing_data | no: rejected before execution | — | — | `SignatureFailure`: Transaction simulation failed: Transaction did not pass signature verification |
| open_door_signature_over_different_routing_data | no: rejected before execution | — | — | `SignatureFailure`: Transaction simulation failed: Transaction did not pass signature verification |
| sell_exceeding_balance | yes | `7N3tLqC5qSHzXE7KeW8JWumsYGYKbjf9RumExiKvchMM5SJCkpMXwkeqL3wxapkq2WMcaSZuQYXvKj1Yja23yEq` | 631 | {"InstructionError":[1,{"Custom":1}]}; `Program TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb failed: custom program error: 0x1` |
| claim_door_fees_by_non_recipient | yes | `3GzX4ktd5t9gtt8BZ7Gnc1jaYN3nLfC47hCVZaEinNUiBgyHU6C6oAp84MqVTXXMY24scsSB64SbghViV6g59Z7F` | 634 | {"InstructionError":[1,{"Custom":6006}]}; `Program log: AnchorError thrown in programs/doors_v1/src/lib.rs:750. Error Code: Authority. Error Number: 6006. Error Message: Unauthorized.` |

**On-chain state checks after the sequence:**

| check | result |
|---|---|
| room mint `AkMjSLbrRnypSk53gpu7623h35kMVJLVU8T3v4PrSYiB`: supply, mint/freeze/metadata authorities | 1000000000000000, None, None, None → ok |
| door 0 mint `5mUvyhJzP6pavprLqKMdkLA9apxXZsAhQ3tY7sbU2S2t`: supply, authorities | 1000000000000000, None, None, None → ok |
| door 0 backing vault vs circulating door supply | 882397366623 vs 882397366623 → equal |
| door 1 mint `CEiuZZE1RuvC8UkwJ3jVBntK7NL1ZaXfN2eKcPT6feU`: supply, authorities | 1000000000000000, None, None, None → ok |
| door 1 backing vault vs circulating door supply | 4388842602598 vs 4388842602598 → equal |
| reserve vs curve integral of `sold` | 197908792 vs 197908792 → covers |
| ReserveVault lamports − rent vs `reserve` | 197908792 vs 197908792 → covers |
| RoomVault vs unsold supply | 992967883781714 vs U − 7032116218286 → covers |
| fee counters vs 60/40 split of every Trade event's fee | expected {'door0': 893538, 'door1': 594060, 'fee_total': 2974380, 'founder': 0, 'pending_reserve': 297030, 'protocol': 1189752}; on-chain {'door0': 893538, 'door1': 594060, 'fee_total': 2974380, 'founder': 0, 'pending_reserve': 297030, 'protocol': 1189752} → match |
| retire_pending | pending 0, reserve +297030 |
| claim_door_fees (door 0) | accrued 0, claimed 893538 |

**Live CU against the VM.** The VM column comes from LiteSVM running the same
ELF (`verification/devnet/deployed_elf_vm/`):

- most localnet figures sit at or below the VM range;
- `open_door` is 11,770 below the VM maximum;
- `claim_door_fees` is 4,827 above it, and `create_room` 2,728 above.

The likely source is the different bundled Token-2022 and ATA binaries, since
the doors code is identical. That is not established here. **The throughput
headroom figures in `verification/cu.md` remain VM measurements until the
devnet run replaces this table.** Devnet runs the cluster's deployed SPL
programs and active feature set.

## Devnet

Pending funding. `run_deploy.sh` will record the program ID, deploy signature,
deploy slot, ProgramData account and every smoke-test and failure-case
signature with its slot and live CU, under `verification/devnet/devnet/`.

**Cost on devnet** (Rent sysvar at slot 518,695,292: 5,080 lamports per byte):

| item | cost |
|---|---|
| ProgramData for the 525,032-byte ELF | 2.668 SOL |
| program account | 0.00083 SOL |
| buffer-write transaction fees | a few thousandths of a SOL |
| smoke sequence: two rooms, two doors, 0.25 SOL of trades | under 0.5 SOL |

## Mainnet: what differs

1. **Keys.**
   - Generate the program and upgrade-authority keys on hardware the owner
     controls, not in a cloud session.
   - Store the upgrade authority offline, or as a multisig (below).
   - The matcher key lives with the matcher service. It must not be the
     upgrade authority or the admin.
2. **Config admin.** `initialize_config` makes the current upgrade authority
   the Config admin. To separate them, hand admin to a distinct key with
   `update_config(settings, new_admin)` after initialising.
3. **Protocol fee recipient.** Devnet uses the deploy wallet. Mainnet needs the
   real treasury address.
4. **Funding and cost.** ProgramData costs the same 2.668 SOL at the current
   5,080 lamports-per-byte rent. The deploy wallet also pays the buffer-write
   fees, with a priority fee under load.
5. **Run from a fresh session**, against the mainnet RPC the owner chooses, after
   a successful devnet run of this exact ELF.
6. **The tip regression must be fixed or the deploy commit pinned.** Do not
   deploy `8ce373f`.

## Open owner decision: upgrade authority

**This is unresolved, and this document does not decide it.**

Every room and door mint has its mint, freeze and metadata-update authorities
revoked; the rehearsal checks all three on-chain. But while the program has a
live upgrade authority, whoever holds that key can replace the program, and
with it every rule that guards the reserve, the backing and the fees. Scanners
and careful buyers check exactly this.

The options:

| option | what holders get | cost |
|---|---|---|
| keep a single upgrade key | nothing beyond trust in the key holder | the fastest response to bugs |
| multisig upgrade authority (e.g. Squads) | no single key can upgrade | slower fixes; the signer set is public |
| timelocked upgrades | time to exit before a change lands | needs a timelock program or multisig with delay; still upgradeable |
| immutable (`solana program set-upgrade-authority --final`) | the program can never change | no bug fix ever, and **graduation (phase 2) cannot be added to this program ID**: it would need a new program |

Phase 2 (graduation) does not exist in this version, so making v1 immutable
would freeze it at "curve only, graduation fails closed".
