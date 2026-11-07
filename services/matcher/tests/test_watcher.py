"""The launch watcher (watcher/): decoders against real mainnet data captured 7 November 2026, constants against the
programs' own IDLs, and the shadow matcher."""
import base64
import hashlib
import json

from conftest import SERVICE

from watcher import decode as D
from watcher.shadow import Shadow

FIX = SERVICE / "tests/fixtures/watcher"


def load(name):
    return json.loads((FIX / name).read_text())


def test_constants_match_the_onchain_idls():
    pump = json.loads((SERVICE / "watcher/idl/pump.json").read_text())
    ll = json.loads((SERVICE / "watcher/idl/raydium_launchpad.json").read_text())
    ix = lambda j, n: bytes(next(i for i in j["instructions"] if i["name"] == n)["discriminator"])  # noqa: E731
    acc = lambda j, n: [a["name"] for a in next(i for i in j["instructions"] if i["name"] == n)["accounts"]]  # noqa: E731
    assert bytes(next(e for e in pump["events"] if e["name"] == "CreateEvent")["discriminator"]) == D.PUMP_CREATE_EVENT
    for disc, (name, user_ix) in D.PUMP_IX.items():
        assert ix(pump, name) == disc and acc(pump, name)[user_ix] == "user" and acc(pump, name)[0] == "mint"
    for disc, name in D.LAUNCHLAB_IX.items():
        a = acc(ll, name)
        assert ix(ll, name) == disc
        assert (a[D.LL_CREATOR], a[D.LL_PLATFORM], a[D.LL_BASE_MINT], a[D.LL_QUOTE_MINT]) == \
            ("creator", "platform_config", "base_mint", "quote_mint")
    assert bytes(next(a for a in ll["accounts"] if a["name"] == "PlatformConfig")["discriminator"]) == D.PLATFORM_CONFIG_DISC
    pc = next(t for t in ll["types"] if t["name"] == "PlatformConfig")["type"]["fields"]
    assert [f["name"] for f in pc[:9]] == ["epoch", "platform_fee_wallet", "platform_nft_wallet", "platform_scale",
                                          "creator_scale", "burn_scale", "fee_rate", "name", "web"]
    assert D.PLATFORM_CONFIG_DISC == hashlib.sha256(b"account:PlatformConfig").digest()[:8]


def test_base58_round_trip():
    for s in ("11111111111111111111111111111111", D.PUMP, D.LAUNCHLAB, "1"):
        assert D.b58encode(D.b58decode(s)) == s


def test_pump_launch_decodes_from_logs_and_from_the_transaction_alike():
    v = load("pump_create_notification.json")
    assert D.is_create_log("pump", v["logs"])
    from_logs = D.pump_create_from_logs(v["logs"])
    from_tx = D.launches_from_tx(load("pump_create_tx.json"))
    assert len(from_logs) == len(from_tx) == 1
    assert from_logs[0]["name"] == "Pepe Wif Sword" and from_logs[0]["symbol"] == "SwordPepe"
    for k in ("name", "symbol", "uri", "mint", "creator"):
        assert from_logs[0][k] == from_tx[0][k], k
    assert from_tx[0]["mint"].endswith("pump")


def test_truncated_or_foreign_log_lines_are_skipped():
    assert D.pump_create_from_logs(["Program data: abc", "Program data: !!!", "Program log: x"]) == []
    bad = base64.b64encode(D.PUMP_CREATE_EVENT + b"\xff\xff\xff\x7f").decode()
    assert D.pump_create_from_logs(["Program data: " + bad]) == []


def test_launchlab_launches_decode_with_their_platform_config():
    want = {0: ("FloatFuse", "FUSE", "initialize_with_token_2022", "Bnfzaj33ZHHGhp256Nr496ucJ4CNsQDU2KeDCtAFkDSV"),
            1: ("Stonk Market Meme Man", "STMEMEMAN", "initialize_with_token_2022",
                "A4WcA9u1hivjeL1CaJU4oZtRRL8j7rLu4xVfZWGAWKex"),
            2: ("a gently discontinued cybertruck", "cybertruck", "initialize_v2",
                "2TDPJJPV6nvTEqXABxrqno6Uzpipxxvh1zjLN3SMYn69"),
            3: ("MoonGoat", "MGOAT", "initialize_with_token_2022", "Bnfzaj33ZHHGhp256Nr496ucJ4CNsQDU2KeDCtAFkDSV")}
    for i, (name, symbol, ix, cfg) in want.items():
        (got,) = D.launches_from_tx(load(f"launchlab_create_{i}_tx.json"))
        assert (got["name"], got["symbol"], got["ix"], got["platform_config"]) == (name, symbol, ix, cfg)
        assert got["platform"] == "launchlab" and got["mint"] and got["quote_mint"]


def test_failed_transactions_yield_nothing():
    tx = load("pump_create_tx.json")
    tx["meta"]["err"] = {"InstructionError": [0, "Custom"]}
    assert D.launches_from_tx(tx) == [] and D.launches_from_tx(None) == []


def test_platform_config_and_labels():
    data = bytearray(D.PLATFORM_NAME_OFFSET + 320 + 64)
    data[:8] = D.PLATFORM_CONFIG_DISC
    data[D.PLATFORM_NAME_OFFSET:D.PLATFORM_NAME_OFFSET + 8] = b"StonkFun"
    w = b"https://www.stonkfun.xyz"
    data[D.PLATFORM_NAME_OFFSET + 64:D.PLATFORM_NAME_OFFSET + 64 + len(w)] = w
    name, web, _ = D.platform_config(bytes(data))
    assert (name, web) == ("StonkFun", "https://www.stonkfun.xyz") and D.platform_label(name, web) == "StonkFun"
    assert D.platform_label("letsbonk.fun", "https://letsbonk.fun/") == "bonk.fun"
    assert D.platform_label("pump2", "https://pump2.lol") == "pump2"
    assert D.platform_config(b"\0" * 400) is None


def test_shadow_routes_by_the_live_name_key():
    s = Shadow()
    L = lambda n, sym, p="pump.fun", c="w1": {"name": n, "symbol": sym, "platform": p, "creator": c, "ts": 1}  # noqa: E731
    assert s.route(L("Pepe Wif Sword", "SwordPepe"))["decision"] == "new_room"
    d = s.route(L("pepe wif sword", "PWS", "StonkFun", "w2"))
    assert d["decision"] == "door" and d["tier"] == "T2n" and d["door0"]["name"] == "Pepe Wif Sword"
    assert d["same_creator_as_door0"] is False
    assert s.route(L("Pepe Wif Sword", "SwordPepe"))["same_creator_as_door0"] is True
    assert s.route(L("ᴘᴇᴘᴇ ᴡɪꜰ ꜱᴡᴏʀᴅ", "X"))["decision"] == "door"          # rule C
    assert s.route(L("🚀🚀", "X"))["decision"] == "no_key"
    assert s.route(L("Pepe Wif Swords", "X"))["decision"] == "new_room"         # a typo still escapes
    assert s.rooms[0]["doors"] == 3 and s.rooms[0]["platforms"]["StonkFun"] == 1
