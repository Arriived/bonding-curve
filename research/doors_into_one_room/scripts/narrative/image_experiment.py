"""Archived image-assisted scorer for offline experiments only.

Production matching is matcher.decide and never imports this module. Image bytes,
hashes and their calibration remain research artifacts, with no v1 routing role.
"""
from matcher import DEFAULTS as V1_DEFAULTS, ident, text_tier, is_live, room_weight, TIER_RANK

DEFAULTS = {
    **V1_DEFAULTS,
    'route_score': 3,
    'text_points': {'T3': 3, 'T2n': 3, 'T2s': 2, 'T1': 1, 'T0': 0},
    'image_points': {'I2': 2, 'I1': 1, 'I0': 0},
    'image_routing': 'shadow',
    'image_strong_max_hamming': 10,
    'image_weak_max_hamming': 16,
}

def hamming(h1, h2):
    if not h1 or not h2:
        return None
    return bin(int(h1, 16) ^ int(h2, 16)).count("1")

def image_tier(d, p):
    if d is None:
        return "I0"
    if d <= p["image_strong_max_hamming"]:
        return "I2"
    if d <= p["image_weak_max_hamming"]:
        return "I1"
    return "I0"

def score_room(c, cph, room, p):
    """Best (score, text tier, hamming or -1, face index, reason, image tier) over the room's faces."""
    best, best_key = None, None
    for i, face in enumerate(room["faces"]):
        f = ident(face["name"], face["symbol"])
        tier, why = text_tier(c, f, p, fuzzy=(i == 0))  # fuzzy text only against door 0; exact against any door
        d = hamming(cph, face.get("phash"))
        it = image_tier(d, p)
        s_img = p["text_points"][tier] + p["image_points"][it]
        s = s_img if p["image_routing"] == "on" else p["text_points"][tier]
        tie_distance = d if p["image_routing"] == "on" else None
        key = (s, TIER_RANK[tier], -(tie_distance if tie_distance is not None else 99), -i)
        if best_key is None or key > best_key:
            best, best_key = (s, tier, -1 if d is None else d, i, why, it, s_img), key
    return best

def decide_experiment(inp):
    p = dict(DEFAULTS)
    p.update(inp.get("params", {}))
    now = inp["now"]
    cand = inp["candidate"]
    c = ident(cand["name"], cand["symbol"])
    cph = cand.get("phash")
    evaluated, matches = [], []
    for room in inp["rooms"]:
        s, tier, d, face, why, it, s_img = score_room(c, cph, room, p)
        live, lreason = is_live(room, now, p)
        row = {"room_id": room["room_id"], "score": s, "text": tier, "text_reason": why, "image": it,
               "hamming": None if d < 0 else d, "face": face, "live": live, "live_reason": lreason,
               "would_route_with_image": bool(live and s_img >= p["route_score"])}
        evaluated.append(row)
        if s >= p["route_score"] and live:
            matches.append((row, room))
    if not matches:
        return {"decision": "new_room", "candidate_keys": {"symbol": c["sk"], "name": c["nk"]}, "evaluated": evaluated}
    # Tie-break: score, then text tier, then image distance, then SOL depth, then lowest room_id.
    matches.sort(key=lambda m: (-m[0]["score"], -TIER_RANK[m[0]["text"]],
                                m[0]["hamming"] if p["image_routing"] == "on" and m[0]["hamming"] is not None else 99,
                                -room_weight(m[1]), m[1]["room_id"]))
    win = matches[0][0]
    return {"decision": "door", "room_id": win["room_id"], "rule": f"{win['text']}+{win['image']} score {win['score']}",
            "candidate_keys": {"symbol": c["sk"], "name": c["nk"]}, "tied_live_matches": len(matches),
            "evaluated": evaluated}
