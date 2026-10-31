"""Decode Jupiter v6 exact-in routes touching a mint; compare quoted_out with what the signer received.

Usage: python3 jupiter_quote_check.py <mint> <n_signatures>. Reads live mainnet RPC.
"""
import json, sys, time, urllib.request, struct, hashlib
RPC = "https://api.mainnet-beta.solana.com"
JUP = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"
ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
def b58d(s):
    n = 0
    for c in s: n = n*58 + ALPH.index(c)
    b = n.to_bytes((n.bit_length()+7)//8, "big") if n else b""
    return b"\0"*(len(s)-len(s.lstrip("1"))) + b
def disc(name): return hashlib.sha256(f"global:{name}".encode()).digest()[:8]
# Only these layouts are decoded; their trailing args are in_amount u64, quoted_out u64, slippage_bps u16,
# platform_fee_bps u8. route_v2 variants have a different layout and are reported undecoded, not guessed.
EXACT_IN = {disc(n): n for n in ("route", "shared_accounts_route")}
def rpc(method, params):
    req = urllib.request.Request(RPC, data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
                                 headers={"content-type":"application/json"})
    for a in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as r: out = json.load(r)
            if "error" in out: raise RuntimeError(out["error"])
            return out["result"]
        except Exception:
            if a == 4: raise
            time.sleep(2*(a+1))
mint, n = sys.argv[1], int(sys.argv[2])
rows = []
for s in rpc("getSignaturesForAddress", [mint, {"limit": n}]):
    if s.get("err"): continue
    tx = rpc("getTransaction", [s["signature"], {"maxSupportedTransactionVersion": 1, "encoding": "json"}]); time.sleep(0.25)
    if not tx: continue
    keys = list(tx["transaction"]["message"]["accountKeys"])
    la = tx["meta"].get("loadedAddresses") or {}; keys += la.get("writable", []) + la.get("readonly", [])
    for ix in tx["transaction"]["message"]["instructions"]:
        if keys[ix["programIdIndex"]] != JUP: continue
        d = b58d(ix["data"])
        name = EXACT_IN.get(d[:8])
        if not name:
            rows.append(dict(sig=s["signature"], kind="jupiter ix not decoded (exact-out or other)", disc=d[:8].hex())); continue
        # trailing args for exact-in routes: in_amount u64, quoted_out_amount u64, slippage_bps u16, platform_fee_bps u8
        tail = d[-19:]
        in_amt, quoted_out, slip, pfee = struct.unpack("<QQHB", tail)
        signer = keys[0]
        pre = {b["accountIndex"]: b for b in tx["meta"]["preTokenBalances"]}
        post = {b["accountIndex"]: b for b in tx["meta"]["postTokenBalances"]}
        recv = {}
        for i, b in post.items():
            if b.get("owner") != signer: continue
            before = int(pre[i]["uiTokenAmount"]["amount"]) if i in pre else 0
            delta = int(b["uiTokenAmount"]["amount"]) - before
            if delta > 0: recv[b["mint"]] = recv.get(b["mint"], 0) + delta
        sent = {}
        for i, b in pre.items():
            if b.get("owner") != signer: continue
            after = int(post[i]["uiTokenAmount"]["amount"]) if i in post else 0
            dlt = int(b["uiTokenAmount"]["amount"]) - after
            if dlt > 0: sent[b["mint"]] = sent.get(b["mint"], 0) + dlt
        credited_fee_mint = sum(int(post[i]["uiTokenAmount"]["amount"]) - (int(pre[i]["uiTokenAmount"]["amount"]) if i in pre else 0)
                                for i, b in post.items() if b["mint"] == mint and b.get("owner") != signer
                                and int(b["uiTokenAmount"]["amount"]) > (int(pre[i]["uiTokenAmount"]["amount"]) if i in pre else 0))
        rows.append(dict(sig=s["signature"], slot=tx["slot"], ix=name, sent=sent, fee_mint_credited_to_others=credited_fee_mint, in_amount=in_amt, quoted_out=quoted_out, slippage_bps=slip,
                         platform_fee_bps=pfee, received=recv,
                         received_vs_quote=(round(recv[mint]/quoted_out-1, 6) if mint in recv and quoted_out else None),
                         output_is_fee_mint=mint in recv))
print(json.dumps(rows, indent=1))
