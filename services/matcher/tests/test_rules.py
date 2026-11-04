"""Normalisation, the name-length minimum, the program's own fold, and parity with the research matcher."""
import json

import pytest
from conftest import SERVICE, research_matcher

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
