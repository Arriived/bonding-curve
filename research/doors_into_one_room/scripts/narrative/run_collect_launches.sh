#!/usr/bin/env bash
set -euo pipefail
# Collects real pump.fun launches (name, symbol, uri, mint, slot) from public mainnet RPC.
# Appends to outputs/narrative/pump_launches.jsonl and resumes where it stopped. Not deterministic: live chain data.
cd "$(dirname "$0")/../.."
mkdir -p outputs/narrative
python3 scripts/narrative/collect_pump_launches.py "${1:-5000}" outputs/narrative/pump_launches.jsonl
