"""Liveness boundaries (just inside / just outside each threshold) and every tie-break tier."""
import pytest
from conftest import FakeSnapshot, config, room

from matcher_service import rules
from matcher_service.decide import Refusal, decide
from matcher_service.liveness import GraduatedRoom, Thresholds, is_live

T = Thresholds(live_new_seconds=3600, live_min_reserve_lamports=500_000_000, live_max_idle_seconds=21_600,
               live_min_volume_lamports=5_000_000_000)
NOW = 1_800_000_000 // 3600 * 3600 + 1800   # mid-hour
OLD = NOW - 10 * 86400


def mature(reserve=600_000_000, idle=60, volume=6_000_000_000, start_offset=0):
    start = (NOW - 3600) // 3600 * 3600 + start_offset
    return room(1, [("A", "A")], created_at=OLD, reserve=reserve, last_trade_at=NOW - idle,
                buckets=[(start, volume)])


def test_age_threshold():
    assert is_live(room(1, [("A", "A")], created_at=NOW - 3599, reserve=0), NOW, T)[0]
    assert not is_live(room(1, [("A", "A")], created_at=NOW - 3600, reserve=0), NOW, T)[0]


def test_reserve_threshold():
    assert is_live(mature(reserve=500_000_000), NOW, T)[0]
    assert not is_live(mature(reserve=499_999_999), NOW, T)[0]


def test_idle_threshold():
    assert is_live(mature(idle=21_600), NOW, T)[0]
    assert not is_live(mature(idle=21_601), NOW, T)[0]


def test_volume_threshold():
    assert is_live(mature(volume=5_000_000_000), NOW, T)[0]
    assert not is_live(mature(volume=4_999_999_999), NOW, T)[0]


def test_volume_window_edges():
    edge = NOW - 86400  # a bucket starting exactly 24 h ago counts; one hour earlier does not
    r = room(1, [("A", "A")], created_at=OLD, reserve=10**10, last_trade_at=NOW, buckets=[(edge // 3600 * 3600 + 3600, 5 * 10**9)])
    assert is_live(r, NOW, T)[0]
    r["buckets"] = [(edge // 3600 * 3600, 5 * 10**9)]   # starts before now - 86400
    assert not is_live(r, NOW, T)[0]
    r["buckets"] = [(NOW // 3600 * 3600 + 3600, 5 * 10**9)]  # future bucket
    assert not is_live(r, NOW, T)[0]
    r["buckets"] = [(NOW - 1000, 5 * 10**9)]  # not an hour boundary: ignored, as the program does
    assert not is_live(r, NOW, T)[0]


def test_future_timestamps_are_not_live():
    assert not is_live(room(1, [("A", "A")], created_at=NOW + 1), NOW, T)[0]
    r = mature()
    r["last_trade_at"] = NOW + 1
    assert not is_live(r, NOW, T)[0]


def test_graduated_room_raises():
    with pytest.raises(GraduatedRoom):
        is_live(room(1, [("A", "A")], status=2), NOW, T)


def live_room(i, faces, reserve=10_000_000_000):
    return room(i, faces, created_at=NOW - 60, reserve=reserve)


def dead_room(i, faces):
    return room(i, faces, created_at=OLD, reserve=0, last_trade_at=OLD)


def test_tie_floor_beats_text():
    ident = rules.program_identity("Elon", "ELON").hex()
    snap = FakeSnapshot([live_room(1, [("Elon", "ELON")], reserve=1), live_room(2, [("Elon", "ELON")], reserve=99 * 10**9)],
                        NOW, locks={ident: 1})
    d = decide(snap, "Elon", "ELON", "")
    assert (d.kind, d.rule, d.room_id) == ("door", "floor", 1)


def test_tie_stronger_text_tier_wins():
    snap = FakeSnapshot([live_room(1, [("Elon", "OTHER")], reserve=99 * 10**9), live_room(2, [("Elon", "ELON")], reserve=1)], NOW)
    d = decide(snap, "Elon", "ELON", "")
    assert (d.rule, d.room_id) == ("T3", 2)


def test_tie_deeper_reserve_wins():
    snap = FakeSnapshot([live_room(1, [("Elon", "ELON")], reserve=5), live_room(2, [("ELON", "elon")], reserve=6)], NOW)
    assert decide(snap, "Elon", "ELON", "").room_id == 2


def test_tie_lowest_room_id_wins():
    snap = FakeSnapshot([live_room(7, [("Elon", "ELON")], reserve=5), live_room(3, [("Elon", "ELON")], reserve=5)], NOW)
    assert decide(snap, "Elon", "ELON", "").room_id == 3


def test_dead_floor_holder_is_passed_and_text_routing_continues():
    ident = rules.program_identity("Elon", "ELON").hex()
    snap = FakeSnapshot([dead_room(1, [("Elon", "ELON")]), live_room(2, [("Elon", "OTHER")])], NOW, locks={ident: 1})
    d = decide(snap, "Elon", "ELON", "")
    assert (d.kind, d.rule, d.room_id, d.old_holder_room_id) == ("door", "T2n", 2, 1)
    snap = FakeSnapshot([dead_room(1, [("Elon", "ELON")])], NOW, locks={ident: 1})
    d = decide(snap, "Elon", "ELON", "")
    assert (d.kind, d.old_holder_room_id) == ("new_room", 1)


def test_graduated_floor_holder_is_refused():
    ident = rules.program_identity("Elon", "ELON").hex()
    snap = FakeSnapshot([room(1, [("Elon", "ELON")], status=2)], NOW, locks={ident: 1})
    with pytest.raises(Refusal) as e:
        decide(snap, "Elon", "ELON", "")
    assert e.value.code == "graduated_identity" and e.value.status == 409


def test_graduated_text_match_is_not_a_target():
    snap = FakeSnapshot([room(1, [("Elon", "ELON")], status=2), live_room(2, [("Elon", "X")])], NOW)
    d = decide(snap, "Elon", "ELON", "")
    assert (d.rule, d.room_id) == ("T2n", 2)


def test_match_on_a_later_door_face():
    """A later face with door 0's key can give the stronger tier: door 0 MarvinCoin/MARV (key MARVIN) matches
    Marvin/MARVIN by name only (T2n); face 1 Marvin/MARVIN matches both (T3)."""
    snap = FakeSnapshot([live_room(5, [("MarvinCoin", "MARV"), ("Marvin", "MARVIN")])], NOW)
    d = decide(snap, "Marvin", "MARVIN", "")
    assert (d.room_id, d.rule, d.face) == (5, "T3", 1)


def test_face_laundering_through_the_floor_is_not_matchable():
    """CORRECTIONS §17: room 7 is "solpepe"/PEPE (key SOLPEPE). A floor door "Sol Pepe"/PEPE (same program identity,
    key PEPE) gave it a Pepe face, and every Pepe launch used to route into it, beating a genuine Pepe room on
    reserve depth. Only faces carrying the room's own key match now."""
    assert rules.program_identity("solpepe", "PEPE") == rules.program_identity("Sol Pepe", "PEPE")
    laundered = live_room(7, [("solpepe", "PEPE"), ("Sol Pepe", "PEPE")], reserve=20_000_000_000)
    for cand in (("Pepe", "PEPE"), ("Pepe", "FROG"), ("PEPE", "PEPE2")):
        d = decide(FakeSnapshot([laundered], NOW), *cand, "")
        assert d.kind == "new_room", cand
    genuine = live_room(3, [("Pepe", "PEPE")], reserve=2_000_000_000)
    d = decide(FakeSnapshot([genuine, laundered], NOW), "Pepe", "FROG", "")
    assert (d.kind, d.rule, d.room_id) == ("door", "T2n", 3)
    # The floor itself still routes the exact identity into room 7, as the program requires.
    ident = rules.program_identity("Sol Pepe", "PEPE").hex()
    d = decide(FakeSnapshot([laundered], NOW, locks={ident: 7}), "Sol Pepe", "PEPE", "")
    assert (d.kind, d.rule, d.room_id) == ("door", "floor", 7)
    # And its own key's launches still find it.
    d = decide(FakeSnapshot([laundered], NOW), "solpepe", "OTHER", "")
    assert (d.kind, d.rule, d.room_id) == ("door", "T2n", 7)


def test_paused_program_is_refused():
    with pytest.raises(Refusal) as e:
        decide(FakeSnapshot([], NOW, config(paused=True)), "A", "A", "")
    assert e.value.code == "program_paused"


# ---- NameLock (H-1) ----------------------------------------------------------------------------------
def test_new_room_signs_its_name_key_and_passes_a_dead_name_holder():
    key = rules.name_lock_key("Elon", "OTHER").hex()
    d = decide(FakeSnapshot([], NOW), "Elon", "OTHER", "")
    assert (d.kind, d.name_key, d.old_name_holder_room_id) == ("new_room", key, None)
    # Room 1 ("Elon"/"ELON") is dead and holds the name; the SlugLock of "Elon"/"OTHER" is free.
    snap = FakeSnapshot([dead_room(1, [("Elon", "ELON")])], NOW, names={key: 1})
    d = decide(snap, "Elon", "OTHER", "")
    assert (d.kind, d.old_holder_room_id, d.old_name_holder_room_id) == ("new_room", None, 1)
    # Both locks held by different dead rooms: both are passed.
    ident = rules.program_identity("Elon", "OTHER").hex()
    snap = FakeSnapshot([dead_room(1, [("Elon", "ELON")]), dead_room(2, [("Elon", "OTHER")])], NOW,
                        locks={ident: 2}, names={key: 1})
    d = decide(snap, "Elon", "OTHER", "")
    assert (d.kind, d.old_holder_room_id, d.old_name_holder_room_id) == ("new_room", 2, 1)


def test_doors_carry_no_name_key():
    d = decide(FakeSnapshot([live_room(2, [("Elon", "ELON")])], NOW), "Elon", "OTHER", "")
    assert (d.kind, d.name_key, d.old_name_holder_room_id) == ("door", "", None)


def test_launch_without_a_name_key():
    d = decide(FakeSnapshot([], NOW), "The Official Coin", "X", "")
    assert (d.kind, d.name_key) == ("new_room", "")


def test_graduated_name_holder_is_refused():
    key = rules.name_lock_key("Elon", "OTHER").hex()
    snap = FakeSnapshot([room(1, [("Elon", "ELON")], status=2)], NOW, names={key: 1})
    with pytest.raises(Refusal) as e:
        decide(snap, "Elon", "OTHER", "")
    assert e.value.code == "graduated_name" and e.value.status == 409


def test_live_name_holder_the_text_rule_missed_fails_closed():
    """Only possible if the lock was keyed under other Unicode tables (or the snapshot is inconsistent)."""
    key = rules.name_lock_key("Elon", "OTHER").hex()
    snap = FakeSnapshot([live_room(1, [("Zed", "ZED")])], NOW, names={key: 1})
    with pytest.raises(Refusal) as e:
        decide(snap, "Elon", "OTHER", "")
    assert e.value.code == "inconsistent_state" and e.value.status == 503
    with pytest.raises(Refusal) as e:
        decide(FakeSnapshot([], NOW, names={key: 9}), "Elon", "OTHER", "")
    assert e.value.code == "inconsistent_state"
