import numpy as np
import pytest
from bonding_lab.copycat.matching import Matcher,normalize,near
from bonding_lab.copycat.election import Election
from bonding_lab.copycat.config import Variant
from bonding_lab.fast import FastBook


def setup(v):
    b=FastBook(3,4,.01,.0001,0,.003,1000000)
    m=Matcher(v.matching)
    for i in range(3):m.admit(i,"ELON")
    return b,Election(v,m,np.array([0.,2.,4.]),np.ones(3,dtype=bool),b)


def test_matching_boundaries_and_semantic_evasion():
    for mode in ("exact","case","fuzzy"):
        m=Matcher(mode);root=m.admit(0,"ELON")
        assert (m.admit(1,"elon")==root)==(mode!="exact")
    m=Matcher("fuzzy");root=m.admit(0,"ELON")
    for i,t in enumerate(("EL0N","ELON1"," ELON ","ELONN"),1):assert m.admit(i,t)==root
    assert m.admit(9,"ELONXX")!=root


def test_fixed_threshold_title_can_survive_dump():
    b,e=setup(Variant(rule="threshold",threshold=100000))
    b.execute(0,1,40000,"buy");e.refresh(2)
    assert e.leader(0)==1
    b.execute(0,1,40000,"sell");e.refresh(3)
    assert e.leader(0)==1 and b.q[1]==0


def test_continuous_dwell_and_cooldown():
    b,e=setup(Variant(rule="held",window=5,min_age=0,changes="cooldown",cooldown=30))
    b.execute(0,0,1000,"buy");e.refresh(0);e.refresh(5)
    assert e.leader(0)==0
    b.execute(1,1,10000,"buy");e.refresh(6);e.refresh(12)
    assert e.leader(0)==0
    e.refresh(36);assert e.leader(0)==1


def test_distinct_first_buys_reject_one_address_wash_but_not_sybils():
    b,e=setup(Variant(rule="volume",window=30,min_age=0))
    for _ in range(100):e.record(5,1,0,1000)
    e.refresh(5);assert e.leader(0) is None
    e.record(6,1,1,100);e.record(6,1,2,100);e.refresh(6)
    assert e.leader(0)==1
    assert e.vol[1]==1200
