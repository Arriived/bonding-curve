"""The routing decision: a pure function of a snapshot and the candidate's metadata.

Order (research matcher plus the two rules the program itself enforces):
  1. Metadata limits (`Launch::validate`).
  2. Exact-identity floor. The candidate's SlugLock is keyed by the program's own fold. If it is held:
       - holder graduated (status 2)   -> refuse: the program cannot route this identity in v1;
       - holder live                   -> door into the holder (the program rejects anything else);
       - holder not live               -> the lock can be taken over; continue, passing the holder.
  3. Text rule over every room with status 0/1: the candidate's name key (rules.name_lock_key) equals the room's
     own key, its door 0's, and the room is live. The face is the best T3/T2n face carrying that key. Faces that
     entered through the floor with another key are never matched (face laundering, CORRECTIONS §17); since T3/T2n
     hold exactly when keys are equal, this is the calibrated rule without the floor bridge.
     Ties: stronger text tier, greater SOL depth (reserve), lowest room id. Graduated rooms are not
     routing targets in v1 (open_door into one fails with PhaseTwo).
  4. Otherwise a new room. Its NameLock key (`rules.name_lock_key`) is signed with it; if a dead room holds
     that key, it is passed as the old name holder (a live holder would have matched in step 3).
The function never reads the clock, the network or the key: the caller supplies `now` from the
snapshot. That is what makes a recorded decision recomputable.
"""
from dataclasses import dataclass, field

from . import rules
from .liveness import GraduatedRoom, Thresholds, is_live

RULE_CODE = {"new_room": 0, "floor": 1, "T3": 2, "T2n": 3}  # Launch.rule; the program requires <= 4


class Refusal(Exception):
    """A request the service will not sign. `code` is stable for clients; `status` is the HTTP code."""

    def __init__(self, code, message, status=422):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


@dataclass
class Decision:
    kind: str                      # "door" | "new_room"
    rule: str                      # "floor" | "T3" | "T2n" | "new_room"
    room_id: int | None = None     # target room for a door
    face: int = 0                  # door index whose face matched (0 for new rooms and floor ties)
    old_holder_room_id: int | None = None   # dead SlugLock holder the program needs to see
    identity: str = ""             # program identity hex (SlugLock seed)
    name_key: str = ""             # NameLock key hex for a new room ("" when the launch has none)
    old_name_holder_room_id: int | None = None   # dead NameLock holder the program needs to see
    candidate_keys: dict = field(default_factory=dict)
    evaluated: list = field(default_factory=list)   # every room with a T3/T2n text match, and why


def thresholds(config) -> Thresholds:
    return Thresholds(config["live_new_seconds"], config["live_min_reserve_lamports"],
                      config["live_max_idle_seconds"], config["live_min_volume_lamports"])


def decide(snapshot, name, symbol, uri) -> Decision:
    err = rules.validate_metadata(name, symbol, uri)
    if err:
        raise Refusal("invalid_metadata", err)
    if snapshot.config["paused"]:
        raise Refusal("program_paused", "Config.paused is set; the program rejects launches", 503)
    now = snapshot.clock_unix
    t = thresholds(snapshot.config)
    identity = rules.program_identity(name, symbol).hex()
    c = rules.ident(name, symbol)
    d = Decision(kind="new_room", rule="new_room", identity=identity,
                 candidate_keys={"symbol": c["sk"], "name": c["nk"], "unicode": rules.UNICODE_VERSION})

    # 2. exact-identity floor
    holder_id = snapshot.slug_holder(identity)
    if holder_id is not None:
        holder = snapshot.rooms.get(holder_id)
        if holder is None:
            raise Refusal("inconsistent_state", f"SlugLock points at room {holder_id}, which the snapshot lacks", 503)
        try:
            live, why = is_live(holder, now, t)
        except GraduatedRoom:
            raise Refusal("graduated_identity", f"identity is held by graduated room {holder_id}; v1 has no "
                          "graduation adapter and the program rejects both a door and a new room", 409)
        d.evaluated.append({"room_id": holder_id, "role": "slug_lock_holder", "live": live, "live_reason": why})
        if live:
            s, tier, face, _ = rules.score_room(c, holder["faces"])
            d.kind, d.rule, d.room_id, d.face = "door", "floor", holder_id, face if s else 0
            return d
        d.old_holder_room_id = holder_id

    # 3. text rule: rooms whose own name key (door 0's) is the candidate's
    key = rules.name_lock_key(name, symbol)
    matches = []
    for room in snapshot.rooms.values():
        if key is None or not room["faces"]:
            continue
        d0 = room["faces"][0]
        if rules.name_lock_key(d0["name"], d0["symbol"]) != key:
            continue
        scored = rules.score_room_keyed(c, room["faces"], key)
        if scored is None or scored[1] not in rules.ROUTING_TIERS:
            continue
        s, tier, face, why = scored
        row = {"room_id": room["room_id"], "role": "text_match", "text": tier, "text_reason": why, "face": face}
        if room["status"] > 1:
            row.update(live=False, live_reason="graduated: not a routing target in v1")
            d.evaluated.append(row)
            continue
        live, lwhy = is_live(room, now, t)
        row.update(live=live, live_reason=lwhy)
        d.evaluated.append(row)
        if live:
            matches.append((row, room))
    d.evaluated.sort(key=lambda r: r["room_id"])
    if matches:
        matches.sort(key=lambda m: (-rules.TIER_RANK[m[0]["text"]], -m[1]["reserve"], m[1]["room_id"]))
        row, room = matches[0]
        d.kind, d.rule, d.room_id, d.face = "door", row["text"], room["room_id"], row["face"]
        if d.old_holder_room_id == room["room_id"]:
            d.old_holder_room_id = None  # cannot happen (a dead holder is never live), kept explicit
        return d

    # 4. new room: the NameLock
    if key is not None:
        d.name_key = key.hex()
        holder_id = snapshot.name_holder(d.name_key)
        if holder_id is not None:
            holder = snapshot.rooms.get(holder_id)
            if holder is None:
                raise Refusal("inconsistent_state", f"NameLock points at room {holder_id}, which the snapshot lacks", 503)
            try:
                live, why = is_live(holder, now, t)
            except GraduatedRoom:
                raise Refusal("graduated_name", f"this name is held by graduated room {holder_id}; v1 has no "
                              "graduation adapter and the program rejects a new room under it", 409)
            d.evaluated.append({"room_id": holder_id, "role": "name_lock_holder", "live": live, "live_reason": why})
            if live:
                # Its door 0 has this key, so step 3 would have matched it. Different Unicode tables from the
                # service that created the lock can cause this; fail closed rather than sign a failing launch.
                raise Refusal("inconsistent_state", f"NameLock is held by live room {holder_id}, which the text "
                              f"rule did not match (unicode {rules.UNICODE_VERSION})", 503)
            d.old_name_holder_room_id = holder_id
    return d
