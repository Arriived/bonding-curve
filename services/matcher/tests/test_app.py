"""HTTP layer: signed requests, rate limits, health readiness, metrics, decision lookup."""
import time
from conftest import room
from fastapi.testclient import TestClient
from solders.keypair import Keypair
from test_failures import NOW, FakeRpc, Snap, make

from matcher_service import auth
from matcher_service.app import create_app
from matcher_service.ops import RateLimiter


def client(svc):
    return TestClient(create_app(svc, start_refresher=False))


def signed(body, kp=None, **over):
    """A /route body signed by `kp` (a fresh keypair by default), as a launcher's wallet would sign it."""
    kp = kp or Keypair()
    return auth.sign(kp, dict(body, launcher=str(kp.pubkey()), **over))


def test_route_and_decision_lookup(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000, [room(1, [("Elon", "ELON")], created_at=NOW - 60)]))
    c = client(svc)
    r = c.post("/route", json=signed({"name": "Elon", "symbol": "ELON", "uri": ""}))
    assert r.status_code == 200, r.text
    got = c.get(f"/decision/{r.json()['id']}")
    assert got.status_code == 200 and got.json()["record"]["decision"]["room_id"] == "1"
    assert c.get("/decision/nope").status_code == 404


def test_refusals_are_structured(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000), rpc=FakeRpc(down=True))
    r = client(svc).post("/route", json=signed({"name": "A", "symbol": "A"}))
    assert r.status_code == 503 and r.json()["error"] == "rpc_unavailable" and r.headers["retry-after"]
    r = client(svc).post("/route", json={"launcher": "not-a-key", "name": "A", "symbol": "A"})
    assert r.status_code == 422 and r.json()["error"] == "invalid_request"


def test_rate_limit_per_launcher(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000, [room(1, [("Elon", "ELON")], created_at=NOW - 60)]))
    c = client(svc)
    who = Keypair()
    now = int(time.time())
    codes = [c.post("/route", json=signed({"name": "Elon", "symbol": "ELON"}, who, issued_at=now - i)).status_code
             for i in range(svc.cfg.rate_launcher_per_min + 1)]
    assert codes[-1] == 429 and codes[0] == 200


def test_rate_limiter_refills():
    rl = RateLimiter(60)  # one per second
    assert all(rl.allow("k", now=0.0) for _ in range(60))
    assert not rl.allow("k", now=0.0)
    assert rl.allow("k", now=1.01)


def test_rate_limit_per_ip(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000))
    c = client(svc)
    codes = [c.post("/route", json=signed({"name": f"N{i}xyz", "symbol": "S"})).status_code
             for i in range(svc.cfg.rate_ip_per_min + 1)]
    assert codes[-1] == 429


def test_health_reports_unready_on_key_mismatch(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000))
    c = client(svc)
    assert c.get("/health").status_code == 200
    svc.chain.snap.config["matcher_authority"] = str(Keypair().pubkey())
    h = c.get("/health")
    assert h.status_code == 503 and "matcher_authority" in h.json()["reason"]


def test_health_unready_when_stale(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(900))
    assert client(svc).get("/health").status_code == 503


def test_metrics_count_decisions_and_refusals(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000, [room(1, [("Elon", "ELON")], created_at=NOW - 60)]))
    c = client(svc)
    c.post("/route", json=signed({"name": "Elon", "symbol": "ELON"}))
    c.post("/route", json=signed({"name": "", "symbol": "X"}))
    m = c.get("/metrics").text
    assert 'matcher_decisions_total{kind="door",rule="T3"} 1' in m
    assert 'matcher_refusals_total{code="invalid_metadata"} 1' in m
    assert "matcher_route_seconds_count 2" in m


def test_lone_surrogate_over_http_is_a_structured_refusal(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000))
    body = '{"launcher": "%s", "name": "A\\ud800", "symbol": "A"}' % Keypair().pubkey()
    r = client(svc).post("/route", content=body, headers={"content-type": "application/json"})
    assert r.status_code == 422 and r.json()["error"] == "invalid_metadata"


def test_oversized_body_and_launcher_are_refused_before_use(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000))
    c = client(svc)
    r = c.post("/route", json={"launcher": "x" * 20_000, "name": "A", "symbol": "A"})
    assert r.status_code == 413 and r.json()["error"] == "request_too_large"
    r = c.post("/route", json={"launcher": "x" * 2_000, "name": "A", "symbol": "A"})
    assert r.status_code == 422 and r.json()["error"] == "invalid_request"


def test_spoofed_forwarded_for_entries_do_not_evade_the_ip_limit(tmp_path, kp, monkeypatch):
    # A slow machine can refill this token bucket while constructing 31 launches.
    # Keep the limiter's own clock fixed to test the intended single burst.
    allow = RateLimiter.allow
    monkeypatch.setattr(RateLimiter, "allow", lambda limiter, key, now=None: allow(limiter, key, now=1000.0))
    svc = make(tmp_path, kp, Snap(1000))
    import dataclasses
    svc.cfg = dataclasses.replace(svc.cfg, trust_forwarded_for=True, forwarded_hops=1)
    c = client(svc)
    codes = [c.post("/route", headers={"x-forwarded-for": f"10.0.0.{i}, 203.0.113.7"},
                    json=signed({"name": f"N{i}xyz", "symbol": "S"})).status_code
             for i in range(svc.cfg.rate_ip_per_min + 1)]
    assert codes[-1] == 429          # keyed on the proxy-appended 203.0.113.7, not the spoofed prefix


def test_route_requires_a_fresh_single_use_signature_by_the_launcher(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000, [room(1, [("Elon", "ELON")], created_at=NOW - 60)]))
    c = client(svc)
    me, other = Keypair(), Keypair()
    body = {"name": "Elon", "symbol": "ELON"}
    cases = {
        "unsigned": dict(body, launcher=str(me.pubkey()), issued_at=int(time.time())),
        "signed by another key": dict(signed(body, other), launcher=str(me.pubkey())),
        "changed after signing": dict(signed(body, me), name="Elon2"),
        "stale": signed(body, me, issued_at=int(time.time()) - 600),
    }
    for label, b in cases.items():
        r = c.post("/route", json=b)
        assert r.status_code == 401 and r.json()["error"] == "unauthenticated", label
    good = signed(body, me)
    assert c.post("/route", json=good).status_code == 200
    r = c.post("/route", json=good)                                   # replay of the same signed request
    assert r.status_code == 401 and "already used" in r.json()["message"]
    r = c.post("/route", json=dict(signed(body, me), extra_unsigned_field=1))
    assert r.status_code == 422 and r.json()["error"] == "invalid_request"


def test_a_victims_launcher_limit_cannot_be_spent_by_someone_else(tmp_path, kp):
    """M-3: requests naming the victim's key without its signature are refused before the limiter."""
    svc = make(tmp_path, kp, Snap(1000, [room(1, [("Elon", "ELON")], created_at=NOW - 60)]))
    c = client(svc)
    victim = Keypair()
    for i in range(svc.cfg.rate_launcher_per_min * 3):
        forged = dict(signed({"name": "Elon", "symbol": "ELON"}, Keypair()), launcher=str(victim.pubkey()))
        assert c.post("/route", json=forged).status_code == 401
    assert c.post("/route", json=signed({"name": "Elon", "symbol": "ELON"}, victim)).status_code == 200
