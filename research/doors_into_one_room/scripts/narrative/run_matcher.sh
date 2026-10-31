#!/usr/bin/env bash
set -euo pipefail
# Route one candidate launch against a set of rooms. Default input: the worked examples.
# Usage: run_matcher.sh [input.json]   (format: header of scripts/narrative/matcher.py)
cd "$(dirname "$0")/../.."
if [ "$#" -gt 0 ]; then
  python3 scripts/narrative/matcher.py "$1"
else
  python3 scripts/narrative/run_examples.py scripts/narrative/examples
fi
