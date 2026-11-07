"""How often a deliberately disguised vamp gets the same name key as the name it copies, per rule.

Targets: one launch per distinct name key (current service rule) in the calibration sample
(research/doors_into_one_room/outputs/narrative/pump_launches.jsonl), the earliest launch with that key.
Variants: scripts/name_fuzz.py (dnstwist-derived typo and homoglyph generators plus disguise and affix fuzzers),
at most PER variants per fuzzer per target, sampled with a fixed seed. A variant the program would reject
(name over 32 bytes or symbol over 10 bytes of UTF-8) is dropped and counted. A variant is caught by a rule when
its key equals the target's key under that rule.

Two modes: the vamp keeps the target's symbol, or the same fuzzer is applied to the symbol too (one variant,
same seed). Only class P keys (names under 4 folded characters) read the symbol, so the modes differ there.

This measures dodge recall only. A rule that catches more typos will also merge more different names; that
cost is measured on real launches by scripts/rule_candidates.py, not here.

Rules: v1, the service rule (A + B; checked equal to rule_candidates' A + B on every variant), and the research
candidates C (transliteration), F5 (phonetic), G (no stopwords) and I (split-invariant affixes), defined in
rule_candidates.py. C and F need requirements-research.txt.

Usage: python3 scripts/evasion_benchmark.py [--md OUT.md] [--json OUT.json] [--per N]
"""
import json
import random
import sys
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import name_fuzz as NF  # noqa: E402
import rule_candidates as RC  # noqa: E402  (also puts the service and the research replay on sys.path)
from matcher_service import rules as R  # noqa: E402

NAME_MAX, SYMBOL_MAX = 32, 10   # the program's launch limits, in UTF-8 bytes
SEED = "evasion-benchmark-v1"


def rule_keys():
    """name -> key function for each rule compared, cached."""
    out = {"v1": RC.candidate_key({}, False)[1]}
    out["A + B (service)"] = lambda n, s: R.ident(n, s)["key"]
    out["A + B + C"] = RC.candidate_key(dict(confusables=True, translit=True), True)[1]
    out["A + B + F5"] = RC.candidate_key(dict(confusables=True), True, 5)[1]
    out["A + B + G"] = RC.candidate_key(dict(confusables=True, stopwords=False), True)[1]
    out["A + B + I"] = RC.candidate_key(dict(confusables=True, split_invariant=True), True)[1]
    out["A + B + I + C"] = RC.candidate_key(dict(confusables=True, split_invariant=True, translit=True), True)[1]
    return {k: lru_cache(maxsize=None)(f) for k, f in out.items()}


AB_CHECK = lru_cache(maxsize=None)(RC.candidate_key(dict(confusables=True), True)[1])


def targets():
    seen, out = set(), []
    for r in RC.C.load(str(RC.LAUNCHES)):
        k = R.ident(r["name"], r["symbol"])["key"]
        if k and k not in seen:
            seen.add(k)
            out.append((r["name"].strip(), r["symbol"].strip()))
    return out


def variants(fuzzer, name, symbol, per, rng_key):
    rng = random.Random(f"{SEED}:{rng_key}")
    vs = sorted(v for v in fuzzer(name) if v != name)
    vs = rng.sample(vs, min(per, len(vs)))
    sv = sorted(v for v in fuzzer(symbol) if v != symbol) if symbol else []
    sym_fuzzed = rng.choice(sv) if sv else symbol
    return vs, sym_fuzzed


def run(per=4, target_list=None, rules=None):
    rules = rules or rule_keys()
    tl = target_list if target_list is not None else targets()
    modes = ("symbol kept", "symbol fuzzed")
    stats = {m: {c: {f: {"n": 0, "dropped": 0, **{r: 0 for r in rules}} for f in fs} for c, fs in NF.FUZZERS.items()}
             for m in modes}
    escapes = {}
    for ti, (name, symbol) in enumerate(tl):
        tkeys = {r: f(name, symbol) for r, f in rules.items()}
        for cls, fs in NF.FUZZERS.items():
            for fname, fz in fs.items():
                vs, sym_f = variants(fz, name, symbol, per, f"{ti}:{fname}")
                for mode, sym in zip(modes, (symbol, sym_f)):
                    st = stats[mode][cls][fname]
                    for v in vs:
                        if len(v.encode()) > NAME_MAX or len(sym.encode()) > SYMBOL_MAX:
                            st["dropped"] += 1
                            continue
                        st["n"] += 1
                        if "A + B (service)" in rules:
                            assert rules["A + B (service)"](v, sym) == AB_CHECK(v, sym), (v, sym)
                        for r, f in rules.items():
                            hit = tkeys[r] is not None and f(v, sym) == tkeys[r]
                            st[r] += hit
                            if (not hit and r == "A + B (service)" and mode == modes[0]
                                    and len(escapes.setdefault(fname, [])) < 5):
                                escapes[fname].append(f"`{name}` -> `{v}`")
    return stats, escapes, len(tl)


def render(stats, escapes, n_targets, per):
    rules = [k for k in next(iter(next(iter(stats.values()))["disguise"].values())) if k not in ("n", "dropped")]
    pct = lambda a, b: f"{a / b:.1%}" if b else "-"  # noqa: E731
    out = ["<!-- generated by services/matcher/scripts/evasion_benchmark.py -->", "",
           f"{n_targets:,} target names (one per distinct name key in the 2,956-launch calibration sample), up to {per} "
           "variants per fuzzer per target, fixed seed. A cell is the share of variants whose name key equals the "
           "target's under that rule. Dodge recall only: the cost of catching more (different names merged) is in "
           "RULE_CANDIDATES.md. C, F, G and I are research candidates, not adopted.", ""]
    for mode, by_cls in stats.items():
        out += [f"### Vamp {'keeps the target symbol' if mode == 'symbol kept' else 'applies the same fuzzer to the symbol'}",
                "", "| class | fuzzer | variants | " + " | ".join(rules) + " |", "|---|---|---|" + "---|" * len(rules)]
        for cls, fs in by_cls.items():
            tot = {r: 0 for r in rules}
            tn = 0
            for fname, st in fs.items():
                out.append(f"| {cls} | {fname} | {st['n']:,} | " + " | ".join(pct(st[r], st["n"]) for r in rules) + " |")
                tn += st["n"]
                for r in rules:
                    tot[r] += st[r]
            out.append(f"| **{cls}** | **all** | **{tn:,}** | " + " | ".join(f"**{pct(tot[r], tn)}**" for r in rules)
                       + " |")
        dropped = sum(st["dropped"] for fs in by_cls.values() for st in fs.values())
        out += ["", f"Variants dropped as unlaunchable (over 32-byte name or 10-byte symbol): {dropped:,}.", ""]
    out += ["### Disguises the service rule (A + B) misses, first examples (symbol kept)", ""]
    for fname in NF.FUZZERS["disguise"]:
        if escapes.get(fname):
            out.append(f"- {fname}: " + "; ".join(escapes[fname]))
    return "\n".join(out) + "\n"


def main():
    per = int(sys.argv[sys.argv.index("--per") + 1]) if "--per" in sys.argv else 4
    stats, escapes, n = run(per)
    text = render(stats, escapes, n, per)
    if "--md" in sys.argv:
        Path(sys.argv[sys.argv.index("--md") + 1]).write_text(text, encoding="utf-8")
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(
            json.dumps({"targets": n, "per": per, "seed": SEED, "stats": stats}, indent=1), encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
