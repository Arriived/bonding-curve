"""Backfill historical pump.fun launches, far faster than watching for new ones.

Every `create`/`create_v2` passes through one fixed mint-authority PDA,
`TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM`, which trades do not touch. So `getSignaturesForAddress` on that
one account enumerates launches directly instead of sifting the program's whole traffic (the program sees roughly
286 transactions a second; launches are about 0.4 of them). Measured 19 November 2026: ~44,000 signatures a day at
that address, matching the ~42,000 launches a second-by-second watch records, and 1,000 signatures per call covers
about 32 minutes of history.

Transactions are then fetched in parallel and decoded with `watcher.decode`, the same code the live watcher uses,
so backfilled rows and watched rows are directly comparable.

Free endpoints enforce a sustained-rate quota that a burst test does not reveal, so this throttles itself:
concurrency halves whenever a page's failure rate passes `--max-fail`, and creeps back up after clean pages.
A signature whose transaction could not be fetched is written to `failed.jsonl` and never silently dropped;
`--retry` drains that file. The first version of this script had neither, and lost roughly 48,000 launches to a
cursor that advanced past failures while the cumulative counter hid a 100% failure rate (CORRECTIONS section 27).

Resumable: `cursor.json` holds the oldest signature already walked, so a restart continues rather than redoing.
Rows are appended to `launches.jsonl` and deduplicated on (signature, mint).

Usage:
  python3 -m watcher.backfill --out DIR --days 7
  python3 -m watcher.backfill --out DIR --until 1794000000      # a unix timestamp
  python3 -m watcher.backfill --out DIR --retry                 # re-fetch everything in failed.jsonl
Run from services/matcher. Read-only RPC; nothing is signed or sent.
"""
import argparse
import collections
import concurrent.futures as cf
import itertools
import json
import os
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from watcher import decode as D  # noqa: E402

MINT_AUTHORITY = "TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM"
# Both of these serve getSignaturesForAddress and getTransaction. Each has its own sustained-rate quota, so the
# pool rotates and a 429 parks one endpoint without stalling the walk.
DEFAULT_RPCS = ("https://solana-rpc.publicnode.com", "https://api.mainnet-beta.solana.com")
USER_AGENT = "doors-launch-backfill/3"
MISSING = object()   # EVERY endpoint answered and none has the record; only then is it treated as absent


def _ctx():
    ca = os.environ.get("SSL_CERT_FILE") or ("/root/.ccr/ca-bundle.crt"
                                             if os.path.exists("/root/.ccr/ca-bundle.crt") else None)
    return ssl.create_default_context(cafile=ca)


class Rpc:
    """One endpoint, with a cooldown so a rate-limited host is skipped instead of hammered."""

    def __init__(self, url):
        self.url, self.ctx = url, _ctx()
        self.errors = collections.Counter()
        self.calls = 0
        self.cool_until = 0.0
        self.lock = threading.Lock()

    def available(self):
        return time.time() >= self.cool_until

    def once(self, method, params, timeout=30):
        """One attempt. Returns the result, MISSING for a null result, or None if the call itself failed."""
        with self.lock:
            self.calls += 1
        try:
            req = urllib.request.Request(
                self.url, json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                {"content-type": "application/json", "user-agent": USER_AGENT})
            body = urllib.request.urlopen(req, timeout=timeout, context=self.ctx).read()
            r = json.loads(body)
        except (urllib.error.URLError, OSError, ValueError) as e:
            with self.lock:
                self.errors[type(e).__name__] += 1
                if isinstance(e, urllib.error.HTTPError) and e.code == 429:
                    self.cool_until = time.time() + 5
            return None
        if "result" in r:
            return MISSING if r["result"] is None else r["result"]
        code = r.get("error", {}).get("code")
        with self.lock:
            self.errors[f"rpc {code}"] += 1
            if code == 429 or code == -32429:
                self.cool_until = time.time() + 5
        return None


class Pool:
    """Round-robin over endpoints, preferring ones not in cooldown."""

    def __init__(self, urls):
        self.rpcs = [Rpc(u) for u in urls]
        self.turn = itertools.cycle(range(len(self.rpcs)))
        self.lock = threading.Lock()

    def pick(self):
        with self.lock:
            for _ in range(len(self.rpcs)):
                r = self.rpcs[next(self.turn)]
                if r.available():
                    return r
            return self.rpcs[next(self.turn)]

    def call(self, method, params, attempts=4):
        """Try across endpoints with backoff.

        A null result means only that *this* endpoint does not have the record, which on a free endpoint usually
        means it has pruned it, not that it never existed. Endpoints prune at very different depths: measured
        19 November 2026, publicnode had dropped transactions 2.4 days old that api.mainnet-beta still served in
        full. So MISSING is returned only once every endpoint has been asked and none of them had it; otherwise
        the backfill silently discards all history older than the shallowest endpoint's retention
        (CORRECTIONS section 27).
        """
        for a in range(attempts):
            saw_missing = False
            for _ in range(len(self.rpcs)):
                got = self.pick().once(method, params)
                if got is MISSING:
                    saw_missing = True
                    continue
                if got is not None:
                    return got
            if saw_missing:
                return MISSING          # every endpoint answered; none has it
            time.sleep(min(10, 0.4 * 2 ** a))
        return None

    def report(self, label):
        for r in self.rpcs:
            if r.errors:
                print(f"  {label} {r.url}: {r.calls:,} calls, errors {dict(r.errors)}")


def _row(sig, tx, x, source):
    return {"ts": sig.get("blockTime"), "slot": tx.get("slot"), "signature": sig["signature"],
            "platform": "pump.fun" if x["platform"] == "pump" else x["platform"],
            "mint": x["mint"], "name": x["name"], "symbol": x["symbol"], "uri": x["uri"],
            "creator": x.get("creator"), "ix": x.get("ix"), "source": source}


def fetch_many(pool, sigs, workers):
    """Fetch and decode a batch. Returns (rows, missing, failed_sigs)."""
    rows, missing, failed = [], 0, []

    def one(s):
        return s, pool.call("getTransaction", [s["signature"],
                                               {"maxSupportedTransactionVersion": 1, "encoding": "json"}])

    with cf.ThreadPoolExecutor(max(1, workers)) as ex:
        for s, tx in ex.map(one, sigs):
            if tx is MISSING:
                missing += 1
                continue
            if tx is None:
                failed.append(s)
                continue
            for x in D.launches_from_tx(tx):
                rows.append((s, tx, x))
    return rows, missing, failed


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--days", type=float, help="how far back to walk from the newest launch")
    ap.add_argument("--until", type=int, help="stop at this unix timestamp (overrides --days)")
    ap.add_argument("--retry", action="store_true", help="re-fetch the signatures in failed.jsonl and stop")
    ap.add_argument("--rpc", action="append", help="repeatable; defaults to both known free endpoints")
    ap.add_argument("--workers", type=int, default=6, help="starting concurrency; throttles itself downwards")
    ap.add_argument("--max-fail", type=float, default=0.05, help="page failure rate above which to back off")
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    pool = Pool(a.rpc or DEFAULT_RPCS)

    path, failed_path, cursor_file = out / "launches.jsonl", out / "failed.jsonl", out / "cursor.json"
    seen = set()
    if path.exists():
        for line in path.open(encoding="utf-8"):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            seen.add((r.get("signature"), r.get("mint")))
        print(f"{len(seen):,} rows already present")

    def write(sink, batch, source):
        n = 0
        for s, tx, x in batch:
            k = (s["signature"], x["mint"])
            if k in seen:
                continue
            seen.add(k)
            sink.write(json.dumps(_row(s, tx, x, source), ensure_ascii=False) + "\n")
            n += 1
        return n

    # ---- retry mode: drain failed.jsonl ------------------------------------------------------------
    if a.retry:
        if not failed_path.exists():
            sys.exit("no failed.jsonl to retry")
        pending, dedupe = [], set()
        for line in failed_path.open(encoding="utf-8"):
            try:
                s = json.loads(line)
            except ValueError:
                continue
            if s["signature"] not in dedupe:
                dedupe.add(s["signature"])
                pending.append(s)
        print(f"retrying {len(pending):,} signatures at {a.workers} workers")
        still, written, workers = [], 0, a.workers
        with path.open("a", encoding="utf-8") as sink:
            for i in range(0, len(pending), 200):
                chunk = pending[i:i + 200]
                rows, missing, fails = fetch_many(pool, chunk, workers)
                written += write(sink, rows, "backfill-retry")
                still.extend(fails)
                sink.flush()
                rate = len(fails) / max(1, len(chunk))
                workers = max(1, workers // 2) if rate > a.max_fail else min(a.workers, workers + 1)
                print(f"  {i + len(chunk):>7,}/{len(pending):,} | +{written:,} launches | "
                      f"{missing} absent | {len(still):,} still failing | {workers}w", flush=True)
                if rate > a.max_fail:
                    time.sleep(3)
        failed_path.write_text("".join(json.dumps(s) + "\n" for s in still), encoding="utf-8")
        print(f"\n{written:,} launches recovered; {len(still):,} signatures still failing")
        pool.report("tx")
        return

    # ---- forward (backwards-in-time) walk ----------------------------------------------------------
    before = json.loads(cursor_file.read_text()).get("before") if cursor_file.exists() else None
    if before:
        print(f"resuming before {before}")
    stop_at, oldest = a.until, None
    pages = written = missing_total = failed_total = 0
    workers, clean = a.workers, 0
    started = time.time()
    sink, fsink = path.open("a", encoding="utf-8"), failed_path.open("a", encoding="utf-8")
    try:
        while True:
            params = [MINT_AUTHORITY, {"limit": 1000, **({"before": before} if before else {})}]
            # A signature page can fail on every endpoint at once and still be fine a minute later: the cursor
            # signature may be pruned on one endpoint while the other is rate-limiting. Giving up on the first
            # such page stopped a run 1.4 days in with the walk otherwise healthy, so wait it out first.
            sigs = None
            for wait in (0, 10, 20, 40, 60):
                if wait:
                    print(f"  signature page failed on every endpoint; waiting {wait}s", flush=True)
                    time.sleep(wait)
                sigs = pool.call("getSignaturesForAddress", params)
                if sigs is MISSING or sigs:
                    break
            if sigs is MISSING or sigs == []:
                print("no more signatures")
                break
            if not sigs:
                print("signature page still failing after 130s of retries; stopping "
                      "(resume with the same --out)")
                break
            pages += 1
            if stop_at is None and a.days:
                stop_at = sigs[0]["blockTime"] - int(a.days * 86400)
                print(f"walking back to {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(stop_at))}")
            before = sigs[-1]["signature"]
            oldest = sigs[-1].get("blockTime") or oldest
            todo = [s for s in sigs if not s.get("err")]

            rows, missing, fails = fetch_many(pool, todo, workers)
            written += write(sink, rows, "backfill")
            missing_total += missing
            failed_total += len(fails)
            for s in fails:
                fsink.write(json.dumps({"signature": s["signature"], "blockTime": s.get("blockTime")}) + "\n")
            sink.flush()
            fsink.flush()
            cursor_file.write_text(json.dumps({"before": before, "oldest_block_time": oldest}))

            rate = len(fails) / max(1, len(todo))
            if rate > a.max_fail:
                workers, clean = max(1, workers // 2), 0
            else:
                clean += 1
                if clean >= 3 and workers < a.workers:
                    workers, clean = workers + 1, 0
            when = time.strftime("%Y-%m-%d %H:%M", time.gmtime(oldest)) if oldest else "?"
            print(f"page {pages:>4} | {written:>7,} launches | back to {when} UTC | "
                  f"{written / max(1e-9, time.time() - started):.0f}/s | "
                  f"page fail {100 * rate:4.1f}% | {workers}w | queued for retry {failed_total:,}", flush=True)
            if rate > a.max_fail:
                time.sleep(3)
            if stop_at and oldest and oldest <= stop_at:
                print("reached the requested start time")
                break
    finally:
        sink.close()
        fsink.close()
        print(f"\n{written:,} launches written to {path}")
        print(f"{missing_total:,} transactions genuinely absent; {failed_total:,} queued in {failed_path}")
        if failed_total:
            print(f"recover them with: python3 -m watcher.backfill --out {a.out} --retry")
        pool.report("rpc")


if __name__ == "__main__":
    main()
