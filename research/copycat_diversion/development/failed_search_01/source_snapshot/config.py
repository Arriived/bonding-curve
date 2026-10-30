from dataclasses import dataclass,asdict
import math


@dataclass(frozen=True)
class Variant:
    rule:str="first"
    form:str="buyer"
    rate:float=.05
    matching:str="exact"
    changes:str="fixed"
    window:float=30.
    threshold:float=100000.
    min_age:float=5.
    cooldown:float=30.
    badge:float=0.
    burn:str="lock"
    treasury_exit:str="never"
    volume_mode:str="first_buy"

    def __post_init__(self):
        if self.rule not in ("first","threshold","held","volume"):raise ValueError("Unknown leader rule")
        if self.form not in ("creator","holders","buyer","treasury","burn","control"):raise ValueError("Unknown routing")
        if self.matching not in ("exact","case","fuzzy") or self.changes not in ("fixed","flip","cooldown"):
            raise ValueError("Unknown matching/election policy")
        if not 0<=self.rate<=.1 or not 0<=self.badge<=1:raise ValueError("Invalid diversion/badge rate")
        if self.window<=0 or self.cooldown<0 or self.min_age<0 or self.threshold<=0:raise ValueError("Invalid election parameter")
        if self.burn not in ("lock","supply") or self.treasury_exit not in ("never","first"):
            raise ValueError("Unknown protocol inventory policy")
        if self.volume_mode not in ("first_buy","raw"):raise ValueError("Unknown volume definition")

    @property
    def label(self):
        rule=self.rule+(str(int(self.threshold)) if self.rule=="threshold" else str(int(self.window)) if self.rule in ("held","volume") else "")
        form=self.form+("_supply" if self.form=="burn" and self.burn=="supply" else "_exit" if self.form=="treasury" and self.treasury_exit=="first" else "")
        return f"{rule}_{form}_{round(self.rate*100)}pct_{self.matching}_{self.changes}_badge{round(self.badge*100)}"

    def control(self,badge=0):
        from dataclasses import replace
        return replace(self,form="control",rate=0,badge=badge,burn="lock",treasury_exit="never")


@dataclass(frozen=True)
class MarketConfig:
    events:int=240
    horizon:float=240.
    base_tokens:int=15
    max_spam:int=24
    seed:int=11
    p0:float=.01
    k:float=.0001
    fee:float=.003
    confusion:float=.35
    informed:float=.2
    total_demand:float=600000.
    organic_capital:float=1000000.
    attacker_capital:float=1100000.
    launch_cost:float=10.
    gas:float=.05
    exit_probability:float=.7
    leader_slippage:float=.02
    exit_order:str="random"

    def __post_init__(self):
        for key,val in asdict(self).items():
            if isinstance(val,(int,float)) and (not math.isfinite(val) or val<0):raise ValueError(f"Invalid {key}")
        if self.events<10 or self.horizon<120 or self.base_tokens<3 or self.max_spam<0:raise ValueError("Invalid market dimensions")
        if not all(0<=x<=1 for x in (self.confusion,self.informed,self.exit_probability,self.leader_slippage)):
            raise ValueError("Invalid probability")
        if self.p0<=0 or self.k<=0 or not 0<=self.fee<1:raise ValueError("Invalid curve")
        if self.exit_order not in ("random","reverse","forward"):raise ValueError("Unknown exit order")


@dataclass(frozen=True)
class Strategy:
    family:str="idle"
    ticker:str="ELON"
    copies:int=0
    start:float=2.
    pump:float=1.
    seed_budget:float=500.
    residual:float=1.
    exit_at:float=180.
    aliases:int=1
    rounds:int=1
    pulse:float=0.
    front_mode:str="optimal"
    front_scale:float=1.
    exit_on_capture:bool=False

    def __post_init__(self):
        if self.family not in ("idle","race","spam","evasion","flip","front"):raise ValueError("Unknown strategy")
        if not self.ticker or not 0<=self.residual<=1 or not 1<=self.aliases<=32 or self.copies<0 or self.rounds<1:
            raise ValueError("Invalid strategy constraints")
        for name,val in asdict(self).items():
            if isinstance(val,(int,float)) and (not math.isfinite(val) or val<0):raise ValueError(f"Invalid {name}")

    @property
    def label(self):
        import json
        return json.dumps(asdict(self),sort_keys=True,separators=(",",":"))
