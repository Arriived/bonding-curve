"""Read-only OSV scan of both pinned Rust dependency lockfiles.

Uses OSV's documented crates.io query API, not a local cargo-audit installation.
Results identify advisories to investigate, not proof of exploitability in SBF.

`--bulk` uses OSV's official bulk export of every crates.io record instead
(https://osv-vulnerabilities.storage.googleapis.com/crates.io/all.zip, the export the
query API serves from) and evaluates each exact lockfile version against each record's
affected `versions` and SEMVER `ranges` locally. Use it where api.osv.dev is unreachable.
The export's GCS generation, Last-Modified and SHA-256 are recorded in the report.
"""
import argparse
import hashlib
import io
import json
import re
import time
import tomllib
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = 'https://api.osv.dev/v1'


def request(path, body=None):
    for attempt in range(4):
        req = urllib.request.Request(API + path, None if body is None else json.dumps(body).encode(),
                                     {'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise
            time.sleep(2 ** attempt)


BULK = 'https://osv-vulnerabilities.storage.googleapis.com/crates.io/all.zip'


def semver(v):
    """Sortable key per SemVer 2.0.0 precedence: release > pre-release; build metadata ignored."""
    m = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?', v)
    if not m:
        raise ValueError(f'not a semver version: {v!r}')
    pre = m[4]
    pre_key = (1,) if pre is None else (0, *[(0, int(x), '') if x.isdigit() else (1, 0, x)
                                               for x in pre.split('.')])
    return (int(m[1]), int(m[2]), int(m[3]), pre_key)


def affected_by(record, name, version):
    """OSV semantics for one package version: listed explicitly, or inside a SEMVER range."""
    v = semver(version)
    for a in record.get('affected', []):
        if a['package'].get('ecosystem') != 'crates.io' or a['package']['name'] != name:
            continue
        if version in a.get('versions', []):
            return True
        for r in a.get('ranges', []):
            if r['type'] != 'SEMVER':
                raise ValueError(f"{record['id']}: unsupported range type {r['type']}")
            hit = False
            for e in r['events']:  # events are sorted; walk them as OSV's reference matcher does
                if 'introduced' in e:
                    if e['introduced'] == '0' or semver(e['introduced']) <= v:
                        hit = True
                elif 'fixed' in e:
                    if semver(e['fixed']) <= v:
                        hit = False
                elif 'last_affected' in e:
                    if semver(e['last_affected']) < v:
                        hit = False
                elif 'limit' in e:
                    if semver(e['limit']) <= v:
                        hit = False
            if hit:
                return True
    return False


def bulk_records():
    with urllib.request.urlopen(BULK, timeout=120) as response:
        raw = response.read()
        source = {'url': BULK, 'last_modified': response.headers.get('Last-Modified'),
                  'gcs_generation': response.headers.get('x-goog-generation'),
                  'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    records = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for n in z.namelist():
            r = json.loads(z.read(n))
            records[r['id']] = r
    source['records'] = len(records)
    source['withdrawn_excluded'] = sum(1 for r in records.values() if r.get('withdrawn'))
    return {k: r for k, r in records.items() if not r.get('withdrawn')}, source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='fail on vulnerabilities or unreviewed notices')
    parser.add_argument('--bulk', action='store_true', help='use the OSV bulk export instead of api.osv.dev')
    args = parser.parse_args()
    packages = {}
    locks = {}
    for path in [ROOT / 'Cargo.lock', ROOT / 'test-fixtures/launch_proxy/Cargo.lock']:
        label = path.relative_to(ROOT).as_posix()
        locks[label] = hashlib.sha256(path.read_bytes()).hexdigest()
        for p in tomllib.loads(path.read_text())['package']:
            if p.get('source', '').startswith('registry+'):
                packages.setdefault((p['name'], p['version']), []).append(label)
    keys = sorted(packages)
    matches = []
    source = {'url': API}
    if args.bulk:
        all_records, source = bulk_records()
        for key in keys:
            ids = sorted(i for i, r in all_records.items() if affected_by(r, *key))
            if ids:
                matches.append({'name': key[0], 'version': key[1], 'lockfiles': packages[key],
                                'advisories': ids})
    for start in range(0, len(keys) if not args.bulk else 0, 100):
        batch = keys[start:start + 100]
        queries = [{'package': {'name': name, 'ecosystem': 'crates.io'}, 'version': version}
                   for name, version in batch]
        rows = request('/querybatch', {'queries': queries})['results']
        assert len(rows) == len(batch)
        for key, row in zip(batch, rows):
            assert not row.get('next_page_token'), 'OSV pagination needs an explicit follow-up'
            if row.get('vulns'):
                matches.append({'name': key[0], 'version': key[1], 'lockfiles': packages[key],
                                'advisories': [v['id'] for v in row['vulns']]})
    ids = sorted({id for row in matches for id in row['advisories']})
    if args.bulk:
        records = {id: all_records[id] for id in ids}
    else:
        with ThreadPoolExecutor(max_workers=4) as pool:
            records = dict(zip(ids, pool.map(lambda id: request('/vulns/' + id), ids)))
    policy = json.loads((ROOT / 'dependency-policy.json').read_text())
    accepted = {(r['name'], r['version'], r['advisory']) for r in policy['reviewed_maintenance_notices']}
    unreviewed = []
    for row in matches:
        for id in row['advisories']:
            affected = [a for a in records[id].get('affected', [])
                        if a['package']['name'] == row['name']]
            maintenance_only = bool(affected) and all(
                a.get('database_specific', {}).get('informational') == 'unmaintained'
                for a in affected)
            if not maintenance_only or (row['name'], row['version'], id) not in accepted:
                unreviewed.append({'name': row['name'], 'version': row['version'], 'advisory': id})
    report = {'scan_at_utc': datetime.now(timezone.utc).isoformat(),
              'service': BULK if args.bulk else API, 'source': source,
              'method': ('OSV bulk export, local exact-version evaluation of versions/SEMVER ranges'
                         if args.bulk else 'OSV querybatch, exact crates.io versions')
                        + '; all lockfile dependencies including dev/host',
              'lock_sha256': locks, 'unique_registry_packages': len(keys),
              'matches': matches, 'records': records, 'unreviewed': unreviewed}
    (ROOT / 'verification/dependency_audit.json').write_text(json.dumps(report, indent=2) + '\n',
                                                          encoding='utf-8', newline='\n')
    print(f'Scanned {len(keys)} exact package versions; {len(matches)} package matches, {len(ids)} advisory IDs.')
    for row in matches:
        summaries = '; '.join(records[id].get('summary', id) for id in row['advisories'])
        print(f"{row['name']} {row['version']}: {summaries}")
    if args.check and unreviewed:
        raise SystemExit('Dependency policy rejected: ' + json.dumps(unreviewed))
    if args.check:
        print('Dependency policy passed: no vulnerabilities or unreviewed notices.')


if __name__ == '__main__':
    main()
