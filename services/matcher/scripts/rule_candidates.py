"""Measure candidate matcher rules with the same routing replay and estimator as the published calibration.

Data, labels and estimator are those of research/doors_into_one_room/scripts/narrative/calibrate_text.py: 2,956
pump.fun launches replayed in launch order, every room treated as live, a route correct if the launch is the same
narrative as the room's door 0. A pair's probability of being the same narrative is 1/0 when certain (same URI or
same research identity) or labelled S/D; otherwise its stratum's measured S/(S+D); a pair with no text signal in
the research strata cannot be estimated and is reported separately (counted as wrong in both precision columns).
The labels were written by the assistant from name and symbol and have not been human-reviewed.

Each candidate routes a launch into the room whose door 0 carries the same name key (the v1 equivalence, as the
service does since the face-laundering fix). Candidates change how the key is computed:
  v1     the rule before 7 November 2026: class N over the folded name (4+ chars), else class P over (symbol, name).
  A + B  adopted 7 November 2026. The last row recomputes the replay with the live service code; it must equal A + B.
  A      exact-name fix: the 4-character minimum is applied to the folded name *before* stopwords and the
         COIN/TOKEN suffix are removed, so "Bitcoin"/BTC and "Bitcoin"/BITCOIN share a key.
  D      affix stopwords: BABY, FAUCET, INU, AI, REAL, OG, CLASSIC, V2, 2 are dropped like COIN or THE.
  B      confusables: non-ASCII letters that Unicode lists as confusable with one ASCII letter or digit fold to it
         (data/confusables_ascii.json), and I, l, 1 and | fold together.
  E      not a key: also route into a room whose door 0 has the same folded symbol and shares a 4+ character
         name word (oldest such room). Cannot be enforced by the on-chain NameLock.
  C      transliteration: after B, every remaining non-ASCII letter or digit is replaced by its anyascii
         transliteration (anyascii 0.3.3), so "Пепе" reads as Pepe and "ᴇʟᴏɴ" as elon. Phonetic, not visual:
         Cyrillic п becomes p, not n.
  F4/F5  phonetic: when the Metaphone code (jellyfish 1.3.0) of the folded name has at least 4 (F4) or 5 (F5)
         letters, the key is that code instead of the name; otherwise the key is unchanged. The code is taken over
         the name folded without B's L -> I step (Metaphone drops vowels, so L must stay a consonant). A single key,
         so the NameLock could enforce it.
  G      no stopwords: the key is every folded name letter, stopwords and COIN/TOKEN kept ("The Runner" and
         "Runner" differ; "tHe rUnNeR", "T h e Runner" and "TheRunner" agree). Stopwords are removed per token,
         so with them the key depends on where the name is split, which case and spacing control.
  I      split-invariant affixes: like G, but the joined folded name then loses a leading THE or OFFICIAL and any
         trailing COIN, TOKEN, OFFICIAL, SOLANA or CTO (repeatedly; a leading word only when 4+ characters remain).
         Interior stopwords (A, OF, ON, AND, ...) are kept. The fold (including rn -> m, vv -> w) runs once on the
         joined letters, so case and spacing cannot change the key.
  H      invisibles dropped before the camelCase split (today "Lost<ZWJ>ThePlot" is not split at the T).
C and F need the research-only packages in requirements-research.txt.

Usage: python3 scripts/rule_candidates.py [--md OUT.md]
"""
import collections
import csv
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVICE = HERE.parent
REPO = SERVICE.parent.parent
NARR = REPO / "research/doors_into_one_room/scripts/narrative"
sys.path.insert(0, str(SERVICE))
sys.path.insert(0, str(NARR))
import calibrate_text as C  # noqa: E402  (research replay: load, strata, labels, estimator pieces)
from matcher_service import rules as R  # noqa: E402

LAUNCHES = REPO / "research/doors_into_one_room/outputs/narrative/pump_launches.jsonl"
LABELS = NARR / "labels_assistant.csv"
CONF = {k: v for k, v in json.loads((SERVICE / "data/confusables_ascii.json").read_text(encoding="utf-8"))["map"].items()}
AFFIX = {"BABY", "FAUCET", "INU", "AI", "REAL", "OG", "CLASSIC", "V2", "2"}


def _fold_v1(word_lower):  # the pre-rule-B fold, kept here so candidates are measured independently of the service
    for a, b in R.MULTI_FOLD:
        word_lower = word_lower.replace(a, b)
    return word_lower.upper().translate(R.DIGIT_FOLD)


def _translit(s):
    from anyascii import anyascii   # research-only dependency (requirements-research.txt)
    return "".join(anyascii(ch) if ord(ch) > 127 and unicodedata.category(ch)[0] in "LN" else ch for ch in s)


def make_ident(confusables=False, affix=False, translit=False, li_fold=True, stopwords=True, invisible_first=False,
               split_invariant=False):

    def pre(s):
        s = unicodedata.normalize("NFKC", s)
        if confusables:
            s = "".join(CONF.get(ch, ch) for ch in s).replace("|", "l")
        if translit:
            s = _translit(s)
        return s

    def base(s):
        s = pre(s)
        s = "".join(ch for ch in s if ch not in R.INVISIBLE and unicodedata.category(ch) != "Cf")
        s = "".join(R.HOMOGLYPHS.get(ch, ch) for ch in s)
        s = "".join(ch for ch in unicodedata.normalize("NFD", s) if not unicodedata.combining(ch))
        return s.lower()

    def fold(w):
        w = _fold_v1(w)
        return w.replace("L", "I") if confusables and li_fold else w

    stop = {fold(w.lower()) for w in R.STOPWORDS | (AFFIX if affix else set())} if stopwords else set()
    suffixes = tuple(fold(w.lower()) for w in R.SUFFIXES)

    def tokens(name, keep_stop=False, raw=False):
        s = pre(name)   # as the service: confusables (and C) before the camelCase split
        if invisible_first:
            s = "".join(ch for ch in s if ch not in R.INVISIBLE and unicodedata.category(ch) != "Cf")
        s = R.CAMEL.sub(" ", s)
        out = []
        for t in re.split(r"[^0-9a-zÀ-￿]+", base(s)):
            if not t or not any(ch.isalnum() for ch in t):
                continue
            t = "".join(ch for ch in t if ch.isalnum())
            if raw:
                out.append(t)
                continue
            t = fold(t)
            if keep_stop:
                out.append(t)
                continue
            for suf in suffixes:
                if t.endswith(suf) and len(t) > len(suf):
                    out.append(t[: -len(suf)])
                    t = suf
            if t not in stop:
                out.append(t)
        return out

    lead = tuple(fold(w) for w in ("the", "official"))
    trail = tuple(sorted((fold(w) for w in ("coin", "token", "official", "solana", "cto")), key=len, reverse=True))

    def strip_affixes(s):
        changed = True
        while changed:
            changed = False
            for w in lead:
                if s.startswith(w) and len(s) - len(w) >= 4:
                    s, changed = s[len(w):], True
            for w in trail:
                if s.endswith(w) and len(s) > len(w):
                    s, changed = s[: -len(w)], True
        return s

    def ident(name, symbol):
        if split_invariant:
            full = fold("".join(tokens(name, raw=True)))   # fold once, after joining: rn/vv cannot straddle a split
            nk = strip_affixes(full)
            return {"sk": fold("".join(ch for ch in base(symbol) if ch.isalnum())), "nk": nk, "nt": {nk} - {""},
                    "full": full}
        nt = tokens(name)
        return {"sk": fold("".join(ch for ch in base(symbol) if ch.isalnum())), "nk": "".join(nt), "nt": set(nt),
                "full": "".join(tokens(name, keep_stop=True))}
    return ident


def key_fn(ident, exact_name_fix=False, phonetic_min=None, ident_ph=None):
    def key(name, symbol):
        c = ident(name, symbol)
        if phonetic_min:
            from jellyfish import metaphone   # research-only dependency (requirements-research.txt)
            code = metaphone(ident_ph(name, symbol)["nk"]) if ident_ph(name, symbol)["nk"] else ""
            if len(code) >= phonetic_min:
                return "F\0" + code
        long_enough = len(c["full"] if exact_name_fix else c["nk"]) >= R.NAME_EQUAL_MIN_LEN
        if c["nk"] and long_enough:
            return "N\0" + c["nk"]
        if c["nk"] and c["sk"]:
            return "P\0" + c["sk"] + "\0" + c["nk"]
        return None
    return key


CANDIDATES = [
    ("v1 (before 7 Nov 2026)", dict(), False, False),
    ("A + B (adopted 7 Nov 2026)", dict(confusables=True), True, False),
    ("A: exact-name fix", dict(), True, False),
    ("D: affix stopwords", dict(affix=True), False, False),
    ("B: confusables", dict(confusables=True), False, False),
    ("A + B + D (all key rules)", dict(affix=True, confusables=True), True, False),
    ("E: same symbol + shared 4-char word", dict(), False, True),
    ("A + B + D + E", dict(affix=True, confusables=True), True, True),
    ("A + B + G (no stopwords)", dict(confusables=True, stopwords=False), True, False),
    ("A + B + I (split-invariant affixes)", dict(confusables=True, split_invariant=True), True, False),
    ("A + B + I + C", dict(confusables=True, split_invariant=True, translit=True), True, False),
    ("A + B + H (invisibles before camelCase split)", dict(confusables=True, invisible_first=True), True, False),
    ("A + B + C (transliteration)", dict(confusables=True, translit=True), True, False),
    ("A + B + F4 (phonetic, code >= 4)", dict(confusables=True), True, False, 4),
    ("A + B + F5 (phonetic, code >= 5)", dict(confusables=True), True, False, 5),
    ("A + B + C + F5", dict(confusables=True, translit=True), True, False, 5),
]


def candidate_key(opts, exact_fix, phonetic_min=None):
    """(ident, key) for a CANDIDATES row; shared with evasion_benchmark.py."""
    ident = make_ident(**opts)
    ph = make_ident(**{**opts, "li_fold": False}) if phonetic_min else None
    return ident, key_fn(ident, exact_fix, phonetic_min, ph)


def main():
    L = C.load(str(LAUNCHES))
    labels = {}
    for row in csv.DictReader(open(LABELS, encoding="utf-8", newline="")):
        labels[tuple(sorted((row["a"], row["b"])))] = row["label"].strip()

    # earlier matches, pairs and stratum precision: exactly calibrate_text.main's definitions
    index, by_uri, earlier = collections.defaultdict(list), collections.defaultdict(list), []
    for j, r in enumerate(L):
        cand = set(by_uri.get(r["uri"], ()))
        for k in C.probe_keys(r):
            cand.update(index.get(k, ()))
        earlier.append(sorted(i for i in cand if L[i]["uri"] == r["uri"] or C.matches(r, L[i], "T1")
                              or C.matches(r, L[i], "floor") or C.matches(r, L[i], "raw-symbol")))
        for k in C.index_keys(r):
            index[k].append(j)
        by_uri[r["uri"]].append(j)
    certain = lambda a, b: a["uri"] == b["uri"] or C.vkey(a) == C.vkey(b)  # noqa: E731
    pairs = {}
    for j, ms in enumerate(earlier):
        for i in ms:
            a, b = L[i], L[j]
            if not certain(a, b) and (s := C.stratum(a, b)):
                pairs.setdefault(C.pair_key(a, b), s)
    sampled = {pk for pk in labels if pk in pairs}
    sp = {}
    for s in C.STRATA:
        labs = [labels.get(pk) for pk in sampled if pairs[pk] == s]
        S, D = labs.count("S"), labs.count("D")
        sp[s] = dict(p=S / (S + D) if S + D else 0.0, lo=C.wilson(S, S + D)[0])

    def p_same(a, b, bound="mid"):
        if certain(a, b):
            return 1.0, True
        lab = labels.get(C.pair_key(a, b))
        if lab in ("S", "D"):
            return (1.0 if lab == "S" else 0.0), True
        s = C.stratum(a, b)
        if s is None:
            return 0.0, False
        if bound == "lo":
            return (0.0 if lab == "U" else sp[s]["lo"]), True
        return sp[s]["p"], True

    pv = [max([p_same(L[i], L[j])[0] for i in ms], default=0.0) for j, ms in enumerate(earlier)]
    exp_v = sum(pv)
    certain_v = {j for j, ms in enumerate(earlier) if any(certain(L[i], L[j]) for i in ms)}

    rows = []
    service_key = lambda n, s: R.ident(n, s)["key"]  # noqa: E731  the live service rule, for the check row
    for name, opts, exact_fix, use_e, *ph in CANDIDATES + [("service code (matcher_service.rules)", None, None, False)]:
        ident, key = candidate_key(opts or {}, exact_fix, ph[0] if ph else None)
        if opts is None:
            key = service_key
        rooms, by_key, by_sym = [], {}, collections.defaultdict(list)
        routed = no_signal = 0
        c_mid = c_lo = c_cert = 0.0
        examples = []
        for j, r in enumerate(L):
            k = key(r["name"], r["symbol"])
            rid = by_key.get(k) if k else None
            how = "key"
            if rid is None and use_e:
                c = ident(r["name"], r["symbol"])
                words = {t for t in c["nt"] if len(t) >= 4}
                for cand in by_sym.get(c["sk"], ()) if c["sk"] else ():
                    d0 = ident(L[rooms[cand][0]]["name"], L[rooms[cand][0]]["symbol"])
                    if words & {t for t in d0["nt"] if len(t) >= 4}:
                        rid, how = cand, "E"
                        break
            if rid is None:
                rooms.append([j])
                if k:
                    by_key.setdefault(k, len(rooms) - 1)
                sk = ident(r["name"], r["symbol"])["sk"]
                if sk:
                    by_sym[sk].append(len(rooms) - 1)
                continue
            rooms[rid].append(j)
            routed += 1
            d0 = L[rooms[rid][0]]
            pm, known = p_same(d0, r)
            c_mid += pm
            c_lo += p_same(d0, r, "lo")[0]
            no_signal += 0 if known else 1
            if j in certain_v:
                c_cert += pm
            ex = f"`{d0['name']}`/`{d0['symbol']}` <- `{r['name']}`/`{r['symbol']}` ({how})"
            if not known and ex not in examples:
                examples.append(ex)
        rows.append(dict(name=name, rooms=len(rooms), routed=routed, prec=c_mid / routed, lo=c_lo / routed,
                         hi=(c_mid + no_signal) / routed, rec=c_mid / exp_v, rec_c=c_cert / len(certain_v),
                         ns=no_signal, ex=examples))

    out = ["<!-- generated by services/matcher/scripts/rule_candidates.py -->", "",
           f"Replay of {len(L):,} pump.fun launches (the calibration sample), rooms treated as live; expected vamps "
           f"{exp_v:,.0f}, certain vamps {len(certain_v):,}. Precision and recall are estimates from assistant labels "
           "(not human-reviewed); see the script's docstring. Routes with no measurable signal count as wrong in "
           "every column except \"precision if unmeasured are right\"; recall columns count them as misses, so a "
           "rule that routes a vamp into an older, unlabelled room of the same narrative scores lower than it is. "
           "Label those routes before reading a candidate's recall.", "",
           "| rule | rooms formed | launches routed | precision (est.) | precision, pessimistic | precision if "
           "unmeasured are right | recall of vamps (est.) | recall of certain vamps | routes with no measurable signal |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['name']} | {r['rooms']:,} | {r['routed']:,} | {r['prec']:.1%} | {r['lo']:.1%} | "
                   f"{r['hi']:.1%} | {r['rec']:.1%} | {r['rec_c']:.1%} | {r['ns']} |")
    out += ["", "Routes with no measurable signal (not certain, not labelled, no research stratum), distinct pairs:", ""]
    for r in rows:
        if r["ex"]:
            out.append(f"- {r['name']}: " + "; ".join(r["ex"]))
    text = "\n".join(out) + "\n"
    if "--md" in sys.argv:
        Path(sys.argv[sys.argv.index("--md") + 1]).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
