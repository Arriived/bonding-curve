"""Shared ground-truth estimator matching calibrate_text.py's fixed population and labels."""
import collections
import csv
import json
from pathlib import Path

import calibrate_text as T


def verify_image_labels(images, path):
    """Do not reuse image-aware judgements after mutable image bytes change."""
    for row in csv.DictReader(Path(path).open(encoding='utf-8', newline='')):
        for prefix in ('root','candidate'):
            expected=row.get(prefix+'_image_sha256')
            if expected and images[row[prefix+'_mint']].get('image_sha256')!=expected:
                raise ValueError('Image bytes changed; re-review image label for '+row[prefix+'_mint'])


def ground_truth(rows, labels_path, extra_labels_path=None):
    labels = {}
    for path in (labels_path, extra_labels_path):
        if path and Path(path).exists():
            for row in csv.DictReader(Path(path).open(encoding="utf-8", newline="")):
                if row['label'] in ('S', 'D', 'U'):
                    labels[tuple(sorted((row['a'], row['b'])))] = row['label']
    index = collections.defaultdict(list)
    uris = collections.defaultdict(list)
    earlier = []
    pairs = {}
    for j, r in enumerate(rows):
        candidates = set(uris.get(r['uri'], ()))
        for key in T.probe_keys(r):
            candidates.update(index.get(key, ()))
        matches = sorted(i for i in candidates if rows[i]['uri'] == r['uri'] or
                         T.matches(r, rows[i], 'T1') or T.matches(r, rows[i], 'floor') or
                         T.matches(r, rows[i], 'raw-symbol'))
        earlier.append(matches)
        for i in matches:
            if rows[i]['uri'] != r['uri'] and T.vkey(rows[i]) != T.vkey(r):
                stratum = T.stratum(rows[i], r)
                if stratum:
                    pairs.setdefault(T.pair_key(rows[i], r), stratum)
        for key in T.index_keys(r):
            index[key].append(j)
        uris[r['uri']].append(j)
    rates = {}
    for stratum in T.STRATA:
        labs = [labels[key] for key, value in pairs.items() if value == stratum and key in labels]
        same, different = labs.count('S'), labs.count('D')
        rates[stratum] = (same / (same + different) if same + different else 0,
                           T.wilson(same, same + different)[0])

    def certain(a, b):
        return a['uri'] == b['uri'] or T.vkey(a) == T.vkey(b)

    def probability(a, b, lower=False):
        if certain(a, b):
            return 1.0
        label = labels.get(T.pair_key(a, b))
        if label in ('S', 'D'):
            return float(label == 'S')
        stratum = T.stratum(a, b)
        if stratum is None or (lower and label == 'U'):
            return 0.0
        return rates[stratum][int(lower)]

    population = sum(max((probability(rows[i], rows[j]) for i in members), default=0)
                     for j, members in enumerate(earlier))
    certain_vamps = {j for j, members in enumerate(earlier)
                     if any(certain(rows[i], rows[j]) for i in members)}
    return probability, certain_vamps, population, labels
