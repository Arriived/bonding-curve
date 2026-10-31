#!/usr/bin/env bash
set -euo pipefail
# Regenerates outputs/curve_identities.md from scripts/curve_identities.py (exact arithmetic, deterministic).
cd "$(dirname "$0")/.."
mkdir -p outputs
python3 scripts/curve_identities.py > outputs/curve_identities.md
echo "wrote $(pwd)/outputs/curve_identities.md"
