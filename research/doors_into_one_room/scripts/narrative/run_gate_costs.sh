#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p outputs/narrative
python3 scripts/narrative/gate_costs.py > outputs/narrative/gate_costs.md
cat outputs/narrative/gate_costs.md
