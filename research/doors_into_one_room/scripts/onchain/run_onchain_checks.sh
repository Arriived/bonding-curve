#!/usr/bin/env bash
set -euo pipefail
# Live mainnet RPC evidence for GRADUATION_TRANSFER_FEE.md. Not deterministic: results depend on recent
# transactions; each output records slots. BERN = CKfatsPMUf8SkiURsDXs7eK6GWb4Jsd6UDbs7twMCWxo
# (Token-2022 mint with a 269 bps TransferFee).
cd "$(dirname "$0")"
mkdir -p ../../outputs/onchain
MINT=CKfatsPMUf8SkiURsDXs7eK6GWb4Jsd6UDbs7twMCWxo
python3 program_mix.py "$MINT" 60 > ../../outputs/onchain/bern_program_mix.json
python3 jupiter_quote_check.py "$MINT" 100 > ../../outputs/onchain/bern_jupiter_quotes.json
echo "wrote outputs/onchain/bern_program_mix.json and bern_jupiter_quotes.json"
