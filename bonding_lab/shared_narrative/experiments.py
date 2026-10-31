"""Matched-seed experiments: main comparison, sensitivities and adaptive attacks.

Every task builds one tape per seed and runs it in both arms. Attack tasks also
run the same seed without the attack, so profits are incremental.
"""
from dataclasses import replace
import json
import multiprocessing as mp
import os
import time

import numpy as np
import pandas as pd

from .tape import Config, make_tape
from .world import run_arm

MAIN_SEEDS = range(1000, 1300)
SMALL_SEEDS = range(1000, 1150)
TRAIN_SEEDS = range(0, 40)
CONFIRM_SEEDS = range(5000, 5200)
CONCENTRATIONS = (0.0, .25, .5, .75, .9, 1.0)
RET_BINS = np.linspace(-1.1, 20, 4221)
GROUPS = ("all", "early", "late", "a_winner", "a_loser", "a_bottom_half")

WASH_GRID = [(g, every, dur) for g in (100.0, 500.0, 2000.0) for every in (30, 120) for dur in (600, 3600)]
WASH_RANKS = (0, 4, 9)
WASH_SHARES = (.3, .5, .7, .9, 1.0)
SPAM_GRID = [(m, ts, dev) for m in (1, 3, 10, 30) for ts in (120.0, 600.0) for dev in (0.0, 50.0)]
BUNDLE_GRID = [(strategy, b, tp, hold) for b in (500.0, 2000.0, 8000.0) for strategy in ("first", "spread", "leader5")
               for tp, hold in ((1.5, 600), (3.0, 1800), (6.0, 7200), (1e9, 14400))]


# ---------------------------------------------------------------- summaries
def group_masks(tape, ra):
    org = ra["organic"]
    t = org["time"]
    peaks = ra["creators"]["peak"]
    winner = int(np.argmax(peaks))
    bottom = np.flatnonzero(peaks < np.median(peaks))
    pick = org["pick"]
    return dict(all=np.ones(len(t), bool), early=t < 600, late=t >= 3600, a_winner=pick == winner,
                a_loser=pick != winner, a_bottom_half=np.isin(pick, bottom))


def organic_summary(tape, ra, rb, masks):
    out, hist = {}, {}
    b = ra["organic"]["budget"]
    for g, mask in masks.items():
        pa, pb = ra["organic"]["pnl"][mask], rb["organic"]["pnl"][mask]
        if not mask.any():
            continue
        x, y = pa/b[mask], pb/b[mask]
        out.update({f"{g}_n": int(mask.sum()), f"{g}_ret_mean_A": float(x.mean()), f"{g}_ret_mean_B": float(y.mean()),
                    f"{g}_ret_median_A": float(np.median(x)), f"{g}_ret_median_B": float(np.median(y)),
                    f"{g}_win_A": float((pa > 0).mean()), f"{g}_win_B": float((pb > 0).mean()),
                    f"{g}_worst_A": float(x.min()), f"{g}_worst_B": float(y.min()),
                    f"{g}_q05_A": float(np.quantile(x, .05)), f"{g}_q05_B": float(np.quantile(y, .05)),
                    f"{g}_diff_mean": float((y-x).mean()), f"{g}_b_better": float((pb > pa+1e-9).mean()),
                    f"{g}_pnl_A": float(pa.sum()), f"{g}_pnl_B": float(pb.sum()),
                    f"{g}_budget": float(b[mask].sum()),
                    f"{g}_paper_ret_mean_A": float((ra["organic"]["paper"][mask]/b[mask]).mean()),
                    f"{g}_paper_ret_mean_B": float((rb["organic"]["paper"][mask]/b[mask]).mean())})
        hist[g] = (np.histogram(np.clip(x, RET_BINS[0], RET_BINS[-1]), RET_BINS)[0],
                   np.histogram(np.clip(y, RET_BINS[0], RET_BINS[-1]), RET_BINS)[0])
    return out, hist


def pair_task(args):
    name, kw, seed = args
    tape = make_tape(Config(seed=seed, **kw))
    ra, rb = run_arm(tape, "A"), run_arm(tape, "B")
    rows = []
    for arm, r in (("A", ra), ("B", rb)):
        rows.append(dict(scenario=name, **r["metrics"]))
    creators = []
    order = np.argsort(tape.launch[:tape.config.n_memes], kind="stable")
    rank = np.empty_like(order)
    rank[order] = np.arange(len(order))
    for arm, r in (("A", ra), ("B", rb)):
        cr = r["creators"]
        for j in range(len(cr["fees"])):
            creators.append(dict(scenario=name, seed=seed, arm=arm, creator=j, launch_rank=int(rank[j]),
                                 launch=float(cr["launch"][j]), fees=float(cr["fees"][j]),
                                 fees_buy=float(cr["fees_buy"][j]),
                                 dev_pnl=float(cr["dev_pnl"][j]), net=float(cr["fees"][j]+cr["dev_pnl"][j]),
                                 buy_dollars=float(cr["buy_dollars"][j]), meme_peak=float(cr["peak"][j])))
    masks = group_masks(tape, ra)
    if tape.config.shock:
        masks["shock_bystander"] = ra["organic"]["shocked"] & rb["organic"]["shocked"]
    org, hist = organic_summary(tape, ra, rb, masks)
    org.update(scenario=name, seed=seed)
    if tape.config.shock:
        # Counterfactual: the same seed without the shock. The effect on a bystander
        # (holder of another meme, open at the shock in both arms) is pure contagion.
        base = make_tape(Config(seed=seed, **{**kw, "shock": False}))
        ba, bb = run_arm(base, "A"), run_arm(base, "B")
        m = masks["shock_bystander"]
        bud = ra["organic"]["budget"][m]
        da = (ra["organic"]["pnl"][m]-ba["organic"]["pnl"][m])/bud
        db = (rb["organic"]["pnl"][m]-bb["organic"]["pnl"][m])/bud
        if m.any():
            org.update(shock_n=int(m.sum()), shock_eff_mean_A=float(da.mean()), shock_eff_mean_B=float(db.mean()),
                       shock_eff_q05_A=float(np.quantile(da, .05)), shock_eff_q05_B=float(np.quantile(db, .05)),
                       shock_eff_worst_A=float(da.min()), shock_eff_worst_B=float(db.min()),
                       shock_harmed_A=float((da < -.01).mean()), shock_harmed_B=float((db < -.01).mean()),
                       shock_eff_dollars_A=float((ra["organic"]["pnl"][m]-ba["organic"]["pnl"][m]).sum()),
                       shock_eff_dollars_B=float((rb["organic"]["pnl"][m]-bb["organic"]["pnl"][m]).sum()))
    return dict(rows=rows, creators=creators, organic=org, hist=hist)


def wash_task(args):
    seed, share, rank, grid = args
    base_kw = dict(creator_share=share)
    out = []
    base = make_tape(Config(seed=seed, **base_kw))
    target = int(np.argsort(base.launch[:base.config.n_memes], kind="stable")[rank])
    ref = {arm: run_arm(base, arm) for arm in "AB"}
    for g, every, dur, arms in grid:
        tape = make_tape(Config(seed=seed, wash=(rank, g, every, dur), **base_kw))
        for arm in arms:
            r = run_arm(tape, arm)
            fee_gain = r["creators"]["fees"][target]-ref[arm]["creators"]["fees"][target]
            dev_gain = r["creators"]["dev_pnl"][target]-ref[arm]["creators"]["dev_pnl"][target]
            out.append(dict(seed=seed, share=share, rank=rank, gross=g, interval=every, duration=dur, arm=arm,
                            rounds=r["metrics"]["wash_rounds"], fee_gain=fee_gain, dev_gain=dev_gain,
                            profit=fee_gain+dev_gain,
                            organic_dollars_gain=float(tape.meme_buy_dollars[target]-base.meme_buy_dollars[target]
                                                       - r["metrics"]["wash_rounds"]*g),
                            other_creators_fee_change=float(r["creators"]["fees"].sum()-r["creators"]["fees"][target]
                                                            - ref[arm]["creators"]["fees"].sum()
                                                            + ref[arm]["creators"]["fees"][target])))
    return out


def spam_task(args):
    seed, = args
    base = make_tape(Config(seed=seed))
    n = base.config.n_memes
    ref = {arm: run_arm(base, arm) for arm in "AB"}
    out = []
    for m, ts, dev in SPAM_GRID:
        tape = make_tape(Config(seed=seed, spam=(m, ts, dev, 2.0)))
        spam_buyers = tape.org_pick >= n
        for arm in "AB":
            r = run_arm(tape, arm)
            mt = r["metrics"]
            out.append(dict(seed=seed, m=m, launch_time=ts, dev_buy=dev, arm=arm,
                            spammer_fees=mt["spammer_fees"], spammer_trading_pnl=mt["spammer_pnl"],
                            gross_profit=mt["spammer_fees"]+mt["spammer_pnl"],
                            honest_fee_change=float(r["creators"]["fees"].sum()-ref[arm]["creators"]["fees"].sum()),
                            honest_net_change=float((r["creators"]["fees"]+r["creators"]["dev_pnl"]).sum()
                                                    - (ref[arm]["creators"]["fees"]+ref[arm]["creators"]["dev_pnl"]).sum()),
                            spam_buyer_dollars=float(r["organic"]["budget"][spam_buyers].sum()),
                            spam_buyer_pnl=float(r["organic"]["pnl"][spam_buyers].sum()),
                            organic_pnl_change=mt["organic_pnl"]-ref[arm]["metrics"]["organic_pnl"]))
    return out


def bundle_task(args):
    seed, = args
    out = []
    base = make_tape(Config(seed=seed, bundle=()))
    ref = {arm: run_arm(base, arm)["metrics"] for arm in "AB"}
    for strategy, b, tp, hold in BUNDLE_GRID:
        tape = make_tape(Config(seed=seed, bundle=(strategy, b, tp, hold)))
        for arm in "AB":
            mt = run_arm(tape, arm)["metrics"]
            out.append(dict(seed=seed, strategy=strategy, budget=b, tp=tp, hold=hold, arm=arm,
                            profit=mt["bundler_pnl"], share_1min=mt["bundler_share_1min"],
                            organic_pnl_change=mt["organic_pnl"]-ref[arm]["organic_pnl"]))
    return out


def select_best(frame, by, policy, value="profit"):
    """Best response: the policy with the highest mean profit on training seeds."""
    means = frame.groupby(by+policy, as_index=False)[value].mean()
    idx = means.groupby(by)[value].idxmax()
    return means.loc[idx].reset_index(drop=True)


# ---------------------------------------------------------------- runners
def pool_map(fn, tasks, workers):
    if workers <= 1:
        return [fn(t) for t in tasks]
    with mp.get_context("fork").Pool(workers) as pool:
        return pool.map(fn, tasks, chunksize=max(1, len(tasks)//(workers*8)))


def run_pairs(name, kw, seeds, workers):
    res = pool_map(pair_task, [(name, kw, s) for s in seeds], workers)
    rows = pd.DataFrame([r for x in res for r in x["rows"]])
    creators = pd.DataFrame([r for x in res for r in x["creators"]])
    organic = pd.DataFrame([x["organic"] for x in res])
    hist = {}
    for x in res:
        for g, (ha, hb) in x["hist"].items():
            if g not in hist:
                hist[g] = [np.zeros_like(ha), np.zeros_like(hb)]
            hist[g][0] += ha
            hist[g][1] += hb
    return rows, creators, organic, hist


PAIR_STAGES = {
    "main": [(f"c{c:g}", dict(concentration=c), MAIN_SEEDS) for c in CONCENTRATIONS],
    "linear": [(f"linear_c{c:g}", dict(shape="linear", concentration=c), SMALL_SEEDS) for c in (0.0, .25, .5, 1.0)],
    "shock": [("shock", dict(shock=True), MAIN_SEEDS)],
    "sensitivity": [("demand0.5", dict(demand_scale=.5), SMALL_SEEDS), ("demand2", dict(demand_scale=2.0), SMALL_SEEDS),
                    ("patient_tp2", dict(tp_scale=2.0), SMALL_SEEDS), ("no_exits", dict(organic_exits=False), SMALL_SEEDS),
                    ("share0.5", dict(creator_share=.5), SMALL_SEEDS)],
}


def save(df, path):
    if path.endswith(".gz"):
        df.to_csv(path, index=False, compression="gzip")
    else:
        df.to_csv(path, index=False)


def run_stage(stage, out, workers=4, quick=False):
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    manifest = dict(stage=stage, quick=quick, workers=workers, default_config=Config().__dict__)
    if stage in PAIR_STAGES:
        all_rows, all_cr, all_org, hists = [], [], [], {}
        for name, kw, seeds in PAIR_STAGES[stage]:
            seeds = list(seeds)[:8] if quick else list(seeds)
            rows, cr, org, hist = run_pairs(name, kw, seeds, workers)
            all_rows.append(rows); all_cr.append(cr); all_org.append(org)
            hists[name] = {g: [h[0].tolist(), h[1].tolist()] for g, h in hist.items()}
            manifest.setdefault("scenarios", {})[name] = dict(overrides=kw, seeds=[seeds[0], seeds[-1]], n=len(seeds))
        save(pd.concat(all_rows), f"{out}/{stage}_runs.csv.gz")
        save(pd.concat(all_cr), f"{out}/{stage}_creators.csv.gz")
        save(pd.concat(all_org), f"{out}/{stage}_organic.csv.gz")
        with open(f"{out}/{stage}_return_hist.json", "w") as f:
            json.dump(dict(bins=RET_BINS.tolist(), hist=hists), f)
    elif stage in ("wash", "spam", "bundle"):
        for phase, seeds in (("train", TRAIN_SEEDS), ("confirm", CONFIRM_SEEDS)):
            seeds = list(seeds)[:4] if quick else list(seeds)
            if stage == "wash":
                if phase == "train":
                    full = [(g, e, d, "AB") for g, e, d in WASH_GRID]
                    tasks = [(s, sh, rk, full) for s in seeds for sh in WASH_SHARES for rk in WASH_RANKS]
                else:   # confirmation runs only the best response frozen on training seeds
                    best = select_best(train, ["share", "rank", "arm"], ["gross", "interval", "duration"])
                    manifest["wash_frozen_best"] = best.to_dict("records")
                    tasks = []
                    for sh in WASH_SHARES:
                        for rk in WASH_RANKS:
                            pol = []
                            for arm in "AB":
                                b = best[(best.share == sh) & (best["rank"] == rk) & (best.arm == arm)].iloc[0]
                                pol.append((b.gross, int(b.interval), int(b.duration), arm))
                            tasks += [(s, sh, rk, pol) for s in seeds]
                fn = wash_task
            else:
                tasks = [(s,) for s in seeds]
                fn = spam_task if stage == "spam" else bundle_task
            res = pool_map(fn, tasks, workers)
            frame = pd.DataFrame([r for x in res for r in x])
            if phase == "train":
                train = frame
            save(frame, f"{out}/{stage}_{phase}.csv.gz")
            manifest[f"{phase}_seeds"] = [seeds[0], seeds[-1], len(seeds)]
        manifest["grid"] = dict(wash=WASH_GRID, wash_ranks=WASH_RANKS, wash_shares=WASH_SHARES,
                                spam=SPAM_GRID, bundle=BUNDLE_GRID)[stage] if stage != "wash" else \
            dict(grid=WASH_GRID, ranks=WASH_RANKS, shares=WASH_SHARES)
    else:
        raise ValueError(f"Unknown stage {stage}")
    manifest["elapsed_s"] = round(time.time()-t0, 2)
    with open(f"{out}/{stage}_manifest.json", "w") as f:
        json.dump(manifest, f, indent=1, default=str)
    return manifest
