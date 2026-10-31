"""On-chain reads for calibrating the pre-graduation liveness gate, from pump.fun bonding curves.

Proxy: a doors room's reserve is the SOL bought into the room through all its doors, and its last_trade_at is the
last trade through any door. On pump.fun each copy has its own curve, so for a copy launched at time t into
narrative cluster K, the room it would join is approximated by the members of K launched before t:
  room_reserve(t)   = sum over members of real_sol_reserves after each member's last trade before t
  room_last_trade(t) = latest trade on any member's curve before t
Bonding curve PDA: ["bonding-curve", mint] under 6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P.
Trade data: pump TradeEvent (idl/pump.json @ 639b87fb, discriminator [189,219,127,211,78,230,97,238]),
emitted by self-CPI; real_sol_reserves at byte 105 of the event body (after the discriminator; mint 32,
sol_amount 8, token_amount 8, is_buy 1, user 32, timestamp 8, virtual_sol 8, virtual_token 8).

Part B reads the current BondingCurve account of a random sample of launches (real_quote_reserves at offset 32,
complete at 48) and each curve's latest signature, with the context slot recorded.
Part C does the same for launches about 1 day and 7 days old. The slot offset comes from the measured seconds per
slot over the last 200,000 slots; getBlock at the offset slot gives a signature, and getSignaturesForAddress(mint authority,
before=that signature) lists the launches just before it.

Usage: python3 liveness_reads.py <launches.jsonl> <copies.json> <out.json> [n_copies] [n_population]
copies.json: [{"copy_sig", "copy_time", "members": [{"mint", "launch_time"}...]}] (from calibrate_text.py)
"""
import base64
import json
import os
import random
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from collect_pump_launches import MINT_AUTHORITY, PUMP, b58d, b58e, decode_create, find_pda, rpc  # noqa: E402

SEED = 20261031
TRADE_DISC = bytes([189, 219, 127, 211, 78, 230, 97, 238])
EVENT_IX_TAG = bytes.fromhex("e445a52e51cb9a1d")  # Anchor EVENT_IX_TAG_LE (self-CPI event prefix)
BC_DISC = bytes([23, 183, 248, 55, 96, 216, 172, 96])


def bonding_curve(mint):
    return find_pda([b"bonding-curve", b58d(mint).rjust(32, b"\0")], PUMP)


def trade_reserves(tx, mint):
    """real_sol_reserves after the last TradeEvent for `mint` in the transaction, or None."""
    out = None
    for inner in tx["meta"].get("innerInstructions") or []:
        for ix in inner["instructions"]:
            d = b58d(ix["data"])
            if d[:8] == EVENT_IX_TAG and d[8:16] == TRADE_DISC:
                body = d[16:]
                if b58e(body[:32]) == mint:
                    out = struct.unpack_from("<Q", body, 105)[0]
    return out


def last_trade_before(mint, before_sig):
    sigs = rpc("getSignaturesForAddress", [bonding_curve(mint), {"limit": 5, "before": before_sig}])
    for s in sigs:
        if s.get("err"):
            continue
        tx = rpc("getTransaction", [s["signature"], {"maxSupportedTransactionVersion": 1, "encoding": "json"}])
        time.sleep(0.1)
        if not tx:
            continue
        r = trade_reserves(tx, mint)
        return {"sig": s["signature"], "slot": s["slot"], "time": s.get("blockTime"),
                "real_sol_reserves": r if r is not None else 0, "is_trade": r is not None}
    return None


def main():
    launches_path, copies_path, out = sys.argv[1:4]
    n_copies = int(sys.argv[4]) if len(sys.argv) > 4 else 150
    n_pop = int(sys.argv[5]) if len(sys.argv) > 5 else 300
    rng = random.Random(SEED)
    copies = json.load(open(copies_path))
    sample = rng.sample(copies, min(n_copies, len(copies)))
    part_a = []
    for i, c in enumerate(sample):
        members = sorted(c["members"], key=lambda m: -m["launch_time"])[:8]  # the 8 most recent earlier members
        reads = []
        for m in members:
            r = last_trade_before(m["mint"], c["copy_sig"])
            reads.append({"mint": m["mint"], **(r or {"sig": None, "time": None, "real_sol_reserves": 0})})
        times = [r["time"] for r in reads if r.get("time")]
        part_a.append({"copy_sig": c["copy_sig"], "copy_time": c["copy_time"], "members_total": len(c["members"]),
                       "members_read": len(reads), "room_reserve": sum(r["real_sol_reserves"] for r in reads),
                       "room_idle": (c["copy_time"] - max(times)) if times else None, "reads": reads})
        if (i + 1) % 10 == 0:
            print(f"part A {i + 1}/{len(sample)}", file=sys.stderr, flush=True)

    launches = [json.loads(l) for l in open(launches_path)]
    pop = rng.sample(launches, min(n_pop, len(launches)))
    part_b, ctx_slots = [], []
    for k in range(0, len(pop), 100):
        chunk = pop[k:k + 100]
        res = rpc("getMultipleAccounts", [[bonding_curve(r["mint"]) for r in chunk], {"encoding": "base64"}])
        ctx_slots.append(res["context"]["slot"])
        for r, acc in zip(chunk, res["value"]):
            row = {"mint": r["mint"], "launch_time": r["block_time"], "exists": acc is not None}
            if acc:
                d = base64.b64decode(acc["data"][0])
                assert d[:8] == BC_DISC
                row["real_quote_reserves"] = struct.unpack_from("<Q", d, 32)[0]
                row["complete"] = bool(d[48])
                row["quote_mint"] = b58e(d[83:115]) if len(d) >= 115 else None
            part_b.append(row)
    part_c = {}
    tip = rpc("getSlot", [{"commitment": "finalized"}])
    def block_time_near(slot):
        for k in range(20):
            try:
                blk = rpc("getBlock", [slot + k, {"transactionDetails": "signatures", "rewards": False,
                                                  "maxSupportedTransactionVersion": 1}])
            except RuntimeError:
                continue  # skipped slot
            if blk and blk.get("signatures"):
                return slot + k, blk["blockTime"]
        raise RuntimeError("no block found")

    s_tip, t_tip = block_time_near(tip - 100)
    s_p, t_p = block_time_near(tip - 200_000)
    sec_per_slot = (t_tip - t_p) / (s_tip - s_p)  # measured, not nominal
    for label, secs in (("1d", 86_400), ("7d", 604_800)):
        slot = tip - int(secs / sec_per_slot)
        sig0 = None
        for k in range(20):
            try:
                blk = rpc("getBlock", [slot + k, {"transactionDetails": "signatures", "rewards": False,
                                                  "maxSupportedTransactionVersion": 1}])
            except RuntimeError:
                continue  # skipped slot
            if blk and blk.get("signatures"):
                sig0 = blk["signatures"][0]
                break
        sigs = rpc("getSignaturesForAddress", [MINT_AUTHORITY, {"limit": 150, "before": sig0}])
        rows = []
        for sg in sigs:
            if sg.get("err") or len(rows) >= n_pop // 3:
                continue
            tx = rpc("getTransaction", [sg["signature"], {"maxSupportedTransactionVersion": 1, "encoding": "json"}])
            time.sleep(0.1)
            r = decode_create(tx, sg["signature"], sg["slot"], sg.get("blockTime")) if tx else None
            if r:
                rows.append(r)
        res_rows = []
        for k in range(0, len(rows), 100):
            chunk = rows[k:k + 100]
            res = rpc("getMultipleAccounts", [[bonding_curve(r["mint"]) for r in chunk], {"encoding": "base64"}])
            ctx_slots.append(res["context"]["slot"])
            for r, acc in zip(chunk, res["value"]):
                row = {"mint": r["mint"], "launch_time": r["block_time"], "launch_slot": r["slot"],
                       "exists": acc is not None}
                if acc:
                    d = base64.b64decode(acc["data"][0])
                    row["real_quote_reserves"] = struct.unpack_from("<Q", d, 32)[0]
                    row["complete"] = bool(d[48])
                res_rows.append(row)
        part_c[label] = {"anchor_slot": slot, "anchor_sig": sig0, "rows": res_rows}
    now_wall = int(time.time())
    for row in part_b + [r for v in part_c.values() for r in v["rows"]]:
        sigs = rpc("getSignaturesForAddress", [bonding_curve(row["mint"]), {"limit": 1}])
        time.sleep(0.1)
        row["last_sig_time"] = sigs[0].get("blockTime") if sigs else None
        row["last_sig_slot"] = sigs[0]["slot"] if sigs else None
    json.dump({"program": PUMP, "seed": SEED, "part_a_copies": part_a,
               "part_b_context_slots": ctx_slots, "part_b_read_unix": now_wall, "part_b": part_b,
               "part_c": part_c, "tip_slot": tip, "sec_per_slot_measured": sec_per_slot},
              open(out, "w"), indent=1)
    print(json.dumps({"part_a": len(part_a), "part_b": len(part_b), "slots": ctx_slots}))


if __name__ == "__main__":
    main()
