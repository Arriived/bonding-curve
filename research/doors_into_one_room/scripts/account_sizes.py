"""Exact byte layouts and rent for the pre-minted room/door design and its DAMM v2 graduation.

Rent-exempt minimum = (128 + data_bytes) * 5,080 lamports, verified by raw
getMinimumBalanceForRentExemption RPC reads in outputs/narrative/rent_confirmation.json.

Token-2022 layout (solana-program/token-2022 @ 986b3aa5, interface/src/extension/mod.rs):
accounts with extensions are padded to Account::LEN = 165 bytes, then a 1-byte AccountType,
then TLV entries with a 2-byte type and 2-byte length. MetadataPointer = 64 bytes;
MintCloseAuthority = 32 bytes. TokenMetadata (solana-program/token-metadata @ 685b8b66,
interface/src/state.rs) is Borsh: update_authority 32, mint 32, name, symbol, uri as
u32-length strings, additional_metadata as a u32-length Vec<(String, String)>.
A token account for a mint whose extensions require no account extensions is 165 bytes;
an ATA created by the ATA program for a Token-2022 mint adds ImmutableOwner (170 bytes).

DAMM v2 (MeteoraAg/damm-v2 @ 5398b5c7): Pool::INIT_SPACE = 1104 (state/pool.rs:185),
Position::INIT_SPACE = 400 (state/position.rs:121), both + 8-byte discriminator. Position NFT
mint: decimals 0, MetadataPointer + MintCloseAuthority, TokenMetadata "Meteora Position NFT" /
"MPN" / fixed URI (instructions/ix_create_position.rs, create_position_nft).
"""
LAMPORTS_PER_BYTE = 5080
OVERHEAD = 128
SOL = 1_000_000_000
USD_PER_SOL = 150.0       # only to quote SOL figures in dollars
DAMM_NFT_URI = "https://raw.githubusercontent.com/MeteoraAg/token-metadata/main/meteora_position_nft.png"


def rent(n):
    return (OVERHEAD+n)*LAMPORTS_PER_BYTE


# Door-mint additional_metadata as (key bytes, value bytes) pairs, as created by
# programs/doors_v1/src/vaults.rs create_mint: ("room", base58 room pubkey), ("door", index
# u32 decimal), ("door_nonce", nonce u64 decimal), ("program", base58 program id). Base58 of a
# 32-byte key is up to 44 characters; u32 up to 10 digits; u64 up to 20.
ROOM_MINT_META = [(4, 44)]
DOOR_MINT_META_MAX = [(4, 44), (4, 10), (10, 20), (7, 44)]
DOOR_MINT_META_MIN = [(4, 44), (4, 1), (10, 1), (7, 44)]
# Before 5 November 2026 (door address from the index): ("room", ...), ("door", index) only.
DOOR_MINT_META_MAX_BEFORE_NONCE = [(4, 44), (4, 10)]


LAYOUTS = {
    "Config": [
        ("anchor discriminator", 8), ("admin: Pubkey", 32), ("protocol_fee_recipient: Pubkey", 32),
        ("fee_bps: u16", 2), ("door_share_bps: u16", 2), ("door_fee_lamports: u64 (default 0)", 8),
        ("room_fee_lamports: u64 (default 0)", 8), ("convert_fee_lamports: u64", 8),
        ("v_sol_lamports: u64", 8), ("v_tok: u64 (base units)", 8), ("supply: u64 (base units)", 8),
        ("r_star_lamports: u64 (pool seed)", 8), ("meteora_dynamic_config: Pubkey", 32),
        ("graduation_trigger_lamports: u64 (R* + graduation rent)", 8),
        ("paused: bool", 1), ("bump: u8", 1), ("matcher_authority: Pubkey", 32),
        ("live_min_reserve_lamports: u64", 8), ("live_max_idle_seconds: u64", 8),
        ("live_new_seconds: u64", 8), ("live_min_volume_lamports: u64", 8),
        ("pool_min_window_lp_fee: u64", 8),
        ("founder_share_bps: u16 (default 0; copied into each room)", 2)],
    "Room": [
        ("anchor discriminator", 8), ("room_id: u64", 8),
        ("bumps: room, reserve_vault, fee_vault, grad_payer, room_vault, retired_vault, fee_wsol (7 x u8)", 7),
        ("status: u8 (0 curve, 1 complete, 2 graduated)", 1),
        ("room_mint: Pubkey", 32), ("room_vault: Pubkey", 32), ("retired_vault: Pubkey", 32), ("fee_wsol: Pubkey", 32),
        ("v_sol_lamports: u64", 8), ("v_tok: u64", 8), ("supply: u64", 8), ("r_star_lamports: u64", 8),
        ("graduation_trigger_lamports: u64", 8),
        ("fee_bps: u16", 2), ("door_share_bps: u16", 2),
        ("reserve: u64 (lamports the program credited to ReserveVault)", 8),
        ("sold: u64 (program curve position q; never inferred from vault balance)", 8),
        ("retired: u64 (accounted retirement; excess stays locked)", 8), ("door_count: u32", 4),
        ("protocol_accrued_sol: u64", 8), ("protocol_accrued_wsol: u64", 8),
        ("pending_reserve_sol: u64", 8), ("pending_reserve_wsol: u64", 8), ("reserve_share_total: u64", 8),
        ("volume_gross: u128", 16), ("trades: u64", 8), ("created_at: i64", 8), ("last_trade_at: i64", 8),
        ("graduated_at: i64", 8), ("damm_pool: Pubkey", 32), ("damm_position: Pubkey", 32),
        ("position_nft_mint: Pubkey", 32), ("identity: [u8; 32] (derived SlugLock key)", 32),
        ("uri_len: u8", 1), ("uri: [u8; 200]", 200),
        ("fee_ckpt: u128", 16), ("fee_ckpt_ts: i64", 8),
        ("liveness_buckets: [(start: i64, amount: u128); 25] (packed Borsh)", 25 * 24),
        ("founder: Pubkey (immutable launcher)", 32),
        ("founder_accrued: u64 (SOL lamports)", 8),
        ("founder_accrued_wsol: u64 (WSOL base units)", 8),
        ("founder_share_bps: u16 (immutable Config snapshot; default 0)", 2)],
    "ReserveVault (program-owned, no data; SOL reserve)": [],
    "FeeVault (program-owned, no data; SOL fees)": [],
    "GradPayer (SYSTEM-owned PDA, no data; holds DAMM v2 rent, signs as payer)": [],
    "SlugLock": [("anchor discriminator", 8), ("room_id: u64", 8), ("bump: u8", 1)],
    "Door": [
        ("anchor discriminator", 8), ("room: Pubkey", 32), ("index: u32", 4), ("mint: Pubkey", 32),
        ("door_vault: Pubkey", 32), ("room_token_vault: Pubkey", 32), ("creator: Pubkey", 32),
        ("fee_recipient: Pubkey", 32), ("bumps: door, mint, door_vault, room_token_vault (4 x u8)", 4),
        ("backing: u64 (program-tracked 1:1 redemption liability; vaults may hold surplus)", 8),
        ("accrued_sol: u64", 8), ("accrued_wsol: u64", 8), ("claimed_sol: u64", 8), ("claimed_wsol: u64", 8),
        ("buy_volume: u128 (gross lamports)", 16), ("sell_volume: u128", 16), ("trades: u64", 8),
        ("created_at: i64", 8), ("matcher_version: u16", 2), ("rule: u8", 1),
        ("face: u32 (door index)", 4),
        ("nonce: u64 (Door PDA seed, Launch.door_nonce; 0 for door 0)", 8), ("reserved: [u8; 17]", 17)],
}


def token_metadata_value(name, symbol, uri, extra):
    n = 32+32+(4+name)+(4+symbol)+(4+uri)+4
    for k, v in extra:
        n += 4+k+4+v
    return n


def meme_mint(name, symbol, uri, extra):
    """Token-2022 mint with MetadataPointer + TokenMetadata only (what wallets see as a plain memecoin)."""
    return 165+1+(4+64)+4+token_metadata_value(name, symbol, uri, extra)


def damm_nft_mint():
    return 165+1+(4+64)+(4+32)+4+token_metadata_value(len("Meteora Position NFT"), len("MPN"), len(DAMM_NFT_URI), [])


def graduation_rent_lamports():
    """Rent for the accounts graduate creates (DAMM v2 pool, position, NFT mint + account, two vaults,
    protocol's NFT ATA). Shared with curve_identities.py and fee_model.py."""
    TA, ATA22 = 165, 170
    return sum(rent(n) for n in (8+1104, 8+400, damm_nft_mint(), TA, TA, TA, ATA22))


def per_door_rent_lamports():
    door = sum(b for _, b in LAYOUTS["Door"])
    return rent(door)+rent(meme_mint(32, 10, 200, DOOR_MINT_META_MAX))+2*rent(165)


def per_room_rent_lamports():
    return (rent(sum(b for _, b in LAYOUTS["Room"])) + 3 * rent(0)
            + rent(sum(b for _, b in LAYOUTS["SlugLock"]))
            + rent(meme_mint(32, 10, 200, ROOM_MINT_META)) + 3 * rent(165))


def main():
    print("<!-- generated by scripts/account_sizes.py -->")
    sizes = {k: sum(b for _, b in v) for k, v in LAYOUTS.items()}
    room_mint = meme_mint(32, 10, 200, ROOM_MINT_META)                 # ("room", pubkey)
    door_mint_max = meme_mint(32, 10, 200, DOOR_MINT_META_MAX)         # + door, door_nonce, program
    door_mint_min = meme_mint(1, 1, 0, DOOR_MINT_META_MIN)
    TA, ATA22 = 165, 170
    rows = [(k, v) for k, v in sizes.items()]
    rows += [("RoomMint (Token-2022 + MetadataPointer + TokenMetadata; name 32 / symbol 10 / uri 200)", room_mint),
             ("RoomVault (room-token account owned by Room PDA; 1B pre-minted here)", TA),
             ("RetiredVault (room-token account owned by Room PDA)", TA),
             ("FeeWsol (SPL WSOL account owned by Room PDA; post-graduation sell fees)", TA),
             ("DoorMint, max metadata (name 32 / symbol 10 / uri 200)", door_mint_max),
             ("DoorMint, minimum metadata", door_mint_min),
             ("DoorVault (door-token account owned by Door PDA; 1B pre-minted here)", TA),
             ("DoorRoomVault (room-token account owned by Door PDA; the backing)", TA),
             ("trader's Token-2022 ATA (door or room token; ImmutableOwner)", ATA22),
             ("check: classic SPL token account", 165)]
    print("| account | data bytes | rent-exempt lamports | SOL |\n|---|---|---|---|")
    for k, n in rows:
        print(f"| {k} | {n} | {rent(n):,} | {rent(n)/SOL:.6f} |")
    per_door = rent(sizes["Door"])+rent(door_mint_max)+2*rent(TA)
    per_door_min = rent(sizes["Door"])+rent(door_mint_min)+2*rent(TA)
    per_room = (rent(sizes["Room"])+3*rent(0)+rent(sizes["SlugLock"])+rent(room_mint)+3*rent(TA))
    print(f"\nPer-door rent (Door + DoorMint max + DoorVault + DoorRoomVault): {per_door:,} lamports "
          f"= {per_door/SOL:.6f} SOL = ${per_door/SOL*USD_PER_SOL:,.2f} at ${USD_PER_SOL:.0f}/SOL "
          f"(minimum metadata: {per_door_min:,} = {per_door_min/SOL:.6f} SOL = ${per_door_min/SOL*USD_PER_SOL:,.2f})")
    print(f"Data bytes allocated per door (Door + DoorMint max + DoorVault + DoorRoomVault): "
          f"{sizes['Door']+door_mint_max+2*TA:,}")
    print(f"Per-room rent excluding door accounts (Room + ReserveVault + FeeVault + GradPayer + SlugLock + RoomMint "
          f"+ RoomVault + RetiredVault + FeeWsol): {per_room:,} lamports = {per_room/SOL:.6f} SOL "
          f"= ${per_room/SOL*USD_PER_SOL:,.2f}")
    launch = per_room+per_door
    before = meme_mint(32, 10, 200, DOOR_MINT_META_MAX_BEFORE_NONCE)
    print(f"Door-mint metadata self-description (door_nonce + program, 5 Nov 2026): DoorMint max "
          f"{before} -> {door_mint_max} bytes, +{door_mint_max-before} bytes, "
          f"+{rent(door_mint_max)-rent(before):,} lamports per door at a 20-digit nonce")
    print(f"Launching a room (room accounts + door 0 at max metadata; no room or door fee): {launch:,} lamports "
          f"= {launch/SOL:.6f} SOL = ${launch/SOL*USD_PER_SOL:,.2f}, plus transaction fees")
    nft = damm_nft_mint()
    grad = [("DAMM v2 Pool (8 + 1104)", 8+1104), ("DAMM v2 Position (8 + 400)", 8+400),
            ("DAMM v2 position NFT mint", nft), ("DAMM v2 position NFT account", TA),
            ("DAMM v2 token A vault (room token)", TA), ("DAMM v2 token B vault (WSOL)", TA),
            ("protocol fee recipient's ATA for the position NFT (Token-2022, ImmutableOwner)", ATA22)]
    print("\nAccounts created at graduation, and their rent:\n")
    print("| account | data bytes | rent-exempt lamports |\n|---|---|---|")
    for k, n in grad:
        print(f"| {k} | {n} | {rent(n):,} |")
    g = sum(rent(n) for _, n in grad)
    assert g == graduation_rent_lamports()
    print(f"| **total, moved from the reserve to GradPayer at graduate** | | **{g:,} lamports = {g/SOL:.6f} SOL** |")
    print(f"\nA temporary WSOL account (165 bytes, {rent(165):,} lamports) is created and closed inside `graduate`; "
          "its rent is returned in the same transaction.")
    print("\nField layouts:\n")
    for name, fields in LAYOUTS.items():
        if not fields:
            continue
        off = 0
        print(f"**{name}** ({sizes[name]} bytes)\n\n| offset | bytes | field |\n|---|---|---|")
        for fld, b in fields:
            print(f"| {off} | {b} | {fld} |")
            off += b
        print()


if __name__ == "__main__":
    main()
