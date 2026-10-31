#!/usr/bin/env bash
set -euo pipefail
# Needs outputs/narrative/copies.json from run_calibrate_text.sh.
cd "$(dirname "$0")/../.."
RPC_CACHE="${RPC_CACHE:-$(mktemp -d)/rpc_cache.jsonl}" python3 scripts/narrative/liveness_reads.py outputs/narrative/pump_launches.jsonl outputs/narrative/copies.json outputs/narrative/liveness_reads.json "${1:-100}" "${2:-300}"
python3 scripts/narrative/liveness_table.py outputs/narrative/liveness_reads.json outputs/narrative/liveness_table.md
