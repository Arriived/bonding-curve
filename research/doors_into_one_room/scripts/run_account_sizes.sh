#!/usr/bin/env bash
set -euo pipefail
# Regenerates outputs/account_sizes.md from scripts/account_sizes.py (deterministic).
cd "$(dirname "$0")/.."
mkdir -p outputs
python3 scripts/account_sizes.py > outputs/account_sizes.md
echo "wrote $(pwd)/outputs/account_sizes.md"
