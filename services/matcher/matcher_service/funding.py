"""Conservative new-room rent budget; existing/prefunded accounts are not credited.

Mirror the program's exact Borsh TokenMetadata sizing. Query the cluster's rent
minimums instead of hardcoding a lamports-per-byte calibration. Funds are checked,
not escrowed: this raises squatting cost but cannot replace an on-chain NameLock.
"""
from . import layouts


def creation_rent_sizes(name, symbol, uri, room_key, program_key, first_buy):
    text_bytes = sum(len(s.encode("utf-8")) for s in (name, symbol, uri))

    def mint_size(extra):
        metadata = 64 + 12 + text_bytes + 4 + sum(
            8 + len(k.encode()) + len(v.encode()) for k, v in extra)
        return 234 + 4 + metadata

    room_extra = [("room", str(room_key))]
    door_extra = room_extra + [("door", "0"), ("door_nonce", "0"), ("program", str(program_key))]
    sizes = [layouts.ROOM_LEN, 0, 0, 0, layouts.SLUG_LEN, layouts.DOOR_LEN,
             mint_size(room_extra), mint_size(door_extra), 165, 165, 165, 165, 165]
    if first_buy:
        sizes.append(170)  # Token-2022 user ATA with ImmutableOwner
    return sizes
