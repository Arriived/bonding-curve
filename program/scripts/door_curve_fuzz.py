"""Independent check of the paired-door curve math: an exact-integer port of math.rs `door_integral` and
`door_advance`, fuzzed for solvency.

Properties:
  1. Buying with R room tokens and selling the door tokens straight back never returns more than R.
  2. door_advance never moves `sold` backwards.
  3. Over random buy/sell sequences, a door's backing never falls below integral(sold), the room tokens its
     holders can redeem.
  4. swap_doors round trips (A to B, then all of it back to A) never return more door-A tokens than went in, and
     both doors stay solvent; the 1% fee is charged as lib.rs charges it (ceil of SWAP_FEE_BPS).
  5. Splitting: buying with R room tokens in k pieces never yields more door tokens than one buy of R, and selling
     in k pieces returns exactly what one sell returns (the floors telescope).
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


SWAP_FEE_BPS = int(re.search(r"pub const SWAP_FEE_BPS: u(?:16|64) = ([0-9_]+);", text).group(1).replace("_", ""))
assert "ratio(room_tokens, SWAP_FEE_BPS, true)" in (SRC.parent / "lib.rs").read_text(), "swap fee rounding changed"


def swap(vq_a, s_a, b_a, vq_b, s_b, b_b, x):
    """lib.rs swap_doors: x door-A tokens in. Returns new (s_a, b_a, s_b, b_b, tokens_out) or None if refused."""
    nxt_a = s_a - x
    room = integral(vq_a, s_a) - integral(vq_a, nxt_a)
    fee = -(-room * SWAP_FEE_BPS // 10_000)
    net = room - fee
    if net <= 0 or room > b_a:
        return None
    nxt_b = advance(vq_b, s_b, net)
    out = nxt_b - s_b
    if out <= 0:
        return None
    return nxt_a, b_a - room, nxt_b, b_b + net, out


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
    swap_gain = swap_insolvent = swaps = 0
    for _ in range(max(1, n // 20)):
        vq_a, vq_b = rng.randint(10**9, 10**15), rng.randint(10**9, 10**15)
        s_a = s_b = b_a = b_b = 0
        try:
            for r in (rng.randint(10**6, 10**14), rng.randint(10**6, 10**14)):
                nxt = advance(vq_a, s_a, r); b_a += r; s_a = nxt
            r = rng.randint(10**6, 10**14); nxt = advance(vq_b, s_b, r); b_b += r; s_b = nxt
        except Exhausted:
            continue
        x = rng.randint(1, s_a)
        try:
            one = swap(vq_a, s_a, b_a, vq_b, s_b, b_b, x)
            if one is None:
                continue
            s_a2, b_a2, s_b2, b_b2, got_b = one
            back_ = swap(vq_b, s_b2, b_b2, vq_a, s_a2, b_a2, got_b)
        except Exhausted:
            continue
        swaps += 1
        if back_ is not None:
            s_b3, b_b3, s_a3, b_a3, got_a = back_
            swap_gain += got_a > x
            swap_insolvent += b_a3 < integral(vq_a, s_a3) or b_b3 < integral(vq_b, s_b3)
        swap_insolvent += b_a2 < integral(vq_a, s_a2) or b_b2 < integral(vq_b, s_b2)
    split_gain = split_sell_diff = splits = 0
    for _ in range(max(1, n // 40)):
        vq, sold = rng.randint(10**9, 10**15), rng.randint(0, 10**14)
        r, k = rng.randint(10**3, 10**13), rng.randint(2, 50)
        try:
            single = advance(vq, sold, r) - sold
            s_, left = sold, r
            for i in range(k):
                piece = left if i == k - 1 else max(1, left // (k - i))
                left -= piece
                s_ = advance(vq, s_, piece)
        except Exhausted:
            continue
        splits += 1
        pieces = s_ - sold
        split_gain += pieces > single
        top = sold + single
        x = rng.randint(1, single) if single else 0
        one_sell = integral(vq, top) - integral(vq, top - x)
        parts, cur, left = 0, top, x
        for i in range(k):
            piece = left if i == k - 1 else left // (k - i)
            parts += integral(vq, cur) - integral(vq, cur - piece)
            cur -= piece
            left -= piece
        split_sell_diff += parts != one_sell
    print(f"buys checked {n - exh:,} (exhausted {exh:,}); round-trip gains {rt}; non-monotone {mono}; "
          f"max rounding kept {worst:,} base units; sequences with backing below redeemable {back}")
    print(f"swap round trips {swaps:,} (fee {SWAP_FEE_BPS} bps): gains {swap_gain}; insolvent states {swap_insolvent}; "
          f"split buys {splits:,}: pieces beat one buy {split_gain}; split sells differing from one sell {split_sell_diff}")
    sys.exit(1 if rt or mono or back or swap_gain or swap_insolvent or split_gain or split_sell_diff else 0)


if __name__ == "__main__":
    main()
