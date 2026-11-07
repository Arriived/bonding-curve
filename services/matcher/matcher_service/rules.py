"""Text rules, ported from research/doors_into_one_room/scripts/narrative/matcher.py.

The character folds are the research matcher's, plus owner-approved rules A, B (CORRECTIONS §18), C and I (§20):
the name key is the name's folded letters joined, with a few affixes stripped, not the research per-token stopword
removal. The v1 rule routes only on:
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
import json
import re
import unicodedata
from functools import lru_cache
from importlib import metadata as _metadata

from anyascii import anyascii as _anyascii
from pathlib import Path

UNICODE_VERSION = unicodedata.unidata_version
# The fold depends on the interpreter's Unicode tables, and name keys are now permanent on-chain (the NameLock PDA
# seed). A service or verifier on other tables would key the same name differently: refuse to run instead
# (CORRECTIONS §17). Change this only together with a migration plan for existing NameLocks.
PINNED_UNICODE_VERSION = "15.1.0"
PINNED_ANYASCII_VERSION = "0.3.3"   # rule C's tables; same reasoning


class UnicodeMismatch(RuntimeError):
    pass


def check_unicode(version=None):
    if hashlib.sha256(_CONF_RAW).hexdigest() != CONFUSABLES_SHA256:
        raise UnicodeMismatch(f"{_CONF_PATH} is not the pinned confusables table {CONFUSABLES_SHA256}")
    have = _metadata.version("anyascii")
    if have != PINNED_ANYASCII_VERSION:
        raise UnicodeMismatch(f"anyascii {have} is installed; name keys are pinned to {PINNED_ANYASCII_VERSION} "
                              "(rule C transliteration tables)")
    v = UNICODE_VERSION if version is None else version
    if v != PINNED_UNICODE_VERSION:
        raise UnicodeMismatch(f"Unicode tables are {v}; name keys are pinned to {PINNED_UNICODE_VERSION}. Run on a "
                              "Python whose unicodedata.unidata_version matches (3.13 ships 15.1.0).")
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
# STOPWORDS, SUFFIXES and CAMEL are the research matcher's. The live key no longer removes stopwords per token (rule I,
# CORRECTIONS §20); they stay for scripts/rule_candidates.py, which replays the earlier rules.
STOPWORDS = {"THE", "A", "AN", "OF", "ON", "AND", "COIN", "TOKEN", "OFFICIAL", "SOL", "SOLANA", "MEME", "CTO"}
SUFFIXES = ("COIN", "TOKEN")
CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z])")
# Blank-rendering letters that str.isalnum() accepts (Hangul fillers, braille blank); format chars are dropped too.
INVISIBLE = {"ᅟ", "ᅠ", "ㅤ", "ﾠ", "⠀"}


# ---- rule B (owner ruling, 7 November 2026; CORRECTIONS §18) --------------------------------------
# Unicode confusables: a non-ASCII character that Unicode lists as confusable with one ASCII letter or digit folds to
# it, after NFKC and before any splitting; '|' reads as 'l'; and after folding, L and I are one letter (with the
# existing 1 -> I). The table is pinned by hash like the Unicode tables: other data would key names differently.
_CONF_PATH = Path(__file__).resolve().parent.parent / "data" / "confusables_ascii.json"
_CONF_RAW = _CONF_PATH.read_bytes()
CONFUSABLES_SHA256 = "2e181ed8e97c8b9ec30b52ecf99dbdfc3f1917f1c8ae34fd88a74d1836412566"
_CONF = json.loads(_CONF_RAW)["map"]


def _pre(s):
    """NFKC, Unicode confusables to ASCII, '|' to 'l' (rule B), then every remaining non-ASCII letter or digit to its
    anyascii transliteration (rule C: "ᴇʟᴏɴ" -> elon, "Пепе" -> Pepe). Applied to raw names and symbols first."""
    s = unicodedata.normalize("NFKC", s)
    s = "".join(_CONF.get(ch, ch) for ch in s).replace("|", "l")
    return "".join(_anyascii(ch) if ord(ch) > 127 and unicodedata.category(ch)[0] in "LN" else ch for ch in s)


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
    return word_lower.upper().translate(DIGIT_FOLD).replace("L", "I")   # rule B: I, l, 1 and | read alike


def symbol_key(symbol):
    """Folded symbol: alphanumerics only (any script), '$' and punctuation dropped, confusables folded."""
    return _fold("".join(ch for ch in _base(_pre(symbol)) if ch.isalnum()))


def name_letters(name):
    """Every letter and digit of the name, joined, then folded once (rule I): separators, case and the camelCase
    split cannot change it, and rn/vv cannot straddle a split. Stopwords are kept."""
    raw = re.split(r"[^0-9a-zÀ-￿]+", _base(_pre(name)))
    return _fold("".join(ch for t in raw for ch in t if ch.isalnum()))


# Rule I's affixes, in folded form (L reads as I: OFFICIAL -> OFFICIAI, SOLANA -> SOIANA).
_LEAD = tuple(_fold(w) for w in ("the", "official"))
_TRAIL = tuple(sorted((_fold(w) for w in ("coin", "token", "official", "solana", "cto")), key=len, reverse=True))


def _strip_affixes(s):
    """A leading THE or OFFICIAL (only while 4+ letters remain) and any trailing COIN, TOKEN, OFFICIAL, SOLANA or
    CTO, repeatedly. Interior words are kept: "Swimming in the Money" and "Swimming in Money" differ."""
    changed = True
    while changed:
        changed = False
        for w in _TRAIL:   # trailing first, so "Theory Coin" keys like "Theory"
            if s.endswith(w) and len(s) > len(w):
                s, changed = s[: -len(w)], True
        for w in _LEAD:
            if s.startswith(w) and len(s) - len(w) >= 4:
                s, changed = s[len(w):], True
    return s


def name_key(name):
    return _strip_affixes(name_letters(name))


def _key_string(sk, nk, full):
    """The routing key. Class N over the name key when the folded name *before* affixes are stripped has at least
    NAME_EQUAL_MIN_LEN characters (rule A: so "Bitcoin"/BTC and "Bitcoin"/BITCOIN share a key); else class P over
    (symbol, name) when both are non-empty; else none."""
    if nk and len(full) >= NAME_EQUAL_MIN_LEN:
        return "N\0" + nk
    if nk and sk:
        return "P\0" + sk + "\0" + nk
    return None


@lru_cache(maxsize=65536)
def ident(name, symbol):
    full = name_letters(name)
    sk, nk = symbol_key(symbol), _strip_affixes(full)
    return {"sk": sk, "nk": nk, "full": full, "key": _key_string(sk, nk, full)}


# ---- the v1 equality tiers ------------------------------------------------------------------------
TIER_RANK = {"T3": 4, "T2n": 3, "T2s": 2, "T0": 0}
ROUTING_TIERS = ("T3", "T2n")


def text_tier(c, f):
    """Two launches route together exactly when their keys are equal (so the NameLock enforces the routing rule):
    T3 with equal folded symbols, T2n without. Symbol equality alone (T2s) is recorded and never routes."""
    sym_eq = bool(c["sk"]) and c["sk"] == f["sk"]
    if c["key"] is not None and c["key"] == f["key"]:
        if sym_eq:
            return "T3", "symbol and name equal after folding"
        return "T2n", "name equal after folding"
    if sym_eq:
        return "T2s", "symbol equal after folding"
    return "T0", ""


def score_room_keyed(c, faces, key):
    """score_room over only the faces that carry `key`, the room's own name key (its door 0's). Face indices are the
    room's. A face with another key reached the room through the on-chain floor (identity equal under the program's
    ASCII fold, name key different under this module's); matching on it would let one room absorb another
    narrative (face laundering, CORRECTIONS §17), so it is not matchable. Returns score_room's tuple, or None."""
    best, best_key = None, None
    for i, face in enumerate(faces):
        if name_lock_key(face["name"], face["symbol"]) != key:
            continue
        tier, why = text_tier(c, ident(face["name"], face["symbol"]))
        s = 3 if tier in ROUTING_TIERS else 0
        k = (s, TIER_RANK[tier], -i)
        if best_key is None or k > best_key:
            best, best_key = (s, tier, i, why), k
    return best


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


@lru_cache(maxsize=65536)
def name_lock_key(name, symbol):
    """The key the program locks for a new room: one key per launch, equal for two launches exactly when text_tier
    routes them together (it is defined by the same key). Class N: the folded name (rule A decides the class on the
    unstripped folded name). Class P: folded symbol and short folded name. sha256(domain || 0 || class || 0 ||
    payload)[:16], payload UTF-8. The program never computes it."""
    k = ident(name, symbol)["key"]
    if k is None:
        return None
    cls, _, payload = k.partition("\0")
    return hashlib.sha256(NAME_KEY_DOMAIN + b"\x00" + cls.encode() + b"\x00" + payload.encode()).digest()[:NAME_KEY_LEN]


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
