#!/usr/bin/env bash
set -euo pipefail
# Fetches the Twemoji corpus from the npm registry into a fresh temp dir (npm verifies the registry's sha512),
# checks the reference implementation agrees with ours, then measures robustness and false-match rates.
cd "$(dirname "$0")/../.."
mkdir -p outputs/narrative
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
(cd "$work" && npm pack emoji-datasource-twitter@15.1.2 --silent >/dev/null)
sha256sum "$work"/emoji-datasource-twitter-15.1.2.tgz
mkdir "$work/pkg"
tar xzf "$work"/emoji-datasource-twitter-15.1.2.tgz -C "$work/pkg"
python3 -I scripts/narrative/phash_reference_check.py "$work/pkg/package" outputs/narrative/phash_reference_check.txt
python3 -I scripts/narrative/image_robustness.py "$work/pkg/package" outputs/narrative/image_robustness.md "${1:-400}"
