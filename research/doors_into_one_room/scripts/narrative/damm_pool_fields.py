"""Read live DAMM v2 Pool accounts and decode the fields the post-graduation liveness gate uses.

Layout: MeteoraAg/damm-v2 @ 5398b5c7c534de014091132da37c6478cce671a8, programs/cp-amm/src/state/pool.rs
(Pool L110-183, PoolMetrics L189-197; Pool::INIT_SPACE = 1104, so the account is 8 + 1104 = 1112 bytes).
Offsets below include the 8-byte Anchor discriminator and are derived field by field in OFFSETS.

Method: take recent transactions of the DAMM v2 program, collect their accounts, keep those owned by the program
with 1112 bytes of data, decode. Read twice, WAIT seconds apart, to show which fields move with trading.

Usage: python3 damm_pool_fields.py <out.json> [wait_seconds]
"""
import base64
import json
import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from collect_pump_launches import b58e, rpc  # noqa: E402

DAMM = "cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG"
WSOL = "So11111111111111111111111111111111111111112"
# (name, offset, format); offsets: disc 8 + pool_fees 160 = 168 for token_a_mint, etc.
OFFSETS = [
    ("token_a_mint", 168, "pk"), ("token_b_mint", 200, "pk"),
    ("liquidity", 360, "u128"), ("protocol_b_fee", 400, "u64"),
    ("sqrt_price", 456, "u128"), ("pool_status", 481, "u8"), ("collect_fee_mode", 484, "u8"),
    ("permanent_lock_liquidity", 552, "u128"),
    ("metrics.total_lp_a_fee", 568, "u128"), ("metrics.total_lp_b_fee", 584, "u128"),
    ("metrics.total_protocol_b_fee", 608, "u64"),
    ("token_a_amount", 680, "u64"), ("token_b_amount", 688, "u64"), ("layout_version", 696, "u8"),
]


def decode(d):
    out = {}
    for name, off, fmt in OFFSETS:
        if fmt == "pk":
            out[name] = b58e(d[off:off + 32])
        elif fmt == "u128":
            lo, hi = struct.unpack_from("<QQ", d, off)
            out[name] = lo + (hi << 64)
        elif fmt == "u64":
            out[name] = struct.unpack_from("<Q", d, off)[0]
        else:
            out[name] = d[off]
    return out


def read(keys):
    res = rpc("getMultipleAccounts", [keys, {"encoding": "base64"}])
    rows = {}
    for k, acc in zip(keys, res["value"]):
        if acc and acc["owner"] == DAMM:
            d = base64.b64decode(acc["data"][0])
            if len(d) == 1112:
                rows[k] = decode(d)
    return res["context"]["slot"], rows


def main():
    out = sys.argv[1]
    wait = int(sys.argv[2]) if len(sys.argv) > 2 else 600
    sigs = rpc("getSignaturesForAddress", [DAMM, {"limit": 60}])
    keys = set()
    for s in sigs:
        if s.get("err"):
            continue
        tx = rpc("getTransaction", [s["signature"], {"maxSupportedTransactionVersion": 1, "encoding": "json"}])
        time.sleep(0.1)
        if tx:
            keys.update(tx["transaction"]["message"]["accountKeys"])
            la = tx["meta"].get("loadedAddresses") or {}
            keys.update(la.get("writable", []))
    keys = sorted(keys)
    pools = []
    slot1 = None
    for k in range(0, len(keys), 100):
        s, rows = read(keys[k:k + 100])
        slot1 = s
        pools += list(rows)
    s1, r1 = read(pools)
    t1 = int(time.time())
    time.sleep(wait)
    s2, r2 = read(pools)
    t2 = int(time.time())
    moved = {}
    for name, _, fmt in OFFSETS:
        if fmt != "pk":
            moved[name] = sum(1 for p in pools if r1[p][name] != r2[p][name])
    wsol_b = [p for p in pools if r1[p]["token_b_mint"] == WSOL]
    summary = {"program": DAMM, "source": "MeteoraAg/damm-v2@5398b5c7c534de014091132da37c6478cce671a8",
               "pools": len(pools), "pools_with_wsol_as_token_b": len(wsol_b),
               "read1": {"slot": s1, "unix": t1}, "read2": {"slot": s2, "unix": t2},
               "fields_changed_between_reads (pool count)": moved,
               "collect_fee_mode_counts": {m: sum(1 for p in pools if r1[p]["collect_fee_mode"] == m) for m in range(3)},
               "layout_version_counts": {v: sum(1 for p in pools if r1[p]["layout_version"] == v) for v in range(2)},
               "pools_detail": [{"pool": p, "read1": r1[p], "read2": r2[p]} for p in pools]}
    json.dump(summary, open(out, "w"), indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k != "pools_detail"}, indent=1))


if __name__ == "__main__":
    main()
