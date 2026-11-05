"""HTTP layer: rate limits, health readiness, metrics, decision lookup."""
from conftest import room
from fastapi.testclient import TestClient
from solders.keypair import Keypair
from test_failures import NOW, FakeRpc, Snap, make

from matcher_service.app import create_app
from matcher_service.ops import RateLimiter


def client(svc):
    return TestClient(create_app(svc, start_refresher=False))


def test_route_and_decision_lookup(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000, [room(1, [("Elon", "ELON")], created_at=NOW - 60)]))
    c = client(svc)
    r = c.post("/route", json={"launcher": str(Keypair().pubkey()), "name": "Elon", "symbol": "ELON", "uri": ""})
    assert r.status_code == 200, r.text
    got = c.get(f"/decision/{r.json()['id']}")
    assert got.status_code == 200 and got.json()["record"]["decision"]["room_id"] == "1"
    assert c.get("/decision/nope").status_code == 404


def test_refusals_are_structured(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000), rpc=FakeRpc(down=True))
    r = client(svc).post("/route", json={"launcher": str(Keypair().pubkey()), "name": "A", "symbol": "A"})
    assert r.status_code == 503 and r.json()["error"] == "rpc_unavailable" and r.headers["retry-after"]
    r = client(svc).post("/route", json={"launcher": "not-a-key", "name": "A", "symbol": "A"})
    assert r.status_code == 422 and r.json()["error"] == "invalid_request"


def test_rate_limit_per_launcher(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000, [room(1, [("Elon", "ELON")], created_at=NOW - 60)]))
    c = client(svc)
    who = str(Keypair().pubkey())
    codes = [c.post("/route", json={"launcher": who, "name": "Elon", "symbol": "ELON"}).status_code
             for _ in range(svc.cfg.rate_launcher_per_min + 1)]
    assert codes[-1] == 429 and codes[0] == 200


def test_rate_limiter_refills():
    rl = RateLimiter(60)  # one per second
    assert all(rl.allow("k", now=0.0) for _ in range(60))
    assert not rl.allow("k", now=0.0)
    assert rl.allow("k", now=1.01)


def test_rate_limit_per_ip(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000))
    c = client(svc)
    codes = [c.post("/route", json={"launcher": str(Keypair().pubkey()), "name": f"N{i}xyz", "symbol": "S"}).status_code
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
    c.post("/route", json={"launcher": str(Keypair().pubkey()), "name": "Elon", "symbol": "ELON"})
    c.post("/route", json={"launcher": str(Keypair().pubkey()), "name": "", "symbol": "X"})
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


def test_spoofed_forwarded_for_entries_do_not_evade_the_ip_limit(tmp_path, kp):
    svc = make(tmp_path, kp, Snap(1000))
    import dataclasses
    svc.cfg = dataclasses.replace(svc.cfg, trust_forwarded_for=True, forwarded_hops=1)
    c = client(svc)
    codes = [c.post("/route", headers={"x-forwarded-for": f"10.0.0.{i}, 203.0.113.7"},
                    json={"launcher": str(Keypair().pubkey()), "name": f"N{i}xyz", "symbol": "S"}).status_code
             for i in range(svc.cfg.rate_ip_per_min + 1)]
    assert codes[-1] == 429          # keyed on the proxy-appended 203.0.113.7, not the spoofed prefix
