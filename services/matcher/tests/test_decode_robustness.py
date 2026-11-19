"""The decoder must never raise on a malformed transaction: it reads whatever an RPC returns.

watcher.decode is research-collector code; the production matcher service does not import it. But a single
malformed transaction used to end a multi-hour collection run, because _instructions is a generator consumed by
a `for` statement in launches_from_tx, so anything raised inside it escaped that function's own try/except.
Twelve shapes were probed and eleven raised (CORRECTIONS section 33). All are pinned here.
"""
import pytest

from watcher import decode as D


def tx(**over):
    base = {"transaction": {"message": {"accountKeys": ["A", "B"], "instructions": []}}, "meta": {"err": None}}
    base.update(over)
    return base


def with_ix(ix):
    return {"transaction": {"message": {"accountKeys": ["A", "B"], "instructions": [ix]}}, "meta": {"err": None}}


@pytest.mark.parametrize("bad", [
    pytest.param({"meta": {"err": None}}, id="no transaction"),
    pytest.param({"transaction": {}, "meta": {"err": None}}, id="no message"),
    pytest.param({"transaction": {"message": {"instructions": []}}, "meta": {"err": None}}, id="no accountKeys"),
    pytest.param({"transaction": {"message": {"accountKeys": []}}, "meta": {"err": None}}, id="no instructions"),
    pytest.param(with_ix({"programIdIndex": 99, "accounts": [0], "data": "1"}), id="programIdIndex overruns"),
    pytest.param(with_ix({"programIdIndex": 0, "accounts": [99], "data": "1"}), id="account index overruns"),
    pytest.param(with_ix({"programIdIndex": 0, "accounts": [0], "data": "!!!"}), id="data is not base58"),
    pytest.param(with_ix({"programIdIndex": 0, "accounts": [0]}), id="no data"),
    pytest.param(with_ix({"programIdIndex": 0, "data": "1"}), id="no accounts"),
    pytest.param(with_ix("not even a dict"), id="instruction is not a dict"),
    pytest.param(tx(meta={"err": None, "innerInstructions": [{"nope": 1}]}), id="inner malformed"),
    pytest.param(tx(meta={"err": None, "loadedAddresses": "oops"}), id="loadedAddresses not a dict"),
    pytest.param({}, id="empty dict"),
])
def test_malformed_transactions_yield_nothing_and_never_raise(bad):
    assert D.launches_from_tx(bad) == []


def test_none_and_failed_transactions():
    assert D.launches_from_tx(None) == []
    assert D.launches_from_tx(tx(meta={"err": {"InstructionError": [0, "x"]}})) == []


def test_a_v0_transaction_with_unresolved_lookup_tables_is_skipped_not_fatal():
    """The realistic trigger: the key list is short because loadedAddresses came back empty, so every index
    overruns. Yielding nothing is right; ending the run is not."""
    t = {"transaction": {"message": {"accountKeys": ["A"],
                                     "instructions": [{"programIdIndex": 7, "accounts": [7], "data": "1"}]}},
         "meta": {"err": None, "loadedAddresses": {"writable": [], "readonly": []}}}
    assert D.launches_from_tx(t) == []


def test_b58decode_raises_value_error_not_key_error():
    """So a caller catching ValueError catches it. A KeyError used to escape every such handler."""
    with pytest.raises(ValueError):
        D.b58decode("!!!")
    assert D.b58decode("1") == b"\x00"


def test_valid_decoding_still_works():
    """The hardening must not have made the decoder skip real launches: round-trip a known key."""
    assert D.b58encode(D.b58decode("11111111111111111111111111111111")) == "11111111111111111111111111111111"
