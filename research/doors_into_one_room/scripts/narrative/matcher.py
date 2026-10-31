"""Narrative matcher prototype: route a launch to a door in a live room, or to a new room.

Input (JSON): {"now": unix_seconds, "candidate": {...}, "rooms": [...], "params": {...optional overrides}}
  candidate: {"name", "symbol", "uri", "phash": "16 hex chars" | null}
  room: {"room_id": int, "status": 0|1|2,
         "faces": [{"name", "symbol", "phash"}...],   # faces[0] is door 0 (the room token's identity)
         "reserve": lamports, "last_trade_at": unix,   # status 0/1, maintained by the doors program
         "pool": {"total_lp_b_fee": int, "ckpt_fee": int, "ckpt_ts": unix,   # status 2, DAMM v2 Pool reads
                  "last_window_fee": int, "token_b_amount": int}}
Output (JSON): the decision, the rule that fired, the evidence, and every room's gate result.

Rules are specified in NARRATIVE_DETECTION.md. All thresholds live in DEFAULTS and are overridable for calibration.
"""
import json
import re
import sys
import unicodedata

DEFAULTS = {
    # combination: route when text_points + image_points >= route_score
    "route_score": 3,
    # T3 symbol and name equal; T2n name equal; T2s symbol equal; T1 fuzzy (outputs/narrative/text_calibration.md)
    "text_points": {"T3": 3, "T2n": 3, "T2s": 2, "T1": 1, "T0": 0},
    "image_points": {"I2": 2, "I1": 1, "I0": 0},
    # "shadow": image points are computed and reported (would_route_with_image) but do not change the decision,
    # until the image rule is calibrated on real token images. "on": they count.
    "image_routing": "shadow",
    "name_equal_min_len": 4,
    "image_strong_max_hamming": 10,   # I2: pHash distance <= this
    "image_weak_max_hamming": 16,     # I1
    "jaccard_min": 0.5,
    "symbol_edit1_min_len": 5,
    "containment_min_len": 3,
    # liveness, pre-graduation (status 0/1)
    "live_min_reserve_lamports": 2_000_000_000,
    "live_max_idle_seconds": 6 * 3600,
    # liveness, post-graduation (status 2), from DAMM v2 Pool.metrics.total_lp_b_fee
    "pool_window_seconds": 86_400,
    "pool_min_window_lp_fee": 20_000_000,       # lamports of LP fee per window
    "pool_min_token_b_amount": 0,               # optional floor on Pool.token_b_amount; 0 = off
}

# Cross-script homoglyphs that NFKC does not fold (Cyrillic and Greek capitals and smalls that render as Latin).
HOMOGLYPHS = {
    "а": "a", "в": "b", "е": "e", "к": "k", "м": "m", "н": "h", "о": "o", "р": "p", "с": "c", "т": "t", "у": "y",
    "х": "x", "і": "i", "ј": "j", "ѕ": "s", "ԁ": "d", "ɡ": "g", "ո": "n", "ս": "u", "ⅼ": "l",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C", "Т": "T", "У": "Y",
    "Х": "X", "І": "I", "Ј": "J", "Ѕ": "S",
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M", "Ν": "N", "Ο": "O", "Ρ": "P",
    "Τ": "T", "Υ": "Y", "Χ": "X", "ο": "o", "ν": "v", "α": "a", "ι": "i", "κ": "k", "ρ": "p", "τ": "t", "υ": "u",
}
DIGIT_FOLD = str.maketrans({"0": "O", "1": "I", "3": "E", "4": "A", "5": "S", "7": "T", "8": "B"})
MULTI_FOLD = (("rn", "m"), ("vv", "w"))  # applied to lower case, where they read as one letter
STOPWORDS = {"THE", "A", "AN", "OF", "ON", "AND", "COIN", "TOKEN", "OFFICIAL", "SOL", "SOLANA", "MEME", "CTO"}
SUFFIXES = ("COIN", "TOKEN")
CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z])")


# Blank-rendering letters that str.isalnum() accepts (Hangul fillers, braille blank); format chars are dropped too.
INVISIBLE = {"\u115f", "\u1160", "\u3164", "\uffa0", "\u2800"}


def _base(s):
    """NFKC, drop invisibles, homoglyph fold, strip accents, lower case. Separators are kept."""
    s = unicodedata.normalize("NFKC", s)
    s = "".join(ch for ch in s if ch not in INVISIBLE and unicodedata.category(ch) != "Cf")
    s = "".join(HOMOGLYPHS.get(ch, ch) for ch in s)
    s = "".join(ch for ch in unicodedata.normalize("NFD", s) if not unicodedata.combining(ch))
    return s.lower()


def _fold(word_lower):
    for a, b in MULTI_FOLD:
        word_lower = word_lower.replace(a, b)
    return word_lower.upper().translate(DIGIT_FOLD)


def symbol_key(symbol):
    """Folded symbol: alphanumerics only (any script), '$' and punctuation dropped, confusables folded."""
    return _fold("".join(ch for ch in _base(symbol) if ch.isalnum()))


def name_tokens(name):
    """Folded name tokens, stopwords removed, COIN/TOKEN suffixes split off."""
    s = CAMEL.sub(" ", unicodedata.normalize("NFKC", name))
    raw = re.split(r"[^0-9a-zÀ-￿]+", _base(s))
    out = []
    for t in raw:
        if not t or not any(ch.isalnum() for ch in t):
            continue
        t = _fold("".join(ch for ch in t if ch.isalnum()))
        for suf in SUFFIXES:
            if t.endswith(suf) and len(t) > len(suf):
                out.append(t[: -len(suf)])
                t = suf
        if t not in STOPWORDS:
            out.append(t)
    return out


def name_key(name):
    return "".join(name_tokens(name))


def damerau1(a, b):
    """True if Damerau-Levenshtein distance between a and b is exactly 1."""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        return len(diff) == 1 or (len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]]
                                  and a[diff[1]] == b[diff[0]])
    if len(a) > len(b):
        a, b = b, a
    for i in range(len(b)):
        if b[:i] + b[i + 1:] == a:
            return True
    return False


def text_tier(c, f, p, fuzzy=True):
    """Return (tier, reason) for candidate identity c against room face f.
    c, f: dicts with precomputed 'sk' (symbol key), 'nk' (name key), 'nt' (name token set)."""
    sym_eq = bool(c["sk"]) and c["sk"] == f["sk"]
    name_eq = bool(c["nk"]) and c["nk"] == f["nk"]
    if sym_eq and name_eq:
        return "T3", "symbol and name equal after folding"
    if name_eq and len(c["nk"]) >= p["name_equal_min_len"]:
        return "T2n", "name equal after folding"
    if sym_eq:
        return "T2s", "symbol equal after folding"
    if not fuzzy:
        return "T0", ""
    m = p["containment_min_len"]
    if (len(c["sk"]) >= m and (c["sk"] in f["nt"] or c["sk"] == f["nk"])) or \
       (len(f["sk"]) >= m and (f["sk"] in c["nt"] or f["sk"] == c["nk"])):
        return "T1", "one side's symbol is a word of the other's name"
    if c["nt"] and f["nt"]:
        inter, union = c["nt"] & f["nt"], c["nt"] | f["nt"]
        if len(inter) / len(union) >= p["jaccard_min"] and max(len(t) for t in inter) >= 4:
            return "T1", f"name word overlap {len(inter)}/{len(union)}"
    if min(len(c["sk"]), len(f["sk"])) >= p["symbol_edit1_min_len"] and damerau1(c["sk"], f["sk"]):
        return "T1", "symbols one edit apart"
    return "T0", ""


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


def ident(name, symbol):
    nt = name_tokens(name)
    return {"sk": symbol_key(symbol), "nk": "".join(nt), "nt": set(nt)}


def is_live(room, now, p):
    """Hard gate. Returns (live, reason)."""
    st = room["status"]
    if st in (0, 1):
        if room["reserve"] < p["live_min_reserve_lamports"]:
            return False, f"reserve {room['reserve']} < {p['live_min_reserve_lamports']}"
        idle = now - room["last_trade_at"]
        if idle > p["live_max_idle_seconds"]:
            return False, f"idle {idle}s > {p['live_max_idle_seconds']}s"
        return True, "pre-graduation: reserve and recent trade"
    pool = room["pool"]
    if pool["token_b_amount"] < p["pool_min_token_b_amount"]:
        return False, "pool token_b_amount below floor"
    age = now - pool["ckpt_ts"]
    if age > 2 * p["pool_window_seconds"]:
        return False, f"fee checkpoint stale ({age}s old)"
    in_window = pool["total_lp_b_fee"] - pool["ckpt_fee"]
    if in_window >= p["pool_min_window_lp_fee"]:
        return True, f"pool LP fee since checkpoint {in_window}"
    if age <= p["pool_window_seconds"] and pool["last_window_fee"] >= p["pool_min_window_lp_fee"]:
        return True, f"pool LP fee in last window {pool['last_window_fee']}"
    return False, "pool LP fee below threshold"


def room_weight(room):
    """SOL depth used in tie-breaking: curve reserve before graduation, pool token_b_amount (WSOL) after."""
    return room["reserve"] if room["status"] in (0, 1) else room["pool"]["token_b_amount"]


TIER_RANK = {"T3": 4, "T2n": 3, "T2s": 2, "T1": 1, "T0": 0}


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
        key = (s, TIER_RANK[tier], -(d if d is not None else 99), -i)
        if best_key is None or key > best_key:
            best, best_key = (s, tier, -1 if d is None else d, i, why, it, s_img), key
    return best


def decide(inp):
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
                                m[0]["hamming"] if m[0]["hamming"] is not None else 99,
                                -room_weight(m[1]), m[1]["room_id"]))
    win = matches[0][0]
    return {"decision": "door", "room_id": win["room_id"], "rule": f"{win['text']}+{win['image']} score {win['score']}",
            "candidate_keys": {"symbol": c["sk"], "name": c["nk"]}, "tied_live_matches": len(matches),
            "evaluated": evaluated}


def main():
    inp = json.load(open(sys.argv[1]) if len(sys.argv) > 1 else sys.stdin)
    print(json.dumps(decide(inp), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
