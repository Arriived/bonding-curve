"""Run every example in a directory through matcher.decide and check the expected decision.

Usage: python3 run_examples.py <dir>
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from matcher import decide  # noqa: E402


def main():
    d = sys.argv[1]
    bad = 0
    for f in sorted(os.listdir(d)):
        if not f.endswith(".json"):
            continue
        inp = json.load(open(os.path.join(d, f), encoding="utf-8"))
        exp = inp.pop("expect")
        out = decide(inp)
        got = (out["decision"], out.get("room_id"))
        ok = got == (exp["decision"], exp["room_id"])
        bad += not ok
        detail = out.get("rule") or "; ".join(f"room {e['room_id']}: {e['text']}, "
                                              f"{'live' if e['live'] else 'not live: ' + e['live_reason']}"
                                              for e in out["evaluated"])
        print(f"{'ok  ' if ok else 'FAIL'} {f[:-5]}: {got[0]}{'' if got[1] is None else ' ' + str(got[1])}  ({detail})")
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
