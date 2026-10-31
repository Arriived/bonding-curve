"""Decimal reference for the pump-shaped skin ledger.

Reuses ``bonding_lab.engine``'s 160-digit ``precise`` context, ``decimal`` input
validation and ``RejectedTrade``. The linear-shape reference is ``engine.Curve``
itself (coupling 0 = Arm A, coupling 1 = Arm B); see tests.

Cash conservation is exact: each trade's gross amount is computed once and
moved between wallet, reserve and fee accounts. The constant-product invariant
holds up to the 1e-40 quote quantum, rounded in the pool's favour.
"""
from decimal import Decimal, ROUND_CEILING
from ..engine import RejectedTrade, decimal, precise

ZERO = Decimal(0)
QUANTUM = Decimal("1e-40")


def ceil40(v):
    """Pool-favourable rounding; keeps every later sum exact at 160 digits."""
    return v.quantize(QUANTUM, rounding=ROUND_CEILING)


class PumpReference:
    @precise
    def __init__(self, curve_of_skin, wallets, cash, *, x0="4500", y0="1073000000",
                 supply="1000000000", grad_tokens="793100000", fee="0.01", creator_share="0.3"):
        self.map = list(curve_of_skin)
        self.x0, self.y0 = decimal(x0), decimal(y0)
        self.supply, self.grad = decimal(supply), decimal(grad_tokens)
        self.fee, self.share = decimal(fee), decimal(creator_share)
        self.k0 = self.x0*self.y0
        self.xg = ceil40(self.k0/(self.y0-self.grad))
        n = max(self.map)+1
        self.states = [[0, self.x0, self.y0, self.k0] for _ in range(n)]
        self.cash = [decimal(cash) for _ in range(wallets)]
        self.hold = [[ZERO]*len(self.map) for _ in range(wallets)]
        self.creator = [ZERO]*len(self.map)
        self.protocol = ZERO
        self.initial = sum(self.cash, ZERO)

    def reserve(self, s):
        return s[1]-self.x0 if s[0] == 0 else s[1]

    @precise
    def price(self, skin):
        s = self.states[self.map[skin]]
        return s[1]/s[2]

    @precise
    def _buy_gross(self, s, d):
        if s[0] == 0:
            left = s[2]-(self.y0-self.grad)
            if d < left:
                y1 = s[2]-d
                x1 = ceil40(s[3]/y1)
                g = x1-s[1]
                s[1], s[2] = x1, y1
                return g
            g = self.xg-s[1]
            d -= left
            real = self.xg-self.x0
            s[0], s[1], s[2] = 1, real, self.supply-self.grad
            s[3] = s[1]*s[2]
        else:
            g = ZERO
        if d > 0:
            if d >= s[2]:
                raise RejectedTrade("Pool cannot deliver that many tokens")
            y1 = s[2]-d
            x1 = ceil40(s[3]/y1)
            g += x1-s[1]
            s[1], s[2] = x1, y1
        return g

    @precise
    def execute(self, w, skin, quantity, side):
        d = decimal(quantity)
        if d <= 0 or side not in ("buy", "sell"):
            raise RejectedTrade("Positive quantity and buy/sell side required")
        s = self.states[self.map[skin]]
        if side == "buy":
            probe = list(s)
            gross = self._buy_gross(probe, d)
            fee = gross*self.fee
            if gross+fee > self.cash[w]:
                raise RejectedTrade("Insufficient wallet cash")
            s[:] = probe
            self.cash[w] -= gross+fee
            self.hold[w][skin] += d
        else:
            if d > self.hold[w][skin]:
                raise RejectedTrade("Insufficient wallet token holdings")
            y1 = s[2]+d
            x1 = ceil40(s[3]/y1)
            if s[0] == 0 and x1 < self.x0:
                raise RejectedTrade("Sell below curve floor")
            gross = s[1]-x1
            fee = gross*self.fee
            s[1], s[2] = x1, y1
            self.cash[w] += gross-fee
            self.hold[w][skin] -= d
        c = fee*self.share
        self.creator[skin] += c
        self.protocol += fee-c
        return gross

    @precise
    def assert_invariants(self):
        for row in self.hold:
            assert all(v >= 0 for v in row), "Negative holdings"
        assert all(c >= 0 for c in self.cash), "Negative cash"
        reserves = sum((self.reserve(s) for s in self.states), ZERO)
        total = sum(self.cash, ZERO)+reserves+self.protocol+sum(self.creator, ZERO)
        assert total == self.initial, "Cash conservation failure"
        for i, s in enumerate(self.states):
            assert ZERO <= s[1]*s[2]-s[3] <= s[2]*QUANTUM, "Constant product drift"
            held = sum((self.hold[w][j] for w in range(len(self.hold)) for j in range(len(self.map))
                        if self.map[j] == i), ZERO)
            circ = self.y0-s[2] if s[0] == 0 else self.supply-s[2]
            assert held == circ, "Unbacked supply"
