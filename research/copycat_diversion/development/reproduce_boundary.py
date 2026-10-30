from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from bonding_lab.copycat.market import Market
from bonding_lab.copycat.config import Variant,MarketConfig
from bonding_lab.copycat.attacks import candidates
failures=[]
for form in ("creator","holders","buyer","burn"):
    for rate in (.01,.03,.05,.1):
        v=Variant(rule="volume",window=5,form=form,rate=rate)
        for strategy in candidates(v,"flip"):
            for seed in (11,22):
                market=Market(v,MarketConfig(events=160,seed=seed),strategy)
                try:market.run()
                except Exception as exc:
                    failures.append(dict(variant=v.label,strategy=strategy.label,seed=seed,error=str(exc),
                                         source_cash=float(market.book.cash[market.attack[0]]),
                                         min_cash=float(market.book.cash.min())))
print(json.dumps(failures,indent=2))
(Path(__file__).parent/"postfix_boundary_validation.json").write_text(json.dumps(dict(cases=416,failures=failures),indent=2),encoding="utf-8")
assert not failures,"Boundary regression remains unresolved"
