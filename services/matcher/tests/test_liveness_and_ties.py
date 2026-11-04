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
    snap = FakeSnapshot([live_room(5, [("MarvinCoin", "MARV"), ("Marvin The Martian", "MARVIN")])], NOW)
    d = decide(snap, "Marvin The Martian", "MARVIN", "")
    assert (d.room_id, d.rule, d.face) == (5, "T3", 1)


def test_paused_program_is_refused():
    with pytest.raises(Refusal) as e:
        decide(FakeSnapshot([], NOW, config(paused=True)), "A", "A", "")
    assert e.value.code == "program_paused"
