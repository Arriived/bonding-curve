#!/usr/bin/env bash
set -euo pipefail
# Regenerates outputs/door_creator_model.md from scripts/door_creator_model.py (deterministic).
cd "$(dirname "$0")/.."
mkdir -p outputs
python3 scripts/door_creator_model.py > outputs/door_creator_model.md
echo "wrote $(pwd)/outputs/door_creator_model.md"
