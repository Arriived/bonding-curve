#!/usr/bin/env bash
set -euo pipefail
# Requires real-image caches from fetch_token_images.py and requirements_images.txt.
cd "$(dirname "$0")/../.."
mkdir -p outputs/narrative
python3 scripts/narrative/phash_reference_check.py --real outputs/narrative/real_phash_reference_check.txt
python3 scripts/narrative/real_image_robustness.py "${1:-400}"
