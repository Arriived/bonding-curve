"""MULTI_FOLD (rn -> m, vv -> w) pinned against the behaviour measured on 61,388 real pump.fun launches.

Nothing pinned this fold before. The docstring on name_letters claimed "rn/vv cannot straddle a split", which the
code had never done, and the whole suite passed anyway (CORRECTIONS section 21). Every case below is either a
deliberate property of the fold or a known, accepted cost of it, and all are observed in the real launch set.
"""
import pytest

from matcher_service import rules


def key(name, symbol="X"):
    return rules.ident(name, symbol)["key"]


# ---- the fold is deliberate: a homoglyph pair reads as one letter ----------------------------------
@pytest.mark.parametrize("disguised, target", [
    ("Purnpkin", "Pumpkin"),        # rn for m, the attack the fold exists to stop
    ("Chirnpshot", "Chimpshot"),
    ("Arnerican", "American"),
    ("Deweed", "Devveed"),          # vv for w, the other direction
])
def test_homoglyph_pair_routes_to_the_target(disguised, target):
    assert key(disguised) == key(target)


def test_the_fold_straddles_a_separator_on_purpose():
    """Letters are joined before the fold, so splitting the homoglyph cannot dodge. This is the reason the join
    happens first, and the reason the boundary artefacts below are accepted."""
    assert key("Pur npkin") == key("Pumpkin")
    assert key("Pu rnpkin") == key("Pumpkin")
    assert key("Pur-npkin") == key("Pumpkin")


# ---- the accepted cost: it also fires where no reader sees one letter ------------------------------
@pytest.mark.parametrize("name, folded", [
    ("BURN", "BUM"),
    ("TURN", "TUM"),
    ("BARN", "BAM"),
    ("Unicorn", "UNICOM"),
    ("Arnold", "AMOID"),            # L also folds to I (rule B)
    ("Tournament", "TOUMAMENT"),
    ("Remember November", "REMEMBEMOVEMBER"),   # straddles a word boundary
])
def test_known_collateral_is_unchanged(name, folded):
    assert rules.name_letters(name) == folded


def test_the_one_false_merge_found_in_61388_launches():
    """"BURN" and "bum" share a key. Measured cost of the fold on 61,388 real launches: this, and nothing else."""
    assert key("BURN", "BURN") == key("bum", "bum")


def test_the_fold_never_loses_a_merge():
    """Removing MULTI_FOLD split no room and merged none on the real set; it only ever adds equalities, so a name
    with no rn or vv pair must key identically either way."""
    saved = rules.MULTI_FOLD
    try:
        for name in ("Dacity Coin", "GTA VI", "Lucia", "Audacity", "Founder", "goat coin"):
            before = rules.name_letters(name)
            rules.MULTI_FOLD = ()
            assert rules.name_letters(name) == before, name
            rules.MULTI_FOLD = saved
    finally:
        rules.MULTI_FOLD = saved


def test_the_pairs_themselves_are_pinned():
    """The fold is part of the on-chain NameLock key, so changing this tuple is a breaking key change."""
    assert rules.MULTI_FOLD == (("rn", "m"), ("vv", "w"))
