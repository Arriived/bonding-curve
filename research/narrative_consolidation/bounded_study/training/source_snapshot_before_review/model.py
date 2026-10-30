"""Matched synthetic opportunities, observable elections and funded A-D worlds."""
from dataclasses import dataclass,asdict
from collections import defaultdict
import hashlib,json,math,random
from .ledger import Book,Auction,Refused,reserve,MONEY as M,TOKEN as Q


def stream(seed,name):
    return random.Random(int.from_bytes(hashlib.sha256(f'{seed}:{name}'.encode()).digest()[:16],'big'))


def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'))
def hash_obj(obj):return hashlib.sha256(canonical(obj).encode()).hexdigest()


@dataclass(frozen=True)
class Config:
    name:str='A'
    arch:str='A'
    rule:str='cap'
    acceptance:float=.6
    reach:float=.6
    reject_preferred:float=.5
    reject_outside:float=.25
    migration:float=.25
    broad:float=.6
    lock_willingness:float=.7
    post_choice:float=.65
    feedback:float=0.
    collapse:bool=False
    grouping:bool=False
    refusal:float=0.
    no_winner:bool=False
    force_tie:bool=False
    withheld:bool=False
    delay:int=0
    random_close:bool=False
    support_mode:str='protocol_lock'
    overlay:bool=False
    fp:int=10
    fc:int=30
    gas:int=10_000
    opportunities:int=480
    window:int=1800
    horizon:int=604800
    unlock:int=259200
    price_elasticity:float=.35


@dataclass(frozen=True)
class Policy:
    family:str='idle'
    budget:int=0
    exit_delay:int=0
    aliases:int=1
    rounds:int=1


def make_tape(seed,count=480,window=1800,horizon=604800):
    rng=stream(seed,'qualities');quality=[rng.uniform(.6,1.4) for _ in range(10)]
    rng=stream(seed,'agents')
    kinds=('retail','narrative','loyal','momentum','whale','creator_follower','bundler','sniper','arbitrageur','migrator','loyal')
    agents=[]
    for i in range(64):
        kind=kinds[i%len(kinds)]
        agents.append(dict(kind=kind,loyalty=.9 if kind=='loyal' else .1 if kind=='narrative' else rng.uniform(.15,.6),
                           home=rng.randrange(10),risk=rng.uniform(.7,1.3)))
    weights=[5 if a['kind']=='whale' else 1 for a in agents];total=sum(weights)
    capital=[32000*M*w//total for w in weights];capital[0]+=32000*M-sum(capital)
    rows=[];pre=count//4
    for j in range(count):
        rng=stream(seed,f'opportunity:{j}')
        t=rng.randint(1,window-1) if j<pre else window+int(math.expm1(rng.random()*math.log1p(horizon)))
        # Extra late opportunities exist on the same tape, not only for winners.
        if j>=count-24:t=window+int(horizon*(.85+.15*rng.random()))
        actor=rng.randrange(64);kind=agents[actor]['kind']
        budget=int(min(180,math.exp(rng.normalvariate(math.log(35),.65)))*(3 if kind=='whale' else 1)*M)
        pref=max(range(10),key=lambda k:math.log(quality[k])+rng.gammavariate(1, .4)+(1.5 if k==agents[actor]['home'] else 0))
        hold=int(math.exp(rng.uniform(math.log(60),math.log(900000))))
        rows.append(dict(id=j,t=t,actor=actor,budget=budget,pref=pref,attention=rng.random(),price_draw=rng.random(),
                         reach=rng.random(),accept=rng.random(),fallback=rng.random(),broad=rng.random(),
                         lock=rng.random(),cancel=rng.random(),hold=hold,exit_fraction=rng.uniform(.3,1),
                         alternative=rng.randrange(10)))
    future=[0]*10
    for row in rows:
        if row['t']>=window:future[row['pref']]+=row['budget']
    tape=dict(seed=seed,quality=quality,agents=agents,capital=capital,opportunities=rows,
              future_benchmark=max(range(10),key=lambda i:future[i]),future_offered=future)
    tape['_sha256']=hash_obj(tape)
    return tape


def elect(book,rule,members,time,receipts=(),overlay=(),force_tie=False,qualified=10*M):
    """Only pre-close public balances/receipts. Unknown/inapplicable inputs N/A."""
    scores={}
    if rule in ('commit','timecommit'):
        records=list(receipts)+list(overlay)
        for i in members:
            rows=[r for r in records if r.preferred==i and r.state=='live']
            scores[i]=sum(r.amount*(time-r.time if rule=='timecommit' else 1) for r in rows)
        threshold=qualified*(time if rule=='timecommit' else 1)
    else:
        for i in members:
            q=book.q[i]
            if rule=='cap':scores[i]=q*(q+1_000_000)  # common positive scale omitted
            elif rule=='holders':
                holdings=[d for (o,j),d in book.hold.items() if j==i and d>=Q and not o.startswith('support')]
                scores[i]=len(holdings)
            elif rule=='concentration':
                h=[d for (o,j),d in book.hold.items() if j==i and d>0]
                scores[i]=(q*q-sum(d*d for d in h))*1_000_000//max(1,q*q)
            else:return None,{},'N/A'
        threshold=0
    if not scores:return None,scores,'no_qualified'
    if rule in ('cap','holders','concentration'):
        scores={i:v for i,v in scores.items() if reserve(book.q[i])>=qualified}
    eligible={i:s for i,s in scores.items() if s>threshold}
    if not eligible:return None,scores,'no_qualified'
    top=max(eligible.values());winners=[i for i,s in eligible.items() if s==top]
    if force_tie or len(winners)!=1:return None,scores,'tie'
    return winners[0],scores,'finalized'


class World:
    def __init__(self,c,tape,policy=Policy(),capture=False):
        self.c=c;self.t=tape;self.p=policy;self.b=Book(11,c.fp,c.fc,c.gas,capture)
        self.close=c.window+(stream(tape['seed'],'close').randint(-180,180) if c.random_close else 0)
        self.final=self.close+c.delay;self.end=self.final+c.horizon
        self.winner=None;self.closed=False;self.finalized=False;self.reason='pending';self.rankings=[]
        self.auction=Auction(self.b,self.close,int(.9*c.window),self.close+7200,50_000*Q)
        self.overlay=Auction(self.b,self.close,int(.9*c.window),self.close+7200,50_000*Q)
        self.count=defaultdict(int);self.activity=[];self.snapshots=[];self.actual={};self.accounting=[]
        self.slippage=defaultdict(list);self.capital_seconds=0;self.last_time=0
        self.support_owned=[];self.fee_sources=defaultdict(int);self.actor=['attacker']+[f'alias:{i}' for i in range(1,policy.aliases)]
        self.actor_initial=5000*M;self.peak=0;self.capture_cost=0;self.was_captured=False
        self.initial_trader={f'u:{i}':v for i,v in enumerate(tape['capital'])}
        for o,v in self.initial_trader.items():self.b.fund(o,v)
        for i in range(10):self.b.fund(f'creator:{i}',200*M)
        self.b.fund('attacker',self.actor_initial);self.b.fund('sponsor',100*M)
        self.members=[i for i in range(10) if stream(tape['seed'],f'creator:{i}').random()>=c.refusal]
        self.creator_initial={f'creator:{i}':200*M for i in range(10)}
        self.single=c.arch in ('single_spot','single_batch')
        self.batch=c.arch in ('D','single_batch','independent_batch')
        for i in range(10):
            self.b.transfer(f'creator:{i}','platform_launch' if i in self.members else 'outside_launch',M)
            self.b.transfer(f'creator:{i}','promotion',5*M)
            if self.batch:
                allowed=(i,) if c.arch=='independent_batch' else tuple(range(10))
                self.auction.commit(f'creator:{i}',i,allowed,10*M,0,self.auction.deadline)
            elif not self.single or i==0:self.buy(f'creator:{i}',i,10*M)
        if c.overlay:
            for i in range(64):self.overlay.commit(f'u:{i}',tape['agents'][i]['home'],tuple(range(10)),5*M,0,self.overlay.deadline)

    def risk(self):
        live=sum(r.amount for r in self.auction.receipts if r.owner in self.actor and r.state=='live')
        self.peak=max(self.peak,self.actor_initial-sum(self.b.cash[o] for o in self.actor))
        self.count['actor_live_escrow']=live

    def harvest(self,tx):
        if self.c.arch!='B' or tx.token not in self.members or self.closed and self.winner is None or self.b.time>=self.final+self.c.unlock:return
        if self.c.support_mode.startswith('protocol'):
            amount=tx.protocol_fee//2
            self.b.transfer('protocol','support_cash',amount);self.fee_sources['protocol']+=amount
        else:
            amount=tx.creator_fee
            self.b.transfer(f'creator:{tx.token}','creator_pool',amount)
            self.fee_sources[f'creator:{tx.token}']+=amount

    def buy(self,owner,token,budget,minimum=0):
        tx=self.b.buy(owner,token,min(budget,self.b.cash[owner]),allowed=(token,),minimum=minimum)
        self.harvest(tx);return tx

    def sell(self,owner,token,d):
        tx=self.b.sell(owner,token,d);self.harvest(tx);return tx

    def preferred(self,row):
        agent=self.t['agents'][row['actor']]
        # Utility uses current observable price/momentum/participation, never future demand.
        scores=[]
        for i in range(10):
            p=.01+.0001*self.b.q[i]/Q
            score=math.log(self.t['quality'][i])+(2*agent['loyalty'] if i==row['pref'] else 0)
            if agent['kind']=='momentum':score+=.3*math.log(p/.01)
            score+=.04*math.log1p(self.b.holder_count[i])
            scores.append(score)
        return max(range(10),key=lambda i:(scores[i],-i))

    def outside(self,owner,budget,token=10):
        try:tx=self.buy(owner,token,budget)
        except Refused:return
        self.count['outside_spent']-=tx.cash_delta
        return token

    def record_organic(self,owner,tx):
        self.activity.append((self.b.time,owner,tx.principal,tx.side))
        self.count['organic_buy' if tx.side=='buy' else 'organic_sell']+=tx.principal
        oldq=self.b.q[tx.token]+(-tx.quantity if tx.side=='buy' else tx.quantity)
        price=.01+.0001*oldq/Q
        ratio=tx.principal*Q/(M*tx.quantity*price)
        net=abs(tx.cash_delta)*Q/(M*tx.quantity*price)
        self.slippage[tx.side].append((ratio-1 if tx.side=='buy' else 1-ratio)*10000)
        self.slippage[tx.side+'_allin'].append((net-1 if tx.side=='buy' else 1-net)*10000)

    def opportunity(self,row):
        c=self.c;owner=f"u:{row['actor']}";agent=self.t['agents'][row['actor']]
        if row['t']<self.close:
            attention=1.
        else:attention=.8*(1+(row['t']-self.close)/3600)**(-.12)
        if self.finalized and self.winner is not None and c.arch in ('B','C','D'):attention*=max(0,1+c.feedback)
        if row['attention']>=min(1,attention):return
        desired=self.preferred(row);budget=min(row['budget'],self.b.cash[owner])
        if budget<=c.gas:return
        self.count['offered']+=budget
        routed=False
        if desired not in self.members:
            self.actual[row['id']]=self.outside(owner,budget,desired);return
        target=desired
        if self.batch and not self.finalized:
            if self.closed or row['lock']>=c.lock_willingness:
                if row['fallback']<c.reject_outside:self.actual[row['id']]=self.outside(owner,budget)
                return
            allowed=tuple(self.members) if row['broad']<c.broad*(.35 if c.grouping else 1) else (desired,)
            idx=self.auction.commit(owner,desired,allowed,budget,self.b.time,self.auction.deadline)
            self.count['committed']+=budget;self.actual[row['id']]=('receipt',idx)
            # Explicit early cancellations, before the lock boundary, with unchanged future budget.
            if row['cancel']<.03 and self.b.time<self.auction.cancel_until:
                self.auction.cancel(idx,owner,self.b.time);self.count['cancelled']+=budget
            return
        if self.single or self.batch and c.arch!='independent_batch':
            target=0 if self.single else self.winner
            if target is None:return
            propensity=c.post_choice*(1-.6*agent['loyalty'])
            if desired!=target and row['accept']>=propensity:
                if row['fallback']<c.reject_outside:self.actual[row['id']]=self.outside(owner,budget)
                return
        elif c.arch=='C' and self.finalized and self.winner is not None and desired!=self.winner and row['reach']<c.reach:
            self.count['reachable']+=budget
            propensity=c.acceptance*(1-.6*agent['loyalty'])*( .35 if c.grouping else 1.)
            # Expected winner price is a behavioral cost, while actual execution remains integer.
            p=.01+.0001*self.b.q[self.winner]/Q
            propensity*=min(1,(max(.25,p)/.25)**(-.15))
            if row['accept']<propensity:
                target=self.winner;self.count['authorized']+=budget;self.count['accepted_orders']+=1
                routed=True
            else:
                self.count['rejected_orders']+=1
                if row['fallback']<c.reject_preferred:target=desired
                elif row['fallback']<c.reject_preferred+c.reject_outside:
                    self.actual[row['id']]=self.outside(owner,budget);return
                else:return
        p=.01+.0001*self.b.q[target]/Q
        if self.finalized and c.collapse and target==self.winner and row['price_draw']<.8:return
        elasticity=min(1,(max(.25,p)/.25)**(-c.price_elasticity))
        if row['price_draw']>=elasticity:return
        try:tx=self.buy(owner,target,budget)
        except Refused:return
        self.count['executed']-=tx.cash_delta;self.actual[row['id']]=target
        if routed:self.count['routed_executed']-=tx.cash_delta
        self.record_organic(owner,tx)

    def close_election(self):
        self.closed=True;c=self.c
        if c.no_winner:self.reason='no_qualified';return
        if self.single:self.winner=0;self.reason='single_candidate';return
        if self.batch and c.rule not in ('commit','timecommit'):
            self.reason='N/A_spot_metric_before_issuance';return
        receipts=self.auction.receipts if self.batch else ()
        overlay=self.overlay.receipts if c.overlay else ()
        self.winner,scores,self.reason=elect(self.b,c.rule,self.members,self.close,receipts,overlay,c.force_tie)
        self.rankings.append(dict(time=self.close,scores=scores,winner=self.winner,reason=self.reason))
        self.b.log('election',winner=self.winner,reason=self.reason,scores=scores)

    def finalize(self):
        self.finalized=True;c=self.c
        if c.withheld or self.final>self.auction.deadline:self.winner=None;self.reason='withheld_or_timeout'
        if c.overlay:self.overlay.abort('overlay_released_after_scoring')
        if self.batch:
            if self.winner is None and c.arch!='independent_batch':self.auction.abort(self.reason)
            else:
                outputs=self.auction.settle(self.winner,self.final,independent=c.arch=='independent_batch')
                if not outputs and c.arch!='independent_batch':self.winner=None;self.reason='insufficient_compatible_raise'
                for token,qty,g,pf,cf in outputs:
                    from .ledger import Fill
                    self.harvest(Fill('escrow',token,'batch',qty,g,pf,cf,0,-g-pf-cf))
                for r in self.auction.receipts:
                    if r.owner.startswith('u:') and r.spent:
                        self.count['executed']+=r.spent
                        self.activity.append((self.final,r.owner,r.spent,'buy'));self.count['organic_buy']+=r.spent
        if self.winner is None and c.arch=='B':
            for owner,amount in self.fee_sources.items():
                source='support_cash' if c.support_mode.startswith('protocol') else 'creator_pool'
                self.b.transfer(source,owner,amount)
            self.fee_sources.clear()
        self.was_captured=self.winner==9 and self.p.family!='idle'

    def voluntary_migration(self):
        if self.c.arch!='C' or self.winner is None:return
        eligible=0;eligible_gross=0
        for i in self.members:
            if i==self.winner:continue
            qty=sum(v for (o,j),v in self.b.hold.items() if j==i and o.startswith('u:'))
            eligible+=qty
            if qty:eligible_gross+=reserve(self.b.q[i])-reserve(self.b.q[i]-qty)
        self.count['migration_eligible_claims']=eligible;self.count['migration_eligible_gross']=eligible_gross
        for j,agent in enumerate(self.t['agents']):
            if stream(self.t['seed'],f'migrate:{j}').random()>=self.c.migration*(1-agent['loyalty']):continue
            for i in self.members:
                d=self.b.hold.get((f'u:{j}',i),0)
                if i==self.winner or not d:continue
                try:first,second=self.b.migrate(f'u:{j}',i,self.winner,d,allowed=(self.winner,))
                except Refused:self.count['migration_failed']+=1;continue
                self.harvest(first);self.harvest(second)
                self.count['migration_claims']+=d;self.count['migration_proceeds']+=first.cash_delta
                self.count['migration_winner_principal']+=second.principal

    def epoch(self):
        if self.c.arch!='B' or self.winner is None:return
        if not self.c.support_mode.startswith('protocol'):
            pool=self.b.cash['creator_pool'];buy=pool*60//100;creator=pool*30//100
            self.b.transfer('creator_pool','support_cash',buy)
            self.b.transfer('creator_pool',f'creator:{self.winner}',creator)
            self.b.transfer('creator_pool','protocol',pool-buy-creator)
        front=None
        if self.p.family=='support_front':
            try:front=self.buy('attacker',self.winner,min(self.p.budget,self.b.cash['attacker']))
            except Refused:pass
            self.risk()
        budget=self.b.cash['support_cash']
        try:tx=self.buy('support_cash',self.winner,budget)
        except Refused:tx=None
        if tx:
            self.count['support_principal']+=tx.principal
            if self.c.support_mode.endswith('destroy'):self.b.destroy('support_cash',self.winner,tx.quantity)
        if front:
            try:self.sell('attacker',self.winner,front.quantity)
            except Refused:pass

    def unlock(self):
        if self.c.arch!='B':return
        for i in range(10):
            d=self.b.hold.get(('support_cash',i),0)
            if d:
                try:tx=self.sell('support_cash',i,d);self.count['support_unlock_proceeds']+=tx.cash_delta
                except Refused:pass

    def exit_opportunity(self,row):
        if self.c.arch=='locked_spot' and self.b.time<self.final:return
        owner=f"u:{row['actor']}";target=self.actual.get(row['id'])
        if isinstance(target,tuple):
            r=self.auction.receipts[target[1]]
            if r.state!='settled' or r.tokens==0:return
            target=r.preferred if self.c.arch=='independent_batch' else 0 if self.single else self.winner
        if target is None:return
        held=self.b.hold.get((owner,target),0)
        d=int(held*row['exit_fraction'])
        if d<=0:return
        try:tx=self.sell(owner,target,d)
        except Refused:return
        self.record_organic(owner,tx)

    def act(self):
        if self.p.family in ('idle','support_front'):return
        target=0 if self.single else 9;budget=min(self.p.budget,self.b.cash['attacker'])
        if self.batch:
            if not self.closed:
                self.auction.commit('attacker',target,(target,),budget,self.b.time,self.auction.deadline)
                self.risk()
            return
        share=budget//self.p.aliases
        for owner in self.actor:
            if owner!='attacker':self.b.transfer('attacker',owner,share)
            for _ in range(self.p.rounds if self.p.family=='wash' else 1):
                try:tx=self.buy(owner,target,min(share,self.b.cash[owner]))
                except Refused:break
                self.risk()
                if self.p.family=='wash':
                    try:self.sell(owner,target,tx.quantity)
                    except Refused:break
        self.risk()

    def exit_actor(self):
        for owner in self.actor:
            for i in range(11):
                d=self.b.hold.get((owner,i),0)
                if not d:continue
                try:self.sell(owner,i,d)
                except Refused:pass
        self.risk()

    def snapshot(self,label):
        b=self.b;w=self.winner;c=self.c
        locked=('support_cash',) if b.time<self.final+c.unlock else ()
        row=dict(seed=self.t['seed'],name=c.name,label=label,time=b.time,winner=w,reason=self.reason,
                 initial_world=b.initial/M,cohort_reserve=sum(reserve(b.q[i]) for i in self.members)/M,
                 winner_reserve=reserve(b.q[w])/M if w is not None else 0,
                 largest_reserve=max((reserve(b.q[i]) for i in self.members),default=0)/M,
                 winner_price=(.01+.0001*b.q[w]/Q) if w is not None else None,
                 winner_cap=(.01+.0001*b.q[w]/Q)*b.q[w]/Q if w is not None else 0,
                 benchmark_reserve=reserve(b.q[self.t['future_benchmark']])/M,
                 outside_reserve=sum(reserve(b.q[i]) for i in range(11) if i not in self.members)/M,
                 protocol_cash=b.cash['protocol']/M,creator_cash=sum(b.cash[f'creator:{i}'] for i in range(10))/M,
                 protocol_fees_accrued=b.protocol_accrued/M,creator_fees_accrued=b.creator_accrued/M,
                 platform_launch_cash=b.cash['platform_launch']/M,network_cash=b.cash['network']/M,
                 creator_participation=len(self.members)/10,escrow=b.cash['escrow']/M,
                 support_cash=(b.cash['support_cash']+b.cash['creator_pool'])/M,
                 support_claims=sum(b.hold.get(('support_cash',i),0) for i in range(10))/Q,
                 inaccessible_buffer=sum(b.buffer)/M,creator_pnl=(sum(b.cash[f'creator:{i}'] for i in range(10))-2000*M)/M,
                 trader_cash_change=sum(b.cash[o]-v for o,v in self.initial_trader.items())/M,
                 trader_residual_claims=sum(v for (o,i),v in b.hold.items() if o.startswith('u:'))/Q,
                 attacker_cash_pnl=(sum(b.cash[o] for o in self.actor)-self.actor_initial)/M,
                 attacker_peak=self.peak/M,attacker_fees=sum(b.fees_paid[o] for o in self.actor)/M,
                 attacker_acquisition=sum(b.principal_bought[o] for o in self.actor)/M,
                 attacker_capital_days=self.capital_seconds/(M*86400),
                 attacker_opportunity_cost_10pct=self.capital_seconds*.1/(M*365*86400),
                 attacker_residual=sum(b.hold.get((o,i),0) for o in self.actor for i in range(11))/Q,
                 attacker_unrealized_mark=sum(b.hold.get((o,i),0)/Q*(.01+.0001*b.q[i]/Q)-b.basis.get((o,i),0)/M for o in self.actor for i in range(11)),
                 captured=int(self.was_captured),correct_future_choice=int(w==self.t['future_benchmark']),
                 tape_hash=self.t['_sha256'])
        for bp in (100,500,1000):
            row[f'winner_depth_{bp}']=b.depth(w,bp,locked)/M if w is not None else 0
            row[f'cohort_depth_{bp}']=sum(b.depth(i,bp,locked) for i in self.members)/M
        window=3600 if label in ('plus_1h','creation_1h') else 21600 if '24h' in label else 86400
        recent=[r for r in self.activity if b.time-window<r[0]<=b.time]
        row['organic_active']=len({r[1] for r in recent});row['organic_events']=len(recent)
        row['organic_recent_principal']=sum(r[2] for r in recent)/M
        for key in ('offered','reachable','authorized','executed','outside_spent','committed','cancelled',
                    'migration_proceeds','migration_winner_principal','migration_eligible_gross',
                    'support_principal','support_unlock_proceeds','organic_buy','organic_sell','routed_executed'):
            row[key]=self.count[key]/M
        row['accepted_orders']=self.count['accepted_orders'];row['rejected_orders']=self.count['rejected_orders']
        row['abandoned_unexecuted']=max(0,row['offered']-row['executed']-row['outside_spent'])
        row['unsettled_commitments']=sum(r.amount for r in self.auction.receipts if r.state=='live')/M
        row['refunds']=sum(r.refunded for r in self.auction.receipts)/M
        row['realized_acceptance']=row['authorized']/row['reachable'] if row['reachable'] else None
        row['migration_claim_fraction']=self.count['migration_claims']/self.count['migration_eligible_claims'] if self.count['migration_eligible_claims'] else None
        row['organic_realized_pnl']=sum(b.realized[o] for o in self.initial_trader)/M
        pnls=sorted((b.cash[o]-v)/M for o,v in self.initial_trader.items())
        row['trader_cash_pnl_p05']=pnls[3];row['trader_cash_pnl_median']=(pnls[31]+pnls[32])/2
        row['trader_cash_pnl_p95']=pnls[60];row['trader_cash_pnl_min']=pnls[0]
        for side in ('buy','sell','buy_allin','sell_allin'):
            row[side+'_slippage_bps']=sum(self.slippage[side])/len(self.slippage[side]) if self.slippage[side] else None
        self.snapshots.append(row);b.invariant();self.auction.invariant()

    def run(self):
        events=[]
        def add(t,priority,kind,data=None):events.append((t,priority,len(events),kind,data))
        for row in self.t['opportunities']:
            add(row['t'],10,'opportunity',row)
            add(row['t']+row['hold'],11,'exit',row)
        add(self.close,0,'close');add(self.final,1,'final')
        add(self.final+60,2,'migration')
        add(max(1,int(.85*self.close)),-1,'attack')
        add(self.final+self.p.exit_delay,3,'attack_exit')
        for offset in (0,3600,21600,86400,172800):add(self.final+offset,4,'epoch')
        add(self.final+self.c.unlock,4,'unlock')
        checks={'plus_1h':self.final+3600,'plus_24h':self.final+86400,'plus_7d':self.end,
                'creation_1h':3600,'creation_24h':86400,'creation_7d':604800,
                'before_unlock':self.final+self.c.unlock-1,'after_unlock':self.final+self.c.unlock+1}
        for label,t in checks.items():add(t,30,'snapshot',label)
        for t,_,_,kind,data in sorted(events):
            if t>self.end:continue
            deployed=max(0,self.actor_initial-sum(self.b.cash[o] for o in self.actor))
            self.capital_seconds+=deployed*(t-self.last_time);self.last_time=t
            self.b.time=t
            if kind=='opportunity':self.opportunity(data)
            elif kind=='exit':self.exit_opportunity(data)
            elif kind=='close':self.close_election()
            elif kind=='final':self.finalize()
            elif kind=='migration':self.voluntary_migration()
            elif kind=='epoch':self.epoch()
            elif kind=='unlock':self.unlock()
            elif kind=='attack':self.act()
            elif kind=='attack_exit':self.exit_actor()
            elif kind=='snapshot':self.snapshot(data)
        # Feasible terminal exits are separate from observed 7-day participation.
        self.b.time=self.end+1;self.exit_actor()
        order=list(self.initial_trader)+list(self.creator_initial)
        stream(self.t['seed'],'terminal_order').shuffle(order)
        for owner in order:
            for i in range(11):
                d=self.b.hold.get((owner,i),0)
                if d:
                    try:self.sell(owner,i,d)
                    except Refused:pass
        self.snapshot('feasible_exit')
        return self.snapshots,self.b.trace,self.rankings


def run(c,tape,policy=Policy(),capture=False):return World(c,tape,policy,capture).run()
