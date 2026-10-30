from bonding_lab.copycat.config import MarketConfig,Variant
from bonding_lab.copycat.market import run
from scripts.copycat_strict_badges import strict_run


def test_first_launch_badge_needs_no_undefined_leader_fallback():
    v=Variant(form="control",rate=0,badge=.5)
    c=MarketConfig(events=30,seed=101)
    assert strict_run(v,c)[0]==run(v,c)[0]


def test_an_unqualified_badge_does_not_steer_buyers_to_an_original_oracle():
    v=Variant(rule="threshold",threshold=1e12,form="control",rate=0,badge=.75)
    c=MarketConfig(events=30,seed=101)
    assert strict_run(v,c)[0]==run(v.control(),c)[0]
