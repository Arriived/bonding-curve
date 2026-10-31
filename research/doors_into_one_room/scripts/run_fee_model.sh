#!/usr/bin/env bash
set -euo pipefail
# Regenerates outputs/fee_model.md from scripts/fee_model.py (deterministic).
cd "$(dirname "$0")/.."
mkdir -p outputs
python3 scripts/fee_model.py > outputs/fee_model.md
echo "wrote $(pwd)/outputs/fee_model.md"
