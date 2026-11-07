"""Decode launches on pump.fun and Raydium LaunchLab (bonk.fun, StonkFun and other platforms) from RPC data.

Layouts and discriminators come from each program's own Anchor IDL, read from chain and saved in watcher/idl/
(pump.json: program 6EF8..., raydium_launchpad.json: program LanMV9...). tests/test_watcher.py checks the constants
below against those files.

Two paths:
  * pump.fun emits CreateEvent in its logs ("Program data: ..."), so most launches decode from the websocket
    notification alone (`pump_create_from_logs`).
  * Otherwise, and always for LaunchLab (its PoolCreateEvent is a self-CPI, not a log), the transaction is fetched
    and the create instruction's own arguments are decoded (`launches_from_tx`), from outer or inner instructions.
"""
import base64
import binascii
import struct

PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
LAUNCHLAB = "LanMV9sAd7wArD4vJFi2qDdfnVhFxYSUg6eADduJ3uj"

PUMP_CREATE_EVENT = bytes([27, 114, 169, 77, 222, 235, 99, 118])
PUMP_IX = {bytes([24, 30, 200, 40, 5, 28, 7, 119]): ("create", 7),        # (name, index of `user` in accounts)
           bytes([214, 144, 76, 236, 95, 139, 49, 180]): ("create_v2", 5)}
LAUNCHLAB_IX = {bytes([175, 175, 109, 31, 13, 152, 155, 237]): "initialize",
                bytes([67, 153, 175, 39, 218, 16, 38, 32]): "initialize_v2",
                bytes([37, 190, 126, 222, 44, 154, 171, 17]): "initialize_with_token_2022"}
# LaunchLab initialize* accounts (same order in all three): payer, creator, global_config, platform_config,
# authority, pool_state, base_mint, quote_mint, ...
LL_CREATOR, LL_PLATFORM, LL_BASE_MINT, LL_QUOTE_MINT = 1, 3, 6, 7
PLATFORM_CONFIG_DISC = bytes([160, 78, 128, 0, 248, 83, 230, 160])
PLATFORM_NAME_OFFSET = 8 + 8 + 32 + 32 + 8 * 4   # disc, epoch, fee wallet, nft wallet, 4 x u64; then name[64], web[256]
PLATFORM_FEE_WALLET_OFFSET = 16

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_INDEX = {c: i for i, c in enumerate(_B58)}


def b58encode(b):
    n, s = int.from_bytes(b, "big"), ""
    while n:
        n, r = divmod(n, 58)
        s = _B58[r] + s
    return "1" * (len(b) - len(b.lstrip(b"\0"))) + s


def b58decode(s):
    n = 0
    for c in s:
        n = n * 58 + _B58_INDEX[c]
    body = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    return b"\0" * (len(s) - len(s.lstrip("1"))) + body


class _Reader:
    def __init__(self, b, o=0):
        self.b, self.o = b, o

    def u8(self):
        v = self.b[self.o]
        self.o += 1
        return v

    def string(self, limit=1024):
        (n,) = struct.unpack_from("<I", self.b, self.o)
        if n > limit or self.o + 4 + n > len(self.b):
            raise ValueError("string out of range")
        v = self.b[self.o + 4:self.o + 4 + n].decode("utf-8", "replace")
        self.o += 4 + n
        return v

    def pubkey(self):
        if self.o + 32 > len(self.b):
            raise ValueError("pubkey out of range")
        v = b58encode(self.b[self.o:self.o + 32])
        self.o += 32
        return v


def pump_create_from_logs(logs):
    """Every CreateEvent in a pump.fun transaction's logs: dicts with name, symbol, uri, mint, user. Logs that are
    not valid base64 (the RPC truncates long logs) are skipped."""
    out = []
    for line in logs:
        if not line.startswith("Program data: "):
            continue
        try:
            b = base64.b64decode(line[14:], validate=True)
        except (binascii.Error, ValueError):
            continue
        if b[:8] != PUMP_CREATE_EVENT:
            continue
        try:
            r = _Reader(b, 8)
            name, symbol, uri, mint = r.string(), r.string(), r.string(), r.pubkey()
            r.pubkey()                       # bonding_curve
            user = r.pubkey()
        except (ValueError, struct.error):
            continue
        out.append({"name": name, "symbol": symbol, "uri": uri, "mint": mint, "creator": user})
    return out


def is_create_log(platform, logs):
    """True when a notification's logs show a create instruction of that program (a cheap pre-filter)."""
    if platform == "pump":
        return any(l in ("Program log: Instruction: Create", "Program log: Instruction: CreateV2") for l in logs)
    return any(l in ("Program log: Instruction: Initialize", "Program log: Instruction: InitializeV2",
                     "Program log: Instruction: InitializeWithToken2022") for l in logs)


def _account_keys(tx):
    msg = tx["transaction"]["message"]
    keys = list(msg["accountKeys"])
    loaded = (tx.get("meta") or {}).get("loadedAddresses") or {}
    return keys + list(loaded.get("writable", [])) + list(loaded.get("readonly", []))


def _instructions(tx):
    """Outer and inner instructions as (program_id, [account keys], data bytes)."""
    keys = _account_keys(tx)
    raw = list(tx["transaction"]["message"]["instructions"])
    for inner in (tx.get("meta") or {}).get("innerInstructions") or []:
        raw += inner["instructions"]
    for ix in raw:
        yield keys[ix["programIdIndex"]], [keys[i] for i in ix["accounts"]], b58decode(ix["data"])


def launches_from_tx(tx):
    """Every pump.fun or LaunchLab launch in a transaction fetched with getTransaction (encoding "json"), from the
    create instruction's own arguments. LaunchLab launches carry the platform_config account; the platform's
    declared name is looked up separately (`platform_config`)."""
    if tx is None or (tx.get("meta") or {}).get("err") is not None:
        return []
    out = []
    for program, accts, data in _instructions(tx):
        try:
            if program == PUMP and data[:8] in PUMP_IX:
                kind, user_ix = PUMP_IX[data[:8]]
                r = _Reader(data, 8)
                out.append({"platform": "pump", "ix": kind, "name": r.string(), "symbol": r.string(),
                            "uri": r.string(), "mint": accts[0], "creator": accts[user_ix]})
            elif program == LAUNCHLAB and data[:8] in LAUNCHLAB_IX:
                r = _Reader(data, 8)
                r.u8()                        # decimals
                out.append({"platform": "launchlab", "ix": LAUNCHLAB_IX[data[:8]], "name": r.string(),
                            "symbol": r.string(), "uri": r.string(), "mint": accts[LL_BASE_MINT],
                            "quote_mint": accts[LL_QUOTE_MINT], "creator": accts[LL_CREATOR],
                            "platform_config": accts[LL_PLATFORM]})
        except (ValueError, struct.error, IndexError):
            continue
    return out


def platform_config(data):
    """(declared name, declared website, fee wallet) of a LaunchLab PlatformConfig account, or None. The name and
    site are whatever the config's creator wrote: anyone can create a config named "StonkFun"."""
    if len(data) < PLATFORM_NAME_OFFSET + 320 or data[:8] != PLATFORM_CONFIG_DISC:
        return None
    o = PLATFORM_NAME_OFFSET
    clean = lambda b: b.split(b"\0", 1)[0].decode("utf-8", "replace").strip()  # noqa: E731
    return (clean(data[o:o + 64]), clean(data[o + 64:o + 320]),
            b58encode(data[PLATFORM_FEE_WALLET_OFFSET:PLATFORM_FEE_WALLET_OFFSET + 32]))


def platform_label(name, web):
    """Group a LaunchLab platform by its declared site, falling back to its declared name."""
    w = web.lower()
    for host, label in (("stonkfun.xyz", "StonkFun"), ("letsbonk.fun", "bonk.fun"), ("bonk.fun", "bonk.fun")):
        if host in w:
            return label
    return name or "LaunchLab (unnamed platform)"
