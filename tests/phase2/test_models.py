from decimal import Decimal, localcontext
from fractions import Fraction
import numpy as np
import pytest
from hypothesis import given, strategies as st, settings

from bonding_lab.phase2.surfaces import Asset,Spec,ExactSurface,FloatSurface,F,bounded_order_profit,calibrate
from bonding_lab.phase2.amm import WeightedPool,HubPool,SettledWeightedPool,check_admission
from bonding_lab.phase2.external import ReferenceDealer
from bonding_lab.fast import FastBook


def funded(kind="bounded",fee=".003",scale=1000000):
    ledger=ExactSurface(Spec(kind,2000,40000,gamma=2000,tau=1),fee)
    for i in range(3):ledger.admit(Asset(str(i),scale))
    ledger.wallet("a",100000)
    ledger.wallet("b",100000)
    return ledger


@given(st.lists(st.tuples(st.integers(0,2),st.integers(1,20),st.booleans()),min_size=1,max_size=50))
@settings(max_examples=60,deadline=None)
def test_exact_random_funded_paths(events):
    c=funded()
    for t,(i,amount,selling) in enumerate(events):
        w="a" if t%2 else "b"
        d=Fraction(amount,1000)
        if selling and c.holdings[w][i]>0:
            c.trade(w,i,min(d,c.holdings[w][i]),"sell")
        elif c.q[i]+d<=1:
            c.trade(w,i,d,"buy")
        c.assert_invariants()


@pytest.mark.parametrize("kind",["independent","quadratic","bounded"])
def test_fast_exact_parity(kind):
    exact=funded(kind,fee=".003")
    fast=FloatSurface(exact.spec,3,0,.003)
    rng=np.random.default_rng(714)
    for _ in range(300):
        i=int(rng.integers(3));d=Fraction(int(rng.integers(1,10)),1000)
        side="sell" if exact.holdings["a"][i]>=d and rng.random()<.5 else "buy"
        g,f=exact.quote(i,d,side)
        assert fast.quote(i,float(d),side)==pytest.approx(float(g+f if side=="buy" else g-f),abs=1e-8,rel=1e-10)
        exact.trade("a",i,d,side);fast.trade(i,float(d),side)
        fast.assert_invariants()
    exact.assert_invariants()


@given(st.integers(1,10000),st.integers(1,10000))
def test_raw_redenomination(scale,multiplier):
    a=funded(scale=scale);b=funded(scale=scale*multiplier)
    d=Fraction(scale,100)
    casha=a.trade("a",0,d,"buy",raw=True)
    cashb=b.trade("a",0,d*multiplier,"buy",raw=True)
    assert casha==cashb
    assert a.price(0,raw=True)==b.price(0,raw=True)*multiplier
    assert a.reserve==b.reserve


def test_admission_does_not_reprice_or_fund():
    c=funded();c.trade("a",0,".1","buy")
    before=c.reserve,c.price(0),list(c.q)
    c.admit(Asset("new",10**12))
    assert (c.reserve,c.price(0),c.q[:-1])==before
    assert c.q[-1]==0
    with pytest.raises(ValueError):c.trade("a",3,".01","sell")
    with pytest.raises(ValueError):Asset("bad",10,False)
    c.assert_invariants()


@given(st.integers(0,100000),st.integers(1,100),st.integers(1,100))
def test_bounded_derivatives_and_attack(X,a,b):
    s=Spec("bounded",2000,40000,gamma=2000,tau=1)
    X,a,b=Fraction(X,100),Fraction(a,1000),Fraction(b,1000)
    assert 0<=s.global_slope(X,True)<2000
    assert s.global_curvature(X,True)>0
    p=bounded_order_profit(s,X,a,b,True)
    t=1+X
    formula=2000*a*b*(2*t+a+b)/(t*(t+a)*(t+b)*(t+a+b))
    assert p==formula>0
    assert p<=s.global_curvature(X,True)*a*b


def test_hessian_convexity_and_roundtrip():
    s=Spec("bounded",2000,40000)
    H=np.eye(10)*s.own_coefficient()+np.ones((10,10))*s.global_curvature(2)
    assert np.linalg.eigvalsh(H).min()>0
    c=funded(fee=0);initial=c.cash["a"]
    c.trade("a",0,".1","buy");c.trade("a",1,".05","buy")
    c.trade("a",0,".1","sell");c.trade("a",1,".05","sell")
    assert c.cash["a"]==initial and c.reserve==0
    c.assert_invariants()


@pytest.mark.parametrize("kind",["independent","quadratic","bounded"])
@pytest.mark.parametrize("n",[2,10,100,1000])
def test_capital_and_price_calibration(kind,n):
    s,x=calibrate(kind,n,11000)
    f=FloatSurface(s,n,x)
    assert f.cash==pytest.approx(11000,abs=1e-7)
    assert f.price(0)==pytest.approx(10000,abs=1e-7)
    assert 0<x<1


@pytest.mark.parametrize("n",[2,10])
def test_weighted_reference_parity_and_invariant(n):
    p=WeightedPool(n,10000)
    ref=SettledWeightedPool(n,p.cash,p.y)
    for _ in range(10):
        payment=20
        with localcontext() as ctx:
            ctx.prec=80
            d=ref.buy_input(0,payment)
        # Buy output implied by an exact cash input, then obtain the same input quote.
        assert p.quote(0,float(d),"buy")==pytest.approx(payment,abs=1e-8)
        p.trade(0,float(d),"buy")
        sell=float(d)/2
        got=p.trade(0,sell,"sell")
        exact=ref.sell_input(0,str(sell))
        assert got==pytest.approx(float(exact),abs=1e-8)
        p.assert_invariants()
    assert p.cash==pytest.approx(float(ref.cash),abs=1e-7)


def test_weighted_local_depth_and_toxicity():
    pool=WeightedPool(10,10000,fee=0);hub=HubPool(10,10000,fee=0)
    d=1e-6
    assert pool.quote(0,d,"buy")<hub.quote(0,d,"buy")
    before=pool.price(1)
    shared=pool.trade(0,.9,"sell");isolated=hub.trade(0,.9,"sell")
    assert shared>isolated
    assert pool.price(1)<before and hub.price(1)==before
    with pytest.raises(ValueError):pool.admit("bad")
    with pytest.raises(ValueError):check_admission(10000,1)


def test_external_finite_depth_and_sequence_cost():
    p=ReferenceDealer([10000],.1,spread=0)
    together=p.quote(0,.02,"buy")
    part=p.trade(0,.01,"buy")+p.trade(0,.01,"buy")
    assert part==pytest.approx(together)
    with pytest.raises(ValueError):p.quote(0,.04,"buy")
    assert p.max_buy(0)==pytest.approx(.03)


def test_legacy_genesis_underfunding_rejected():
    with pytest.raises(ValueError):FastBook(2,2,.01,.0001,.25,.003,1000,q0=1000,reserve_capital=145-5e-10)
