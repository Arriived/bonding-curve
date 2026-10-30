"""Matched-capital closed-world cash and token accounting for four architectures."""
from dataclasses import asdict,dataclass
import math
import numpy as np

from .surfaces import FloatSurface,calibrate
from .amm import WeightedPool,HubPool
from .external import ReferenceDealer

SPONSOR,DEALER,RETAIL,ARB,CREATOR,NETWORK=range(6)
ARCHITECTURES=("independent","quadratic","bounded","weighted")


@dataclass(frozen=True)
class Study:
    tokens:int=10
    capital:float=10000.
    reference_price:float=10000.
    dealer_capital:float=100000.
    retail_capital:float=20000.
    arb_capital:float=5000.
    dealer_seed_fraction:float=.1
    external_depth_notional:float=500.
    external_spread:float=.001
    fee:float=.003
    coupling:float=.25
    bounded_cap_fraction:float=.2
    tau:float=1.
    network_cost:float=.01
    max_arb_notional:float=500.
    arb_passes:int=2
    volatility:float=.02
    retail_size:float=20.
    buy_pressure:float=.55
    events:int=500
    seed:int=42
    scenario:str="baseline"

    def __post_init__(self):
        for k,v in asdict(self).items():
            if isinstance(v,(int,float)) and (not math.isfinite(v) or v<0):raise ValueError(f"Invalid {k}")
        if type(self.tokens) is not int or not 2<=self.tokens<=1000:raise ValueError("2–1000 tokens required")
        if self.capital<=0 or self.reference_price<=0 or self.external_depth_notional<=0:raise ValueError("Positive capital/price/depth required")
        if self.dealer_capital<=self.capital*self.dealer_seed_fraction:raise ValueError("Dealer inventory must be paid")
        if not 0<=self.fee<1 or not 0<=self.external_spread<1 or not 0<=self.buy_pressure<=1:
            raise ValueError("Invalid fee or pressure")
        if not 0<=self.coupling<=1 or not 0<=self.bounded_cap_fraction<.8 or self.tau<=0:raise ValueError("Invalid coupling")
        if type(self.events) is not int or self.events<1 or type(self.seed) is not int:raise ValueError("Integer horizon/seed required")
        if self.scenario not in ("baseline","divergent","crash","toxic_admission","joint_run"):
            raise ValueError("Unknown phase-2 scenario")


class World:
    def __init__(self,architecture,config):
        if architecture not in ARCHITECTURES+("hub",):raise ValueError("Unknown architecture")
        self.architecture=architecture
        self.config=c=config
        n,P,B=c.tokens,c.reference_price,c.capital
        E0=B*c.dealer_seed_fraction
        h=E0/(n*P)
        self.cash=np.array([B+E0,c.dealer_capital,c.retail_capital,c.arb_capital,0.,0.])
        self.total_initial_cash=float(self.cash.sum())
        self.h=np.zeros((6,n))
        self.basis=np.zeros(n)
        self.retail_realized=0.
        self.reference=np.full(n,P)
        if architecture in ("weighted","hub"):
            self.mechanism=(WeightedPool if architecture=="weighted" else HubPool)(n,B,P,c.fee)
            self.cash[SPONSOR]-=B
            self.cash[CREATOR]+=B/2+E0
            self.h[CREATOR]=1-self.mechanism.y-h
            if np.any(self.h[CREATOR]<0):raise ValueError("Issuer cap cannot supply paid inventory")
            self.genesis_gain=0.
            self.calibration=dict(a=None,b=None,initial_fraction=None,gamma=None)
        else:
            spec,q0=calibrate(architecture,n,B+E0,P,c.coupling,c.bounded_cap_fraction,c.tau)
            self.mechanism=FloatSurface(spec,n,q0,c.fee)
            self.cash[SPONSOR]-=self.mechanism.cash
            self.cash[SPONSOR]+=E0
            self.h[SPONSOR]=q0-h
            if np.any(self.h[SPONSOR]<0):raise ValueError("Dealer claims exceed funded issuance")
            self.genesis_gain=(q0*n*P)-(B+E0)
            self.calibration=dict(a=float(spec.a),b=float(spec.b),initial_fraction=q0,gamma=float(spec.gamma))
        self.cash[DEALER]-=E0
        self.h[DEALER]=h
        self.external=ReferenceDealer(self.reference,c.external_depth_notional/P,c.external_spread)
        self.initial_sponsor_wealth=self.sponsor_wealth()
        self.initial_reserve=self.mechanism.cash
        self.max_cash_error=self.max_token_error=self.max_backing_error=0.
        self.arb_routes=0
        self.arb_profit=0.
        self.toxic_purchase=0.
        self.assert_invariants()

    def sponsor_wealth(self):
        value=self.cash[SPONSOR]+float(np.dot(self.h[SPONSOR],self.reference))
        if isinstance(self.mechanism,WeightedPool):value+=self.mechanism.nav(self.reference)
        return value

    def refresh(self,prices):
        self.reference=np.asarray(prices,dtype=float).copy()
        self.external.refresh(prices)

    def internal(self,w,i,d,side):
        if not math.isfinite(d) or d<=0:raise ValueError("Invalid quantity")
        value=self.mechanism.quote(i,d,side)
        if side=="buy" and value>self.cash[w]+1e-9:raise ValueError("Unfunded purchase")
        if side=="sell" and d>self.h[w,i]:raise ValueError("Unowned redemption")
        if w==RETAIL:
            if side=="buy":self.basis[i]+=value
            else:
                basis=self.basis[i] if d==self.h[w,i] else self.basis[i]*d/self.h[w,i]
                self.basis[i]-=basis
                self.retail_realized+=value-basis
        actual=self.mechanism.trade(i,d,side)
        self.cash[w]+=-actual if side=="buy" else actual
        self.h[w,i]+=(1 if side=="buy" else -1)*d
        return actual

    def external_trade(self,w,i,d,side):
        value=self.external.quote(i,d,side)
        buyer,seller=(w,DEALER) if side=="buy" else (DEALER,w)
        if value>self.cash[buyer]+1e-9 or d>self.h[seller,i]:raise ValueError("External dealer/wallet limit")
        self.external.trade(i,d,side)
        self.cash[buyer]-=value;self.cash[seller]+=value
        self.h[buyer,i]+=d;self.h[seller,i]-=d
        return value

    def buy_quantity(self,i,budget):
        limit=self.mechanism.max_buy(i)
        if limit<=1e-12 or budget<=0:return 0.
        lo,hi=0.,limit
        if self.mechanism.quote(i,hi,"buy")<=budget:return hi
        for _ in range(36):
            mid=(lo+hi)/2
            if self.mechanism.quote(i,mid,"buy")<=budget:lo=mid
            else:hi=mid
        return lo

    def marginal_internal(self,i,d,side):
        m=self.mechanism
        if isinstance(m,FloatSurface):
            sign=1 if side=="buy" else -1
            p=float(m.spec.a)+m.spec.own_coefficient()*(m.q[i]+sign*d)+m.spec.global_slope(m.X+sign*d)
            return p*(1+m.fee if side=="buy" else 1-m.fee)
        if isinstance(m,HubPool):
            if side=="buy":return m.c[i]*m.y[i]/(m.y[i]-d)**2/(1-m.fee)
            return m.c[i]*(1-m.fee)*m.y[i]/(m.y[i]+(1-m.fee)*d)**2
        if side=="buy":return m.price(i)*(1-d/m.y[i])**(-1-1/m.n)/(1-m.fee)
        return m.price(i)*(1+(1-m.fee)*d/m.y[i])**(-1-1/m.n)*(1-m.fee)

    def arb_candidate(self,i,route):
        c=self.config;m=self.mechanism;e=self.external
        gas=c.network_cost
        available=self.cash[ARB]-gas
        if available<=0:return None
        if route=="internal_buy":
            limit=min(m.max_buy(i),e.max_sell(i),c.max_arb_notional/self.reference[i])
            cost=lambda d:m.quote(i,d,"buy")
            receipt=lambda d:e.quote(i,d,"sell")
            derivative=lambda d:(e.z[i]*(1+(e.u[i]-d)/e.L[i])*(1-e.spread)-self.marginal_internal(i,d,"buy"))
            recipient_budget=self.cash[DEALER]
        else:
            limit=min(m.max_sell(i),e.max_buy(i),self.h[DEALER,i],c.max_arb_notional/self.reference[i])
            cost=lambda d:e.quote(i,d,"buy")
            receipt=lambda d:m.quote(i,d,"sell")
            derivative=lambda d:(self.marginal_internal(i,d,"sell")-e.z[i]*(1+(e.u[i]+d)/e.L[i])*(1+e.spread))
            recipient_budget=float("inf")
        if limit<=1e-12 or derivative(0)<=0:return None
        lo,hi=0.,limit
        if derivative(hi)>0:lo=hi
        else:
            for _ in range(28):
                mid=(lo+hi)/2
                if derivative(mid)>0:lo=mid
                else:hi=mid
        d=lo
        if d<=1e-12:return None
        if cost(d)>available or receipt(d)>recipient_budget:
            lo,hi=0.,d
            for _ in range(30):
                mid=(lo+hi)/2
                if cost(mid)<=available and receipt(mid)<=recipient_budget:lo=mid
                else:hi=mid
            d=lo
        if d<=1e-12:return None
        profit=receipt(d)-cost(d)-gas
        return (profit,i,d,route) if profit>1e-7 else None

    def arbitrage(self):
        for _ in range(self.config.arb_passes):
            m=self.mechanism;e=self.external
            own=m.prices()
            bids=e.z*(1+e.u/e.L)*(1-e.spread)
            asks=e.z*(1+e.u/e.L)*(1+e.spread)
            buy_gap=bids-own/(1-m.fee) # conservative screen for both fee conventions
            sell_gap=own*(1-m.fee)-asks
            buy_gap=np.where(np.array([m.max_buy(i) for i in range(len(own))])>1e-12,buy_gap,-np.inf)
            sell_gap=np.where(self.h[DEALER]>1e-12,sell_gap,-np.inf)
            candidates=[]
            for i,route in ((int(np.argmax(buy_gap)),"internal_buy"),(int(np.argmax(sell_gap)),"external_buy")):
                candidate=self.arb_candidate(i,route)
                if candidate:candidates.append(candidate)
            if not candidates:break
            profit,i,d,route=max(candidates)
            before=self.cash[ARB]
            if route=="internal_buy":
                self.internal(ARB,i,d,"buy");self.external_trade(ARB,i,d,"sell")
            else:
                self.external_trade(ARB,i,d,"buy");self.internal(ARB,i,d,"sell")
            self.cash[ARB]-=self.config.network_cost
            self.cash[NETWORK]+=self.config.network_cost
            assert self.cash[ARB]>=-1e-8
            assert self.cash[ARB]-before>0
            self.arb_profit+=self.cash[ARB]-before
            self.arb_routes+=1

    def toxic_creator_sale(self,i=0):
        if not isinstance(self.mechanism,WeightedPool):return 0.
        # Explicit OTC acquisition from finite authorized creator stock. No depth
        # refresh or free tokens: attacker pays the collapsed reference price.
        d=min(self.h[CREATOR,i],max(0.,self.cash[ARB]-self.config.network_cost)/self.reference[i],self.mechanism.max_sell(i))
        if d<=1e-12:return 0.
        cost=d*self.reference[i]
        receipt=self.mechanism.quote(i,d,"sell")
        if receipt-cost<=self.config.network_cost:return 0.
        self.cash[ARB]-=cost;self.cash[CREATOR]+=cost
        self.h[CREATOR,i]-=d;self.h[ARB,i]+=d
        self.toxic_purchase+=cost
        self.internal(ARB,i,d,"sell")
        self.cash[ARB]-=self.config.network_cost;self.cash[NETWORK]+=self.config.network_cost
        profit=receipt-cost-self.config.network_cost
        self.arb_profit+=profit;self.arb_routes+=1
        return profit

    def assert_invariants(self):
        m=self.mechanism
        m.assert_invariants(self.h)
        assert np.all(self.cash>=-1e-7) and np.all(self.h>=-1e-10)
        total=float(self.cash.sum())+m.cash+(m.fees if isinstance(m,FloatSurface) else 0.)
        error=abs(total-self.total_initial_cash)
        self.max_cash_error=max(self.max_cash_error,error)
        assert error<1e-8*self.total_initial_cash
        supply=self.h.sum(axis=0)+(m.y if isinstance(m,WeightedPool) else -m.q)
        err=float(np.max(np.abs(supply-(1 if isinstance(m,WeightedPool) else 0))))
        self.max_token_error=max(self.max_token_error,err)
        if isinstance(m,FloatSurface):
            self.max_backing_error=max(self.max_backing_error,abs(m.cash-m.spec.reserve(m.q)))
        assert err<1e-8

    def metrics(self):
        c=self.config;m=self.mechanism;pool=isinstance(m,WeightedPool)
        self.assert_invariants()
        return dict(architecture=self.architecture,seed=c.seed,scenario=c.scenario,tokens=c.tokens,events=c.events,
                    sponsor_net_deployed=c.capital,total_initial_cash=self.total_initial_cash,
                    initial_cash_reserve=self.initial_reserve,final_cash_reserve=m.cash,
                    cash_depletion_fraction=1-m.cash/self.initial_reserve,
                    token_inventory_cost=c.capital/2 if pool else 0.,
                    creator_cash=self.cash[CREATOR],
                    arb_profit=self.arb_profit,arb_routes=self.arb_routes,
                    retail_pnl=float(self.cash[RETAIL]+np.dot(self.h[RETAIL],self.reference)-c.retail_capital),
                    retail_realized_pnl=self.retail_realized,
                    dealer_pnl=float(self.cash[DEALER]+np.dot(self.h[DEALER],self.reference)-c.dealer_capital),
                    sponsor_mark_change=self.sponsor_wealth()-self.initial_sponsor_wealth,
                    sponsor_pnl_vs_paid=self.sponsor_wealth()-(c.capital*(1+c.dealer_seed_fraction)),
                    initial_genesis_mark_gain=self.genesis_gain,
                    operator_fee_income=m.fees if not pool else None,
                    lp_nav=m.nav(self.reference) if pool else None,
                    lp_pnl=m.nav(self.reference)-c.capital if pool else None,
                    lp_loss_vs_hodl=m.nav(self.reference)-m.hodl(self.reference) if pool else None,
                    fee_value_at_execution=m.fee_value if pool else m.fees,
                    backing_shortfall=max(0.,float(m.spec.reserve(m.q)-m.cash)) if not pool else None,
                    backing_absolute_error=self.max_backing_error if not pool else None,
                    max_cash_conservation_error=self.max_cash_error,max_token_conservation_error=self.max_token_error,
                    mean_final_mispricing=float(np.mean(np.abs(m.prices()/self.reference-1))),
                    toxic_inventory_purchase_cost=self.toxic_purchase,**self.calibration)
