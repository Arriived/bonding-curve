#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p outputs/narrative
python3 scripts/narrative/damm_pool_fields.py outputs/narrative/damm_pool_fields.json "${1:-600}"
