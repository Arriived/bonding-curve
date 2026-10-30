"""Actual shared-inventory AMM and an isolated hub control, not minting curves."""
from decimal import Decimal, localcontext, ROUND_FLOOR
import math
import numpy as np


def check_admission(proposed_price,reference_price,verified=True):
    if not verified or not all(math.isfinite(v) and v>0 for v in (proposed_price,reference_price)):
        raise ValueError("Unverified supply or nonpositive admission price")
    if abs(proposed_price/reference_price-1)>.05:
        raise ValueError("Admission price differs from supplied reference by more than 5%")


class WeightedPool:
    def __init__(self,n,budget,price=10000.,fee=.003):
        if type(n) is not int or not 1<=n<=1000 or not budget>0 or not price>0 or not 0<=fee<1:
            raise ValueError("Invalid weighted pool")
        check_admission(price,price)
        self.n=n
        self.cash=float(budget/2)
        self.y=np.full(n,budget/(2*n*price))
        if np.any(self.y>=1):raise ValueError("Seed inventory exceeds verified supply")
        self.initial_y=self.y.copy()
        self.initial_cash=self.cash
        self.fee=fee
        self.fee_value=0.
        self.fees=0. # Fees stay in pool; this is not an external cash treasury.
        self.initial_log_invariant=self.log_invariant()

    def admit(self,*args,**kwargs):
        raise ValueError("Fixed cohort: new assets require a newly funded pool")

    def price(self,i):return self.cash/(self.n*self.y[i])
    def prices(self):return self.cash/(self.n*self.y)
    def max_buy(self,i):return self.y[i]*(1-1e-10)
    def max_sell(self,i):return max(0.,1-self.y[i])
    def log_invariant(self):return .5*math.log(self.cash)+float(np.log(self.y).sum())/(2*self.n)

    def quote(self,i,d,side):
        if not math.isfinite(d) or d<=0 or side not in ("buy","sell"):raise ValueError("Invalid swap")
        if d>(self.max_buy(i) if side=="buy" else self.max_sell(i)):
            raise ValueError("Finite pool inventory limit")
        if side=="buy":
            return self.cash*math.expm1(-math.log1p(-d/self.y[i])/self.n)/(1-self.fee)
        return -self.cash*math.expm1(-math.log1p((1-self.fee)*d/self.y[i])/self.n)

    def trade(self,i,d,side):
        amount=self.quote(i,d,side)
        if side=="buy":
            self.fee_value+=amount*self.fee
            self.cash+=amount
            self.y[i]-=d
        else:
            self.fee_value+=d*self.fee*self.price(i)
            self.cash-=amount
            self.y[i]+=d
        return amount

    def nav(self,reference):return float(self.cash+np.dot(self.y,reference))
    def hodl(self,reference):return float(self.initial_cash+np.dot(self.initial_y,reference))

    def assert_invariants(self,holdings=None):
        assert math.isfinite(self.cash) and self.cash>0
        assert np.all(np.isfinite(self.y)) and np.all(self.y>0) and np.all(self.y<=1+1e-10)
        assert self.log_invariant()>=self.initial_log_invariant-1e-10
        if holdings is not None:assert np.allclose(self.y+holdings.sum(axis=0),1,atol=1e-9,rtol=1e-9)
        return 1e-8*max(1.,self.cash)


class HubPool(WeightedPool):
    """Shared custody/router with ring-fenced per-token constant-product cash."""
    def __init__(self,n,budget,price=10000.,fee=.003):
        super().__init__(n,budget,price,fee)
        self.c=np.full(n,budget/(2*n))
        self.initial_products=self.c*self.y

    def price(self,i):return self.c[i]/self.y[i]
    def prices(self):return self.c/self.y

    def quote(self,i,d,side):
        if not math.isfinite(d) or d<=0 or side not in ("buy","sell"):raise ValueError("Invalid swap")
        if d>(self.max_buy(i) if side=="buy" else self.max_sell(i)):raise ValueError("Inventory limit")
        return self.c[i]*d/(self.y[i]-d)/(1-self.fee) if side=="buy" else self.c[i]*(1-self.fee)*d/(self.y[i]+(1-self.fee)*d)

    def trade(self,i,d,side):
        value=self.quote(i,d,side)
        if side=="buy":
            self.fee_value+=value*self.fee
            self.c[i]+=value
            self.y[i]-=d
        else:
            self.fee_value+=d*self.fee*self.price(i)
            self.c[i]-=value
            self.y[i]+=d
        self.cash=float(self.c.sum())
        return value

    def assert_invariants(self,holdings=None):
        assert np.all(self.c>0) and np.all(self.y>0)
        assert np.all(self.c*self.y>=self.initial_products*(1-1e-10))
        if holdings is not None:assert np.allclose(self.y+holdings.sum(axis=0),1,atol=1e-9,rtol=1e-9)
        return 1e-8*max(1.,self.cash)


class SettledWeightedPool:
    """Decimal reference: conservative outputs; cash 1e-12, cap fractions 1e-18.

    Rational fractional powers are evaluated at 100 digits then output is rounded
    down. These are research quanta, not a production token settlement policy.
    """
    def __init__(self,n,cash,inventory,fee=".003"):
        self.n=n
        self.cash=Decimal(str(cash))
        self.y=[Decimal(str(v)) for v in inventory]
        self.fee=Decimal(str(fee))
        if len(self.y)!=n or self.cash<=0 or any(v<=0 for v in self.y) or not 0<=self.fee<1:
            raise ValueError("Invalid reference pool")

    def buy_input(self,i,payment):
        with localcontext() as ctx:
            ctx.prec=100
            B=Decimal(str(payment))
            if not B>0:raise ValueError("Positive payment required")
            d=self.y[i]*(1-(self.cash/(self.cash+(1-self.fee)*B))**self.n)
            d=d.quantize(Decimal("1e-18"),rounding=ROUND_FLOOR)
            self.cash+=B
            self.y[i]-=d
            return d

    def sell_input(self,i,quantity):
        with localcontext() as ctx:
            ctx.prec=100
            d=Decimal(str(quantity))
            if not d>0:raise ValueError("Positive input required")
            ratio=self.y[i]/(self.y[i]+(1-self.fee)*d)
            out=self.cash*(1-(ratio.ln()/self.n).exp())
            out=out.quantize(Decimal("1e-12"),rounding=ROUND_FLOOR)
            self.cash-=out
            self.y[i]+=d
            return out
