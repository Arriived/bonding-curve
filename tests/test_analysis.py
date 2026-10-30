from decimal import Decimal
import pytest
import numpy as np
from bonding_lab.engine import Curve, Parameters, precise
from bonding_lab.simulation import Config, compare, run
from bonding_lab.attacks import frontrun
from bonding_lab.experiments import monte_carlo


@precise
def test_market_cap_identity_and_wallet_vector_liquidation():
    c = Curve(Parameters(coupling=".5", fee_rate=".003"))
    for i in range(3):
        c.create_token(str(i))
    c.create_wallet("a", 100000)
    c.create_wallet("b", 100000)
    for i in range(3):
        c.execute("a", i, 100, "buy")
        c.execute("b", i, 200, "buy")
    cap = sum((c.price(i)*q for i,q in enumerate(c.supplies)),Decimal(0))
    assert cap == 2*c.required_reserve-c.params.p0*c.total_supply
    h = list(c.wallets["a"].holdings)
    expected = sum((c.price(i)*v for i,v in enumerate(h)),Decimal(0))-c.params.k/2*((1-c.params.coupling)*sum(v*v for v in h)+c.params.coupling*sum(h)**2)
    paid = sum((c.execute("a",i,v,"sell").gross for i,v in enumerate(h)),Decimal(0))
    assert expected == paid
    c.transfer_cash("a","b",1)
    c.assert_invariants()


def test_heterogeneous_supplies_and_capital_matching():
    c = Config(tokens=2, initial_supplies=(100,200), events=30, traders=10)
    pair = compare(c, "equal_capital")
    assert pair["shared"].metrics["initial_required"] == pytest.approx(pair["independent"].metrics["initial_required"])
    assert run(c).metrics["material_reserve_shortfall"] == 0


def test_small_monte_carlo_matches_seed_differences():
    raw, summary = monte_carlo(Config(events=20,traders=10),seeds=3)
    differences = raw.pivot(index="seed",columns="model",values="final_reserve")
    expected = (differences.shared-differences.independent).mean()
    found = summary[(summary.model=="shared_minus_independent")&(summary.metric=="final_reserve")].iloc[0]
    assert found["mean"] == pytest.approx(expected)
    assert found["n"] == 3


def test_gas_is_capital_constrained():
    assert frontrun(capital="100",gas_per_tx="100")["attackers_funded"] == 0
    r = frontrun(gas_per_tx="1")
    assert r["net_profit"] == pytest.approx(r["ledger_profit"]-2)
