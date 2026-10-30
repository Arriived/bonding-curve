"""One original, copied landing pages, fixed narrative demand, one-hour horizon."""
from dataclasses import dataclass
from collections import defaultdict
import random, hashlib, math, json
from ledger import Book, Refused, reserve, MONEY as M, TOKEN as Q

def rng(seed,key):
    return random.Random(int.from_bytes(hashlib.sha256(f'{seed}:{key}'.encode()).digest()[:16],'big'))
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

@dataclass(frozen=True)
class Environment:
    name:str='copies9'
    coins:int=10
    half_life:int=600
    first_copy:int=15
    original_share:float=.25
    reach:float=.6
    acceptance:float=.6
    viral_copy:bool=False
    preclaim:bool=False
    rejection:str='direct'
    sale_rule:str='lot'
    fee_bps:int=40
    opportunities:int=480
    network:int=10000

@dataclass(frozen=True)
class Mechanism:
    name:str='independent'
    rule:str='independent'
    close:int=0

@dataclass(frozen=True)
class Policy:
    target:int=0
    start:int=1
    budget:int=0
    exit:int=900

class AuditBook(Book):
    def invariant(self):
        assert sum(self.cash.values())==self.initial
        assert min(self.cash.values(),default=0)>=0
        sums=[0]*self.n;counts=[0]*self.n
        for (owner,i),quantity in self.hold.items():
            assert quantity>=0
            sums[i]+=quantity
            counts[i]+=int(quantity>0)
        assert sums==self.q and counts==self.holder_count
        for i in range(self.n):assert self.cash.get(f'market:{i}',0)==reserve(self.q[i])+self.buffer[i]
        return True

def make_tape(seed,opportunities=480,half_life=600):
    agents=[]
    for i in range(64):
        r=rng(seed,f'agent:{i}')
        agents.append(dict(loyalty=r.uniform(0,.35),weight=4 if i%11==0 else 1))
    total=sum(a['weight'] for a in agents)
    capital=[32000*M*a['weight']//total for a in agents]
    capital[0]+=32000*M-sum(capital)
    rows=[]
    scale=half_life/math.log(2)
    for j in range(opportunities):
        r=rng(seed,f'visit:{j}')
        t=max(1,min(3599,int(-scale*math.log(1-r.random()*(1-math.exp(-3600/scale))))))
        actor=r.randrange(64)
        budget=int(min(120,math.exp(r.normalvariate(math.log(25),.5)))*(2 if agents[actor]['weight']==4 else 1)*M)
        hold=max(5,min(1200,int(math.exp(r.uniform(math.log(15),math.log(900))))))
        rows.append(dict(id=j,t=t,actor=actor,budget=budget,source=r.random(),copy=r.random(),reach=r.random(),
                         accept=r.random(),fallback=r.random(),hold=hold,sell_fraction=r.uniform(.4,1)))
    rows.sort(key=lambda row:(row['t'],row['id']))
    result=dict(seed=seed,agents=agents,capital=capital,visits=rows)
    result['hash']=digest(result)
    return result

class World:
    def __init__(self,e,m,tape,p=Policy(),trace=False):
        self.e,self.m,self.t,self.p=e,m,tape,p
        self.b=AuditBook(e.coins+1,max(0,e.fee_bps-30),min(30,e.fee_bps),e.network,trace)
        self.live=set();self.launch_time={};self.closed=False;self.lead=None
        self.buys=[];self.offers=[];self.landing=[];self.actual={};self.lots={};self.routes=[]
        self.observations=[];self.minutes=[];self.area=defaultdict(int);self.last_score_time=-1
        self.counter=defaultdict(int);self.peak=0;self.tx_count=0
        for i,cash in enumerate(tape['capital']):self.b.fund(f'u:{i}',cash)
        self.b.fund('creator:0',200*M)
        allocation=1800*M//(e.coins-1)
        for i in range(1,e.coins):self.b.fund(f'creator:{i}',allocation+(1800*M-allocation*(e.coins-1) if i==1 else 0))
        self.b.fund('attacker',5000*M);self.b.fund('sponsor',100*M)
        assert self.b.initial==39100*M
        self.launches={0:0}
        for i in range(1,e.coins):
            when=e.first_copy if i==1 else rng(tape['seed'],f'copy-launch:{i}').randint(e.first_copy,max(e.first_copy,180))
            self.launches[i]=-1 if i==1 and e.preclaim else when

    def accrue(self):
        if self.m.rule!='timecap' or self.closed:return
        end=min(self.b.time,self.m.close)
        if end<=self.last_score_time:return
        for i in self.live:
            q=self.b.q[i];self.area[i]+=q*(q+1000000)*(end-self.last_score_time)
        self.last_score_time=end

    def check(self):
        self.tx_count+=1
        if self.tx_count%32==0:self.b.invariant()

    def buy(self,owner,i,budget):
        self.accrue();tx=self.b.buy(owner,i,min(budget,self.b.cash[owner]),allowed=(i,));self.check()
        return tx
    def sell(self,owner,i,d):
        self.accrue();tx=self.b.sell(owner,i,d);self.check();return tx

    def launch(self,i):
        owner=f'creator:{i}';cost=30000
        if self.b.cash[owner]<cost:return
        self.b.transfer(owner,'network',10000)
        self.b.transfer(owner,f'account_deposit:{i}',20000)
        self.live.add(i);self.launch_time[i]=self.b.time
        if self.m.rule=='original' and self.lead is None:
            # Observable first registration, never evaluator-only true originality.
            self.lead=i;self.closed=True
        self.b.log('launch',token=i,creator=owner,platform_fee=0,network=10000,account_deposit=20000)

    def choose(self,row):
        if 0 not in self.live:return min(self.live) if self.live else None
        copies=sorted(self.live-{0})
        if not copies or row['source']<self.e.original_share:return 0
        weights=[10 if self.e.viral_copy and i==1 else 1 for i in copies]
        draw=row['copy']*sum(weights)
        for i,w in zip(copies,weights):
            draw-=w
            if draw<0:return i
        return copies[-1]

    def visit(self,row):
        desired=self.choose(row)
        if desired is None:return
        owner=f'u:{row["actor"]}';budget=min(row['budget'],self.b.cash[owner])
        self.offers.append((self.b.time,row['budget'],budget))
        self.landing.append((self.b.time,desired,row['budget']))
        if budget<=self.b.gas:return
        target=desired;routed=False
        if self.m.rule!='independent' and self.closed and self.lead is not None and desired!=self.lead and row['reach']<self.e.reach:
            self.counter['reachable']+=budget
            acceptance=self.e.acceptance*(1-.3*self.t['agents'][row['actor']]['loyalty'])
            if row['accept']<acceptance:
                target=self.lead;routed=True;self.counter['authorized']+=budget
            elif self.e.rejection=='leave':return
            elif self.e.rejection=='outside':target=self.e.coins
        try:tx=self.buy(owner,target,budget)
        except Refused:return
        self.actual[row['id']]=target
        self.lots[row['id']]=[owner,target,tx.quantity]
        gross=-tx.cash_delta
        self.buys.append((self.b.time,target,tx.principal,gross,desired))
        self.counter['executed']+=gross
        if routed:
            self.counter['routed']+=gross;self.routes.append((self.b.time,desired,target,gross))
            if desired!=0:self.counter['redirected_copy']+=gross
            if desired==0 and target!=0:self.counter['redirected_original']+=gross
        self.b.log('buyer_fill',id=row['id'],intended=desired,received=target,consented=routed,gross=gross)

    def exit_visit(self,row):
        lot=self.lots.get(row['id'])
        if lot is None:return
        owner,target,remaining=lot
        held=self.b.hold.get((owner,target),0)
        d=int((remaining if self.e.sale_rule=='lot' else held)*row['sell_fraction'])
        if d<=0:return
        try:self.sell(owner,target,d)
        except Refused:return
        if self.e.sale_rule=='lot':lot[2]-=d

    def select(self):
        self.accrue();self.closed=True
        scores={}
        for i in self.live:
            if reserve(self.b.q[i])<10*M:continue
            q=self.b.q[i]
            scores[i]=self.area[i] if self.m.rule=='timecap' else q*(q+1000000)
        if scores:
            highest=max(scores.values());winners=[i for i,v in scores.items() if v==highest]
            if len(winners)==1:self.lead=winners[0]
        self.b.log('selection',rule=self.m.rule,lead=self.lead,scores=scores)

    def attack(self):
        if not self.p.budget or self.p.target not in self.live:return
        try:self.buy('attacker',self.p.target,self.p.budget*M)
        except Refused:return
        self.peak=max(self.peak,5000*M-self.b.cash['attacker'])
    def actor_exit(self):
        for i in range(self.e.coins+1):
            d=self.b.hold.get(('attacker',i),0)
            if d:
                try:self.sell('attacker',i,d)
                except Refused:pass

    def flow(self,t,width=300):
        quote=[0]*(self.e.coins+1);counts=[0]*(self.e.coins+1)
        for when,i,principal,gross,desired in self.buys:
            if t-width<when<=t:quote[i]+=gross;counts[i]+=1
        total=sum(quote);narrative=sum(quote[:-1]);lead=self.lead if self.m.rule!='independent' else None
        top=max(quote[:-1],default=0)
        shares=[v/narrative for v in quote[:-1] if v] if narrative else []
        latent=sum(v for when,v,funded in self.offers if t-width<when<=t)
        offered=sum(funded for when,v,funded in self.offers if t-width<when<=t)
        return dict(seed=self.t['seed'],environment=self.e.name,mechanism=self.m.name,time=t,lead=lead,
            top_share=top/narrative if narrative else None,original_share=quote[0]/narrative if narrative else None,
            lead_share=quote[lead]/narrative if narrative and lead is not None else None,
            top_to_latent=top/latent if latent else None,fill_to_latent=total/latent if latent else None,
            fill_to_funded=total/offered if offered else None,
            effective_markets=1/sum(s*s for s in shares) if shares else None,
            window_gross=total/M,window_orders=sum(counts),original_gross=quote[0]/M,
            lead_gross=quote[lead]/M if lead is not None else None)

    def depth(self,i,bp=500):
        q=self.b.q[i];private=q-self.b.hold.get(('attacker',i),0)
        d=min(private,(q+1000000)*bp//10000)
        return (reserve(q)-reserve(q-d))/M if d else 0.

    def snapshot(self,t,label):
        self.b.invariant()
        if self.e.sale_rule=='lot' and label!='exit':
            owned=defaultdict(int)
            for o,i,d in self.lots.values():owned[o,i]+=d
            actual={(o,i):d for (o,i),d in self.b.hold.items() if o.startswith('u:') and d}
            assert {k:v for k,v in owned.items() if v}==actual
        row=self.flow(t)
        window_quote=[0]*self.e.coins
        for when,i,principal,gross,desired in self.buys:
            if t-300<when<=t and i<self.e.coins:window_quote[i]+=gross/M
        depths=[self.depth(i) for i in range(self.e.coins)]
        backing=[reserve(self.b.q[i])/M for i in range(self.e.coins)]
        row.update(label=label,original_depth=depths[0],lead_depth=depths[self.lead] if self.lead is not None else None,
            largest_depth=max(depths),cohort_backing=sum(backing),original_backing=backing[0],
            leader_backing=backing[self.lead] if self.lead is not None else None,
            executed=self.counter['executed']/M,routed=self.counter['routed']/M,reachable=self.counter['reachable']/M,
            authorized=self.counter['authorized']/M,redirected_copy=self.counter['redirected_copy']/M,
            redirected_original=self.counter['redirected_original']/M,
            total_latent=sum(v for when,v,f in self.offers)/M,live=len(self.live),
            original_creator_cash=(self.b.cash['creator:0']-200*M)/M,
            copy_creator_cash=(sum(self.b.cash[f'creator:{i}'] for i in range(1,self.e.coins))-1800*M)/M,
            trader_cash=sum(self.b.cash[f'u:{i}']-c for i,c in enumerate(self.t['capital']))/M,
            actor_profit=(self.b.cash['attacker']-5000*M)/M,actor_peak=self.peak/M,
            actor_residual=sum(self.b.hold.get(('attacker',i),0) for i in range(self.e.coins+1))/Q,
            actor_led=int(self.lead==self.p.target and self.p.budget>0),initial_world=self.b.initial/M,
            depth_vector=json.dumps(depths,separators=(',',':')),backing_vector=json.dumps(backing,separators=(',',':')),
            flow_vector=json.dumps(window_quote,separators=(',',':')),
            tape_hash=self.t['hash'])
        self.observations.append(row)

    def run(self):
        events=[]
        def add(t,priority,kind,data=None):events.append((t,priority,len(events),kind,data))
        for i,t in self.launches.items():add(t,-3,'launch',i)
        for row in self.t['visits']:
            add(row['t'],10,'visit',row);add(row['t']+row['hold'],11,'sell',row)
        if self.m.rule in ('cap','timecap'):add(self.m.close,0,'select')
        if self.p.budget:
            start=max(self.p.start,self.launches[self.p.target]+1)
            add(start,1,'attack');add(max(start+1,self.p.exit),2,'actor_exit')
        for t in range(60,3601,60):add(t,20,'minute')
        for t in (300,900,1800,3600):add(t,30,'snapshot')
        for t,priority,event_id,kind,data in sorted(events):
            if t>3600:continue
            self.b.time=t
            if kind=='launch':self.launch(data)
            elif kind=='visit':self.visit(data)
            elif kind=='sell':self.exit_visit(data)
            elif kind=='select':self.select()
            elif kind=='attack':self.attack()
            elif kind=='actor_exit':self.actor_exit()
            elif kind=='minute':self.minutes.append(self.flow(t))
            elif kind=='snapshot':self.snapshot(t,str(t//60)+'m')
        self.b.time=3601;self.actor_exit()
        order=[f'u:{i}' for i in range(64)];rng(self.t['seed'],'terminal-order').shuffle(order)
        for owner in order:
            for i in range(self.e.coins+1):
                d=self.b.hold.get((owner,i),0)
                if d:
                    try:self.sell(owner,i,d)
                    except Refused:pass
        self.snapshot(3601,'exit')
        return self.observations,self.minutes
