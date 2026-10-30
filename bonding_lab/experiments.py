"""Experiments A-H, Monte Carlo summaries, matched differences, provenance."""
from dataclasses import asdict, replace
from datetime import datetime, timezone
from decimal import Decimal
import importlib.metadata
import hashlib
import json
from pathlib import Path
import platform
import time

import numpy as np
import pandas as pd

from .attacks import bundle, frontrun
from .engine import Curve, Parameters, precise
from .simulation import Config, compare, initial_required, run


def distribution(values):
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if not len(x):
        return {"n": 0}
    std = float(x.std(ddof=1)) if len(x) > 1 else 0.
    # Normal approximation across IID seed-level outcomes, not across trades.
    half = 1.96*std/np.sqrt(len(x))
    return dict(n=len(x), mean=float(x.mean()), median=float(np.median(x)), std=std,
                q01=float(np.quantile(x,.01)), q05=float(np.quantile(x,.05)),
                q25=float(np.quantile(x,.25)), q75=float(np.quantile(x,.75)),
                q95=float(np.quantile(x,.95)), q99=float(np.quantile(x,.99)),
                min=float(x.min()), max=float(x.max()),
                mean_ci95_low=float(x.mean()-half), mean_ci95_high=float(x.mean()+half))


def monte_carlo(config, seeds=100, paired=True, basis="equal_supplies", progress=None):
    if seeds < 1:
        raise ValueError("At least one seed required")
    rows = []
    for i in range(seeds):
        current = replace(config, seed=config.seed+i)
        outcomes = compare(current, basis, record=False) if paired else {"shared": run(current, record=False)}
        for model, result in outcomes.items():
            rows.append(dict(model=model, scenario=config.scenario, basis=basis, **result.metrics))
        if progress:
            progress(i+1, seeds)
    raw = pd.DataFrame(rows)
    summaries = []
    metric_names = [k for k in raw.select_dtypes("number").columns if k != "seed"]
    for model, group in raw.groupby("model"):
        for metric in metric_names:
            summaries.append(dict(model=model, metric=metric, **distribution(group[metric])))
        if group.attack_opportunities.sum() > 0:
            successes = int((group.attacker_profit > 0).sum())
            n = len(group)
            phat = successes/n
            z = 1.96
            center = (phat+z*z/(2*n))/(1+z*z/n)
            half = z*np.sqrt(phat*(1-phat)/n+z*z/(4*n*n))/(1+z*z/n)
            summaries.append(dict(model=model,metric="probability_profitable_attack_run",n=n,
                                  mean=phat,mean_ci95_low=center-half,mean_ci95_high=center+half))
    if paired:
        a = raw[raw.model == "shared"].set_index("seed")
        b = raw[raw.model == "independent"].set_index("seed")
        for metric in metric_names:
            summaries.append(dict(model="shared_minus_independent", metric=metric,
                                  **distribution(a[metric]-b[metric])))
    return raw, pd.DataFrame(summaries)


def attack_grid():
    rows = []
    for lam in ("0", ".1", ".25", ".5", ".75", "1"):
        for fee in ("0", ".003", ".01"):
            for slip in ("0", ".02", "1"):
                for competitors in (1, 3):
                    r = frontrun(coupling=lam, fee=fee, slippage=slip, competitors=competitors)
                    r.pop("logs")
                    r.pop("individual_profits")
                    r.update(slippage=float(slip))
                    rows.append(r)
    return pd.DataFrame(rows)


def scaling():
    rows = []
    for n in (2, 10, 100, 1000):
        for lam in (0, .1, .25, .5, .75, 1):
            c = Config(tokens=n, coupling=lam)
            R = initial_required(c)
            price = c.p0+c.k*c.initial_supply*(1+lam*(n-1))
            new_price = c.p0+c.k*lam*n*c.initial_supply
            # Equal unit supplies, not an economic claim that arbitrary token
            # denominations are comparable.
            rows.append(dict(tokens=n, coupling=lam, initial_reserve=R, marginal_price=price,
                              new_token_starting_price=new_price,
                              buy_100_cost=price*100+c.k*100**2/2,
                              cross_drop_per_1000_redemption=c.k*lam*1000,
                              own_slope=c.k, cross_slope=c.k*lam))
    return pd.DataFrame(rows)


def scaling_simulations():
    """Executed markets at all four requested sizes, with timing observations."""
    rows = []
    for n in (2,10,100,1000):
        for lam in (0,.25,1):
            for seed in (42,43,44):
                config = Config(tokens=n,coupling=lam,seed=seed,events=1000)
                start = time.perf_counter()
                result = run(config,record=False)
                rows.append(dict(tokens=n,coupling=lam,elapsed_seconds=time.perf_counter()-start,**result.metrics))
    return pd.DataFrame(rows)


def growth():
    rows = []
    for n in (2, 10, 100, 1000):
        for lam in (0, .1, .25, .5, .75, 1):
            c = Config(tokens=n, coupling=lam)
            price = c.p0+c.k*c.initial_supply*(1+lam*(n-1))
            for multiple in (2, 10, 100):
                for source in ("own", "other"):
                    slope = c.k if source == "own" else c.k*lam
                    if slope == 0:
                        continue
                    d = (multiple-1)*price/slope
                    capital = price*d+c.k*d*d/2
                    # Final global reserve and aggregate cap, no fees in this
                    # mathematical experiment. Holdings unchanged on target when
                    # source=other, yet target quoted cap rises.
                    initial_r = initial_required(c)
                    Q = n*c.initial_supply+d
                    final_r = initial_r+capital
                    mcap = 2*final_r-c.p0*Q
                    rows.append(dict(tokens=n, coupling=lam, price_multiple=multiple, source=source,
                                      target_start_price=price, issued_quantity=d, external_capital=capital,
                                      initial_required=initial_r, final_collective_liquidation=final_r,
                                      final_quoted_market_cap=mcap))
    return pd.DataFrame(rows)


@precise
def bank_run_orders(seeds=30):
    rows = []
    for lam in ("0", ".25", "1"):
        for seed in range(seeds):
            c = Curve(Parameters(coupling=lam, fee_rate="0"))
            for i in range(10):
                c.create_token(str(i))
                c.create_wallet(str(i), "1e6")
            for i in range(10):
                c.execute(str(i), i, 1000, "buy")
            reserve = c.reserve
            order = np.random.default_rng(seed).permutation(10)
            receipts = []
            for position, token in enumerate(order):
                tx = c.execute(str(token), int(token), 1000, "sell")
                receipts.append(tx.gross)
                rows.append(dict(coupling=float(lam), seed=seed, exit_position=position,
                                  token=int(token), proceeds=float(tx.gross),
                                  realized_pnl=float(c.wallets[str(token)].realized_pnl),
                                  remaining_reserve=float(c.reserve)))
            assert sum(receipts, Decimal(0)) == reserve
            assert c.reserve == 0
            c.assert_invariants()
    return pd.DataFrame(rows)


@precise
def controlled_spillover():
    rows = []
    for lam in ("0", ".1", ".25", ".5", ".75", "1"):
        c = Curve(Parameters(coupling=lam, fee_rate="0"))
        for i in range(10):
            c.create_token(str(i))
        c.create_wallet("lp", "1e9")
        for i in range(10):
            c.execute("lp", i, 1000, "buy")
        before = c.price(1)
        buy = c.execute("lp", 0, 10000, "buy")
        after = c.price(1)
        crash = c.execute("lp", 0, 11000, "sell")
        rows.append(dict(coupling=float(lam), other_start_price=float(before),
                          other_after_popular_price=float(after),
                          spillover=float(after-before), own_demand_in_other=0,
                          popular_buy_cost=float(buy.gross), crash_proceeds=float(crash.gross),
                          other_price_after_full_crash=float(c.price(1)),
                          other_crash_drop=float(after-c.price(1)), reserve_after=float(c.reserve)))
        c.assert_invariants()
    return pd.DataFrame(rows)


def bundle_grid():
    return pd.DataFrame([bundle(sequence, order, lam, fee, victim)
                         for sequence in ((0,0,0,0), (0,1,0,1), (0,0,1,1))
                         for order in ("forward", "reverse")
                         for lam in ("0", ".25", "1")
                         for fee in ("0", ".003") for victim in (0,1000)])


def provenance(config, **extra):
    return dict(created_utc=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
                packages={p:importlib.metadata.version(p) for p in ("numpy","pandas","plotly","streamlit","pytest","hypothesis")},
                config=asdict(config), synthetic=True,
                source_sha256={str(p.relative_to(Path(__file__).parent.parent)):hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted(Path(__file__).parent.glob("*.py"))},
                intervals="95% normal approximation of IID seed means; paired differences use matched seed outcomes",
                **extra)


def research_suite(output, config, seeds=100, scenarios=("baseline","popular","crash","bundled","frontrun","bank_run"), bases=("equal_supplies","equal_capital")):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    manifest = provenance(config, seeds=seeds, scenarios=list(scenarios), bases=list(bases), status="running")
    (output/"manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    completed = []
    try:
        for scenario in scenarios:
            for basis in bases:
                print(f"{scenario} / {basis}: {seeds} seeds x {config.events} events x 2 models", flush=True)
                raw, summary = monte_carlo(replace(config,scenario=scenario), seeds, basis=basis)
                stem = scenario+"_"+basis
                raw.to_csv(output/(stem+"_runs.csv"), index=False)
                summary.to_csv(output/(stem+"_summary.csv"), index=False)
                completed.append(stem)
        for name, fn in (("attack_grid",attack_grid), ("scaling",scaling), ("growth",growth),
                         ("bank_run_orders",bank_run_orders), ("controlled_spillover",controlled_spillover),
                         ("bundle_grid",bundle_grid), ("scaling_simulations",scaling_simulations)):
            fn().to_csv(output/(name+".csv"),index=False)
            completed.append(name)
        manifest["status"] = "complete"
    except BaseException as exc:
        manifest.update(status="failed", failure=repr(exc))
        raise
    finally:
        manifest.update(completed=completed, elapsed_seconds=time.perf_counter()-start)
        (output/"manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
