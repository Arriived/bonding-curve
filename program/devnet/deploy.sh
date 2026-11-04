#!/usr/bin/env bash
set -euo pipefail
# Deploy doors_v1 and initialise Config on one cluster. Run once per cluster.
# Usage: devnet/deploy.sh <cluster_url> <keys_dir> <out_dir>
# Devnet status: PENDING (deploy wallet unfunded; see docs/DEPLOYMENT.md section 5).
# keys_dir holds program.json, upgrade-authority.json, matcher-authority.json,
# deploy-wallet.json, smoke-launcher.json, smoke-trader.json. Only public keys,
# signatures and hashes are written to out_dir. Run from program/ after
# `cargo build-sbf --tools-version v1.58` on the deploy source.
URL="$1"; KEYS="$2"; OUT="$3"
cd "$(dirname "$0")/.."
mkdir -p "$OUT"
export DOORS_RPC="$URL"
SO=target/deploy/doors_v1.so
pk() { solana-keygen pubkey "$KEYS/$1.json"; }
PROGRAM=$(pk program); MATCHER=$(pk matcher-authority); WALLET=$(pk deploy-wallet)

# Only the pinned deploy ELF (436c002 + program-ID patch) may be deployed.
grep -q "declare_id!(\"$PROGRAM\")" programs/doors_v1/src/lib.rs
EXPECTED=$(cut -d' ' -f1 devnet/DEPLOY_ELF.sha256)
ACTUAL=$(sha256sum "$SO" | cut -d' ' -f1)
if [ "$ACTUAL" != "$EXPECTED" ]; then
  echo "refusing to deploy: $SO is $ACTUAL, pinned deploy ELF is $EXPECTED" >&2
  exit 1
fi
{ rustc --version; cargo --version; cargo-build-sbf --version; anchor --version; solana --version; } > "$OUT/toolchain.txt"
echo "$ACTUAL  $SO" > "$OUT/elf.sha256"

# Deploy. The deploy wallet pays; the upgrade authority is a separate key.
# A pre-generated buffer keypair stops the CLI printing an ephemeral seed phrase.
BUFDIR=$(mktemp -d)
trap 'rm -rf "$BUFDIR"' EXIT
solana-keygen new --no-bip39-passphrase --silent --outfile "$BUFDIR/buffer.json" >/dev/null
solana program deploy "$SO" --url "$URL" --keypair "$KEYS/deploy-wallet.json" \
  --program-id "$KEYS/program.json" --upgrade-authority "$KEYS/upgrade-authority.json" \
  --buffer "$BUFDIR/buffer.json" --output json > "$OUT/deploy.json"
cat "$OUT/deploy.json"
solana program show "$PROGRAM" --url "$URL" --output json > "$OUT/program_show.json"
cat "$OUT/program_show.json"
# Deployed bytes against the local ELF (the dump may be padded past the ELF length).
solana program dump "$PROGRAM" "$BUFDIR/onchain.so" --url "$URL" >/dev/null
head -c "$(stat -c %s "$SO")" "$BUFDIR/onchain.so" | sha256sum | cut -d' ' -f1 > "$OUT/onchain.sha256"
[ "$(cat "$OUT/onchain.sha256")" = "$ACTUAL" ]

# A program is executable from the slot after its deploy slot.
DEPLOY_SLOT=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["lastDeploySlot"])' "$OUT/program_show.json")
until [ "$(solana slot --url "$URL" --commitment confirmed)" -gt $((DEPLOY_SLOT + 1)) ]; do sleep 1; done

# The upgrade authority signs (and pays rent for) initialize_config.
solana transfer --url "$URL" --keypair "$KEYS/deploy-wallet.json" --allow-unfunded-recipient \
  "$(pk upgrade-authority)" 0.05 >/dev/null
python3 scripts/default_config.py --matcher "$MATCHER" --recipient "$WALLET" > "$OUT/settings.json"
devnet/target/release/doors-devnet init "$KEYS" "$OUT/settings.json" "$OUT/init.json"
devnet/target/release/doors-devnet config "$OUT/settings.json" "$OUT/config.json"
echo "deployed $PROGRAM to $URL; Config initialised and matches settings"
