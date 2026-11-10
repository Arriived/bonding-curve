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

Total metadata budgets report the packet envelope for name + symbol + URI. They
can exceed the 242-byte sum of the three program field maxima. URI limits retain
the 32-byte name, 10-byte symbol and 200-byte program URI cap.

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


def launch(uri, door_nonce, name, symbol):
    return txbuild.encode_launch(name, symbol, uri, 10**9, 1, 1, 0, 0, 10**9, b"\0" * 32, door_nonce, 10**9)


def shapes(b, user, matcher):
    has_name_lock = any(a["name"] == "name_lock" for a in b.ix["create_room"]["accounts"])
    ident = os.urandom(32)

    def create(old=None, name_old=None):
        def f(uri, name=NAME, symbol=SYMBOL):
            kw = {}
            if has_name_lock:
                kw = {"name_key": os.urandom(16), "old_name_holder_room_id": name_old}
            return b.create_room_ix(user, matcher, 7, ident, old, launch(uri, 0, name, symbol), **kw)[0]
        return f

    def door(old=None):
        def f(uri, name=NAME, symbol=SYMBOL):
            return b.open_door_ix(user, matcher, 7, 9, ident, old, launch(uri, 9, name, symbol))[0]
        return f

    out = {"create_room": create(), "create_room_takeover": create(old=11),
           "open_door": door(), "open_door_takeover": door(old=11)}
    if has_name_lock:
        out["create_room_name_takeover"] = create(name_old=12)
        out["create_room_both_takeovers"] = create(old=11, name_old=12)
    return out, has_name_lock


def largest(build, payer, size=wire_len, ceiling=200):
    if size(build(""), payer) > txbuild.PACKET_LIMIT:
        return None
    low, high = 0, ceiling
    while low < high:
        mid = (low + high + 1) // 2
        if size(build("u" * mid), payer) <= txbuild.PACKET_LIMIT:
            low = mid
        else:
            high = mid - 1
    return low


def total_metadata_budget(build, payer, size=wire_len):
    # Synthetic strings isolate wire overhead, including the instruction length
    # prefix. The individual field caps are applied separately to usable bytes.
    return largest(lambda data: build(data, "", ""), payer, size, ceiling=txbuild.PACKET_LIMIT)


def main():
    b = txbuild.Builder(PROGRAM)
    user, matcher = Keypair().pubkey(), Keypair().pubkey()
    rows, has_name_lock = shapes(b, user, matcher)
    res = {k: largest(f, user) for k, f in rows.items()}
    alt = static_alt(b)
    def size_v0(ix, payer):
        return wire_len_v0(ix, payer, alt)

    v0 = {k: largest(f, user, size_v0) for k, f in rows.items()}
    legacy_budget = {k: total_metadata_budget(f, user) for k, f in rows.items()}
    v0_budget = {k: total_metadata_budget(f, user, size_v0) for k, f in rows.items()}
    out = {"idl": os.path.relpath(txbuild.IDL_PATH), "name_lock_in_idl": has_name_lock,
           "packet_limit": txbuild.PACKET_LIMIT, "name_bytes": len(NAME), "symbol_bytes": len(SYMBOL),
           "priority_fee_instruction": True, "compute_unit_limit": DEFAULT_CU_LIMIT,
           "largest_uri_bytes": res,
           "largest_uri_wire_bytes": {k: None if n is None else wire_len(rows[k]("u" * n), user)
                                      for k, n in res.items()},
           "full_200_byte_uri_wire_bytes": {k: wire_len(f("u" * 200), user) for k, f in rows.items()},
           "comparison_only_v0_with_static_lookup_table": v0,
           "metadata_field_limit_bytes": len(NAME) + len(SYMBOL) + 200,
           "legacy_metadata_budget_bytes": legacy_budget,
           "v0_metadata_budget_bytes": v0_budget}
    if "--json" in sys.argv:
        print(json.dumps(out, indent=2))
        return
    print(f"{'shape':32} {'legacy total':>12} {'legacy URI':>11} {'v0 total':>10} {'v0 URI':>9}")
    for k in rows:
        values = (legacy_budget[k], res[k], v0_budget[k], v0[k])
        cells = [str(n) if n is not None else "no fit" for n in values]
        print(f"{k:32} {cells[0]:>12} {cells[1]:>11} {cells[2]:>10} {cells[3]:>9}")


if __name__ == "__main__":
    main()
