#!/usr/bin/env bash
set -euo pipefail
# Regenerates outputs/transfer_fee_model.md from scripts/transfer_fee_model.py (deterministic).
cd "$(dirname "$0")/.."
mkdir -p outputs
python3 scripts/transfer_fee_model.py > outputs/transfer_fee_model.md
echo "wrote $(pwd)/outputs/transfer_fee_model.md"
