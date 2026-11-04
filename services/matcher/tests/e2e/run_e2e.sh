#!/usr/bin/env bash
set -euo pipefail
# End-to-end test of the matcher service against the doors program.
# Target: the single line in tests/e2e/target (localnet | devnet). devnet exits 3 (PENDING) until deployed.
# Usage: tests/e2e/run_e2e.sh <keys_dir>
cd "$(dirname "$0")/../.."
python3 tests/e2e/e2e.py "$1"
