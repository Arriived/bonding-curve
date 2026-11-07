"""Service configuration, from environment variables only. Secrets are never read from the environment:
the signer is selected here, but its key lives in a KMS (production) or a keyfile path (development).
"""
import os
from .program_id import PROGRAM_ID
from dataclasses import dataclass


@dataclass(frozen=True)
class Budget:
    coherence_slots: int     # all reads of one snapshot within this many slots of each other
    max_lag_slots: int       # snapshot slot at most this far behind the cluster when signing
    max_age_seconds: float   # snapshot read at most this long ago
    refresh_seconds: float   # background refresh interval


@dataclass(frozen=True)
class Config:
    env: str                 # "production" | "development"
    rpc_url: str
    program_id: str
    signer: str              # "gcp-kms" | "aws-kms" | "keyfile"
    keyfile: str | None
    gcp_key_version: str | None
    aws_key_id: str | None
    db_path: str
    matcher_version: int
    budget: Budget
    cu_limit: int
    max_cu_price: int        # micro-lamports; requests above it are refused
    rate_ip_per_min: int
    rate_launcher_per_min: int
    trust_forwarded_for: bool
    # With trust_forwarded_for: how many trusted proxies append to X-Forwarded-For. The client address
    # is the entry that many places from the right; everything left of it is client-supplied.
    # 1 = one proxy appending the peer (nginx $proxy_add_x_forwarded_for); a GCP HTTPS load balancer
    # appends "<client>, <lb>", so use 2 behind it.
    forwarded_hops: int = 1


def _int(name, default):
    return int(os.environ.get(name, default))


def load() -> Config:
    env = os.environ.get("MATCHER_ENV", "development")
    signer = os.environ.get("MATCHER_SIGNER", "gcp-kms" if env == "production" else "keyfile")
    if env == "production" and signer == "keyfile":
        raise SystemExit("MATCHER_ENV=production refuses MATCHER_SIGNER=keyfile; use gcp-kms or aws-kms")
    for forbidden in ("MATCHER_PRIVATE_KEY", "MATCHER_SECRET_KEY", "MATCHER_KEYPAIR"):
        if forbidden in os.environ:
            raise SystemExit(f"{forbidden} is set: the matcher key is never taken from an environment variable")
    return Config(
        env=env,
        rpc_url=os.environ["MATCHER_RPC_URL"],
        program_id=os.environ.get("MATCHER_PROGRAM_ID", PROGRAM_ID),
        signer=signer,
        keyfile=os.environ.get("MATCHER_KEYFILE"),
        gcp_key_version=os.environ.get("MATCHER_GCP_KEY_VERSION"),
        aws_key_id=os.environ.get("MATCHER_AWS_KEY_ID"),
        db_path=os.environ.get("MATCHER_DB", "decisions.sqlite3"),
        matcher_version=_int("MATCHER_VERSION", 1),
        budget=Budget(
            coherence_slots=_int("MATCHER_COHERENCE_SLOTS", 30),
            max_lag_slots=_int("MATCHER_MAX_LAG_SLOTS", 30),
            max_age_seconds=float(os.environ.get("MATCHER_MAX_AGE_SECONDS", 8)),
            refresh_seconds=float(os.environ.get("MATCHER_REFRESH_SECONDS", 2)),
        ),
        cu_limit=_int("MATCHER_CU_LIMIT", 400_000),
        max_cu_price=_int("MATCHER_MAX_CU_PRICE", 1_000_000),
        rate_ip_per_min=_int("MATCHER_RATE_IP_PER_MIN", 30),
        rate_launcher_per_min=_int("MATCHER_RATE_LAUNCHER_PER_MIN", 6),
        trust_forwarded_for=os.environ.get("MATCHER_TRUST_X_FORWARDED_FOR", "0") == "1",
        forwarded_hops=_int("MATCHER_TRUSTED_PROXY_HOPS", 1),
    )
