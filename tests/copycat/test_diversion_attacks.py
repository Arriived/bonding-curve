from decimal import Decimal
from dataclasses import replace
import numpy as np
import pytest
from bonding_lab.copycat.reference import DiversionReference
from bonding_lab.copycat.config import Variant,MarketConfig,Strategy
from bonding_lab.copycat.market import run
from bonding_lab.copycat.attacks import candidates,FAMILIES
from bonding_lab.engine import precise


@precise
def test_self_paid_creator_wash_is_not_external_revenue():
    c=DiversionReference();c.create_token("L");c.create_token("C");c.create_wallet("actor",10000)
    out=c.routed_buy("actor",1,1000,leader=0,creator="actor",form="creator",rate=".1")
    c.execute("actor",1,out["copy_quantity"],"sell");c.assert_invariants()
    rho=(1-c.params.fee_rate)/(1+c.params.fee_rate)
    predicted=Decimal(10000)-(1-rho)*Decimal(900)
    assert abs(c.wallets["actor"].cash-predicted)<Decimal("1e-10")


@precise
def test_budget_frontrun_and_literal_burn_cancellation():
    for burn in ("lock","supply"):
        c=DiversionReference();c.create_token("L");c.create_token("C")
        for w in ("seed","bot","buyer"):c.create_wallet(w,100000)
        c.execute("seed",0,1000,"buy")
        before=c.wallets["bot"].cash
        tx=c.execute("bot",0,100,"buy")
        out=c.routed_buy("buyer",1,1000,leader=0,form="burn",rate=".1",burn=burn)
        c.execute("bot",0,100,"sell");c.assert_invariants()
        expected=(1-c.params.fee_rate)*c.params.k*100*out["leader_quantity"]-2*c.params.fee_rate*tx.gross if burn=="lock" else -2*c.params.fee_rate*tx.gross
        assert abs(c.wallets["bot"].cash-before-expected)<Decimal("1e-20")


@pytest.mark.parametrize("family",FAMILIES)
def test_funded_adaptive_strategies(family):
    v=Variant(rule="volume",changes="cooldown",form="holders")
    options=candidates(v,family)
    assert options[0].family=="idle" and len(options)>=5
    for s in (options[1],options[-1]):
        m,_,_=run(v,MarketConfig(events=60),s)
        assert m["cash_conservation_error"]<1e-5
        assert m["reserve_backing_error"]<1e-5


def test_capital_capture_and_evasion_are_actual_strategies():
    v=Variant(rule="threshold",threshold=100000,form="creator")
    s=Strategy(family="race",residual=0.,exit_on_capture=True,pump=1.001)
    m,h,_=run(v,MarketConfig(events=120),s,details=True)
    assert m["leader_final_is_attacker"]
    assert m["creator_diversion_receipts"]>0
    assert m["peak_attacker_cash_committed"]>40000
    ev,_,_=run(Variant(matching="fuzzy",form="creator"),MarketConfig(events=60),
               Strategy(family="evasion",ticker="ELONXX",copies=8,seed_budget=3000))
    assert ev["initial_external_cash"]==m["initial_external_cash"]


@pytest.mark.parametrize("form,rate,aliases,residual",[("buyer",.01,3,1.),("burn",.03,32,.000001),
                                                       ("burn",.1,12,.000001)])
def test_repeated_depleted_alias_funding_stays_nonnegative(form,rate,aliases,residual):
    v=Variant(rule="volume",window=5,form=form,rate=rate)
    s=Strategy(family="flip",aliases=aliases,seed_budget=10000,rounds=3,residual=residual,
               pump=10,pulse=6,exit_at=235,exit_on_capture=True)
    m,_,_=run(v,MarketConfig(events=160,seed=11),s)
    assert m["minimum_wallet_cash"]>=0
    assert m["cash_conservation_error"]<1e-5
