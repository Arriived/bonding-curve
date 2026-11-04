"""Decisions that are signed but whose blockhash has not expired yet.

The program enforces single use where it can: a room-id nonce can be created once (`init` on the Room
PDA), a door index once (`init` on the Door PDA at `room.door_count`), and the runtime rejects a
duplicate signature and any blockhash older than 150 slots. What the program cannot see is two
*different* launches decided against the same snapshot. The service tracks those here, until the
decision's `last_valid_block_height` passes:

  - name/identity reservation: while a new-room decision for folded name N (or identity I) is in
    flight, another launch with name N or identity I is refused with retry-after. Otherwise both would
    be told "new room" and the T2n rule would be silently bypassed by the second one.
  - door index allocation: in-flight door decisions into a room take consecutive indices from
    `room.door_count`. If an earlier one never lands, later ones fail on-chain and must re-request.

State is per process. Running more than one replica needs this moved to shared storage (README).
"""
import threading


class InFlight:
    def __init__(self):
        self._lock = threading.Lock()
        self._names = {}     # folded name or identity -> (decision_id, last_valid_block_height)
        self._doors = {}     # room_id -> list of (index, last_valid_block_height)

    def _prune(self, height):
        self._names = {k: v for k, v in self._names.items() if v[1] >= height}
        self._doors = {r: [x for x in v if x[1] >= height] for r, v in self._doors.items()}
        self._doors = {r: v for r, v in self._doors.items() if v}

    def conflict(self, keys, height):
        with self._lock:
            self._prune(height)
            for k in keys:
                if k and k in self._names:
                    return self._names[k][0]
        return None

    def reserve_names(self, keys, decision_id, last_valid):
        with self._lock:
            for k in keys:
                if k:
                    self._names[k] = (decision_id, last_valid)

    def next_door_index(self, room_id, door_count, height):
        with self._lock:
            self._prune(height)
            used = [i for i, _ in self._doors.get(room_id, [])]
            return max([door_count - 1] + used) + 1

    def reserve_door(self, room_id, index, last_valid):
        with self._lock:
            self._doors.setdefault(room_id, []).append((index, last_valid))
