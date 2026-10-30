from bonding_lab.copycat.config import MarketConfig,Strategy,Variant
from bonding_lab.copycat.market import run
from scripts.copycat_portfolio_controls import PortfolioControl


def test_zero_voluntary_split_is_the_existing_no_tax_control():
    v=Variant(rule="volume",window=30,form="buyer",rate=.1)
    c=MarketConfig(events=30,seed=1001)
    s=Strategy(family="spam",copies=6,seed_budget=10000,residual=.001,exit_at=80)
    expected,_,_=run(v.control(),c,s)
    actual,_,_=PortfolioControl(v,c,s,0).run()
    assert actual==expected


def test_voluntary_portfolio_only_spends_actor_money_not_outsider_money():
    v=Variant(form="buyer",rate=.05)
    m=PortfolioControl(v,MarketConfig(events=30),Strategy(),.05)
    m.launch(0,0,seed=1000)
    m.launch(2,m.main)
    actor=int(m.attack[0]);before=m.book.cash[actor]
    m.buy(2,actor,m.main,1000)
    assert m.book.holdings[actor,0]>0 and m.book.holdings[actor,m.main]>0
    assert 1000<=before-m.book.cash[actor]<=1000.101
    leader_supply=m.book.q[0]
    m.buy(3,0,m.main,1000,organic=True)
    assert m.book.q[0]==leader_supply
    assert m.book.holdings[0,0]==0
    m.book.assert_invariants()
