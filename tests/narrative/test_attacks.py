from dataclasses import replace
import pytest
from bonding_lab.narrative.model import Config,World,Policy,make_tape
from bonding_lab.narrative.attacks import policies,ordering_study
from bonding_lab.narrative.ledger import MONEY as M


def test_ordering_search_finds_profit_and_tight_limit_rollback():
    rows=ordering_study()
    assert len(rows)==56
    assert any(r['complete_exit_profit']>0 and r['filled'] for r in rows if r['fee_bps']==40)
    assert all(not r['filled'] for r in rows if r['slippage_bps']==0 and r['budget']>0)
    assert all(r['attacker_residual']==0 and r['peak_funding']<=5000 for r in rows)
    assert all(r['complete_exit_profit']==r['independent_pending_buy_control_profit'] for r in rows)


@pytest.mark.parametrize('arch',['A','B','C','D'])
def test_finite_policies_include_abstention_and_obey_actor_budget(arch):
    c=Config(name=arch,arch=arch,rule='commit' if arch=='D' else 'cap',opportunities=80)
    for p in policies(arch=='D'):
        w=World(c,make_tape(100,80),p);w.run()
        w.b.invariant()
        assert 0<=w.peak<=5000*M
    assert policies(arch=='D')[0].family=='idle'


def test_immediate_auction_exit_is_a_real_funded_strategy():
    c=Config(name='D',arch='D',rule='commit',opportunities=120,broad=1,lock_willingness=1)
    w=World(c,make_tape(100,120),Policy('capture',3000*M,0));rows,_,_=w.run()
    # Feasibility and cash P&L, not a forced assertion of profit in every seed.
    assert rows[-1]['attacker_residual']==0
    assert rows[-1]['attacker_peak']>0 and w.auction.state=='settled'
