"""The liveness gate, ported from the deployed program's `Room::live` (programs/doors_v1/src/state.rs).

The program re-checks this gate at execution, so the service must agree with it exactly; where the
research matcher and the program could differ, the program wins. Thresholds come from the on-chain
Config account, never from defaults in this file:

    live = age < live_new_seconds
        OR (reserve >= live_min_reserve_lamports
            AND now - last_trade_at <= live_max_idle_seconds
            AND trailing 24 h bucket volume >= live_min_volume_lamports)

Graduated rooms (status 2) cannot exist in v1; the program's `live` fails with PhaseTwo for them, so a
launch that would need one fails on-chain whatever the matcher signs. `GraduatedRoom` makes that an
explicit refusal instead of an undefined decision.
"""
from dataclasses import dataclass

BUCKET_SECONDS = 3600   # `now / 3600 * 3600` in Room::record
WINDOW_SECONDS = 86400  # `now.saturating_sub(86400)` in Room::live


class GraduatedRoom(Exception):
    """Status >= 2: v1 has no graduation adapter and the program fails closed (Error::PhaseTwo)."""


@dataclass(frozen=True)
class Thresholds:
    live_new_seconds: int
    live_min_reserve_lamports: int
    live_max_idle_seconds: int
    live_min_volume_lamports: int


def trailing_volume(buckets, now):
    """Sum of bucket amounts whose start is an hour boundary within [now - 86400, now]."""
    total = 0
    for start, amount in buckets:
        if start % BUCKET_SECONDS == 0 and now - WINDOW_SECONDS <= start <= now:
            total += amount
    return total


def is_live(room, now, t: Thresholds):
    """Return (live, reason). `room` has status, created_at, reserve, last_trade_at, buckets."""
    if room["status"] > 1:
        raise GraduatedRoom(f"room {room['room_id']} has status {room['status']}")
    if room["created_at"] > now:
        return False, "creation timestamp in the future"
    age = now - room["created_at"]
    if age < t.live_new_seconds:
        return True, f"new room: age {age}s < {t.live_new_seconds}s"
    if room["last_trade_at"] > now:
        return False, "last trade timestamp in the future"
    volume = trailing_volume(room["buckets"], now)
    idle = now - room["last_trade_at"]
    if room["reserve"] < t.live_min_reserve_lamports:
        return False, f"reserve {room['reserve']} < {t.live_min_reserve_lamports}"
    if idle > t.live_max_idle_seconds:
        return False, f"idle {idle}s > {t.live_max_idle_seconds}s"
    if volume < t.live_min_volume_lamports:
        return False, f"trailing volume {volume} < {t.live_min_volume_lamports}"
    return True, f"reserve {room['reserve']}, idle {idle}s, trailing volume {volume}"
