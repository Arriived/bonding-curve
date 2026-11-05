#!/usr/bin/env bash
set -euo pipefail
# Upgrade an already-deployed doors_v1 to the pinned ELF, then read Config back unchanged.
# Usage: devnet/upgrade.sh <cluster_url> <keys_dir> <out_dir> <settings.json the Config was initialised with>
# The upgrade authority signs; the deploy wallet pays (buffer rent is returned when the upgrade lands;
# a larger ELF also pays the permanent ProgramData extension). Run from program/ on the pinned source.
URL="$1"; KEYS="$2"; OUT="$3"; SETTINGS="$4"
cd "$(dirname "$0")/.."
mkdir -p "$OUT"
export DOORS_RPC="$URL"
SO=target/deploy/doors_v1.so
pk() { solana-keygen pubkey "$KEYS/$1.json"; }
PROGRAM=$(pk program); WALLET=$(pk deploy-wallet)
grep -q "declare_id!(\"$PROGRAM\")" programs/doors_v1/src/lib.rs
EXPECTED=$(cut -d' ' -f1 devnet/DEPLOY_ELF.sha256)
ACTUAL=$(sha256sum "$SO" | cut -d' ' -f1)
if [ "$ACTUAL" != "$EXPECTED" ]; then
  echo "refusing to upgrade: $SO is $ACTUAL, pinned deploy ELF is $EXPECTED" >&2
  exit 1
fi
{ rustc --version; cargo --version; cargo-build-sbf --version; anchor --version; solana --version; } > "$OUT/toolchain.txt"
echo "$ACTUAL  $SO" > "$OUT/elf.sha256"
solana program show "$PROGRAM" --url "$URL" --output json > "$OUT/program_show_before.json"
BUFDIR=$(mktemp -d)
trap 'rm -rf "$BUFDIR"' EXIT
trap 'echo "upgrade failed: recover any stranded buffer with" >&2
      echo "  solana program show --buffers --buffer-authority $(pk upgrade-authority) --url $URL" >&2
      echo "  solana program close <buffer> --authority $KEYS/upgrade-authority.json --recipient $WALLET --keypair $KEYS/deploy-wallet.json --url $URL" >&2' ERR
solana-keygen new --no-bip39-passphrase --silent --outfile "$BUFDIR/buffer.json" >/dev/null
# Same program ID + existing program = upgrade. The CLI extends ProgramData if the ELF grew.
solana program deploy "$SO" --url "$URL" --keypair "$KEYS/deploy-wallet.json" \
  --program-id "$KEYS/program.json" --upgrade-authority "$KEYS/upgrade-authority.json" \
  --buffer "$BUFDIR/buffer.json" --use-rpc --max-sign-attempts 20 --output json > "$OUT/upgrade.json"
cat "$OUT/upgrade.json"
solana program show "$PROGRAM" --url "$URL" --output json > "$OUT/program_show.json"
solana program dump "$PROGRAM" "$BUFDIR/onchain.so" --url "$URL" >/dev/null
head -c "$(stat -c %s "$SO")" "$BUFDIR/onchain.so" | sha256sum | cut -d' ' -f1 > "$OUT/onchain.sha256"
[ "$(cat "$OUT/onchain.sha256")" = "$ACTUAL" ]
DEPLOY_SLOT=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["lastDeploySlot"])' "$OUT/program_show.json")
until [ "$(solana slot --url "$URL" --commitment confirmed)" -gt $((DEPLOY_SLOT + 1)) ]; do sleep 1; done
# Config is not re-initialised: it must still decode and match the settings it was created with.
devnet/target/release/doors-devnet config "$SETTINGS" "$OUT/config.json"
echo "upgraded $PROGRAM on $URL to $ACTUAL; Config unchanged"
