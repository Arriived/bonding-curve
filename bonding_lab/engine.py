"""Precise reference ledger. No token or cash allocation bypasses this ledger.

Inputs: finite nonnegative decimals, at most 18 fractional places, <= 1e18.
160-digit arithmetic covers the documented bounded domain without cash rounding.
This is an off-chain mathematical ledger, not USDC's six-decimal settlement model.
"""

from dataclasses import dataclass
from decimal import Decimal, localcontext
from functools import wraps
from types import MappingProxyType
from collections.abc import Sequence

ZERO = Decimal(0)
ONE = Decimal(1)
LIMIT = Decimal("1e18")


class RejectedTrade(ValueError):
    """An invalid request; the ledger has not been mutated."""


def precise(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        with localcontext() as ctx:
            ctx.prec = 160
            return fn(*args, **kwargs)
    return wrapped


def decimal(value):
    """Public input validation; floats are converted through their decimal string."""
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise RejectedTrade("Expected a finite decimal") from exc
    if not result.is_finite() or result < 0 or result > LIMIT:
        raise RejectedTrade("Value must be finite and between zero and 1e18")
    if result.as_tuple().exponent < -18:
        raise RejectedTrade("At most 18 fractional decimal places are supported")
    return result


@dataclass(frozen=True)
class Parameters:
    p0: Decimal = Decimal("0.01")
    k: Decimal = Decimal("0.0001")
    coupling: Decimal = Decimal("0.25")
    fee_rate: Decimal = Decimal("0.003")

    def __post_init__(self):
        for name in ("p0", "k", "coupling", "fee_rate"):
            object.__setattr__(self, name, decimal(getattr(self, name)))
        if self.coupling > 1 or self.fee_rate >= 1:
            raise RejectedTrade("Coupling must be <= 1; fee rate must be < 1")
        if self.p0 <= 0:
            raise RejectedTrade("The minimum marginal price must be positive")


@dataclass(frozen=True)
class Wallet:
    cash: Decimal
    holdings: Sequence
    cost_basis: Sequence
    realized_pnl: Decimal


class Balances(Sequence):
    """Read-only public view; the ledger updates the private backing list in O(1)."""
    def __init__(self, values):
        self._values = list(values)

    def __getitem__(self, index):
        return self._values[index]

    def __len__(self):
        return len(self._values)


@dataclass(frozen=True)
class Trade:
    wallet: str
    token: int
    side: str
    quantity: Decimal
    gross: Decimal
    fee: Decimal
    cash_change: Decimal
    pre_price: Decimal
    post_price: Decimal


class Curve:
    """O(1) quotes and execution via cached Q and sum(q_i**2).

    Parameters and public views are immutable. Changing the model requires a new
    curve and explicit funding. Fees belong to a separate treasury, never backing.
    """

    def __init__(self, params=None):
        self._params = params or Parameters()
        self._q = []
        self._names = []
        self._wallets = {}
        self._Q = ZERO
        self._squares = ZERO
        self._required = ZERO
        self._reserve = ZERO
        self._buffer = ZERO
        self._fees = ZERO
        self._initial_cash = ZERO

    @property
    def params(self):
        return self._params

    @property
    def supplies(self):
        return tuple(self._q)

    @property
    def token_names(self):
        return tuple(self._names)

    @property
    def wallets(self):
        return MappingProxyType(self._wallets)

    @property
    def total_supply(self):
        return self._Q

    @property
    def reserve(self):
        return self._reserve

    @property
    def required_reserve(self):
        return self._required

    @property
    def buffer(self):
        return self._buffer

    @property
    def fees(self):
        return self._fees

    @precise
    def reserve_function(self, supplies=None):
        q = self._q if supplies is None else [decimal(x) for x in supplies]
        total = sum(q, ZERO)
        squares = sum((x*x for x in q), ZERO)
        p = self.params
        return p.p0*total + p.k/2*((1-p.coupling)*squares + p.coupling*total*total)

    def create_token(self, name):
        if not isinstance(name, str) or not name.strip() or name in self._names:
            raise RejectedTrade("Token names must be nonempty and unique")
        if len(self._q) >= 100_000:
            raise RejectedTrade("Reference engine supports at most 100,000 tokens")
        self._q.append(ZERO)
        self._names.append(name)
        for wallet in self._wallets.values():
            wallet.holdings._values.append(ZERO)
            wallet.cost_basis._values.append(ZERO)
        return len(self._q)-1

    @precise
    def create_wallet(self, name, cash=0):
        if not isinstance(name, str) or not name or name in self._wallets:
            raise RejectedTrade("Wallet names must be nonempty and unique")
        amount = decimal(cash)
        self._wallets[name] = Wallet(amount, Balances([ZERO]*len(self._q)),
                                     Balances([ZERO]*len(self._q)), ZERO)
        self._initial_cash += amount

    def _token(self, token):
        if isinstance(token, bool) or not isinstance(token, int) or not 0 <= token < len(self._q):
            raise RejectedTrade("Unknown token")

    def _wallet(self, name):
        if name not in self._wallets:
            raise RejectedTrade("Unknown wallet")
        return self._wallets[name]

    @precise
    def donate(self, wallet, amount):
        amount = decimal(amount)
        owner = self._wallet(wallet)
        if amount > owner.cash:
            raise RejectedTrade("Insufficient cash for reserve donation")
        self._wallets[wallet] = Wallet(owner.cash-amount, owner.holdings,
                                       owner.cost_basis, owner.realized_pnl)
        self._reserve += amount
        self._buffer += amount

    @precise
    def transfer_cash(self, sender, recipient, amount):
        """An explicit funded cash transfer, e.g. a modeled network expense."""
        amount = decimal(amount)
        source, target = self._wallet(sender), self._wallet(recipient)
        if amount > source.cash:
            raise RejectedTrade("Insufficient cash for transfer")
        if sender == recipient:
            return
        self._wallets[sender] = Wallet(source.cash-amount, source.holdings, source.cost_basis, source.realized_pnl)
        self._wallets[recipient] = Wallet(target.cash+amount, target.holdings, target.cost_basis, target.realized_pnl)

    @precise
    def price(self, token):
        self._token(token)
        p = self.params
        return p.p0+p.k*((1-p.coupling)*self._q[token]+p.coupling*self._Q)

    @precise
    def quote(self, token, quantity, side):
        self._token(token)
        d = decimal(quantity)
        if d <= 0 or side not in ("buy", "sell"):
            raise RejectedTrade("Positive quantity and buy/sell side required")
        if side == "sell" and d > self._q[token]:
            raise RejectedTrade("Cannot burn more than outstanding supply")
        if side == "buy" and self._q[token]+d > LIMIT:
            raise RejectedTrade("Outstanding token supply would exceed 1e18")
        # Algebraic reserve difference, exactly equivalent to R(q +/- d e_i)-R(q).
        gross = self.price(token)*d + (1 if side == "buy" else -1)*self.params.k*d*d/2
        return gross, gross*self.params.fee_rate

    @precise
    def liquidation_value(self, token, quantity=None):
        self._token(token)
        d = self._q[token] if quantity is None else decimal(quantity)
        if d == 0:
            return ZERO
        gross, fee = self.quote(token, d, "sell")
        return gross-fee

    @precise
    def execute(self, wallet, token, quantity, side, *, max_payment=None, min_receipt=None):
        """Atomic validation then mutation. Slippage limits include fees."""
        owner = self._wallet(wallet)
        d = decimal(quantity)
        gross, fee = self.quote(token, d, side)
        cash_change = -(gross+fee) if side == "buy" else gross-fee
        if side == "buy" and owner.cash < -cash_change:
            raise RejectedTrade("Insufficient wallet cash")
        if side == "sell" and owner.holdings[token] < d:
            raise RejectedTrade("Insufficient wallet token holdings")
        if max_payment is not None and -cash_change > decimal(max_payment):
            raise RejectedTrade("Maximum payment exceeded")
        if min_receipt is not None and cash_change < decimal(min_receipt):
            raise RejectedTrade("Minimum receipt not met")
        pre = self.price(token)
        sign = 1 if side == "buy" else -1
        old_q = self._q[token]
        holdings = owner.holdings._values
        basis = owner.cost_basis._values
        realized = owner.realized_pnl
        if side == "buy":
            basis[token] += gross+fee
        else:
            # Average cost basis is a reporting convention; it never affects cash.
            removed_basis = basis[token] if d == holdings[token] else basis[token]*d/holdings[token]
            realized += gross-fee-removed_basis
            basis[token] -= removed_basis
        holdings[token] += sign*d
        self._wallets[wallet] = Wallet(owner.cash+cash_change, owner.holdings, owner.cost_basis, realized)
        self._q[token] += sign*d
        self._Q += sign*d
        self._squares += self._q[token]**2-old_q**2
        self._required += sign*gross
        self._reserve += sign*gross
        self._fees += fee
        return Trade(wallet, token, side, d, gross, fee, cash_change, pre, self.price(token))

    @precise
    def assert_invariants(self):
        assert all(q >= 0 for q in self._q), "Negative supply"
        assert self._Q == sum(self._q, ZERO), "Cached total supply drift"
        assert self._squares == sum((q*q for q in self._q), ZERO), "Cached squares drift"
        assert self._required == self.reserve_function(), "Required reserve drift"
        assert self._reserve == self._required+self._buffer, "Backing mismatch"
        assert self._reserve >= self._required >= 0 and self._fees >= 0, "Insolvency"
        for wallet in self._wallets.values():
            assert wallet.cash >= 0 and all(q >= 0 for q in wallet.holdings), "Negative wallet"
        for token, q in enumerate(self._q):
            assert sum((w.holdings[token] for w in self._wallets.values()), ZERO) == q, "Unbacked supply"
        cash = sum((w.cash for w in self._wallets.values()), ZERO)
        assert cash+self._reserve+self._fees == self._initial_cash, "Cash conservation failure"

