from dataclasses import replace
import pytest
from bonding_lab.narrative.model import Config,Policy,World,run,make_tape,elect
from bonding_lab.narrative.ledger import Book,MONEY as M,TOKEN as Q


def config(arch):return Config(name=arch,arch=arch,rule='commit' if arch in ('D','single_batch','independent_batch') else 'cap',opportunities=100)


@pytest.mark.parametrize('arch',['A','B','C','D','single_spot','single_batch','independent_batch','locked_spot'])
def test_deterministic_conservation_and_matched_endowments(arch):
    c=config(arch);t=make_tape(0,c.opportunities)
    a,trace,rank=run(c,t,capture=True);b,_,_=run(c,t)
    assert a==b
    assert all(r['initial_world']==39100 and r['escrow']==0 for r in a)
    assert all(r['tape_hash']==t['_sha256'] for r in a)
    assert trace and rank or arch in ('single_spot','single_batch')


def test_router_reach_and_consent_are_distinct():
    t=make_tape(3,100);c=config('C')
    zero,_,_=run(replace(c,reach=0),t)
    refuse,_,_=run(replace(c,acceptance=0),t)
    accept,_,_=run(replace(c,acceptance=1,reach=1),t)
    assert zero[-2]['reachable']==0
    assert refuse[-2]['authorized']==0
    assert accept[-2]['reachable']>0 and accept[-2]['authorized']>0
    assert accept[-2]['authorized']<accept[-2]['reachable']


@pytest.mark.parametrize('setting',[dict(no_winner=True),dict(force_tie=True),dict(withheld=True),dict(delay=8000)])
def test_no_winner_refund_and_timeout(setting):
    c=replace(config('D'),**setting);w=World(c,make_tape(1,100));w.run()
    assert w.winner is None and w.b.cash['escrow']==0
    assert sum(r.spent for r in w.auction.receipts)==0
    assert all(r.amount==r.refunded for r in w.auction.receipts)
    w.b.invariant()


def test_independent_zero_reach_routing_disabled_control():
    t=make_tape(2,100)
    a=run(config('A'),t)[0];c=run(replace(config('C'),reach=0,migration=0),t)[0]
    for ar,cr in zip(a,c):
        for key in ('cohort_reserve','executed','offered','outside_spent','trader_cash_change'):
            assert ar[key]==cr[key]


def test_wallet_count_can_be_manipulated_without_actor_capital_creation():
    b=Book(10,0,0,0);b.fund('actor',200*M);b.fund('honest',200*M)
    b.buy('honest',0,100*M);b.buy('actor',1,100*M)
    for i in range(8):b.transfer_claims('actor',f'alias{i}',1,Q)
    winner,_,_=elect(b,'holders',range(2),1800)
    assert winner==1 and sum(b.cash.values())==400*M
    b.invariant()


@pytest.mark.parametrize('rule',['commit','timecommit'])
def test_commitment_overlay_is_funded_and_refunded(rule):
    c=replace(config('C'),rule=rule,overlay=True)
    w=World(c,make_tape(5,100));w.run()
    assert w.b.cash['escrow']==0
    assert all(r.refunded==r.amount for r in w.overlay.receipts)
    w.b.invariant()


def test_unavailable_d_spot_metric_is_explicit():
    w=World(replace(config('D'),rule='cap'),make_tape(0,100));w.run()
    assert w.reason=='N/A_spot_metric_before_issuance' and w.winner is None


def test_timeout_refunds_by_deadline_before_late_finalizer():
    c=replace(config('D'),delay=8000)
    w=World(c,make_tape(1,100),capture=True);w.run()
    refunds=[r for r in w.b.trace if r['event']=='refund']
    assert refunds and max(r['time'] for r in refunds)<=w.auction.deadline+1


def test_refusing_d_creators_launch_outside_without_platform_escrow():
    c=replace(config('D'),refusal=.5)
    w=World(c,make_tape(0,100))
    refused=set(range(10))-set(w.members)
    assert refused
    assert all(r.owner not in {f'creator:{i}' for i in refused} for r in w.auction.receipts)
    assert all(w.b.q[i]>0 for i in refused)
    w.run();w.b.invariant()


def test_b_lock_unlock_and_destruction_have_separate_traces():
    t=make_tape(1,100)
    locked=World(config('B'),t);locked.run()
    burned=World(replace(config('B'),support_mode='protocol_destroy'),t);burned.run()
    before=next(r for r in locked.snapshots if r['label']=='before_unlock')
    after=next(r for r in locked.snapshots if r['label']=='after_unlock')
    assert before['support_claims']>0 and after['support_claims']==0
    assert sum(burned.b.buffer)>0 and sum(locked.b.buffer)==0


def test_adversarial_aliases_use_one_endowment():
    c=replace(config('C'),rule='holders')
    p=Policy('split',3000*M,0,8)
    w=World(c,make_tape(0,100),p);w.run()
    assert w.peak<=5000*M
    assert sum(w.b.principal_bought[o] for o in w.actor)<=3000*M
    assert w.b.initial==39100*M
