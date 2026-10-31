"""Count DAMM v2 Config accounts by type and whether pool creation is restricted to an authority."""
import json, urllib.request, base64, hashlib, collections
RPC="https://api.mainnet-beta.solana.com"
PROG="cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG"
ALPH="123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
def b58e(b):
    n=int.from_bytes(b,"big"); s=""
    while n: n,r=divmod(n,58); s=ALPH[r]+s
    return "1"*(len(b)-len(b.lstrip(b"\0")))+s
def rpc(m,p):
    req=urllib.request.Request(RPC,data=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode(),headers={"content-type":"application/json"})
    with urllib.request.urlopen(req,timeout=120) as r: o=json.load(r)
    if "error" in o: raise RuntimeError(o["error"])
    return o["result"]
disc=hashlib.sha256(b"account:Config").digest()[:8]
res=rpc("getProgramAccounts",[PROG,{"encoding":"base64","withContext":True,"dataSlice":{"offset":40,"length":163},
       "filters":[{"dataSize":328},{"memcmp":{"offset":0,"bytes":b58e(disc)}}]}])
c=collections.Counter(); examples=[]
for a in res["value"]:
    d=base64.b64decode(a["account"]["data"][0])
    auth=d[0:32]; ctype=d[162]
    restricted=auth!=bytes(32)
    c[(ctype,restricted)]+=1
    if ctype==1 and restricted and len(examples)<3: examples.append(dict(config=a["pubkey"],pool_creator_authority=b58e(auth)))
print(json.dumps(dict(slot=res["context"]["slot"], total=len(res["value"]),
      by_type_and_restricted={f"config_type={k[0]},restricted={k[1]}":v for k,v in sorted(c.items())},
      dynamic_restricted_examples=examples),indent=1))
