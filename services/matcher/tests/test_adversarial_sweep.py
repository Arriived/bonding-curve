"""Adversarial signing-time and lifecycle regressions. No live keys or RPCs."""
import json

import pytest

from conftest import FakeSnapshot, room
from test_failures import NOW, REQ, Snap, make, rows
from matcher_service import rules
from matcher_service.decide import Refusal, decide


@pytest.mark.parametrize("stage", ["blockhash", "signer"])
@pytest.mark.parametrize("expired", ["age", "lag"])
def test_snapshot_must_still_be_fresh_when_signature_is_released(tmp_path, kp, stage, expired):
    snap = Snap(1000)
    svc = make(tmp_path, kp, snap)
    calls = []

    def expire():
        if expired == "age":
            snap.read_wall -= svc.cfg.budget.max_age_seconds + 1
        else:
            svc.rpc._slot += svc.cfg.budget.max_lag_slots + 1

    blockhash, sign = svc.rpc.latest_blockhash, svc.signer.sign

    def slow_blockhash():
        out = blockhash()
        if stage == "blockhash":
            expire()
        return out

    def slow_sign(message):
        calls.append(True)
        out = sign(message)
        if stage == "signer":
            expire()
        return out

    svc.rpc.latest_blockhash, svc.signer.sign = slow_blockhash, slow_sign
    with pytest.raises(Refusal) as err:
        svc.route(dict(REQ))
    assert err.value.code == "stale_state"
    assert rows(svc) == 0
    assert len(calls) == (stage == "signer")
    print(json.dumps({"case": "signing_time_freshness", "stage": stage, "expired": expired,
                      "attack_cost_lamports": 0, "direct_payoff_lamports": 0,
                      "decisions_released": 0}))


def revived_snapshot():
    # Both rooms were legitimately created: room 1 went dead, room 2 took its
    # NameLock, then room 1 resumed trading. Room/door permanence allows revival.
    name = "Revival Frog"
    key = rules.name_lock_key(name, "NEW").hex()
    old = room(1, [(name, "OLD")], created_at=NOW - 90000, reserve=1_000_000_000,
               last_trade_at=NOW, buckets=[(NOW // 3600 * 3600, 5_000_000_000)])
    current = room(2, [(name, "NEW")], created_at=NOW - 10, reserve=500_000_000)
    return FakeSnapshot([old, current], NOW, names={key: 2})


def test_live_current_name_holder_wins_over_deeper_revived_former_holder():
    snapshot = revived_snapshot()
    # A third symbol has no SlugLock, so it reaches text matching.
    out = decide(snapshot, "Revival Frog", "THIRD", "")
    assert out.room_id == 2


def test_revived_former_holder_receives_no_new_door_even_with_stronger_text_tier():
    snapshot = revived_snapshot()
    # Its old identity lock was released while dead. Its T3 text match still
    # cannot beat the current holder's T2n match when the name lock has moved.
    out = decide(snapshot, "Revival Frog", "OLD", "")
    assert out.kind == "door" and out.room_id == 2
    assert snapshot.name_holder(rules.name_lock_key("Revival Frog", "THIRD").hex()) == 2


def test_live_slug_of_former_holder_cannot_override_current_name_holder():
    snap = revived_snapshot()
    snap.locks[rules.program_identity('Revival Frog', 'OLD').hex()] = 1
    # The program's identity floor forbids moving this exact identity while its
    # former room is live. Refuse the conflict; do not give it a new door.
    with pytest.raises(Refusal) as err:
        decide(snap, 'Revival Frog', 'OLD', '')
    assert err.value.code == 'slug_name_conflict'
