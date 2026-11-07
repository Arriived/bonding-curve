# Portions of this file are derived from dnstwist 20250130 (https://github.com/elceef/dnstwist),
# Copyright Marcin Ulikowski, licensed under the Apache License, Version 2.0:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#
# Taken from dnstwist's Fuzzer: the glyphs_unicode, glyphs_ascii, latin_to_cyrillic and keyboard tables (copied
# unchanged) and the omission, repetition, insertion, replacement, transposition, vowel-swap, plural, hyphenation,
# homoglyph and cyrillic generators. Changed here: they work on a token name ("Pepe Wif Hat") instead of a domain
# label, skip non-letters, and the homoglyph generator makes one substitution, not two. The disguise and affix
# fuzzers below are new. See THIRD_PARTY_NOTICES.md.
"""Name variants a vamp could launch to dodge the matcher's name key. Used by scripts/evasion_benchmark.py.

Each fuzzer maps a name to a set of variants. Three classes:
  disguise  reads as the same name to a person (case, spacing, invisible or look-alike characters);
  typo      one edit away (dnstwist's typo generators); a person may or may not read it as the same name;
  affix     the name with a memecoin word added.
Only a missed disguise is unambiguously a miss. Catching typos and affixes trades precision, which only the
real-data replay (scripts/rule_candidates.py) can measure.
"""

# ---- dnstwist tables (unchanged) ------------------------------------------------------------------
GLYPHS_UNICODE = {
    '2': ('ƻ',), '3': ('ʒ',), '5': ('ƽ',),
    'a': ('ạ', 'ă', 'ȧ', 'ɑ', 'å', 'ą', 'â', 'ǎ', 'á', 'ə', 'ä', 'ã', 'ā', 'à'),
    'b': ('ḃ', 'ḅ', 'ƅ', 'ʙ', 'ḇ', 'ɓ'),
    'c': ('č', 'ᴄ', 'ċ', 'ç', 'ć', 'ĉ', 'ƈ'),
    'd': ('ď', 'ḍ', 'ḋ', 'ɖ', 'ḏ', 'ɗ', 'ḓ', 'ḑ', 'đ'),
    'e': ('ê', 'ẹ', 'ę', 'è', 'ḛ', 'ě', 'ɇ', 'ė', 'ĕ', 'é', 'ë', 'ē', 'ȩ'),
    'f': ('ḟ', 'ƒ'),
    'g': ('ǧ', 'ġ', 'ǵ', 'ğ', 'ɡ', 'ǥ', 'ĝ', 'ģ', 'ɢ'),
    'h': ('ȟ', 'ḫ', 'ḩ', 'ḣ', 'ɦ', 'ḥ', 'ḧ', 'ħ', 'ẖ', 'ⱨ', 'ĥ'),
    'i': ('ɩ', 'ǐ', 'í', 'ɪ', 'ỉ', 'ȋ', 'ɨ', 'ï', 'ī', 'ĩ', 'ị', 'î', 'ı', 'ĭ', 'į', 'ì'),
    'j': ('ǰ', 'ĵ', 'ʝ', 'ɉ'),
    'k': ('ĸ', 'ǩ', 'ⱪ', 'ḵ', 'ķ', 'ᴋ', 'ḳ'),
    'l': ('ĺ', 'ł', 'ɫ', 'ļ', 'ľ'),
    'm': ('ᴍ', 'ṁ', 'ḿ', 'ṃ', 'ɱ'),
    'n': ('ņ', 'ǹ', 'ń', 'ň', 'ṅ', 'ṉ', 'ṇ', 'ꞑ', 'ñ', 'ŋ'),
    'o': ('ö', 'ó', 'ȯ', 'ỏ', 'ô', 'ᴏ', 'ō', 'ò', 'ŏ', 'ơ', 'ő', 'õ', 'ọ', 'ø'),
    'p': ('ṗ', 'ƿ', 'ƥ', 'ṕ'),
    'q': ('ʠ',),
    'r': ('ʀ', 'ȓ', 'ɍ', 'ɾ', 'ř', 'ṛ', 'ɽ', 'ȑ', 'ṙ', 'ŗ', 'ŕ', 'ɼ', 'ṟ'),
    's': ('ṡ', 'ș', 'ŝ', 'ꜱ', 'ʂ', 'š', 'ś', 'ṣ', 'ş'),
    't': ('ť', 'ƫ', 'ţ', 'ṭ', 'ṫ', 'ț', 'ŧ'),
    'u': ('ᴜ', 'ų', 'ŭ', 'ū', 'ű', 'ǔ', 'ȕ', 'ư', 'ù', 'ů', 'ʉ', 'ú', 'ȗ', 'ü', 'û', 'ũ', 'ụ'),
    'v': ('ᶌ', 'ṿ', 'ᴠ', 'ⱴ', 'ⱱ', 'ṽ'),
    'w': ('ᴡ', 'ẇ', 'ẅ', 'ẃ', 'ẘ', 'ẉ', 'ⱳ', 'ŵ', 'ẁ'),
    'x': ('ẋ', 'ẍ'),
    'y': ('ŷ', 'ÿ', 'ʏ', 'ẏ', 'ɏ', 'ƴ', 'ȳ', 'ý', 'ỿ', 'ỵ'),
    'z': ('ž', 'ƶ', 'ẓ', 'ẕ', 'ⱬ', 'ᴢ', 'ż', 'ź', 'ʐ'),
    'ae': ('æ',), 'oe': ('œ',),
}
GLYPHS_ASCII = {
    '0': ('o',), '1': ('l', 'i'), '3': ('8',), '6': ('9',), '8': ('3',), '9': ('6',),
    'b': ('d', 'lb'), 'c': ('e',), 'd': ('b', 'cl', 'dl'), 'e': ('c',), 'g': ('q',), 'h': ('lh',),
    'i': ('1', 'l'), 'k': ('lc',), 'l': ('1', 'i'), 'm': ('n', 'nn', 'rn'), 'n': ('m', 'r'), 'o': ('0',),
    'q': ('g',), 'u': ('v',), 'v': ('u',), 'w': ('vv',), 'rn': ('m',), 'cl': ('d',),
}
LATIN_TO_CYRILLIC = {
    'a': 'а', 'b': 'ь', 'c': 'с', 'd': 'ԁ', 'e': 'е', 'g': 'ԍ', 'h': 'һ',
    'i': 'і', 'j': 'ј', 'k': 'к', 'l': 'ӏ', 'm': 'м', 'o': 'о', 'p': 'р',
    'q': 'ԛ', 's': 'ѕ', 't': 'т', 'v': 'ѵ', 'w': 'ԝ', 'x': 'х', 'y': 'у',
}
QWERTY = {
    '1': '2q', '2': '3wq1', '3': '4ew2', '4': '5re3', '5': '6tr4', '6': '7yt5', '7': '8uy6', '8': '9iu7', '9': '0oi8',
    '0': 'po9', 'q': '12wa', 'w': '3esaq2', 'e': '4rdsw3', 'r': '5tfde4', 't': '6ygfr5', 'y': '7uhgt6', 'u': '8ijhy7',
    'i': '9okju8', 'o': '0plki9', 'p': 'lo0', 'a': 'qwsz', 's': 'edxzaw', 'd': 'rfcxse', 'f': 'tgvcdr', 'g': 'yhbvft',
    'h': 'ujnbgy', 'j': 'ikmnhu', 'k': 'olmji', 'l': 'kop', 'z': 'asx', 'x': 'zsdc', 'c': 'xdfv', 'v': 'cfgb',
    'b': 'vghn', 'n': 'bhjm', 'm': 'njk',
}

# ---- new tables -----------------------------------------------------------------------------------
SMALL_CAPS = dict(zip("abcdefghijklmnopqrstuvwxyz", "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ"))
LEET = {"a": "4", "e": "3", "i": "1", "o": "0", "s": "5", "t": "7", "b": "8"}
# Cyrillic letters that look like a Latin letter they do not transliterate to (Unicode confusables lists most).
# Case matters: lower-case н does not look like h, upper-case Н looks like H.
CYRILLIC_LOOKALIKE = {"n": "п", "u": "и", "r": "г", "w": "ш", "B": "В", "H": "Н", "K": "К", "M": "М", "T": "Т"}
# The subset of dnstwist's glyphs_ascii that reads as the same letter in a launch name; the rest (b/d, m/n, c/e, ...)
# are one-letter changes and run as the typo fuzzer ascii_glyph.
ASCII_SAME = {'0': ('o',), 'o': ('0',), '1': ('l', 'i'), 'i': ('1', 'l'), 'l': ('1', 'i'), 'm': ('rn',),
              'rn': ('m',), 'w': ('vv',), 'd': ('cl',), 'cl': ('d',)}
ZW = ("​", "‌", "‍", "⁠")
PREFIXES = ("Baby", "Real", "The Real", "Based", "Mini", "Super", "Official", "Mr", "Lil")
SUFFIXES = ("Inu", "AI", "2.0", "Classic", "Coin", "Token", "On Sol", "CTO", "Dog", "Cat", "X")


def _letters(name):
    return [i for i, ch in enumerate(name) if ch.isascii() and ch.isalpha()]


def _sub(name, i, rep, n=1):
    return name[:i] + rep + name[i + n:]


# ---- disguise -------------------------------------------------------------------------------------
def case(name):
    return {name.upper(), name.lower(), name.title(), "".join(c.upper() if k % 2 else c.lower()
                                                               for k, c in enumerate(name))}


def spacing(name):
    out = {name.replace(" ", ""), name.replace(" ", "_"), name.replace(" ", "-"), name.replace(" ", "."),
           " ".join(name.replace(" ", "")), "  ".join(name.split()), " " + name + " "}
    out |= {name[:i] + "-" + name[i:] for i in range(1, len(name)) if name[i - 1] != " " and name[i] != " "}  # dnstwist
    return out


def invisible(name):
    return {name[:i] + z + name[i:] for z in ZW for i in range(1, len(name))}


def fullwidth(name):
    fw = "".join(chr(ord(c) + 0xFEE0) if "!" <= c <= "~" else c for c in name)
    bold = "".join(chr(0x1D400 + ord(c) - 65) if "A" <= c <= "Z" else chr(0x1D41A + ord(c) - 97) if "a" <= c <= "z"
                   else c for c in name)
    return {fw, bold}


def homoglyph(name):  # dnstwist _homoglyph, Unicode table, one substitution
    low = name.lower()
    out = set()
    for i in _letters(name):
        for g in GLYPHS_UNICODE.get(low[i], ()):
            out.add(_sub(name, i, g))
    for i in range(len(low) - 1):
        for g in GLYPHS_UNICODE.get(low[i:i + 2], ()):
            out.add(_sub(name, i, g, 2))
    return out


def cyrillic(name):  # dnstwist _cyrillic (whole name), plus every single-letter swap
    whole = "".join(LATIN_TO_CYRILLIC.get(c, LATIN_TO_CYRILLIC.get(c.lower(), c)) for c in name)
    out = {whole} if whole != name else set()
    out |= {_sub(name, i, LATIN_TO_CYRILLIC[name[i].lower()]) for i in _letters(name)
            if name[i].lower() in LATIN_TO_CYRILLIC}
    return out


def cyrillic_lookalike(name):
    return {_sub(name, i, CYRILLIC_LOOKALIKE[name[i]]) for i in _letters(name) if name[i] in CYRILLIC_LOOKALIKE}


def small_caps(name):
    return {"".join(SMALL_CAPS.get(c.lower(), c) for c in name)} | \
        {_sub(name, i, SMALL_CAPS[name[i].lower()]) for i in _letters(name)}


def _glyph_swap(name, table):  # dnstwist _homoglyph over an ASCII table, one substitution
    low = name.lower()
    out = set()
    for i, c in enumerate(low):
        for g in table.get(c, ()):
            out.add(_sub(name, i, g))
    for i in range(len(low) - 1):
        for g in table.get(low[i:i + 2], ()):
            out.add(_sub(name, i, g, 2))
    return out


def ascii_lookalike(name):
    return _glyph_swap(name, ASCII_SAME)


def ascii_glyph(name):
    return _glyph_swap(name, GLYPHS_ASCII)


def leet(name):
    return {"".join(LEET.get(c.lower(), c) for c in name)} | \
        {_sub(name, i, LEET[name[i].lower()]) for i in _letters(name) if name[i].lower() in LEET}


def decoration(name):
    return {"$" + name, name + "!", name + " 🐸", "🚀" + name, "[" + name + "]", name + ".", '"' + name + '"'}


# ---- typo (dnstwist generators on the letters of the name) ----------------------------------------
def omission(name):
    return {_sub(name, i, "") for i in _letters(name)}


def repetition(name):
    return {_sub(name, i, name[i] * 2) for i in _letters(name)}


def insertion(name):
    out = set()
    for i in _letters(name):
        for c in QWERTY.get(name[i].lower(), ""):
            out |= {_sub(name, i, c + name[i]), _sub(name, i, name[i] + c)}
    return out


def replacement(name):
    return {_sub(name, i, r) for i in _letters(name) for r in QWERTY.get(name[i].lower(), "")}


def transposition(name):
    return {name[:i] + name[i + 1] + name[i] + name[i + 2:] for i in range(len(name) - 1)
            if name[i].isalpha() and name[i + 1].isalpha() and name[i].lower() != name[i + 1].lower()}


def vowel_swap(name):
    return {_sub(name, i, v) for i in _letters(name) if name[i].lower() in "aeiou" for v in "aeiou"
            if v != name[i].lower()}


def plural(name):
    return {name + ("es" if name[-1:].lower() in "sxz" else "s")} if name[-1:].isalpha() else set()


# ---- affix ----------------------------------------------------------------------------------------
def affix(name):
    return {p + " " + name for p in PREFIXES} | {name + " " + s for s in SUFFIXES}


FUZZERS = {
    "disguise": {f.__name__: f for f in (case, spacing, invisible, fullwidth, homoglyph, cyrillic, cyrillic_lookalike,
                                         small_caps, ascii_lookalike, leet, decoration)},
    "typo": {f.__name__: f for f in (ascii_glyph, omission, repetition, insertion, replacement, transposition, vowel_swap, plural)},
    "affix": {"affix": affix},
}
