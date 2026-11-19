"""symbol_key strips no affixes while the name key does. Pinned, because the asymmetry is easy to "tidy up".

name_letters feeds _strip_affixes, so a trailing COIN/TOKEN/OFFICIAL/SOLANA/CTO leaves the NAME key.
symbol_key never calls it. For class N that is irrelevant, since the key is the name alone. For class P the key
is (symbol, name), so the same short name splits by whether the creator put COIN in the ticker.

Measured on 65,630 real launches: the split happens once, "gta"/GTACOIN against "gta"/GTA. Lowering
NAME_EQUAL_MIN_LEN to 3 as recommended in CORRECTIONS section 27a removes the surface for three-character names
entirely, since class N ignores the symbol. So this is documented and pinned rather than changed: it is part of
the on-chain key, and a breaking key change is not worth one launch in 65,630.
"""
from matcher_service import rules


def test_the_name_key_strips_affixes():
    assert rules.name_letters("Bitcoin") == "BITCOIN"
    assert rules.ident("Bitcoin", "BTC")["nk"] == "BIT"


def test_the_symbol_key_does_not():
    assert rules.symbol_key("GTACOIN") == "GTACOIN"
    assert rules._strip_affixes(rules.symbol_key("GTACOIN")) == "GTA", "the affix is there to strip"
    assert rules.symbol_key("BITCOIN") == "BITCOIN"


def test_the_asymmetry_splits_one_short_name_in_the_real_sample():
    """The single observed consequence. If this ever starts failing, the symbol key began stripping affixes and
    the on-chain NameLock derivation changed with it."""
    assert rules.ident("gta", "GTACOIN")["key"] != rules.ident("gta", "GTA")["key"]
    assert rules.ident("gta", "GTACOIN")["key"] == "P\0GTACOIN\0GTA"
    assert rules.ident("gta", "GTA")["key"] == "P\0GTA\0GTA"


def test_class_n_is_unaffected_by_the_symbol_entirely():
    """Why the asymmetry costs so little: above the length threshold the symbol is not in the key at all."""
    for sym in ("GTA", "GTACOIN", "SOMETHINGELSE", "$X"):
        assert rules.ident("Grand Theft Auto VI", sym)["key"] == "N\0GRANDTHEFTAUTOVI"
