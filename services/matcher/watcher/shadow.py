"""The matcher in shadow mode over outside launches: what our launchpad would have done with each one.

Uses the live rule (matcher_service.rules): a launch becomes a door of the room whose door 0 has the same name key,
otherwise it opens a new room. Rooms are treated as live for the whole run, as in the calibration replay; on our
launchpad a dead room's key could be taken over, so this counts the upper end of doors. Nothing is signed or sent.
"""
import collections

from matcher_service import rules


class Shadow:
    def __init__(self):
        self.rooms = []            # each: door0 launch, doors, platforms, creators
        self.by_key = {}

    def route(self, launch):
        """Decision for one launch: kind "door" (with the room's door 0), "new_room", or "no_key" (the name folds to
        nothing, e.g. only emoji: our matcher would refuse such a launch)."""
        c = rules.ident(launch["name"], launch["symbol"])
        key = c["key"]
        out = {"key": key.replace("\0", "|") if key else None}
        if key is None:
            return {**out, "decision": "no_key"}
        rid = self.by_key.get(key)
        if rid is None:
            self.rooms.append({"door0": launch, "doors": 0, "platforms": collections.Counter([launch["platform"]]),
                               "creators": {launch.get("creator")}, "last_ts": launch.get("ts")})
            self.by_key[key] = len(self.rooms) - 1
            return {**out, "decision": "new_room", "room": len(self.rooms) - 1}
        room = self.rooms[rid]
        d0 = room["door0"]
        tier = rules.text_tier(c, rules.ident(d0["name"], d0["symbol"]))[0]
        same_creator = bool(launch.get("creator")) and launch.get("creator") == d0.get("creator")
        room["doors"] += 1
        room["platforms"][launch["platform"]] += 1
        room["creators"].add(launch.get("creator"))
        room["last_ts"] = launch.get("ts")
        return {**out, "decision": "door", "room": rid, "tier": tier, "same_creator_as_door0": same_creator,
                "door0": {k: d0.get(k) for k in ("name", "symbol", "platform", "mint", "ts", "signature")},
                "doors_in_room": room["doors"]}
