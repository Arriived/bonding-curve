"""Usage: python3 scripts/secondary_matcher_marginal.py   (needs requirements-research.txt for the replay import)

Marginal quality of a SECONDARY (flagging) matcher: of the pairs it surfaces that the live name rule does
not route together, what share are genuinely the same narrative? Uses rule_candidates' own estimator."""
import sys, collections, csv, json
sys.path.insert(0, "scripts")
import rule_candidates as RC
C = RC.C
L = C.load(str(RC.LAUNCHES))
images, socials = RC.load_images(), RC.load_socials()
labels = {}
for row in csv.DictReader(open(RC.LABELS, encoding="utf-8", newline="")):
    labels[tuple(sorted((row["a"], row["b"])))] = row["label"].strip()
# estimator, as rule_candidates.main builds it
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
certain = lambda a, b: a["uri"] == b["uri"] or C.vkey(a) == C.vkey(b)
pairs = {}
for j, ms in enumerate(earlier):
    for i in ms:
        if not certain(L[i], L[j]) and (s := C.stratum(L[i], L[j])):
            pairs.setdefault(C.pair_key(L[i], L[j]), s)
sp = {}
for s in C.STRATA:
    labs = [labels.get(pk) for pk in pairs if pk in labels and pairs[pk] == s]
    S, D = labs.count("S"), labs.count("D")
    sp[s] = S / (S + D) if S + D else 0.0
def p_same(a, b):
    if certain(a, b): return 1.0, True
    lab = labels.get(C.pair_key(a, b))
    if lab in ("S", "D"): return (1.0 if lab == "S" else 0.0), True
    s = C.stratum(a, b)
    return (sp[s], True) if s else (0.0, False)

ident = RC.make_ident(confusables=True, split_invariant=True, translit=True)
key = RC.key_fn(ident, True)
ham = lambda a, b: bin(a ^ b).count("1")
for require in (None, "symbol", "word", "creator", "social"):
    rooms, by_key, by_sha, phs = [], {}, {}, []
    flagged = []           # (candidate, door0) the name rule did NOT route together
    for j, r in enumerate(L):
        k = key(r["name"], r["symbol"])
        rid = by_key.get(k) if k else None
        if rid is None and (m := images.get(r["mint"])):
            hits = [i for h, i in phs if ham(h, m[1]) <= 4]
            if (x := by_sha.get(m[0])) is not None: hits = [x] + [h for h in hits if h != x]
            c = ident(r["name"], r["symbol"]); words = {t for t in c["nt"] if len(t) >= 4}
            mine = socials.get(r["uri"], frozenset())
            for h in hits:
                d0 = L[rooms[h][0]]; e = ident(d0["name"], d0["symbol"])
                ok = True if require is None else {
                    "symbol": bool(c["sk"]) and c["sk"] == e["sk"],
                    "word": bool(words & {t for t in e["nt"] if len(t) >= 4}),
                    "creator": bool(r.get("creator")) and r.get("creator") == d0.get("creator"),
                    "social": bool(mine & socials.get(d0.get("uri"), frozenset()))}[require]
                if ok: flagged.append((r, d0)); break
        if rid is None:
            rooms.append([j])
            if k: by_key.setdefault(k, len(rooms) - 1)
            if (m := images.get(r["mint"])):
                by_sha.setdefault(m[0], len(rooms) - 1); phs.append((m[1], len(rooms) - 1))
        else:
            rooms[rid].append(j)
    ps = [p_same(d0, r) for r, d0 in flagged]
    known = [p for p, k_ in ps if k_]
    print(f"IMG p4" + (f" AND {require}" if require else " alone") +
          f": {len(flagged):4} flags the name rule misses | est. share genuine "
          f"{(sum(known)/len(known) if known else 0):.0%} | unmeasurable {len(ps)-len(known):3}")
