"""Public refusal/health errors must not disclose an authenticated RPC URL."""
import httpx
import pytest

from matcher_service.chain import RpcClient, RpcError


@pytest.mark.parametrize("failure", ["http", "jsonrpc"])
def test_rpc_errors_never_echo_credentials_or_provider_error_data(failure):
    marker = "synthetic-credential-marker"

    def respond(request):
        if failure == "http":
            return httpx.Response(503, request=request)
        return httpx.Response(200, json={"jsonrpc":"2.0","id":1,"error":{
            "code":-32000,"message":"provider rejected " + marker,"data":str(request.url)}},request=request)

    rpc = RpcClient("https://rpc.invalid/?api-key=" + marker,
                    transport=httpx.MockTransport(respond))
    with pytest.raises(RpcError) as err:
        rpc.slot()
    assert marker not in str(err.value)
    assert "rpc.invalid" not in str(err.value)


@pytest.mark.parametrize('failure', ['http', 'jsonrpc'])
def test_rpc_detail_is_available_only_to_internal_debug_logging(failure, caplog):
    import logging
    marker = 'synthetic-operator-diagnostic'
    def respond(request):
        if failure == 'http':
            return httpx.Response(503, request=request)
        return httpx.Response(200, json={'error': {'code':-32000, 'message':marker,
                                                  'data':{'provider_detail':'retry node 7'}}})
    rpc = RpcClient('https://rpc.invalid/?diagnostic='+marker, transport=httpx.MockTransport(respond))
    log = logging.getLogger('matcher.rpc.internal')
    log.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.DEBUG, logger='matcher.rpc.internal'):
            with pytest.raises(RpcError) as err:
                rpc.slot()
    finally:
        log.removeHandler(caplog.handler)
    internal = [r for r in caplog.records if r.name == 'matcher.rpc.internal']
    assert internal and marker in ' '.join(r.getMessage() for r in internal)
    assert all(r.levelno == logging.DEBUG for r in internal)
    assert marker not in str(err.value) and 'rpc.invalid' not in str(err.value)


def test_internal_rpc_diagnostics_never_enter_health_or_route_responses(tmp_path, kp):
    from fastapi.testclient import TestClient
    from solders.keypair import Keypair
    from matcher_service.app import create_app
    from matcher_service import auth
    from test_failures import Snap, make
    marker='synthetic-private-provider-diagnostic'
    rpc=RpcClient('https://rpc.invalid/?private='+marker,
        transport=httpx.MockTransport(lambda request:httpx.Response(503,request=request)))
    svc=make(tmp_path,kp,Snap(1000))
    svc.rpc.slot=rpc.slot
    wallet=Keypair()
    request=auth.sign(wallet,dict(launcher=str(wallet.pubkey()),name='Operator Frog',symbol='OP'))
    with TestClient(create_app(svc,start_refresher=False)) as client:
        for response in (client.get('/health'),client.post('/route',json=request)):
            assert response.status_code==503
            assert marker not in response.text and 'rpc.invalid' not in response.text
