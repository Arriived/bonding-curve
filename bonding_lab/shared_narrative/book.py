"""Skin ledger: mints (skins) mapped onto reserve-holding curves.

Arm A maps skin i -> curve i. Arm B maps every skin -> curve 0. That map is the
only difference between the arms. Wallet constraints are enforced on every
trade: no wallet spends cash it does not have or sells skins it does not hold.
Fees (protocol + per-skin creator) and gas leave the reserve's accounting
entirely, so curve state is path independent and cash is conserved exactly up to
float tolerance (checked by ``check``).
"""
import numpy as np


class Rejected(ValueError):
    """Trade refused; no state was mutated."""


class SkinBook:
    def __init__(self, shape, curve_of_skin, cash, *, fee=.01, creator_share=.3, gas=.05):
        self.shape = shape
        self.map = np.asarray(curve_of_skin, dtype=int)
        if self.map.min() < 0:
            raise ValueError("Invalid skin map")
        self.n_skins = len(self.map)
        self.n_curves = int(self.map.max())+1
        self.states = [shape.new_state() for _ in range(self.n_curves)]
        self.cash = np.array(cash, dtype=float)
        if np.any(self.cash < 0) or not np.all(np.isfinite(self.cash)):
            raise ValueError("Nonnegative finite cash required")
        self.hold = np.zeros((len(self.cash), self.n_skins))
        self.fee, self.share, self.gas = float(fee), float(creator_share), float(gas)
        if not 0 <= self.fee < 1 or not 0 <= self.share <= 1 or self.gas < 0:
            raise ValueError("Invalid fee parameters")
        self.creator_fees = np.zeros(self.n_skins)
        self.creator_fees_buy = np.zeros(self.n_skins)
        self.skin_volume = np.zeros(self.n_skins)
        self.protocol_fees = 0.0
        self.gas_paid = 0.0
        self.migration_paid = 0.0
        self.sunk = 0.0               # launch costs and other explicit expenses
        self.terminal_fees = 0.0      # fees during terminal accounting liquidation
        self.terminal = False
        self.initial_total = float(self.cash.sum())
        self.trades = 0

    # ----- views -----
    def curve(self, skin):
        return self.states[self.map[skin]]

    def price(self, skin):
        return self.shape.price(self.curve(skin))

    def curve_prices(self):
        return np.array([self.shape.price(s) for s in self.states])

    def skin_prices(self):
        return self.curve_prices()[self.map]

    # ----- accounting helpers -----
    def _fees(self, skin, gross, buy=False):
        fee = gross*self.fee
        if self.terminal:
            self.terminal_fees += fee
        else:
            c = fee*self.share
            self.creator_fees[skin] += c
            if buy:
                self.creator_fees_buy[skin] += c
            self.protocol_fees += fee-c
            self.skin_volume[skin] += gross
        self.gas_paid += self.gas
        self.trades += 1
        return fee

    def spend(self, w, amount):
        """Explicit expense (e.g. a launch cost) leaving the system."""
        if amount < 0 or amount > self.cash[w]+1e-9:
            raise Rejected("Unfunded expense")
        self.cash[w] -= amount
        self.sunk += amount

    # ----- trading -----
    def buy(self, w, skin, budget):
        """Spend ``budget`` (incl. fee and gas). Returns (tokens, gross)."""
        if not 0 <= skin < self.n_skins:
            raise Rejected("Unknown skin")
        if budget > self.cash[w]+1e-9:
            raise Rejected("Buy exceeds wallet cash")
        budget = min(budget, self.cash[w])
        usable = budget-self.gas
        if usable <= 0:
            raise Rejected("Budget does not cover gas")
        gross = usable/(1+self.fee)
        tokens, mig = self.shape.buy(self.curve(skin), gross)
        self.migration_paid += mig
        fee = self._fees(skin, gross, buy=True)
        self.cash[w] -= gross+fee+self.gas
        if self.cash[w] < 0:
            self.cash[w] = 0.0 if self.cash[w] > -1e-9 else self.cash[w]
        self.hold[w, skin] += tokens
        return tokens, gross

    def sell(self, w, skin, tokens):
        """Sell ``tokens`` of ``skin``. Returns (net cash received, gross)."""
        held = self.hold[w, skin]
        if tokens <= 0 or tokens > held*(1+1e-12)+1e-12:
            raise Rejected("Sell exceeds wallet holdings")
        tokens = min(tokens, held)
        state = self.curve(skin)
        probe = list(state)
        gross = self.shape.sell(probe, tokens)
        net = gross-gross*self.fee-self.gas
        if self.cash[w]+net < -1e-12:
            raise Rejected("Proceeds do not cover gas")
        state[:] = probe
        self._fees(skin, gross)
        self.cash[w] += net
        self.hold[w, skin] = held-tokens if tokens < held else 0.0
        return net, gross

    def sell_all(self, w):
        total = 0.0
        for skin in np.flatnonzero(self.hold[w] > 0):
            try:
                total += self.sell(w, int(skin), self.hold[w, skin])[0]
            except Rejected:
                pass  # dust whose proceeds cannot cover gas stays held
        return total

    def execute(self, w, skin, quantity, side):
        """Quantity-denominated trade, FastBook convention (fee on top, no gas)."""
        state = self.curve(skin)
        if side == "buy":
            probe = list(state)
            gross = self.shape.buy_gross_quantity(probe, quantity)
            fee = gross*self.fee
            if gross+fee > self.cash[w]+1e-10:
                raise Rejected("Insufficient cash")
            state[:] = probe
            self.cash[w] -= gross+fee
            self.hold[w, skin] += quantity
        else:
            if quantity > self.hold[w, skin]*(1+1e-12):
                raise Rejected("Insufficient holdings")
            gross = self.shape.sell(state, quantity)
            fee = gross*self.fee
            self.cash[w] += gross-fee
            self.hold[w, skin] -= quantity
        c = fee*self.share
        self.creator_fees[skin] += c
        self.protocol_fees += fee-c
        return gross

    def convert(self, w, src, dst, tokens):
        """Arm B 1:1 skin conversion against the shared reserve (no price effect)."""
        if self.map[src] != self.map[dst]:
            raise Rejected("Skins do not share a reserve")
        if tokens > self.hold[w, src]*(1+1e-12):
            raise Rejected("Conversion exceeds holdings")
        tokens = min(tokens, self.hold[w, src])
        self.hold[w, src] -= tokens
        self.hold[w, dst] += tokens

    # ----- curve metrics -----
    def reserves(self):
        return np.array([self.shape.reserve(s) for s in self.states])

    def recoverable(self):
        """Net cash if all holders of each curve sold (fee outside reserve; gas ignored)."""
        return np.array([self.shape.recoverable_gross(s) for s in self.states])*(1-self.fee)

    def mcaps(self):
        return np.array([self.shape.mcap(s) for s in self.states])

    def locked(self):
        return np.array([self.shape.locked(s) for s in self.states])

    def check(self):
        scale = max(1.0, self.initial_total)
        tol = 1e-8*scale
        assert np.all(self.cash >= -1e-9), "negative cash"
        assert np.all(self.hold >= -1e-6), "negative holdings"
        total = (self.cash.sum()+self.reserves().sum()+self.protocol_fees+self.creator_fees.sum()
                 +self.gas_paid+self.migration_paid+self.sunk+self.terminal_fees)
        assert abs(total-self.initial_total) <= tol, f"cash conservation {total-self.initial_total}"
        per_curve = np.zeros(self.n_curves)
        np.add.at(per_curve, self.map, self.hold.sum(axis=0))
        circ = np.array([self.shape.circulating(s) for s in self.states])
        assert np.allclose(per_curve, circ, rtol=1e-7, atol=1e-3), "unbacked supply"
        return True
