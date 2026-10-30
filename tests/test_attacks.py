import pytest
from hypothesis import given, strategies as st
from bonding_lab.attacks import bundle, frontrun
from bonding_lab.experiments import bank_run_orders, controlled_spillover, distribution, growth


@given(st.integers(1,10000), st.integers(1,1000), st.integers(0,100))
def test_frontrun_formula(a, b, lam):
    r = frontrun(amount_a=str(a), amount_b=str(b), coupling=str(lam/100), slippage="1e6", capital="1e9")
    assert r["victim_filled"]
    assert r["ledger_profit"] == pytest.approx(.0001*(lam/100)*a*b, abs=1e-8)
    assert r["reserve_shortfall"] == 0


def test_constraints_and_competition():
    assert frontrun(slippage="0")["victim_filled"] is False
    assert frontrun(capital="1")["attackers_funded"] == 0
    assert frontrun(ordering="victim_first")["ledger_profit"] == 0
    assert frontrun(slippage="0", fee=".003")["ledger_profit"] < 0
    r = frontrun(competitors=3, fee=".003")
    assert len(r["individual_profits"]) == 3


def test_bundle_closed_loop_and_external_transfer():
    for sequence in ((0,0,0,0), (0,1,0,1)):
        assert bundle(sequence, victim_quantity=0)["profit"] == 0
        assert bundle(sequence, fee=".003", victim_quantity=0)["profit"] < 0
    assert bundle((1,1,1,1), victim_quantity=1000)["profit"] > 0


def test_bankrun_and_analyses():
    bank = bank_run_orders(3)
    assert (bank[bank.exit_position==9].remaining_reserve==0).all()
    independent = bank[bank.coupling==0]
    assert independent.proceeds.nunique()==1
    r = controlled_spillover()
    assert r.loc[r.coupling==.25,"spillover"].iloc[0] == pytest.approx(.25)
    assert len(growth()) > 0
    assert distribution([1,2,3])["median"] == 2
