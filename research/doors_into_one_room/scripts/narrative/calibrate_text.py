"""Calibrate the text rules on real pump.fun launches.

Replays the sample in launch order (slot, then signature). At each operating point every launch is routed by the
matcher's text rules against the rooms formed so far, all treated as live (the liveness gate is measured
separately, by liveness_reads.py). A routed launch becomes a door; its exact keys join the room. Fuzzy rules
match each room's door 0 only, as in matcher.py. Ties: stronger text tier, then the oldest room.
A route is correct if the launch is the same narrative as the room's door 0 (the room token's identity), so
loose rules that chain unrelated launches into one room are charged for every launch that follows.

Legacy benchmark label policy for a pair of launches (A earlier, B later):
  certain same - equal metadata URI strings (including missing URIs in this historical definition), or identical folded
                 name AND symbol (the label rule treats one identity as one narrative);
  labelled     - pairs with different identities are labelled S (same narrative), D (different) or U (unsure)
                 in scripts/narrative/labels_assistant.csv. The labels were written by the assistant (Claude)
                 from name and symbol alone, without images, and have not been reviewed by a human.
Only a stratified random sample of the different-identity pairs is labelled: up to SAMPLE_PER_STRATUM pairs per
signal (symbol equal, name equal, containment, name-word Jaccard, symbol one edit apart), drawn once with SEED
when no labels file exists. A labelled pair is counted in the stratum of its current strongest signal. A pair that was not
labelled takes its stratum's measured share of S among S+D. This makes precision and recall at the looser
operating points estimates; the doc reports them as such.

A launch is a vamp if an earlier launch is the same narrative. Copies that change name and symbol and keep only
the image are invisible here, so recall is measured over text-findable copies and is an upper bound.

Usage: python3 calibrate_text.py <launches.jsonl> <labels.csv> <out_dir>
Writes text_calibration.md, label_sample.csv (the pairs to label), copies.json (input to liveness_reads.py).
These historical definitions are retained for reproduction. label_dependency.py
separately excludes missing URIs and distinguishes exact URI metrics from semantic
correctness: mutable URI equality does not prove identical historical metadata bytes.
"""
import collections
import csv
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
import matcher as M  # noqa: E402

P = dict(M.DEFAULTS)
SEED = 20261031
SAMPLE_PER_STRATUM = 60
STRATA = ["symbol equal", "name equal", "containment", "jaccard", "symbol edit 1"]
OPERATING_POINTS = [
    ("floor", "on-chain floor: ASCII-folded symbol and name both equal"),
    ("T3", "symbol and name equal after full folding"),
    ("T3+name", "T3, or name equal after folding (name key >= 4 chars): the v1 text operating point"),
    ("T2-symbol", "T3, or symbol equal after folding"),
    ("T2", "T3, or symbol equal, or name equal, after folding"),
    ("T1", "T2, or fuzzy: containment, name-word Jaccard >= 0.5, symbols one edit apart (len >= 5)"),
    ("raw-symbol", "baseline: symbol equal, case-insensitive, no folding"),
]


OP_TIERS = {"T3": {"T3"}, "T3+name": {"T3", "T2n"}, "T2-symbol": {"T3", "T2s"}, "T2": {"T3", "T2n", "T2s"},
            "T1": {"T3", "T2n", "T2s", "T1"}}


def floor_fold(s):
    """What the program can compute on-chain over raw UTF-8 bytes: on all-ASCII input, lower-case, rn->m, vv->w;
    then ASCII letters upper-cased, ASCII non-alphanumerics dropped, digits folded 0->O 1->I 3->E 4->A 5->S
    7->T 8->B; non-ASCII bytes kept unchanged (no Unicode normalisation on-chain)."""
    low = s.lower().replace("rn", "m").replace("vv", "w") if s.isascii() else s
    out = []
    for ch in low:
        if ch.isascii():
            if ch.isalnum():
                out.append(ch.upper().translate(M.DIGIT_FOLD))
        else:
            out.append(ch)
    return "".join(out)


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def vkey(r):
    return f"{r['nk']}|{r['sk']}"


def pair_key(a, b):
    return tuple(sorted((vkey(a), vkey(b))))


def stratum(a, b):
    """Strongest signal between two launches with different identities, or None."""
    t, why = M.text_tier(a, b, P, fuzzy=True)
    if t == "T2s":
        return "symbol equal"
    if t == "T2n":
        return "name equal"
    if t == "T1":
        if why.startswith("one side"):
            return "containment"
        if why.startswith("name word"):
            return "jaccard"
        return "symbol edit 1"
    return None


def matches(a, b, op):
    if op == "floor":
        return bool(a["ff"][0]) and a["ff"] == b["ff"]
    if op == "raw-symbol":
        return bool(a["rs"]) and a["rs"] == b["rs"]
    t, _ = M.text_tier(a, b, P, fuzzy=True)
    return t in OP_TIERS[op]


def exact_matches(a, b, op):
    """Match against a non-door-0 face: exact rules only."""
    if op in ("floor", "raw-symbol"):
        return False
    t, _ = M.text_tier(a, b, P, fuzzy=False)
    return t in OP_TIERS[op]


def index_keys(r):
    ks = {("s", r["sk"]), ("n", r["nk"]), ("f", "\0".join(r["ff"])), ("r", r["rs"]), ("t", r["sk"])}
    ks |= {("t", t) for t in r["nt"]}
    if len(r["sk"]) >= P["symbol_edit1_min_len"] - 1:
        ks |= {("d", r["sk"][:i] + r["sk"][i + 1:]) for i in range(len(r["sk"]))} | {("d", r["sk"])}
    return {k for k in ks if k[1]}


def probe_keys(r):
    ks = index_keys(r) | {("s", t) for t in r["nt"]} | {("n", r["sk"])} | {("t", r["nk"])}
    return {k for k in ks if k[1]}


def load(path):
    rows = [json.loads(l) for l in open(path, encoding='utf-8')]
    rows.sort(key=lambda r: (r["slot"], r["signature"]))
    seen, out = set(), []
    for r in rows:
        if r["mint"] in seen:
            continue
        seen.add(r["mint"])
        r.update(M.ident(r["name"], r["symbol"]))
        r["ff"] = (floor_fold(r["symbol"]), floor_fold(r["name"]))
        r["rs"] = r["symbol"].strip().lower()
        out.append(r)
    return out


def main():
    launches_path, labels_path, out_dir = sys.argv[1:4]
    L = load(launches_path)
    labels = {}
    if os.path.exists(labels_path):
        for row in csv.DictReader(open(labels_path, encoding='utf-8', newline='')):
            labels[tuple(sorted((row["a"], row["b"])))] = row["label"].strip()

    # ---- every earlier launch each launch matches under any rule (candidate generation by inverted index)
    index = collections.defaultdict(list)
    by_uri = collections.defaultdict(list)
    earlier = []
    for j, r in enumerate(L):
        cand = set(by_uri.get(r["uri"], ()))
        for k in probe_keys(r):
            cand.update(index.get(k, ()))
        ms = sorted(i for i in cand if L[i]["uri"] == r["uri"] or matches(r, L[i], "T1")
                    or matches(r, L[i], "floor") or matches(r, L[i], "raw-symbol"))
        earlier.append(ms)
        for k in index_keys(r):
            index[k].append(j)
        by_uri[r["uri"]].append(j)

    def certain(a, b):
        return a["uri"] == b["uri"] or vkey(a) == vkey(b)

    # ---- distinct-identity pairs by stratum; stratified sample to label
    pairs = {}
    for j, ms in enumerate(earlier):
        for i in ms:
            a, b = L[i], L[j]
            if certain(a, b):
                continue
            s = stratum(a, b)
            if s is None:  # found only by raw-symbol / floor, which imply symbol equality: cannot happen
                continue
            pk = pair_key(a, b)
            pairs.setdefault(pk, (s, f"{a['name']} / {a['symbol']}", f"{b['name']} / {b['symbol']}"))
    # The sample is drawn once (when no labels exist) and then fixed: it is whatever the labels file covers.
    if labels:
        sampled = {pk for pk in labels if pk in pairs}
    else:
        rng = random.Random(SEED)
        sampled = set()
        for s in STRATA:
            ks = sorted(pk for pk, v in pairs.items() if v[0] == s)
            sampled.update(rng.sample(ks, min(SAMPLE_PER_STRATUM, len(ks))))
        with open(os.path.join(out_dir, "label_sample.csv"), "w", newline="", encoding='utf-8') as f:
            w = csv.writer(f, lineterminator='\n')
            w.writerow(["a", "b", "stratum", "label", "example_a", "example_b"])
            for pk in sorted(sampled, key=lambda k: (STRATA.index(pairs[k][0]), k)):
                w.writerow([pk[0], pk[1], pairs[pk][0], "", pairs[pk][1], pairs[pk][2]])

    # stratum precision from labelled pairs in the sample
    sp = {}
    for s in STRATA:
        labs = [labels.get(pk) for pk in sampled if pairs[pk][0] == s]
        S, D, U = labs.count("S"), labs.count("D"), labs.count("U")
        n_all = sum(1 for v in pairs.values() if v[0] == s)
        sp[s] = dict(pairs=n_all, sampled=len(labs), S=S, D=D, U=U, missing=len(labs) - S - D - U,
                     p=S / (S + D) if S + D else 0.0, ci=wilson(S, S + D))

    def p_same(a, b, bound="mid"):
        """Probability the pair is the same narrative: 1/0 when certain or labelled S/D; stratum share otherwise
        (U labels also take the stratum share). bound='lo' uses the Wilson lower bound and counts U as 0."""
        if certain(a, b):
            return 1.0
        pk = pair_key(a, b)
        lab = labels.get(pk)
        if lab == "S":
            return 1.0
        if lab == "D":
            return 0.0
        s = stratum(a, b)
        if s is None:  # no direct text signal: reached through a chain of fuzzy matches; counted as wrong
            return 0.0
        if bound == "lo":
            return 0.0 if lab == "U" else sp[s]["ci"][0]
        return sp[s]["p"]

    # ---- vamps: expected number, and the certain subset
    pv = []
    for j, ms in enumerate(earlier):
        pv.append(max([p_same(L[i], L[j]) for i in ms], default=0.0))
    pv_lo = [max([p_same(L[i], L[j], "lo") for i in ms], default=0.0) for j, ms in enumerate(earlier)]
    certain_v = {j for j, ms in enumerate(earlier) if any(certain(L[i], L[j]) for i in ms)}
    uri_v = {j for j, ms in enumerate(earlier) if any(L[i]["uri"] == L[j]["uri"] for i in ms)}
    dc_v = {j for j, ms in enumerate(earlier)
            if any(certain(L[i], L[j]) and L[i]["creator"] != L[j]["creator"] for i in ms)}
    exp_v = sum(pv)

    # copies.json for liveness_reads.py: certain vamps by a different creator, with their earlier cluster members
    copies = []
    for j in sorted(dc_v):
        mem = [i for i in earlier[j] if certain(L[i], L[j])]
        copies.append({"copy_sig": L[j]["signature"], "copy_time": L[j]["block_time"],
                       "members": [{"mint": L[i]["mint"], "launch_time": L[i]["block_time"]} for i in mem]})
    json.dump(copies, open(os.path.join(out_dir, "copies.json"), "w", encoding='utf-8', newline='\n'))

    # ---- sequential replay per operating point
    results = []
    for op, desc in OPERATING_POINTS:
        rooms, idx = [], collections.defaultdict(set)
        routed = 0
        c_mid = c_lo = 0.0
        c_certain = c_uri = c_dc = 0.0
        for j, r in enumerate(L):
            cands = set()
            for k in probe_keys(r):
                cands |= idx.get(k, set())
            best = None
            for rid in sorted(cands):
                faces = rooms[rid]
                tiers = []
                if matches(r, L[faces[0]], op):
                    tiers.append(M.TIER_RANK[M.text_tier(r, L[faces[0]], P, fuzzy=True)[0]])
                tiers += [M.TIER_RANK[M.text_tier(r, L[fi], P, fuzzy=False)[0]] for fi in faces[1:]
                          if exact_matches(r, L[fi], op)]
                if not tiers:
                    continue
                key = (max(tiers), -rid)
                if best is None or key > best[0]:
                    best = (key, rid, faces[0])
            if best is None:
                rooms.append([j])
                for k in index_keys(r):
                    idx[k].add(len(rooms) - 1)
                continue
            _, rid, hit = best
            rooms[rid].append(j)
            for k in (("s", r["sk"]), ("n", r["nk"])):
                if k[1]:
                    idx[k].add(rid)
            routed += 1
            pm = p_same(L[hit], r)
            c_mid += pm
            c_lo += p_same(L[hit], r, "lo")
            if j in certain_v:
                c_certain += pm
                c_uri += pm if j in uri_v else 0
                c_dc += pm if j in dc_v else 0
        results.append(dict(op=op, desc=desc, rooms=len(rooms), routed=routed, c_mid=c_mid, c_lo=c_lo,
                            c_certain=c_certain, c_uri=c_uri, c_dc=c_dc))

    t0, t1 = L[0], L[-1]
    hours = (t1["block_time"] - t0["block_time"]) / 3600
    o = ["<!-- generated by scripts/narrative/calibrate_text.py -->",
         f"**Sample:** {len(L):,} pump.fun launches (`create` / `create_v2` of "
         f"6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P), slots {t0['slot']:,}–{t1['slot']:,}, block times "
         f"{t0['block_time']}–{t1['block_time']} ({hours:.2f} hours, one contiguous window).", "",
         f"- Certain vamps (identical folded name and symbol, or identical metadata URI, to an earlier launch): "
         f"**{len(certain_v):,}** ({len(certain_v) / len(L):.1%} of launches). By a different creator: "
         f"{len(dc_v):,}. Identical metadata URI: {len(uri_v):,}.",
         f"- Expected vamps including different-identity copies (stratum estimates): **{exp_v:,.0f}** "
         f"(lower bound {sum(pv_lo):,.0f}).",
         f"- Different-identity pairs found by the loosest rule: {len(pairs):,}; stratified sample labelled: "
         f"{sum(v['S'] + v['D'] + v['U'] for v in sp.values()):,} (seed {SEED}, up to {SAMPLE_PER_STRATUM} per "
         f"stratum).", "",
         "### Per-signal precision on different-identity pairs (assistant labels, name and symbol only)", "",
         "| signal (strongest between the two) | pairs in sample window | labelled | S | D | U | "
         "precision S/(S+D) | 95% CI |", "|---|---|---|---|---|---|---|---|"]
    for s in STRATA:
        v = sp[s]
        o.append(f"| {s} | {v['pairs']:,} | {v['S'] + v['D'] + v['U']} | {v['S']} | {v['D']} | {v['U']} | "
                 f"{v['p']:.0%} | {v['ci'][0]:.0%}–{v['ci'][1]:.0%} |")
    o += ["", "### Routing replay (text only, every room treated as live)", "",
          "| operating point | rule | rooms formed | launches routed | precision (est.) | precision, pessimistic | "
          "recall of vamps (est.) | recall of certain vamps | of different-creator certain vamps | "
          "of identical-URI vamps |", "|---|---|---|---|---|---|---|---|---|---|"]
    for x in results:
        r = x["routed"] or 1
        o.append(f"| {x['op']} | {x['desc']} | {x['rooms']:,} | {x['routed']:,} | {x['c_mid'] / r:.1%} | "
                 f"{x['c_lo'] / r:.1%} | {x['c_mid'] / exp_v:.1%} | {x['c_certain'] / len(certain_v):.1%} | "
                 f"{x['c_dc'] / max(1, len(dc_v)):.1%} | {x['c_uri'] / max(1, len(uri_v)):.1%} |")
    o += ["", "- *precision (est.)*: certain and labelled routes count 1 or 0; unlabelled routes count their "
          "stratum's S/(S+D). *Pessimistic*: unlabelled routes at the stratum's Wilson lower bound, U as wrong.",
          "- *recall of vamps (est.)*: expected correct routes / expected vamps. The last three columns restrict "
          "the denominator to certain vamps (no labels needed to know they are vamps); a route still counts by "
          "the same-narrative test against the room's door 0. Identical-URI vamps are the one ground truth that "
          "does not depend on the text at all.",
          "- A route counts as correct only if the launch is the same narrative as the room's door 0."]
    open(os.path.join(out_dir, "text_calibration.md"), "w", encoding='utf-8', newline='\n').write("\n".join(o) + "\n")
    print("\n".join(o))


if __name__ == "__main__":
    main()
