"""Build tables (markdown) and a JSON summary from experiment outputs."""
import json
import os

import numpy as np
import pandas as pd

from .stats import bootstrap, cluster_bootstrap, cara_ce, ssd_dominates
from .experiments import select_best, WASH_SHARES

U = (1, 5, 10)


def money(x):
    if not np.isfinite(x):
        return "n/a"
    a = abs(x)
    if a >= 1e6:
        return f"${x/1e6:,.2f}M"
    if a >= 1e4:
        return f"${x/1e3:,.1f}k"
    return f"${x:,.0f}" if a >= 100 else f"${x:,.2f}"


def pct(x):
    return f"{100*x:.1f}%" if np.isfinite(x) else "n/a"


def ci(v, stat=np.mean, fmt=money):
    p, lo, hi = bootstrap(v, stat)
    return f"{fmt(p)} [{fmt(lo)}, {fmt(hi)}]"


def table(rows, header):
    out = ["| "+" | ".join(header)+" |", "|"+"---|"*len(header)]
    out += ["| "+" | ".join(str(c) for c in r)+" |" for r in rows]
    return "\n".join(out)


def paired(runs, scenario, col):
    d = runs[runs.scenario == scenario].pivot(index="seed", columns="arm", values=col)
    return d["A"].values, d["B"].values


# ------------------------------------------------------------------ sections
def runner_section(runs, scen_list, S):
    rows = []
    for sc in scen_list:
        a, b = paired(runs, sc, "peak_top_mcap")
        ta, _ = paired(runs, sc, "peak_total_mcap")
        h = runs[(runs.scenario == sc) & (runs.arm == "A")].hhi.mean()
        ratio = b/a
        rows.append([sc, f"{h:.2f}", ci(a, np.median), ci(b, np.median), money(np.quantile(a, .9)), money(np.quantile(b, .9)),
                     f"{np.median(ratio):.2f}× [{np.quantile(ratio, .1):.2f}, {np.quantile(ratio, .9):.2f}]",
                     pct((b > a).mean()), pct((a >= 1e6).mean()), pct((b >= 1e6).mean()), ci(ta, np.median)])
        S.setdefault("runner", {})[sc] = dict(hhi=h, A_median=float(np.median(a)), B_median=float(np.median(b)),
                                             A_mean=float(a.mean()), B_mean=float(b.mean()),
                                             ratio_median=float(np.median(ratio)), p_B_bigger=float((b > a).mean()),
                                             p_A_1m=float((a >= 1e6).mean()), p_B_1m=float((b >= 1e6).mean()),
                                             p_A_5m=float((a >= 5e6).mean()), p_B_5m=float((b >= 5e6).mean()),
                                             A_total_median=float(np.median(ta)), A_max=float(a.max()), B_max=float(b.max()))
    return table(rows, ["scenario", "HHI", "A best-token peak (median, 95% CI)", "B shared peak (median, 95% CI)",
                        "A p90", "B p90", "B/A per seed (median [p10, p90])", "P(B>A)", "P(A≥$1M)", "P(B≥$1M)",
                        "A summed narrative peak (median)"])


def recoverable_section(runs, scen_list, S):
    rows = []
    for sc in scen_list:
        out = [sc]
        for arm in "AB":
            r = runs[(runs.scenario == sc) & (runs.arm == arm)]
            paper = r.peak_top_mcap.values
            rec = r.recoverable_at_peak_top.values
            out += [money(np.median(paper)), money(np.median(rec)), f"{np.median(paper/np.maximum(rec, 1)):.1f}×"]
        a, b = paired(runs, sc, "peak_total_recoverable")
        out += [ci(a, np.median), ci(b, np.median), ci(b-a, np.mean)]
        rows.append(out)
        S.setdefault("recoverable", {})[sc] = dict(A_peak_total_recoverable_median=float(np.median(a)),
                                                  B_peak_total_recoverable_median=float(np.median(b)),
                                                  diff_mean=float((b-a).mean()))
    return table(rows, ["scenario", "A top paper peak", "A recoverable at that moment", "A paper/rec",
                        "B paper peak", "B recoverable at that moment", "B paper/rec",
                        "A peak total recoverable (median)", "B peak total recoverable (median)", "B−A (mean, CI)"])


def depth_section(runs, sc, S):
    rows = []
    for minute in (30, 120):
        for label, col_a, col_b in (("reserve held (total)", f"reserve_total_{minute}", f"reserve_total_{minute}"),
                                    ("reserve held (largest curve)", f"reserve_top_{minute}", f"reserve_top_{minute}"),
                                    ("recoverable (total)", f"recoverable_total_{minute}", f"recoverable_total_{minute}")):
            a, _ = paired(runs, sc, col_a)
            _, b = paired(runs, sc, col_b)
            rows.append([f"{minute} min", label, ci(a, np.median), ci(b, np.median), ci(b-a, np.mean)])
        for u in U:
            for side in ("buy", "sell"):
                a_top, b = paired(runs, sc, f"depth_{side}_top_{u}pct_{minute}")
                a_med, _ = paired(runs, sc, f"depth_{side}_median_{u}pct_{minute}")
                what = f"{'cost to lift' if side == 'buy' else 'sale that drops'} price {u}%"
                rows.append([f"{minute} min", what, f"top {money(np.median(a_top))} · median meme {money(np.median(a_med))}",
                             ci(b, np.median), f"B/A-top median {np.median(b/np.maximum(a_top, 1e-9)):.2f}×"])
                S.setdefault("depth", {})[f"{sc}_{side}_{u}_{minute}"] = dict(
                    A_top=float(np.median(a_top)), A_median=float(np.median(a_med)), B=float(np.median(b)))
    return table(rows, ["time", "quantity", "Arm A (median; top/median meme)", "Arm B shared (median, CI)", "paired"])


def creator_frame(cr, sc):
    return cr[cr.scenario == sc]


def creator_section(cr, sc, S, launch_cost=0.0):
    d = creator_frame(cr, sc)
    rows = []
    stats = {}
    for arm in "AB":
        x = d[d.arm == arm]
        net, fees, seeds = x.net.values-launch_cost, x.fees.values, x.seed.values
        st = dict(
            mean_net=cluster_bootstrap(net, seeds, np.mean), median_net=cluster_bootstrap(net, seeds, np.median),
            p_net_pos=cluster_bootstrap(net, seeds, lambda v: (v > 0).mean()),
            mean_fees=cluster_bootstrap(fees, seeds, np.mean), median_fees=cluster_bootstrap(fees, seeds, np.median),
            p_fees_100=cluster_bootstrap(fees, seeds, lambda v: (v >= 100).mean()),
            p_fees_1000=cluster_bootstrap(fees, seeds, lambda v: (v >= 1000).mean()),
            p_net_1000=cluster_bootstrap(net, seeds, lambda v: (v >= 1000).mean()),
            q=np.quantile(net, [.01, .05, .10, .25, .5, .75, .90, .95, .99]).tolist(),
            fq=np.quantile(fees, [.10, .25, .5, .75, .90, .99]).tolist(),
            min=float(net.min()), max=float(net.max()), fee_max=float(fees.max()),
            ce_1000=cara_ce(net, 1/1000), ce_300=cara_ce(net, 1/300), ce_100=cara_ce(net, 1/100),
            top_share=float(x.groupby("seed").fees.apply(lambda v: v.max()/max(v.sum(), 1e-9)).mean()),
            dev_mean=float(x.dev_pnl.mean()), dev_median=float(x.dev_pnl.median()),
            dev_p_pos=float((x.dev_pnl > 0).mean()),
            fees_buy_mean=float(x.fees_buy.mean()), fees_sell_mean=float((x.fees-x.fees_buy).mean()))
        stats[arm] = st
    na = creator_frame(cr, sc)
    a_net = na[na.arm == "A"].net.values-launch_cost
    b_net = na[na.arm == "B"].net.values-launch_cost
    stats["B_ssd_A"] = ssd_dominates(b_net, a_net)
    stats["A_ssd_B"] = ssd_dominates(a_net, b_net)
    S.setdefault("creators", {})[sc] = stats

    def f3(t, fmt=money):
        return f"{fmt(t[0])} [{fmt(t[1])}, {fmt(t[2])}]"
    A, B = stats["A"], stats["B"]
    rows = [["mean net (fees + first-buy P&L)", f3(A["mean_net"]), f3(B["mean_net"])],
            ["median net", f3(A["median_net"]), f3(B["median_net"])],
            ["P(net > 0)", f3(A["p_net_pos"], pct), f3(B["p_net_pos"], pct)],
            ["P(net ≥ $1,000)", f3(A["p_net_1000"], pct), f3(B["p_net_1000"], pct)],
            ["mean fee income", f3(A["mean_fees"]), f3(B["mean_fees"])],
            ["median fee income", f3(A["median_fees"]), f3(B["median_fees"])],
            ["P(fees ≥ $100)", f3(A["p_fees_100"], pct), f3(B["p_fees_100"], pct)],
            ["P(fees ≥ $1,000)", f3(A["p_fees_1000"], pct), f3(B["p_fees_1000"], pct)],
            ["fee income: buy side / sell side (mean)", f"{money(A['fees_buy_mean'])} / {money(A['fees_sell_mean'])}",
             f"{money(B['fees_buy_mean'])} / {money(B['fees_sell_mean'])}"],
            ["first-buy P&L mean / median / P(>0)", f"{money(A['dev_mean'])} / {money(A['dev_median'])} / {pct(A['dev_p_pos'])}",
             f"{money(B['dev_mean'])} / {money(B['dev_median'])} / {pct(B['dev_p_pos'])}"],
            ["top creator's share of the ten creators' fees", pct(A["top_share"]), pct(B["top_share"])],
            ["net quantiles p1/p5/p10/p25", " / ".join(money(v) for v in A["q"][:4]), " / ".join(money(v) for v in B["q"][:4])],
            ["net quantiles p50/p75/p90/p95/p99", " / ".join(money(v) for v in A["q"][4:]), " / ".join(money(v) for v in B["q"][4:])],
            ["worst / best observed net", f"{money(A['min'])} / {money(A['max'])}", f"{money(B['min'])} / {money(B['max'])}"],
            ["certainty equivalent, CARA a=1/$1000 · 1/$300 · 1/$100",
             f"{money(A['ce_1000'])} · {money(A['ce_300'])} · {money(A['ce_100'])}",
             f"{money(B['ce_1000'])} · {money(B['ce_300'])} · {money(B['ce_100'])}"],
            ["second-order stochastic dominance", "A ⪰ B" if stats["A_ssd_B"] else "no", "B ⪰ A" if stats["B_ssd_A"] else "no"]]
    return table(rows, ["per creator (pooled over creators × seeds; seed-cluster 95% CI)", "Arm A", "Arm B"])


def creator_rank_section(cr, sc, S):
    d = creator_frame(cr, sc)
    rows = []
    for r in range(10):
        x = d[d.launch_rank == r]
        a, b = x[x.arm == "A"], x[x.arm == "B"]
        rows.append([r+1, f"{a.launch.mean():.0f}", money(a.fees.mean()), money(b.fees.mean()),
                     money(a.dev_pnl.mean()), money(b.dev_pnl.mean()), money(a.net.median()), money(b.net.median()),
                     pct((a.net > 0).mean()), pct((b.net > 0).mean())])
    S.setdefault("creator_rank", {})[sc] = [list(map(str, r)) for r in rows]
    return table(rows, ["launch order", "mean launch (s)", "A fees", "B fees", "A first-buy P&L", "B first-buy P&L",
                       "A median net", "B median net", "A P(net>0)", "B P(net>0)"])


def creator_sweep_section(cr, scen_list, S):
    rows = []
    for sc in scen_list:
        d = creator_frame(cr, sc)
        a, b = d[d.arm == "A"], d[d.arm == "B"]
        rows.append([sc, money(a.net.mean()), money(b.net.mean()), money(a.net.median()), money(b.net.median()),
                     pct((a.net > 0).mean()), pct((b.net > 0).mean()), pct((a.fees >= 100).mean()), pct((b.fees >= 100).mean()),
                     money(cara_ce(a.net.values, 1/300)), money(cara_ce(b.net.values, 1/300))])
    return table(rows, ["scenario", "A mean net", "B mean net", "A median net", "B median net", "A P(net>0)", "B P(net>0)",
                        "A P(fees≥$100)", "B P(fees≥$100)", "A CE (a=1/$300)", "B CE (a=1/$300)"])


def trader_section(org, sc, S, groups=("all", "early", "late", "a_winner", "a_loser", "a_bottom_half")):
    d = org[org.scenario == sc]
    rows = []
    for g in groups:
        if f"{g}_ret_mean_A" not in d:
            continue
        x = d.dropna(subset=[f"{g}_ret_mean_A"])
        rows.append([g, f"{x[f'{g}_n'].mean():.0f}", ci(x[f"{g}_ret_mean_A"], fmt=pct), ci(x[f"{g}_ret_mean_B"], fmt=pct),
                     ci(x[f"{g}_diff_mean"], fmt=pct),
                     f"{pct(x[f'{g}_pnl_A'].sum()/x[f'{g}_budget'].sum())} / {pct(x[f'{g}_pnl_B'].sum()/x[f'{g}_budget'].sum())}"
                     if f"{g}_budget" in x else "n/a",
                     f"{pct(x[f'{g}_ret_median_A'].mean())} / {pct(x[f'{g}_ret_median_B'].mean())}",
                     f"{pct(x[f'{g}_win_A'].mean())} / {pct(x[f'{g}_win_B'].mean())}", pct(x[f"{g}_b_better"].mean()),
                     f"{pct(x[f'{g}_q05_A'].mean())} / {pct(x[f'{g}_q05_B'].mean())}",
                     f"{pct(x[f'{g}_worst_A'].min())} / {pct(x[f'{g}_worst_B'].min())}",
                     f"{pct(x[f'{g}_paper_ret_mean_A'].mean())} / {pct(x[f'{g}_paper_ret_mean_B'].mean())}"])
        S.setdefault("traders", {}).setdefault(sc, {})[g] = dict(
            ret_A=float(x[f"{g}_ret_mean_A"].mean()), ret_B=float(x[f"{g}_ret_mean_B"].mean()),
            dw_A=float(x[f"{g}_pnl_A"].sum()/x[f"{g}_budget"].sum()) if f"{g}_budget" in x else None,
            dw_B=float(x[f"{g}_pnl_B"].sum()/x[f"{g}_budget"].sum()) if f"{g}_budget" in x else None,
            diff=bootstrap(x[f"{g}_diff_mean"]), win_A=float(x[f"{g}_win_A"].mean()), win_B=float(x[f"{g}_win_B"].mean()),
            b_better=float(x[f"{g}_b_better"].mean()), worst_A=float(x[f"{g}_worst_A"].min()),
            worst_B=float(x[f"{g}_worst_B"].min()), q05_A=float(x[f"{g}_q05_A"].mean()), q05_B=float(x[f"{g}_q05_B"].mean()))
    return table(rows, ["buyer group", "n/seed", "A mean return (CI)", "B mean return (CI)", "paired B−A (CI)",
                        "dollar-weighted return A / B", "median return A / B", "win rate A / B", "same buyer better in B", "p5 return A / B",
                        "worst observed A / B", "paper return at 240 min A / B"])


def shock_effect_section(so, S):
    if "shock_eff_mean_A" not in so:
        return ""
    x = so.dropna(subset=["shock_eff_mean_A"])
    rows = [["mean change in return (pct points of own budget; includes forgone gains)", ci(x.shock_eff_mean_A, fmt=pct), ci(x.shock_eff_mean_B, fmt=pct),
             ci(x.shock_eff_mean_B-x.shock_eff_mean_A, fmt=pct)],
            ["p5 change (mean over seeds)", pct(x.shock_eff_q05_A.mean()), pct(x.shock_eff_q05_B.mean()), ""],
            ["worst single bystander", pct(x.shock_eff_worst_A.min()), pct(x.shock_eff_worst_B.min()), ""],
            ["share of bystanders harmed by >1pt", pct(x.shock_harmed_A.mean()), pct(x.shock_harmed_B.mean()), ""],
            ["total bystander dollar change per seed (negative = loss)", money(x.shock_eff_dollars_A.mean()), money(x.shock_eff_dollars_B.mean()), ""]]
    S["shock_effect"] = dict(mean_A=bootstrap(x.shock_eff_mean_A), mean_B=bootstrap(x.shock_eff_mean_B),
                             worst_A=float(x.shock_eff_worst_A.min()), worst_B=float(x.shock_eff_worst_B.min()),
                             harmed_A=float(x.shock_harmed_A.mean()), harmed_B=float(x.shock_harmed_B.mean()),
                             q05_A=float(x.shock_eff_q05_A.mean()), q05_B=float(x.shock_eff_q05_B.mean()),
                             dollars_A=float(x.shock_eff_dollars_A.mean()), dollars_B=float(x.shock_eff_dollars_B.mean()),
                             n=float(x.shock_n.mean()))
    return table(rows, ["contagion effect on bystanders (shock world − same seed without shock)", "Arm A", "Arm B", "B − A"])


def downside_section(runs, scen_list, S):
    rows = []
    for sc in scen_list:
        out = [sc]
        for col in ("top_max_drawdown", "meme_mean_max_drawdown", "top_vol_hourly", "meme_mean_vol_hourly"):
            a, b = paired(runs, sc, col)
            out.append(f"{a.mean():.2f} / {b.mean():.2f}")
            S.setdefault("downside", {}).setdefault(sc, {})[col] = (float(a.mean()), float(b.mean()))
        rows.append(out)
    return table(rows, ["scenario", "max drawdown, A best token / B", "max drawdown, the meme a holder picked (mean) A / B",
                        "hourly realised vol (1-min, first 2h), A best / B", "same, picked meme mean A / B"])


def agents_section(runs, scen_list, S):
    rows = []
    for sc in scen_list:
        out = [sc]
        for col in ("sniper_pnl", "bundler_pnl", "adversary_pnl", "arb_pnl", "organic_pnl", "protocol_fees", "locked_lp"):
            a, b = paired(runs, sc, col)
            out.append(f"{money(a.mean())} / {money(b.mean())}")
        rows.append(out)
    return table(rows, ["scenario", "snipers A / B", "bundler A / B", "adversary A / B", "arbitrage A / B",
                        "all organic buyers A / B", "protocol fees A / B", "LP locked A / B"])


def wash_section(out, S):
    tr = pd.read_csv(f"{out}/wash_train.csv.gz")
    cf = pd.read_csv(f"{out}/wash_confirm.csv.gz")
    best = select_best(tr, ["share", "rank", "arm"], ["gross", "interval", "duration"])
    rows = []
    res = {}
    for _, b in best.iterrows():
        c = cf[(cf.share == b.share) & (cf["rank"] == b["rank"]) & (cf.arm == b.arm)]
        p, lo, hi = bootstrap(c.profit.values)
        res[(b.share, b["rank"], b.arm)] = (p, lo, hi)
        rows.append([f"{b.share:.0%}", int(b["rank"])+1, b.arm, f"{money(b.gross)} every {int(b.interval)}s for {int(b.duration)//60} min",
                     money(b.profit), f"{money(p)} [{money(lo)}, {money(hi)}]", pct((c.profit > 0).mean()),
                     money(c.fee_gain.mean()), money(c.dev_gain.mean()), money(c.organic_dollars_gain.mean()),
                     money(c.other_creators_fee_change.mean())])
    # also report the least-bad aggressive policy (largest volume) to show the direct cost scale
    agg = tr.groupby(["share", "arm", "gross", "interval", "duration"], as_index=False).profit.mean()
    S["wash"] = {f"{k[0]}_{k[1]}_{k[2]}": v for k, v in res.items()}
    breakeven = {}
    for arm in "AB":
        for rank in sorted(best["rank"].unique()):
            ok = [s for s in WASH_SHARES if res[(s, rank, arm)][1] > 0]
            breakeven[f"{arm}_rank{int(rank)+1}"] = min(ok) if ok else None
    S["wash_breakeven_share"] = breakeven
    full = tr.groupby(["share", "arm"]).profit.agg(["mean", "max"]).reset_index()
    t2 = table([[f"{r.share:.0%}", r.arm, money(r["mean"]), money(r["max"])] for _, r in full.iterrows()],
               ["creator share", "arm", "mean profit over the whole grid (train)", "best single policy-seed"])
    return table(rows, ["creator share of fee", "washer's launch order", "arm", "best response (train)", "train mean",
                        "confirmation mean [95% CI]", "P(profit>0)", "Δ fee income", "Δ first-buy P&L",
                        "Δ organic dollars drawn to washer", "Δ other creators' fees"]), t2


def spam_section(out, S):
    tr = pd.read_csv(f"{out}/spam_train.csv.gz")
    cf = pd.read_csv(f"{out}/spam_confirm.csv.gz")
    rows = []
    for arm in "AB":
        g = tr[tr.arm == arm].groupby(["m", "launch_time", "dev_buy"], as_index=False).gross_profit.mean()
        g["per_skin"] = g.gross_profit/g.m
        b = g.loc[g.per_skin.idxmax()]       # maximises break-even launch cost
        b0 = g.loc[g.gross_profit.idxmax()]  # maximises profit at zero launch cost
        for label, pol in (("max break-even launch cost", b), ("max profit at zero launch cost", b0)):
            c = cf[(cf.arm == arm) & (cf.m == pol.m) & (cf.launch_time == pol.launch_time) & (cf.dev_buy == pol.dev_buy)]
            per = c.gross_profit.values/pol.m
            p, lo, hi = bootstrap(per)
            rows.append([arm, label, f"{int(pol.m)} skins at {int(pol.launch_time)}s, first buy {money(pol.dev_buy)}",
                         f"{money(p)} [{money(lo)}, {money(hi)}]", money(c.gross_profit.mean()), money(c.spammer_fees.mean()),
                         money(c.honest_fee_change.mean()), money(c.honest_net_change.mean()), money(c.organic_pnl_change.mean())])
            S.setdefault("spam", {})[f"{arm}_{label}"] = dict(policy=[int(pol.m), float(pol.launch_time), float(pol.dev_buy)],
                                                             breakeven_per_skin=(p, lo, hi),
                                                             gross_profit=float(c.gross_profit.mean()))
    return table(rows, ["arm", "objective", "best response (train)", "break-even launch cost per skin (confirm, CI)",
                        "spammer gross profit at zero launch cost", "of which fees", "honest creators' fee change",
                        "honest creators' net change", "organic buyers' P&L change"])


def bundle_section(out, S):
    tr = pd.read_csv(f"{out}/bundle_train.csv.gz")
    cf = pd.read_csv(f"{out}/bundle_confirm.csv.gz")
    rows = []
    for budget in sorted(tr.budget.unique()):
        for arm in "AB":
            g = tr[(tr.arm == arm) & (tr.budget == budget)].groupby(["strategy", "tp", "hold"], as_index=False).profit.mean()
            b = g.loc[g.profit.idxmax()]
            c = cf[(cf.arm == arm) & (cf.budget == budget) & (cf.strategy == b.strategy) & (cf.tp == b.tp) & (cf.hold == b.hold)]
            first = cf[(cf.arm == arm) & (cf.budget == budget) & (cf.strategy == "first") & (cf.tp > 1e6)]
            p, lo, hi = bootstrap(c.profit.values)
            tp = "hold to end" if b.tp > 1e6 else f"TP {b.tp:g}×"
            rows.append([money(budget), arm, f"{b.strategy}, {tp}, max {int(b.hold)//60} min",
                         f"{money(p)} [{money(lo)}, {money(hi)}]", pct(p/budget), pct((c.profit > 0).mean()),
                         pct(c.share_1min.mean()), pct(first.share_1min.mean()), money(c.organic_pnl_change.mean())])
            S.setdefault("bundle", {})[f"{arm}_{int(budget)}"] = dict(policy=[b.strategy, float(b.tp), int(b.hold)],
                                                                     profit=(p, lo, hi), share_1min=float(c.share_1min.mean()),
                                                                     first_share_1min=float(first.share_1min.mean()))
    return table(rows, ["budget", "arm", "best response (train)", "confirmation profit [95% CI]", "return on budget",
                        "P(profit>0)", "share of bundled supply at +1 min (best)", "share at +1 min, launch-block bundle of meme 0 held (same budget)",
                        "organic buyers' P&L change vs no bundler"])


def build(out):
    S = {}
    md = ["# Generated tables (shared narrative study)", "",
          "All values are synthetic model outputs. Medians/means across matched seeds; 95% percentile-bootstrap CIs.", ""]
    runs = pd.read_csv(f"{out}/main_runs.csv.gz")
    cr = pd.read_csv(f"{out}/main_creators.csv.gz")
    org = pd.read_csv(f"{out}/main_organic.csv.gz")
    scen = sorted(runs.scenario.unique(), key=lambda s: float(s[1:]))
    md += ["## 1. Runner: peak paper market cap of the largest single token", runner_section(runs, scen, S), ""]
    md += ["## 1b. Paper vs recoverable", recoverable_section(runs, scen, S), ""]
    md += ["## 2. Depth at default concentration (c0.25)", depth_section(runs, "c0.25", S), ""]
    md += ["## 3. Creator earnings at default concentration (c0.25)", creator_section(cr, "c0.25", S), ""]
    for sc in ("c0", "c0.5", "c0.9"):
        md += [f"### Creator earnings, {sc}", creator_section(cr, sc, S), ""]
    md += ["### Creator earnings by launch order (c0.25)", creator_rank_section(cr, "c0.25", S), ""]
    md += ["### Creator earnings across concentration", creator_sweep_section(cr, scen, S), ""]
    md += ["## 4. Trader outcomes (c0.25)", trader_section(org, "c0.25", S), ""]
    md += ["### Trader outcomes (c0.9)", trader_section(org, "c0.9", S), ""]
    md += ["## 5. Shared downside", downside_section(runs, scen, S), ""]
    md += ["## Strategic agents", agents_section(runs, scen, S), ""]
    if os.path.exists(f"{out}/shock_runs.csv.gz"):
        sr = pd.read_csv(f"{out}/shock_runs.csv.gz")
        so = pd.read_csv(f"{out}/shock_organic.csv.gz")
        md += ["### Panic shock at 60 min in another meme (c0.25)",
               trader_section(so, "shock", S, groups=("shock_bystander", "all")), "",
               downside_section(sr, ["shock"], S), "", shock_effect_section(so, S), ""]
    for stage in ("sensitivity", "linear"):
        if os.path.exists(f"{out}/{stage}_runs.csv.gz"):
            r = pd.read_csv(f"{out}/{stage}_runs.csv.gz")
            c = pd.read_csv(f"{out}/{stage}_creators.csv.gz")
            o = pd.read_csv(f"{out}/{stage}_organic.csv.gz")
            sl = list(r.scenario.unique())
            md += [f"## Robustness: {stage}", runner_section(r, sl, S), "", recoverable_section(r, sl, S), "",
                   creator_sweep_section(c, sl, S), "", agents_section(r, sl, S), ""]
            for sc in sl:
                S.setdefault("robust_traders", {})[sc] = {}
                trader_section(o, sc, S.setdefault("_scratch", {}), groups=("all", "a_loser"))
    if os.path.exists(f"{out}/wash_confirm.csv.gz"):
        t1, t2 = wash_section(out, S)
        md += ["## Attack 2: wash trading for fee share", t1, "", t2, ""]
    if os.path.exists(f"{out}/spam_confirm.csv.gz"):
        md += ["## Attack 1: skin spam", spam_section(out, S), ""]
    if os.path.exists(f"{out}/bundle_confirm.csv.gz"):
        md += ["## Attack 3: bundling", bundle_section(out, S), ""]
    with open(f"{out}/tables.md", "w") as f:
        f.write("\n".join(md))
    S.pop("_scratch", None)
    with open(f"{out}/summary.json", "w") as f:
        json.dump(S, f, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    return S
