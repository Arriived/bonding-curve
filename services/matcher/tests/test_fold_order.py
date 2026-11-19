"""The order inside _pre is load-bearing: appearance-folding must run before sound-folding.

_pre applies the Unicode confusables table (rule B) and then transliterates what is left (rule C). Where the two
disagree, only the first one is right for impersonation, because an impersonator is exploiting how a character
LOOKS, not how it sounds. Cyrillic Р looks like P and romanizes to R. Swap the two lines and every attack in that
class escapes, silently and with no test failing. One such attack is live in the collected pump.fun sample
(CORRECTIONS section 28), so these cases are pinned.
"""
import unicodedata

import pytest

from matcher_service import rules


def key(name, symbol="X"):
    return rules.ident(name, symbol)["key"]


@pytest.mark.parametrize("ch, looks_like, sounds_like", [
    ("Р", "P", "R"),      # CYRILLIC CAPITAL LETTER ER
    ("р", "p", "r"),      # CYRILLIC SMALL LETTER ER
    ("ѕ", "s", "dz"),     # CYRILLIC SMALL LETTER DZE
])
def test_appearance_wins_over_sound(ch, looks_like, sounds_like):
    """Both folds have an opinion and they differ. The appearance one must be the one that lands in the key."""
    assert rules._CONF.get(ch) == looks_like
    assert rules._anyascii(ch).lower() == sounds_like.lower()
    assert rules._pre(ch) == looks_like


def test_the_live_cyrillic_attack_in_the_sample_is_caught():
    """Observed on pump.fun: "Pebu The Market Bull" copied with Cyrillic Р and е. It routes into the original's
    room only because confusables run first; under transliteration alone it would fold to REBU... and escape."""
    assert key("Реbu Thе Market Bull") == key("Pebu The Market Bull")
    assert rules.name_letters("Реbu Thе Market Bull") == "PEBUTHEMARKETBUII"


def test_confusables_run_before_transliteration_in_pre():
    """A direct check on the pipeline rather than on one example, so a reordering fails here even if every
    character named above later leaves the confusables table.

    Restricted to characters NFKC leaves alone. NFKC runs first in _pre and for anything it decomposes its answer
    stands, which is why U+017F LATIN SMALL LETTER LONG S keys as "s" and not as the "f" the confusables table
    gives: that is the pipeline working, not a fold-order fault.
    """
    disagree = [c for c in rules._CONF
                if ord(c) > 127
                and unicodedata.normalize("NFKC", c) == c
                and rules._anyascii(c).lower() not in ("", rules._CONF[c].lower())]
    assert disagree, "no character left where the two folds disagree; this test needs new cases"
    for c in disagree:
        assert rules._pre(c) == rules._CONF[c], f"U+{ord(c):04X} folded by sound, not appearance"


@pytest.mark.parametrize("a, b", [
    ("毒うさぎ", "毒ウサギ"),   # the same word in hiragana and in katakana
    ("こむぎ", "Komugi"),                            # kana and its romanization
    ("わこ", "Wako"),
])
def test_transliteration_merges_the_same_word_across_scripts(a, b):
    """Rule C's real job in the sample: switching script is a disguise, so the writings must share a key."""
    assert key(a) == key(b)


def test_cjk_names_are_routable_not_refused():
    """Checked because the opposite was assumed: rule C does not rescue CJK names from refusal. They survive the
    separator split either way; rule C only decides whether they key as romanized text or as the raw codepoints."""
    assert key("蝴蝶") is not None
    assert rules.name_letters("蝴蝶") == "HUDIE"
