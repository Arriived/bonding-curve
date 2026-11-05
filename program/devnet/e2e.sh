#!/usr/bin/env bash
set -euo pipefail
# End-to-end test of the deployed program: smoke sequence, failure cases and
# hard assertions on the on-chain state (devnet/report.py --check).
#
# The target is the single line in devnet/e2e-target:
#   localnet  - starts a fresh solana-test-validator, deploys the pinned ELF and
#               initialises Config (devnet/deploy.sh), then runs the test.
#   devnet    - runs the test against the program already deployed on devnet.
#               PENDING until devnet/deploy.sh has run there: until then this
#               exits 3 with a PENDING message. It is never skipped silently.
#
# Usage: devnet/e2e.sh <keys_dir>   (run from program/, after building the
# deploy ELF and `cargo build --release` in devnet/)
#
# DOORS_LOCALNET_FEATURES_FROM=<cluster url> (localnet only): start the local validator with that
# cluster's feature set (--clone-feature-set) and write to verification/devnet/localnet-features/,
# to separate feature-set effects on CU from everything else. With DOORS_LOCALNET_CLONE_TOKEN_PROGRAMS=1
# as well, it also clones that cluster's Token-2022, SPL Token and ATA programs in place of the
# validator's bundled ones, and writes to verification/devnet/localnet-cluster-programs/.
KEYS="$1"
cd "$(dirname "$0")/.."
TARGET=$(tr -d '[:space:]' < devnet/e2e-target)
pk() { solana-keygen pubkey "$KEYS/$1.json"; }
PROGRAM=$(pk program)
OUT="verification/devnet/$TARGET"
FEATURES=()
if [ "$TARGET" = localnet ] && [ -n "${DOORS_LOCALNET_FEATURES_FROM:-}" ]; then
  FEATURES=(--clone-feature-set --url "$DOORS_LOCALNET_FEATURES_FROM")
  OUT="verification/devnet/localnet-features"
  if [ "${DOORS_LOCALNET_CLONE_TOKEN_PROGRAMS:-}" = 1 ]; then
    FEATURES+=(--clone-upgradeable-program TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb
               --clone-upgradeable-program TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA
               --clone ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL)
    OUT="verification/devnet/localnet-cluster-programs"
  fi
fi

case "$TARGET" in
  localnet)
    URL=http://127.0.0.1:8899
    LEDGER=$(mktemp -d)
    solana-test-validator --ledger "$LEDGER" --reset --quiet --rpc-port 8899 "${FEATURES[@]}" > "$LEDGER/validator.log" 2>&1 &
    VALIDATOR=$!
    trap 'kill "$VALIDATOR" 2>/dev/null || true; wait "$VALIDATOR" 2>/dev/null || true; rm -rf "$LEDGER"' EXIT
    until solana cluster-version --url "$URL" >/dev/null 2>&1; do sleep 1; done
    for w in deploy-wallet smoke-launcher smoke-trader; do
      solana airdrop 20 "$(pk "$w")" --url "$URL" >/dev/null
    done
    rm -rf "$OUT"
    devnet/deploy.sh "$URL" "$KEYS" "$OUT"
    ;;
  devnet)
    URL=https://api.devnet.solana.com
    if ! solana program show "$PROGRAM" --url "$URL" >/dev/null 2>&1 || [ ! -f "$OUT/deploy.json" ]; then
      echo "PENDING: $PROGRAM is not deployed on devnet yet (deploy wallet $(pk deploy-wallet) unfunded)." >&2
      echo "Fund it, run: devnet/deploy.sh $URL <keys_dir> $OUT   then rerun this test." >&2
      exit 3
    fi
    # Smoke wallets pay rent for two rooms, two doors and about 0.25 SOL of trades.
    for w in smoke-launcher smoke-trader; do
      BAL=$(solana balance "$(pk "$w")" --url "$URL" --lamports | cut -d' ' -f1)
      if [ "$BAL" -lt 600000000 ]; then
        solana transfer --url "$URL" --keypair "$KEYS/deploy-wallet.json" --allow-unfunded-recipient "$(pk "$w")" 0.6 >/dev/null
      fi
    done
    ;;
  *)
    echo "devnet/e2e-target must be 'localnet' or 'devnet', not '$TARGET'" >&2
    exit 2
    ;;
esac

export DOORS_RPC="$URL"
devnet/target/release/doors-devnet smoke "$KEYS" "$OUT/smoke.json"
devnet/target/release/doors-devnet fail "$KEYS" "$OUT/smoke.json" "$OUT/failures.json"
# The VM baseline must be the SBF evidence of the pinned deploy ELF itself, or "live vs VM" compares
# two different programs. verification/build.json records the ELF that produced svm_report.json.
PINNED=$(cut -d' ' -f1 devnet/DEPLOY_ELF.sha256)
VM_ELF=$(python3 -c 'import json;print(json.load(open("verification/build.json"))["elf_sha256"])')
if [ "$PINNED" != "$VM_ELF" ]; then
  echo "VM baseline verification/svm_report.json is from ELF $VM_ELF, not the pinned $PINNED;" >&2
  echo "rerun the SBF suite and scripts/build_evidence.py on the pinned source first." >&2
  exit 1
fi
python3 devnet/report.py "$OUT" verification/svm_report.json "$TARGET" --check
echo "e2e $TARGET: PASS"
