"""Read the quote mint of every bonding curve used in liveness_reads.json, so the tables can keep SOL-quoted
curves only. pump.fun curves can be quoted in other tokens (BondingCurve.quote_mint, idl/pump.json @ 639b87fb,
bytes 83..115 of the account); their reserves are not lamports. Default pubkey (all zeros) or the WSOL mint = SOL.
The quote mint is fixed at creation, so reading it now is valid for any past time.

Usage: python3 liveness_quote_mints.py <liveness_reads.json> <out.json>
"""
import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from collect_pump_launches import b58e, rpc  # noqa: E402
from liveness_reads import BC_DISC, bonding_curve  # noqa: E402


def main():
    d = json.load(open(sys.argv[1]))
    mints = {r["mint"] for a in d["part_a_copies"] for r in a["reads"]}
    mints |= {b["mint"] for b in d["part_b"]}
    mints |= {r["mint"] for v in d["part_c"].values() for r in v["rows"]}
    mints = sorted(mints)
    out, slots = {}, []
    for k in range(0, len(mints), 100):
        chunk = mints[k:k + 100]
        res = rpc("getMultipleAccounts", [[bonding_curve(m) for m in chunk], {"encoding": "base64"}])
        slots.append(res["context"]["slot"])
        for m, acc in zip(chunk, res["value"]):
            if not acc:
                out[m] = None
                continue
            raw = base64.b64decode(acc["data"][0])
            assert raw[:8] == BC_DISC
            out[m] = b58e(raw[83:115]) if len(raw) >= 115 else "11111111111111111111111111111111"
    json.dump({"context_slots": slots, "quote_mint": out}, open(sys.argv[2], "w"), indent=0)
    sol = sum(1 for v in out.values() if v in ("11111111111111111111111111111111",
                                                 "So11111111111111111111111111111111111111112"))
    print(json.dumps({"curves": len(out), "sol_quoted": sol, "slots": slots}))


if __name__ == "__main__":
    main()
