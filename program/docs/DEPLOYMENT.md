# Doors v1 deployment

4 November 2026.

## 1. Status

| part | status |
|---|---|
| program ID, upgrade authority, matcher authority | generated; public keys in §2 |
| build of the deploy source | done; 46 SBF tests passing and 1 ignored (the reproduction of open finding M-7), including the 10,000-iteration property run; ELF pinned in `devnet/DEPLOY_ELF.sha256` (§3) |
| **devnet deployment** | **DONE**, 5 November 2026: deploy slot 518,934,300, on-chain bytes equal the pinned ELF, Config initialised and read back with 0 of 22 fields differing (§5) |
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
| source | the branch tip, commit `b6fe25d` (`verification/build.json` records it with every source hash) |
| history | Until 5 November the deploy source was `436c002` plus the program-ID patch (ELF `f2cfdb85…b436`; `verification/devnet/deployed_source.patch`, `deployed_elf_vm/`), because the tip `8ce373f` failed 10 of 38 SBF tests. The tip was then fixed (`6385fdd`), extended (`e9bd2aa`, `1558b2e`) and repinned ([CORRECTIONS](CORRECTIONS.md)). |
| ELF | 522,776 bytes, SHA-256 `c36ba443d6bb08726028919f28de1b8432422b876433ed4a208a96e5a808ed29`, pinned in `devnet/DEPLOY_ELF.sha256`. `deploy.sh` refuses any other binary. |
| IDL | byte-identical to `anchor idl build`, SHA-256 `cbd6625e826527e2432095bfaf08d0d93dad35f4746842db880c6eaa58861d6e` |
| tests on this exact source | `cargo test --locked --test svm`: 46 passed, 0 failed, 1 ignored (the reproduction of open finding M-7 in `SECURITY_REVIEW.md`); `cargo fmt --check` clean; `check_layouts.py` passes |

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

## 5. Devnet deployment — done

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
  3.63 SOL).
- Its slots are local.

The devnet run below has none of these limits.

### Devnet run

'''+rep+'''
```text
'''+"
".join(checks)+"

"+summary+'''
```

**Live devnet CU against the VM.** The VM column is what LiteSVM (Agave 4.3.2)
observed for this ELF at fixed fixture addresses. These are observations, not
upper bounds. Live devnet figures exceeded them for:

'''+"".join(f"- `{n}`: {d:,} CU above the VM observed maximum;
" for n,d in above)+'''
That is real-cluster confirmation that no VM figure is a ceiling.

**Against the service's 400,000 CU limit.** The worst tested launch is 326,893
VM CU (a prefunded takeover `create_room`). Adding the largest drift seen here,
12,003, still leaves about 61,000 CU of margin.

### Localnet run

| item | value |
|---|---|
| program ID | `D7YsLsiJXoAF38vCUhFqYStepvSz6goG7EddHDe5NVJG` |
| deploy signature | `Q4ejdBmxQSSq1x5jKpVH3taxPLKoNkUGuf1dCULQ5buqwXNf3CeoPaS8VRLSVHks89dyBpkM7iiCbnbnrwEzHj8` |
| deploy slot (`lastDeploySlot`) | 17 |
| ProgramData account | `4SbbsdYLxSgVP42JRpGj6DZVSBp9tVas8iTRQfiFjMNi` |
| upgrade authority | `HbvturaYqGpCVqrWV6StwJ3rJdBh2QQr26vyo2Q2nky` |
| ProgramData lamports | 3,639,725,040 |
| local ELF SHA-256 | `c36ba443d6bb08726028919f28de1b8432422b876433ed4a208a96e5a808ed29` |
| on-chain bytes SHA-256 (first ELF-length bytes of `solana program dump`) | `c36ba443d6bb08726028919f28de1b8432422b876433ed4a208a96e5a808ed29` |
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
| initialize_config | `35Lu6ciznMqoHR9zBcRkDkVJZe8boNtKhb5jTfLZpkk1JuWWZHGnWEy6nLQGQpbszUYdZJwh3mwdabrhkuvQhWf5` | 22 | 13,347 | 13,347–13,347 (n=1) | +0 |
| create_room | `9AC6xLfYACU55ZuH1sp7jgHFGcWXNqs8AdUAWhidR4Vs7bL3phqHrcjRUVnYmSBHfsTaZZCBt9XDWQY488NJBcQ` | 25 | 227,089 | 230,768–230,768 (n=1) | -3,679 |
| create_atas_launcher | `3qPjb8WKWBpSEr62ocJwVvfmhC7p3cUrdkFKbCdfkWNJc7HrxKobtWJgVFSAq7ioGWfp916JUDAq8izSvpVAfqA3` | 27 | None | not measured | — |
| open_door | `5AFYv39zi2aHrJCiLD3aivjxBxy5U5UxsGkcp8BRxU246ESq95eBUwCyoMyGeMVRFHmfhs19nfPAoEYMMzXzspcV` | 30 | 132,218 | 138,509–149,950 (n=3) | -17,732 |
| create_atas_trader | `QzKVTr29mHvNNDYxViffGaekK5zc3exxUe2Lqm2pTSJhogdyCXsRwTQ1NH1VG4BwU9spcNgM82vP9K7ZE8KZt1Z` | 32 | None | not measured | — |
| buy_door0 | `5Fg3cTW4v5JzMNEBDKzofZGZSDzjENgc4p1kDTPdsc3fU5Fcd3wgFUgYuhj1Es3qDbbJHaRUSn6RAwcjvRgzJ9yV` | 35 | 62,965 | 57,090–69,303 (n=3,348) | -6,338 |
| buy_door1 | `VPsiuoUivd5nb5BhheQnRvs3FKzbJms6f1avHtguF8PKqeyrLi4Sma13ghY7qLv8xVbGu73pxTF3SzHaRwzffbw` | 37 | 63,198 | 57,090–69,303 (n=3,348) | -6,105 |
| sell_door0 | `5nwNvKZ2veAmPFrJQYkbwMJvcHcE7DH9zRKMqC25Xg5jHAS7uGVSRY2MhZwd9fadqRAfeyGB2BsBeUcomoLsNk6K` | 39 | 60,041 | 54,175–57,189 (n=1,673) | +2,852 |
| convert_door0_to_door1 | `3mwSbYfBQCEqgXcPk2CKLQx2rj6ug9dJk9iNnHReTg23ydT9eFFFce4wkdWMuqxqQpQ1XwnqQgoPVvj5PumtZxWB` | 42 | 70,117 | 65,833–68,844 (n=800) | +1,273 |
| buy_room_token | `5GMzsemwwNgCJqQsPhSDNqf1WiBEnJXi6VHt3nYoonWyE198Bk9xgj2LtAHGeh2FhenafiDhjBVqqBy7S7HXn6G4` | 44 | 41,524 | 44,575–53,568 (n=840) | -12,044 |
| retire_pending | `2aUQpGMwaS7EhndLTVvo3eYDKczyy3Qcmtt1xm5HGY1skHd8dMpjCyzw9TmrFsVokTWYiFRsJwY51oe9gaZ9Du7y` | 47 | 29,716 | 20,819–29,789 (n=829) | -73 |
| claim_door_fees | `4ftBig6NnuG8XU5cQNCPcRNB65p6GdDgRqat2ZLZzHwSZT7MEKBK61v8GfSz6xMAo5eCyWHSDtsnARFKxwLNwxfQ` | 49 | 50,837 | 36,580–40,337 (n=808) | +10,500 |

ATA rows are client setup (Associated Token program), not doors program CU.

**Expected failures:**

| case | landed on-chain | signature | slot | error |
|---|---|---|---|---|
| create_room_without_matcher_signature | yes | `3QNk1vaQyrwsY6d1jmFxMP9FUQrRKmuojBRwVPPqrcajHkGCu68tENxxEyBHGSfQmXf9gpEzd6LUpGwpXg539oE3` | 52 | {"InstructionError":[1,{"Custom":3010}]}; `Program log: AnchorError caused by account: matcher. Error Code: AccountNotSigner. Error Number: 3010. Error Message: The given account did not sign.` |
| open_door_without_matcher_signature | yes | `2SFA1x6otstGpxWNjETcAeXbB4vRUhkB8sq71okmUgVt2kAmBDaLh7A1D85G8LfMxjhruGbSYd3A1UNrt3jLZ4Yg` | 55 | {"InstructionError":[1,{"Custom":3010}]}; `Program log: AnchorError caused by account: matcher. Error Code: AccountNotSigner. Error Number: 3010. Error Message: The given account did not sign.` |
| create_room_signature_over_different_routing_data | no: rejected before execution | — | — | `SignatureFailure`: Transaction simulation failed: Transaction did not pass signature verification |
| open_door_signature_over_different_routing_data | no: rejected before execution | — | — | `SignatureFailure`: Transaction simulation failed: Transaction did not pass signature verification |
| sell_exceeding_balance | yes | `E8Cz8uz1hF9tfN2iJL15VNbza4QrV8tSXiEWWidCpCy6NiWWCGCdqRdA3QGhqkPvv2riiohZz6NN8xVSgvt9ELN` | 57 | {"InstructionError":[1,{"Custom":1}]}; `Program TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb failed: custom program error: 0x1` |
| claim_door_fees_by_non_recipient | yes | `3XBpNp9oLWfPeqU6teJr9uw36672XSiMTZvMBYGk9NdLhXN5KLyJqxq5sXLrx7xZCbRvPe2dLSuv8U58MmuEY2Wd` | 60 | {"InstructionError":[1,{"Custom":6006}]}; `Program log: AnchorError thrown in programs/doors_v1/src/lib.rs:757. Error Code: Authority. Error Number: 6006. Error Message: Unauthorized.` |

**On-chain state checks after the sequence:**

| check | result |
|---|---|
| room mint `t1tz3w9ZEw5APKQChdVEVNVM18ykGw6oJ51RPwanVGk`: supply, mint/freeze/metadata authorities | 1000000000000000, None, None, None → ok |
| door 0 mint `FphDPsc2Wgz6vWjam8pGGzfGtwv9VqE6PAi5yYqbWM7X`: supply, authorities | 1000000000000000, None, None, None → ok |
| door 0 backing vault vs circulating door supply | 882397366623 vs 882397366623 → equal |
| door 1 mint `HVFP5tMbo7782CtGuhc2GFM1iV6ATrVPavPj9v6ytWre`: supply, authorities | 1000000000000000, None, None, None → ok |
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

**Live CU against the VM.** The VM column is what LiteSVM (Agave 4.3.2) observed for
the pinned ELF itself, at fixed fixture addresses (`verification/svm_report.json`;
`e2e.sh` refuses a baseline from any other ELF). **These are observations, not upper
bounds.** Live figures in this run range from 17,732 CU below the VM observed maximum
to 10,500 above it:

- `claim_door_fees` is 10,500 above the VM observed maximum;
- `sell_door0` is 2,852 above the VM observed maximum;
- `convert_door0_to_door1` is 1,273 above the VM observed maximum;

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
