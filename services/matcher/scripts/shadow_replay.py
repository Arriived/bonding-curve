"""Replay the live matcher over collected launches: routing, merge attribution, and the value of each fold.

Input is one or more `launches.jsonl` files from `watcher.watch` or `watcher.backfill`. Rows are deduplicated on
mint and replayed in true chronological order, which matters: the backfill writes newest first, so replaying a
file as written inverts every routing decision.

Four measurements, each answering a question the synthetic evasion benchmark cannot:

  routing      what our launchpad would have done with each launch, splitting doors opened by a *different*
               creator (impersonation) from doors opened by the launch's own creator (one wallet spamming).
  merges       which lenient rule each room owes its merge to, so a false merge can be attributed. Rooms are
               also ranked by how much their members' raw names differ: false merges surface at the top.
  naive        the full rule stack against NFKC + strip non-alphanumerics + uppercase and nothing else. This is
               the honest measure of what the folds are worth on organic traffic.
  multifold    the blast radius of MULTI_FOLD (rn -> m, vv -> w): keys moved, rooms merged that would otherwise
               be separate, rooms split that would otherwise be one.

Door share rises with the length of the window, because rooms stay live for the whole replay, so a figure is
meaningless without the span this prints. Nothing is signed or sent.

Usage:
  python3 scripts/shadow_replay.py LAUNCHES.jsonl [MORE.jsonl ...] [--only routing,merges,naive,multifold]
Run from services/matcher.
"""
import argparse
import collections
import json
import sys
import time
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from matcher_service import rules  # noqa: E402
from watcher.shadow import Shadow  # noqa: E402


def load(paths):
    rows, seen = [], set()
    for p in paths:
        for line in Path(p).open(encoding="utf-8"):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not r.get("mint") or r["mint"] in seen:
                continue
            seen.add(r["mint"])
            rows.append(r)
    rows.sort(key=lambda r: (r.get("ts") or 0, r.get("signature") or ""))
    return rows


def naive_key(name):
    """The cheapest matcher anyone would write: NFKC, alphanumerics only, upper case."""
    s = unicodedata.normalize("NFKC", name)
    return "".join(ch for ch in s if ch.isalnum()).upper() or None


def live_key(row):
    return rules.ident(row["name"], row["symbol"])["key"]


def strict(name):
    """Baseline for merge attribution: identical before any folding at all."""
    return "".join(ch for ch in unicodedata.normalize("NFKC", name) if ch.isalnum()).upper()


def pct(a, b):
    return f"{100 * a / b:5.1f}%" if b else "    -"


def routing(rows):
    sh = Shadow()
    dec = collections.Counter()
    other = same = 0
    for r in rows:
        d = sh.route(r)
        dec[d["decision"]] += 1
        if d["decision"] == "door":
            if d["same_creator_as_door0"]:
                same += 1
            else:
                other += 1
    n = len(rows)
    print(f"=== routing ({n:,} launches)")
    print(f"  new room                {dec['new_room']:>8,} {pct(dec['new_room'], n)}")
    print(f"  door                    {dec['door']:>8,} {pct(dec['door'], n)}")
    print(f"    different creator     {other:>8,} {pct(other, n)}   impersonation")
    print(f"    same creator          {same:>8,} {pct(same, n)}   one wallet spamming")
    print(f"  refused (no key)        {dec['no_key']:>8,} {pct(dec['no_key'], n)}")
    sizes = collections.Counter(room["doors"] for room in sh.rooms)
    got = sum(v for k, v in sizes.items() if k)
    print(f"  rooms {len(sh.rooms):,}; {got:,} ({pct(got, len(sh.rooms)).strip()}) received a door; "
          f"largest {max(sizes):,} doors")


def rooms_by(rows, keyfn):
    d = collections.defaultdict(list)
    for r in rows:
        k = keyfn(r)
        if k:
            d[k].append(r)
    return d


def merges(rows, top=12):
    occupied = {k: v for k, v in rooms_by(rows, live_key).items() if len(v) >= 2}
    cause = collections.Counter()
    buckets = collections.defaultdict(list)
    for k, mem in occupied.items():
        if len({strict(r["name"]) for r in mem}) == 1:
            cause["identical before any folding"] += 1
            continue
        full = {rules.name_letters(r["name"]) for r in mem}
        if len(full) > 1 and len({rules._strip_affixes(f) for f in full}) == 1:
            cause["affix strip (rule I)"] += 1
            buckets["rule I"].append((k, mem))
            continue
        unfolded = {strict(r["name"]).translate(rules.DIGIT_FOLD) for r in mem}
        if len(unfolded) > 1:
            cause["confusables / digit / L-I fold (rules B, C)"] += 1
            buckets["rules B, C"].append((k, mem))
            continue
        cause["case, spacing or punctuation only"] += 1
    print(f"\n=== what made each merge ({len(occupied):,} rooms with 2+ members)")
    for c, n in cause.most_common():
        print(f"  {n:>7,} {pct(n, len(occupied))}  {c}")

    print(f"\n=== rooms whose members' raw names differ most (false-merge suspects)")
    ranked = sorted(occupied.items(), key=lambda t: -len({r["name"] for r in t[1]}))
    for k, mem in ranked[:top]:
        names = collections.Counter(r["name"] for r in mem)
        print(f"  {k.replace(chr(0), '|')!r:30} {len(mem):>5} members, {len(names):>3} names: " +
              ", ".join(f"{n!r}x{c}" for n, c in names.most_common(4)))


def naive(rows):
    def doors(keyfn):
        live, d = set(), 0
        for r in rows:
            k = keyfn(r)
            if not k:
                continue
            if k in live:
                d += 1
            else:
                live.add(k)
        return d, len(live)

    full_d, full_r = doors(live_key)
    nv_d, nv_r = doors(lambda r: naive_key(r["name"]))
    print(f"\n=== the full rule stack against the cheapest possible matcher")
    print(f"  {'live rule (A+B+I+C)':34} {full_d:>8,} doors {pct(full_d, len(rows))}  {full_r:>8,} rooms")
    print(f"  {'NFKC + alnum + upper, nothing else':34} {nv_d:>8,} doors {pct(nv_d, len(rows))}  {nv_r:>8,} rooms")
    print(f"  the folds add {full_d - nv_d:,} doors: {100 * (full_d - nv_d) / len(rows):+.1f}pp, "
          f"{100 * (full_d - nv_d) / max(1, nv_d):+.1f}% relative")


def multifold(rows, top=10):
    def keys():
        rules.ident.cache_clear()
        return {r["mint"]: live_key(r) for r in rows}

    saved = rules.MULTI_FOLD
    with_fold = keys()
    rules.MULTI_FOLD = ()
    without = keys()
    rules.MULTI_FOLD = saved
    rules.ident.cache_clear()

    moved = [r for r in rows if with_fold[r["mint"]] != without[r["mint"]]]
    print(f"\n=== MULTI_FOLD {saved} blast radius")
    print(f"  moves the on-chain key of {len(moved):,} launches ({100 * len(moved) / len(rows):.2f}%)")

    def occupied(k):
        return {a: b for a, b in rooms_by(rows, lambda r: k[r["mint"]]).items() if len(b) >= 2}

    rw, ro = occupied(with_fold), occupied(without)
    print(f"  rooms with the fold {len(rw):,}; without it {len(ro):,}")
    merged = [(k, m) for k, m in rw.items() if len({without[r["mint"]] for r in m}) > 1]
    print(f"  rooms the fold merges that would otherwise be separate: {len(merged)}")
    for k, mem in sorted(merged, key=lambda t: -len(t[1]))[:top]:
        names = collections.Counter(r["name"] for r in mem)
        print(f"    {k.replace(chr(0), '|')!r:24} " + ", ".join(f"{n!r}x{c}" for n, c in names.most_common(4)))
    if moved:
        print(f"  most affected names:")
        for n, c in collections.Counter(r["name"] for r in moved).most_common(top):
            print(f"    {c:>4}x {n!r:34} -> {rules.name_letters(n)!r}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("files", nargs="+")
    ap.add_argument("--only", default="routing,merges,naive,multifold",
                    help="comma-separated subset of routing,merges,naive,multifold")
    a = ap.parse_args()

    rows = load(a.files)
    if not rows:
        sys.exit("no launches found")
    span = (rows[-1].get("ts", 0) - rows[0].get("ts", 0)) / 3600
    print(f"{len(rows):,} unique launches over {span:.1f}h "
          f"({time.strftime('%d %b %H:%M', time.gmtime(rows[0]['ts']))} -> "
          f"{time.strftime('%d %b %H:%M', time.gmtime(rows[-1]['ts']))} UTC)\n")
    want = {s.strip() for s in a.only.split(",")}
    for name, fn in (("routing", routing), ("merges", merges), ("naive", naive), ("multifold", multifold)):
        if name in want:
            fn(rows)


if __name__ == "__main__":
    main()
