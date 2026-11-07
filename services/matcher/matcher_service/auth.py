"""Launcher-signed `/route` requests (SECURITY_REVIEW.md M-3).

The per-launcher rate limit used to key on the request's `launcher` field, which anyone could set to
any pubkey: evadable, and aimable at a victim's wallet. A request must now carry the launcher's
ed25519 signature over a canonical message, so the limiter key is a key the caller proved control of.

Canonical message (UTF-8):

    doors-matcher:route:v1\n
    + JSON array, no whitespace, of the values of FIELDS in this order:
      strings as JSON strings, integers as JSON strings of their decimal form (JavaScript cannot carry
      u64 exactly as a number), absent optional fields as null.

Python: json.dumps(values, ensure_ascii=False, separators=(",", ":")). JavaScript:
JSON.stringify(values) produces the same bytes for these values. `signature` is the base58 ed25519
signature by `launcher` over those bytes (a wallet's `signMessage`). `issued_at` (unix seconds) must
be within MAX_SKEW_SECONDS of the server clock, and each signature is accepted once while it is
inside that window, so a captured request cannot be replayed to spend the launcher's limit.
"""
import json
import threading
import time

from solders.pubkey import Pubkey
from solders.signature import Signature

PREFIX = b"doors-matcher:route:v1\n"
FIELDS = ("launcher", "name", "symbol", "uri", "first_buy_lamports", "min_tokens_out", "max_slippage_bps",
          "max_fee_lamports", "cu_price_micro_lamports", "issued_at", "max_room_price")
ALLOWED = frozenset(FIELDS) | {"signature"}
MAX_SKEW_SECONDS = 120


class AuthError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message


def message(req: dict) -> bytes:
    values = []
    for k in FIELDS:
        v = req.get(k)
        if v is None or isinstance(v, str):
            values.append(v)
        elif isinstance(v, int) and not isinstance(v, bool):
            values.append(str(v))
        else:
            raise AuthError("invalid_request", f"{k} must be a string or an integer")
    try:
        return PREFIX + json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except UnicodeEncodeError:
        raise AuthError("invalid_metadata", "name, symbol and uri must be valid Unicode (no lone surrogates)")


def sign(keypair, req: dict) -> dict:
    """Client helper (tests, e2e, reference for integrators): returns req plus issued_at and signature."""
    out = dict(req)
    out.setdefault("issued_at", int(time.time()))
    out["signature"] = str(keypair.sign_message(message(out)))
    return out


class Verifier:
    def __init__(self, max_skew=MAX_SKEW_SECONDS):
        self.max_skew = max_skew
        self._seen = {}            # signature -> expiry (unix seconds)
        self._lock = threading.Lock()

    def verify(self, req: dict, now=None) -> str:
        """Returns the verified launcher pubkey (base58) or raises AuthError."""
        now = time.time() if now is None else now
        unknown = set(req) - ALLOWED
        if unknown:
            raise AuthError("invalid_request", f"unknown fields: {sorted(unknown)}")
        try:
            launcher = Pubkey.from_string(req.get("launcher") or "")
        except (ValueError, TypeError):
            raise AuthError("invalid_request", "launcher must be a base58 public key")
        msg = message(req)          # refuses non-string/integer values and lone surrogates first
        issued = req.get("issued_at")
        if not isinstance(issued, int) or isinstance(issued, bool):
            raise AuthError("unauthenticated", "issued_at (unix seconds) is required")
        if abs(now - issued) > self.max_skew:
            raise AuthError("unauthenticated", f"issued_at is more than {self.max_skew} s from the server clock")
        raw = req.get("signature")
        try:
            sig = Signature.from_string(raw) if isinstance(raw, str) else None
        except ValueError:
            sig = None
        if sig is None or not sig.verify(launcher, msg):
            raise AuthError("unauthenticated", "signature by launcher over the canonical request is required "
                                               "(see matcher_service/auth.py)")
        with self._lock:
            self._seen = {s: t for s, t in self._seen.items() if t >= now}
            if raw in self._seen:
                raise AuthError("unauthenticated", "this signed request was already used")
            self._seen[raw] = issued + self.max_skew
        return str(launcher)
