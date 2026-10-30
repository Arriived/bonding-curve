from dataclasses import FrozenInstanceError
from decimal import Decimal, localcontext

import pytest
from hypothesis import given, settings, strategies as st

from bonding_lab.engine import Curve, Parameters, RejectedTrade, decimal, precise


def funded(coupling="0.25", fee="0", n=3):
    c = Curve(Parameters(coupling=coupling, fee_rate=fee))
    for i in range(n):
        c.create_token(f"T{i}")
    c.create_wallet("alice", "1e18")
    c.create_wallet("bob", "1e18")
    return c


@given(st.integers(1, 100_000), st.integers(1, 100_000), st.integers(0, 100))
@precise
def test_exact_reserve_differences(a, b, lam):
    c = funded(str(Decimal(lam)/100))
    c.execute("alice", 0, a, "buy")
    before = c.reserve_function()
    cost, _ = c.quote(1, b, "buy")
    c.execute("bob", 1, b, "buy")
    assert c.reserve_function()-before == cost
    proceeds, _ = c.quote(1, b, "sell")
    c.execute("bob", 1, b, "sell")
    assert c.reserve_function() == before
    assert cost == proceeds
    c.assert_invariants()


@given(st.lists(st.tuples(st.integers(0, 2), st.integers(1, 10_000), st.booleans()), min_size=1, max_size=120),
       st.integers(0, 100), st.integers(0, 50))
@settings(max_examples=100, deadline=None)
@precise
def test_random_valid_sequences(events, lam, fee):
    c = funded(str(Decimal(lam)/100), str(Decimal(fee)/10_000))
    for j, (token, quantity, selling) in enumerate(events):
        name = "alice" if j % 2 else "bob"
        held = c.wallets[name].holdings[token]
        if selling and held:
            c.execute(name, token, min(decimal(quantity), held), "sell")
        else:
            c.execute(name, token, quantity, "buy")
        c.assert_invariants()


@pytest.mark.parametrize("lam", ["0", "0.1", "0.25", "0.5", "0.75", "1"])
@precise
def test_self_cross_sensitivity_and_roundtrip(lam):
    c = funded(lam)
    p0, p1 = c.price(0), c.price(1)
    buy = c.execute("alice", 0, 100, "buy")
    assert c.price(0)-p0 == c.params.k*100
    assert c.price(1)-p1 == c.params.k*c.params.coupling*100
    sell = c.execute("alice", 0, 100, "sell")
    assert buy.gross == sell.gross
    assert c.wallets["alice"].cash == Decimal("1e18")
    c.assert_invariants()


@precise
def test_path_independence_and_full_redemption():
    a, b = funded(), funded()
    for i in (0, 1, 2):
        a.execute("alice", i, 1000, "buy")
    for i in (2, 0, 1):
        b.execute("alice", i, 1000, "buy")
    assert a.reserve == b.reserve == a.reserve_function()
    total = a.reserve
    returned = sum((a.execute("alice", i, 1000, "sell").gross for i in (1, 2, 0)), Decimal(0))
    assert total == returned
    assert a.reserve == 0
    a.assert_invariants()


def test_creation_and_immutable_parameters():
    c = funded()
    c.execute("alice", 0, 50, "buy")
    reserve, total = c.reserve, c.total_supply
    new = c.create_token("NEW")
    assert c.supplies[new] == c.wallets["alice"].holdings[new] == 0
    assert c.reserve == reserve and c.total_supply == total
    with pytest.raises(FrozenInstanceError):
        c.params.coupling = Decimal("0.5")
    with pytest.raises(AttributeError):
        c.params = Parameters(coupling="1")
    with pytest.raises(TypeError):
        c.wallets["mint"] = c.wallets["alice"]
    c.assert_invariants()


@pytest.mark.parametrize("bad", ["-1", "NaN", "Infinity", "1e19", "1e-19", "abc"])
def test_invalid_inputs(bad):
    c = funded()
    with pytest.raises(RejectedTrade):
        c.execute("alice", 0, bad, "buy")
    c.assert_invariants()


def test_atomic_rejection_and_slippage():
    c = funded()
    c.create_wallet("poor", 1)
    for kwargs in [dict(wallet="poor", token=0, quantity=10000, side="buy"),
                   dict(wallet="alice", token=0, quantity=1, side="sell"),
                   dict(wallet="alice", token=-1, quantity=1, side="buy"),
                   dict(wallet="alice", token=0, quantity=0, side="buy"),
                   dict(wallet="alice", token=0, quantity=10, side="buy", max_payment="0.01"),
                   dict(wallet="missing", token=0, quantity=1, side="buy")]:
        snapshot = (c.reserve, c.supplies, dict(c.wallets), c.fees)
        with pytest.raises(RejectedTrade):
            c.execute(**kwargs)
        assert snapshot == (c.reserve, c.supplies, dict(c.wallets), c.fees)
    c.assert_invariants()


@pytest.mark.parametrize("q", ["0.000000000000000001", "1", "100000000000"])
@precise
def test_extreme_quantities(q):
    c = Curve(Parameters(k="0.000000000000000001", fee_rate="0.001"))
    c.create_token("X")
    c.create_wallet("alice", "1e18")
    buy = c.execute("alice", 0, q, "buy")
    sell = c.execute("alice", 0, q, "sell")
    assert buy.gross == sell.gross
    assert c.wallets["alice"].realized_pnl == -buy.fee-sell.fee
    c.assert_invariants()


@precise
def test_fees_buffer_and_independence():
    c = funded("0", "0.01")
    c.donate("alice", 100)
    c.execute("bob", 0, 1000, "buy")
    assert c.price(1) == c.params.p0
    assert c.reserve == c.reserve_function()+100
    assert c.fees > 0
    c.execute("bob", 0, 1000, "sell")
    assert c.reserve == c.buffer == 100
    assert c.wallets["bob"].realized_pnl < 0
    c.assert_invariants()
