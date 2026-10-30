"""Decimal reference routing on the existing exact independent-curve ledger."""
from decimal import Decimal,ROUND_FLOOR
from ..engine import Curve,Parameters,Wallet,RejectedTrade,decimal,precise,ZERO


class DiversionReference(Curve):
    def __init__(self,p0=".01",k=".0001",fee=".003"):
        super().__init__(Parameters(p0=p0,k=k,coupling=0,fee_rate=fee))
        self.create_wallet("treasury",0);self.create_wallet("dead",0)

    @precise
    def quantity(self,token,budget):
        B=decimal(budget)/(1+self.params.fee_rate);p=self.price(token);k=self.params.k
        d=2*B/(p+(p*p+2*k*B).sqrt())
        return d.quantize(Decimal("1e-12"),rounding=ROUND_FLOOR)

    @precise
    def destroy(self,wallet,token,d):
        d=decimal(d);self._token(token);owner=self._wallet(wallet)
        if d<=0 or d>owner.holdings[token]:raise RejectedTrade("Invalid unfunded destruction")
        released,_=self.quote(token,d,"sell")
        old=self._q[token]
        removed=owner.cost_basis[token]*d/owner.holdings[token]
        owner.holdings._values[token]-=d;owner.cost_basis._values[token]-=removed
        self._wallets[wallet]=Wallet(owner.cash,owner.holdings,owner.cost_basis,owner.realized_pnl-removed)
        self._q[token]-=d;self._Q-=d;self._squares+=self._q[token]**2-old**2
        self._required-=released;self._buffer+=released

    @precise
    def routed_buy(self,wallet,token,budget,leader=None,creator=None,form="buyer",rate=".05",burn="lock"):
        B=decimal(budget);alpha=decimal(rate)
        if B<=0 or alpha>1 or B>self._wallet(wallet).cash:raise RejectedTrade("Unfunded buy")
        self._token(token)
        if form not in ("creator","holders","buyer","treasury","burn","control"):raise RejectedTrade("Unknown route")
        if leader is not None:self._token(leader)
        tax=leader is not None and leader!=token and form!="control"
        D=B*alpha if tax else ZERO
        holders=[]
        if form=="holders" and D:
            holders=[(name,w.holdings[leader]) for name,w in self.wallets.items()
                     if name not in ("treasury","dead") and w.holdings[leader]>0]
            if not holders:D=ZERO
        if form=="creator" and D:self._wallet(creator)
        copy_d=self.quantity(token,B-D)
        lead_d=self.quantity(leader,D) if D and form in ("buyer","treasury","burn") else ZERO
        if copy_d<=0:raise RejectedTrade("Below quantity quantum")
        self.quote(token,copy_d,"buy")
        if lead_d:self.quote(leader,lead_d,"buy")
        if D and form in ("creator","holders"):
            if form=="creator":self.transfer_cash(wallet,creator,D)
            else:
                total=sum(h for _,h in holders);remaining=D
                for j,(name,h) in enumerate(holders):
                    amount=remaining if j==len(holders)-1 else (D*h/total).quantize(Decimal("1e-18"),rounding=ROUND_FLOOR)
                    self.transfer_cash(wallet,name,amount);remaining-=amount
        self.execute(wallet,token,copy_d,"buy")
        if lead_d:
            receiver=wallet if form=="buyer" else "treasury" if form=="treasury" else "dead"
            if receiver!=wallet:self.transfer_cash(wallet,receiver,D)
            self.execute(receiver,leader,lead_d,"buy")
            if form=="burn" and burn=="supply":self.destroy(receiver,leader,lead_d)
        return dict(copy_quantity=copy_d,leader_quantity=lead_d,diversion=D)
