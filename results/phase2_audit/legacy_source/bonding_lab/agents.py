"""Synthetic agent policies; these are assumptions, not fitted market behavior."""
from dataclasses import dataclass
import numpy as np

KINDS = ("retail", "whale", "momentum", "holder", "creator", "sniper", "bundler", "cross_mev", "adversary")


@dataclass(frozen=True)
class DemandTape:
    wallets: np.ndarray
    tokens: np.ndarray
    side_draw: np.ndarray
    budgets: np.ndarray
    behavior_draw: np.ndarray


def agent_kinds(count, retail_fraction, whale_fraction):
    retail = round(count*retail_fraction)
    whales = min(count-retail, round(count*whale_fraction))
    kinds = ["retail"]*retail+["whale"]*whales
    kinds += [KINDS[2+i % 7] for i in range(count-len(kinds))]
    return np.array(kinds)


def make_tape(config):
    rng = np.random.default_rng(config.seed)
    return DemandTape(
        rng.integers(config.traders, size=config.events),
        rng.integers(config.tokens, size=config.events),
        rng.random(config.events),
        config.trade_size*np.minimum(20, rng.lognormal(-config.volatility**2/2, config.volatility, config.events)),
        rng.random(config.events),
    )


def intention(config, tape, t, kind, momentum):
    """Returns token, side, notional budget. No policy sees future random shocks."""
    token = int(tape.tokens[t])
    buy = tape.side_draw[t] < config.buy_pressure
    budget = float(tape.budgets[t])
    progress = t/max(1, config.events-1)
    if kind == "whale":
        budget *= 10
    elif kind == "momentum":
        if tape.behavior_draw[t] < .75:
            token = int(np.argmax(momentum)) if buy else int(np.argmin(momentum))
        buy = momentum[token] >= 0 if tape.behavior_draw[t] < .75 else buy
    elif kind == "holder":
        buy = tape.side_draw[t] < .95
    elif kind == "creator":
        token = int(tape.wallets[t]) % config.tokens
        buy = progress < .7 or buy
    elif kind == "sniper":
        buy = progress < .12
        budget *= 2
    elif kind == "bundler":
        token = 0
        buy = progress < .3
        budget *= 3
    elif kind == "cross_mev":
        # A coupling follower, not a claim of risk-free arbitrage. Explicit
        # pending-order strategies live in attacks.py and the frontrun scenario.
        token = (int(np.argmax(momentum))+1) % config.tokens
        buy = float(np.max(momentum)) > 0
    elif kind == "adversary":
        token = 0
        buy = progress < .35
        budget *= 4
    if config.scenario == "popular" and tape.behavior_draw[t] < .85:
        token, buy = 0, tape.side_draw[t] < .9
    elif config.scenario == "crash" and progress > .5 and tape.behavior_draw[t] < .85:
        token, buy = 0, False
    elif config.scenario == "bank_run" and progress > .5:
        buy = False
    elif config.scenario == "bundled" and kind in ("creator", "bundler", "adversary"):
        token, buy = 0, progress < .3
    return token, "buy" if buy else "sell", budget

