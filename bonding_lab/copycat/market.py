"""Viral arrival/exit market with funded copy creators, routing and strategy hooks."""
from dataclasses import asdict
import math
import numpy as np
from ..fast import FastBook
from .config import Strategy
from .matching import Matcher
from .election import Election
from .router import Router


class Market:
    def __init__(self,v,c,strategy=Strategy(),capture=False,details=False):
        self.v=v;self.c=c;self.s=strategy;self.capture=capture;self.details=details
        self.n=c.base_tokens+c.max_spam+1
        self.org=np.arange(c.events)
        self.creators=np.arange(c.events,c.events+c.base_tokens)
        self.snipers=np.arange(self.creators[-1]+1,self.creators[-1]+5)
        self.bundlers=np.arange(self.snipers[-1]+1,self.snipers[-1]+5)
        self.attack=np.arange(self.bundlers[-1]+1,self.bundlers[-1]+34)
        self.treasury=int(self.attack[-1]+1);self.dead=self.treasury+1;self.fee_wallet=self.dead+1;self.network=self.fee_wallet+1
        wallets=self.network+1
        self.book=FastBook(self.n,wallets,c.p0,c.k,0.,c.fee,0.)
        cash=np.zeros(wallets);cash[self.org]=c.organic_capital/c.events
        cash[self.creators]=5000.;cash[self.creators[:2]]=10000.
        cash[self.snipers]=5000.;cash[self.bundlers]=5000.;cash[self.attack[0]]=c.attacker_capital
        self.book.cash=cash;self.book.initial_wealth=cash.copy();self.book.initial_external=float(cash.sum())
        self.initial=cash.copy()
        self.active=np.zeros(self.n,dtype=bool);self.launches=np.full(self.n,np.inf)
        self.creator=np.full(self.n,int(self.attack[0]),dtype=int)
        self.creator[:c.base_tokens]=self.creators
        self.tickers=["ELON"]*self.n
        near=["elon","ELON1","ELONN","EL0N"," ELON ","ELON "]
        for i in range(8,c.base_tokens):self.tickers[i]=near[(i-8)%len(near)]
        self.matcher=Matcher(v.matching)
        self.election=Election(v,self.matcher,self.launches,self.active,self.book)
        self.router=Router(self.book,v,self.treasury,self.dead,self.network,c.gas,self.election.record,self.attack)
        rng=np.random.default_rng(c.seed)
        self.budgets=c.total_demand/c.events*np.minimum(6,rng.lognormal(-.32,.8,c.events))
        self.informed=rng.random(c.events)<c.informed
        self.confused=rng.random(c.events)<c.confusion
        self.badge_draw=rng.random(c.events);self.choice=rng.random(c.events)
        delay=rng.uniform(20,100,c.events)
        self.exit_indices=np.floor(np.arange(c.events)+delay/c.horizon*c.events).astype(int)
        self.exit_indices[rng.random(c.events)>c.exit_probability]=c.events+1
        self.exit_schedule={}
        for w,idx in enumerate(self.exit_indices):self.exit_schedule.setdefault(int(idx),[]).append(w)
        self.closing=rng.permutation(wallets) if c.exit_order=="random" else np.arange(wallets)
        if c.exit_order=="reverse":self.closing=self.closing[::-1]
        self.target=np.full(c.events,-1,dtype=int);self.role=np.full(c.events,"unfilled",dtype=object)
        self.was_confused=np.zeros(c.events,dtype=bool)
        self.history=[];self.area=np.zeros(11);self.previous_t=0.;self.previous_state=None
        self.started=False;self.unwound=False;self.last_pulse=-1e9;self.front_count=0
        self.completed_buys=0;self.rejected=0
        self.peak_capital=0.

    @property
    def main(self):return self.c.base_tokens

    def root_leader(self):return self.election.leader(0) if self.active[0] else None

    def buy(self,t,w,token,budget,organic=False,minimum=0.):
        if not self.active[token]:return False
        self.election.refresh(t);leader=self.election.leader(token)
        budget=min(float(budget),max(0.,self.book.cash[w]-2*self.c.gas))
        if budget<=.000001:return False
        try:
            self.router.buy(t,int(w),int(token),budget,leader,self.creator[leader] if leader is not None else None,
                            organic,min_leader_quantity=minimum)
        except ValueError as exc:
            if "minimum output" not in str(exc):raise
            self.rejected+=1;return False
        self.peak_capital=max(self.peak_capital,self.c.attacker_capital-float(self.book.cash[self.attack].sum()))
        self.election.refresh(t);return True

    def sell_wallet(self,t,w,fraction=1.,organic=False):
        if w in (self.dead,self.treasury,self.network,self.fee_wallet):return
        for token in np.flatnonzero(self.book.holdings[w]>1e-10):
            held=self.book.holdings[w,token]
            d=held if fraction==1 else held*fraction
            if d>1e-10:self.router.sell(t,int(w),int(token),float(d),organic)
        self.election.refresh(t)

    def launch(self,t,token,ticker=None,seed=0.):
        if self.active[token]:return True
        owner=int(self.creator[token])
        if self.book.cash[owner]<self.c.launch_cost:return False
        self.router.transfer(owner,self.fee_wallet,self.c.launch_cost)
        if ticker is not None:self.tickers[token]=ticker
        self.active[token]=True;self.launches[token]=t;self.matcher.admit(token,self.tickers[token])
        self.election.refresh(t)
        if seed>0:self.buy(t,owner,token,seed)
        return True

    def _fund_alias(self,index,amount):
        w=int(self.attack[index]);source=int(self.attack[0])
        if index and self.book.cash[w]<amount:
            self.router.transfer(source,w,min(amount-self.book.cash[w],self.book.cash[source]))
        return w

    def _pump(self,t,target,scale):
        q=self.book.q[target];p0=self.c.p0;k=self.c.k
        cap=(p0+k*self.book.q)*self.book.q
        goal=self.v.threshold*scale if self.v.rule=="threshold" else max(100000.*scale,float(cap[self.active].max())*1.1)
        desired=2*goal/(p0+math.sqrt(p0*p0+4*k*goal))
        d=max(0.,desired-q)
        need=(self.book.price(target)*d+k*d*d/2)*(1+self.c.fee)
        if self.election.leader(target) not in (None,target) and self.v.form!="control":need/=1-self.v.rate
        self.buy(t,int(self.attack[0]),target,min(need*1.000001,self.book.cash[self.attack[0]]*.95))

    def _wash(self,t,target):
        for a in range(max(3,self.s.aliases)):
            w=self._fund_alias(a,self.s.seed_budget*1.1+2*self.c.gas)
            for _ in range(self.s.rounds):
                self.buy(t,w,target,min(self.s.seed_budget,self.book.cash[w]-2*self.c.gas))
                self.sell_wallet(t,w,1-self.s.residual)

    def act(self,t):
        s=self.s
        if s.family in ("idle","front"):return
        # A first-launched title cannot be stolen by a later capital/flip attack.
        if s.family in ("race","flip") and self.v.rule=="first":return
        if t+1e-9<s.start:return
        if not self.started:
            self.started=True
            self.launch(t,self.main,s.ticker,0.)
            for j in range(min(s.copies,self.c.max_spam)):
                self.launch(t,self.main+j+1,s.ticker,min(50.,self.book.cash[self.attack[0]]*.01))
            if s.family in ("race","flip") and self.v.rule!="volume":self._pump(t,self.main,s.pump)
            elif s.family in ("spam","evasion"):self.buy(t,int(self.attack[0]),self.main,s.seed_budget)
            if self.v.rule=="volume" and s.family in ("race","flip"):
                self._wash(t,self.main);self.last_pulse=t
        if s.family=="flip" and self.active[self.main]:
            interval=s.pulse if s.pulse>0 else self.v.window+1
            eligible_time=self.launches[self.main]+self.v.min_age
            if t>=eligible_time and t-self.last_pulse>=interval:
                if self.v.rule=="volume":self._wash(t,self.main)
                else:self._pump(t,self.main,s.pump)
                self.last_pulse=t
        if (t>=s.exit_at or (s.exit_on_capture and self.root_leader()==self.main)) and not self.unwound:
            for w in self.attack:self.sell_wallet(t,int(w),1-s.residual)
            self.unwound=True

    def front(self,t,token,B):
        if self.s.family!="front":return None
        self.election.refresh(t);leader=self.election.leader(token);v=self.v;b=self.book
        if leader is None or leader==token or v.form in ("control","creator") or not v.rate:return None
        D=B*v.rate;q=b.q[leader];p=b.price(leader);f=b.fee_rate;k=b.k
        cash=b.cash[self.attack[0]]-3*self.c.gas
        if cash<=0:return None
        maxqty=b.buy_quantity(leader,cash)
        victim0=b.buy_quantity(leader,D)
        if v.form=="burn" and v.burn=="supply":return None
        if v.form=="holders" and q<=1e-10:return None
        def outcome(d):
            C=p*d+k*d*d/2
            if v.form=="holders":return D*d/(q+d)-2*f*C-2*self.c.gas
            price=p+k*d
            vd=2*(D/(1+f))/(price+math.sqrt(price*price+2*k*D/(1+f)))
            if vd+1e-12<victim0*(1-self.c.leader_slippage):return -1e30
            return (1-f)*k*d*vd-2*f*C-2*self.c.gas
        if self.s.front_mode=="optimal":
            lo,hi=0.,maxqty
            # Golden-section search includes abstention and the slippage boundary.
            for _ in range(28):
                a=lo+(hi-lo)*.38196601125;z=lo+(hi-lo)*.61803398875
                if outcome(a)<outcome(z):lo=a
                else:hi=z
            d=(lo+hi)/2
        else:d=min(maxqty,b.buy_quantity(leader,D*self.s.front_scale))
        if d<=1e-10 or outcome(d)<=1e-7:return None
        cost=(p*d+k*d*d/2)*(1+f)
        old=b.holdings[self.attack[0],leader]
        self.buy(t,int(self.attack[0]),leader,cost)
        acquired=b.holdings[self.attack[0],leader]-old
        if acquired<=1e-10:return None
        self.front_count+=1
        return leader,float(acquired),victim0*(1-self.c.leader_slippage) if v.form in ("buyer","treasury","burn") else 0.

    def snapshot(self,t):
        if not self.capture:return
        liq=np.maximum(0,self.router.accessible());total=float(liq.sum());lead=self.root_leader()
        volume=self.router.organic_volume;vtotal=float(volume.sum())
        state=np.array([liq[lead]/total if lead is not None and total else 0.,
                        liq[0]/total if total else 0.,float(liq.max()/total) if total else 0.,
                        volume[lead]/vtotal if lead is not None and vtotal else 0.,
                        float(lead==0),float(lead is not None),float(liq[lead]) if lead is not None else 0.,float(liq[0]),total,
                        sum(float(liq[self.matcher.groups[g]].sum()) for g,l in self.election.leaders.items()
                            if l is not None and l>=self.c.base_tokens)/total if total else 0.,
                        float(liq[self.matcher.groups[self.matcher.token_group[0]]].sum())/total if total else 0.])
        if self.previous_state is not None:self.area+=self.previous_state*(t-self.previous_t)
        self.previous_state=state;self.previous_t=t
        if self.details:
            self.history.append(dict(minute=t,leader=lead,leader_liquidity_share=state[0],original_liquidity_share=state[1],
                                     largest_token_share=state[2],leader_organic_volume_share=state[3],
                                     original_is_leader=state[4],leader_defined=state[5],
                                     actual_reserve=self.book.reserve,required=self.book.required,
                                     donated_burn_surplus=self.book.buffer,total_accessible_liquidity=total,
                                     leader_accessible_liquidity=state[6],original_accessible_liquidity=state[7],
                                     attacker_led_groups_liquidity_share=state[9],original_matching_group_share=state[10],
                                     diverted_cash=self.router.diverted))

    def run(self):
        c=self.c;dt=c.horizon/c.events
        self.launch(0,0,seed=1000.)
        for j in range(c.events):
            t=j*dt
            for i in range(1,c.base_tokens):
                if not self.active[i] and t>=8+(i-1)*4:
                    self.launch(t,i,seed=3000. if i==1 else 100.)
            if t>=1 and not getattr(self,"sniped",False):
                for w in self.snipers:self.buy(t,int(w),0,1000.)
                self.sniped=True
            if self.active[1] and not getattr(self,"bundled",False):
                for w in self.bundlers:self.buy(t,int(w),1,1500.)
                self.bundled=True
            if t>=20 and not getattr(self,"sniper_exit",False):
                for w in self.snipers:self.sell_wallet(t,int(w))
                self.sniper_exit=True
            if t>=65 and not getattr(self,"bundle_exit",False):
                for w in self.bundlers:self.sell_wallet(t,int(w))
                self.bundle_exit=True
            if t>=90 and not getattr(self,"vamp_exit",False):
                self.sell_wallet(t,int(self.creators[1]),.75);self.vamp_exit=True
            self.act(t)
            for w in self.exit_schedule.get(j,[]):self.sell_wallet(t,w,organic=True)
            self.election.refresh(t);lead=self.root_leader()
            copies=np.flatnonzero(self.active)[1:]
            if self.informed[j] or self.badge_draw[j]<self.v.badge:
                target=lead if lead is not None else 0
            elif self.confused[j] and len(copies):
                target=int(copies[min(len(copies)-1,int(self.choice[j]*len(copies)))]);self.was_confused[j]=True
            else:target=0
            self.target[j]=target;self.role[j]="leader" if lead==target else "original_unselected" if target==0 else "copy"
            B=min(self.budgets[j],self.book.cash[j]-2*c.gas)
            front=self.front(t,target,B)
            success=self.buy(t,j,target,B,organic=True,minimum=front[2] if front else 0.)
            self.completed_buys+=success
            if front:self.router.sell(t,int(self.attack[0]),front[0],front[1]);self.election.refresh(t)
            self.snapshot(t)
            self.peak_capital=max(self.peak_capital,c.attacker_capital-float(self.book.cash[self.attack].sum()))
        self.election.refresh(c.horizon);self.snapshot(c.horizon)
        lead=self.root_leader();liq=np.maximum(self.router.accessible(),0.)
        before=dict(leader_final=lead,leader_final_is_original=lead==0,
                    leader_final_is_attacker=lead is not None and lead>=self.c.base_tokens,
                    original_final_liquidity_share=float(liq[0]/liq.sum()) if liq.sum() else 0.,
                    total_accessible_liquidity=float(liq.sum()),donated_burn_surplus=self.book.buffer,
                    locked_tokens=float(self.book.holdings[self.dead].sum()),treasury_tokens=float(self.book.holdings[self.treasury].sum()),
                    leader_switches=self.election.switches)
        if self.v.form=="treasury" and self.v.treasury_exit=="first":
            for i in np.flatnonzero(self.book.holdings[self.treasury]>1e-10):
                self.router.sell(c.horizon,self.treasury,int(i),float(self.book.holdings[self.treasury,i]),protocol=True)
        for w in self.closing:self.sell_wallet(c.horizon,int(w),organic=int(w)<c.events)
        self.book.assert_invariants()
        pnl=self.book.cash-self.initial
        metrics=dict(attacker_profit=float(pnl[self.attack].sum()),vamper_profit=float(pnl[self.creators[1]]),
                     creator_original_profit=float(pnl[self.creators[0]]),retail_profit=float(pnl[self.org].sum()),
                     retail_mean_profit=float(pnl[self.org].mean()),sniper_profit=float(pnl[self.snipers].sum()),
                     bundler_profit=float(pnl[self.bundlers].sum()),front_opportunities_exploited=self.front_count,
                     diversion_paid=float(self.router.diverted),creator_diversion_receipts=self.router.creator_receipts,
                     holder_dividend_receipts=self.router.holder_receipts,
                     original_creator_received_cash=float(self.router.received[self.creators[0]]),
                     attacker_external_diversion_receipts=self.router.external_actor_receipts,
                     confused_buyers=int(self.was_confused.sum()),
                     confused_mean_profit=float(pnl[self.org][self.was_confused].mean()) if self.was_confused.any() else None,
                     protocol_fees=float(self.book.fees),launch_fees=float(self.book.cash[self.fee_wallet]),
                     network_expense=float(self.book.cash[self.network]),initial_external_cash=self.book.initial_external,
                     final_reserve=float(self.book.reserve),final_required=float(self.book.required),
                     minimum_wallet_cash=float(self.book.cash.min()),
                     terminal_private_token_dust=float(self.book.holdings[np.r_[self.org,self.creators,self.snipers,self.bundlers,self.attack]].sum()),
                     cash_conservation_error=abs(float(self.book.cash.sum())+self.book.reserve+self.book.fees-self.book.initial_external),
                     reserve_backing_error=abs(self.book.reserve-self.book.reserve_function()-self.book.buffer),
                     completed_buys=self.completed_buys,rejected_buys=self.rejected,peak_attacker_cash_committed=self.peak_capital,**before)
        if self.capture:
            names=("leader_liquidity_share_time_mean","original_liquidity_share_time_mean","largest_share_time_mean",
                   "leader_organic_volume_share_time_mean","original_leader_time_fraction","leader_defined_time_fraction",
                   "leader_accessible_liquidity_time_mean","original_accessible_liquidity_time_mean","total_accessible_liquidity_time_mean",
                   "attacker_led_groups_liquidity_share_time_mean","original_matching_group_share_time_mean")
            metrics.update(zip(names,(self.area/c.horizon).tolist()))
            time=np.arange(c.events)*dt
            for timing,mask in (("early",time<c.horizon/3),("late",time>=2*c.horizon/3)):
                for role in ("leader","copy","original_unselected"):
                    selected=mask&(self.role==role)
                    metrics[f"{timing}_{role}_mean_pnl"]=float(pnl[self.org][selected].mean()) if selected.any() else None
                    metrics[f"{timing}_{role}_buyers"]=int(selected.sum())
        wallet_rows=[]
        if self.details:
            for j in self.org:
                wallet_rows.append(dict(wallet=int(j),minute=float(j*dt),target=int(self.target[j]),target_role=self.role[j],
                                        confused=bool(self.was_confused[j]),informed=bool(self.informed[j]),
                                        realized_cash_pnl=float(pnl[j]),diversion_paid=float(self.router.paid[j]),
                                        dividends_received=float(self.router.received[j])))
        return metrics,self.history,wallet_rows


def run(variant,config,strategy=Strategy(),capture=True,details=False):
    return Market(variant,config,strategy,capture,details).run()
