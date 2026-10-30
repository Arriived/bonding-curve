from decimal import Decimal
from dataclasses import replace
import numpy as np
import pytest
from hypothesis import given,strategies as st
from bonding_lab.copycat.config import Variant,MarketConfig,Strategy
from bonding_lab.copycat.reference import DiversionReference
from bonding_lab.copycat.router import Router
from bonding_lab.copycat.market import run
from bonding_lab.fast import FastBook
from bonding_lab.engine import precise


@pytest.mark.parametrize("form",["creator","holders","buyer","treasury","burn","control"])
@pytest.mark.parametrize("burn",["lock","supply"])
@precise
def test_decimal_routing_and_float_parity(form,burn):
    c=DiversionReference()
    for t in ("leader","copy"):c.create_token(t)
    for name in ("holder","buyer","creator"):c.create_wallet(name,10000)
    c.execute("holder",0,1000,"buy")
    cash0=c.wallets["buyer"].cash
    ref=c.routed_buy("buyer",1,100,leader=0,creator="creator",form=form,rate=".05",burn=burn)
    c.assert_invariants()
    b=FastBook(2,6,.01,.0001,0,.003,10000)
    # Float IDs: holder,buyer,creator,treasury,dead,network. Reference treasury/dead
    # start at zero; equalize the deliberately different fixture wallet funding.
    b.cash[3:]=0;b.initial_external=float(b.cash.sum());b.initial_wealth=b.cash.copy()
    b.execute(0,0,1000,"buy")
    r=Router(b,Variant(form=form,burn=burn),3,4,5)
    r.buy(0,1,1,100,0,2)
    b.assert_invariants()
    for i in range(2):assert b.q[i]==pytest.approx(float(c.supplies[i]),abs=1e-8)
    assert b.reserve==pytest.approx(float(c.reserve),abs=1e-8)
    assert b.buffer==pytest.approx(float(c.buffer),abs=1e-8)
    assert b.cash[1]==pytest.approx(float(c.wallets["buyer"].cash),abs=1e-8)


@given(st.integers(1,10000),st.sampled_from([".01",".03",".05",".1"]))
@precise
def test_buyer_owned_split_has_same_isolated_roundtrip(B,rate):
    c=DiversionReference()
    c.create_token("L");c.create_token("C");c.create_wallet("buyer",100000)
    out=c.routed_buy("buyer",1,B,leader=0,form="buyer",rate=rate)
    for i in (0,1):
        h=c.wallets["buyer"].holdings[i]
        if h:c.execute("buyer",i,h,"sell")
    c.assert_invariants()
    rho=(1-c.params.fee_rate)/(1+c.params.fee_rate)
    assert abs(c.wallets["buyer"].cash-(Decimal(100000)-Decimal(B)*(1-rho)))<Decimal("1e-10")


@precise
def test_literal_burn_retraces_price_and_preserves_collateral():
    c=DiversionReference();c.create_token("L");c.create_token("C")
    c.create_wallet("owner",10000);c.execute("owner",0,1000,"buy")
    price=c.price(0);required=c.required_reserve
    c.routed_buy("owner",1,100,leader=0,form="burn",burn="supply")
    assert c.price(0)==price and c.buffer>0
    assert c.required_reserve>required # copy issuance is backed too
    c.assert_invariants()


def test_zero_holder_waiver_and_atomic_slippage():
    b=FastBook(2,5,.01,.0001,0,.003,10000)
    r=Router(b,Variant(form="holders"),2,3,4)
    r.buy(0,0,1,100,0,1)
    assert r.diverted==0
    r=Router(b,Variant(form="buyer"),2,3,4)
    before=b.cash.copy(),b.q.copy(),b.reserve
    with pytest.raises(ValueError):r.buy(1,0,1,100,0,1,min_leader_quantity=1e9)
    assert np.array_equal(before[0],b.cash) and np.array_equal(before[1],b.q) and before[2]==b.reserve


@pytest.mark.parametrize("form",["creator","holders","buyer","treasury","burn","control"])
def test_market_funded_and_reproducible(form):
    c=MarketConfig(events=60)
    v=Variant(form=form)
    a,_,_=run(v,c);b,_,_=run(v,c)
    assert a==b
    assert a["cash_conservation_error"]<1e-5
    assert a["reserve_backing_error"]<1e-5


def test_never_selling_treasury_and_lock_have_same_public_path():
    c=MarketConfig(events=60)
    t,_,_=run(Variant(form="treasury"),c)
    d,_,_=run(Variant(form="burn",burn="lock"),c)
    for key in ("retail_profit","vamper_profit","original_final_liquidity_share","total_accessible_liquidity"):
        assert t[key]==pytest.approx(d[key],abs=1e-6)
