"""If our matcher had consolidated these launches into rooms, how many runners would that have produced?

A "runner" here is a curve whose peak real SOL reserve crosses a threshold; pump.fun graduation is about 85 SOL.
Consolidation is a COUNTERFACTUAL, so it is bounded rather than predicted:

  max   the room's reserve is the best its members managed alone. Assumes consolidation adds nothing.
        Lower bound: it is what happens if buyers of a copy would simply not have bought at all.
  sum   the room's reserve is every member's peak added together. Upper bound, and it overstates, because the
        peaks are not simultaneous and because part of the demand for a copy is demand for a FRESH curve
        (cheap entry, lottery odds) that a room at 40 SOL does not offer.

Room assignment uses both liveness models, since a room that has died does not aggregate later copies at all.
peak_rs is null on 19.6% of rows (unresolved, or a curve not quoted in SOL); nulls count as 0, which understates
every aggregate below.
"""
import collections, glob, sys
sys.path.insert(0, "/home/user/matcher-service/services/matcher")
import pyarrow.parquet as pq
from matcher_service import rules

SP = "/tmp/claude-0/-home-user-bonding-curve/9283a73d-39d3-5b93-8f86-df883ca5b196/scratchpad"
C = ["name", "symbol", "t0", "peak_rs", "graduated"]
rows = []
for f in sorted(glob.glob(f"{SP}/hfpump/launches/*.parquet")) + sorted(glob.glob(f"{SP}/hfpump/legacy/*.parquet")):
    t = pq.read_table(f, columns=C)
    rows.extend(zip(*[t.column(c).to_pylist() for c in C]))
rows.sort(key=lambda r: r[2] or 0)
n = len(rows)
nulls = sum(1 for r in rows if r[3] is None)
print(f"{n:,} launches; peak_rs null on {nulls:,} ({100*nulls/n:.1f}%), counted as 0\n")

GRACE, IDLE = 3600, 21600
def rooms_of(mode):
    open_at, last, room_of, nxt = {}, {}, [], 0
    ids = {}
    for name, sym, t0, peak, grad in rows:
        k = rules.ident(name or "", sym or "")["key"]
        if not k:
            room_of.append(None); continue
        alive = k in open_at and (True if mode == "forever"
                                 else (t0 - open_at[k]) <= GRACE if mode == "grace"
                                 else (t0 - last.get(k, open_at[k])) <= IDLE)
        if not alive:
            open_at[k] = t0; ids[k] = nxt; nxt += 1
        last[k] = t0
        room_of.append(ids[k])
    return room_of, nxt

TH = [10, 25, 85, 200, 500]
actual = {t: sum(1 for r in rows if (r[3] or 0) >= t) for t in TH}
grads = sum(1 for r in rows if r[4] == 1)
print(f"=== what actually happened, one coin at a time")
print(f"  true graduations recorded: {grads:,} ({100*grads/n:.3f}% of launches)")
for t in TH:
    print(f"  launches whose peak reserve reached {t:>3} SOL: {actual[t]:>7,} ({100*actual[t]/n:5.3f}%)")

for mode, lab in (("forever", "live forever"), ("idle", "idle window"), ("grace", "grace only")):
    room_of, nroom = rooms_of(mode)
    smax = collections.defaultdict(float); ssum = collections.defaultdict(float)
    size = collections.Counter()
    for (name, sym, t0, peak, grad), rid in zip(rows, room_of):
        if rid is None: continue
        p = peak or 0.0
        smax[rid] = max(smax[rid], p); ssum[rid] += p
        size[rid] += 1
    merged = sum(1 for r in size.values() if r > 1)
    print(f"\n=== consolidation under '{lab}': {n:,} coins -> {nroom:,} rooms "
          f"({merged:,} rooms hold more than one coin)")
    print(f"  {'threshold':>10} {'rooms (max)':>13} {'rooms (sum)':>13} {'actual coins':>14} {'created (sum)':>15}")
    for t in TH:
        rmax = sum(1 for v in smax.values() if v >= t)
        rsum = sum(1 for v in ssum.values() if v >= t)
        # rooms that only clear the bar once their members are added together
        created = sum(1 for rid in ssum if ssum[rid] >= t and smax[rid] < t)
        print(f"  {t:>8} SOL {rmax:>13,} {rsum:>13,} {actual[t]:>14,} {created:>15,}")
