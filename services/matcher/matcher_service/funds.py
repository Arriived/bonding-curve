"""Proof of funds for a new-room decision (H-1 interim; program/docs/SECURITY_REVIEW.md).

A new-room decision holds its folded name and identity in flight until it expires. Requests are signed
(auth.py) but keys are free, so the hold is only worth something if the launcher could actually pay for
the launch it asked for. At decision time the launcher's confirmed balance must cover:

  - rent for every account create_room makes, sized exactly as the program sizes them (below), each
    priced by the cluster's own getMinimumBalanceForRentExemption;
  - the flat room and door fees in Config;
  - the first buy;
  - SIGNATURE_FEES for the transaction's signatures.

Sizes (programs/doors_v1/src/state.rs, vaults.rs create_mint; research/.../account_sizes.py):
Room 1,315; ReserveVault, FeeVault, GradPayer 0; SlugLock 17 (new identity only); token accounts 165
(RoomVault, RetiredVault, FeeWsol, DoorVault, DoorRoomVault); Door 328; mints 238 + metadata value;
the launcher's door-token ATA 170 when there is a first buy.
"""
ROOM, DOOR, SLUG, TOKEN, ATA22 = 1315, 328, 17, 165, 170
SIGNATURE_FEES = 2 * 5_000  # launcher + matcher, base fee per signature


def _meta_value(name, symbol, uri, extra):
    return 64 + 12 + len(name.encode()) + len(symbol.encode()) + len(uri.encode()) + 4 + sum(8 + k + v for k, v in extra)


def mint_size(name, symbol, uri, extra):
    return 238 + _meta_value(name, symbol, uri, extra)


def create_room_sizes(name, symbol, uri, first_buy, new_identity, room_key_b58_len=44):
    room_meta = [(4, room_key_b58_len)]
    door0_meta = [(4, room_key_b58_len), (4, 1), (10, 1), (7, 44)]   # ("door","0"), ("door_nonce","0"), program
    sizes = [ROOM, 0, 0, 0, mint_size(name, symbol, uri, room_meta), TOKEN, TOKEN, TOKEN,
             DOOR, mint_size(name, symbol, uri, door0_meta), TOKEN, TOKEN]
    if new_identity:
        sizes.append(SLUG)
    if first_buy:
        sizes.append(ATA22)
    return sizes


def required_lamports(rpc, sizes, fees, first_buy):
    cache = {}
    rent = 0
    for n in sizes:
        if n not in cache:
            cache[n] = rpc.min_balance(n)
        rent += cache[n]
    return rent + fees + first_buy + SIGNATURE_FEES, rent
