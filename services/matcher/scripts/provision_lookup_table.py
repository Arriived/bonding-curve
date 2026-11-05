"""Create, extend and freeze the audited launch table in one transaction."""
import argparse
import base64
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from solders.hash import Hash
from solders.keypair import Keypair
from solders.system_program import create_lookup_table, extend_lookup_table, freeze_lookup_table
from solders.transaction import Transaction

from matcher_service.chain import RpcClient
from matcher_service.lookup_table import expected_addresses, load_frozen_table
from matcher_service.txbuild import load_idl


def provision(rpc, payer, program):
    authority = payer.pubkey()
    recent_slot = rpc.call("getSlot", [{"commitment": "finalized"}])
    create, address = create_lookup_table({
        "authority_address": authority, "payer_address": authority, "recent_slot": recent_slot,
    })
    entries = expected_addresses(program)
    extend = extend_lookup_table({
        "authority_address": authority, "payer_address": authority,
        "lookup_table_address": address, "new_addresses": entries,
    })
    freeze = freeze_lookup_table({"authority_address": authority, "lookup_table_address": address})
    blockhash, last_valid, _ = rpc.latest_blockhash()
    tx = Transaction.new_signed_with_payer([create, extend, freeze], authority, [payer], Hash.from_string(blockhash))
    signature = str(tx.signatures[0])
    print(f"Submitting lookup table {address} with signature {signature}", file=sys.stderr, flush=True)
    sent = rpc.call("sendTransaction", [
        base64.b64encode(bytes(tx)).decode(), {"encoding": "base64", "preflightCommitment": "confirmed"},
    ])
    if sent != signature:
        raise RuntimeError("RPC returned a different transaction signature")

    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        result = rpc.call("getSignatureStatuses", [[signature], {"searchTransactionHistory": True}])
        status = result["value"][0]
        if status and status["err"] is not None:
            raise RuntimeError(f"lookup table transaction failed at slot {status['slot']}: {status['err']}")
        if status and status["confirmationStatus"] == "finalized":
            freeze_slot = status["slot"]
            if rpc.call("getSlot", [{"commitment": "finalized"}]) > freeze_slot:
                break
        if status is None and rpc.block_height() > last_valid:
            raise RuntimeError("lookup table transaction blockhash expired")
        time.sleep(1)
    else:
        raise RuntimeError(f"confirmation timed out for table {address}, transaction {signature}")

    table, verified_slot = load_frozen_table(rpc, address, program)
    return {"table": str(address), "program": program, "freeze_signature": signature,
            "freeze_slot": freeze_slot, "verified_slot": verified_slot,
            "addresses": [str(entry) for entry in table.addresses]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rpc", required=True)
    parser.add_argument("--keypair", required=True, type=Path)
    args = parser.parse_args()
    payer = Keypair.from_bytes(bytes(json.loads(args.keypair.read_text())))
    print(json.dumps(provision(RpcClient(args.rpc, timeout=30), payer, load_idl()["address"]), indent=2))


if __name__ == "__main__":
    main()
