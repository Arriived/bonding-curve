# Doors v1 Anchor program

Curve-phase implementation of the [build spec](../research/doors_into_one_room/PERMANENT_CURVE_SPEC.md).
Work branch: `claude/program-v1`, based on research commit `de1f7fd`.
No program is deployed by the build or test workflow.

The program creates immutable Token-2022 room and door mints, premints their
entire supply and revokes mint and metadata update authorities atomically.
The native-WSOL fee account uses the existing classic SPL native mint.
Room creation and door opening require the configured matcher to co-sign the
whole transaction alongside the launcher. These launch instructions must be
top-level: an untrusted CPI proxy cannot reinterpret a propagated matcher
signer into different metadata or routing arguments. The matcher chooses a random u64
room nonce; `scripts/room_nonce.py` generates one using the OS CSPRNG. Encode
it as an exact u64/BigInt/BN, never a JavaScript Number. A collision needs a new
nonce and fresh signatures. Config is read-only on permissionless creation.

`buy`, `sell`, `convert`, `retire_pending`, door/founder fee claims, recipient
rotation, protocol sweeps and slug release are implemented. Room-token and
door routes have the same curve and fee. There is no door-to-room conversion,
door closing or referral feature. Founder plumbing defaults to zero; the
generated deployment settings preserve the exact existing 60/40 split.
The reason for carrying it is the pending measurement of founder volume lost
to copies, not a finding that a nonzero share is justified.

Status 0 is the curve. At the room's copied Config trigger a capped buy or
retirement sets status 1, complete; buy/sell then stop. Open, convert and
claims remain available. Status 2, graduation, Meteora CPIs, pool swaps and
pool checkpoints are phase 2 and cannot be reached by this version. A
status-2 liveness request fails closed until that adapter exists.

## Toolchain and build

The reproducible Linux workflow is [program-v1.yml](../.github/workflows/program-v1.yml).
It pins Anchor **1.2.2**, Agave/Solana stable **4.4.0**, cargo-build-sbf **4.5.0**,
platform-tools **v1.58** and host Rust **1.99.0**. Anchor uses its `solana-v4`
feature explicitly. LiteSVM is pinned to **0.18.1**, with its supported
**Agave 4.3.2** test runtime locked from the upstream dependency snapshot
`aff262da627cbd6dfef24d24fb435fbaa5e61bc4`. Unbounded resolution against 4.4
does not compile; this test-runtime version is distinct from the 4.4 build
target. The resolved Rust crates are pinned by Cargo.lock. Actual version outputs and dependency graph are
written to `verification/build.json`; the SBF builder's default platform
version in `--version` is overridden by the explicit build flag below.

Use Linux (including an already configured WSL environment) with these tools.
For Agave, the official installer is
`https://release.anza.xyz/v4.4.0/install`. Install cargo-build-sbf with
`cargo install cargo-build-sbf --version 4.5.0 --locked`; put `~/.cargo/bin`
before the Solana installer's bin directory so its bundled builder cannot
shadow the pinned version. CI invokes the pinned binary explicitly. Use the
official Anchor 1.2.2 release binary. The current Windows workspace has no compiler or
WSL installation; its builds run on GitHub's Ubuntu runner.

From this directory:

```sh
cargo check --locked --tests
cargo build-sbf --tools-version v1.58
cargo build-sbf --tools-version v1.58 --manifest-path test-fixtures/launch_proxy/Cargo.toml --sbf-out-dir "$(pwd)/target/deploy"
mkdir -p target/idl
anchor idl build -o target/idl/doors_v1.json
python3 scripts/check_layouts.py
cargo test --locked --test svm -- --nocapture
cargo fmt -- --check
python3 scripts/build_evidence.py
python3 scripts/report_cu.py
```

Treat every SBF stack/frame diagnostic as a build failure even if the builder
returns success. CI explicitly enforces this. The generated IDL is
`target/idl/doors_v1.json`; the ELF is `target/deploy/doors_v1.so`. CI uploads
both, the lockfile, formatted source and verification evidence. Secret
deployment keypairs are never uploaded. The CU generator writes the spec's
measured block from execution evidence and refuses to fabricate absent data.

## Tests and accounting

`tests/svm.rs` loads the compiled Anchor ELF into LiteSVM, calls the real SPL
programs and leaves transaction signature verification enabled. Its mixed
property test executes at least 10,000 iterations. It uses a fixed random
seed and deterministic public test keys for reproduction; fixture IDs and keys
are separate from the production nonce generator and deployment wallets.
Only duplicate-transaction history is disabled in the test VM, so repeated
random operations can run without collecting a new blockhash each time.

Tests exercise creation, opening with first buys, both trade routes,
conversion, capped crossing and retirement, all fees, admin bounds, paused
trades, exact liveness boundaries, lock release/takeover, immutable mint
authorities, changed/missing matcher signatures, full redemptions, slippage,
zero balances, donations and holder burns. Signature tests include a test-only
untrusted SBF proxy for launch-CPI rejection; it is not an application
instruction or deployment component. The external audit in each test
enumerates every door, checks global fee coverage and reconciles all token
account balances to live mint supply. Each affected instruction is checked
for `delta(ReserveVault lamports) == delta(room.reserve)` independently of
its internal assertions. Initial account funding is tested separately.

Prices, payouts, available inventory, fees and retirement use **program
counters only**. Vault balances cover liabilities with `>=`; mint supply is
exactly U at initialization and `<= U` afterwards. Donations and burns change
neither prices nor accounting liabilities. All unaccounted surplus stays
locked. There is no sweep or automatic retirement of surplus.

The fixed Room schema has no aggregate door-fee counter. On-chain checks
prove the global fee invariant inductively: every path changes FeeVault and
its affected fee counters by exactly the same amount. It also checks coverage
of room liabilities plus touched doors; the tests check the full global sum.
An off-chain audit must ingest Token-2022 transfers into vaults and holder
burns as well as launchpad events. Excess balance or reduced supply alone is
not a program bug. See [the approved corrections](docs/CORRECTIONS.md).

Measured CU is VM execution cost, not a cluster throughput benchmark. The
spec reports the compute-only ceiling from the actual writable-account cap.
Signature, lock, data and requested compute-budget costs also constrain
accepted transactions. Pool-phase compute remains unmeasured.

## Devnet deployment

Use a separate devnet wallet and program keypair. The checked-in program ID
is a test address; its private key is not supplied. Generate your deployment
program keypair and sync its address **before rebuilding**:

```sh
solana-keygen new --outfile target/deploy/doors_v1-keypair.json
anchor keys sync
cargo build-sbf --tools-version v1.58
anchor idl build -o target/idl/doors_v1.json
cargo test --locked --test svm -- --nocapture
solana config set --url devnet
solana airdrop 2
anchor deploy --provider.cluster devnet
```

The airdrop amount is a request, not a guarantee or deployment-cost estimate.
Check the wallet balance and simulation/rent requirements before deploying.
Keep the program upgrade key and matcher key distinct. Do not commit either.

After deployment, initialize Config through `initialize_config(settings)`
using the IDL. Its signer must equal the deployed program's **current upgrade
authority**, validated against the canonical ProgramData account; an arbitrary
first caller cannot take the admin role. Settings defaults can be generated
without signing or submitting anything:

```sh
python3 scripts/default_config.py --matcher MATCHER_PUBLIC_KEY --recipient PROTOCOL_PUBLIC_KEY
```

Pass the returned decimal strings as exact u64 values. The output preserves
the verified curve/trigger and shared liveness defaults, including founder
share **0 bps** and zero launch/conversion fees. Config updates require its
admin; fee and curve parameters are snapshotted into each new room. Existing
rooms keep their original trigger and snapshots after Config changes.

Launch clients derive SlugLock from raw metadata, fetch its holder if any,
obtain the matcher's route/nonce/signature and the launcher's signature over
the identical recent-blockhash transaction. The instruction creates a first
buy's canonical ATA atomically if needed; later trades expect a pre-existing
ATA, normally created idempotently in a preceding client instruction. Use
versioned transactions/lookup tables where maximum metadata and account lists
exceed the transaction packet budget. Room IDs are not enumerable; discover
rooms and doors with getProgramAccounts and account discriminators.

The v1 program intentionally stops curve trading at completion. Deploy only
with that explicit phase boundary understood; this repository does not claim
an implemented graduation path.
