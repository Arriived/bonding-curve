#!/usr/bin/env bash
set -euo pipefail
# Reads pump.fun FeeConfig accounts (pump fees program) from mainnet RPC; records the slot.
cd "$(dirname "$0")"
mkdir -p ../../outputs/onchain
python3 pump_fee_config.py > ../../outputs/onchain/pump_fee_config.json
echo "wrote outputs/onchain/pump_fee_config.json"
