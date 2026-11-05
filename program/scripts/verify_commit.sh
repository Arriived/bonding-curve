#!/usr/bin/env bash
# Full SBF suite on a clean checkout of one commit, then the heap probe: the evidence every program change
# needs (CORRECTIONS.md). Builds the doors_v1 ELF and the launch_proxy test fixture as CI does (two tests
# load the fixture), runs every test including the 10,000-iteration property run, and prints the ELF hash,
# the test summary and the CU lines. The probe writes program/verification/heap_headroom[.<short>].json.
#
# Usage: program/scripts/verify_commit.sh <commit> <log_dir>
set -euo pipefail
C=$(git rev-parse --short "$1"); LOGS=$(realpath "$2"); mkdir -p "$LOGS"
REPO=$(git rev-parse --show-toplevel)
export PATH="$HOME/.cargo/bin:$HOME/.local/share/agave-4.4.0/solana-release/bin:$PATH"
WT=$(mktemp -d)/wt
git -C "$REPO" worktree add --detach "$WT" "$C" >/dev/null
trap 'git -C "$REPO" worktree remove --force "$WT"' EXIT
cd "$WT/program"
rustup override set 1.99.0-x86_64-unknown-linux-gnu >/dev/null
cargo-build-sbf --tools-version v1.58 > "$LOGS/$C.build.log" 2>&1
cargo-build-sbf --tools-version v1.58 --manifest-path test-fixtures/launch_proxy/Cargo.toml \
  --sbf-out-dir "$(pwd)/target/deploy" >> "$LOGS/$C.build.log" 2>&1
sha256sum target/deploy/doors_v1.so
set +e
cargo test --locked --test svm -- --nocapture > "$LOGS/$C.svm.log" 2>&1
status=$?
set -e
grep -E "CU_REPORT|PREFUNDED|test result|FAILED" "$LOGS/$C.svm.log"
cp verification/{svm_report,trace_budget,packets,cu_buy_attribution}.json "$LOGS/" 2>/dev/null || true
rustup override unset >/dev/null
[ "$status" -eq 0 ] || exit "$status"
python3 "$REPO/program/scripts/heap_probe.py" "$C" > "$LOGS/$C.probe.log" 2>&1
tail -n 30 "$LOGS/$C.probe.log" | grep -E '"(create_room|open_door|create_room_takeover_uri70|create_room_takeover_uri200|open_door_takeover)"'
