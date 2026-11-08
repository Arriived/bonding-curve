"""Decoders for the deployed program's accounts.

Offsets come from idl/layouts.paired.json (program/verification/layouts.json of the deployed source,
generated from the IDL and checked by program/scripts/check_layouts.py). A test asserts the constants
below equal that file, so layout drift fails the build instead of producing wrong decisions.
"""
import hashlib
import struct

from solders.pubkey import Pubkey


def account_discriminator(name: str) -> bytes:
    return hashlib.sha256(f"account:{name}".encode()).digest()[:8]


ROOM_LEN, DOOR_LEN, SLUG_LEN, NAME_LEN, CONFIG_LEN = 1335, 360, 17, 33, 248
ROOM_BIRTH_LEN = 735
DISC = {k: account_discriminator(k) for k in ("Room", "Door", "SlugLock", "NameLock", "Config")}

# field -> (offset, bytes), the subset the service reads
ROOM_FIELDS = {"room_id": (8, 8), "status": (23, 1), "room_mint": (24, 32), "reserve": (196, 8),
               "door_count": (220, 4), "volume_gross": (264, 16), "created_at": (288, 8),
               "last_trade_at": (296, 8), "identity": (408, 32), "liveness_buckets": (665, 604),
               # curve state for the first-buy quote (quote.py)
               "v_sol_lamports": (152, 8), "v_tok": (160, 8), "supply": (168, 8),
               "graduation_trigger_lamports": (184, 8), "fee_bps": (192, 2), "sold": (204, 8),
               "pending_reserve_sol": (240, 8), "door_share_bps": (194, 2)}
DOOR_FIELDS = {"room": (8, 32), "index": (40, 4), "mint": (44, 32), "nonce": (303, 8)}
SLUG_FIELDS = {"room_id": (8, 8)}
NAME_FIELDS = {"room_id": (8, 8), "key": (16, 16)}
CONFIG_FIELDS = {"paused": (172, 1), "matcher_authority": (174, 32), "room_fee_lamports": (84, 8),
                 "door_fee_lamports": (76, 8), "live_min_reserve_lamports": (206, 8),
                 "live_max_idle_seconds": (214, 8), "live_new_seconds": (222, 8),
                 "live_min_volume_lamports": (230, 8),
                 # Config::launch_terms_hash inputs (create_room requires Launch.expected_terms_hash)
                 "fee_bps": (72, 2), "door_share_bps": (74, 2), "v_sol_lamports": (100, 8), "v_tok": (108, 8),
                 "supply": (116, 8), "r_star_lamports": (124, 8), "graduation_trigger_lamports": (164, 8),
                 "founder_share_bps": (246, 2)}
BUCKETS = 25  # liveness_buckets: [Bucket { start: i64, amount: u128 }; 25] = 600 bytes


class LayoutError(ValueError):
    pass


def _check(data: bytes, name: str, length: int):
    if len(data) != length or data[:8] != DISC[name]:
        raise LayoutError(f"not a {name} account (len {len(data)})")


def decode_room(data: bytes) -> dict:
    if len(data) not in (ROOM_BIRTH_LEN,ROOM_LEN) or data[:8] != DISC['Room']:
        raise LayoutError(f'not a sparse Room account (len {len(data)})')
    f = ROOM_FIELDS
    lo, hi = struct.unpack_from("<QQ", data, f["volume_gross"][0])
    buckets = []
    off = f["liveness_buckets"][0]
    count = struct.unpack_from('<I',data,off)[0]
    off += 4
    if count > BUCKETS or off+24*count+66 > len(data):
        raise LayoutError('invalid sparse liveness bucket count')
    if len(data)==ROOM_BIRTH_LEN and count:
        raise LayoutError('birth room cannot contain allocated volume slots')
    for i in range(count):
        start = struct.unpack_from("<q", data, off + 24 * i)[0]
        a_lo, a_hi = struct.unpack_from("<QQ", data, off + 24 * i + 8)
        buckets.append((start, a_lo + (a_hi << 64)))
    return {
        "room_id": struct.unpack_from("<Q", data, f["room_id"][0])[0],
        "status": data[f["status"][0]],
        "room_mint": str(Pubkey.from_bytes(data[24:56])),
        "reserve": struct.unpack_from("<Q", data, f["reserve"][0])[0],
        "door_count": struct.unpack_from("<I", data, f["door_count"][0])[0],
        "volume_gross": lo + (hi << 64),
        "created_at": struct.unpack_from("<q", data, f["created_at"][0])[0],
        "last_trade_at": struct.unpack_from("<q", data, f["last_trade_at"][0])[0],
        "identity": data[408:440].hex(),
        **{k: struct.unpack_from("<Q", data, f[k][0])[0]
           for k in ("v_sol_lamports", "v_tok", "supply", "graduation_trigger_lamports", "sold",
                     "pending_reserve_sol")},
        "fee_bps": struct.unpack_from("<H", data, f["fee_bps"][0])[0],
        "door_share_bps": struct.unpack_from("<H", data, f["door_share_bps"][0])[0],
        "buckets": buckets,
    }


def decode_door(data: bytes) -> dict:
    _check(data, "Door", DOOR_LEN)
    return {"room": str(Pubkey.from_bytes(data[8:40])), "index": struct.unpack_from("<I", data, 40)[0],
            "mint": str(Pubkey.from_bytes(data[44:76])), "nonce": struct.unpack_from("<Q", data, 303)[0]}


def decode_slug(data: bytes) -> dict:
    _check(data, "SlugLock", SLUG_LEN)
    return {"room_id": struct.unpack_from("<Q", data, 8)[0]}


def decode_name(data: bytes) -> dict:
    _check(data, "NameLock", NAME_LEN)
    return {"room_id": struct.unpack_from("<Q", data, 8)[0], "key": data[16:32].hex()}


def decode_config(data: bytes) -> dict:
    _check(data, "Config", CONFIG_LEN)
    u = lambda k: struct.unpack_from("<Q", data, CONFIG_FIELDS[k][0])[0]  # noqa: E731
    h = lambda k: struct.unpack_from("<H", data, CONFIG_FIELDS[k][0])[0]  # noqa: E731
    terms = hashlib.sha256(b"doors-v1:launch-terms:v1" + b"".join(
        struct.pack("<Q", u(k)) for k in ("v_sol_lamports", "v_tok", "supply", "r_star_lamports",
                                          "graduation_trigger_lamports"))
        + b"".join(struct.pack("<H", h(k)) for k in ("fee_bps", "door_share_bps", "founder_share_bps"))).hexdigest()
    return {
        "launch_terms_hash": terms,
        "paused": bool(data[172]),
        "matcher_authority": str(Pubkey.from_bytes(data[174:206])),
        "room_fee_lamports": u("room_fee_lamports"),
        "door_fee_lamports": u("door_fee_lamports"),
        "live_min_reserve_lamports": u("live_min_reserve_lamports"),
        "live_max_idle_seconds": u("live_max_idle_seconds"),
        "live_new_seconds": u("live_new_seconds"),
        "live_min_volume_lamports": u("live_min_volume_lamports"),
        # a new room's curve, for the first-buy quote (quote.new_room_curve)
        **{k: u(k) for k in ("v_sol_lamports", "v_tok", "supply", "graduation_trigger_lamports")},
        "fee_bps": h("fee_bps"),
    }


# ---- Token-2022 mint with TokenMetadata (immutable door faces) ---------------------------------
MINT_BASE_LEN = 82
ACCOUNT_TYPE_OFFSET = 165  # extensions follow the 165-byte base account area and one account-type byte
TOKEN_METADATA_EXT = 19


def decode_mint_face(data: bytes) -> dict:
    """Name/symbol/uri of a Token-2022 mint's TokenMetadata, plus the authorities the program revokes."""
    if len(data) < ACCOUNT_TYPE_OFFSET + 1 or data[ACCOUNT_TYPE_OFFSET] != 1:
        raise LayoutError("not a Token-2022 mint with extensions")
    mint_auth_tag = struct.unpack_from("<I", data, 0)[0]
    freeze_tag = struct.unpack_from("<I", data, 46)[0]
    i = ACCOUNT_TYPE_OFFSET + 1
    while i + 4 <= len(data):
        ext, length = struct.unpack_from("<HH", data, i)
        body = data[i + 4:i + 4 + length]
        if ext == TOKEN_METADATA_EXT:
            update_authority = body[:32]
            o = 64
            vals = []
            for _ in range(3):
                n = struct.unpack_from("<I", body, o)[0]
                vals.append(body[o + 4:o + 4 + n].decode("utf-8"))
                o += 4 + n
            return {"name": vals[0], "symbol": vals[1], "uri": vals[2],
                    "immutable": update_authority == bytes(32) and mint_auth_tag == 0 and freeze_tag == 0}
        if ext == 0:
            break
        i += 4 + length
    raise LayoutError("mint has no TokenMetadata extension")
