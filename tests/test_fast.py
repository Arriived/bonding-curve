import numpy as np
import pytest
from bonding_lab.engine import Curve, Parameters
from bonding_lab.fast import FastBook
from bonding_lab.simulation import Config, compare, run


@pytest.mark.parametrize("coupling", [0, .1, .25, .5, .75, 1])
def test_fast_matches_decimal(coupling):
    reference = Curve(Parameters(coupling=str(coupling), fee_rate="0.003"))
    for i in range(10):
        reference.create_token(str(i))
    for i in range(5):
        reference.create_wallet(str(i), 1_000_000)
    fast = FastBook(10, 5, .01, .0001, coupling, .003, 1_000_000)
    rng = np.random.default_rng(2026)
    for _ in range(1000):
        w, token = int(rng.integers(5)), int(rng.integers(10))
        q = int(rng.integers(1, 50))
        side = "sell" if reference.wallets[str(w)].holdings[token] >= q and rng.random() < .5 else "buy"
        a = reference.execute(str(w), token, q, side)
        b = fast.execute(w, token, q, side)
        assert b.gross == pytest.approx(float(a.gross), abs=1e-8, rel=1e-10)
    reference.assert_invariants()
    fast.assert_invariants()
    assert fast.reserve == pytest.approx(float(reference.reserve), abs=1e-7, rel=1e-10)
    assert fast.cash == pytest.approx([float(reference.wallets[str(i)].cash) for i in range(5)], abs=1e-7)


@pytest.mark.parametrize("scenario", ["baseline", "popular", "crash", "bundled", "frontrun", "bank_run"])
def test_scenarios_reproducible(scenario):
    c = Config(events=200, traders=20, scenario=scenario)
    a, b = run(c), run(c)
    assert a.metrics == b.metrics
    assert a.history.equals(b.history)
    assert a.metrics["material_reserve_shortfall"] == 0
    assert (a.wallets.cash >= -1e-8).all()


def test_comparison_and_export():
    c = Config(events=50)
    paired = compare(c, "equal_capital")
    assert paired["shared"].metrics["initial_required"] == pytest.approx(paired["independent"].metrics["initial_required"])
    assert paired["shared"].export_zip().startswith(b"PK")
    with pytest.raises(ValueError):
        run(Config(reserve_capital=1))
