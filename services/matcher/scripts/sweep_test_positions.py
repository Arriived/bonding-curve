"""Sell every door and room token a test wallet holds back to its curve, then send the wallet's SOL above a
reserve to a destination. Keeps a test cluster's balance usable as upgrade budget (program/docs/DEPLOYMENT.md).

Sells always work, in any room state and while paused (spec section 3, finding M-5). Each sell sets its
min_lamports_out to 0: these are test positions being unwound on a test cluster, not trades to protect.
Never point this at a wallet with real holdings.

Usage: python3 scripts/sweep_test_positions.py <rpc_url> <wallet_keypair.json> <destination_pubkey> <keep_lamports>
Prints one line per sell (mint, tokens, signature, slot, lamports received) and the final transfer.
"""
import base64
import json
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from solders.hash import Hash  # noqa: E402
from solders.keypair import Keypair  # noqa: E402
from solders.message import Message  # noqa: E402
from solders.pubkey import Pubkey  # noqa: E402
from solders.system_program import TransferParams, transfer  # noqa: E402
from solders.transaction import Transaction  # noqa: E402

from matcher_service import layouts  # noqa: E402
from matcher_service.chain import RpcClient  # noqa: E402
from matcher_service.txbuild import T22, Builder, ata, load_idl  # noqa: E402

PROGRAM = load_idl()["address"]


def send(rpc, signer, ixs):
    bh = rpc.latest_blockhash()[0]
    tx = Transaction([signer], Message.new_with_blockhash(ixs, signer.pubkey(), Hash.from_string(bh)),
                     Hash.from_string(bh))
    sig = rpc.call("sendTransaction", [base64.b64encode(bytes(tx)).decode(), {"encoding": "base64"}])
    for _ in range(120):
        st = rpc.call("getSignatureStatuses", [[sig], {"searchTransactionHistory": True}])["value"][0]
        if st and st.get("confirmationStatus") in ("confirmed", "finalized"):
            return sig, st
        time.sleep(0.5)
    raise RuntimeError(f"no confirmation for {sig}")


def main():
    url, keyfile, dest, keep = sys.argv[1], sys.argv[2], Pubkey.from_string(sys.argv[3]), int(sys.argv[4])
    me = Keypair.from_bytes(bytes(json.loads(Path(keyfile).read_text())))
    rpc, b = RpcClient(url, timeout=30), Builder(PROGRAM)
    rooms = {layouts.decode_room(d)["room_mint"]: (layouts.decode_room(d)["room_id"], k)
             for k, d in rpc.program_accounts(PROGRAM, "Room", layouts.ROOM_LEN)[1]}
    doors = {d["mint"]: d for d in (layouts.decode_door(x) for _, x in rpc.program_accounts(PROGRAM, "Door", layouts.DOOR_LEN)[1])}
    room_ids = {k: rid for _, (rid, k) in rooms.items()}
    held = rpc.call("getTokenAccountsByOwner", [str(me.pubkey()), {"programId": str(T22)}, {"encoding": "jsonParsed"}])
    for acc in held["value"]:
        info = acc["account"]["data"]["parsed"]["info"]
        mint, n = info["mint"], int(info["tokenAmount"]["amount"])
        if n == 0:
            continue
        if mint in doors:
            d = doors[mint]
            rid = room_ids[d["room"]]
            room, core = b.room_accounts(rid)
            extra = b.door_accounts(room, d["nonce"])
        elif mint in rooms:
            rid = rooms[mint][0]
            room, core = b.room_accounts(rid)
            extra = {}
        else:
            print(f"skip {mint}: not a doors mint")
            continue
        values = {"user": me.pubkey(), "core.config": b.p(b"config"), "core.room": room,
                  **{"core." + k: v for k, v in core.items()}, **extra,
                  "user_token": ata(me.pubkey(), Pubkey.from_string(mint), T22)}
        ix = b._instruction("sell", values, struct.pack("<QQ", n, 0))
        before = rpc.balance(me.pubkey())
        sig, st = send(rpc, me, [ix])
        if st.get("err"):
            print(f"sell {mint} {n}: FAILED {st['err']} {sig}")
            continue
        print(f"sold {mint} {n} -> {sig} slot {st['slot']} +{rpc.balance(me.pubkey()) - before} lamports")
    bal = rpc.balance(me.pubkey())
    amount = bal - keep - 5000
    if amount > 0:
        sig, st = send(rpc, me, [transfer(TransferParams(from_pubkey=me.pubkey(), to_pubkey=dest, lamports=amount))])
        print(f"sent {amount} lamports to {dest} -> {sig} slot {st['slot']}")


if __name__ == "__main__":
    main()
