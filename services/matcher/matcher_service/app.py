"""HTTP API: POST /route, GET /decision/{id}, GET /health, GET /metrics."""
import threading
import time

import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from . import config as config_mod
from .auth import AuthError, Verifier
from .chain import ChainState, RpcClient, RpcError
from .decide import Refusal
from .layouts import LayoutError
from .ops import Metrics, RateLimiter, logger
from .service import Service
from .signer import SignerUnavailable, from_config
from .store import Store
from .txbuild import Builder


# A /route body is a launcher key, metadata of at most 242 bytes and four integers; 8 KiB is ample.
MAX_BODY_BYTES = 8 * 1024


def build_service(cfg=None, rpc=None, signer=None):
    cfg = cfg or config_mod.load()
    rpc = rpc or RpcClient(cfg.rpc_url)
    log = logger()
    try:
        signer = signer or from_config(cfg)
    except SignerUnavailable as e:
        raise SystemExit(f"signer unavailable at startup: {e}")
    return Service(cfg, rpc, ChainState(rpc, cfg.program_id), signer, Store(cfg.db_path),
                   Builder(cfg.program_id), log, Metrics())


def create_app(service: Service, start_refresher=True):
    app = FastAPI(title="doors matcher", version="1")
    ip_limit = RateLimiter(service.cfg.rate_ip_per_min)
    launcher_limit = RateLimiter(service.cfg.rate_launcher_per_min)
    verifier = Verifier()

    def refresher():
        while True:
            try:
                service.chain.refresh()
            except (RpcError, LayoutError) as e:
                service.metrics.inc("matcher_rpc_errors_total", where="refresh")
                service.log.warning("refresh failed", extra={"fields": {"error": str(e)}})
            time.sleep(service.cfg.budget.refresh_seconds)

    if start_refresher:
        threading.Thread(target=refresher, daemon=True, name="snapshot-refresher").start()

    def client_ip(request: Request):
        peer = request.client.host if request.client else "unknown"
        if service.cfg.trust_forwarded_for and "x-forwarded-for" in request.headers:
            # The leftmost entries are whatever the client sent; only the entries the trusted proxies
            # appended (the rightmost `forwarded_hops`) are real. Taking the leftmost let any client
            # pick its own rate-limit key.
            hops = [h.strip() for h in request.headers["x-forwarded-for"].split(",")]
            n = service.cfg.forwarded_hops
            return hops[-n] if n >= 1 and len(hops) >= n and hops[-n] else peer
        return peer

    async def bounded_json(request: Request):
        declared = request.headers.get("content-length")
        if declared is not None and (not declared.isdigit() or int(declared) > MAX_BODY_BYTES):
            raise Refusal("request_too_large", f"body over {MAX_BODY_BYTES} bytes", 413)
        body = bytearray()
        async for chunk in request.stream():
            body += chunk
            if len(body) > MAX_BODY_BYTES:
                raise Refusal("request_too_large", f"body over {MAX_BODY_BYTES} bytes", 413)
        try:
            return json.loads(body)
        except (ValueError, UnicodeDecodeError):
            raise Refusal("invalid_request", "body must be JSON")

    def refuse(r: Refusal, extra=None):
        body = {"error": r.code, "message": r.message}
        if extra:
            body.update(extra)
        headers = {"Retry-After": "5"} if r.status in (409, 429, 503) else {}
        return JSONResponse(body, status_code=r.status, headers=headers)

    @app.post("/route")
    async def route(request: Request):
        service.metrics.inc("matcher_requests_total", endpoint="route")
        ip = client_ip(request)
        if not ip_limit.allow(ip):
            service.metrics.inc("matcher_refusals_total", code="rate_limited_ip")
            return refuse(Refusal("rate_limited", "too many requests from this address", 429))
        try:
            req = await bounded_json(request)
        except Refusal as r:
            return refuse(r)
        if not isinstance(req, dict):
            return refuse(Refusal("invalid_request", "body must be a JSON object"))
        # The launcher limit keys on a key the caller proved control of (M-3): a signature by the
        # launcher over the canonical request, fresh and single-use. Nothing else is read first.
        try:
            launcher_key = verifier.verify(req)
        except AuthError as e:
            service.metrics.inc("matcher_refusals_total", code=e.code)
            return refuse(Refusal(e.code, e.message, 401 if e.code == "unauthenticated" else 422))
        if not launcher_limit.allow(launcher_key):
            service.metrics.inc("matcher_refusals_total", code="rate_limited_launcher")
            return refuse(Refusal("rate_limited", "too many requests for this launcher", 429))
        try:
            # The pipeline does blocking I/O (RPC, KMS); run it off the event loop.
            from starlette.concurrency import run_in_threadpool
            out = await run_in_threadpool(service.route, req)
            return JSONResponse(out)
        except Refusal as r:
            service.log.info("refused", extra={"fields": {"code": r.code, "message": r.message, "ip": ip}})
            return refuse(r)

    @app.get("/decision/{decision_id}")
    def decision(decision_id: str):
        row = service.store.get(decision_id)
        if row is None:
            return JSONResponse({"error": "not_found"}, status_code=404)
        return JSONResponse(row)

    @app.get("/health")
    def health():
        h = service.health()
        return JSONResponse(h, status_code=200 if h.get("ready") else 503)

    @app.get("/metrics")
    def metrics():
        snap = service.chain.current()
        gauges = {"matcher_rpc_errors_cumulative": service.rpc.errors,
                  "matcher_snapshot_slot": snap.slot if snap else 0,
                  "matcher_snapshot_age_seconds": round(time.time() - snap.read_wall, 3) if snap else -1}
        return PlainTextResponse(service.metrics.render(gauges))

    return app


def factory():
    """`uvicorn --factory matcher_service.app:factory`: builds the service from the environment."""
    return create_app(build_service())
