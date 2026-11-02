"""Read-only OSV scan of both pinned Rust dependency lockfiles.

Uses OSV's documented crates.io query API, not a local cargo-audit installation.
Results identify advisories to investigate, not proof of exploitability in SBF.
"""
import argparse
import hashlib
import json
import time
import tomllib
import urllib.error
import urllib.request
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='fail on vulnerabilities or unreviewed notices')
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
    for start in range(0, len(keys), 100):
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
    report = {'scan_at_utc': datetime.now(timezone.utc).isoformat(), 'service': API,
              'method': 'OSV querybatch, exact crates.io versions; all lockfile dependencies including dev/host',
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
