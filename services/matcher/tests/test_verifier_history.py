"""The independent replay needs the current NameLock on every launch path."""
import sys
from pathlib import Path

import pytest

from conftest import room
from test_failures import NOW, REQ, Snap, make

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import verify_decision as vd


@pytest.mark.parametrize("floor", [False, True])
def test_open_door_replays_candidate_name_lock_history(tmp_path, kp, monkeypatch, floor):
    snap = Snap(1000, [room(1, [("Elon", "ELON")], created_at=NOW - 60)])
    if floor:
        snap.slug_holder = lambda _: 1
    svc = make(tmp_path, kp, snap)
    out = svc.route(dict(REQ, symbol="ELON" if floor else "OTHER"))
    record = svc.store.get(out["id"])["record"]
    assert record["decision"]["kind"] == "door"
    assert record["decision"]["rule"] == ("floor" if floor else "T2n")

    # Isolate the history-selection part of verify(): the empty room history
    # deliberately cannot establish an overall verdict. The NameLock read must
    # still use the candidate's independently derived key and decision slot.
    class Rpc:
        def __init__(self, *args, **kwargs):
            pass

        def program_accounts(self, *args):
            return 1000, []

        def call(self, method, params):
            assert method == "getBlockTime"
            return NOW

    seen = []
    monkeypatch.setattr(vd, "RpcClient", Rpc)
    monkeypatch.setattr(vd.History, "signatures", lambda *args: [])
    monkeypatch.setattr(vd, "config_at", lambda *args: record["config"])
    monkeypatch.setattr(vd, "lock_holder_at", lambda *args: None)
    monkeypatch.setattr(vd, "name_holder_at", lambda *args: seen.append(args[1:]))
    vd.verify(record, "unused")
    expected = vd.name_key_research(vd.research(), "Elon", "ELON" if floor else "OTHER")
    expected_pda = str(vd.pda([b"name", expected], record["program"]))
    assert seen == [(expected_pda, expected.hex(), record["state"]["slot"])]
