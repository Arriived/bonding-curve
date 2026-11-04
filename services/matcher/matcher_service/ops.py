"""Rate limiting, metrics and structured logging. No external dependencies."""
import json
import logging
import sys
import threading
import time


class RateLimiter:
    """Fixed per-minute token buckets keyed by IP and by launcher pubkey."""

    def __init__(self, per_minute):
        self.rate = per_minute / 60.0
        self.cap = float(per_minute)
        self._b = {}
        self._lock = threading.Lock()

    def allow(self, key, now=None):
        now = time.monotonic() if now is None else now
        with self._lock:
            tokens, last = self._b.get(key, (self.cap, now))
            tokens = min(self.cap, tokens + (now - last) * self.rate)
            if tokens < 1.0:
                self._b[key] = (tokens, now)
                return False
            self._b[key] = (tokens - 1.0, now)
            if len(self._b) > 100_000:  # bound memory under key-spraying
                self._b = {k: v for k, v in self._b.items() if now - v[1] < 120}
            return True


class Metrics:
    BUCKETS = (0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10)

    def __init__(self):
        self._lock = threading.Lock()
        self.counters = {}
        self.hist = {b: 0 for b in self.BUCKETS}
        self.hist_count = 0
        self.hist_sum = 0.0

    def inc(self, name, **labels):
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            self.counters[key] = self.counters.get(key, 0) + 1

    def observe(self, seconds):
        with self._lock:
            self.hist_count += 1
            self.hist_sum += seconds
            for b in self.BUCKETS:
                if seconds <= b:
                    self.hist[b] += 1

    def render(self, gauges):
        lines = []
        with self._lock:
            for (name, labels), v in sorted(self.counters.items()):
                lab = ",".join(f'{k}="{val}"' for k, val in labels)
                lines.append(f"{name}{{{lab}}} {v}")
            for b in self.BUCKETS:
                lines.append(f'matcher_route_seconds_bucket{{le="{b}"}} {self.hist[b]}')
            lines.append(f'matcher_route_seconds_bucket{{le="+Inf"}} {self.hist_count}')
            lines.append(f"matcher_route_seconds_count {self.hist_count}")
            lines.append(f"matcher_route_seconds_sum {self.hist_sum:.6f}")
        for k, v in gauges.items():
            lines.append(f"{k} {v}")
        return "\n".join(lines) + "\n"


class JsonFormatter(logging.Formatter):
    def format(self, record):
        out = {"ts": round(record.created, 3), "level": record.levelname, "msg": record.getMessage()}
        out.update(getattr(record, "fields", {}))
        return json.dumps(out, sort_keys=True)


def logger():
    log = logging.getLogger("matcher")
    if not log.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(JsonFormatter())
        log.addHandler(h)
        log.setLevel(logging.INFO)
        log.propagate = False
    return log


def event(log, msg, **fields):
    log.info(msg, extra={"fields": fields})
