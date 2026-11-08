"""Paired program parity and signed-request regressions; no network."""
import concurrent.futures

import pytest

from conftest import config, curve_state
from matcher_service import auth, quote
from solders.keypair import Keypair


def test_first_buy_is_in_door_tokens_against_sbf_vector():
    # review_door_open_front_run.json, room seeded with 10.1 SOL gross.
    curve = dict(curve_state(10_000_000_000, pending=60_000_000), status=0, reserve=10_000_000_000)
    assert quote.first_buy_tokens(curve, 1_010_000_000) == 33_699_309_828_108


def test_room_price_limit_uses_pre_settlement_price_and_slippage():
    curve = curve_state(10_000_000_000, pending=3_000_000)
    num = curve['v_sol_lamports'] * curve['v_tok']
    den = (curve['v_tok'] - curve['sold']) ** 2
    assert quote.room_price_limit(curve, 200) == num * 10**18 * 10200 // (den * 10000)


@pytest.mark.parametrize('field,value', [
    ('launcher', '11111111111111111111111111111111'), ('name', 'Altered'),
    ('symbol', 'ALT'), ('uri', 'https://example.invalid/changed'),
    ('first_buy_lamports', 102), ('min_tokens_out', 99), ('max_slippage_bps', 300),
    ('max_fee_lamports', 9), ('cu_price_micro_lamports', 2), ('issued_at', 1001),
    ('max_room_price', '987654321'),
])
def test_every_signed_field_refuses_alteration(field, value):
    # Signature verification must fail before the signature enters the replay set.
    wallet = Keypair()
    request = auth.sign(wallet, dict(launcher=str(wallet.pubkey()), name='Original', symbol='ORG',
        uri='', first_buy_lamports=101, min_tokens_out=1, max_slippage_bps=200,
        max_fee_lamports=0, cu_price_micro_lamports=0, issued_at=1000))
    verifier = auth.Verifier()
    with pytest.raises(auth.AuthError, match='signature'):
        verifier.verify(dict(request, **{field: value}), now=1000)
    assert verifier.verify(request, now=1000) == str(wallet.pubkey())
    with pytest.raises(auth.AuthError, match='already used'):
        verifier.verify(request, now=1000)


def test_concurrent_replays_accept_exactly_once():
    wallet = Keypair()
    request = auth.sign(wallet, dict(launcher=str(wallet.pubkey()), name='Replay', symbol='R', issued_at=1000))
    verifier = auth.Verifier()
    def attempt(_):
        try:
            verifier.verify(request, now=1000)
            return True
        except auth.AuthError:
            return False
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(attempt, range(32))) == 1


def test_independent_verifier_quotes_both_legs_and_pending_fees():
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / 'scripts/verify_decision.py'
    spec = importlib.util.spec_from_file_location('paired_verifier', path)
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    for reserve in (0, 500_000_000, 10_000_000_000, 80_000_000_000):
        for pending in (0, 60_000_000, 3_000_000):
            curve = dict(curve_state(reserve, pending=pending), status=0, reserve=reserve)
            for gross in (101, 1_010_000_000, 80_000_000_000):
                assert verifier.first_buy_quote(curve, gross) == quote.first_buy_tokens(curve, gross)


def test_service_encodes_and_records_optional_room_price_limit(tmp_path, kp):
    import base64
    import sys
    from pathlib import Path
    from solders.transaction import Transaction
    from conftest import room
    from test_failures import NOW, REQ, Snap, make
    from matcher_service import txbuild
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
    from verify_decision import decode_launch_ix
    r = room(1, [('Elon', 'ELON')], created_at=NOW-60, reserve=10_000_000_000)
    svc = make(tmp_path, kp, Snap(1000, [r]))
    for requested in (None, '0', '12345678901234567890'):
        req = dict(REQ, first_buy_lamports=1_010_000_000)
        if requested is not None:
            req['max_room_price'] = requested
        out = svc.route(req)
        record = svc.store.get(out['id'])['record']
        msg = Transaction.from_bytes(base64.b64decode(out['transaction_base64'])).message
        launch = decode_launch_ix(msg, svc.cfg.program_id, txbuild.IDL_PATH)[3]
        expected = quote.room_price_limit(r, 200) if requested is None else int(requested)
        assert launch['max_room_price'] == int(record['launch_max_room_price']) == expected
        assert record['request']['max_room_price'] == requested


@pytest.mark.parametrize('bad', [-1, str(2**128), True, 1.5, '01', 'no'])
def test_service_refuses_invalid_room_price_limit(tmp_path, kp, bad):
    from test_failures import REQ, Snap, make
    from matcher_service.decide import Refusal
    svc = make(tmp_path, kp, Snap(1000))
    with pytest.raises(Refusal) as e:
        svc.route(dict(REQ, max_room_price=bad))
    assert e.value.code == 'invalid_request'


def test_new_room_price_field_precedes_the_name_key(tmp_path, kp):
    import base64
    import sys
    from pathlib import Path
    from solders.transaction import Transaction
    from test_failures import REQ, Snap, make
    from matcher_service import txbuild
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
    from verify_decision import decode_launch_ix
    svc = make(tmp_path, kp, Snap(1000))
    out = svc.route(dict(REQ, max_room_price='123456789'))
    msg = Transaction.from_bytes(base64.b64decode(out['transaction_base64'])).message
    name, _, _, launch = decode_launch_ix(msg, svc.cfg.program_id, txbuild.IDL_PATH)
    assert name == 'create_room'
    assert launch['max_room_price'] == 123456789
    from matcher_service import rules
    assert launch['name_key'] == rules.name_lock_key(REQ['name'], REQ['symbol']).hex()


def test_boundary_fuzzer_really_truncates_multibyte_names():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
    import name_fuzz as nf
    assert not nf.utf8_boundary('Cat')
    out = nf.utf8_boundary('A' * 31 + '🐸')
    assert out and all(len(v.encode('utf-8')) <= 32 for v in out)
    assert all('\ufffd' not in v for v in out)
    assert any(any(ord(c) > 127 for c in v) and any(c.isascii() and c.isalpha() for c in v)
               for v in nf.mixed_script_words('Pepe'))
