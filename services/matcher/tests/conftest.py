import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest
from solders.keypair import Keypair

HERE = Path(__file__).resolve().parent
SERVICE = HERE.parent
REPO = SERVICE.parent.parent
sys.path.insert(0, str(SERVICE))

RESEARCH = REPO / "research/doors_into_one_room/scripts/narrative"
EXAMPLES = RESEARCH / "examples"


def research_matcher():
    """The research matcher module itself, loaded from its file (the reference the service ports)."""
    spec = importlib.util.spec_from_file_location("research_matcher", RESEARCH / "matcher.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_examples():
    out = []
    for f in sorted(os.listdir(EXAMPLES)):
        if f.endswith(".json"):
            out.append((f[:-5], json.load(open(EXAMPLES / f, encoding="utf-8"))))
    return out


PROGRAM = "D7YsLsiJXoAF38vCUhFqYStepvSz6goG7EddHDe5NVJG"
MATCHER = "5Bb2HVR9XeTeNBeM28W2ecdKcwycwPMJqGXmcWtuRrCN"


def config(**over):
    c = {"paused": False, "matcher_authority": MATCHER, "room_fee_lamports": 0, "door_fee_lamports": 0,
         "live_min_reserve_lamports": 500_000_000, "live_max_idle_seconds": 21_600,
         "live_new_seconds": 3_600, "live_min_volume_lamports": 5_000_000_000,
         "launch_terms_hash": "ab" * 32}
    c.update(over)
    return c


class FakeSnapshot:
    """The parts of chain.Snapshot that decide() reads."""

    def __init__(self, rooms, now, cfg=None, locks=None):
        self.rooms = {r["room_id"]: r for r in rooms}
        self.clock_unix = now
        self.config = cfg or config()
        self.locks = locks or {}  # identity hex -> holder room_id
        self.program_id = PROGRAM

    def slug_holder(self, identity_hex):
        return self.locks.get(identity_hex)

    def slug_pda(self, identity_hex):
        return "lock:" + identity_hex


def room(room_id, faces, created_at=0, reserve=10_000_000_000, last_trade_at=None, buckets=None, status=0,
         door_count=None):
    """A room dict in the service's decoded form; faces as (name, symbol) pairs."""
    return {"room_id": room_id, "pubkey": f"room{room_id}", "status": status, "created_at": created_at,
            "reserve": reserve, "last_trade_at": created_at if last_trade_at is None else last_trade_at,
            "buckets": buckets or [], "faces": [{"name": n, "symbol": s} for n, s in faces],
            "door_count": len(faces) if door_count is None else door_count, "volume_gross": 0,
            "identity": "", "room_mint": ""}


def snapshot_from_example(inp):
    """Map a research example's input onto the service's snapshot form."""
    p = dict(research_matcher().DEFAULTS)
    p.update(inp.get("params", {}))
    rooms = []
    for r in inp["rooms"]:
        rooms.append({"room_id": r["room_id"], "pubkey": f"room{r['room_id']}", "status": r["status"],
                      "created_at": r["created_at"], "reserve": r.get("reserve", 0),
                      "last_trade_at": r.get("last_trade_at", r["created_at"]),
                      "buckets": [(b["start"], b["amount"]) for b in r.get("liveness_buckets", [])],
                      "faces": r["faces"], "door_count": len(r["faces"]), "volume_gross": 0,
                      "identity": "", "room_mint": ""})
    cfg = config(live_min_reserve_lamports=p["live_min_reserve_lamports"],
                 live_max_idle_seconds=p["live_max_idle_seconds"], live_new_seconds=p["live_new_seconds"],
                 live_min_volume_lamports=p["live_min_volume_lamports"])
    return FakeSnapshot(rooms, inp["now"], cfg)


@pytest.fixture
def kp(tmp_path):
    """A throwaway matcher keypair written as a dev keyfile."""
    k = Keypair()
    p = tmp_path / "matcher.json"
    p.write_text(json.dumps(list(bytes(k))))
    return k, str(p)
