from copy import deepcopy
from decimal import Decimal,localcontext
import random
import pytest
from bonding_lab.narrative.ledger import Book,Auction,Refused,reserve,prorata,MONEY as M,TOKEN as Q
from bonding_lab.narrative.reference import reference_book


def book(fees=False,gas=0):
    b=Book(10,10 if fees else 0,30 if fees else 0,gas,capture=True)
    for name in ('a','b','bot','victim','support','sponsor'):b.fund(name,10000*M)
    return b


def state(b):
    return deepcopy((dict(b.cash),dict(b.hold),dict(b.basis),b.q,b.buffer,b.trace))


def test_reference_and_integer_reserve_cap_witness():
    r=reference_book();r.create_wallet('a',1000);r.execute('a',0,1000,'buy')
    r.assert_invariants()
    assert r.reserve==60 and r.price(0)*r.supplies[0]==110
    b=book();b.buy('a',0,60*M)
    assert b.q[0]==1000*Q and b.cash['market:0']==60*M
    b.invariant()


def test_d_equal_subscribers_and_first_exit_witness():
    b=book();a=Auction(b,minimum_raise=0)
    for who in ('a','b'):a.commit(who,0,(0,),30*M,0,9000)
    a.settle(0,1800)
    assert b.hold['a',0]==b.hold['b',0]==500*Q
    assert b.sell('a',0,500*Q).cash_delta==42_500_000
    assert b.sell('b',0,500*Q).cash_delta==17_500_000
    b.invariant();a.invariant()


def test_b_support_can_be_extracted_by_original_holders():
    b=book();b.buy('a',0,60*M)
    tx=b.buy('support',0,30*M)
    assert tx.quantity==2453624
    paid=b.sell('a',0,1000*Q).cash_delta
    assert abs(paid-84.53624*M)<=2
    assert abs(b.cash['market:0']-5.46376*M)<=2
    assert b.hold['support',0]==tx.quantity
    b.invariant()


def test_lock_and_destroy_are_different_ownership():
    b=book();b.buy('support',0,30*M)
    q=b.q[0];backing=b.cash['market:0']
    b.destroy('support',0,q)
    assert b.q[0]==0 and b.buffer[0]==backing and b.depth(0,1000)==0
    b.invariant()


def test_migration_ordering_and_atomic_minimum():
    b=book();b.buy('a',0,60*M)
    b.buy('victim',1,160*M)
    out=b.buy('bot',0,160*M)
    baseline_qty=b.buy_quote(0,160*M)[0]
    before=state(b)
    with pytest.raises(Refused):b.migrate('victim',1,0,b.hold['victim',1],allowed=(0,),minimum=baseline_qty+1)
    assert state(b)==before
    victim=b.buy('victim',0,260*M)
    sold=b.sell('bot',0,out.quantity)
    assert out.principal==160*M and victim.quantity==1000*Q
    assert sold.principal==260*M and sold.principal-out.principal==100*M
    b.invariant()


def test_successful_migration_uses_only_net_sale_proceeds():
    b=book(True,10000);b.buy('a',1,100*M)
    before=sum(b.cash[f'market:{i}'] for i in range(10));cash=b.cash['a']
    first,second=b.migrate('a',1,0,b.hold['a',1],allowed=(0,))
    assert second.principal+second.protocol_fee+second.creator_fee+second.network<=first.cash_delta
    assert cash<=b.cash['a']<=cash+10
    assert sum(b.cash[f'market:{i}'] for i in range(10))<before
    b.invariant()


@pytest.mark.parametrize('bad',[-1,1.5,True,10**19])
def test_invalid_quantities_never_authorize_spend(bad):
    b=book();before=state(b)
    with pytest.raises(Refused):b.buy('a',0,bad)
    assert state(b)==before


def test_consent_and_underfunded_execution_do_not_mutate():
    b=book();before=state(b)
    for kwargs in ({'budget':100*M,'allowed':(1,)},{'budget':10001*M},{'budget':M,'minimum':10**15}):
        with pytest.raises(Refused):b.buy('a',0,**kwargs)
        assert state(b)==before


@pytest.mark.parametrize('seed',range(6))
def test_random_integer_conservation_and_decimal_reference(seed):
    b=book(True,1000);rng=random.Random(seed)
    with localcontext() as ctx:
        ctx.prec=80
        for _ in range(120):
            i=rng.randrange(10);owner=rng.choice(('a','b'))
            old=b.q[i]
            if b.hold[owner,i] and rng.random()<.4:
                d=rng.randint(1,b.hold[owner,i])
                try:tx=b.sell(owner,i,d)
                except Refused:continue
                new=old-d
            else:
                budget=rng.randint(2000,2*M)
                tx=b.buy(owner,i,budget);new=old+tx.quantity
                assert -tx.cash_delta<=budget
            def R(q):return Decimal(q)/Q/100+Decimal(q)**2/(2*10000*Q*Q)
            exact=abs(R(new)-R(old))*M
            assert abs(Decimal(tx.principal)-exact)<1
            b.invariant()


def test_alias_funding_and_fee_accounts():
    b=book(True);initial=b.initial
    b.transfer('bot','alias',25*M);b.buy('alias',0,25*M)
    assert b.cash['bot']==9975*M and b.cash['alias']>=0 and b.initial==initial
    assert b.cash['protocol']>0 and b.cash['creator:0']>0
    with pytest.raises(Refused):b.transfer('alias','bot',26*M)
    b.invariant()


@pytest.mark.parametrize('path',['cancel','timeout','no_winner','incompatible','too_small'])
def test_refund_paths_idempotence(path):
    b=book();a=Auction(b,minimum_raise=10*M)
    amount=M if path=='too_small' else 30*M
    idx=a.commit('a',0,(0,),amount,0,9000)
    before=b.cash['a']
    if path=='cancel':a.cancel(idx,'a',1)
    else:a.settle(None if path=='no_winner' else 1 if path=='incompatible' else 0,
                  10000 if path=='timeout' else 1800)
    cash=b.cash['a'];a.refund(idx);a.settle(0,1800)
    assert b.cash['a']==cash==before+amount
    assert b.cash['escrow']==0
    a.invariant();b.invariant()


def test_receipt_permissions_expiry_cap_partial_and_repeated_settlement():
    b=book();a=Auction(b,qmax=500*Q,minimum_raise=0)
    with pytest.raises(Refused):a.commit('a',0,(0,),M,0,8999)
    idx=a.commit('a',0,(0,),60*M,0,9000)
    with pytest.raises(Refused):a.cancel(idx,'b',1)
    with pytest.raises(Refused):a.cancel(idx,'a',1700)
    a.settle(0,1800);before=state(b);a.settle(0,1800)
    assert state(b)==before and b.q[0]==500*Q
    assert a.receipts[0].spent==17_500_000
    assert a.receipts[0].refunded==42_500_000
    b.invariant()


def test_c_equal_retention_no_extra_demand_does_not_create_capital():
    a=book();c=book()
    for i in range(10):a.buy('a',i,10*M);c.buy('a',i,10*M)
    for i in range(10):a.buy('b',i,20*M);c.buy('b',0,20*M,allowed=(0,))
    ra=sum(a.cash[f'market:{i}'] for i in range(10));rc=sum(c.cash[f'market:{i}'] for i in range(10))
    # Different prices leave different owned token-quantum dust, never new money.
    ca=a.cash['a']+a.cash['b'];cc=c.cash['a']+c.cash['b']
    assert ra<=300*M and rc<=300*M and ra+ca==rc+cc==20000*M
    assert ra-rc==cc-ca
    a.invariant();c.invariant()


def test_allocation_exact_and_dust_funded():
    for total in range(100):
        alloc=prorata(total,[7,3,1])
        assert sum(alloc)==total and min(alloc)>=0


def test_live_receipt_cannot_be_refunded_outside_authorized_transition():
    b=book();a=Auction(b)
    idx=a.commit('a',0,(0,),30*M,0,9000)
    before=state(b)
    with pytest.raises(Refused):a.refund(idx)
    assert state(b)==before
    with pytest.raises(Refused):a.commit('a',0,(1,),30*M,0,9000)


def test_batch_success_fees_and_principal_are_attributed_to_actual_owners():
    b=book(True,10000);a=Auction(b,minimum_raise=0)
    for o in ('a','b'):a.commit(o,0,(0,),30*M,0,9000)
    a.settle(0,1800)
    assert sum(r.principal for r in a.receipts)==b.cash['market:0']
    assert sum(r.fee for r in a.receipts)==b.protocol_accrued+b.creator_accrued
    for r in a.receipts:
        assert r.principal+r.fee==r.spent
        assert b.principal_bought[r.owner]==r.principal and b.fees_paid[r.owner]==r.fee
    b.invariant()
