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
