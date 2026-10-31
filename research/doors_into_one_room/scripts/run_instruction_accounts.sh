#!/usr/bin/env bash
set -euo pipefail
# Regenerates outputs/instruction_accounts.md from scripts/instruction_accounts.py (deterministic).
cd "$(dirname "$0")/.."
mkdir -p outputs
python3 scripts/instruction_accounts.py > outputs/instruction_accounts.md
echo "wrote $(pwd)/outputs/instruction_accounts.md"
