"""Independent check of the paired-door curve math: an exact-integer port of math.rs `door_integral` and
`door_advance`, fuzzed for solvency.

Properties:
  1. Buying with R room tokens and selling the door tokens straight back never returns more than R.
  2. door_advance never moves `sold` backwards.
  3. Over random buy/sell sequences, a door's backing never falls below integral(sold), the room tokens its
     holders can redeem.
The constants are read from math.rs, so the port fails loudly if the program's constants change.

Usage: python3 program/scripts/door_curve_fuzz.py [--iterations N]   (no dependencies; about 30 s at the default)
"""
import random
import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "programs/doors_v1/src/math.rs"
text = SRC.read_text()
U = int(re.search(r"pub const U: u64 = ([0-9_]+);", text).group(1).replace("_", ""))
B = int(re.search(r"pub const DOOR_VIRTUAL_BASE: u64 = ([0-9_]+);", text).group(1).replace("_", ""))
assert "numerator / u128::from(DOOR_VIRTUAL_BASE - sold)" in text, "door_integral changed; update the port"
assert "(target * u128::from(DOOR_VIRTUAL_BASE) - 1) / (virtual_quote + target)" in text, "door_advance changed"


class Exhausted(Exception):
    pass


def integral(vq, sold):
    assert vq > 0 and sold <= U
    return vq * sold // (B - sold)


def advance(vq, sold, r):
    target = integral(vq, sold) + r + 1
    nxt = (target * B - 1) // (vq + target)
    if nxt > U:
        raise Exhausted
    return nxt


def main():
    n = int(sys.argv[sys.argv.index("--iterations") + 1]) if "--iterations" in sys.argv else 400_000
    rng = random.Random(20261107)
    rt = mono = back = exh = worst = 0
    for _ in range(n):
        vq = rng.choice([rng.randint(1, 10**6), rng.randint(10**6, 10**12), rng.randint(10**12, 10**15),
                         rng.randint(10**15, 10**17)])
        sold = rng.choice([0, rng.randint(0, 10**9), rng.randint(0, U), U - rng.randint(0, 10**6)])
        r = rng.choice([1, rng.randint(1, 10**6), rng.randint(1, 10**12), rng.randint(1, 10**15)])
        try:
            nxt = advance(vq, sold, r)
        except Exhausted:
            exh += 1
            continue
        if nxt < sold:
            mono += 1
            continue
        got = integral(vq, nxt) - integral(vq, sold)
        rt += got > r
        worst = max(worst, r - got)
    for _ in range(max(1, n // 130)):
        vq, sold, backing = rng.randint(10**9, 10**15), 0, 0
        for _ in range(60):
            if rng.random() < 0.6:
                r = rng.randint(1, 10**14)
                try:
                    nxt = advance(vq, sold, r)
                except Exhausted:
                    continue
                backing, sold = backing + r, nxt
            elif sold:
                x = rng.randint(1, sold)
                out = integral(vq, sold) - integral(vq, sold - x)
                if out > backing:
                    back += 1
                    break
                backing, sold = backing - out, sold - x
            if backing < integral(vq, sold):
                back += 1
                break
    print(f"buys checked {n - exh:,} (exhausted {exh:,}); round-trip gains {rt}; non-monotone {mono}; "
          f"max rounding kept {worst:,} base units; sequences with backing below redeemable {back}")
    sys.exit(1 if rt or mono or back else 0)


if __name__ == "__main__":
    main()
