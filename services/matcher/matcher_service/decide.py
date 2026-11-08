"""The routing decision: a pure function of a snapshot and the candidate's metadata.

Order:
  1. Validate metadata and pause state.
  2. Enforce the program's exact-identity SlugLock restriction. A live identity
     holder may receive a door only when it also holds the candidate's live
     NameLock. Conflicting live locks cause a refusal, never a reroute to a
     former holder. Metadata without a name key retains the identity floor.
  3. Route text only to the live current NameLock holder, regardless of another
     room's reserve depth or text tier. No holder means no text target.
  4. Otherwise create a room, passing any dead holders needed for takeover.
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

    key = rules.name_lock_key(name, symbol)
    d.name_key = key.hex() if key is not None else ""
    # SlugLock is an on-chain restriction, never permission to override NameLock.
    slug_live = None
    holder_id = snapshot.slug_holder(identity)
    if holder_id is not None:
        holder = snapshot.rooms.get(holder_id)
        if holder is None:
            raise Refusal("inconsistent_state", f"SlugLock points at missing room {holder_id}", 503)
        try:
            live, why = is_live(holder, now, t)
        except GraduatedRoom:
            raise Refusal("graduated_identity", f"identity is held by graduated room {holder_id}", 409)
        d.evaluated.append({"room_id":holder_id,"role":"slug_lock_holder","live":live,"live_reason":why})
        if live:
            slug_live = holder
        else:
            d.old_holder_room_id = holder_id

    # 3. Only the current name holder can receive text-routed launches. A revived
    # former holder's depth and text tier cannot restore its launch eligibility.
    name_holder_id = snapshot.name_holder(d.name_key) if key is not None else None
    name_live = None
    if name_holder_id is not None:
        holder = snapshot.rooms.get(name_holder_id)
        if holder is None:
            raise Refusal("inconsistent_state", f"NameLock points at missing room {name_holder_id}", 503)
        try:
            live, why = is_live(holder, now, t)
        except GraduatedRoom:
            raise Refusal("graduated_name", f"name is held by graduated room {name_holder_id}", 409)
        d.evaluated.append({"room_id":name_holder_id,"role":"name_lock_holder","live":live,"live_reason":why})
        if live:
            name_live = holder
        else:
            d.old_name_holder_room_id = name_holder_id
    if slug_live is not None:
        if key is not None and (name_live is None or slug_live["room_id"] != name_holder_id):
            raise Refusal("slug_name_conflict", "the live identity holder is not the current live name holder; "
                          "the identity floor prevents rerouting this launch", 409)
        score = rules.score_room(c, slug_live["faces"])
        d.kind, d.rule, d.room_id, d.face = "door", "floor", slug_live["room_id"], score[2] if score[0] else 0
        d.name_key = ""
        return d
    if name_live is not None:
        faces = name_live["faces"]
        if not faces or rules.name_lock_key(faces[0]["name"], faces[0]["symbol"]) != key:
            raise Refusal("inconsistent_state", "current name holder's immutable face does not match its lock", 503)
        scored = rules.score_room_keyed(c, faces, key)
        if scored is None or scored[1] not in rules.ROUTING_TIERS:
            raise Refusal("inconsistent_state", "current name holder has no matching immutable face", 503)
        d.kind, d.rule, d.room_id, d.face = "door", scored[1], name_holder_id, scored[2]
        d.name_key = ""
    return d
