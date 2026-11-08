"""Largest URI the service can sign in a legacy transaction, per launch shape.

Uses the service's own builder (`txbuild.Builder`, the pinned IDL) and its own size check: the
placeholder-signed wire transaction must be at most `txbuild.PACKET_LIMIT` (1,232) bytes. Name 32
bytes and symbol 10 bytes, the program's maxima. Every shape is measured with the compute-unit-price
instruction the service adds for a priority fee, since that is the larger message.

Shapes:
  create_room                  new identity, no old holder
  create_room_takeover         the SlugLock is held by a dead room (one old holder)
  open_door / open_door_takeover
and, when the pinned IDL has a NameLock (`name_lock` on create_room):
  create_room_name_takeover    the NameLock is held by a dead room that is not the SlugLock holder
  create_room_both_takeovers   SlugLock and NameLock held by two different dead rooms

Also, for comparison only (the service signs legacy transactions): the same shapes as a v0 message
whose lookup table holds the accounts that are the same in every launch and are not invoked as a top-level
program (Config, Token-2022, classic SPL Token, the WSOL mint, the ATA program, the System program).

Usage: python3 scripts/max_uri.py [--json]
"""
import json
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from solders.address_lookup_table_account import AddressLookupTableAccount  # noqa: E402
from solders.hash import Hash  # noqa: E402
from solders.keypair import Keypair  # noqa: E402
from solders.message import MessageV0  # noqa: E402
from solders.transaction import VersionedTransaction  # noqa: E402
from solders.signature import Signature  # noqa: E402
from solders.transaction import Transaction  # noqa: E402

from matcher_service import txbuild  # noqa: E402
from matcher_service.config import DEFAULT_CU_LIMIT  # noqa: E402

from matcher_service.program_id import PROGRAM_ID as PROGRAM
BLOCKHASH = "11111111111111111111111111111111"
NAME, SYMBOL = "N" * 32, "S" * 10


def wire_len(ix, payer):
    m = txbuild.build_message(ix, payer, BLOCKHASH, DEFAULT_CU_LIMIT, 1)
    return len(bytes(Transaction.populate(m, [Signature.default()] * m.header.num_required_signatures)))


def static_alt(b):
    keys = [b.p(b"config"), txbuild.T22, txbuild.CLASSIC, txbuild.WSOL, txbuild.ATA, txbuild.SYSTEM]
    return AddressLookupTableAccount(Keypair().pubkey(), keys)


def wire_len_v0(ix, payer, alt):
    from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
    m = MessageV0.try_compile(payer, [set_compute_unit_limit(DEFAULT_CU_LIMIT), set_compute_unit_price(1), ix], [alt],
                              Hash.from_string(BLOCKHASH))
    return len(bytes(VersionedTransaction.populate(m, [Signature.default()] * m.header.num_required_signatures)))


def launch(uri, door_nonce):
    return txbuild.encode_launch(NAME, SYMBOL, uri, 10**9, 1, 1, 0, 0, 10**9, b"\0" * 32, door_nonce, 10**9)


def shapes(b, user, matcher):
    has_name_lock = any(a["name"] == "name_lock" for a in b.ix["create_room"]["accounts"])
    ident = os.urandom(32)

    def create(old=None, name_old=None):
        def f(uri):
            kw = {}
            if has_name_lock:
                kw = {"name_key": os.urandom(16), "old_name_holder_room_id": name_old}
            return b.create_room_ix(user, matcher, 7, ident, old, launch(uri, 0), **kw)[0]
        return f

    def door(old=None):
        return lambda uri: b.open_door_ix(user, matcher, 7, 9, ident, old, launch(uri, 9))[0]

    out = {"create_room": create(), "create_room_takeover": create(old=11),
           "open_door": door(), "open_door_takeover": door(old=11)}
    if has_name_lock:
        out["create_room_name_takeover"] = create(name_old=12)
        out["create_room_both_takeovers"] = create(old=11, name_old=12)
    return out, has_name_lock


def largest(build, payer, size=wire_len):
    best = None
    for n in range(0, 201):
        if size(build("u" * n), payer) <= txbuild.PACKET_LIMIT:
            best = n
        else:
            break
    return best  # None: does not fit even with an empty URI


def main():
    b = txbuild.Builder(PROGRAM)
    user, matcher = Keypair().pubkey(), Keypair().pubkey()
    rows, has_name_lock = shapes(b, user, matcher)
    res = {k: largest(f, user) for k, f in rows.items()}
    alt = static_alt(b)
    v0 = {k: largest(f, user, lambda ix, payer: wire_len_v0(ix, payer, alt)) for k, f in rows.items()}
    out = {"idl": os.path.relpath(txbuild.IDL_PATH), "name_lock_in_idl": has_name_lock,
           "packet_limit": txbuild.PACKET_LIMIT, "name_bytes": len(NAME), "symbol_bytes": len(SYMBOL),
           "priority_fee_instruction": True, "compute_unit_limit": DEFAULT_CU_LIMIT,
           "largest_uri_bytes": res,
           "largest_uri_wire_bytes": {k: None if n is None else wire_len(rows[k]("u" * n), user)
                                      for k, n in res.items()},
           "full_200_byte_uri_wire_bytes": {k: wire_len(f("u" * 200), user) for k, f in rows.items()},
           "comparison_only_v0_with_static_lookup_table": v0}
    if "--json" in sys.argv:
        print(json.dumps(out, indent=2))
        return
    fmt = lambda v: "does not fit" if v is None else f"URI <= {v} bytes"  # noqa: E731
    print(f"{'shape':28} {'legacy (what the service signs)':32} v0 + static lookup table (comparison)")
    for k, v in res.items():
        print(f"{k:28} {fmt(v):32} {fmt(v0[k])}")


if __name__ == "__main__":
    main()
