#!/usr/bin/env bash
set -euo pipefail
# Regenerates outputs/curve_tables.md from scripts/curve_model.py (deterministic).
cd "$(dirname "$0")/.."
mkdir -p outputs
python3 scripts/curve_model.py > outputs/curve_tables.md
echo "wrote $(pwd)/outputs/curve_tables.md"
