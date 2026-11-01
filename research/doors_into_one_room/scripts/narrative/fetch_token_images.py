"""Fetch the original launch sample's metadata/images, with resumable local byte caches.

IPFS fallbacks preserve the CID and path; no other image corpus is substituted.
Outputs a provenance/hash manifest, including failures for every launch. Large image
bytes stay in the ignored .tmp cache. Usage: python3 scripts/narrative/fetch_token_images.py
"""
import concurrent.futures
import datetime
import hashlib
import io
import json
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image
from phash import phash_hex

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "narrative"
CACHE = ROOT.parents[1] / ".tmp" / "narrative_images"
MAX_BYTES = 12_000_000


def alternatives(url):
    parsed = urllib.parse.urlparse(url)
    path = None
    if parsed.scheme == "ipfs":
        path = (parsed.netloc + parsed.path).removeprefix("ipfs/")
    elif "/ipfs/" in parsed.path:
        path = parsed.path.split("/ipfs/", 1)[1]
    if path:
        fallback = [f"https://pump.mypinata.cloud/ipfs/{path}",
                    f"https://gateway.pinata.cloud/ipfs/{path}"]
        return list(dict.fromkeys(fallback + ([url] if parsed.scheme == "https" else [])))
    return [url]


def get_bytes(url):
    failures = []
    for resolved in alternatives(url):
        if urllib.parse.urlparse(resolved).scheme != "https":
            failures.append("non-HTTPS URI")
            continue
        key = hashlib.sha256(resolved.encode()).hexdigest()
        path = CACHE / key
        if path.exists():
            return path.read_bytes(), resolved, path
        try:
            request = urllib.request.Request(resolved, headers={"User-Agent": "bonding-curve-research/1.0"})
            with urllib.request.urlopen(request, timeout=12) as response:
                data = response.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise ValueError("download exceeds byte limit")
            path.write_bytes(data)
            return data, resolved, path
        except Exception as error:
            failures.append(f"{resolved}: {error}")
    raise ValueError("; ".join(failures))


def metadata(uri):
    try:
        data, resolved, _ = get_bytes(uri)
        obj = json.loads(data)
        image = obj.get("image") or obj.get("image_url")
        if not isinstance(image, str) or not image:
            raise ValueError("metadata has no image URI")
        return {"metadata_resolved_uri": resolved, "metadata_sha256": hashlib.sha256(data).hexdigest(),
                "image_uri": image}
    except Exception as error:
        return {"error": str(error)}


def image_record(uri):
    try:
        data, resolved, path = get_bytes(uri)
        with Image.open(io.BytesIO(data)) as img:
            width, height = img.size
            if width * height > 40_000_000:
                raise ValueError("image exceeds decoded pixel limit")
            value = phash_hex(img)
        return {"image_resolved_uri": resolved, "image_sha256": hashlib.sha256(data).hexdigest(),
                "width": width, "height": height, "phash": value, "cache_key": path.name}
    except Exception as error:
        return {"image_error": str(error)}


def parallel(items, function, label):
    result = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as executor:
        jobs = {executor.submit(function, item): item for item in sorted(items)}
        for future in concurrent.futures.as_completed(jobs):
            result[jobs[future]] = future.result()
            if len(result) % 100 == 0:
                print(f"{label}: {len(result)}/{len(jobs)}", flush=True)
    return result


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    launches = [json.loads(line) for line in (OUT / "pump_launches.jsonl").read_text(encoding="utf-8").splitlines()]
    metas = parallel({row["uri"] for row in launches}, metadata, "metadata")
    images = parallel({row["image_uri"] for row in metas.values() if "image_uri" in row}, image_record, "images")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rows = []
    for launch in launches:
        meta = metas[launch["uri"]]
        row = {"mint": launch["mint"], "metadata_uri": launch["uri"], "fetched_at_utc": now, **meta}
        if "image_uri" in meta:
            row.update(images[meta["image_uri"]])
        rows.append(row)
    (OUT / "token_images.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                                            encoding="utf-8", newline="\n")
    summary = {"fetched_at_utc": now, "launches": len(rows), "unique_metadata_uris": len(metas),
               "unique_image_uris": len(images), "launches_with_phash": sum("phash" in r for r in rows),
               "unique_image_sha256": len({r["image_sha256"] for r in rows if "phash" in r}),
               "metadata_failures": sum("error" in r for r in rows),
               "image_failures": sum("image_error" in r for r in rows)}
    (OUT / "image_fetch_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2))
    return 0 if summary["launches_with_phash"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
