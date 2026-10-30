"""Disclosed adaptive policy search space, with abstention in every family."""
from dataclasses import replace
from .config import Strategy

FAMILIES=("race","spam","evasion","flip","front")


def candidates(v,family):
    policies=[Strategy()]
    if family=="race":
        if v.rule=="first":return policies # later launches cannot steal an immutable oldest title
        for pump in (1.001,4.,10.):
            for residual in (0.,.000001,1.):
                policies.append(Strategy(family="race",pump=pump,residual=residual,exit_at=235,exit_on_capture=True,
                                         aliases=12,seed_budget=10000 if pump>2 else 1000))
        for start in (6.,20.,45.):
            policies.append(Strategy(family="race",start=start,pump=2.,residual=.000001,exit_at=235,exit_on_capture=True,
                                     aliases=32,seed_budget=20000))
    elif family=="spam":
        for copies in (0,6,24):
            for budget in (100.,10000.):
                for residual in (.001,1.):
                    policies.append(Strategy(family="spam",copies=copies,seed_budget=budget,residual=residual,exit_at=80. if residual<1 else 235.))
    elif family=="evasion":
        for ticker in ("ELON","elon","ELON ","EL0N","ELONN","ELONXX","ΕLΟN"):
            for copies in (0,8):
                policies.append(Strategy(family="evasion",ticker=ticker,copies=copies,seed_budget=3000.,exit_at=180.,residual=.05))
    elif family=="flip":
        if v.rule=="first":return policies
        for aliases in (3,12,32):
            for budget in (1000.,10000.):
                for residual in (.000001,1.):
                    policies.append(Strategy(family="flip",aliases=aliases,seed_budget=budget,residual=residual,
                                             rounds=1 if budget<5000 else 3,pump=1.01 if budget<5000 else 10.,
                                             pulse=max(v.window+1,v.cooldown+1 if v.changes=="cooldown" else 0),
                                             exit_at=235.,exit_on_capture=True))
    elif family=="front":
        if v.form in ("control","creator") or (v.form=="burn" and v.burn=="supply") or v.rate==0:return policies
        policies.append(Strategy(family="front",front_mode="optimal"))
        for scale in (.1,1.,10.):policies.append(Strategy(family="front",front_mode="budget",front_scale=scale))
    else:raise ValueError("Unknown attack family")
    return policies
