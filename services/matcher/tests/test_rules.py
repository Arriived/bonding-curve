"""Normalisation, the name-length minimum, the program's own fold, and parity with the research matcher."""
import json
from pathlib import Path

import pytest
from conftest import SERVICE, load_examples, research_matcher

from matcher_service import rules
from matcher_service.layouts import (CONFIG_FIELDS, DOOR_FIELDS, ROOM_FIELDS, SLUG_FIELDS)


@pytest.mark.parametrize("a,b", [
    ("$ELON", "$EL0N"),        # 0 -> O
    ("PIG", "p1g"),            # 1 -> I, and casing
    ("SPEED", "5PEED"),        # 5 -> S
    ("BOB", "8O8"),            # 8 -> B, 0 -> O
    ("MOON", "rnoon"),         # rn -> m
    ("WOW", "vvow"),           # vv -> w
    ("PEPE", "РЕРЕ"),          # Cyrillic homoglyphs
    ("PEPE", "ＰＥＰＥ"),        # full-width, folded by NFKC
    ("PEPE", "P​EPE"),     # zero-width space dropped
    ("CAFE", "Café"),          # accents stripped
])
def test_symbol_confusables_fold_together(a, b):
    assert rules.symbol_key(a) == rules.symbol_key(b)


@pytest.mark.parametrize("a,b", [
    ("Moon Frog", "🐸 Moon Frog"),           # emoji dropped
    ("SPEED-VERSE", "speed verse"),          # punctuation and whitespace
    ("random walk", "RandomWalk"),           # camelCase split
    ("Marvin", "MarvinCoin"),                # COIN suffix split off, then a stopword
    ("Elon", "The Official Elon Coin"),      # stopwords removed
    ("Doge", "  d o g e ".replace(" ", "")),
])
def test_name_keys_fold_together(a, b):
    assert rules.name_key(a) == rules.name_key(b)


def test_different_names_stay_different():
    assert rules.name_key("Thick Booty Coin") != rules.name_key("The Boring Company")
    assert rules.symbol_key("TBC") == rules.symbol_key("tbc")


def test_name_length_minimum_for_name_only_match():
    c = rules.ident("Inu", "AAA")       # name key "INU": 3 characters
    f = rules.ident("INU", "BBB")
    assert rules.text_tier(c, f)[0] == "T0"
    c = rules.ident("Cate", "AAA")      # 4 characters: routes on name alone
    f = rules.ident("CATE", "BBB")
    assert rules.text_tier(c, f)[0] == "T2n"


def test_symbol_only_never_routes():
    c, f = rules.ident("Thick Booty Coin", "TBC"), rules.ident("The Boring Company", "TBC")
    assert rules.text_tier(c, f)[0] == "T2s"
    assert rules.score_room(c, [{"name": "The Boring Company", "symbol": "TBC"}])[0] == 0


def test_no_fuzzy_or_image_paths_exist():
    # Rejected rules must not be reachable from the service at all.
    for banned in ("damerau1", "jaccard", "containment", "phash", "hamming", "image"):
        assert not any(banned in n.lower() for n in dir(rules)), banned


def test_parity_with_research_normalisation():
    rm = research_matcher()
    samples = ["$EL0N", "Elon Musk Coin", "РЕРЕ", "🐸 Moon Frog", "SPEED-VERSE", "ㅤㅤ", "犬神", "MarvinCoin",
               "rn vv 0134578", "Ⅻ", "ﬁre", "Ⓐbc", "áb", "CATE", "Inu"]
    for s in samples:
        assert rules.symbol_key(s) == rm.symbol_key(s), s
        assert rules.name_tokens(s) == rm.name_tokens(s), s


def test_program_fold_reference_vectors():
    # programs/doors_v1/tests/svm.rs fold_and_integer_math_match_reference_vectors
    assert rules.program_fold(b"rn-vv 0134578") == b"MWOIEASTB"
    assert rules.program_fold("Ã©rn-vv 0".encode()) == "Ã©RNVVO".encode()


def test_metadata_limits_are_bytes_not_characters():
    assert rules.validate_metadata("a" * 32, "S", "") is None
    assert rules.validate_metadata("a" * 33, "S", "")
    assert rules.validate_metadata("é" * 17, "S", "")      # 34 bytes
    assert rules.validate_metadata("N", "S" * 11, "")
    assert rules.validate_metadata("N", "S", "u" * 201)
    assert rules.validate_metadata("", "S", "")


def test_layout_constants_match_the_deployed_layout_file():
    lay = json.load(open(SERVICE / "idl/layouts.deployed.json"))
    for name, fields in (("Room", ROOM_FIELDS), ("Door", DOOR_FIELDS), ("SlugLock", SLUG_FIELDS),
                         ("Config", CONFIG_FIELDS)):
        table = {f["field"]: (f["offset"], f["bytes"]) for f in lay[name]["fields"]}
        for k, v in fields.items():
            assert table[k] == v, (name, k)


def _name_pairs():
    """Every slug_coverage pair, the research examples' faces against each other, and edge cases."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("slug_coverage", Path(__file__).resolve().parents[1]
                                                  / "scripts/slug_coverage.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    launches = [a for _, a, _ in mod.PAIRS] + [b for _, _, b in mod.PAIRS]
    for _, ex in load_examples():
        launches.append((ex["candidate"]["name"], ex["candidate"]["symbol"]))
        launches += [(f["name"], f["symbol"]) for r in ex["rooms"] for f in r["faces"]]
    launches += [("Pep", "PEP"), ("Pep", "PEP2"), ("pep", "pep"), ("The Coin", "THE"), ("Coin", "C"),
                 ("A", "A"), ("A", "B"), ("Pepe", "$$$"), ("Ｐｅｐ", "ＰＥＰ"), ("P3P", "PEP")]
    return [(a, b) for a in launches for b in launches]


def test_name_lock_key_equals_exactly_when_the_matcher_routes_together():
    """One key -> one live room enforces the routing rule only if keys are equal exactly when text_tier
    routes two launches together (T3 or T2n). Checked both ways over every pair."""
    from matcher_service import rules
    pairs = _name_pairs()
    assert len(pairs) > 1000
    for a, b in pairs:
        ka, kb = rules.name_lock_key(*a), rules.name_lock_key(*b)
        tier, _ = rules.text_tier(rules.ident(*b), rules.ident(*a))
        together = tier in rules.ROUTING_TIERS
        assert (ka is not None and ka == kb) == together, (a, b, tier, ka, kb)
        assert ka is None or len(ka) == rules.NAME_KEY_LEN


def test_name_lock_key_classes():
    from matcher_service import rules
    assert rules.name_lock_key("Pepe Coin", "PEPE") == rules.name_lock_key("PEPE", "FROG")     # N: name only
    assert rules.name_lock_key("Pep", "PEP") != rules.name_lock_key("Pep", "FROG")             # P: short name
    assert rules.name_lock_key("Pep", "PEP") == rules.name_lock_key("pep", "$PEP")
    assert rules.name_lock_key("The Official Coin", "X") is None                              # folds to ""


def test_verifier_derives_the_same_name_key_from_the_research_matcher():
    """scripts/verify_decision.py recomputes the key from the research matcher, independently of rules.py."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("verify_decision", SERVICE / "scripts/verify_decision.py")
    vd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vd)
    rm = research_matcher()
    launches = sorted({a for a, _ in _name_pairs()})
    assert len(launches) > 40
    for name, symbol in launches:
        assert vd.name_key_research(rm, name, symbol) == rules.name_lock_key(name, symbol), (name, symbol)


def test_verifier_recompute_returns_the_same_fields_on_every_path():
    """Each recompute() outcome carries the fields verify() compares (a floor door once lacked one)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("verify_decision", SERVICE / "scripts/verify_decision.py")
    vd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vd)
    rm = research_matcher()
    cfg = {"live_min_reserve_lamports": 500_000_000, "live_max_idle_seconds": 21_600, "live_new_seconds": 3_600,
           "live_min_volume_lamports": 5_000_000_000}
    now = 1_800_000_000

    def room(rid, faces, created_at, status=0):
        return {"room_id": rid, "status": status, "faces": [{"name": n, "symbol": s} for n, s in faces],
                "created_at": created_at, "reserve": 0, "last_trade_at": created_at, "buckets": []}
    live, dead = now - 60, now - 10 * 86400
    want = {"kind", "rule", "room_id", "old_holder", "old_name_holder"}
    cases = [({1: room(1, [("Elon", "ELON")], live)}, 1, None),     # floor door
             ({1: room(1, [("Elon", "ELON")], live)}, None, None),  # text door
             ({1: room(1, [("Elon", "ELON")], dead)}, 1, 1),        # new room over two dead holders
             ({}, None, None)]                                      # new room
    for rooms, holder, name_holder in cases:
        out = vd.recompute(rm, rooms, holder, cfg, now, "Elon", "ELON", name_holder)
        assert set(out) == want, (rooms, holder, name_holder, out)
