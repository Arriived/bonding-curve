import base64
import sys
from pathlib import Path

import pytest
from solders.keypair import Keypair
from solders.message import MessageV0, from_bytes_versioned, to_bytes_versioned
from solders.signature import Signature
from solders.transaction import VersionedTransaction

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import max_uri
import verify_decision
from conftest import PROGRAM
from test_failures import FakeRpc, LOOKUP_TABLE, REQ, Snap, lookup_account, make, rows
from matcher_service import txbuild
from matcher_service.decide import Refusal, decide
from matcher_service.lookup_table import LookupTableError, expected_addresses, load_frozen_table, loaded_addresses


@pytest.mark.parametrize("shape,valid,first_wire_overflow", [
    ("create_room", 200, 202),
    ("create_room_takeover", 169, 170),
    ("create_room_name_takeover", 169, 170),
    ("create_room_both_takeovers", 137, 138),
])
def test_builder_uri_boundaries(shape, valid, first_wire_overflow):
    builder = txbuild.Builder(PROGRAM)
    payer, matcher = Keypair().pubkey(), Keypair().pubkey()
    shapes, _ = max_uri.shapes(builder, payer, matcher)
    alt = max_uri.static_alt(builder)

    def message(size):
        return txbuild.build_message(shapes[shape]("u" * size), payer, max_uri.BLOCKHASH, 400_000, 1, alt)

    assert isinstance(message(valid), MessageV0)
    assert txbuild.wire_size(message(valid)) <= txbuild.PACKET_LIMIT
    assert txbuild.wire_size(message(first_wire_overflow - 1)) == txbuild.PACKET_LIMIT
    with pytest.raises(txbuild.TxTooLarge):
        txbuild.assemble(message(first_wire_overflow), matcher, bytes(Signature.default()))
    if shape == "create_room":
        with pytest.raises(Refusal, match="uri"):
            decide(Snap(1000), max_uri.NAME, max_uri.SYMBOL, "u" * (valid + 1))


def test_frozen_table_matches_the_exact_ordered_addresses():
    table, slot = load_frozen_table(FakeRpc(), LOOKUP_TABLE, PROGRAM)
    assert table.key == LOOKUP_TABLE
    assert list(table.addresses) == expected_addresses(PROGRAM)
    assert slot == 1000


@pytest.mark.parametrize("account", [
    lookup_account(authority=Keypair().pubkey()),
    lookup_account(deactivation_slot=3),
    lookup_account(last_extended_slot=1000),
    lookup_account(addresses=list(reversed(expected_addresses(PROGRAM)))),
    lookup_account(addresses=[*expected_addresses(PROGRAM), Keypair().pubkey()]),
    {"context": {"slot": 1000}, "value": None},
])
def test_invalid_lookup_table_refuses_to_sign_or_record(tmp_path, kp, account):
    rpc = FakeRpc()
    rpc.call = lambda method, params: account
    with pytest.raises(LookupTableError):
        load_frozen_table(rpc, LOOKUP_TABLE, PROGRAM)
    service = make(tmp_path, kp, Snap(1000), rpc=rpc)
    with pytest.raises(Refusal) as exc:
        service.route(dict(REQ))
    assert exc.value.code == "inconsistent_state"
    assert rows(service) == 0
    assert not service.health()["ready"]


def test_verifier_resolves_signed_and_landed_v0_keys():
    builder = txbuild.Builder(PROGRAM)
    payer, matcher = Keypair(), Keypair()
    shapes, _ = max_uri.shapes(builder, payer.pubkey(), matcher.pubkey())
    alt = max_uri.static_alt(builder)
    ix = shapes["create_room_both_takeovers"]("u" * 137)
    msg = txbuild.build_message(ix, payer.pubkey(), max_uri.BLOCKHASH, 400_000, 1, alt)
    signed = to_bytes_versioned(msg)
    decoded = from_bytes_versioned(signed)
    loaded = loaded_addresses(decoded, alt)
    kind, _, accounts, launch = verify_decision.decode_launch_ix(
        decoded, PROGRAM, txbuild.IDL_PATH, loaded[0] + loaded[1])
    assert kind == "create_room"
    assert launch["uri"] == "u" * 137
    assert accounts["config"] == str(builder.p(b"config"))
    assert accounts["classic_token_program"] == str(txbuild.CLASSIC)
    assert accounts["wsol_mint"] == str(txbuild.WSOL)
    assert accounts["old_holder"] != accounts["old_name_holder"]
    tx = VersionedTransaction(msg, [payer, matcher])
    result = {"transaction": [base64.b64encode(bytes(tx)).decode(), "base64"],
              "meta": {"loadedAddresses": {"writable": [], "readonly": [str(key) for key in loaded[1]]}}}
    assert verify_decision.landed_message_matches(result, signed, loaded)
    result["meta"]["loadedAddresses"]["readonly"].reverse()
    assert not verify_decision.landed_message_matches(result, signed, loaded)
