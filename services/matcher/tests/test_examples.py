"""The research matcher's 14 worked examples, as regression tests of the port.

Each example runs through (a) the research matcher itself, which must still match its recorded
expectation, and (b) the service's decide(). For the 12 pre-graduation examples the service must reach
the same decision and room. The two graduated examples (08, 09) exercise a post-graduation pool path
that v1 does not have: the service excludes graduated rooms as routing targets, so both are new rooms,
and that policy is asserted explicitly rather than skipped.
"""
import copy

import pytest
from conftest import load_examples, research_matcher, snapshot_from_example

from matcher_service.decide import decide

EXAMPLES = load_examples()
GRADUATED = {"08_graduated_live_by_pool_fees", "09_graduated_stale_checkpoint"}


def test_there_are_fourteen_examples():
    assert len(EXAMPLES) == 14


@pytest.mark.parametrize("name,inp", EXAMPLES, ids=[n for n, _ in EXAMPLES])
def test_research_matcher_still_meets_its_expectation(name, inp):
    inp = copy.deepcopy(inp)
    exp = inp.pop("expect")
    out = research_matcher().decide(inp)
    assert (out["decision"], out.get("room_id")) == (exp["decision"], exp["room_id"])


@pytest.mark.parametrize("name,inp", EXAMPLES, ids=[n for n, _ in EXAMPLES])
def test_service_decision(name, inp):
    inp = copy.deepcopy(inp)
    exp = inp.pop("expect")
    c = inp["candidate"]
    d = decide(snapshot_from_example(inp), c["name"], c["symbol"], c.get("uri", ""))
    if name in GRADUATED:
        assert d.kind == "new_room", "v1 never routes into a graduated room"
        assert all(not r["live"] for r in d.evaluated)
        return
    assert (d.kind, d.room_id) == ({"door": "door", "new_room": "new_room"}[exp["decision"]], exp["room_id"])
    if d.kind == "door":
        assert d.rule in ("T3", "T2n")
