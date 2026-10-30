"""Float64 research ledger, validated against the Decimal reference in tests.

Quotes and trades are O(1); complete snapshots and invariant scans are O(tokens
* wallets). Float tolerances are explicit; this is not the financial reference.
"""
from dataclasses import dataclass
import math
import numpy as np


@dataclass(frozen=True)
class Fill:
    wallet: int
    token: int
    side: str
    quantity: float
    gross: float
    fee: float
    cash_change: float
    pre_price: float
    post_price: float


class FastBook:
    def __init__(self, n, wallets, p0, k, coupling, fee, cash, q0=0.0, reserve_capital=0.0):
        vals = [p0, k, coupling, fee, cash, reserve_capital]
        if not all(math.isfinite(x) and x >= 0 for x in vals):
            raise ValueError("Nonnegative finite model inputs required")
        if n < 1 or wallets < 1 or p0 <= 0 or coupling > 1 or fee >= 1:
            raise ValueError("Invalid ledger dimensions or parameters")
        self.p0, self.k, self.coupling, self.fee_rate = p0, k, coupling, fee
        self.q = np.broadcast_to(np.asarray(q0, dtype=float), (n,)).copy()
        if not np.all(np.isfinite(self.q)) or np.any(self.q < 0):
            raise ValueError("Invalid initial supplies")
        if np.any(self.q > 1e18):
            raise ValueError("Initial supplies exceed the reference input domain")
        self.Q = float(self.q.sum())
        self.q2 = float(np.dot(self.q, self.q))
        self.required = self.reserve_function()
        if reserve_capital and reserve_capital < self.required:
            raise ValueError(f"Starting capital {reserve_capital:,.2f} cannot back supplies; {self.required:,.2f} required")
        self.reserve = reserve_capital if reserve_capital else self.required
        self.buffer = self.reserve-self.required
        # Each wallet contributes its share of genesis backing and receives funded
        # positions. Trading cash is additional. No supply is created for free.
        self.holdings = np.broadcast_to(self.q/wallets, (wallets,n)).copy()
        genesis_basis = self.p0*self.q+self.k/2*self.q*((1-self.coupling)*self.q+self.coupling*self.Q)
        self.basis = np.broadcast_to(genesis_basis/wallets, (wallets,n)).copy()
        self.cash = np.broadcast_to(np.asarray(cash, dtype=float), (wallets,)).copy()
        self.realized = np.zeros(wallets)
        self.initial_wealth = self.cash+self.basis.sum(axis=1)
        self.initial_external = float(self.cash.sum()+self.reserve)
        self.fees = 0.0

    def reserve_function(self):
        return self.p0*self.Q+self.k/2*((1-self.coupling)*self.q2+self.coupling*self.Q*self.Q)

    def price(self, token):
        return self.p0+self.k*((1-self.coupling)*self.q[token]+self.coupling*self.Q)

    def prices(self):
        return self.p0+self.k*((1-self.coupling)*self.q+self.coupling*self.Q)

    def buy_quantity(self, token, budget):
        """Stable quadratic inverse of exact cost, including fee."""
        budget = max(0.0, budget)/(1+self.fee_rate)
        price = self.price(token)
        return min(max(0.,1e18-self.q[token]),2*budget/(price+math.sqrt(price*price+2*self.k*budget)))

    def execute(self, wallet, token, quantity, side, max_payment=None, min_receipt=None):
        if not 0 <= wallet < len(self.cash) or not 0 <= token < len(self.q):
            raise ValueError("Unknown wallet or token")
        if not math.isfinite(quantity) or quantity <= 0 or side not in ("buy", "sell"):
            raise ValueError("Invalid trade")
        if side == "sell" and quantity > self.holdings[wallet, token]:
            raise ValueError("Insufficient holdings")
        if side == "buy" and self.q[token]+quantity > 1e18:
            raise ValueError("Supply would exceed reference input domain")
        price = self.price(token)
        sign = 1 if side == "buy" else -1
        gross = price*quantity+sign*self.k*quantity*quantity/2
        fee = gross*self.fee_rate
        cash_change = -(gross+fee) if sign == 1 else gross-fee
        if -cash_change > self.cash[wallet]+1e-10:
            raise ValueError("Insufficient cash")
        if max_payment is not None and -cash_change > max_payment:
            raise ValueError("Maximum payment exceeded")
        if min_receipt is not None and cash_change < min_receipt:
            raise ValueError("Minimum receipt not met")
        if sign == 1:
            self.basis[wallet, token] += gross+fee
        else:
            held = self.holdings[wallet, token]
            removed = self.basis[wallet, token] if quantity == held else self.basis[wallet, token]*quantity/held
            self.basis[wallet, token] -= removed
            self.realized[wallet] += gross-fee-removed
        self.cash[wallet] += cash_change
        self.holdings[wallet, token] += sign*quantity
        old = self.q[token]
        self.q[token] += sign*quantity
        self.Q += sign*quantity
        self.q2 += self.q[token]**2-old**2
        self.required += sign*gross
        self.reserve += sign*gross
        self.fees += fee
        return Fill(wallet, token, side, quantity, gross, fee, cash_change, price, self.price(token))

    def assert_invariants(self):
        scale = max(1.0, self.initial_external, self.reserve)
        tol = 1e-9*scale
        assert np.all(self.q >= -1e-8) and np.all(self.holdings >= -1e-8), "Negative supply"
        assert np.all(self.cash >= -tol), "Negative cash"
        assert np.allclose(self.holdings.sum(axis=0), self.q, atol=1e-7, rtol=1e-9), "Holdings mismatch"
        assert math.isclose(self.Q, float(self.q.sum()), abs_tol=1e-7, rel_tol=1e-9), "Q drift"
        recomputed = self.p0*self.q.sum()+self.k/2*((1-self.coupling)*np.square(self.q).sum()+self.coupling*self.q.sum()**2)
        assert abs(self.required-recomputed) <= tol, "Backing drift"
        assert abs(self.reserve-self.required-self.buffer) <= tol, "Reserve mismatch"
        assert abs(float(self.cash.sum())+self.reserve+self.fees-self.initial_external) <= tol, "Cash drift"
        assert self.reserve >= -tol, "Reserve insolvency"
        return tol

