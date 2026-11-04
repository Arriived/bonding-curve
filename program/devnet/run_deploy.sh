#!/usr/bin/env bash
set -euo pipefail
# Deploy doors_v1, initialise Config, run the smoke sequence and failure cases.
# Usage: devnet/run_deploy.sh <cluster_url> <keys_dir> <out_dir>
# keys_dir holds program.json, upgrade-authority.json, matcher-authority.json,
# deploy-wallet.json, smoke-launcher.json, smoke-trader.json. Only public keys
# are written to out_dir. Run from program/ after `cargo build-sbf --tools-version v1.58`.
URL="$1"; KEYS="$2"; OUT="$3"
mkdir -p "$OUT"
export DOORS_RPC="$URL"
SO=target/deploy/doors_v1.so
pk() { solana-keygen pubkey "$KEYS/$1.json"; }
PROGRAM=$(pk program); UPGRADE=$(pk upgrade-authority); MATCHER=$(pk matcher-authority)
WALLET=$(pk deploy-wallet); LAUNCHER=$(pk smoke-launcher); TRADER=$(pk smoke-trader)
grep -q "declare_id!(\"$PROGRAM\")" programs/doors_v1/src/lib.rs   # source must carry this program ID

{ rustc --version; cargo --version; cargo-build-sbf --version; anchor --version; solana --version; } > "$OUT/toolchain.txt"
sha256sum "$SO" | tee "$OUT/elf.sha256"

# 1. Deploy. The deploy wallet pays; the upgrade authority is a separate key.
# A pre-generated buffer keypair file stops the CLI printing an ephemeral seed phrase.
BUF=$(mktemp -d)/buffer.json
solana-keygen new --no-bip39-passphrase --silent --outfile "$BUF" >/dev/null
solana program deploy "$SO" --url "$URL" --keypair "$KEYS/deploy-wallet.json" \
  --program-id "$KEYS/program.json" --upgrade-authority "$KEYS/upgrade-authority.json" \
  --buffer "$BUF" --output json > "$OUT/deploy.json"
rm -f "$BUF"
cat "$OUT/deploy.json"
solana program show "$PROGRAM" --url "$URL" --output json > "$OUT/program_show.json"
cat "$OUT/program_show.json"
# Deployed bytes against the local ELF (programdata may be padded past the ELF length).
solana program dump "$PROGRAM" "$OUT/onchain.so" --url "$URL" >/dev/null
head -c "$(stat -c %s "$SO")" "$OUT/onchain.so" | sha256sum | tee "$OUT/onchain.sha256"
rm "$OUT/onchain.so"

# A program is executable from the slot after its deploy slot.
DEPLOY_SLOT=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["lastDeploySlot"])' "$OUT/program_show.json")
until [ "$(solana slot --url "$URL" --commitment confirmed)" -gt $((DEPLOY_SLOT + 1)) ]; do sleep 1; done

# 2. Initialise Config with the generated defaults (initialize_config is signed by the upgrade authority).
python3 scripts/default_config.py --matcher "$MATCHER" --recipient "$WALLET" > "$OUT/settings.json"
devnet/target/release/doors-devnet init "$KEYS" "$OUT/settings.json" "$OUT/init.json"
devnet/target/release/doors-devnet config "$OUT/settings.json" "$OUT/config.json"

# 3. Smoke sequence and 4. failure cases.
devnet/target/release/doors-devnet smoke "$KEYS" "$OUT/smoke.json"
devnet/target/release/doors-devnet fail "$KEYS" "$OUT/smoke.json" "$OUT/failures.json"
echo "program $PROGRAM upgrade_authority $UPGRADE matcher $MATCHER deploy_wallet $WALLET launcher $LAUNCHER trader $TRADER" | tee "$OUT/pubkeys.txt"
