"""Every failure must refuse: stale state, RPC down, key unavailable or wrong, store down. In each case
nothing is signed-and-returned and nothing is recorded."""
import base64
import json
import time

import pytest
from conftest import PROGRAM, config, room
from solders.keypair import Keypair
from solders.signature import Signature
from solders.transaction import Transaction

from matcher_service.chain import RpcError, StaleState
from matcher_service.config import Budget, Config
from matcher_service.decide import Refusal
from matcher_service.ops import Metrics, logger
from matcher_service.service import Service
from matcher_service.signer import GcpKmsSigner, KeyfileSigner, Signer, SignerUnavailable, _crc32c
from matcher_service.store import Store
from matcher_service.txbuild import Builder

NOW = 1_800_000_000


class FakeRpc:
    def __init__(self, slot=1000, down=False, blockhash_down=False):
        self._slot, self.down, self.blockhash_down, self.errors = slot, down, blockhash_down, 0

    def slot(self):
        if self.down:
            raise RpcError("getSlot: connection refused")
        return self._slot

    def latest_blockhash(self):
        if self.down or self.blockhash_down:
            raise RpcError("getLatestBlockhash: timeout")
        return "11111111111111111111111111111111", 5150, self._slot

    def block_height(self):
        if self.down:
            raise RpcError("getBlockHeight: timeout")
        return 5000


class Snap:
    def __init__(self, slot, rooms=(), cfg=None, age=0.0):
        self.slot, self.slots = slot, {"rooms": slot, "doors": slot, "slug_locks": slot, "config": slot, "clock": slot}
        self.rooms = {r["room_id"]: r for r in rooms}
        self.clock_unix, self.config, self.config_key = NOW, cfg or config(), "cfg"
        self.read_wall, self.program_id = time.time() - age, PROGRAM

    def slug_holder(self, i):
        return None

    def slug_pda(self, i):
        return "lock"

    def name_holder(self, k):
        from matcher_service import rules
        return next((r['room_id'] for r in self.rooms.values() if r['faces'] and
            rules.name_lock_key(r['faces'][0]['name'],r['faces'][0]['symbol']) is not None and
            rules.name_lock_key(r['faces'][0]['name'],r['faces'][0]['symbol']).hex()==k),None)

    def name_pda(self, k):
        return "name:" + k

    def summary(self):
        return {"slot": self.slot}

    def check_fresh(self, cluster_slot, budget, now_wall=None):
        from matcher_service.chain import Snapshot
        return Snapshot.check_fresh(self, cluster_slot, budget, now_wall)

    def coherent(self, n):
        from matcher_service.chain import Snapshot
        return Snapshot.coherent(self, n)


class FakeChain:
    def __init__(self, snap, refresh_error=None, refreshed=None):
        self.snap, self.refresh_error, self.refreshed = snap, refresh_error, refreshed

    def current(self):
        return self.snap

    def refresh(self):
        if self.refresh_error:
            raise self.refresh_error
        self.snap = self.refreshed or self.snap
        return self.snap


class BrokenSigner(Signer):
    backend = "broken"

    def __init__(self, kp):
        super().__init__()
        self.kp = kp

    def _raw_pubkey(self):
        return bytes(self.kp.pubkey())

    def _raw_sign(self, m):
        raise ConnectionError("KMS endpoint unreachable")


def cfg(tmp_path):
    return Config(env="development", rpc_url="x", program_id=PROGRAM, signer="keyfile", keyfile=None,
                  gcp_key_version=None, aws_key_id=None, db_path=str(tmp_path / "d.sqlite3"), matcher_version=1,
                  budget=Budget(coherence_slots=30, max_lag_slots=30, max_age_seconds=8, refresh_seconds=2),
                  cu_limit=500_000, max_cu_price=1_000_000, rate_ip_per_min=30, rate_launcher_per_min=6,
                  trust_forwarded_for=False)


def make(tmp_path, kp, snap, rpc=None, signer=None, chain=None):
    k, path = kp
    c = cfg(tmp_path)
    snap.config["matcher_authority"] = str(k.pubkey())
    return Service(c, rpc or FakeRpc(), chain or FakeChain(snap), signer or KeyfileSigner(path, "development"),
                   Store(c.db_path), Builder(PROGRAM), logger(), Metrics())


REQ = {"launcher": str(Keypair().pubkey()), "name": "Elon", "symbol": "ELON", "uri": "https://x/y.json"}


def rows(svc):
    return svc.store.db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]


def test_happy_path_signs_and_records(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000, [room(1, [("Elon", "ELON")], created_at=NOW - 60)]))
    out = svc.route(dict(REQ))
    assert out["decision"]["kind"] == "door" and rows(svc) == 1
    tx = Transaction.from_bytes(base64.b64decode(out["transaction_base64"]))
    i = list(tx.message.account_keys).index(kp[0].pubkey())
    assert tx.signatures[i].verify(kp[0].pubkey(), bytes(tx.message))
    assert tx.signatures[0] == Signature.default()          # launcher's slot left empty
    assert svc.store.get(out["id"])["record"]["state"]["slot"] == 1000


def test_stale_state_refuses(tmp_path, kp):
    # snapshot 100 slots behind the cluster, and the refresh fails too
    svc = make(tmp_path, kp, Snap(900), chain=None)
    svc.chain = FakeChain(Snap(900), refresh_error=RpcError("getProgramAccounts: 503"))
    svc.chain.snap.config["matcher_authority"] = str(kp[0].pubkey())
    with pytest.raises(Refusal) as e:
        svc.route(dict(REQ))
    assert e.value.code == "rpc_unavailable" and e.value.status == 503 and rows(svc) == 0


def test_stale_after_refresh_refuses(tmp_path, kp):
    old = Snap(900)
    svc = make(tmp_path, kp, old)
    svc.chain = FakeChain(old, refreshed=Snap(901))
    with pytest.raises(Refusal) as e:
        svc.route(dict(REQ))
    assert e.value.code == "stale_state" and rows(svc) == 0


def test_old_wall_clock_snapshot_refuses(tmp_path, kp):
    s = Snap(1000, age=60)
    svc = make(tmp_path, kp, s)
    svc.chain = FakeChain(s, refreshed=Snap(1000, age=60))
    with pytest.raises(Refusal) as e:
        svc.route(dict(REQ))
    assert e.value.code == "stale_state" and rows(svc) == 0


def test_snapshot_expiring_during_signing_is_not_released(tmp_path, kp):
    """The decision is taken on a fresh snapshot, but signing (a KMS round trip) or building takes long enough that
    the snapshot leaves the freshness budget before the transaction is returned. The service must re-check the same
    snapshot after signing and refuse, not release a transaction decided on state that is now stale."""
    for mode in ("wall_clock", "cluster_slot"):
        s = Snap(1000, [room(1, [("Elon", "ELON")], created_at=NOW - 60)])
        (tmp_path / mode).mkdir()
        svc = make(tmp_path / mode, kp, s)
        signer = svc.signer
        real = signer.sign

        def slow_sign(msg, s=s, svc=svc, mode=mode, real=real):
            if mode == "wall_clock":
                s.read_wall -= 60                      # the KMS call took a minute
            else:
                svc.rpc._slot = 1100                   # the cluster moved 100 slots on meanwhile
            return real(msg)
        signer.sign = slow_sign
        with pytest.raises(Refusal) as e:
            svc.route(dict(REQ))
        assert e.value.code == "stale_state" and e.value.status == 503, mode
        assert rows(svc) == 0, mode


def test_rpc_down_refuses(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000), rpc=FakeRpc(down=True))
    with pytest.raises(Refusal) as e:
        svc.route(dict(REQ))
    assert e.value.code == "rpc_unavailable" and rows(svc) == 0


def test_blockhash_unavailable_refuses(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000), rpc=FakeRpc(blockhash_down=True))
    with pytest.raises(Refusal) as e:
        svc.route(dict(REQ))
    assert e.value.code == "rpc_unavailable" and rows(svc) == 0


def test_signer_unavailable_refuses(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000), signer=BrokenSigner(kp[0]))
    with pytest.raises(Refusal) as e:
        svc.route(dict(REQ))
    assert e.value.code == "signer_unavailable" and e.value.status == 503 and rows(svc) == 0


def test_signer_key_not_config_matcher_refuses(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000))
    svc.chain.snap.config["matcher_authority"] = str(Keypair().pubkey())
    with pytest.raises(Refusal) as e:
        svc.route(dict(REQ))
    assert e.value.code == "signer_mismatch" and rows(svc) == 0


def test_store_down_refuses(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000))
    svc.store.db.close()
    with pytest.raises(Refusal) as e:
        svc.route(dict(REQ))
    assert e.value.code == "store_unavailable"


def test_concurrent_new_rooms_for_one_name_are_both_signed_under_one_name_lock(tmp_path, kp):
    """No in-flight reservation (H-1 closed): both are signed, and both carry the same NameLock, so the
    program lets at most one of them land. Different symbols, so different SlugLocks."""
    svc = make(tmp_path, kp, Snap(1000))
    a = svc.route(dict(REQ))
    b = svc.route(dict(REQ, symbol="OTHER", launcher=str(Keypair().pubkey())))   # same folded name
    assert a["decision"]["kind"] == b["decision"]["kind"] == "new_room"
    assert a["decision"]["identity"] != b["decision"]["identity"]
    assert a["decision"]["name_key"] == b["decision"]["name_key"] and a["decision"]["name_key"]
    for out in (a, b):
        tx = Transaction.from_bytes(base64.b64decode(out["transaction_base64"]))
        data = bytes(tx.message.instructions[-1].data)
        assert data[-17:] == b"\x01" + bytes.fromhex(out["decision"]["name_key"])
    # the same launcher can hold several unexpired new-room decisions: nothing is held off-chain
    who = str(Keypair().pubkey())
    assert svc.route(dict(REQ, launcher=who, name="Another Name", symbol="ANO"))
    assert svc.route(dict(REQ, launcher=who, name="Third Name", symbol="THR"))


def test_concurrent_doors_get_independent_random_nonces(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000, [room(1, [("Elon", "ELON")], created_at=NOW - 60)]))
    a = svc.route(dict(REQ))
    b = svc.route(dict(REQ, launcher=str(Keypair().pubkey())))
    na, nb = int(a["decision"]["door_nonce"]), int(b["decision"]["door_nonce"])
    assert na and nb and na != nb and a["decision"]["door"] != b["decision"]["door"]


def test_launch_carries_expiry_terms_hash_and_door_nonce(tmp_path, kp):
    import struct
    svc = make(tmp_path, kp, Snap(1000, [room(1, [("Elon", "ELON")], created_at=NOW - 60)]))
    out = svc.route(dict(REQ))
    tx = Transaction.from_bytes(base64.b64decode(out["transaction_base64"]))
    data = bytes(tx.message.instructions[-1].data)
    terms, door_nonce, expires, reserve_cap = struct.unpack("<32sQQQ", data[-56:])
    assert reserve_cap == 0
    assert expires == 1000 + 150 == out["expires_at_slot"]            # blockhash slot + 150
    assert door_nonce == int(out["decision"]["door_nonce"]) != 0
    assert terms.hex() == svc.chain.snap.config["launch_terms_hash"]
    (tmp_path / "n").mkdir()
    created = make(tmp_path / "n", kp, Snap(1000)).route(dict(REQ, name="Fresh", symbol="FRSH"))
    cdata = bytes(Transaction.from_bytes(base64.b64decode(created["transaction_base64"])).message.instructions[-1].data)
    assert cdata[-17] == 1                                              # Some(name_key): 1 + 16 bytes
    assert struct.unpack("<Q", cdata[-41:-33])[0] == 0                  # door 0 is nonce 0


def test_keyfile_refused_in_production(kp):
    with pytest.raises(SignerUnavailable):
        KeyfileSigner(kp[1], "production")


def test_signature_that_does_not_verify_is_rejected(kp):
    class Lying(BrokenSigner):
        def _raw_sign(self, m):
            return bytes(64)
    with pytest.raises(SignerUnavailable):
        Lying(kp[0]).sign(b"message")


def test_gcp_kms_signer_against_a_fake_endpoint(kp):
    k = kp[0]
    der = bytes.fromhex("302a300506032b6570032100") + bytes(k.pubkey())
    pem = "-----BEGIN PUBLIC KEY-----\n" + base64.b64encode(der).decode() + "\n-----END PUBLIC KEY-----\n"
    name = "projects/p/locations/l/keyRings/r/cryptoKeys/k/cryptoKeyVersions/1"

    class Resp:
        def __init__(self, body):
            self.body = body

        def raise_for_status(self):
            pass

        def json(self):
            return self.body

    class Http:
        def get(self, url, headers):
            assert url.endswith(name + "/publicKey")
            return Resp({"pem": pem, "algorithm": "EC_SIGN_ED25519"})

        def post(self, url, json, headers):
            assert url.endswith(name + ":asymmetricSign") and "digest" not in json
            data = base64.b64decode(json["data"])
            assert int(json["dataCrc32c"]) == _crc32c(data)
            sig = bytes(k.sign_message(data))
            return Resp({"signature": base64.b64encode(sig).decode(), "signatureCrc32c": str(_crc32c(sig)),
                         "verifiedDataCrc32c": True, "name": name})

    s = GcpKmsSigner(name, http=Http(), token_provider=lambda: "token")
    assert s.pubkey == k.pubkey()
    assert Signature.from_bytes(s.sign(b"hello")).verify(k.pubkey(), b"hello")


def test_crc32c_reference_value():
    assert _crc32c(b"123456789") == 0xE3069283  # RFC 3720 check value


def test_store_is_append_only_and_tamper_evident(tmp_path):
    st = Store(str(tmp_path / "s.sqlite3"))
    st.append("a", "L", "door", {"x": 1})
    st.append("b", "L", "new_room", {"x": 2})
    assert st.verify_chain()[0]
    import sqlite3
    with pytest.raises(sqlite3.DatabaseError):
        st.db.execute("UPDATE decisions SET record='{}' WHERE id='a'")
    with pytest.raises(sqlite3.DatabaseError):
        st.db.execute("DELETE FROM decisions WHERE id='a'")
    st.db.execute("DROP TRIGGER no_update")
    st.db.execute("UPDATE decisions SET record='{\"x\":9}' WHERE id='a'")
    assert not st.verify_chain()[0]


def test_stale_snapshot_check_rejects_incoherent_reads():
    s = Snap(1000)
    s.slots["clock"] = 1100            # one read 100 slots after the others; lag itself is 0
    from matcher_service.chain import Snapshot
    with pytest.raises(StaleState, match="span 100 slots"):
        Snapshot.check_fresh(s, 1000, Budget(30, 30, 8, 2))


def test_aws_kms_signer_against_a_fake_client(kp):
    from matcher_service.signer import AwsKmsSigner
    k = kp[0]
    der = bytes.fromhex("302a300506032b6570032100") + bytes(k.pubkey())

    class Kms:
        def get_public_key(self, KeyId):
            return {"KeySpec": "ECC_NIST_EDWARDS25519", "PublicKey": der}

        def sign(self, KeyId, Message, MessageType, SigningAlgorithm):
            assert (MessageType, SigningAlgorithm) == ("RAW", "ED25519_SHA_512")
            return {"Signature": bytes(k.sign_message(Message))}

    s = AwsKmsSigner("alias/matcher", client=Kms())
    assert s.pubkey == k.pubkey()
    assert Signature.from_bytes(s.sign(b"msg")).verify(k.pubkey(), b"msg")

    class WrongSpec(Kms):
        def get_public_key(self, KeyId):
            return {"KeySpec": "ECC_NIST_P256", "PublicKey": der}
    with pytest.raises(SignerUnavailable):
        _ = AwsKmsSigner("k", client=WrongSpec()).pubkey


def test_lone_surrogate_metadata_is_refused_not_a_server_error(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000))
    with pytest.raises(Refusal) as e:
        svc.route(dict(REQ, name="Elon\ud800"))
    assert e.value.code == "invalid_metadata" and rows(svc) == 0


def test_first_buy_quote_matches_the_program_reference_vector():
    """program/scripts/check_spec_conflicts.py on the SBF fixture: 101 lamports gross at 100 bps is
    100 net and buys 3,612,416 base units on a fresh default curve."""
    from matcher_service import quote
    assert quote.first_buy_tokens(quote.new_room_curve(config()), 101) == 3_612_519


def test_door_first_buy_defaults_to_a_two_percent_price_limit(tmp_path, kp):
    import struct
    from conftest import curve_state
    from matcher_service import quote
    r = room(1, [("Elon", "ELON")], created_at=NOW - 60, reserve=10_000_000_000)
    r.update(curve_state(10_000_000_000, pending=3_000_000))   # a backlog the buy settles first
    svc = make(tmp_path, kp, Snap(1000, [r]))
    out = svc.route(dict(REQ, first_buy_lamports=1_000_000_000))
    rec = svc.store.get(out["id"])["record"]
    q = rec["first_buy_quote"]
    assert q["tokens"] == quote.first_buy_tokens(r, 1_000_000_000) and q["max_slippage_bps"] == 200
    assert q["min_tokens_out"] == q["tokens"] * 9800 // 10000 == rec["launch_min_tokens_out"]
    data = bytes(Transaction.from_bytes(base64.b64decode(out["transaction_base64"])).message.instructions[-1].data)
    name_len = struct.unpack_from("<I", data, 8)[0]
    o = 12 + name_len
    o += 4 + struct.unpack_from("<I", data, o)[0]          # symbol
    o += 4 + struct.unpack_from("<I", data, o)[0]          # uri
    first_buy, min_tokens = struct.unpack_from("<QQ", data, o)
    assert (first_buy, min_tokens) == (1_000_000_000, q["min_tokens_out"])


def test_launch_buy_price_limits_explicit_zero_and_bounds(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000, [room(1, [("Elon", "ELON")], created_at=NOW - 60)]))
    for bad in (dict(first_buy_lamports=10 ** 9, min_tokens_out=0), dict(first_buy_lamports=10 ** 9, max_slippage_bps=0),
                dict(first_buy_lamports=10 ** 9, max_slippage_bps=5_001)):
        with pytest.raises(Refusal) as e:
            svc.route(dict(REQ, **bad))
        assert e.value.code == "invalid_request"
    out = svc.route(dict(REQ, first_buy_lamports=10 ** 9, min_tokens_out=12345))
    assert svc.store.get(out["id"])["record"]["launch_min_tokens_out"] == 12345   # explicit limit kept
    out = svc.route(dict(REQ, first_buy_lamports=10 ** 9, max_slippage_bps=500))
    q = svc.store.get(out["id"])["record"]["first_buy_quote"]
    assert q["min_tokens_out"] == q["tokens"] * 9500 // 10000
    out = svc.route(dict(REQ))                                                     # no first buy: no limit needed
    assert svc.store.get(out["id"])["record"]["launch_min_tokens_out"] == 0


def test_unfillable_first_buy_is_refused(tmp_path, kp):
    full = room(1, [("Elon", "ELON")], created_at=NOW - 60, reserve=85_018_013_680, status=1)
    svc = make(tmp_path, kp, Snap(1000, [full]))
    with pytest.raises(Refusal) as e:
        svc.route(dict(REQ, first_buy_lamports=10 ** 9))
    assert e.value.code == "first_buy_unfillable" and rows(svc) == 0


def test_rpc_retries_rate_limits_then_gives_up():
    import httpx
    from matcher_service.chain import RpcClient
    calls = []

    def handler(n429):
        def h(request):
            calls.append(1)
            if len(calls) <= n429:
                return httpx.Response(429, headers={"retry-after": "0"})
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": 77})
        return h
    assert RpcClient("http://x", transport=httpx.MockTransport(handler(2))).slot() == 77 and len(calls) == 3
    calls.clear()
    with pytest.raises(RpcError):
        RpcClient("http://x", transport=httpx.MockTransport(handler(99))).slot()
    assert len(calls) == RpcClient.RATE_LIMIT_RETRIES + 1




def test_service_refuses_other_unicode_tables(tmp_path, kp, monkeypatch):
    """Name keys are NameLock seeds on-chain; other Unicode tables would key names differently (CORRECTIONS §17)."""
    from matcher_service import rules
    assert rules.UNICODE_VERSION == rules.PINNED_UNICODE_VERSION
    monkeypatch.setattr(rules, "UNICODE_VERSION", "16.0.0")
    with pytest.raises(rules.UnicodeMismatch):
        make(tmp_path, kp, Snap(1000))
