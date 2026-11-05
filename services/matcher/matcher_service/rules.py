"""Text rules, ported from research/doors_into_one_room/scripts/narrative/matcher.py.

The normalisation and equality tiers are copied, not redesigned. The v1 rule routes only on:
  T3  - folded symbol AND folded name equal;
  T2n - folded name equal, folded name at least `name_equal_min_len` characters.
Symbol-only (T2s) is computed for the record but never routes. The research matcher's fuzzy tiers
(containment, Jaccard, one-edit symbols) and all image matching were measured and rejected; they are
deliberately absent from this module so they cannot be switched on by configuration.

Unicode behaviour depends on the interpreter's `unicodedata` tables. `UNICODE_VERSION` is recorded in
every decision so a verifier can use the same tables.

Also here: the program's own on-chain fold and identity hash (state.rs `fold`, `Launch::identity`),
which key the SlugLock exact-identity floor. They are a different fold from the text rule above (ASCII
only, no NFKC) and must match the program byte for byte.
"""
import hashlib
import re
import unicodedata
from functools import lru_cache

UNICODE_VERSION = unicodedata.unidata_version
NAME_EQUAL_MIN_LEN = 4  # research DEFAULTS["name_equal_min_len"]; calibrated, not configurable

# ---- verbatim from the research matcher -------------------------------------------------------
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
INVISIBLE = {"ᅟ", "ᅠ", "ㅤ", "ﾠ", "⠀"}


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


@lru_cache(maxsize=65536)
def ident(name, symbol):
    nt = name_tokens(name)
    return {"sk": symbol_key(symbol), "nk": "".join(nt), "nt": frozenset(nt)}


# ---- the v1 equality tiers (research text_tier with fuzzy=False) -------------------------------
TIER_RANK = {"T3": 4, "T2n": 3, "T2s": 2, "T0": 0}
ROUTING_TIERS = ("T3", "T2n")


def text_tier(c, f):
    """Research text_tier(c, f, p, fuzzy=False). Returns (tier, reason)."""
    sym_eq = bool(c["sk"]) and c["sk"] == f["sk"]
    name_eq = bool(c["nk"]) and c["nk"] == f["nk"]
    if sym_eq and name_eq:
        return "T3", "symbol and name equal after folding"
    if name_eq and len(c["nk"]) >= NAME_EQUAL_MIN_LEN:
        return "T2n", "name equal after folding"
    if sym_eq:
        return "T2s", "symbol equal after folding"
    return "T0", ""


def score_room(c, faces):
    """Research score_room: best tier over every door face; only T3/T2n score.
    Returns (score, tier, face_index, reason)."""
    best, best_key = None, None
    for i, face in enumerate(faces):
        tier, why = text_tier(c, ident(face["name"], face["symbol"]))
        s = 3 if tier in ROUTING_TIERS else 0
        key = (s, TIER_RANK[tier], -i)
        if best_key is None or key > best_key:
            best, best_key = (s, tier, i, why), key
    return best


# ---- the NameLock key (create_room `name_key`) ---------------------------------------------------
NAME_KEY_LEN = 16  # state.rs NAME_KEY_LEN
NAME_KEY_DOMAIN = b"doors-v1:name-key:v1"


def name_lock_key(name, symbol):
    """The key the program locks for a new room: one key per launch, equal for two launches exactly when
    `text_tier` routes them together (T3 or T2n), so one key -> one live room enforces the routing rule.

      - folded name of at least NAME_EQUAL_MIN_LEN characters: class N over the folded name (covers T2n,
        and T3 for such names, since T3 implies equal names);
      - shorter non-empty folded name with a non-empty folded symbol: class P over (symbol, name) (T3 only);
      - otherwise None: the launch can never route by text, and only the SlugLock applies.

    sha256(domain || 0 || class || 0 || payload)[:16]; payload is UTF-8. The program never computes it.
    """
    c = ident(name, symbol)
    if len(c["nk"]) >= NAME_EQUAL_MIN_LEN:
        cls, payload = b"N", c["nk"].encode()
    elif c["nk"] and c["sk"]:
        cls, payload = b"P", c["sk"].encode() + b"\x00" + c["nk"].encode()
    else:
        return None
    return hashlib.sha256(NAME_KEY_DOMAIN + b"\x00" + cls + b"\x00" + payload).digest()[:NAME_KEY_LEN]


# ---- program fold and identity (programs/doors_v1/src/state.rs) --------------------------------
_PROGRAM_DIGITS = {ord("0"): ord("O"), ord("1"): ord("I"), ord("3"): ord("E"), ord("4"): ord("A"),
                   ord("5"): ord("S"), ord("7"): ord("T"), ord("8"): ord("B")}


def _ascii_upper(c):
    return c - 32 if 97 <= c <= 122 else c


def _ascii_alnum(c):
    return 48 <= c <= 57 or 65 <= c <= 90 or 97 <= c <= 122


def program_fold(data: bytes) -> bytes:
    """Byte-for-byte port of `fold` in state.rs."""
    out = bytearray()
    if any(b >= 128 for b in data):
        for c in data:
            c = _PROGRAM_DIGITS.get(c, _ascii_upper(c))
            if c >= 128 or _ascii_alnum(c):
                out.append(c)
        return bytes(out)
    a = bytes(c + 32 if 65 <= c <= 90 else c for c in data)
    i = 0
    while i < len(a):
        if a[i:i + 2] == b"rn":
            c, step = ord("m"), 2
        elif a[i:i + 2] == b"vv":
            c, step = ord("w"), 2
        else:
            c, step = a[i], 1
        c = _PROGRAM_DIGITS.get(c, _ascii_upper(c))
        if c >= 128 or _ascii_alnum(c):
            out.append(c)
        i += step
    return bytes(out)


def program_identity(name: str, symbol: str) -> bytes:
    """`Launch::identity`: sha256(fold(symbol) || 0x00 || fold(name)). Keys the SlugLock PDA."""
    return hashlib.sha256(program_fold(symbol.encode()) + b"\x00" + program_fold(name.encode())).digest()


def validate_metadata(name: str, symbol: str, uri: str):
    """`Launch::validate` limits, in UTF-8 bytes. Returns an error string or None."""
    n, s, u = len(name.encode()), len(symbol.encode()), len(uri.encode())
    if not 1 <= n <= 32:
        return f"name must be 1-32 bytes of UTF-8, got {n}"
    if not 1 <= s <= 10:
        return f"symbol must be 1-10 bytes of UTF-8, got {s}"
    if u > 200:
        return f"uri must be at most 200 bytes of UTF-8, got {u}"
    return None
