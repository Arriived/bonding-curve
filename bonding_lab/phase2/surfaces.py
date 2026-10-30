"""Bounded reserve mathematics. Economic quantities are fractions of a fixed cap.

The Fraction reference gives exact rational cash/ownership invariants. Float64
is the research implementation, with explicit parity and tolerance tests.
"""
from dataclasses import dataclass
from fractions import Fraction
import math
import numpy as np


def F(value):
    if isinstance(value,Fraction):return value
    return Fraction(str(value))


@dataclass(frozen=True)
class Asset:
    name: str
    raw_cap: Fraction
    verified: bool=True

    def __post_init__(self):
        object.__setattr__(self,"raw_cap",F(self.raw_cap))
        if not self.name or self.raw_cap<=0 or not self.verified:
            raise ValueError("Admission requires a named, verified immutable positive supply cap")


@dataclass(frozen=True)
class Spec:
    kind: str
    a: object
    b: object
    coupling: object=.25
    gamma: object=2000
    tau: object=1

    def __post_init__(self):
        if self.kind not in ("independent","quadratic","bounded"):
            raise ValueError("Unknown potential")
        vals=[F(v) for v in (self.a,self.b,self.coupling,self.gamma,self.tau)]
        if vals[0]<=0 or vals[1]<=0 or not 0<=vals[2]<=1 or vals[3]<0 or vals[4]<=0:
            raise ValueError("Invalid convex surface parameters")

    def global_value(self,X,exact=False):
        b,lam,g,t=([F(v) for v in (self.b,self.coupling,self.gamma,self.tau)] if exact else
                   [float(v) for v in (self.b,self.coupling,self.gamma,self.tau)])
        if self.kind=="quadratic":return b*lam*X*X/2
        if self.kind=="bounded":return g*X*X/(t+X)
        return F(0) if exact else 0.

    def global_slope(self,X,exact=False):
        b,lam,g,t=([F(v) for v in (self.b,self.coupling,self.gamma,self.tau)] if exact else
                   [float(v) for v in (self.b,self.coupling,self.gamma,self.tau)])
        if self.kind=="quadratic":return b*lam*X
        if self.kind=="bounded":return g*(1-t*t/(t+X)**2)
        return F(0) if exact else 0.

    def global_curvature(self,X,exact=False):
        b,lam,g,t=([F(v) for v in (self.b,self.coupling,self.gamma,self.tau)] if exact else
                   [float(v) for v in (self.b,self.coupling,self.gamma,self.tau)])
        if self.kind=="quadratic":return b*lam
        if self.kind=="bounded":return 2*g*t*t/(t+X)**3
        return F(0) if exact else 0.

    def own_coefficient(self,exact=False):
        b=F(self.b) if exact else float(self.b)
        lam=F(self.coupling) if exact else float(self.coupling)
        return b*(1-lam) if self.kind=="quadratic" else b

    def reserve(self,q,exact=False):
        a=F(self.a) if exact else float(self.a)
        X=sum(q,F(0) if exact else 0.)
        return a*X+self.own_coefficient(exact)*sum(x*x for x in q)/2+self.global_value(X,exact)


class ExactSurface:
    """Precise factory and funded mint/burn ledger, including raw redenomination."""
    def __init__(self,spec,fee=0,capacity=1000):
        self.spec=spec
        self.fee=F(fee)
        if not 0<=self.fee<1 or not 1<=capacity<=1000:raise ValueError("Invalid policy")
        self.capacity=capacity
        self.assets=[]
        self.q=[]
        self.cash={}
        self.holdings={}
        self.initial_cash=F(0)
        self.reserve=F(0)
        self.fees=F(0)

    def admit(self,asset):
        if not isinstance(asset,Asset) or not asset.verified or len(self.q)>=self.capacity:
            raise ValueError("Asset rejected by cohort admission policy")
        if asset.name in [a.name for a in self.assets]:raise ValueError("Duplicate asset")
        self.assets.append(asset)
        self.q.append(F(0))
        for h in self.holdings.values():h.append(F(0))
        return len(self.q)-1

    def wallet(self,name,cash):
        cash=F(cash)
        if name in self.cash or cash<0:raise ValueError("Invalid wallet")
        self.cash[name]=cash
        self.holdings[name]=[F(0)]*len(self.q)
        self.initial_cash+=cash

    def price(self,i,raw=False):
        self._token(i)
        p=F(self.spec.a)+self.spec.own_coefficient(True)*self.q[i]+self.spec.global_slope(sum(self.q),True)
        return p/self.assets[i].raw_cap if raw else p

    def _token(self,i):
        if type(i) is not int or not 0<=i<len(self.q):raise ValueError("Unknown asset")

    def quote(self,i,d,side,raw=False):
        self._token(i)
        d=F(d)/(self.assets[i].raw_cap if raw else 1)
        if d<=0 or side not in ("buy","sell"):raise ValueError("Invalid trade")
        change=d if side=="buy" else -d
        after=self.q[i]+change
        if not 0<=after<=1:raise ValueError("Issued supply outside admitted cap")
        q=list(self.q)
        q[i]=after
        delta=self.spec.reserve(q,True)-self.spec.reserve(self.q,True)
        gross=delta if side=="buy" else -delta
        return gross, gross*self.fee

    def trade(self,wallet,i,d,side,raw=False,max_payment=None,min_receipt=None):
        gross,fee=self.quote(i,d,side,raw)
        d=F(d)/(self.assets[i].raw_cap if raw else 1)
        if wallet not in self.cash:raise ValueError("Unknown wallet")
        change=-(gross+fee) if side=="buy" else gross-fee
        if self.cash[wallet]+change<0:raise ValueError("Insufficient cash")
        if side=="sell" and d>self.holdings[wallet][i]:raise ValueError("Insufficient holdings")
        if max_payment is not None and -change>F(max_payment):raise ValueError("Slippage cap")
        if min_receipt is not None and change<F(min_receipt):raise ValueError("Slippage floor")
        sign=1 if side=="buy" else -1
        self.cash[wallet]+=change
        self.holdings[wallet][i]+=sign*d
        self.q[i]+=sign*d
        self.reserve+=sign*gross
        self.fees+=fee
        return change

    def assert_invariants(self):
        assert self.reserve==self.spec.reserve(self.q,True)>=0
        assert all(0<=q<=1 for q in self.q)
        assert all(c>=0 for c in self.cash.values())
        for i,q in enumerate(self.q):
            assert all(h[i]>=0 for h in self.holdings.values())
            assert sum(h[i] for h in self.holdings.values())==q
        assert sum(self.cash.values())+self.reserve+self.fees==self.initial_cash


class FloatSurface:
    """O(1) local potential differences, with cached normalized total supply."""
    def __init__(self,spec,n,q0,fee=.003):
        if type(n) is not int or n<1 or not math.isfinite(q0) or not 0<=q0<=1 or not 0<=fee<1:
            raise ValueError("Invalid initial surface")
        self.spec=spec
        self.q=np.full(n,float(q0))
        self.X=float(n*q0)
        self.cash=float(spec.reserve(self.q))
        self.fee=fee
        self.fees=0.

    def price(self,i):
        return float(self.spec.a)+self.spec.own_coefficient()*self.q[i]+self.spec.global_slope(self.X)

    def prices(self):
        return float(self.spec.a)+self.spec.own_coefficient()*self.q+self.spec.global_slope(self.X)

    def max_buy(self,i):return max(0.,1-self.q[i])
    def max_sell(self,i):return max(0.,self.q[i])

    def gross(self,i,d,side):
        if not math.isfinite(d) or d<=0 or side not in ("buy","sell"):raise ValueError("Invalid trade")
        sign=1 if side=="buy" else -1
        if d>(self.max_buy(i) if side=="buy" else self.max_sell(i))+1e-14:raise ValueError("Supply limit")
        own=self.spec.own_coefficient()
        base=(float(self.spec.a)+own*self.q[i])*d+sign*own*d*d/2
        glob=sign*(self.spec.global_value(self.X+sign*d)-self.spec.global_value(self.X))
        return max(0.,base+glob)

    def quote(self,i,d,side):
        g=self.gross(i,d,side)
        return g*(1+self.fee) if side=="buy" else g*(1-self.fee)

    def trade(self,i,d,side):
        g=self.gross(i,d,side)
        sign=1 if side=="buy" else -1
        self.q[i]+=sign*d
        self.X+=sign*d
        self.cash+=sign*g
        self.fees+=g*self.fee
        return g*(1+self.fee) if side=="buy" else g*(1-self.fee)

    def assert_invariants(self,holdings=None):
        tol=1e-8*max(1.,self.cash)
        assert np.all(self.q>=-1e-10) and np.all(self.q<=1+1e-10)
        assert abs(self.X-self.q.sum())<1e-8
        assert abs(self.cash-self.spec.reserve(self.q))<tol
        assert self.cash>=-tol and self.fees>=0
        if holdings is not None:assert np.allclose(holdings.sum(axis=0),self.q,atol=1e-9,rtol=1e-9)
        return tol


def bounded_order_profit(spec,X,a,b,exact=False):
    if exact:X,a,b=map(F,(X,a,b))
    return (spec.global_value(X+a+b,exact)-spec.global_value(X+a,exact)
            -spec.global_value(X+b,exact)+spec.global_value(X,exact))


def calibrate(kind,n,seed_reserve,price=10000.,coupling=.25,gamma_fraction=.2,tau=1.):
    """Match initial marginal price and funded reserve; report retuned coefficients."""
    a=.2*price
    gamma=gamma_fraction*price
    if gamma>=price-a:raise ValueError("Bound must leave positive own curvature")
    if kind in ("independent","quadratic"):
        x=2*seed_reserve/(n*(price+a))
        b=(price-a)/(x*(1+coupling*(n-1)) if kind=="quadratic" else x)
    elif kind=="bounded":
        proto=Spec(kind,a,1,coupling,gamma,tau)
        lo,hi=0.,float(n)
        for _ in range(90):
            X=(lo+hi)/2
            required=X*(price+a-proto.global_slope(X))/2+proto.global_value(X)
            if required<seed_reserve:lo=X
            else:hi=X
        x=(lo+hi)/(2*n)
        b=(price-a-proto.global_slope(n*x))/x
    else:raise ValueError("Unknown surface")
    if not 0<x<1:raise ValueError("Budget cannot be seeded within verified supply caps")
    return Spec(kind,a,b,coupling,gamma,tau),x
