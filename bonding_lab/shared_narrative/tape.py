"""Matched synthetic narrative tapes and the attention process.

A tape is generated once per seed and executed unchanged in both arms. It fixes
launch times, organic arrival times, types, dollar budgets, exit parameters,
**which meme each buyer picks**, every arm-invariant scheduled buy and the
terminal liquidation order. All behavioural values are assumptions.
"""
from dataclasses import dataclass, field, asdict
import math
import numpy as np

from ..narrative.model import stream, hash_obj

ORGANIC_TYPES = ("retail", "momentum", "whale", "holder")   # subset of agents.KINDS
ATTENTION = ("momentum", "random", "confused")

# Scheduled event kinds (all buy dollars arm-invariant).
DEV, SNIPE, BUNDLE, ADV, WASH, SPAM, ORGANIC = range(7)


@dataclass(frozen=True)
class Config:
    seed: int = 0
    shape: str = "pump"
    n_memes: int = 10
    horizon: int = 240*60
    launch_window: int = 15*60
    tick: int = 30
    # demand
    arrivals: float = 6200.0      # calibrated: median Arm A meme peak ~$50k at c=.25
    demand_scale: float = 1.0
    decay: float = 45*60
    budget_median: float = 50.0
    budget_sigma: float = 1.0
    budget_cap: float = 2000.0
    whale_mult: float = 10.0
    type_mix: tuple = (.55, .20, .05, .20)
    # attention
    concentration: float = .25
    beta: float = 2.0
    trend_halflife: float = 600.0
    trend_prior: float = 100.0
    confused_share: float = .3
    confusion: float = .5
    # fees
    fee: float = .01
    creator_share: float = .30
    gas: float = .05
    launch_cost: float = 0.0
    # strategic agents
    dev_median: float = 300.0
    dev_sigma: float = .6
    dev_cap: float = 1500.0
    snipers: int = 3
    snipe_budget: float = 150.0
    bundle: tuple = ("first", 1500.0, 3.0, 1800)   # strategy, budget, take-profit x, max hold s
    adversary_budget: float = 3000.0
    arbitrageurs: int = 2
    arb_capital: float = 3000.0
    # exit-behaviour sensitivity
    tp_scale: float = 1.0
    organic_exits: bool = True
    # stress / attacks
    shock: bool = False
    shock_time: int = 60*60
    wash: tuple = ()      # (meme_launch_rank, gross_per_round, interval_s, duration_s)
    spam: tuple = ()      # (m, launch_time_s, dev_buy, dev_take_profit)

    def __post_init__(self):
        if self.shape not in ("pump", "linear"):
            raise ValueError("Unknown shape")
        if not 0 <= self.concentration <= 1 or not 0 <= self.confusion <= 1:
            raise ValueError("Probabilities must lie in [0, 1]")
        if abs(sum(self.type_mix)-1) > 1e-9 or self.n_memes < 2:
            raise ValueError("Invalid type mix or meme count")


@dataclass
class Tape:
    config: Config
    n_total: int                 # honest memes + spam skins
    launch: np.ndarray           # launch time per meme/skin
    spam_mask: np.ndarray
    # events, sorted by (time, sequence)
    ev_time: np.ndarray
    ev_kind: np.ndarray
    ev_actor: np.ndarray         # organic index / creator index / agent index
    ev_meme: np.ndarray
    ev_budget: np.ndarray
    # organic arrivals (indexed by organic id)
    org_time: np.ndarray
    org_type: np.ndarray
    org_attention: np.ndarray
    org_pick: np.ndarray
    org_budget: np.ndarray
    tp: np.ndarray
    sl: np.ndarray
    trail: np.ndarray
    max_hold: np.ndarray
    panic: np.ndarray
    dev_budget: np.ndarray
    creator_tp: np.ndarray
    shock_meme: int
    meme_buy_dollars: np.ndarray  # arm-invariant scheduled+organic buy dollars per meme
    liquidation_seed: int
    extra: dict = field(default_factory=dict)

    def fingerprint(self):
        return hash_obj(dict(pick=self.org_pick.tolist(), budget=np.round(self.org_budget, 9).tolist(),
                             time=np.round(self.ev_time, 9).tolist(), kind=self.ev_kind.tolist(),
                             meme=self.ev_meme.tolist(), b=np.round(self.ev_budget, 9).tolist()))


def _u(seed, name, n):
    r = stream(seed, name)
    return np.array([r.random() for _ in range(n)])


def make_tape(c: Config) -> Tape:
    seed = c.seed
    n = c.n_memes
    m_spam = int(c.spam[0]) if c.spam else 0
    n_total = n+m_spam
    # Launch times: meme 0 at t=0, others uniform over the launch window.
    lt = np.concatenate([[0.0], np.sort(_u(seed, "launch", n-1)*c.launch_window)])
    launch = np.concatenate([lt, np.full(m_spam, float(c.spam[1]) if c.spam else 0.0)])
    spam_mask = np.arange(n_total) >= n
    # Organic arrivals: Poisson count, truncated-exponential times.
    lam = c.arrivals*c.demand_scale
    mass = 1-math.exp(-c.horizon/c.decay)
    rng = np.random.default_rng(int.from_bytes(stream(seed, "count").randbytes(8), "big"))
    count = int(rng.poisson(lam))
    u = _u(seed, "arrival", count)
    times = np.sort(-c.decay*np.log1p(-u*mass))
    times = np.minimum(times, c.horizon-1)
    tu = _u(seed, "type", count)
    types = np.searchsorted(np.cumsum(c.type_mix), tu, side="right").clip(0, 3)
    r = stream(seed, "budget")
    budgets = np.array([min(c.budget_cap, math.exp(r.normalvariate(math.log(c.budget_median), c.budget_sigma)))
                        for _ in range(count)])
    budgets = np.where(types == 2, budgets*c.whale_mult, budgets)
    au = _u(seed, "attention", count)
    pm = c.concentration
    pr = (1-pm)*(1-c.confused_share)
    attention = np.where(au < pm, 0, np.where(au < pm+pr, 1, 2))
    pick_u = _u(seed, "pick", count)
    conf_u = _u(seed, "confuse", count)
    other_u = _u(seed, "other", count)
    # Exit parameters per arrival type.
    e = [_u(seed, f"exit{i}", count) for i in range(5)]
    inf = float("inf")
    tp = np.select([types == 0, types == 1, types == 2, types == 3],
                   [1.5+2.5*e[0], np.full(count, inf), 2+3*e[0], 5+15*e[0]])
    sl = np.select([types == 0, types == 1, types == 2, types == 3], [np.full(count, .5), np.full(count, .6),
                   np.full(count, .6), np.zeros(count)])
    trail = np.select([types == 0, types == 1, types == 2, types == 3],
                      [np.full(count, 1.0), np.full(count, .3), np.full(count, .35), np.full(count, 1.0)])
    max_hold = np.select([types == 0, types == 1, types == 2, types == 3],
                         [600+6600*e[1], 900+4500*e[1], 1800+9000*e[1], np.full(count, inf)])
    panic = np.select([types == 0, types == 1, types == 2, types == 3],
                      [.15+.35*e[2], .10+.25*e[2], .20+.30*e[2], np.full(count, inf)])
    tp = tp*c.tp_scale
    if not c.organic_exits:
        tp[:] = inf
        sl[:] = 0.0
        trail[:] = 1.0
        max_hold[:] = inf
        panic[:] = inf
    # Creators.
    r = stream(seed, "dev")
    dev = np.array([min(c.dev_cap, math.exp(r.normalvariate(math.log(c.dev_median), c.dev_sigma))) for _ in range(n)])
    ctp = 3+5*_u(seed, "creator_tp", n)

    # ---- scheduled events (time, sequence-priority, kind, actor, meme, budget) ----
    sched = []
    for j in range(n):
        sched.append((launch[j], 0, DEV, j, j, dev[j]))
        for s in range(c.snipers):
            sched.append((launch[j]+2+s, 2, SNIPE, s, j, c.snipe_budget))
    strategy, bbudget = (c.bundle[0], float(c.bundle[1])) if c.bundle else ("none", 0.0)
    if c.bundle and bbudget > 0:
        if strategy == "first":
            sched.append((launch[0], 1, BUNDLE, 0, 0, bbudget))
        elif strategy == "spread":
            for j in range(n):
                sched.append((launch[j], 1, BUNDLE, 0, j, bbudget/n))
        elif strategy == "leader5":
            sched.append((300.0, 1, BUNDLE, 0, -1, bbudget))   # target chosen by V below
        else:
            raise ValueError("Unknown bundle strategy")
    for k, t in enumerate((180.0, 360.0, 540.0)):
        if c.adversary_budget > 0:
            sched.append((t, 3, ADV, 0, -1, c.adversary_budget/3))
    if c.wash:
        rank, g, every, dur = c.wash
        target = int(np.argsort(launch[:n], kind="stable")[int(rank)])
        t = launch[target]+5
        while t < min(c.horizon, launch[target]+dur):
            sched.append((t, 4, WASH, target, target, float(g)))
            t += every
    if c.spam:
        m, ts, dev_buy = int(c.spam[0]), float(c.spam[1]), float(c.spam[2])
        for i in range(m):
            sched.append((ts, 0, SPAM, i, n+i, dev_buy))
    for i in range(count):
        sched.append((times[i], 5, ORGANIC, i, -1, budgets[i]))
    sched.sort(key=lambda x: (x[0], x[1], x[3], x[4]))
    ev_time = np.array([x[0] for x in sched])
    ev_kind = np.array([x[2] for x in sched], dtype=int)
    ev_actor = np.array([x[3] for x in sched], dtype=int)
    ev_meme = np.array([x[4] for x in sched], dtype=int)
    ev_budget = np.array([x[5] for x in sched])

    # ---- attention process over arm-invariant buy flow ----
    decay_rate = math.log(2)/c.trend_halflife
    V = np.zeros(n_total)
    last = 0.0
    picks = np.full(count, -1)
    cumulative = np.zeros(n_total)
    shock_meme = -1
    shock_done = not c.shock
    for e_i in range(len(ev_time)):
        t = ev_time[e_i]
        if not shock_done and t >= c.shock_time:
            order = np.argsort(-cumulative[:n], kind="stable")
            shock_meme = int(order[1])
            shock_done = True
        V *= math.exp(-decay_rate*(t-last))
        last = t
        kind = ev_kind[e_i]
        live = np.flatnonzero(launch <= t)
        if kind == ORGANIC:
            i = ev_actor[e_i]
            w = (V[live]+c.trend_prior)**c.beta
            intended = live[min(len(live)-1, int(np.searchsorted(np.cumsum(w)/w.sum(), pick_u[i], side="right")))]
            a = attention[i]
            if a == 1:
                choice = live[min(len(live)-1, int(pick_u[i]*len(live)))]
            elif a == 2 and len(live) > 1 and conf_u[i] < c.confusion:
                others = live[live != intended]
                choice = others[min(len(others)-1, int(other_u[i]*len(others)))]
            else:
                choice = intended
            picks[i] = choice
            ev_meme[e_i] = choice
        elif kind in (ADV, BUNDLE) and ev_meme[e_i] < 0:
            honest = live[live < n]
            ev_meme[e_i] = int(honest[np.argmax(V[honest])])
        meme = ev_meme[e_i]
        V[meme] += ev_budget[e_i]
        cumulative[meme] += ev_budget[e_i]
    if not shock_done:
        shock_meme = int(np.argsort(-cumulative[:n], kind="stable")[1])
    liquidation_seed = int.from_bytes(stream(seed, "liquidation").randbytes(4), "big")
    return Tape(c, n_total, launch, spam_mask, ev_time, ev_kind, ev_actor, ev_meme, ev_budget,
                times, types, attention, picks, budgets, tp, sl, trail, max_hold, panic, dev, ctp,
                shock_meme, cumulative, liquidation_seed)


def hhi(dollars):
    total = dollars.sum()
    return float(np.square(dollars/total).sum()) if total > 0 else float("nan")


def config_dict(c):
    return asdict(c)
