"""Collect real pump.fun launch metadata (name, symbol, uri) from public mainnet RPC.

Method: every pump.fun launch (`create` or `create_v2`, pump-fun/pump-public-docs idl/pump.json @ 639b87fb)
passes the program's mint-authority PDA (seeds ["mint-authority"] under 6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P)
as account 1. getSignaturesForAddress on that PDA therefore lists launches. Each transaction is fetched and the
create instruction's Borsh args are decoded (name, symbol, uri: u32-length strings; creator: pubkey).

Usage: python3 collect_pump_launches.py <target_launches> <out.jsonl>
Appends; resumes from the oldest signature already in the file. Public RPC is rate-limited: the script sleeps and
backs off on HTTP 429.
"""
import base64
import http.client
import hashlib
import json
import os
import struct
import sys
import time
import urllib.error
import urllib.request

RPC = "https://api.mainnet-beta.solana.com"
PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
DISC = {bytes([24, 30, 200, 40, 5, 28, 7, 119]): "create", bytes([214, 144, 76, 236, 95, 139, 49, 180]): "create_v2"}
ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58d(s):
    n = 0
    for c in s:
        n = n*58+ALPH.index(c)
    b = n.to_bytes((n.bit_length()+7)//8, "big") if n else b""
    return b"\0"*(len(s)-len(s.lstrip("1")))+b


def b58e(b):
    n = int.from_bytes(b, "big")
    s = ""
    while n:
        n, r = divmod(n, 58)
        s = ALPH[r]+s
    return "1"*(len(b)-len(b.lstrip(b"\0")))+s


P_ED = 2**255-19
D_ED = (-121665*pow(121666, P_ED-2, P_ED)) % P_ED


def on_curve(b):
    y = int.from_bytes(b, "little") & ((1 << 255)-1)
    if y >= P_ED:
        return False
    u, v = (y*y-1) % P_ED, (D_ED*y*y+1) % P_ED
    x2 = u*pow(v, P_ED-2, P_ED) % P_ED
    return x2 == 0 or pow(x2, (P_ED-1)//2, P_ED) == 1


def find_pda(seeds, program):
    prog = b58d(program).rjust(32, b"\0")
    for bump in range(255, -1, -1):
        h = hashlib.sha256(b"".join(seeds)+bytes([bump])+prog+b"ProgramDerivedAddress").digest()
        if not on_curve(h):
            return b58e(h)
    raise RuntimeError("no PDA")


MINT_AUTHORITY = find_pda([b"mint-authority"], PUMP)


RETRYABLE = (429, -32429, -32019, -32005, -32004)  # rate limit, long-term storage, node behind, block not available
_CACHE_PATH = os.environ.get("RPC_CACHE")  # optional: memoise immutable history reads across reruns
_cache = None


def _cache_get(key):
    global _cache
    if not _CACHE_PATH:
        return None
    if _cache is None:
        _cache = {}
        if os.path.exists(_CACHE_PATH):
            for line in open(_CACHE_PATH):
                k, v = json.loads(line)
                _cache[k] = v
    return _cache.get(key)


def _cache_put(key, value):
    if _CACHE_PATH:
        _cache[key] = value
        with open(_CACHE_PATH, "a") as f:
            f.write(json.dumps([key, value]) + "\n")


def rpc(method, params):
    immutable = method == "getTransaction" or (method == "getSignaturesForAddress" and "before" in params[1])
    key = json.dumps([method, params], sort_keys=True) if immutable else None
    if key:
        hit = _cache_get(key)
        if hit is not None:
            return hit
    out = _rpc(method, params)
    if key and out is not None:
        _cache_put(key, out)
    return out


def _rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    delay = 1.0
    for attempt in range(8):
        try:
            req = urllib.request.Request(RPC, data=body, headers={"content-type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                out = json.load(r)
            if "error" in out:
                if out["error"].get("code") in RETRYABLE:
                    raise urllib.error.HTTPError(RPC, 429, "rate", None, None)
                raise RuntimeError(out["error"])
            return out["result"]
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 7:
                time.sleep(delay)
                delay = min(delay*2, 30)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException):
            if attempt < 7:
                time.sleep(delay)
                delay = min(delay*2, 30)
                continue
            raise


def borsh_str(d, o):
    n = struct.unpack_from("<I", d, o)[0]
    return d[o+4:o+4+n].decode("utf-8", "replace"), o+4+n


def decode_create(tx, sig, slot, block_time):
    keys = list(tx["transaction"]["message"]["accountKeys"])
    la = tx["meta"].get("loadedAddresses") or {}
    keys += la.get("writable", [])+la.get("readonly", [])
    ixs = [(ix["programIdIndex"], ix["accounts"], ix["data"]) for ix in tx["transaction"]["message"]["instructions"]]
    for inner in tx["meta"].get("innerInstructions") or []:
        ixs += [(ix["programIdIndex"], ix["accounts"], ix["data"]) for ix in inner["instructions"]]
    for pidx, accts, data in ixs:
        if keys[pidx] != PUMP:
            continue
        d = b58d(data)
        kind = DISC.get(d[:8])
        if not kind:
            continue
        name, o = borsh_str(d, 8)
        symbol, o = borsh_str(d, o)
        uri, o = borsh_str(d, o)
        creator = b58e(d[o:o+32]) if len(d) >= o+32 else None
        return dict(signature=sig, slot=slot, block_time=block_time, ix=kind, mint=keys[accts[0]],
                    name=name, symbol=symbol, uri=uri, creator=creator)
    return None


def main():
    target, out = int(sys.argv[1]), sys.argv[2]
    seen, before = set(), None
    if os.path.exists(out):
        rows = [json.loads(l) for l in open(out)]
        seen = {r["signature"] for r in rows}
        if rows:
            before = min(rows, key=lambda r: r["slot"])["signature"]
    have = len(seen)
    with open(out, "a") as f:
        while have < target:
            params = {"limit": 1000}
            if before:
                params["before"] = before
            sigs = rpc("getSignaturesForAddress", [MINT_AUTHORITY, params])
            if not sigs:
                break
            for s in sigs:
                before = s["signature"]
                if s.get("err") or s["signature"] in seen:
                    continue
                tx = rpc("getTransaction", [s["signature"], {"maxSupportedTransactionVersion": 1, "encoding": "json"}])
                time.sleep(0.12)
                if not tx:
                    continue
                row = decode_create(tx, s["signature"], s["slot"], s.get("blockTime"))
                if row:
                    f.write(json.dumps(row)+"\n")
                    f.flush()
                    seen.add(s["signature"])
                    have += 1
                    if have % 100 == 0:
                        print(f"{have} launches, slot {s['slot']}", file=sys.stderr, flush=True)
                if have >= target:
                    break
    print(json.dumps(dict(mint_authority=MINT_AUTHORITY, launches=have, out=out)))


if __name__ == "__main__":
    main()
