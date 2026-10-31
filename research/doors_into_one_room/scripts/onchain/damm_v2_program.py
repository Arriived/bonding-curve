"""Confirm the deployed Meteora DAMM v2 program contains the instructions the spec uses."""
import json, urllib.request, base64, hashlib, struct
RPC="https://api.mainnet-beta.solana.com"
PROG="cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG"
def rpc(m,p):
    req=urllib.request.Request(RPC,data=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode(),headers={"content-type":"application/json"})
    with urllib.request.urlopen(req,timeout=120) as r: o=json.load(r)
    if "error" in o: raise RuntimeError(o["error"])
    return o["result"]
info=rpc("getAccountInfo",[PROG,{"encoding":"jsonParsed"}])
pd=info["value"]["data"]["parsed"]["info"]["programData"]
r=rpc("getAccountInfo",[pd,{"encoding":"base64"}])
d=base64.b64decode(r["value"]["data"][0])
deploy_slot=struct.unpack("<Q",d[4:12])[0]
elf=d[45:].rstrip(b"\0")
out=dict(program=PROG, programdata=pd, read_at_slot=r["context"]["slot"], last_deploy_slot=deploy_slot,
         upgrade_authority_present=bool(d[12]), elf_sha256=hashlib.sha256(elf).hexdigest(), checks={})
for name in ["initialize_pool_with_dynamic_config","initialize_customizable_pool","permanent_lock_position",
             "claim_position_fee","create_position","swap","swap2","add_liquidity"]:
    disc=hashlib.sha256(f"global:{name}".encode()).digest()[:8]
    camel="".join(w.capitalize() for w in name.split("_"))
    out["checks"][name]=dict(anchor_discriminator=disc.hex(), discriminator_in_elf=disc in elf,
                             log_string_in_elf=f"Instruction: {camel}".encode() in elf)
# Cross-check account sizes against a live DAMM v2 pool (BERN/USELESS pair, found via DexScreener API).
POOL="AeaMYByFeRW6qkAMyiujgU2RY6qMSLtGN8kx4PbemBke"
pr=rpc("getAccountInfo",[POOL,{"encoding":"base64","dataSlice":{"offset":0,"length":0}}])
out["live_pool_check"]=dict(pool=POOL, owner=pr["value"]["owner"], space=pr["value"]["space"],
                            expected_space=8+1104, slot=pr["context"]["slot"])
out["note"]=("Discriminator bytes are not reliably present as raw bytes in compiled BPF; the Anchor "
             "'Instruction: <Name>' log strings are the evidence used.")
print(json.dumps(out,indent=1))
