import numpy as np
from bonding_lab.copycat.config import Variant
from bonding_lab.copycat.router import Router
from bonding_lab.fast import FastBook


def test_two_leg_budget_depletion_never_overdraws_a_wallet():
    b=FastBook(2,6,.01,.0001,0,.003,0.)
    b.cash=np.array([1100000.,10000.,0.,0.,0.,0.])
    b.initial_external=float(b.cash.sum());b.initial_wealth=b.cash.copy()
    b.execute(1,0,1000.,"buy")
    r=Router(b,Variant(form="burn",rate=.1),2,3,4,gas=.05)
    for _ in range(200):
        available=b.cash[0]-.1
        if available<=1e-6:break
        r.buy(0,0,1,min(10000.,available),0,5)
        assert b.cash.min()>=0
    b.assert_invariants()
