"""Fetch the public pump.fun launch dataset we measure against, and verify it against chain.

Our own collectors (`watcher.watch`, `watcher.backfill`) reach roughly 95,000 launches over three days before
free-RPC retention and rate limits bite. This dataset is 2,713,057 launches over 67 days with the fields our
routing needs (name, symbol, uri, creator, t0) plus outcomes we cannot observe at all (graduated, rugged,
peak reserve, creator buy and sell behaviour). It supersedes our own collection for every measurement except
coverage of the current week, which it does not have (CORRECTIONS section 36).

  source   https://huggingface.co/datasets/loopholetape/pumpfun-launches
  licence  CC BY 4.0 - attribution required in anything published from it
  size     67 daily Parquet files, about 372 MB, 43 columns
  window   2026-08-31 to 2026-11-05

NOT committed to this repository: 372 MB of third-party data does not belong in git, and the licence wants
attribution rather than redistribution. This script re-fetches it.

Two documented defects matter when reading it, and neither touches the fields we route on:
  - the `legacy` subset (before 2026-09-27) predates a decoder fix, so about 48% of BUY rows and 32% of SOL
    entering curves are undercounted. Name, symbol, creator and launch time are unaffected.
  - `rugged` is the project's own observation rule, not verified fraud, and the early `f10_`/`f60_` features are
    sampled on 81.6% of launches with heavy selection bias. Treat those as unusable; we do not use them.

Usage:
  python3 scripts/fetch_external_dataset.py --out DIR            # download
  python3 scripts/fetch_external_dataset.py --out DIR --audit 20 # re-verify N rows against chain
Needs network access to huggingface.co and us.aws.cdn.hf.co.
"""
import argparse
import datetime
import json
import random
import ssl
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BASE = "https://huggingface.co/datasets/loopholetape/pumpfun-launches/resolve/main/data"
SUBSETS = {"launches": (datetime.date(2026, 9, 27), datetime.date(2026, 11, 5)),
           "launches_legacy": (datetime.date(2026, 8, 31), datetime.date(2026, 9, 26))}
RPC = "https://api.mainnet-beta.solana.com"


def download(out):
    out.mkdir(parents=True, exist_ok=True)
    got = skipped = 0
    for subset, (a, b) in SUBSETS.items():
        d = out / subset
        d.mkdir(exist_ok=True)
        day = a
        while day <= b:
            f = d / f"{day}.parquet"
            if f.exists() and f.stat().st_size > 0:
                skipped += 1
            else:
                url = f"{BASE}/{subset}/{day}.parquet"
                subprocess.run(["curl", "-sSL", "--max-time", "300", "-o", str(f), url], check=False)
                got += 1
                print(f"  {subset}/{day}.parquet  {f.stat().st_size / 1e6:.1f} MB", flush=True)
            day += datetime.timedelta(days=1)
    print(f"\n{got} downloaded, {skipped} already present")
    try:
        import pyarrow.parquet as pq
    except ImportError:
        print("install pyarrow to count rows")
        return
    total = 0
    for subset in SUBSETS:
        fs = sorted((out / subset).glob("*.parquet"))
        n = sum(pq.ParquetFile(str(f)).metadata.num_rows for f in fs)
        print(f"  {subset:16} {len(fs):>3} files {n:>10,} rows")
        total += n
    print(f"  {'TOTAL':16} {'':>3}       {total:>10,} rows")
    if total != 2_713_057:
        print(f"  WARNING: expected 2,713,057 rows; the dataset may have been republished")


def audit(out, n):
    """Re-decode N random launches from chain with our own decoder and compare. The dataset's window ends before
    ours begins, so there is no shared mint to cross-check: this is the only available provenance test."""
    import pyarrow.parquet as pq
    from watcher import decode as D
    ctx = ssl.create_default_context(cafile="/root/.ccr/ca-bundle.crt"
                                     if Path("/root/.ccr/ca-bundle.crt").exists() else None)

    def call(method, params, tries=5):
        for a in range(tries):
            try:
                req = urllib.request.Request(
                    RPC, json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                    {"content-type": "application/json", "user-agent": "dataset-audit/1"})
                j = json.loads(urllib.request.urlopen(req, timeout=30, context=ctx).read())
                if "result" in j:
                    return j["result"]
            except Exception:
                pass
            time.sleep(1.5 * (a + 1))
        return None

    files = sorted((out / "launches").glob("*.parquet"))
    if not files:
        sys.exit("nothing downloaded yet")
    rows = pq.read_table(str(files[-1]), columns=["mint", "creator", "name", "symbol", "uri"]).to_pylist()
    random.Random("audit").shuffle(rows)
    ok = bad = unver = 0
    for row in rows[:n]:
        sigs = call("getSignaturesForAddress", [row["mint"], {"limit": 1000}])
        tx = call("getTransaction", [sigs[-1]["signature"],
                                     {"maxSupportedTransactionVersion": 1, "encoding": "json"}]) if sigs else None
        mine = next((x for x in D.launches_from_tx(tx) if x["mint"] == row["mint"]), None) if tx else None
        if mine is None:
            unver += 1
            continue
        if all(mine.get(f) == row[f] for f in ("name", "symbol", "uri", "creator")):
            ok += 1
        else:
            bad += 1
            print(f"  MISMATCH {row['mint']}")
            for f in ("name", "symbol", "uri", "creator"):
                if mine.get(f) != row[f]:
                    print(f"      {f}: dataset={row[f]!r} chain={mine.get(f)!r}")
    print(f"\n{ok} match chain exactly, {bad} mismatch, {unver} unverifiable (creation past RPC retention)")
    if bad:
        print("A mismatch means the dataset's decoding differs from ours. Investigate before relying on it.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--audit", type=int, metavar="N", help="re-verify N rows against chain instead of downloading")
    a = ap.parse_args()
    out = Path(a.out)
    if a.audit:
        audit(out, a.audit)
    else:
        download(out)


if __name__ == "__main__":
    main()
