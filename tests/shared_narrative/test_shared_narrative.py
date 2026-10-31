import math

import numpy as np
import pytest
from hypothesis import assume, given, strategies as st

from bonding_lab.engine import Curve, Parameters, RejectedTrade
from bonding_lab.fast import FastBook
from bonding_lab.shared_narrative.book import SkinBook, Rejected
from bonding_lab.shared_narrative.curves import PumpShape, LinearShape
from bonding_lab.shared_narrative.reference import PumpReference
from bonding_lab.shared_narrative.tape import Config, make_tape, ORGANIC
from bonding_lab.shared_narrative.world import run_arm
from bonding_lab.shared_narrative.stats import cara_ce, ssd_dominates

ARM_MAP = {"A": list(range(10)), "B": [0]*10}


# ---------------------------------------------------------------- linear shape == existing engine
@pytest.mark.parametrize("arm,coupling", [("A", 0), ("B", 1)])
def test_linear_skin_book_matches_fastbook_and_decimal_engine(arm, coupling):
    """Arm A is the existing engine at coupling 0; Arm B is exactly coupling 1."""
    p0, k = .01, .0001
    shape = LinearShape(p0=p0, k=k)
    book = SkinBook(shape, ARM_MAP[arm], [1_000_000]*5, fee=.003, creator_share=.3, gas=0)
    fast = FastBook(10, 5, p0, k, coupling, .003, 1_000_000)
    ref = Curve(Parameters(p0="0.01", k="0.0001", coupling=str(coupling), fee_rate="0.003"))
    for i in range(10):
        ref.create_token(str(i))
    for i in range(5):
        ref.create_wallet(str(i), 1_000_000)
    rng = np.random.default_rng(2026)
    for _ in range(1000):
        w, token, q = int(rng.integers(5)), int(rng.integers(10)), int(rng.integers(1, 50))
        side = "sell" if fast.holdings[w, token] >= q and rng.random() < .5 else "buy"
        g_ref = ref.execute(str(w), token, q, side).gross
        g_fast = fast.execute(w, token, q, side).gross
        g_book = book.execute(w, token, float(q), side)
        assert g_book == pytest.approx(g_fast, abs=1e-8, rel=1e-10)
        assert g_book == pytest.approx(float(g_ref), abs=1e-8, rel=1e-10)
    ref.assert_invariants()
    fast.assert_invariants()
    assert book.reserves().sum() == pytest.approx(fast.reserve, rel=1e-10)
    assert book.cash == pytest.approx(fast.cash, abs=1e-7)
    if arm == "B":
        assert len(set(np.round(fast.prices(), 15))) == 1   # every skin priced identically


# ---------------------------------------------------------------- pump shape float vs Decimal
@pytest.mark.parametrize("arm", ["A", "B"])
def test_pump_float_matches_decimal_reference(arm):
    shape = PumpShape()
    book = SkinBook(shape, ARM_MAP[arm], [5_000_000]*5, fee=.01, creator_share=.3, gas=0)
    ref = PumpReference(ARM_MAP[arm], 5, "5000000")
    rng = np.random.default_rng(7)
    for step in range(1500):
        w, skin = int(rng.integers(5)), int(rng.integers(10))
        q = float(int(rng.integers(1, 40))*1_000_000)       # whole tokens, crosses graduation in B
        side = "sell" if book.hold[w, skin] >= q and rng.random() < .45 else "buy"
        try:
            g_book = book.execute(w, skin, q, side)
        except (Rejected, ValueError):
            with pytest.raises(RejectedTrade):     # both ledgers refuse the same infeasible trade
                ref.execute(w, skin, q, side)
            continue
        g_ref = ref.execute(w, skin, q, side)
        assert g_book == pytest.approx(float(g_ref), rel=1e-9, abs=1e-9)
    ref.assert_invariants()
    book.check()
    for i in range(book.n_curves):
        assert book.states[i][0] == ref.states[i][0]
        assert book.states[i][1] == pytest.approx(float(ref.states[i][1]), rel=1e-9)
    if arm == "B":
        assert book.states[0][0] == 1, "the shared curve should have graduated in this sequence"


def test_pump_constants_and_headline_identity():
    s = PumpShape()
    assert s.x_grad-s.x0 == pytest.approx(12750.80, abs=.01)
    st_ = s.new_state()
    s.buy(st_, s.x_grad-s.x0)                     # exactly to graduation
    assert st_[0] == 1
    assert s.mcap(st_) == pytest.approx(61627.86, abs=.05)
    # E2: ten curves at $50k vs one curve with the same net dollars.
    R50 = math.sqrt(50_000*s.k0/s.supply)-s.x0
    assert R50 == pytest.approx(11037.857, abs=1e-3)
    one = s.new_state()
    s.buy(one, 10*R50)
    assert s.mcap(one) == pytest.approx(4_618_186.5, rel=1e-6)
    assert s.recoverable_gross(one) == pytest.approx(107_740.43, abs=.01)
    assert s.locked(one) == pytest.approx(2638.14, abs=.01)
    lin = LinearShape()
    a, b = lin.new_state(), lin.new_state()
    lin.buy(a, R50)
    lin.buy(b, 10*R50)
    assert 10*lin.mcap(a) == pytest.approx(190_155, rel=1e-3)
    assert lin.mcap(b) == pytest.approx(209_946, rel=1e-3)


@given(st.floats(10, 50_000), st.floats(10, 200_000))
def test_round_trip_is_path_independent_and_wash_identity(pre, g):
    """E6: an immediate round trip within one phase returns the same gross; net = -2fG(1-s) - 2 gas.

    A round trip that crosses graduation is not path independent (the pool's K
    differs from the curve's); that case loses more and is tested separately."""
    shape = PumpShape()
    book = SkinBook(shape, ARM_MAP["B"], [1e7, 1e7], fee=.01, creator_share=.3, gas=.05)
    book.buy(0, 3, pre)
    before_cash, before_fees = book.cash[1], book.creator_fees[5]
    state = list(book.states[0])
    tok, gross = book.buy(1, 5, g)
    assume(book.states[0][0] == state[0])
    net, gross_back = book.sell(1, 5, tok)
    assert gross_back == pytest.approx(gross, rel=1e-9)
    assert book.states[0][1] == pytest.approx(state[1], rel=1e-12)
    rebate = book.creator_fees[5]-before_fees
    loss = book.cash[1]+rebate-before_cash
    assert loss == pytest.approx(-2*.01*gross*(1-.3)-2*.05, rel=1e-7, abs=1e-6)


def test_round_trip_across_graduation_loses_locked_value():
    shape = PumpShape()
    book = SkinBook(shape, ARM_MAP["A"], [1e6], fee=0, creator_share=0, gas=0)
    tok, gross = book.buy(0, 0, 20_000.0)
    assert book.states[0][0] == 1
    net, back = book.sell(0, 0, tok)
    assert back < gross
    assert gross-back == pytest.approx(book.reserves()[0], rel=1e-9)   # what stays is the locked LP value


def test_wallet_constraints():
    book = SkinBook(PumpShape(), ARM_MAP["B"], [100.0, 0.0], gas=.05)
    with pytest.raises(Rejected):
        book.buy(0, 0, 100.01)
    with pytest.raises(Rejected):
        book.sell(1, 0, 1.0)
    tok, _ = book.buy(0, 2, 100.0)
    with pytest.raises(Rejected):       # separate mints: cannot sell skin 3 while holding skin 2
        book.sell(0, 3, tok)
    book.convert(0, 2, 3, tok)          # 1:1 conversion against the shared reserve
    book.sell(0, 3, tok)
    book.check()
    a = SkinBook(PumpShape(), ARM_MAP["A"], [100.0])
    t, _ = a.buy(0, 2, 50.0)
    with pytest.raises(Rejected):
        a.convert(0, 2, 3, t)


def test_depth_formula_E3():
    s = PumpShape()
    st_ = s.new_state()
    for u, want in ((.01, 22.444), (.05, 111.128), (.10, 219.640)):
        assert s.buy_gross_to_price(st_, s.price(st_)*(1+u)) == pytest.approx(want, abs=1e-3)
    probe = list(st_)
    s.buy(probe, s.buy_gross_to_price(st_, s.price(st_)*1.05))
    assert s.price(probe) == pytest.approx(s.price(st_)*1.05, rel=1e-12)


# ---------------------------------------------------------------- matching across arms
def test_tape_is_deterministic_and_arm_invariant():
    c = Config(seed=3, arrivals=800)
    t1, t2 = make_tape(c), make_tape(c)
    assert t1.fingerprint() == t2.fingerprint()
    fp = t1.fingerprint()
    ra, rb = run_arm(t1, "A"), run_arm(t1, "B")
    assert t1.fingerprint() == fp, "running an arm must not mutate the tape"
    # identical picks and identical organic buy dollars per meme in both arms
    for r in (ra, rb):
        assert np.array_equal(r["organic"]["pick"], t1.org_pick)
    spent = {arm: np.bincount(r["organic"]["pick"], weights=r["organic"]["budget"], minlength=10)
             for arm, r in (("A", ra), ("B", rb))}
    assert np.allclose(spent["A"], spent["B"])
    # E4: creator fee income on the buy side is identical; differences come from sells only
    # Buy-side creator fees differ only through state-dependent strategic buys (arbitrage in A).
    org_fee = np.bincount(t1.org_pick, weights=(t1.org_budget-c.gas)/(1+c.fee)*c.fee*c.creator_share, minlength=10)
    for r in (ra, rb):
        assert np.all(r["creators"]["fees_buy"] >= org_fee-1e-9)
    no_arb = make_tape(Config(seed=3, arrivals=800, arbitrageurs=0))
    fa, fb = run_arm(no_arb, "A")["creators"]["fees_buy"], run_arm(no_arb, "B")["creators"]["fees_buy"]
    assert np.allclose(fa, fb, rtol=1e-9)


def test_attention_concentration_moves_hhi():
    lo = make_tape(Config(seed=1, arrivals=800, concentration=0.0))
    hi = make_tape(Config(seed=1, arrivals=800, concentration=1.0))
    h = lambda t: float(np.square(t.meme_buy_dollars/t.meme_buy_dollars.sum()).sum())
    assert h(hi) > h(lo)+.3
    assert np.array_equal(lo.org_budget, hi.org_budget)       # concentration changes picks only
    assert np.array_equal(lo.org_time, hi.org_time)


def test_world_conservation_zero_sum_and_wallets():
    """run_arm asserts cash conservation and the E9 zero-sum identity internally."""
    for kw in (dict(), dict(shock=True), dict(shape="linear"), dict(spam=(3, 120.0, 50.0, 2.0)),
               dict(wash=(4, 500.0, 60, 600)), dict(bundle=("spread", 2000.0, 3.0, 1800))):
        tape = make_tape(Config(seed=11, arrivals=600, **kw))
        for arm in "AB":
            r = run_arm(tape, arm)
            assert r["metrics"]["rejects"] >= 0
            assert np.all(np.isfinite(r["organic"]["pnl"]))


def test_arm_b_price_path_independent_of_attention():
    """In B all picks land in one reserve; only fee attribution depends on attention."""
    a = run_arm(make_tape(Config(seed=5, arrivals=800, concentration=0.0, adversary_budget=0, bundle=())), "B")
    b = run_arm(make_tape(Config(seed=5, arrivals=800, concentration=1.0, adversary_budget=0, bundle=())), "B")
    # Snipers and devs are identical; organic dollars identical in time; so the curve is identical.
    assert a["metrics"]["peak_top_mcap"] == pytest.approx(b["metrics"]["peak_top_mcap"], rel=1e-9)
    assert not np.allclose(a["creators"]["fees"], b["creators"]["fees"])


def test_stats_helpers():
    x = np.array([10.0]*100)
    y = np.array([0.0]*90+[100.0]*10)
    assert cara_ce(x, 1/100) == pytest.approx(10)
    assert cara_ce(y, 1/100) < 10
    assert ssd_dominates(x, y) and not ssd_dominates(y, x)
