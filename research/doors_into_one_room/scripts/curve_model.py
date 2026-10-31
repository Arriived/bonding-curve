"""Permanent-curve candidates for the room: price impact, reserve ratio, exits.

All curves are price-as-a-function-of-curve-position q (tokens), with reserve
R(q) = integral of p from 0 to q. Units: USD, with SOL fixed at $150 only to
express pump.fun's 30-SOL virtual reserve and 85-SOL graduation in dollars.
Every candidate passes through two calibration points so the first $12.75k
behaves comparably:

    (R = 0,          p = 4500 / 1.073e9    = pump.fun opening price)
    (R = 12,750.80,  p = 17,250.80 / 2.799e8 = pump.fun price at graduation)

Outputs markdown tables to stdout. Deterministic; no randomness.
"""
import math
import sys

USD_PER_SOL = 150.0
X0 = 30*USD_PER_SOL                  # pump virtual quote reserve
Y0 = 1.073e9                         # pump virtual token reserve
K0 = X0*Y0
S1 = 793.1e6                         # pump graduation (tokens sold)
YG = Y0-S1
XG = K0/YG
R1 = XG-X0                           # 12,750.80
P0 = X0/Y0                           # opening price
P1 = XG/YG                           # price at R1
SUPPLY = 1e9
K1 = R1*(SUPPLY-S1)                  # internal pool constant after the switch


class Curve:
    name = ""

    def price(self, q): raise NotImplementedError
    def reserve(self, q): raise NotImplementedError
    def q_max(self): return float("inf")
    def locked(self): return 0.0

    def q_of_reserve(self, R):
        lo, hi = 0.0, 1.0
        while self.reserve(min(hi, self.q_max())) < R:
            if hi >= self.q_max():
                raise ValueError(f"{self.name}: reserve {R} unreachable")
            hi *= 2
        hi = min(hi, self.q_max())
        for _ in range(200):
            mid = (lo+hi)/2
            if self.reserve(mid) < R:
                lo = mid
            else:
                hi = mid
        return (lo+hi)/2

    def p_of_reserve(self, R):
        return self.price(self.q_of_reserve(R))


class PumpTwoPhase(Curve):
    """pump.fun virtual curve, then an internal constant-product pool (no LP tokens)."""
    name = "A. constant product, virtual reserves (pump.fun params, internal pool after 85 SOL)"

    def q_max(self): return SUPPLY*(1-1e-15)

    def price(self, q):
        if q <= S1:
            return K0/(Y0-q)**2
        y = SUPPLY-q
        return K1/y**2

    def reserve(self, q):
        if q <= S1:
            return K0/(Y0-q)-X0
        return K1/(SUPPLY-q)

    def locked(self):
        return K1/SUPPLY


class Power(Curve):
    """p = p0 + a q^n, through both calibration points."""
    def __init__(self, n):
        self.n = n
        self.q1 = R1/(P0+(P1-P0)/(n+1))
        self.a = (P1-P0)/self.q1**n
        self.name = f"B{n}. power curve p = p0 + a*q^{n}"

    def price(self, q): return P0+self.a*q**self.n
    def reserve(self, q): return P0*q+self.a*q**(self.n+1)/(self.n+1)


class Piecewise(Curve):
    """Segment 1: pump.fun virtual curve up to R1. Then linear price segments whose
    slope starts at the constant-product slope at the junction (C1-continuous) and is
    divided by `cut` at each later breakpoint (in reserve dollars)."""
    def __init__(self, breaks=(), cut=4.0, label=""):
        self.k = 2*K0/YG**3                        # dp/dq of the CP curve at S1
        self.segs = []                             # (q_start, p_start, slope, R_start)
        q, p, R, k = S1, P1, R1, self.k
        for rb in breaks:
            # advance along slope k until reserve reaches rb
            d = (-p+math.sqrt(p*p+2*k*(rb-R)))/k
            self.segs.append((q, p, k, R))
            q, p, R = q+d, p+k*d, rb
            k = k/cut
        self.segs.append((q, p, k, R))
        self.name = label

    def _seg(self, q):
        s = self.segs[0]
        for seg in self.segs:
            if q >= seg[0]:
                s = seg
        return s

    def price(self, q):
        if q <= S1:
            return K0/(Y0-q)**2
        q0, p0, k, _ = self._seg(q)
        return p0+k*(q-q0)

    def reserve(self, q):
        if q <= S1:
            return K0/(Y0-q)-X0
        q0, p0, k, R0 = self._seg(q)
        d = q-q0
        return R0+p0*d+k*d*d/2


CURVES = [PumpTwoPhase(), Power(1), Power(2),
          Piecewise((), label="C1. piecewise: pump.fun curve to 85 SOL, then linear price (C1-continuous)"),
          Piecewise((1e6, 10e6), cut=4.0,
                    label="C2. piecewise flattening: as C1, slope /4 at $1M and again at $10M reserve")]

RESERVES = (10e3, 100e3, 1e6, 10e6, 50e6)
TRADES = (100, 1e3, 10e3, 100e3)


def money(x):
    a = abs(x)
    if a >= 1e12: return f"${x/1e12:,.2f}T"
    if a >= 1e9: return f"${x/1e9:,.2f}B"
    if a >= 1e6: return f"${x/1e6:,.2f}M"
    if a >= 1e3: return f"${x/1e3:,.1f}k"
    return f"${x:,.2f}"


def pct(x):
    if abs(x) >= 10: return f"{x*100:,.0f}%"
    return f"{x*100:.2f}%"


def impact_table(c):
    rows = []
    for R in RESERVES:
        p = c.p_of_reserve(R)
        buys = [pct(c.p_of_reserve(R+b)/p-1) for b in TRADES]
        sells = []
        for b in TRADES:
            if b >= R-c.locked():
                sells.append("exceeds reserve")
            else:
                sells.append(pct(c.p_of_reserve(R-b)/p-1))
        rows.append(f"| {money(R)} | " + " | ".join(buys) + " | " + " | ".join(sells) + " |")
    head = ("| reserve | buy $100 | buy $1k | buy $10k | buy $100k | sell $100 | sell $1k | sell $10k | sell $100k |\n"
            "|---|---|---|---|---|---|---|---|---|")
    return head+"\n"+"\n".join(rows)


def state_table(c):
    rows = []
    p_r1 = c.p_of_reserve(R1)
    for R in RESERVES:
        q = c.q_of_reserve(R)
        p = c.price(q)
        mcap = p*q
        fdv = p*SUPPLY if isinstance(c, PumpTwoPhase) else float("nan")
        # average-price slippage for selling 1%, 10% and 50% of the reserve, versus marginal price
        slips = []
        for f in (.01, .10, .50):
            out = f*R
            dq = q-c.q_of_reserve(R-out)
            slips.append(pct(1-(out/dq)/p))
        fdv_s = money(fdv) if fdv == fdv else "n/a"
        rows.append(f"| {money(R)} | {p:.3e} | {p/p_r1:,.1f}× | {money(mcap)} | {fdv_s} | "
                    f"{mcap/R:,.1f}× | {q:.3e} | {' / '.join(slips)} |")
    head = ("| reserve | price ($/token) | price vs $12.75k level | notional mcap (price × tokens outstanding) | "
            "FDV (price × 1B) | mcap / reserve | tokens outstanding | avg-price slippage selling 1% / 10% / 50% of reserve |\n"
            "|---|---|---|---|---|---|---|---|")
    return head+"\n"+"\n".join(rows)


def reserve_at_mcap(c):
    out = []
    for m in (100e3, 1e6, 10e6, 100e6, 1e9):
        lo, hi = 0.0, 1.0
        f = lambda q: c.price(q)*q
        while hi < c.q_max() and f(min(hi, c.q_max())) < m:
            hi *= 2
        hi = min(hi, c.q_max())
        for _ in range(200):
            mid = (lo+hi)/2
            if f(mid) < m:
                lo = mid
            else:
                hi = mid
        q = (lo+hi)/2
        R = c.reserve(q)
        out.append(f"{money(R)} ({pct(R/m)})")
    return out


def main():
    print(f"<!-- generated by scripts/curve_model.py; SOL = ${USD_PER_SOL:.0f} -->")
    print(f"Calibration: opening price {P0:.4e} $/token; price {P1:.4e} at reserve {money(R1)}. "
          f"Internal-pool locked floor for curve A: {money(K1/SUPPLY)}.\n")
    for c in CURVES:
        print(f"### {c.name}\n")
        print("Price impact (marginal price after the trade vs before; fees excluded):\n")
        print(impact_table(c))
        print("\nState at each reserve level:\n")
        print(state_table(c))
        print()
    print("### Opening trades: price impact of the first buys (sniping profile)\n")
    print("| curve | $100 at reserve $0 | $1k at $0 | $10k at $0 | $100 at $1k | $1k at $1k |\n|---|---|---|---|---|---|")
    for c in CURVES:
        cells = []
        for R, b in ((0, 100), (0, 1e3), (0, 10e3), (1e3, 100), (1e3, 1e3)):
            cells.append(pct(c.p_of_reserve(R+b)/c.p_of_reserve(R)-1))
        print(f"| {c.name.split('.')[0]} | " + " | ".join(cells) + " |")
    print()
    print("### Worst-case notional mcap / reserve (geometric scan, 4,000 points, $100 to $50M)\n")
    print("| curve | max mcap / reserve | at reserve |\n|---|---|---|")
    for c in CURVES:
        best = (0.0, 0.0)
        for i in range(4000):
            R = 100*(5e7/100)**(i/3999)
            q = c.q_of_reserve(R)
            r = c.price(q)*q/R
            if r > best[0]:
                best = (r, R)
        print(f"| {c.name.split('.')[0]} | {best[0]:,.2f}× | {money(best[1])} |")
    print()
    print("### Reserve held at a given notional market cap (price × tokens outstanding)\n")
    print("| curve | $100k | $1M | $10M | $100M | $1B |\n|---|---|---|---|---|---|")
    for c in CURVES:
        print(f"| {c.name.split('.')[0]} | " + " | ".join(reserve_at_mcap(c)) + " |")
    print()
    # Continuity / sanity checks printed for the record.
    gap = None
    for c in CURVES:
        a, b = c.price(S1*(1-1e-12)), c.price(S1*(1+1e-12))
        if isinstance(c, PumpTwoPhase):
            # pump.fun's parameters are not exactly continuous at the switch:
            # K0/YG^2 = 6.1632e-5 vs R1/(SUPPLY-S1) = 6.1628e-5. Assert that known value.
            gap = b/a-1
            assert abs(gap-(R1/(SUPPLY-S1))/(XG/YG)+1) < 1e-9, "unexpected junction gap"
        else:
            assert abs(a/b-1) < 1e-6, f"price discontinuity in {c.name}"
        assert abs(c.reserve(c.q_of_reserve(1e6))-1e6) < 1e-3
    print(f"Checks: curve A has a price step of {gap*100:.4f}% at the 85-SOL switch (pump.fun parameters, "
          f"K0/YG² vs R1/206.9M); every other curve is continuous there; reserve inversion exact to $0.001.")


if __name__ == "__main__":
    sys.exit(main())
