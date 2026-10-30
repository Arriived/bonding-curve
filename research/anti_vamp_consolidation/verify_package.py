"""Read-only verification of the published evidence; no economic reruns."""
from collections import Counter
from pathlib import Path
import csv
import gzip
import hashlib
import json

HERE = Path(__file__).resolve().parent

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def check(condition, message):
    if not condition:
        raise RuntimeError(message)

def check_rows(path, expected_rows, expected_seeds, expected_per_seed):
    counts = Counter()
    with gzip.open(path, 'rt', encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f):
            counts[int(row['seed'])] += 1
    check(sum(counts.values()) == expected_rows, f'Wrong row count: {path.name}')
    check(set(counts) == set(expected_seeds), f'Wrong seed set: {path.name}')
    check(set(counts.values()) == {expected_per_seed}, f'Uneven seed rows: {path.name}')
    return sum(counts.values())

manifest = read(HERE / 'PACKAGE_MANIFEST.json')
for rel, sha in manifest['sha256'].items():
    path = HERE / rel
    check(path.is_file() and digest(path) == sha, f'Package hash mismatch: {rel}')

summary = {'status': 'passed', 'package_files_verified': len(manifest['sha256'])}
for dirname, name, worlds, start, observations, per_seed in (
    ('anti_vamp_study', 'anti_vamp', 11700, 50000, 58500, 585),
    ('c_permissionless_study', 'c_followup', 5600, 30000, 22400, 224),
):
    output = HERE / 'outputs' / dirname
    confirmation = read(output / 'confirmation_manifest.json')
    check(confirmation['status'] == 'complete', f'Incomplete confirmation: {dirname}')
    check(confirmation['worlds'] == worlds and confirmation['seed_count'] == 100,
          f'Unexpected study size: {dirname}')
    frozen = read(output / 'frozen.json')
    for rel, sha in frozen['source_hashes'].items():
        check(digest(HERE / 'work' / name / rel) == sha, f'Frozen source mismatch: {name}/{rel}')
    report = 'ANTI_VAMP_FINDINGS.md' if name == 'anti_vamp' else 'C_PERMISSIONLESS_FINDINGS.md'
    validation = read(output / 'final_validation.json')
    check(validation['findings_sha256'] == digest(HERE / 'outputs' / report), f'Report mismatch: {report}')
    rows = check_rows(output / 'confirmation.csv.gz', observations, range(start, start + 100), per_seed)
    summary[name] = {'worlds': worlds, 'seeds': 100, 'checkpoint_rows_verified': rows}

anti = HERE / 'outputs/anti_vamp_study'
summary['anti_vamp']['minute_rows_verified'] = check_rows(
    anti / 'minute_flows.csv.gz', 702000, range(50000, 50100), 7020)
replays = read(anti / 'replays.json')
check(len(replays) == 3 and all(x['passed'] for x in replays), 'Recorded anti-vamp replay failure')
prior = read(HERE / 'outputs/c_permissionless_study/replay_audit.json')
check(prior['status'] == 'passed' and all(x['passed'] for x in prior['worlds']),
      'Recorded permissionless replay failure')
summary['recorded_replays_verified'] = len(replays) + len(prior['worlds'])
print(json.dumps(summary, indent=2))
