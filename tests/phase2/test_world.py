from dataclasses import replace
import numpy as np
import pytest
from bonding_lab.phase2.world import World,Study,ARCHITECTURES,RETAIL,ARB,DEALER
from bonding_lab.phase2.research import run_world,liquidity_at_start,controlled_toxic,order_attacks,shock_tape,depth_matched_independent


@pytest.mark.parametrize("architecture",ARCHITECTURES+("hub",))
def test_global_genesis_budget_and_ownership(architecture):
    c=Study()
    w=World(architecture,c)
    assert w.total_initial_cash==136000
    assert w.cash[0]==pytest.approx(1000)
    assert w.cash[DEALER]+w.h[DEALER]@w.reference==pytest.approx(c.dealer_capital)
    w.assert_invariants()


@pytest.mark.parametrize("architecture",ARCHITECTURES)
@pytest.mark.parametrize("scenario",["baseline","divergent","crash","toxic_admission","joint_run"])
def test_matched_worlds_deterministic_and_funded(architecture,scenario):
    c=Study(events=40,scenario=scenario)
    a,_=run_world(architecture,c)
    b,_=run_world(architecture,c)
    assert a==b
    assert a["max_cash_conservation_error"]<1e-6
    assert a["max_token_conservation_error"]<1e-9
    assert a["arb_profit"]>=0


def test_arb_is_finite_and_cash_profitable():
    w=World("bounded",Study())
    prices=w.reference.copy();prices[0]*=2
    w.refresh(prices)
    before=w.cash[ARB]
    w.arbitrage()
    assert w.cash[ARB]>before
    assert w.h[ARB].sum()==pytest.approx(0,abs=1e-12)
    w.assert_invariants()
    # An external purchase cannot source more eligible claims than dealer owns.
    w.h[0,0]+=w.h[DEALER,0]
    w.h[DEALER,0]=0
    assert w.arb_candidate(0,"external_buy") is None
    w.assert_invariants()


def test_toxicity_local_depth_and_cross_order_transfers():
    c=Study(events=20)
    tox=controlled_toxic(c).set_index("architecture")
    assert tox.loc["weighted","attack_profit"]>tox.loc["hub","attack_profit"]>0
    assert tox.loc["weighted","unrelated_price_change"]<0
    assert tox.loc["hub","unrelated_price_change"]==0
    table=liquidity_at_start(replace(c,fee=0))
    buys=table[table.side=="buy"].set_index("architecture")
    assert buys.loc["weighted","executable_reference_notional_1pct"]>buys.loc["hub","executable_reference_notional_1pct"]
    attacks=order_attacks(c)
    check=attacks[(attacks.architecture.isin(["independent","quadratic","bounded"]))&(attacks.fee==0)]
    assert np.allclose(check.attacker_net_profit,check.predicted_gross,atol=1e-8)
    matched=depth_matched_independent(c)
    assert matched.exact_buy_100_reference_notional.iloc[0]==pytest.approx(matched.exact_buy_100_reference_notional.iloc[1])
    assert matched.exact_sell_100_reference_notional.iloc[0]==pytest.approx(matched.exact_sell_100_reference_notional.iloc[1])
