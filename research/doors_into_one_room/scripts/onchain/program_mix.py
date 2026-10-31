"""Count which DEX/aggregator programs recent successful transactions of a mint invoke.

Usage: python3 program_mix.py <mint> <n_signatures>. Reads live mainnet RPC.
"""
import json, sys, time, urllib.request, collections
RPC = "https://api.mainnet-beta.solana.com"
NAMES = {
 "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": "Jupiter v6",
 "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C": "Raydium CPMM",
 "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK": "Raydium CLMM",
 "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "Raydium AMM v4",
 "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": "Orca Whirlpools",
 "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo": "Meteora DLMM",
 "cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG": "Meteora DAMM v2",
 "Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB": "Meteora DAMM v1",
 "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA": "PumpSwap",
 "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P": "pump.fun bonding curve",
}
def rpc(method, params):
    req = urllib.request.Request(RPC, data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
                                 headers={"content-type":"application/json"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                out = json.load(r)
            if "error" in out:
                raise RuntimeError(out["error"])
            return out["result"]
        except Exception as e:
            if attempt == 4: raise
            time.sleep(2*(attempt+1))
mint, n = sys.argv[1], int(sys.argv[2])
sigs = rpc("getSignaturesForAddress", [mint, {"limit": n}])
counts = collections.Counter(); seen = 0; first = last = None
for s in sigs:
    if s.get("err"): continue
    tx = rpc("getTransaction", [s["signature"], {"maxSupportedTransactionVersion": 1, "encoding": "json"}])
    time.sleep(0.25)
    if not tx: continue
    keys = list(tx["transaction"]["message"]["accountKeys"])
    la = tx["meta"].get("loadedAddresses") or {}
    keys += la.get("writable", []) + la.get("readonly", [])
    progs = set()
    for ix in tx["transaction"]["message"]["instructions"]:
        progs.add(keys[ix["programIdIndex"]])
    for inner in (tx["meta"].get("innerInstructions") or []):
        for ix in inner["instructions"]:
            if ix["programIdIndex"] < len(keys): progs.add(keys[ix["programIdIndex"]])
    seen += 1
    first = first or s["slot"]; last = s["slot"]
    for p in progs:
        if p in NAMES: counts[NAMES[p]] += 1
print(json.dumps(dict(mint=mint, sampled_successful=seen, newest_slot=first, oldest_slot=last,
                      txs_invoking=dict(counts.most_common())), indent=1))
