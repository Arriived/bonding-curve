#!/usr/bin/env bash
set -euo pipefail
# Reads the deployed Meteora DAMM v2 program and its Config accounts from mainnet RPC; records slots.
cd "$(dirname "$0")"
mkdir -p ../../outputs/onchain
python3 damm_v2_program.py > ../../outputs/onchain/damm_v2_program.json
python3 damm_v2_configs.py > ../../outputs/onchain/damm_v2_configs.json
echo "wrote outputs/onchain/damm_v2_program.json and damm_v2_configs.json"
