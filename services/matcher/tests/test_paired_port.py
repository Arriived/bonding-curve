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


def test_room_reserve_limit_uses_pre_settlement_reserve_and_slippage():
    reserve = 10_000_000_000
    curve = dict(curve_state(reserve, pending=3_000_000), reserve=reserve)
    v_sol = curve['v_sol_lamports']
    limit = quote.room_reserve_limit(curve, 200)
    target = (v_sol + reserve)**2 * 10_200
    assert (v_sol + limit)**2 * 10_000 <= target < (v_sol + limit + 1)**2 * 10_000
    settled = dict(curve, reserve=reserve + curve['pending_reserve_sol'])
    assert quote.room_reserve_limit(settled, 200) > limit


def test_nominal_price_and_quoted_cap_across_validated_curve_extremes():
    from fractions import Fraction

    c = config()
    for vs, vt, cap in (
        (c['v_sol_lamports'], c['v_tok'], c['graduation_trigger_lamports']),
        (1, quote.U + 1, c['graduation_trigger_lamports']),
        (2**63, quote.U + 1, 1_000_000),
        (2**64 - 1, 2**64 - 1, c['graduation_trigger_lamports']),
    ):
        reserves = sorted({0, 1, cap - 1, cap, *(cap * i // 1024 for i in range(1025))})
        prices = [Fraction((vs + reserve)**2, vs * vt) for reserve in reserves]
        assert all(a < b for a, b in zip(prices, prices[1:]))
        for reserve in reserves:
            curve = dict(v_sol_lamports=vs, reserve=reserve, graduation_trigger_lamports=cap)
            for slip in (1, 200, 5_000):
                limit = quote.room_reserve_limit(curve, slip)
                assert max(1, reserve) <= limit <= cap
                target = (vs + reserve)**2 * (10_000 + slip)
                if reserve or limit > 1:
                    assert (vs + limit)**2 * 10_000 <= target
                if limit < cap:
                    assert (vs + limit + 1)**2 * 10_000 > target
    assert quote.room_reserve_limit(dict(v_sol_lamports=1, reserve=0,
                                         graduation_trigger_lamports=1), 1) == 1


@pytest.mark.parametrize('field,value', [
    ('launcher', '11111111111111111111111111111111'), ('name', 'Altered'),
    ('symbol', 'ALT'), ('uri', 'https://example.invalid/changed'),
    ('first_buy_lamports', 102), ('min_tokens_out', 99), ('max_slippage_bps', 300),
    ('max_fee_lamports', 9), ('cu_price_micro_lamports', 2), ('issued_at', 1001),
    ('max_reserve_lamports', '987654321'),
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


def test_service_encodes_and_records_optional_room_reserve_limit(tmp_path, kp):
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
            req['max_reserve_lamports'] = requested
        out = svc.route(req)
        record = svc.store.get(out['id'])['record']
        msg = Transaction.from_bytes(base64.b64decode(out['transaction_base64'])).message
        launch = decode_launch_ix(msg, svc.cfg.program_id, txbuild.IDL_PATH)[3]
        expected = quote.room_reserve_limit(r, 200) if requested is None else int(requested)
        assert launch['max_reserve_lamports'] == int(record['launch_max_reserve_lamports']) == expected
        assert record['request']['max_reserve_lamports'] == requested


@pytest.mark.parametrize('bad', [-1, str(2**64), True, 1.5, '01', 'no'])
def test_service_refuses_invalid_room_reserve_limit(tmp_path, kp, bad):
    from test_failures import REQ, Snap, make
    from matcher_service.decide import Refusal
    svc = make(tmp_path, kp, Snap(1000))
    with pytest.raises(Refusal) as e:
        svc.route(dict(REQ, max_reserve_lamports=bad))
    assert e.value.code == 'invalid_request'


def test_new_room_reserve_field_precedes_the_name_key(tmp_path, kp):
    import base64
    import sys
    from pathlib import Path
    from solders.transaction import Transaction
    from test_failures import REQ, Snap, make
    from matcher_service import txbuild
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
    from verify_decision import decode_launch_ix
    svc = make(tmp_path, kp, Snap(1000))
    out = svc.route(dict(REQ, max_reserve_lamports='123456789'))
    msg = Transaction.from_bytes(base64.b64decode(out['transaction_base64'])).message
    name, _, _, launch = decode_launch_ix(msg, svc.cfg.program_id, txbuild.IDL_PATH)
    assert name == 'create_room'
    assert launch['max_reserve_lamports'] == 123456789
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


@pytest.mark.parametrize('uri_bytes,fits', [(62, True), (63, False), (67, False)])
def test_priority_priced_creation_metadata_budget(tmp_path, kp, uri_bytes, fits):
    import base64
    from test_failures import REQ, Snap, make
    from matcher_service.decide import Refusal

    svc = make(tmp_path, kp, Snap(1000))
    prefix = 'https://example.invalid/'
    request = dict(REQ, name='Pepe Wif Sword', symbol='SwordPepe',
                   uri=prefix + 'x' * (uri_bytes - len(prefix)), cu_price_micro_lamports=1)
    if fits:
        out = svc.route(request)
        assert len(base64.b64decode(out['transaction_base64'])) == 1232
    else:
        with pytest.raises(Refusal) as error:
            svc.route(request)
        assert error.value.code == 'tx_too_large'


def test_old_request_domain_cannot_authorize_an_explicit_reserve_bound():
    wallet = Keypair()
    req = auth.sign(wallet, dict(launcher=str(wallet.pubkey()), name='Bounded',
                                symbol='BND', issued_at=1000, max_reserve_lamports='42'))
    previous_message = auth.message(req).replace(auth.RESERVE_BOUND_PREFIX, auth.PREFIX, 1)
    forged = dict(req, signature=str(wallet.sign_message(previous_message)))
    verifier = auth.Verifier()
    with pytest.raises(auth.AuthError, match='signature'):
        verifier.verify(forged, now=1000)
    assert verifier.verify(req, now=1000) == str(wallet.pubkey())


def test_verifier_keeps_decoding_historical_signed_price_bound_messages():
    import hashlib
    import sys
    from pathlib import Path
    from solders.instruction import Instruction
    from solders.pubkey import Pubkey
    from matcher_service import txbuild
    from matcher_service.program_id import PROGRAM_ID

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
    from verify_decision import decode_launch_ix

    user, matcher = Pubkey.new_unique(), Pubkey.new_unique()
    builder = txbuild.Builder(PROGRAM_ID)
    previous_price = 2**100 + 1234
    key = bytes(range(16))
    launch = txbuild.encode_launch('Old room', 'OLD', '', 0, 0, 1, 0, 0, 0, bytes(32), 0, 100)
    historical_launch = launch[:-8] + previous_price.to_bytes(16, 'little')
    new_ix, _, _ = builder.create_room_ix(user, matcher, 42, bytes(32), None, historical_launch, key)
    old_disc = hashlib.sha256(b'global:create_room').digest()[:8]
    old_ix = Instruction(new_ix.program_id, old_disc + new_ix.data[8:], new_ix.accounts)
    msg = txbuild.build_message(old_ix, user, '11111111111111111111111111111111', 500_000, 0)
    name, room_id, _, decoded = decode_launch_ix(msg, PROGRAM_ID, txbuild.IDL_PATH)
    assert (name, room_id) == ('create_room', 42)
    assert decoded['max_room_price'] == previous_price
    assert decoded['name_key'] == key.hex()
