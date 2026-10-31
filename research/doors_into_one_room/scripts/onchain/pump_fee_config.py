"""Read pump.fun FeeConfig accounts from the pump fees program (pfeeUxB6...VZ) on mainnet.

FeeConfig PDA = ["fee_config", <program id>] under the fees program (pump_fees.json IDL,
pump-fun/pump-public-docs @ 639b87fb). Derived addresses:
  bonding curve 6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P -> 8Wf5TiAheLUqBrKXeYg2JtAFFMWtKdG2BSFgqUcPVwTt
  PumpSwap      pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA -> 5PHirr8joyTMp9JMm6nW7hNDVyEYdkzDqazxPD7RaTjx
"""
import json, urllib.request, base64, struct, sys
RPC="https://api.mainnet-beta.solana.com"
ALPH="123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
def b58e(b):
    n=int.from_bytes(b,"big"); s=""
    while n: n,r=divmod(n,58); s=ALPH[r]+s
    return "1"*(len(b)-len(b.lstrip(b"\0")))+s
def rpc(m,p):
    req=urllib.request.Request(RPC,data=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode(),headers={"content-type":"application/json"})
    with urllib.request.urlopen(req,timeout=60) as r: o=json.load(r)
    if "error" in o: raise RuntimeError(o["error"])
    return o["result"]
PROG="pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
disc=bytes([143,52,146,187,219,123,76,155])
res=rpc("getProgramAccounts",[PROG,{"encoding":"base64","withContext":True,"filters":[{"memcmp":{"offset":0,"bytes":b58e(disc)}}]}])
slot=res["context"]["slot"]
def fees(d,o): return struct.unpack_from("<QQQ",d,o), o+24
LABEL={"8Wf5TiAheLUqBrKXeYg2JtAFFMWtKdG2BSFgqUcPVwTt":"pump bonding curve","5PHirr8joyTMp9JMm6nW7hNDVyEYdkzDqazxPD7RaTjx":"PumpSwap canonical pools"}
allout=[]
for acc in res["value"]:
    d=base64.b64decode(acc["account"]["data"][0]); o=8
    bump=d[o]; o+=1; admin=b58e(d[o:o+32]); o+=32
    flat,o=fees(d,o)
    out=dict(pubkey=acc["pubkey"],program=LABEL.get(acc["pubkey"],"unknown"),slot=slot,flat_fees_lp_protocol_creator_bps=flat,tiers=[],stable_tiers=[])
    for key in ("tiers","stable_tiers"):
        n=struct.unpack_from("<I",d,o)[0]; o+=4
        for _ in range(n):
            lo,hi=struct.unpack_from("<QQ",d,o); o+=16
            f,o=fees(d,o)
            out[key].append(dict(mcap_threshold_sol=(lo+(hi<<64))/1e9, lp_bps=f[0], protocol_bps=f[1], creator_bps=f[2]))
    allout.append(out)
print(json.dumps(allout,indent=1))
