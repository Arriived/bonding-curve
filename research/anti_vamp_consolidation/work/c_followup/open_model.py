"""Open-entry C stress model. Synthetic behavior; original repository untouched."""
from dataclasses import dataclass, asdict
from collections import defaultdict
import math, hashlib, json
from fractions import Fraction
from upstream.ledger import Book, Refused, reserve, MONEY as M, TOKEN as Q
from upstream.model import make_tape, stream, hash_obj

@dataclass(frozen=True)
class Setting:
    name: str = 'base'
    spam: int = 0
    late_spam: bool = False
    reach: float = .6
    acceptance: float = .6
    outside_creators: float = 0.
    feed_fraction: float = .5
    reject_preferred: float = .5
    reject_outside: float = .25
    launch_fee: int = 0
    network_launch: int = 10_000
    account_deposit: int = 20_000
    sponsor_launch: bool = False
    rule: str = 'cap'
    min_age: int = 0
    route_cap: float = 0.
    route_hours: int = 168
    premium_limit: float = 0.
    fp: int = 10
    fc: int = 30
    router_bps: int = 0

@dataclass(frozen=True)
class Strategy:
    budget: int = 0
    start: float = .85
    exit_hours: int = 1
    aliases: int = 1

def tape_for(seed, setting):
    t = make_tape(seed)
    t['open_launches'] = []
    for i in range(10 + setting.spam):
        rng = stream(seed, f'open-launch:{i}')
        native = i >= 10 or rng.random() >= setting.outside_creators
        when = 0 if i < 10 else rng.randint(1, 900)
        if i >= 10 and setting.late_spam: when = 1800 + rng.randint(1, 3600)
        t['open_launches'].append(dict(token=i, time=when, native=native))
    for row in t['opportunities']:
        rng = stream(seed, f'open-discovery:{row["id"]}')
        row['feed_draw'], row['feed_pick'] = rng.random(), rng.random()
    t['_sha256'] = hash_obj({k:v for k,v in t.items() if k != '_sha256'})
    return t

class OpenWorld:
    def __init__(self, setting, arch, tape, strategy=Strategy(), capture=False):
        self.s, self.arch, self.t, self.p = setting, arch, tape, strategy
        self.n = 10 + setting.spam
        self.b = Book(self.n + 1, setting.fp, setting.fc, 10_000, capture)
        self.live, self.native, self.launch_at = set(), set(), {}
        self.members = []
        self.actor = ['attacker'] + [f'alias:{i}' for i in range(1, strategy.aliases)]
        self.target = self.n - 1
        self.winner, self.closed = None, False
        self.count, self.daily = defaultdict(int), defaultdict(int)
        self.activity, self.actual, self.snapshots = [], {}, []
        self.score_area = defaultdict(int)
        self.score_time = 0
        self.close_backing = 0
        self.peak = 0
        self.creator_start = 2000 * M
        for j, cash in enumerate(tape['capital']): self.b.fund(f'u:{j}', cash)
        for i in range(10): self.b.fund(f'creator:{i}', 200*M)
        self.b.fund('attacker', 5000*M)
        self.b.fund('sponsor', 100*M)
        assert self.b.initial == 39100*M

    def accrue(self):
        end = min(1800, self.b.time)
        if end <= self.score_time: return
        dt = end - self.score_time
        for i in self.native:
            q = self.b.q[i]
            self.score_area[i] += q * (q + 1_000_000) * dt
        self.score_time = end

    def creator_fees(self, tx):
        if tx.token >= 10 and tx.token < self.n and tx.creator_fee:
            self.b.transfer(f'creator:{tx.token}', 'attacker', tx.creator_fee)

    def buy(self, owner, token, budget):
        self.accrue()
        tx = self.b.buy(owner, token, min(budget, self.b.cash[owner]), allowed=(token,))
        self.creator_fees(tx)
        return tx

    def sell(self, owner, token, quantity):
        self.accrue()
        tx = self.b.sell(owner, token, quantity)
        self.creator_fees(tx)
        return tx

    def risk(self):
        self.peak = max(self.peak, 5000*M - sum(self.b.cash[a] for a in self.actor))

    def launch(self, row):
        i = row['token']
        if i in self.live: return
        payer = 'attacker' if i >= 10 else f'creator:{i}'
        network_payer = 'sponsor' if self.s.sponsor_launch else payer
        fee = self.s.launch_fee if row['native'] else 0
        cost = self.s.network_launch + self.s.account_deposit
        needed = cost + fee if network_payer == payer else fee
        if self.b.cash[payer] < needed or self.b.cash[network_payer] < cost:
            self.count['failed_launches'] += 1
            return
        self.b.transfer(payer, 'platform_launch', fee)
        self.b.transfer(network_payer, 'network', self.s.network_launch)
        self.b.transfer(network_payer, f'account_deposit:{i}:{network_payer}', self.s.account_deposit)
        self.live.add(i)
        self.launch_at[i] = self.b.time
        if row['native']: self.native.add(i)
        self.b.log('open_launch', token=i, native=row['native'], payer=payer,
                   network_payer=network_payer, platform_fee=fee, network=self.s.network_launch,
                   account_deposit=self.s.account_deposit)
        self.count['launches'] += 1
        self.risk()

    def preferred(self, row):
        agent = self.t['agents'][row['actor']]
        candidates = [i for i in range(10) if i in self.live]
        if not candidates: return None
        def score(i):
            p = .01 + .0001*self.b.q[i]/Q
            value = math.log(self.t['quality'][i]) + (2*agent['loyalty'] if i == row['pref'] else 0)
            if agent['kind'] == 'momentum': value += .3*math.log(p/.01)
            return value + .04*math.log1p(self.b.holder_count[i])
        desired = max(candidates, key=lambda i:(score(i),-i))
        # Named stress: half of arrivals browse a feed giving each live mint one ticket.
        # No additional opportunities, wallets, or budgets are created by more launches.
        if row['feed_draw'] < self.s.feed_fraction:
            visible = sorted(self.live)
            selected = visible[min(len(visible)-1, int(row['feed_pick']*len(visible)))]
            if selected >= 10: desired = selected
        return desired

    def opportunity(self, row):
        s = self.s
        attention = 1. if row['t'] < 1800 else .8*(1+(row['t']-1800)/3600)**(-.12)
        if row['attention'] >= attention: return
        owner = f'u:{row["actor"]}'
        budget = min(row['budget'], self.b.cash[owner])
        if budget <= self.b.gas: return
        desired = self.preferred(row)
        if desired is None: return
        self.count['offered'] += budget
        target, routed = desired, False
        can_route = (self.arch == 'C' and self.closed and self.winner is not None and
                     self.b.time < 1800+s.route_hours*3600 and desired in self.native and
                     desired != self.winner and row['reach'] < s.reach)
        if can_route:
            self.count['reachable'] += budget
            agent = self.t['agents'][row['actor']]
            p = .01+.0001*self.b.q[self.winner]/Q
            propensity = s.acceptance*(1-.6*agent['loyalty'])*min(1,(max(.25,p)/.25)**(-.15))
            if row['accept'] < propensity:
                self.count['authorized'] += budget
                target, routed = self.winner, True
                premium = Fraction(str(s.premium_limit))
                if premium and (self.b.q[self.winner]+1_000_000)*premium.denominator > premium.numerator*(self.b.q[desired]+1_000_000):
                    target, routed = desired, False
                    self.count['premium_fallback'] += 1
                day = (self.b.time-1800)//86400
                if routed and s.route_cap:
                    fraction = Fraction(str(s.route_cap))
                    cap = self.close_backing*fraction.numerator//fraction.denominator
                    if self.daily[day] + budget > cap:
                        target, routed = desired, False
                        self.count['cap_fallback'] += 1
            elif row['fallback'] < s.reject_preferred: pass
            elif row['fallback'] < s.reject_preferred+s.reject_outside: target = self.n
            else:
                self.count['left_cash'] += budget
                return
        p = .01+.0001*self.b.q[target]/Q
        elasticity = min(1,(max(.25,p)/.25)**(-.35))
        if row['price_draw'] >= elasticity: return
        execution_budget = budget*10000//(10000+s.router_bps) if routed else budget
        try: tx = self.buy(owner,target,execution_budget)
        except Refused: return
        route_fee = ((-tx.cash_delta)*s.router_bps+9999)//10000 if routed else 0
        if route_fee:
            assert -tx.cash_delta+route_fee <= budget
            self.b.transfer(owner,'router_fees',route_fee)
            self.count['router_fee'] += route_fee
        self.actual[row['id']] = target
        self.count['executed'] += -tx.cash_delta + route_fee
        if target == self.n: self.count['outside_spent'] -= tx.cash_delta
        if routed:
            self.count['routed'] += -tx.cash_delta + route_fee
            self.daily[(self.b.time-1800)//86400] += -tx.cash_delta + route_fee
            self.b.log('authorized_route', owner=owner, preferred=desired, actual_mint=target,
                       budget=budget, rule=s.rule)
        self.activity.append((self.b.time,owner,tx.principal))

    def exit_opportunity(self, row):
        owner = f'u:{row["actor"]}'
        target = self.actual.get(row['id'])
        if target is None: return
        d = int(self.b.hold[owner,target]*row['exit_fraction'])
        if not d: return
        try: tx = self.sell(owner,target,d)
        except Refused: return
        self.activity.append((self.b.time,owner,tx.principal))

    def close(self):
        self.accrue()
        self.closed = True
        self.members = [i for i in self.native if 1800-self.launch_at[i] >= self.s.min_age
                        and reserve(self.b.q[i]) >= 10*M]
        score = {i:self.score_area[i] if self.s.rule == 'timecap' else
                 self.b.q[i]*(self.b.q[i]+1_000_000) for i in self.members}
        if score:
            top = max(score.values())
            leaders = [i for i,v in score.items() if v == top]
            if len(leaders) == 1: self.winner = leaders[0]
        if self.winner is not None: self.close_backing = reserve(self.b.q[self.winner])
        self.b.log('finalized', winner=self.winner, eligible=self.members, scores=score)

    def attack(self):
        if not self.p.budget or self.target not in self.live: return
        amount = min(self.p.budget*M,self.b.cash['attacker'])
        share = amount//len(self.actor)
        for actor in self.actor:
            if actor != 'attacker': self.b.transfer('attacker',actor,share)
            try: self.buy(actor,self.target,min(share,self.b.cash[actor]))
            except Refused: pass
        self.risk()

    def exit_actor(self):
        for actor in self.actor:
            for i in range(self.n+1):
                d = self.b.hold[actor,i]
                if not d: continue
                try: self.sell(actor,i,d)
                except Refused: pass
        self.risk()

    def snapshot(self, label):
        self.b.invariant()
        w = self.winner
        recent = 3600 if label == '1h' else 21600 if label == '24h' else 86400
        active = [r for r in self.activity if self.b.time-recent < r[0] <= self.b.time]
        actor_value = sum(self.b.cash[a] for a in self.actor)
        row = dict(seed=self.t['seed'],setting=self.s.name,arch=self.arch,label=label,
                   cohort_reserve=sum(reserve(self.b.q[i]) for i in self.live)/M,
                   platform_reserve=sum(reserve(self.b.q[i]) for i in self.native)/M,
                   all_market_reserve=sum(reserve(q) for q in self.b.q)/M,
                   winner_reserve=reserve(self.b.q[w])/M if w is not None else 0,
                   winner_depth=self.b.depth(w,500)/M if w is not None else 0,
                   cohort_depth=sum(self.b.depth(i,500) for i in self.live)/M,
                   active=len({r[1] for r in active}),events=len(active),winner=w,
                   creator_cash=(sum(self.b.cash[f'creator:{i}'] for i in range(10))-self.creator_start)/M,
                   trader_cash=sum(self.b.cash[f'u:{i}']-v for i,v in enumerate(self.t['capital']))/M,
                   attacker_profit=(actor_value-5000*M)/M,attacker_peak=self.peak/M,
                   attacker_residual=sum(self.b.hold[a,i] for a in self.actor for i in range(self.n+1))/Q,
                   captured=int(w == self.target),launched=len(self.live),eligible=len(self.members),
                   deposits=sum(v for k,v in self.b.cash.items() if k.startswith('account_deposit:'))/M,
                   sponsor_spent=(100*M-self.b.cash['sponsor'])/M,
                   initial_world=self.b.initial/M,tape_hash=self.t['_sha256'])
        for key in ('offered','reachable','authorized','executed','outside_spent','routed','left_cash','router_fee'):
            row[key] = self.count[key]/M
        row['actual_consent'] = row['authorized']/row['reachable'] if row['reachable'] else None
        row['unexecuted'] = max(0,row['offered']-row['executed'])
        row['premium_fallback'] = self.count['premium_fallback']
        row['cap_fallback'] = self.count['cap_fallback']
        self.snapshots.append(row)

    def run(self):
        events = []
        def add(t, priority, kind, data=None): events.append((t,priority,len(events),kind,data))
        for row in self.t['open_launches']: add(row['time'],-3,'launch',row)
        for row in self.t['opportunities']:
            add(row['t'],10,'opportunity',row)
            add(row['t']+row['hold'],11,'exit',row)
        add(1800,0,'close')
        add(int(1800*self.p.start),-1,'attack')
        add(1800+self.p.exit_hours*3600,2,'attack_exit')
        for label,offset in [('1h',3600),('24h',86400),('7d',604800)]:
            add(1800+offset,30,'snapshot',label)
        for t,_,_,kind,data in sorted(events):
            if t > 606600: continue
            self.b.time = t
            if kind == 'launch': self.launch(data)
            elif kind == 'opportunity': self.opportunity(data)
            elif kind == 'exit': self.exit_opportunity(data)
            elif kind == 'close': self.close()
            elif kind == 'attack': self.attack()
            elif kind == 'attack_exit': self.exit_actor()
            elif kind == 'snapshot': self.snapshot(data)
        self.b.time = 606601
        self.exit_actor()
        owners = [f'u:{i}' for i in range(64)] + [f'creator:{i}' for i in range(10)]
        stream(self.t['seed'],'terminal_order').shuffle(owners)
        for owner in owners:
            for i in range(self.n+1):
                if self.b.hold[owner,i]:
                    try: self.sell(owner,i,self.b.hold[owner,i])
                    except Refused: pass
        self.snapshot('exit')
        return self.snapshots
