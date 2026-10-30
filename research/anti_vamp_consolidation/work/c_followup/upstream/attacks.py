"""Finite disclosed strategy classes and funded ordering stress experiments."""
from copy import deepcopy
from dataclasses import asdict
from .ledger import Book,Refused,MONEY as M,TOKEN as Q
from .model import Policy


def policies(batch=False):
    rows=[Policy()]
    for budget in (250,1000,3000):
        for delay in (0,3600):rows.append(Policy('capture',budget*M,delay))
    if not batch:
        for aliases in (8,32,64):
            for budget in (1000,3000):rows.append(Policy('split',budget*M,3600,aliases))
        for rounds in (2,8):rows.append(Policy('wash',500*M,3600,1,rounds))
        for budget in (500,2000):rows.append(Policy('support_front',budget*M))
    return rows


def ordering_study():
    """Grid over capital and victim limits; every leg funded, full bot exit.

    Same pending order is an A control, so this is not claimed unique to C.
    """
    rows=[]
    for fee in (0,40):
        for slippage_bps in (0,100,1000,5000):
            for budget in (0,25,100,250,500,1000,3000):
                b=Book(2,fee//4,fee-fee//4,0 if fee==0 else 10_000,capture=True)
                for owner,cash in [('seed',10000*M),('victim',3000*M),('bot',5000*M)]:b.fund(owner,cash)
                b.buy('seed',0,60*M);b.buy('victim',1,2000*M)
                loser=b.hold['victim',1]
                proceeds=b.sell_quote(1,loser)[3]
                expected=b.buy_quote(0,proceeds)[0]
                minimum=expected*(10000-slippage_bps)//10000
                initial=b.cash['bot'];cost0=b.fees_paid['bot'];front=None
                if budget:
                    try:front=b.buy('bot',0,budget*M)
                    except Refused:pass
                peak=initial-b.cash['bot'];snapshot=deepcopy((dict(b.cash),dict(b.hold),list(b.q)))
                try:
                    _,victim=b.migrate('victim',1,0,loser,allowed=(0,),minimum=minimum)
                    filled=True
                except Refused:
                    assert snapshot==(dict(b.cash),dict(b.hold),list(b.q))
                    filled=False;victim=None
                if front:b.sell('bot',0,front.quantity)
                profit=b.cash['bot']-initial
                victim_exit=b.sell('victim',0,b.hold['victim',0]).cash_delta if filled else 0
                b.invariant()
                rows.append(dict(fee_bps=fee,slippage_bps=slippage_bps,budget=budget,
                                 peak_funding=peak/M,acquisition=front.principal/M if front else 0,
                                 irreversible_fees=(b.fees_paid['bot']-cost0)/M,
                                 complete_exit_profit=profit/M,filled=filled,
                                 winner_output=victim.quantity/Q if victim else 0,
                                 victim_complete_exit= victim_exit/M,
                                 reserve_remaining=b.cash['market:0']/M,
                                 attacker_residual=b.hold['bot',0]/Q,
                                 independent_pending_buy_control_profit=profit/M))
    return rows
