"""Execute one matched tape in one arm (A: independent curves, B: shared curve)."""
import math
import numpy as np

from .book import SkinBook, Rejected
from .curves import PumpShape, LinearShape
from .tape import DEV, SNIPE, BUNDLE, ADV, WASH, SPAM, ORGANIC

DEPTH_U = (.01, .05, .10)
DEPTH_AT = (30, 120)   # minutes


def shape_of(c):
    return PumpShape() if c.shape == "pump" else LinearShape()


def depth(book, curve, u):
    """(buy cost incl. fee and gas to lift price by u, net proceeds of sale lowering it by u)."""
    sh, s = book.shape, book.states[curve]
    p = sh.price(s)
    up = sh.buy_gross_to_price(s, p*(1+u))*(1+book.fee)+book.gas
    down = sh.sell_gross_to_price(s, p*(1-u))*(1-book.fee)-book.gas
    return up, max(0.0, down)


def max_drawdown(path):
    peak = np.maximum.accumulate(path)
    return float(np.max(1-path/peak)) if len(path) else 0.0


def run_arm(tape, arm):
    c = tape.config
    n, N = c.n_memes, tape.n_total
    A = len(tape.org_time)
    smap = np.arange(N) if arm == "A" else np.zeros(N, dtype=int)
    # ---- wallets ----
    W_CRE = A
    W_SPAM = A+n
    W_SNIPE = W_SPAM+1
    W_BUNDLE = W_SNIPE+c.snipers
    W_ADV = W_BUNDLE+1
    W_ARB = W_ADV+1
    W = W_ARB+c.arbitrageurs
    cash0 = np.zeros(W)
    cash0[:A] = tape.org_budget+3*c.gas
    cash0[W_CRE:W_CRE+n] = tape.dev_budget+c.launch_cost+20*c.gas
    if c.wash:
        rank, g, every, dur = c.wash
        target = int(np.argsort(tape.launch[:n], kind="stable")[int(rank)])
        rounds = int(np.sum(tape.ev_kind == WASH))
        cash0[W_CRE+target] += 2*g*(1+c.fee)+rounds*(2*c.fee*g+2*c.gas)+50
    if c.spam:
        m, ts, dev_buy = int(c.spam[0]), float(c.spam[1]), float(c.spam[2])
        cash0[W_SPAM] = m*(c.launch_cost+dev_buy+4*c.gas)
    cash0[W_SNIPE:W_BUNDLE] = n*(c.snipe_budget+2*c.gas)
    cash0[W_BUNDLE] = (float(c.bundle[1]) if c.bundle else 0)+(n+2)*2*c.gas
    cash0[W_ADV] = c.adversary_budget+10*c.gas
    cash0[W_ARB:W] = c.arb_capital
    book = SkinBook(shape_of(c), smap, cash0, fee=c.fee, creator_share=c.creator_share, gas=c.gas)

    # ---- organic positions ----
    tokens = np.zeros(A)
    cost = np.zeros(A)
    entry = np.full(A, np.nan)
    is_open = np.zeros(A, dtype=bool)
    peak = np.zeros(A)
    exit_t = np.full(A, np.nan)
    pick = tape.org_pick
    strat = []   # strategic positions: dict(w, skin, tok, cost, entry, tp, sl, until, kind)

    # ---- recording ----
    n_snap = c.horizon//60+1
    nc = book.n_curves
    S_price = np.zeros((n_snap, nc))
    S_mcap = np.zeros((n_snap, nc))
    S_res = np.zeros((n_snap, nc))
    S_rec = np.zeros((n_snap, nc))
    depth_rows = {}
    ring = np.tile(book.curve_prices(), (10, 1))   # last 5 minutes of tick prices
    ring_i = 0
    bundle_first = None
    bundle_share = float("nan")
    shock_done = not c.shock
    shocked_open = np.zeros(A, dtype=bool)
    arb_trades = 0
    rejects = 0
    wash_rounds = 0

    def snap(k):
        for ci, s in enumerate(book.states):
            S_price[k, ci] = book.shape.price(s)
            S_mcap[k, ci] = book.shape.mcap(s)
            S_res[k, ci] = book.shape.reserve(s)
        S_rec[k] = book.recoverable()

    def try_buy(w, skin, budget):
        nonlocal rejects
        try:
            return book.buy(w, skin, min(budget, book.cash[w]))
        except Rejected:
            rejects += 1
            return 0.0, 0.0

    def close_strategic(p):
        if book.hold[p["w"], p["skin"]] > 0 and p["tok"] > 0:
            try:
                book.sell(p["w"], p["skin"], min(p["tok"], book.hold[p["w"], p["skin"]]))
            except Rejected:
                pass
        p["tok"] = 0.0

    def tick(t):
        nonlocal ring_i, bundle_share, shock_done, arb_trades
        if t % 60 == 0:
            snap(t//60)
            if t//60 in DEPTH_AT:
                mc = book.mcaps()
                order = np.argsort(-mc, kind="stable")
                top, med = int(order[0]), int(order[len(order)//2])
                for u in DEPTH_U:
                    depth_rows[(t//60, "top", u)] = depth(book, top, u)
                    depth_rows[(t//60, "median", u)] = depth(book, med, u)
        if bundle_first is not None and math.isnan(bundle_share) and t >= bundle_first+60:
            held = np.zeros(nc)
            np.add.at(held, smap, book.hold[W_BUNDLE])
            circ = np.array([book.shape.circulating(s) for s in book.states])
            mask = held > 0
            bundle_share = float(held[mask].sum()/circ[mask].sum()) if mask.any() else 0.0
        if not shock_done and t >= c.shock_time:
            shock_done = True
            k = tape.shock_meme
            victims = np.flatnonzero(is_open & (pick == k))
            shocked_open[:] = is_open & (pick != k)
            for i in victims:
                try:
                    book.sell(int(i), k, tokens[i])
                except Rejected:
                    continue
                is_open[i] = False
                exit_t[i] = t
            for p in strat:
                if p["kind"] == "creator" and p["skin"] == k:
                    close_strategic(p)
        prices = book.curve_prices()
        ring[ring_i % 10] = prices
        ring_i += 1
        dd = 1-prices/ring.max(axis=0)
        # organic exits (decided on the tick's prices, executed in index order)
        idx = np.flatnonzero(is_open)
        if len(idx):
            ps = prices[smap[pick[idx]]]
            mark = tokens[idx]*ps
            peak[idx] = np.maximum(peak[idx], mark)
            ret = mark/cost[idx]
            go = ((ret >= tape.tp[idx]) | (ret <= tape.sl[idx]) | (mark <= peak[idx]*(1-tape.trail[idx]))
                  | (t-entry[idx] >= tape.max_hold[idx]) | (dd[smap[pick[idx]]] >= tape.panic[idx]))
            for i in idx[go]:
                try:
                    book.sell(int(i), int(pick[i]), tokens[i])
                except Rejected:
                    continue
                is_open[i] = False
                exit_t[i] = t
        # strategic exits
        sp = book.skin_prices()
        for p in strat:
            if p["tok"] <= 0:
                continue
            ret = p["tok"]*sp[p["skin"]]/p["cost"]
            if ret >= p["tp"] or ret <= p["sl"] or t >= p["until"]:
                close_strategic(p)
        # arbitrage: relative-value rotation every 5 minutes
        if c.arbitrageurs and t % 300 == 0:
            r5 = prices/ring.min(axis=0)-1   # crude 5-minute momentum per curve
            live = np.flatnonzero((tape.launch <= t) & ~tape.spam_mask)
            if len(live) > 1:
                rs = r5[smap[live]]
                hot = live[int(np.argmax(rs))]
                if rs.max() > .2:
                    cand = live[smap[live] != smap[hot]]
                    if len(cand):
                        tgt = int(cand[int(np.argmax(r5[smap[cand]]))])
                        for a in range(c.arbitrageurs):
                            w = W_ARB+a
                            if book.cash[w] > 300+c.gas:
                                tok, g = try_buy(w, tgt, 300.0)
                                if tok > 0:
                                    arb_trades += 1
                                    strat.append(dict(w=w, skin=tgt, tok=tok, cost=300.0, entry=t, tp=1.2, sl=.85,
                                                      until=t+600, kind="arb"))

    snap(0)
    next_tick = c.tick
    spam_paid = False
    for e in range(len(tape.ev_time)):
        t = tape.ev_time[e]
        while next_tick <= t and next_tick <= c.horizon:
            tick(next_tick)
            next_tick += c.tick
        kind, actor, meme, budget = tape.ev_kind[e], int(tape.ev_actor[e]), int(tape.ev_meme[e]), float(tape.ev_budget[e])
        if kind == ORGANIC:
            tok, g = try_buy(actor, meme, budget)
            if tok > 0:
                tokens[actor], cost[actor], entry[actor] = tok, budget, t
                is_open[actor] = True
                peak[actor] = tok*book.price(meme)
        elif kind == DEV:
            w = W_CRE+actor
            if c.launch_cost:
                book.spend(w, c.launch_cost)
            tok, g = try_buy(w, meme, budget)
            strat.append(dict(w=w, skin=meme, tok=tok, cost=budget, entry=t, tp=tape.creator_tp[actor], sl=-1,
                              until=float("inf"), kind="creator"))
        elif kind == SNIPE:
            w = W_SNIPE+actor
            tok, g = try_buy(w, meme, budget)
            strat.append(dict(w=w, skin=meme, tok=tok, cost=budget, entry=t, tp=2.0, sl=.6, until=t+600, kind="sniper"))
        elif kind == BUNDLE:
            tok, g = try_buy(W_BUNDLE, meme, budget)
            if bundle_first is None:
                bundle_first = t
            strat.append(dict(w=W_BUNDLE, skin=meme, tok=tok, cost=budget, entry=t, tp=float(c.bundle[2]), sl=-1,
                              until=t+float(c.bundle[3]), kind="bundler"))
        elif kind == ADV:
            tok, g = try_buy(W_ADV, meme, budget)
            strat.append(dict(w=W_ADV, skin=meme, tok=tok, cost=budget, entry=t, tp=2.0, sl=-1, until=3600.0,
                              kind="adversary"))
        elif kind == WASH:
            w = W_CRE+actor
            tok, g = try_buy(w, meme, budget)
            if tok > 0:
                book.sell(w, meme, tok)
                wash_rounds += 1
        elif kind == SPAM:
            if c.launch_cost:
                book.spend(W_SPAM, c.launch_cost)
            if budget > 0:
                tok, g = try_buy(W_SPAM, meme, budget)
                strat.append(dict(w=W_SPAM, skin=meme, tok=tok, cost=budget, entry=t, tp=float(c.spam[3]), sl=-1,
                                  until=t+1800, kind="spam"))
    while next_tick <= c.horizon:
        tick(next_tick)
        next_tick += c.tick
    book.check()

    # ---- terminal accounting: paper mark, then liquidation in seed-fixed order ----
    sp = book.skin_prices()
    paper_wealth = book.cash+book.hold@sp
    rec_final = book.recoverable()
    book.terminal = True
    order = np.random.default_rng(tape.liquidation_seed).permutation(W)
    for w in order:
        book.sell_all(int(w))
    book.check()
    pnl = book.cash-cash0
    paper = paper_wealth-cash0
    locked = float(book.reserves().sum())
    # E9 zero-sum identity: every participant's P&L incl. creator fee income.
    lhs = float(pnl.sum()+book.creator_fees.sum())
    rhs = -(book.protocol_fees+book.gas_paid+book.sunk+book.migration_paid+book.terminal_fees+locked)
    assert abs(lhs-rhs) <= 1e-7*max(1.0, book.initial_total), f"zero-sum identity {lhs} vs {rhs}"

    # ---- metrics ----
    tops = S_mcap.max(axis=1)
    k_peak = int(np.argmax(tops))
    top_curve = int(np.argmax(S_mcap[k_peak]))
    totals = S_mcap.sum(axis=1)
    rec_tot = S_rec.sum(axis=1)
    path = S_price[:, top_curve]
    lr = np.diff(np.log(S_price[:121]), axis=0)
    honest_curves = np.unique(smap[:n])
    vol_by_meme = lr[:, smap[:n]].std(axis=0)*math.sqrt(60)
    dd_by_meme = np.array([max_drawdown(S_price[:, smap[j]]) for j in range(n)])
    meme_peaks = S_mcap[:, smap[:n]].max(axis=0)
    graduated = sum(1 for s in book.states if s[0] == 1) if c.shape == "pump" else 0
    m = dict(arm=arm, seed=c.seed, concentration=c.concentration, shape=c.shape,
             hhi=float(np.square(tape.meme_buy_dollars[:n]/tape.meme_buy_dollars[:n].sum()).sum()),
             peak_top_mcap=float(tops[k_peak]), peak_top_minute=k_peak,
             peak_total_mcap=float(totals.max()),
             meme_peak_median=float(np.median(meme_peaks)), meme_peak_max=float(meme_peaks.max()),
             memes_over_50k=int(np.sum(meme_peaks >= 50_000)) if arm == "A" else int(meme_peaks[0] >= 50_000),
             peak_top_recoverable=float(S_rec[:, top_curve].max()),
             peak_total_recoverable=float(rec_tot.max()),
             recoverable_at_peak_top=float(S_rec[k_peak, top_curve]),
             final_total_recoverable=float(rec_final.sum()), locked_lp=locked,
             graduated=graduated, rejects=rejects, arb_trades=arb_trades, wash_rounds=wash_rounds,
             top_max_drawdown=max_drawdown(path), meme_mean_max_drawdown=float(dd_by_meme.mean()),
             top_vol_hourly=float(lr[:, top_curve].std()*math.sqrt(60)),
             meme_mean_vol_hourly=float(vol_by_meme.mean()),
             protocol_fees=book.protocol_fees, creator_fees_total=float(book.creator_fees[:n].sum()),
             gas=book.gas_paid, volume=float(book.skin_volume.sum()),
             sniper_pnl=float(pnl[W_SNIPE:W_BUNDLE].sum()), bundler_pnl=float(pnl[W_BUNDLE]),
             bundler_share_1min=bundle_share, adversary_pnl=float(pnl[W_ADV]), arb_pnl=float(pnl[W_ARB:W].sum()),
             spammer_fees=float(book.creator_fees[n:].sum()), spammer_pnl=float(pnl[W_SPAM]),
             organic_pnl=float(pnl[:A].sum()), organic_paper_pnl=float(paper[:A].sum()),
             organic_cost=float(cost.sum()))
    for minute in DEPTH_AT:
        m[f"reserve_total_{minute}"] = float(S_res[minute].sum())
        m[f"reserve_top_{minute}"] = float(S_res[minute].max())
        m[f"recoverable_total_{minute}"] = float(S_rec[minute].sum())
        m[f"mcap_total_{minute}"] = float(S_mcap[minute].sum())
        m[f"mcap_top_{minute}"] = float(S_mcap[minute].max())
        for which in ("top", "median"):
            for u in DEPTH_U:
                up, down = depth_rows[(minute, which, u)]
                m[f"depth_buy_{which}_{int(u*100)}pct_{minute}"] = up
                m[f"depth_sell_{which}_{int(u*100)}pct_{minute}"] = down
    creators = dict(fees=book.creator_fees[:n].copy(), fees_buy=book.creator_fees_buy[:n].copy(), dev_pnl=pnl[W_CRE:W_CRE+n].copy(),
                    launch=tape.launch[:n].copy(), peak=meme_peaks, buy_dollars=tape.meme_buy_dollars[:n].copy())
    organic = dict(pnl=pnl[:A].copy(), paper=paper[:A].copy(), budget=tape.org_budget.copy(),
                   time=tape.org_time.copy(), pick=pick.copy(), type=tape.org_type.copy(),
                   shocked=shocked_open.copy(), exit=exit_t)
    series = dict(top_mcap=tops, total_mcap=totals, total_recoverable=rec_tot)
    return dict(metrics=m, creators=creators, organic=organic, series=series)
