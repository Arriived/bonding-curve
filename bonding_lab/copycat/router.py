"""Funded float routing on the existing independent FastBook; no new curve math."""
import math
import numpy as np


class Router:
    def __init__(self,book,variant,treasury,dead,network,gas=0,record=None,actor_wallets=()):
        if book.coupling!=0:raise ValueError("Copycat study requires independent curves")
        self.b=book;self.v=variant;self.treasury=treasury;self.dead=dead;self.network=network
        self.gas=gas;self.record=record
        self.paid=np.zeros(len(book.cash));self.received=np.zeros(len(book.cash))
        self.creator_receipts=0.;self.holder_receipts=0.;self.burned_surplus=0.
        self.diverted=0.;self.organic_volume=np.zeros(len(book.q));self.all_volume=np.zeros(len(book.q))
        self.actor_wallets=set(int(w) for w in actor_wallets);self.external_actor_receipts=0.

    def transfer(self,sender,recipient,amount):
        if not math.isfinite(amount) or amount<0 or amount>self.b.cash[sender]:raise ValueError("Unfunded transfer")
        if sender!=recipient:self.b.cash[sender]-=amount;self.b.cash[recipient]+=amount

    def quantity(self,token,budget):
        if budget<=0:return 0.
        d=self.b.buy_quantity(token,budget)
        # Inverse sqrt can round UP. Settle at a representable quantity whose
        # actual existing-engine debit, including its fee expression, fits.
        for _ in range(16):
            gross=self.b.price(token)*d+self.b.k*d*d/2
            if gross+gross*self.b.fee_rate<=budget:return d
            d=float(np.nextafter(d,0.))
        raise ArithmeticError("Unable to find funded representable quantity")

    def _fill(self,t,w,token,d,side,source,organic):
        tx=self.b.execute(w,token,float(d),side)
        self.all_volume[token]+=tx.gross
        if organic:self.organic_volume[token]+=tx.gross
        if self.record:self.record(t,token,source,tx.gross,side)
        return tx

    def buy(self,t,w,token,budget,leader,creator,organic=False,min_leader_quantity=0.):
        b=self.b;v=self.v
        if not math.isfinite(budget) or budget<=0:raise ValueError("Positive buy budget required")
        eligible=leader is not None and leader!=token and v.form!="control" and v.rate>0
        D=budget*v.rate if eligible else 0.
        holders=None
        if D and v.form=="holders":
            holders=b.holdings[:,leader].copy();holders[[self.dead,self.treasury]]=0
            if holders.sum()<=1e-12:D=0.
        needs_lead=D>0 and v.form in ("buyer","treasury","burn")
        gas=self.gas*(2 if needs_lead else 1)
        if budget+gas>b.cash[w]+1e-8:raise ValueError("Unfunded routed buy")
        spendable=max(0.,float(b.cash[w])-gas-8*math.ulp(float(b.cash[w])))
        if budget>spendable:
            budget=spendable;D=budget*v.rate if eligible else 0.
            if holders is not None and holders.sum()<=1e-12:D=0.
        if budget<=0:raise ValueError("No funded spendable budget")
        d=self.quantity(token,budget-D)
        ld=self.quantity(leader,D) if needs_lead else 0.
        if d<=1e-12:raise ValueError("Below trade quantum")
        if ld+1e-10<min_leader_quantity:raise ValueError("Leader leg minimum output not met")
        # All checks precede transfers, so slippage/funding rejection is atomic.
        self.transfer(w,self.network,gas)
        if D and v.form in ("creator","holders"):
            if v.form=="creator":
                self.transfer(w,creator,D);self.received[creator]+=D;self.creator_receipts+=D
                if w not in self.actor_wallets and creator in self.actor_wallets:self.external_actor_receipts+=D
            else:
                allocation=D*holders/holders.sum()
                j=int(np.argmax(holders));allocation[j]+=D-float(allocation.sum())
                b.cash[w]-=D;b.cash+=allocation;self.received+=allocation;self.holder_receipts+=D
                if w not in self.actor_wallets:self.external_actor_receipts+=sum(allocation[a] for a in self.actor_wallets)
        self._fill(t,w,token,d,"buy",w,organic)
        if needs_lead and ld>1e-12:
            receiver=w if v.form=="buyer" else self.treasury if v.form=="treasury" else self.dead
            amount=D
            if receiver!=w:self.transfer(w,receiver,amount)
            self._fill(t,receiver,leader,ld,"buy",w,organic)
            if v.form=="burn" and v.burn=="supply":self.destroy(leader,ld)
        self.diverted+=D;self.paid[w]+=D
        return d,ld,D

    def sell(self,t,w,token,d,organic=False,protocol=False):
        if w==self.dead or (w==self.treasury and not protocol):raise ValueError("Inaccessible protocol inventory")
        if d<=1e-12:return 0.
        if self.b.cash[w]<self.gas:
            # A sale's funded receipt can pay network expense atomically.
            gross=self.b.price(token)*d-self.b.k*d*d/2
            if gross-gross*self.b.fee_rate+self.b.cash[w]<self.gas:return 0.
        tx=self._fill(t,w,token,d,"sell",w,organic)
        self.transfer(w,self.network,self.gas)
        return tx.cash_change-self.gas

    def destroy(self,token,d):
        b=self.b;old=b.q[token]
        if d>b.holdings[self.dead,token]+1e-10:raise ValueError("Unowned destruction")
        released=b.price(token)*d-b.k*d*d/2
        held=b.holdings[self.dead,token]
        basis=b.basis[self.dead,token] if d==held else b.basis[self.dead,token]*d/held
        b.basis[self.dead,token]-=basis;b.realized[self.dead]-=basis;b.holdings[self.dead,token]-=d
        b.q[token]-=d;b.Q-=d;b.q2+=b.q[token]**2-old**2
        b.required-=released;b.buffer+=released;self.burned_surplus+=released

    def accessible(self):
        b=self.b;locked=b.holdings[self.dead]+b.holdings[self.treasury]
        # Aggregate private-holder exit: mutually compatible across independent tokens.
        return (b.p0*(b.q-locked)+b.k/2*(b.q*b.q-locked*locked))*(1-b.fee_rate)
