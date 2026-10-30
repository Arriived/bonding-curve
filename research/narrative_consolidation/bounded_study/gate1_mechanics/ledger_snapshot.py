"""Integer settlement of independent a=.01, b=.0001 issuance curves.

Quote quantum 1e-6, claim quantum 1e-4. Cumulative backing is rounded DOWN;
differences of that same cumulative function telescope exactly. No floats decide
funding, allocation, fees, consent, minimum output, or execution feasibility.
"""
from collections import defaultdict
from dataclasses import dataclass
from math import isqrt

MONEY = 1_000_000
TOKEN = 10_000
BOUND = 10**18


class Refused(ValueError):
    pass


def integer(x):
    if type(x) is not int or not 0 <= x <= BOUND:
        raise Refused("Expected bounded nonnegative integer")
    return x


def reserve(q):
    integer(q)
    return q + q*q//2_000_000


def inverse_reserve(cash):
    integer(cash)
    return isqrt(10**12 + 2_000_000*(cash+1)-1)-1_000_000


def prorata(total, weights):
    """Largest remainders, stable input/receipt-ID ties; exact integer total."""
    if not weights or sum(weights) == 0:
        return [0]*len(weights)
    denom = sum(weights)
    rows = [divmod(total*w, denom) for w in weights]
    result = [v[0] for v in rows]
    for i in sorted(range(len(rows)), key=lambda i: (-rows[i][1], i))[:total-sum(result)]:
        result[i] += 1
    return result


@dataclass(frozen=True)
class Fill:
    owner: str
    token: int
    side: str
    quantity: int
    principal: int
    protocol_fee: int
    creator_fee: int
    network: int
    cash_delta: int


class Book:
    def __init__(self, n=10, protocol_bps=10, creator_bps=30, gas=10_000, capture=False):
        if not 0 <= protocol_bps+creator_bps < 10000:
            raise Refused("Invalid fees")
        self.n=n; self.fp=protocol_bps; self.fc=creator_bps; self.gas=integer(gas)
        self.cash=defaultdict(int); self.hold=defaultdict(int); self.basis=defaultdict(int)
        self.realized=defaultdict(int); self.q=[0]*n; self.buffer=[0]*n
        self.initial=0; self.trace=[] if capture else None; self.time=0
        self.fees_paid=defaultdict(int); self.principal_bought=defaultdict(int)
        self.principal_sold=defaultdict(int)

    def log(self, event, **kw):
        if self.trace is not None:self.trace.append(dict(time=self.time,event=event,**kw))

    def fund(self, owner, cash):
        integer(cash); self.cash[owner]+=cash; self.initial+=cash
        self.log("endowment",owner=owner,cash=cash)

    def transfer(self, owner, receiver, cash):
        integer(cash)
        if self.cash.get(owner,0)<cash:raise Refused("Unfunded transfer")
        self.cash[owner]-=cash; self.cash[receiver]+=cash
        self.log("cash_transfer",owner=owner,receiver=receiver,cash=cash)

    def check_token(self, token):
        if type(token) is not int or not 0<=token<self.n:raise Refused("Unknown token")

    def fees(self, principal):
        return ((principal*self.fp+9999)//10000, (principal*self.fc+9999)//10000)

    def buy_quote(self, token, budget):
        self.check_token(token); integer(budget)
        usable=budget-self.gas
        if usable<=0:return 0,0,0,0
        gross=usable*10000//(10000+self.fp+self.fc)
        for _ in range(5):
            newq=inverse_reserve(reserve(self.q[token])+max(0,gross))
            d=max(0,newq-self.q[token]); principal=reserve(newq)-reserve(self.q[token])
            pf,cf=self.fees(principal)
            if principal+pf+cf<=usable:return d,principal,pf,cf
            gross-=1
        raise ArithmeticError("Fee inversion failed")

    def buy(self, owner, token, budget, *, allowed=None, minimum=0):
        integer(budget); integer(minimum)
        if allowed is not None and token not in allowed:raise Refused("Received mint not authorized")
        if budget>self.cash.get(owner,0):raise Refused("Buy exceeds owned cash")
        d,g,pf,cf=self.buy_quote(token,budget)
        if d<=0 or d<minimum:raise Refused("Minimum output or quantity")
        spend=g+pf+cf+self.gas
        self.transfer(owner,f"market:{token}",g)
        self.transfer(owner,"protocol",pf); self.transfer(owner,f"creator:{token}",cf)
        self.transfer(owner,"network",self.gas)
        self.q[token]+=d; self.hold[owner,token]+=d; self.basis[owner,token]+=spend
        self.fees_paid[owner]+=pf+cf+self.gas; self.principal_bought[owner]+=g
        tx=Fill(owner,token,"buy",d,g,pf,cf,self.gas,-spend)
        self.log("trade",**tx.__dict__)
        return tx

    def sell_quote(self, token, d):
        self.check_token(token); integer(d)
        if d<=0 or d>self.q[token]:raise Refused("Invalid redemption")
        gross=reserve(self.q[token])-reserve(self.q[token]-d)
        pf,cf=self.fees(gross)
        return gross,pf,cf,gross-pf-cf-self.gas

    def sell(self, owner, token, d, *, minimum=0):
        integer(minimum)
        if self.hold.get((owner,token),0)<d:raise Refused("Unowned claims")
        gross,pf,cf,net=self.sell_quote(token,d)
        if net<minimum or self.cash.get(owner,0)+net<0:raise Refused("Sale limits/costs")
        held=self.hold[owner,token]
        removed=self.basis[owner,token] if d==held else self.basis[owner,token]*d//held
        self.transfer(f"market:{token}",owner,gross)
        self.transfer(owner,"protocol",pf);self.transfer(owner,f"creator:{token}",cf)
        self.transfer(owner,"network",self.gas)
        self.q[token]-=d;self.hold[owner,token]-=d;self.basis[owner,token]-=removed
        self.realized[owner]+=net-removed
        self.fees_paid[owner]+=pf+cf+self.gas;self.principal_sold[owner]+=gross
        tx=Fill(owner,token,"sell",d,gross,pf,cf,self.gas,net)
        self.log("trade",**tx.__dict__)
        return tx

    def migrate(self, owner, loser, winner, d, *, allowed, minimum=0):
        """All feasibility checks precede both independently priced legs."""
        if loser==winner or winner not in allowed:raise Refused("Migration consent")
        if d>self.hold.get((owner,loser),0):raise Refused("Migration ownership")
        _,_,_,net=self.sell_quote(loser,d)
        if net<=0:raise Refused("No funded migration proceeds")
        qty,*_=self.buy_quote(winner,net)
        if qty<=0 or qty<minimum:raise Refused("Atomic conversion minimum")
        first=self.sell(owner,loser,d)
        second=self.buy(owner,winner,net,allowed=allowed,minimum=minimum)
        self.log("migration",owner=owner,loser=loser,winner=winner,proceeds=net,quantity=qty)
        return first,second

    def transfer_claims(self, owner, receiver, token, d):
        integer(d)
        h=self.hold.get((owner,token),0)
        if d>h:raise Refused("Unfunded claim transfer")
        cost=self.basis[owner,token] if d==h else self.basis[owner,token]*d//max(1,h)
        self.hold[owner,token]-=d;self.hold[receiver,token]+=d
        self.basis[owner,token]-=cost;self.basis[receiver,token]+=cost
        self.log("claim_transfer",owner=owner,receiver=receiver,token=token,quantity=d)

    def destroy(self, owner, token, d):
        if d>self.hold.get((owner,token),0):raise Refused("Unowned burn")
        integer(d); before=reserve(self.q[token]); h=self.hold[owner,token]
        cost=self.basis[owner,token] if d==h else self.basis[owner,token]*d//max(1,h)
        self.hold[owner,token]-=d;self.basis[owner,token]-=cost
        self.realized[owner]-=cost;self.q[token]-=d
        self.buffer[token]+=before-reserve(self.q[token])
        self.log("destroy",owner=owner,token=token,quantity=d)

    def depth(self, token, impact_bps, locked=()):
        private=sum(d for (o,i),d in self.hold.items() if i==token and o not in locked)
        # p/b in claim quanta = q + 1,000,000 for this denomination.
        d=min(private,(self.q[token]+1_000_000)*impact_bps//10000)
        if not d:return 0
        return reserve(self.q[token])-reserve(self.q[token]-d)

    def invariant(self):
        assert sum(self.cash.values())==self.initial,"cash conservation"
        assert min(self.cash.values(),default=0)>=0,"negative cash"
        assert min(self.hold.values(),default=0)>=0,"negative holdings"
        for i in range(self.n):
            assert self.q[i]==sum(d for (o,j),d in self.hold.items() if j==i),"ownership"
            assert self.cash[f"market:{i}"]==reserve(self.q[i])+self.buffer[i],"backing"
        return True


@dataclass
class Receipt:
    owner: str
    preferred: int
    allowed: tuple
    amount: int
    time: int
    expiry: int
    max_price: int
    spent: int=0
    tokens: int=0
    refunded: int=0
    state: str="live"


class Auction:
    def __init__(self, book, close=1800, cancel_until=1620, deadline=9000,
                 qmax=1_000_000*TOKEN, minimum_raise=10*MONEY):
        self.b=book;self.close=close;self.cancel_until=cancel_until;self.deadline=deadline
        self.qmax=qmax;self.minimum_raise=minimum_raise;self.receipts=[];self.state="open"

    @property
    def pbar(self):
        # Worst-case average all-in quote quanta per whole token, rounded up.
        g=reserve(self.qmax);pf,cf=self.b.fees(g)
        return ((g+pf+cf)*TOKEN+self.qmax-1)//self.qmax+TOKEN

    def commit(self, owner, preferred, allowed, amount, time, expiry, max_price=None):
        if self.state!="open" or time>=self.close:raise Refused("Commitment closed")
        self.b.check_token(preferred);integer(amount)
        allowed=tuple(allowed)
        if any(type(i) is not int or not 0<=i<self.b.n for i in allowed):raise Refused("Allowed mints")
        price=self.pbar if max_price is None else integer(max_price)
        if amount<=0 or expiry<self.deadline or price<self.pbar:raise Refused("Nonqualifying receipt")
        self.b.transfer(owner,"escrow",amount)
        self.receipts.append(Receipt(owner,preferred,allowed,amount,time,expiry,price))
        self.b.log("commit",receipt=len(self.receipts)-1,owner=owner,preferred=preferred,
                   allowed=allowed,amount=amount,expiry=expiry,max_price=price)
        return len(self.receipts)-1

    def refund(self, idx):
        r=self.receipts[idx]
        if r.state!="live":return 0
        amount=r.amount-r.spent
        self.b.transfer("escrow",r.owner,amount);r.refunded+=amount;r.state="refunded"
        self.b.log("refund",receipt=idx,owner=r.owner,amount=amount)
        return amount

    def cancel(self, idx, owner, time):
        r=self.receipts[idx]
        if owner!=r.owner or time>=self.cancel_until:raise Refused("Cancellation not authorized")
        return self.refund(idx)

    def abort(self, reason="no_winner"):
        if self.state in ("settled","refunded"):return
        for idx in range(len(self.receipts)):self.refund(idx)
        self.state="refunded";self.b.log("auction_abort",reason=reason)

    def settle(self, winner, time, *, independent=False):
        if self.state in ("settled","refunded"):return []
        if time<self.close:raise Refused("Premature settlement")
        if time>self.deadline or winner is None and not independent:
            self.abort("timeout" if time>self.deadline else "no_winner");return []
        outputs=[]
        targets=range(self.b.n) if independent else [winner]
        for token in targets:
            ids=[i for i,r in enumerate(self.receipts) if r.state=="live" and
                 (r.preferred==token if independent else token in r.allowed) and r.expiry>=time]
            if not ids:continue
            if self.b.q[token]!=0:raise Refused("Batch market already exists")
            funds=sum(self.receipts[i].amount for i in ids)
            gross_cap=reserve(self.qmax);pf,cf=self.b.fees(gross_cap)
            budget=min(funds,gross_cap+pf+cf)
            # Batch has no per-bid execution gas. Sponsor pays one settlement call.
            gas=self.b.gas;self.b.gas=0
            try:qty,g,pf,cf=self.b.buy_quote(token,budget)
            finally:self.b.gas=gas
            if g<self.minimum_raise:continue
            spends=prorata(g+pf+cf,[self.receipts[i].amount for i in ids])
            alloc=prorata(qty,spends)
            if any(s*TOKEN>self.receipts[i].max_price*q for i,s,q in zip(ids,spends,alloc)):
                continue
            if self.b.cash.get("sponsor",0)<gas:continue
            self.b.transfer("sponsor","network",gas)
            self.b.transfer("escrow",f"market:{token}",g)
            self.b.transfer("escrow","protocol",pf);self.b.transfer("escrow",f"creator:{token}",cf)
            self.b.q[token]+=qty
            for idx,spent,q in zip(ids,spends,alloc):
                r=self.receipts[idx];r.spent=spent;r.tokens=q
                self.b.hold[r.owner,token]+=q;self.b.basis[r.owner,token]+=spent
                self.b.transfer("escrow",r.owner,r.amount-spent)
                r.refunded=r.amount-spent;r.state="settled"
                self.b.log("allocation",receipt=idx,owner=r.owner,token=token,spent=spent,quantity=q)
            outputs.append((token,qty,g,pf,cf))
        for i in range(len(self.receipts)):self.refund(i)
        self.state="settled" if outputs else "refunded"
        self.b.invariant();self.invariant()
        return outputs

    def invariant(self):
        assert self.b.cash["escrow"]==sum(r.amount for r in self.receipts if r.state=="live")
        for r in self.receipts:
            if r.state!="live":assert r.spent+r.refunded==r.amount
        return True
