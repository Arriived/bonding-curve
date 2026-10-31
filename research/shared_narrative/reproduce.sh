#!/usr/bin/env bash
# Reproduce the shared-narrative study from a clean checkout (about 45 min on 4 cores).
# Synthetic, off-chain research; see DESIGN.md and FINDINGS.md.
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=${OUT:-research/shared_narrative/outputs}
WORKERS=${WORKERS:-4}
python3 -m pip install -q numpy pandas pytest hypothesis
python3 -m pip install -q -e . --no-deps
# Existing engine/parity tests plus the new study's tests.
python3 -m pytest -q tests/test_engine.py tests/test_fast.py tests/shared_narrative \
  --junitxml="$OUT/tests.xml"
for stage in main shock sensitivity linear spam bundle wash; do
  python3 -m bonding_lab.shared_narrative "$stage" --out "$OUT" --workers "$WORKERS"
done
python3 -m bonding_lab.shared_narrative report --out "$OUT"
echo "Tables: $OUT/tables.md   Summary: $OUT/summary.json"
