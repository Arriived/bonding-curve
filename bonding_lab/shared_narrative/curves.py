"""Float64 curve functions for the shared-narrative study.

Two shapes, each operating on a small mutable state vector per curve:

* ``PumpShape``: constant product with virtual reserves (pump.fun-like), then
  graduation into a constant-product pool whose LP is locked. Parameters are
  research defaults, not a quote of any live deployment.
* ``LinearShape``: p = p0 + k*q, i.e. the existing ``bonding_lab.engine`` curve at
  coupling 0 (one token per curve). Parity with ``FastBook`` is tested.

All amounts are "gross": dollars entering/leaving the reserve. Fees are charged
outside the reserve by the ledger, so curve state is path independent.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class PumpShape:
    x0: float = 4500.0          # virtual quote reserve (30 SOL at $150)
    y0: float = 1.073e9         # virtual token reserve
    supply: float = 1e9         # total minted supply; paper mcap = price * supply
    grad_tokens: float = 793.1e6
    migration_fee: float = 0.0  # quote removed from reserve at graduation
    name: str = "pump"

    @property
    def k0(self):
        return self.x0*self.y0

    @property
    def x_grad(self):
        return self.k0/(self.y0-self.grad_tokens)

    @property
    def pool_tokens(self):
        return self.supply-self.grad_tokens

    # state: [phase, x, y, K]; phase 0 = curve (x includes virtual x0), 1 = pool
    def new_state(self):
        return [0, self.x0, self.y0, self.k0]

    def price(self, s):
        return s[1]/s[2]

    def mcap(self, s):
        return self.supply*s[1]/s[2]

    def reserve(self, s):
        """Real quote held by the curve/pool."""
        return s[1]-self.x0 if s[0] == 0 else s[1]

    def circulating(self, s):
        return self.y0-s[2] if s[0] == 0 else self.supply-s[2]

    def recoverable_gross(self, s):
        """Gross cash if every circulating token were sold (path independent)."""
        return s[1]-self.x0 if s[0] == 0 else s[1]-s[3]/self.supply

    def locked(self, s):
        return 0.0 if s[0] == 0 else s[3]/self.supply

    def buy(self, s, gross):
        """Mutates s; returns (tokens_out, migration_fee_paid)."""
        if gross <= 0:
            return 0.0, 0.0
        out = 0.0
        mig = 0.0
        if s[0] == 0:
            xg = self.x_grad
            if s[1]+gross < xg:
                x1 = s[1]+gross
                y1 = s[3]/x1
                out = s[2]-y1
                s[1], s[2] = x1, y1
                return out, 0.0
            used = xg-s[1]
            out = s[2]-(self.y0-self.grad_tokens)
            gross -= used
            real = xg-self.x0
            mig = min(self.migration_fee, real)
            s[0], s[1], s[2] = 1, real-mig, self.pool_tokens
            s[3] = s[1]*s[2]
        if gross > 0:
            x1 = s[1]+gross
            y1 = s[3]/x1
            out += s[2]-y1
            s[1], s[2] = x1, y1
        return out, mig

    def buy_gross_quantity(self, s, d):
        """Mutates s; exact gross for buying ``d`` tokens (used by parity tests)."""
        if s[0] == 0:
            left = s[2]-(self.y0-self.grad_tokens)
            if d < left:
                y1 = s[2]-d
                x1 = s[3]/y1
                g = x1-s[1]
                s[1], s[2] = x1, y1
                return g
            g = self.x_grad-s[1]
            d -= left
            real = self.x_grad-self.x0
            mig = min(self.migration_fee, real)
            s[0], s[1], s[2] = 1, real-mig, self.pool_tokens
            s[3] = s[1]*s[2]
        else:
            g = 0.0
        if d > 0:
            if d >= s[2]:
                raise ValueError("Pool cannot deliver that many tokens")
            y1 = s[2]-d
            x1 = s[3]/y1
            g += x1-s[1]
            s[1], s[2] = x1, y1
        return g

    def sell(self, s, tokens):
        """Mutates s; returns gross quote paid out of the reserve."""
        if tokens <= 0:
            return 0.0
        y1 = s[2]+tokens
        if s[0] == 0 and y1 > self.y0*(1+1e-9):
            raise ValueError("Sell exceeds tokens sold by the curve")
        if s[0] == 0:
            y1 = min(y1, self.y0)
        x1 = s[3]/y1
        if s[0] == 0:
            x1 = max(x1, self.x0)
        gross = s[1]-x1
        s[1], s[2] = x1, y1
        return gross

    def buy_gross_to_price(self, s, target):
        """Gross quote needed to lift the price to ``target`` (handles graduation)."""
        if target <= self.price(s):
            return 0.0
        if s[0] == 0:
            pg = self.x_grad/(self.y0-self.grad_tokens)
            if target <= pg:
                return math.sqrt(target*s[3])-s[1]
            first = self.x_grad-s[1]
            real = self.x_grad-self.x0
            x = real-min(self.migration_fee, real)
            k = x*self.pool_tokens
            return first+max(0.0, math.sqrt(target*k)-x)
        return math.sqrt(target*s[3])-s[1]

    def sell_gross_to_price(self, s, target):
        """Gross proceeds of the sale that lowers price to ``target`` (capped at floor)."""
        if target >= self.price(s):
            return 0.0
        x1 = math.sqrt(target*s[3])
        floor = self.x0 if s[0] == 0 else s[3]/self.supply
        return s[1]-max(x1, floor)


@dataclass(frozen=True)
class LinearShape:
    p0: float = 4500.0/1.073e9
    k: float = 2*(12750.803858520899-4500.0/1.073e9*793.1e6)/793.1e6**2
    name: str = "linear"

    def new_state(self):
        return [0, 0.0]  # [unused phase, q]

    def price(self, s):
        return self.p0+self.k*s[1]

    def mcap(self, s):
        return self.price(s)*s[1]

    def reserve(self, s):
        q = s[1]
        return self.p0*q+self.k/2*q*q

    def circulating(self, s):
        return s[1]

    def recoverable_gross(self, s):
        return self.reserve(s)

    def locked(self, s):
        return 0.0

    def buy(self, s, gross):
        if gross <= 0:
            return 0.0, 0.0
        p = self.price(s)
        # Same stable inverse as bonding_lab.fast.FastBook.buy_quantity.
        d = 2*gross/(p+math.sqrt(p*p+2*self.k*gross))
        s[1] += d
        return d, 0.0

    def buy_gross_quantity(self, s, d):
        """Exact gross for a quantity buy (FastBook convention)."""
        g = self.price(s)*d+self.k*d*d/2
        s[1] += d
        return g

    def sell(self, s, d):
        if d <= 0:
            return 0.0
        if d > s[1]*(1+1e-9)+1e-6:
            raise ValueError("Sell exceeds outstanding supply")
        d = min(d, s[1])
        g = self.price(s)*d-self.k*d*d/2
        s[1] -= d
        return g

    def buy_gross_to_price(self, s, target):
        p = self.price(s)
        if target <= p:
            return 0.0
        d = (target-p)/self.k
        return p*d+self.k*d*d/2

    def sell_gross_to_price(self, s, target):
        p = self.price(s)
        if target >= p:
            return 0.0
        d = min(s[1], (p-target)/self.k)
        return p*d-self.k*d*d/2


SHAPES = {"pump": PumpShape, "linear": LinearShape}
