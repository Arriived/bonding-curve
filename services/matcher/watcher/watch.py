"""Watch pump.fun and Raydium LaunchLab (bonk.fun, StonkFun and every other LaunchLab platform) launches live over
free RPC endpoints and run our matcher on each one in shadow mode.

Streams: one websocket `logsSubscribe` per program (mentions filter), reconnecting with backoff and rotating through
the websocket endpoints. Most pump.fun launches decode from the notification's logs; the rest, and every LaunchLab
launch, are fetched with getTransaction over the HTTP endpoints (rotating, rate-limited, retried).

Output in --out:
  launches.jsonl   one line per launch: platform, signature, slot, mint, name, symbol, uri, creator, decode path,
                   and the shadow decision (door of room N with its door 0, new room, or no key)
  summary.md       rewritten every --summary-every seconds
  events.log       connection and RPC events
On restart the existing launches.jsonl is replayed, so rooms carry over.

Usage: python3 -m watcher.watch --out DIR [--minutes N] [--ws URL ...] [--http URL ...]
Endpoints can also come from WATCHER_WS / WATCHER_HTTP (comma-separated), which keeps a provider key off the command
line; logs and the summary show only each endpoint's host.
(run from services/matcher; needs requirements-watcher.txt). Nothing is signed or sent: read-only RPC calls only.
"""
import argparse
import asyncio
import base64
import collections
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from watcher import decode as D  # noqa: E402
from watcher.shadow import Shadow  # noqa: E402

# Free endpoints that answered from the build environment on 7 November 2026 (others were not reachable from there,
# which says nothing about whether they work elsewhere; see README).
DEFAULT_WS = ["wss://api.mainnet-beta.solana.com"]
DEFAULT_HTTP = ["https://solana-rpc.publicnode.com", "https://api.mainnet-beta.solana.com"]
USER_AGENT = "doors-launch-watcher/1"
MIN_INTERVAL = 0.25          # seconds between HTTP calls per endpoint
PROGRAMS = {"pump": D.PUMP, "launchlab": D.LAUNCHLAB}


def _host(url):
    """scheme://host only: endpoint URLs can carry a provider key, which must not reach logs or the summary."""
    from urllib.parse import urlsplit
    u = urlsplit(url)
    return f"{u.scheme}://{u.hostname}"


def _ssl_context():
    ca = os.environ.get("SSL_CERT_FILE") or ("/root/.ccr/ca-bundle.crt" if os.path.exists("/root/.ccr/ca-bundle.crt")
                                             else None)
    return ssl.create_default_context(cafile=ca)


class Http:
    """Blocking JSON-RPC over several endpoints: rotates on error, spaces calls per endpoint, counts failures."""

    def __init__(self, urls, log):
        self.urls, self.log, self.ctx = list(urls), log, _ssl_context()
        self.next_ok = collections.defaultdict(float)
        self.errors = collections.Counter()
        self.calls = collections.Counter()
        self.i = 0

    def call(self, method, params, attempts=6):
        for a in range(attempts):
            url = self.urls[(self.i + a) % len(self.urls)]
            wait = self.next_ok[url] - time.time()
            if wait > 0:
                time.sleep(wait)
            self.next_ok[url] = time.time() + MIN_INTERVAL
            self.calls[_host(url)] += 1
            try:
                req = urllib.request.Request(url, json.dumps({"jsonrpc": "2.0", "id": 1, "method": method,
                                                              "params": params}).encode(),
                                             {"content-type": "application/json", "user-agent": USER_AGENT})
                r = json.loads(urllib.request.urlopen(req, timeout=20, context=self.ctx).read())
            except (urllib.error.URLError, OSError, ValueError) as e:
                self.errors[f"{_host(url)} {type(e).__name__} {getattr(e, 'code', '')}".strip()] += 1
                self.next_ok[url] = time.time() + min(30, 2 ** a)
                continue
            if "result" in r:
                self.i = (self.i + a) % len(self.urls)
                return r["result"]
            self.errors[f"{_host(url)} rpc {r.get('error', {}).get('code')}"] += 1
            time.sleep(min(10, 0.5 * 2 ** a))
        return None


class Watcher:
    def __init__(self, out, ws_urls, http_urls, minutes, summary_every):
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.ws_urls, self.minutes, self.summary_every = ws_urls, minutes, summary_every
        self.events = open(self.out / "events.log", "a", encoding="utf-8")
        self.http = Http(http_urls, self.log)
        self.shadow = Shadow()
        self.seen = collections.OrderedDict()       # signature:mint of recorded launches
        self.seen_sigs = collections.OrderedDict()  # notifications already queued (a reconnect can repeat them)
        self.platforms = {}            # platform_config -> (label, name, web)
        self.stats = collections.Counter()
        self.started = time.time()
        self.first_ts = None
        self.records = []
        self._replay()
        self.sink = open(self.out / "launches.jsonl", "a", encoding="utf-8")

    def log(self, msg):
        self.events.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}\n")
        self.events.flush()

    def _replay(self):
        p = self.out / "launches.jsonl"
        if not p.exists():
            return
        for line in p.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            self.seen[rec["signature"] + ":" + rec["mint"]] = True
            rec.update(self.shadow.route(rec))
            self.records.append(rec)
            self.first_ts = self.first_ts or rec.get("ts")
        self.log(f"replayed {len(self.records)} launches from {p}")

    # ---- streaming -------------------------------------------------------------------------------
    async def listen(self, queue):
        import websockets
        backoff, n = 1, 0
        while True:
            url = self.ws_urls[n % len(self.ws_urls)]
            n += 1
            try:
                async with websockets.connect(url, ssl=_ssl_context(), max_size=2 ** 24, open_timeout=20,
                                              ping_interval=20, ping_timeout=40,
                                              user_agent_header=USER_AGENT) as ws:
                    for i, (name, prog) in enumerate(PROGRAMS.items()):
                        await ws.send(json.dumps({"jsonrpc": "2.0", "id": i, "method": "logsSubscribe",
                                                  "params": [{"mentions": [prog]}, {"commitment": "confirmed"}]}))
                    subs = {}
                    while len(subs) < len(PROGRAMS):
                        r = json.loads(await ws.recv())
                        if "result" in r and "id" in r:
                            subs[r["result"]] = list(PROGRAMS)[r["id"]]
                        elif "error" in r:
                            raise RuntimeError(f"subscribe refused: {r['error']}")
                    self.log(f"subscribed on {_host(url)}")
                    backoff = 1
                    async for raw in ws:
                        m = json.loads(raw)
                        p = m.get("params") or {}
                        src = subs.get(p.get("subscription"))
                        if src is None:
                            continue
                        self.stats[f"notifications {src}"] += 1
                        v = p["result"]["value"]
                        if v.get("err") is None and D.is_create_log(src, v.get("logs") or []):
                            await queue.put((src, p["result"]["context"]["slot"], v, time.time()))
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001  any socket failure: log, back off, reconnect
                self.stats["ws reconnects"] += 1
                self.log(f"websocket {_host(url)} dropped: {type(e).__name__}; retry in {backoff}s")
                await asyncio.sleep(backoff)
                backoff = min(60, backoff * 2)

    # ---- decoding --------------------------------------------------------------------------------
    def _platform(self, cfg):
        if cfg not in self.platforms:
            acc = self.http.call("getAccountInfo", [cfg, {"encoding": "base64"}])
            pc = D.platform_config(base64.b64decode(acc["value"]["data"][0])) if acc and acc.get("value") else None
            name, web = (pc[0], pc[1]) if pc else ("", "")
            self.platforms[cfg] = (D.platform_label(name, web) if pc else "LaunchLab (config unreadable)", name, web)
        return self.platforms[cfg]

    def _decode(self, src, slot, v):
        """Blocking: the launches in one create notification, as records."""
        sig, launches, path = v["signature"], [], "logs"
        if src == "pump":
            launches = [{**x, "platform_raw": "pump"} for x in D.pump_create_from_logs(v["logs"])]
        if not launches:
            path = "transaction"
            tx = self.http.call("getTransaction", [sig, {"maxSupportedTransactionVersion": 1, "encoding": "json",
                                                         "commitment": "confirmed"}])
            if tx is None:
                self.stats[f"tx fetch failed {src}"] += 1
                return []
            launches = [{**x, "platform_raw": x["platform"]} for x in D.launches_from_tx(tx)]
        if not launches:
            self.stats[f"create seen, nothing decoded {src}"] += 1
            return []
        out = []
        for x in launches:
            if x["platform_raw"] == "pump":
                platform, declared = "pump.fun", None
            else:
                label, name, web = self._platform(x["platform_config"])
                platform, declared = label, {"name": name, "web": web, "config": x["platform_config"]}
            out.append({"ts": int(time.time()), "slot": slot, "signature": sig, "platform": platform,
                        "declared_platform": declared, "mint": x["mint"], "name": x["name"], "symbol": x["symbol"],
                        "uri": x["uri"], "creator": x.get("creator"), "quote_mint": x.get("quote_mint"),
                        "decoded_from": path})
            self.stats[f"decoded from {path} {src}"] += 1
        return out

    async def process(self, queue):
        loop = asyncio.get_running_loop()
        sem = asyncio.Semaphore(4)

        async def one(item):
            src, slot, v, _ = item
            async with sem:
                recs = await loop.run_in_executor(None, self._decode, src, slot, v)
            for rec in recs:
                k = rec["signature"] + ":" + rec["mint"]
                if k in self.seen:
                    continue
                self.seen[k] = True
                if len(self.seen) > 200_000:
                    self.seen.popitem(last=False)
                rec.update(self.shadow.route(rec))
                self.records.append(rec)
                self.first_ts = self.first_ts or rec["ts"]
                self.sink.write(json.dumps(rec, ensure_ascii=False) + "\n")
                self.sink.flush()

        pending = set()
        while True:
            item = await queue.get()
            sig = item[2]["signature"]
            if sig in self.seen_sigs:
                continue
            self.seen_sigs[sig] = True
            if len(self.seen_sigs) > 200_000:
                self.seen_sigs.popitem(last=False)
            t = asyncio.create_task(one(item))
            pending.add(t)
            t.add_done_callback(pending.discard)

    # ---- reporting -------------------------------------------------------------------------------
    def summary(self):
        recs = self.records
        now = time.time()
        span = (now - self.first_ts) / 3600 if self.first_ts else 0
        by_p = collections.Counter(r["platform"] for r in recs)
        dec = collections.Counter((r["platform"], r["decision"]) for r in recs)
        doors = [r for r in recs if r["decision"] == "door"]
        other_creator = [r for r in doors if not r.get("same_creator_as_door0")]
        cross = [r for r in doors if r["door0"]["platform"] != r["platform"]]
        L = ["<!-- generated by services/matcher/watcher/watch.py -->", "",
             f"Watched from {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(self.first_ts or now))} for {span:.2f} h "
             f"(this process up {(now - self.started) / 3600:.2f} h). Read-only; our matcher ran in shadow mode with "
             "the live rule (name-key equality, rules A, B, C, I). Rooms are those formed during the watch, all "
             "treated as live; launches before the watch started are not known, so early launches cannot match "
             "older narratives (the door share rises as the watch runs).", "",
             "| platform | launches | would be doors | new rooms | no key (refused) | door share |",
             "|---|---|---|---|---|---|"]
        for p, n in by_p.most_common():
            d = dec[(p, "door")]
            L.append(f"| {p} | {n:,} | {d:,} | {dec[(p, 'new_room')]:,} | {dec[(p, 'no_key')]:,} | {d / n:.1%} |")
        n = len(recs)
        L += [f"| **all** | **{n:,}** | **{len(doors):,}** | **{sum(1 for r in recs if r['decision'] == 'new_room'):,}**"
              f" | **{sum(1 for r in recs if r['decision'] == 'no_key'):,}** | **{len(doors) / n:.1%}** |" if n else
              "| **all** | 0 | | | | |", ""]
        if doors:
            L += [f"Of the {len(doors):,} would-be doors, {len(other_creator):,} ({len(other_creator) / len(doors):.0%}) "
                  "come from a different wallet than the room's door 0 (copies); the rest are the same wallet "
                  f"relaunching. {len(cross):,} cross platforms (for example a LaunchLab launch into a pump.fun room).",
                  ""]
        if len(recs) >= 50 and span > 0:
            half = (self.first_ts or now) + (now - (self.first_ts or now)) / 2
            for label, part in (("first half", [r for r in recs if r["ts"] < half]),
                                ("second half", [r for r in recs if r["ts"] >= half])):
                if part:
                    L.append(f"- Door share, {label} of the watch: {sum(r['decision'] == 'door' for r in part) / len(part):.1%} "
                             f"of {len(part):,}")
            L.append("")
        rooms = sorted((r for r in self.shadow.rooms if r["doors"]), key=lambda r: -r["doors"])[:20]
        if rooms:
            L += ["Most-copied narratives during the watch:", "",
                  "| door 0 (name / symbol) | platform | doors | distinct wallets | platforms |", "|---|---|---|---|---|"]
            for r in rooms:
                d0 = r["door0"]
                nm = d0["name"].replace("|", "/")
                sy = d0["symbol"].replace("|", "/")
                L.append(f"| `{nm}` / `{sy}` | {d0['platform']} | {r['doors']} | {len(r['creators'] - {None})} | "
                         + ", ".join(f"{p} {c}" for p, c in r["platforms"].most_common()) + " |")
            L.append("")
        L += ["Decoding and RPC:", ""]
        for k, v in sorted(self.stats.items()):
            L.append(f"- {k}: {v:,}")
        for k, v in sorted(self.http.calls.items()):
            L.append(f"- HTTP calls {k}: {v:,}")
        for k, v in self.http.errors.most_common(10):
            L.append(f"- HTTP errors {k}: {v:,}")
        L += ["", "LaunchLab platform names are self-declared in each PlatformConfig account (anyone can create one "
              "named StonkFun); the label groups by declared website: stonkfun.xyz as StonkFun, letsbonk.fun / "
              "bonk.fun as bonk.fun, otherwise the declared name."]
        (self.out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
        return L

    async def report(self):
        while True:
            await asyncio.sleep(self.summary_every)
            self.summary()
            n = len(self.records)
            d = sum(1 for r in self.records if r["decision"] == "door")
            self.log(f"{n} launches, {d} would-be doors")

    async def run(self):
        queue = asyncio.Queue(maxsize=10_000)
        tasks = [asyncio.create_task(self.listen(queue)), asyncio.create_task(self.process(queue)),
                 asyncio.create_task(self.report())]
        try:
            if self.minutes:
                await asyncio.sleep(self.minutes * 60)
            else:
                await asyncio.gather(*tasks)
        finally:
            for t in tasks:
                t.cancel()
            self.summary()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--minutes", type=float, default=0, help="stop after N minutes (0 = run until killed)")
    ap.add_argument("--ws", action="append", help="websocket endpoint (repeatable); default: Solana Foundation")
    ap.add_argument("--http", action="append", help="HTTP endpoint (repeatable); default: PublicNode, Foundation")
    ap.add_argument("--summary-every", type=float, default=60)
    a = ap.parse_args()
    from matcher_service import rules
    rules.check_unicode()          # same pinned tables as the service, or the keys would differ
    env = lambda k: [u.strip() for u in os.environ.get(k, "").split(",") if u.strip()]  # noqa: E731
    w = Watcher(a.out, a.ws or env("WATCHER_WS") or DEFAULT_WS, a.http or env("WATCHER_HTTP") or DEFAULT_HTTP,
                a.minutes, a.summary_every)
    asyncio.run(w.run())
    print("\n".join(w.summary()))


if __name__ == "__main__":
    main()
