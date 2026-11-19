"""Backfill historical pump.fun launches, far faster than watching for new ones.

Every `create`/`create_v2` passes through one fixed mint-authority PDA,
`TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM`, which trades do not touch. So `getSignaturesForAddress` on that
one account enumerates launches directly instead of sifting the program's whole traffic (the program sees roughly
286 transactions a second; launches are about 0.4 of them). Measured 19 November 2026: ~44,000 signatures a day at
that address, matching the ~42,000 launches a second-by-second watch records, and 1,000 signatures per call covers
about 32 minutes of history.

Transactions are then fetched in parallel and decoded with `watcher.decode`, the same code the live watcher uses,
so backfilled rows and watched rows are directly comparable. Measured ~59 tx/s against PublicNode: about 12
minutes per day of history.

Resumable: `cursor.json` holds the oldest signature already walked, so a restart continues rather than redoing.
Rows are appended to `launches.jsonl` and deduplicated on (signature, mint).

Usage:
  python3 -m watcher.backfill --out DIR --days 7
  python3 -m watcher.backfill --out DIR --until 1794000000      # a unix timestamp
Run from services/matcher. Read-only RPC; nothing is signed or sent.
"""
import argparse
import collections
import concurrent.futures as cf
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
DEFAULT_SIG_RPC = "https://api.mainnet-beta.solana.com"     # serves getSignaturesForAddress
DEFAULT_TX_RPC = "https://solana-rpc.publicnode.com"        # much faster for getTransaction
USER_AGENT = "doors-launch-backfill/1"


def _ctx():
    ca = os.environ.get("SSL_CERT_FILE") or ("/root/.ccr/ca-bundle.crt"
                                             if os.path.exists("/root/.ccr/ca-bundle.crt") else None)
    return ssl.create_default_context(cafile=ca)


class Rpc:
    def __init__(self, url):
        self.url, self.ctx = url, _ctx()
        self.errors = collections.Counter()
        self.lock = threading.Lock()

    def call(self, method, params, attempts=5):
        for a in range(attempts):
            try:
                req = urllib.request.Request(
                    self.url, json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                    {"content-type": "application/json", "user-agent": USER_AGENT})
                r = json.loads(urllib.request.urlopen(req, timeout=30, context=self.ctx).read())
            except (urllib.error.URLError, OSError, ValueError) as e:
                with self.lock:
                    self.errors[type(e).__name__] += 1
                time.sleep(min(20, 0.5 * 2 ** a))
                continue
            if "result" in r:
                return r["result"]
            with self.lock:
                self.errors[f"rpc {r.get('error', {}).get('code')}"] += 1
            time.sleep(min(20, 0.5 * 2 ** a))
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--days", type=float, help="how far back to walk from the newest launch")
    ap.add_argument("--until", type=int, help="stop at this unix timestamp (overrides --days)")
    ap.add_argument("--sig-rpc", default=DEFAULT_SIG_RPC)
    ap.add_argument("--tx-rpc", default=DEFAULT_TX_RPC)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sig_rpc, tx_rpc = Rpc(a.sig_rpc), Rpc(a.tx_rpc)

    seen = set()
    path = out / "launches.jsonl"
    if path.exists():
        for line in path.open(encoding="utf-8"):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            seen.add((r.get("signature"), r.get("mint")))
        print(f"{len(seen):,} rows already present")

    cursor_file = out / "cursor.json"
    before = json.loads(cursor_file.read_text()).get("before") if cursor_file.exists() else None
    if before:
        print(f"resuming before {before}")

    stop_at = a.until
    sink = path.open("a", encoding="utf-8")
    pages = written = fetched = failed = 0
    started = time.time()
    oldest = None
    try:
        while True:
            params = [MINT_AUTHORITY, {"limit": 1000, **({"before": before} if before else {})}]
            sigs = sig_rpc.call("getSignaturesForAddress", params)
            if not sigs:
                print("no more signatures" if sigs == [] else "signature page failed; stopping")
                break
            pages += 1
            if stop_at is None and a.days:
                stop_at = sigs[0]["blockTime"] - int(a.days * 86400)
                print(f"walking back to {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(stop_at))}")
            before = sigs[-1]["signature"]
            oldest = sigs[-1].get("blockTime") or oldest
            todo = [s for s in sigs if not s.get("err")]

            def one(s):
                tx = tx_rpc.call("getTransaction", [s["signature"],
                                                    {"maxSupportedTransactionVersion": 1, "encoding": "json"}])
                return s, tx

            with cf.ThreadPoolExecutor(a.workers) as ex:
                for s, tx in ex.map(one, todo):
                    if tx is None:
                        failed += 1
                        continue
                    fetched += 1
                    for x in D.launches_from_tx(tx):
                        key = (s["signature"], x["mint"])
                        if key in seen:
                            continue
                        seen.add(key)
                        sink.write(json.dumps({
                            "ts": s.get("blockTime"), "slot": tx.get("slot"), "signature": s["signature"],
                            "platform": "pump.fun" if x["platform"] == "pump" else x["platform"],
                            "mint": x["mint"], "name": x["name"], "symbol": x["symbol"], "uri": x["uri"],
                            "creator": x.get("creator"), "ix": x.get("ix"), "source": "backfill"},
                            ensure_ascii=False) + "\n")
                        written += 1
            sink.flush()
            cursor_file.write_text(json.dumps({"before": before, "oldest_block_time": oldest}))
            rate = written / max(1e-9, time.time() - started)
            when = time.strftime("%Y-%m-%d %H:%M", time.gmtime(oldest)) if oldest else "?"
            print(f"page {pages:>4} | {written:>7,} launches | back to {when} UTC | "
                  f"{rate:.0f}/s | fetch fail {failed}", flush=True)
            if stop_at and oldest and oldest <= stop_at:
                print("reached the requested start time")
                break
    finally:
        sink.close()
        print(f"\n{written:,} launches written to {path}")
        for r, lab in ((sig_rpc, "signatures"), (tx_rpc, "transactions")):
            if r.errors:
                print(f"  {lab} RPC errors: {dict(r.errors)}")


if __name__ == "__main__":
    main()
