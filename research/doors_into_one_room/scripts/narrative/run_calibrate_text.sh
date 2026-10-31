#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p outputs/narrative
python3 scripts/narrative/calibrate_text.py outputs/narrative/pump_launches.jsonl scripts/narrative/labels_assistant.csv outputs/narrative
