"""Decisions that are signed but whose blockhash has not expired yet.

The program enforces single use where it can: a room-id nonce can be created once (`init` on the Room
PDA), a door nonce once (`init` on the Door PDA `["door", room, door_nonce]`), and the runtime and
program reject a duplicate signature, a blockhash older than 150 slots, and a launch past its signed
`expires_at_slot`. What the program cannot see is two *different* launches decided against the same
snapshot. The service tracks those here, until the
decision's `last_valid_block_height` passes:

  - name/identity reservation: while a new-room decision for folded name N (or identity I) is in
    flight, another launch with name N or identity I is refused with retry-after. Otherwise both would
    be told "new room" and the T2n rule would be silently bypassed by the second one.
  - launcher reservation: a verified funded launcher may hold at most one new-room
    decision, across all names. The launcher, name and identity share one atomic claim.

Door addresses need no tracking: each door decision carries a random signed door nonce, so
concurrent door launches into one room have independent addresses (a nonce collision fails cleanly
on-chain and the client re-requests).

Check and reservation are one atomic step (`claim`), taken *before* signing: `/route` runs on a
thread pool, and a separate check-then-reserve let two concurrent requests for one name both pass the
check and both be signed "new room". A claim that does not become a released decision (refusal, signer
or store failure) is dropped with `release`.

State is per process. Running more than one replica needs this moved to shared storage (README).
"""
import itertools
import threading


class InFlight:
    def __init__(self):
        self._lock = threading.Lock()
        self._names = {}     # folded name or identity -> (holder, last_valid_block_height)
        self._seq = itertools.count(1)

    def _prune(self, height):
        self._names = {k: v for k, v in self._names.items() if v[1] >= height}

    def conflict(self, keys, height):
        with self._lock:
            self._prune(height)
            for k in keys:
                if k and k in self._names:
                    return self._names[k][0]
        return None

    def claim(self, keys, height, last_valid):
        """Atomically: refuse if any key is held, else hold every key. Returns (token, None) or
        (None, holder of the conflicting key)."""
        with self._lock:
            self._prune(height)
            for k in keys:
                if k and k in self._names:
                    return None, self._names[k][0]
            token = f"pending:{next(self._seq)}"
            for k in keys:
                if k:
                    self._names[k] = (token, last_valid)
            return token, None

    def bind(self, token, decision_id):
        """The claim became a released decision: name it by its decision id."""
        with self._lock:
            for k, (holder, lv) in list(self._names.items()):
                if holder == token:
                    self._names[k] = (decision_id, lv)

    def release(self, token):
        with self._lock:
            self._names = {k: v for k, v in self._names.items() if v[0] != token}

    def reserve_names(self, keys, decision_id, last_valid):
        with self._lock:
            for k in keys:
                if k:
                    self._names[k] = (decision_id, last_valid)
