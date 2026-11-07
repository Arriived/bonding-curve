# Third-party notices

## dnstwist (Apache License 2.0)

`scripts/name_fuzz.py` contains tables and generators derived from dnstwist 20250130,
https://github.com/elceef/dnstwist, Copyright Marcin Ulikowski, licensed under the Apache License, Version 2.0
(http://www.apache.org/licenses/LICENSE-2.0). Copied unchanged: the `glyphs_unicode`, `glyphs_ascii`,
`latin_to_cyrillic` and `qwerty` tables. Adapted to launch names (tokens, not domain labels): the omission,
repetition, insertion, replacement, transposition, vowel-swap, plural, hyphenation, homoglyph and cyrillic
generators. The file states its changes in its header. Source checked: the dnstwist 20250130 wheel from PyPI.
Research and test tooling only; the service does not import it.

## confusable_homoglyphs (MIT)

`data/confusables_ascii.json` is derived from confusable_homoglyphs 3.3.1 (Unicode confusables data). Provenance
and hashes: CORRECTIONS §18.

## anyascii (ISC)

Runtime dependency since CORRECTIONS §20 (rule C, transliteration): anyascii 0.3.3, pinned in `requirements.txt`
and checked at start-up. Not vendored.

## Research-only packages (not vendored)

`requirements-research.txt`: jellyfish 1.3.0 (MIT, Metaphone, rejected candidate F). Used by
`scripts/rule_candidates.py` and `scripts/evasion_benchmark.py` only.
