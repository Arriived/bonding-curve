"""Read-only discovery probes; no historical calibration or simulation."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request


OUT = Path(__file__).resolve().parent
QUERIES = ("PNUT", "NEIRO")


def main():
    rows = []
    for query in QUERIES:
        url = f"https://api.dexscreener.com/latest/dex/search?q={query}"
        row = {"query": query, "url": url,
               "requested_at_utc": datetime.now(timezone.utc).isoformat()}
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "NarrativeResearchPhase1/1.0",
                              "Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=15) as response:
                body = response.read(4_000_001)
                row["http_status"] = response.status
                row["content_type"] = response.headers.get("Content-Type")
            if len(body) > 4_000_000:
                raise ValueError("Response exceeded the discovery size limit")
            payload = json.loads(body)
            raw_name = f"dexscreener_{query.lower()}_snapshot.json"
            (OUT / raw_name).write_bytes(body)
            pairs = payload.get("pairs") or []
            row.update(status="snapshot_only", raw_response=raw_name,
                       response_sha256=hashlib.sha256(body).hexdigest(),
                       returned_pairs=len(pairs),
                       distinct_base_assets=len({(p.get("chainId"),
                           p.get("baseToken", {}).get("address")) for p in pairs}),
                       limitations=[
                           "Keyword results are neither verified narrative members nor a complete cohort.",
                           "Pairs are venues, not independent launches or people.",
                           "Current/rolling metrics do not reconstruct historical reserves or net quote flows.",
                           "pairCreatedAt is not necessarily the original token launch time.",
                           "No empirical behavioral parameter is calibrated from this response."])
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            row.update(status="unavailable", error=f"{type(exc).__name__}: {exc}")
        rows.append(row)
    result = {
        "purpose": "Public access feasibility only; explicitly not a historical dataset",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "paid_spend": 0,
        "credentials_used": False,
        "browser_probe": {"url": "https://api.dexscreener.com/latest/dex/search?q=PNUT",
                          "result": "Web tool reported URL inaccessible"},
        "requests": rows,
        "historical_cluster_verified": False,
        "calibrated_parameters": [],
    }
    path = OUT / "data_access_probe.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(path), "requests": [
        {k: r[k] for k in ("query", "status", "returned_pairs", "error") if k in r}
        for r in rows]}, indent=2))


if __name__ == "__main__":
    main()
