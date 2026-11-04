"""HTTP API: POST /route, GET /decision/{id}, GET /health, GET /metrics."""
import threading
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from . import config as config_mod
from .chain import ChainState, RpcClient, RpcError
from .decide import Refusal
from .layouts import LayoutError
from .ops import Metrics, RateLimiter, logger
from .service import Service
from .signer import SignerUnavailable, from_config
from .store import Store
from .txbuild import Builder


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
        if service.cfg.trust_forwarded_for and "x-forwarded-for" in request.headers:
            return request.headers["x-forwarded-for"].split(",")[0].strip()
        return request.client.host if request.client else "unknown"

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
            req = await request.json()
        except ValueError:
            return refuse(Refusal("invalid_request", "body must be JSON"))
        if not isinstance(req, dict):
            return refuse(Refusal("invalid_request", "body must be a JSON object"))
        if not launcher_limit.allow(str(req.get("launcher", ""))):
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
