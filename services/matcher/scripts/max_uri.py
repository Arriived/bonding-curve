"""Largest URI the launch builder can sign, comparing legacy and service v0.

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

The in-memory table contains the same fixed addresses as the frozen table required by the service.

Usage: python3 scripts/max_uri.py [--json]
"""
import json
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from solders.address_lookup_table_account import AddressLookupTableAccount  # noqa: E402
from solders.keypair import Keypair  # noqa: E402

from matcher_service import txbuild  # noqa: E402
from matcher_service.lookup_table import expected_addresses  # noqa: E402

PROGRAM = "D7YsLsiJXoAF38vCUhFqYStepvSz6goG7EddHDe5NVJG"
BLOCKHASH = "11111111111111111111111111111111"
NAME, SYMBOL = "N" * 32, "S" * 10


def wire_len(ix, payer):
    return txbuild.wire_size(txbuild.build_message(ix, payer, BLOCKHASH, 400_000, 1))


def static_alt(b):
    return AddressLookupTableAccount(Keypair().pubkey(), expected_addresses(str(b.program)))


def wire_len_v0(ix, payer, alt):
    return txbuild.wire_size(txbuild.build_message(ix, payer, BLOCKHASH, 400_000, 1, alt))


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
           "priority_fee_instruction": True, "largest_uri_bytes": res,
           "v0_with_frozen_table_addresses": v0}
    if "--json" in sys.argv:
        print(json.dumps(out, indent=2))
        return
    fmt = lambda v: "does not fit" if v is None else f"URI <= {v} bytes"  # noqa: E731
    print(f"{'shape':28} {'legacy (comparison)':32} v0 + frozen table addresses (service)")
    for k, v in res.items():
        print(f"{k:28} {fmt(v):32} {fmt(v0[k])}")


if __name__ == "__main__":
    main()
