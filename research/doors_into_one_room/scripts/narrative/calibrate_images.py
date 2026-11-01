"""Sequential text+image replay on real token hashes, with the text study's fixed vamp population.

Run after fetch_token_images.py. Labels are assistant narrative judgements; never
infer semantic ground truth from a Hamming match. Missing images contribute no points.
Usage: python3 scripts/narrative/calibrate_images.py
"""
import collections
import csv
import json
from pathlib import Path

import calibrate_text as T
import matcher as M
from calibration_common import ground_truth, verify_image_labels

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs' / 'narrative'
SCRIPTS = ROOT / 'scripts' / 'narrative'
THRESHOLDS = [0, 2, 4, 6, 8, 10, 12, 14, 16]


def replay(rows, threshold, weak=None):
    rooms = []
    index = collections.defaultdict(set)
    routes = []
    # Isolate image quality, as the text benchmark does. Mature-room histories are
    # absent from this replay; zero placeholder reserves must not become observations.
    benchmark_grace = max(r['block_time'] for r in rows) - min(r['block_time'] for r in rows) + 1
    params = {'image_routing': 'shadow' if threshold is None else 'on',
              'live_new_seconds': benchmark_grace}
    if threshold is not None:
        params.update(image_strong_max_hamming=threshold, image_weak_max_hamming=threshold if weak is None else weak)
    for j, r in enumerate(rows):
        candidates = set()
        for key in T.probe_keys(r):
            candidates.update(index.get(key, ()))
        inp = {'now': r['block_time'], 'candidate': {'name': r['name'], 'symbol': r['symbol'],
               'phash': r.get('phash') if threshold is not None else None},
               'rooms': [rooms[k] for k in sorted(candidates)], 'params': params}
        decision = M.decide(inp)
        face = {'name': r['name'], 'symbol': r['symbol'],
                'phash': r.get('phash') if threshold is not None else None, 'launch_index': j}
        if decision['decision'] == 'new_room':
            rid = len(rooms)
            rooms.append({'room_id': rid, 'status': 0, 'created_at': r['block_time'],
                          'reserve': 0, 'last_trade_at': r['block_time'], 'faces': [face], 'root': j})
            for key in T.index_keys(r):
                index[key].add(rid)
        else:
            rid = decision['room_id']
            rooms[rid]['faces'].append(face)
            for key in (('s', r['sk']), ('n', r['nk'])):
                if key[1]:
                    index[key].add(rid)
            evidence = next(x for x in decision['evaluated'] if x['room_id'] == rid)
            routes.append({'candidate': j, 'root': rooms[rid]['root'], 'text': evidence['text'],
                           'hamming': evidence['hamming'], 'matched_face': evidence['face'],
                           'matched_launch': rooms[rid]['faces'][evidence['face']]['launch_index']})
    return routes, len(rooms)


def main():
    rows = T.load(OUT / 'pump_launches.jsonl')
    hashes = {r['mint']: r for r in map(json.loads, (OUT / 'token_images.jsonl').read_text(encoding='utf-8').splitlines())}
    verify_image_labels(hashes,SCRIPTS/'labels_images_assistant.csv')
    for r in rows:
        r['phash'] = hashes[r['mint']].get('phash')
    # Freeze the denominator at the original text labels, even when extra route judgements are added.
    _, certain_v, population, _ = ground_truth(rows, SCRIPTS / 'labels_assistant.csv')
    probability, _, _, labels = ground_truth(rows, SCRIPTS / 'labels_assistant.csv',
                                            SCRIPTS / 'labels_images_assistant.csv')
    results, review = [], {}
    for threshold, weak in [(None,None), *((t,t) for t in THRESHOLDS), (10,16)]:
        routes, rooms = replay(rows, threshold, weak)
        correct = sum(probability(rows[r['root']], rows[r['candidate']]) for r in routes)
        lower = sum(probability(rows[r['root']], rows[r['candidate']], True) for r in routes)
        cc = sum(probability(rows[r['root']], rows[r['candidate']]) for r in routes if r['candidate'] in certain_v)
        assisted = [r for r in routes if r['text'] not in ('T3', 'T2n')]
        ac = sum(probability(rows[r['root']], rows[r['candidate']]) for r in assisted)
        al = sum(probability(rows[r['root']], rows[r['candidate']], True) for r in assisted)
        known = sum(T.pair_key(rows[r['root']], rows[r['candidate']]) in labels or
                    rows[r['root']]['uri'] == rows[r['candidate']]['uri'] or
                    T.vkey(rows[r['root']]) == T.vkey(rows[r['candidate']]) for r in assisted)
        assisted_labels = []
        for route in assisted:
            a, b = rows[route['root']], rows[route['candidate']]
            certain = a['uri'] == b['uri'] or T.vkey(a) == T.vkey(b)
            assisted_labels.append('S' if certain else labels.get(T.pair_key(a,b),'unlabelled'))
        label_counts = {label: assisted_labels.count(label) for label in ('S','D','U','unlabelled')}
        result = dict(strong=threshold, weak=weak, assisted_labels=label_counts,
                      rooms=rooms, routed=len(routes), correct=correct, precision=correct / max(1,len(routes)),
                      pessimistic=lower / max(1,len(routes)), recall=correct / population,
                      certain_recall=cc / len(certain_v), assisted=len(assisted),
                      assisted_precision=ac / max(1,len(assisted)), assisted_pessimistic=al / max(1,len(assisted)),
                      assisted_labelled_or_certain=known)
        results.append(result)
        for route in assisted:
            a,b=rows[route['root']],rows[route['candidate']]
            key=T.pair_key(a,b)
            review.setdefault(key, {'a':key[0],'b':key[1],'label':labels.get(key,''),
                                   'root_name':a['name'],'root_symbol':a['symbol'],
                                   'candidate_name':b['name'],'candidate_symbol':b['symbol'],
                                   'root_mint':a['mint'],'candidate_mint':b['mint'],
                                   'hamming':route['hamming'],'strong_first_seen':threshold})
        print(f"threshold {threshold}: {result}", flush=True)
    with (OUT / 'image_routes_to_review.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(next(iter(review.values())).keys()) if review else ['a','b','label'],lineterminator='\n')
        writer.writeheader();writer.writerows(review.values())
    summary={'launches':len(rows),'images_available':sum(bool(r['phash']) for r in rows),
             'fixed_expected_vamps':population,'certain_vamps':len(certain_v),
             'liveness_assumption':'all rooms live; image-only benchmark, not current-gate recall',
             'results':results}
    (OUT/'image_calibration.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8', newline="\n")
    lines=['<!-- generated by scripts/narrative/calibrate_images.py -->','# Real-token image routing calibration','',
           f"Original sample: {len(rows)} launches; {summary['images_available']} have decoded images. "
           f"Same fixed expected-vamp denominator as the text calibration: {population:.3f}; "
           f"certain-vamp denominator {len(certain_v)}. Missing images score zero. "
           "Additional image-aware pair judgements are by the assistant, not a human; "
           "the CSV records the inspected root/candidate image hashes and rationale. "
           "The original text population stays fixed for comparisons.",'',
           '| strong / weak Hamming | routed | precision (est.) | pessimistic | recall (est.) | certain recall | image-assisted routes | assisted precision (est.) | assisted pessimistic | assisted labelled/certain |',
           '|---|---|---|---|---|---|---|---|---|---|']
    for r in results:
        threshold='text only' if r['strong'] is None else f"{r['strong']} / {r['weak']}"
        lines.append(f"| {threshold} | {r['routed']} | {r['precision']:.2%} | {r['pessimistic']:.2%} | "
                     f"{r['recall']:.2%} | {r['certain_recall']:.2%} | {r['assisted']} | "
                     f"{r['assisted_precision']:.2%} | {r['assisted_pessimistic']:.2%} | {r['assisted_labelled_or_certain']} |")
    lines += ['', '| strong / weak | assisted S | D | U | unlabelled | assisted S/(S+D) |',
              '|---|---|---|---|---|---|']
    for r in results[1:]:
        counts=r['assisted_labels'];den=counts['S']+counts['D']
        lines.append(f"| {r['strong']} / {r['weak']} | {counts['S']} | {counts['D']} | {counts['U']} | "
                     f"{counts['unlabelled']} | {counts['S']/max(1,den):.2%} |")
    lines+=['','Replayed in launch order through matcher.decide, including multi-face scoring and ties. '
            'Every room is explicitly treated as live to isolate image quality, as in the text benchmark. '
            'This uses a calibration-only age override covering the sample, independently of the production '
            'grace window. Mature-room reserve/volume histories are unavailable; placeholder reserves '
            'are never treated as measured room state. These figures are conditional on liveness, not '
            'end-to-end recall with the current gate. No pre-window rooms are assumed. '
            'Ground truth follows the text calibration: identical folded '
            'identity/metadata URI is certain; assistant S/D/U narrative labels judge other pairs. '
            'Unlabelled routes take their text-stratum rate; pessimistic uses its Wilson lower bound '
            'and counts U as wrong. These are estimates, with selection bias possible for image-assisted '
            'unlabelled pairs. Image labels were collected from a union of assisted routes, not a held-out '
            'validation set. Estimates remain in-sample. Incremental assisted precision is reported separately so existing exact '
            'routes cannot conceal poor image precision. The review CSV exposes every assisted narrative pair.']
    strict=results[1];base=results[0]
    lines += ['', f"At Hamming 0/0, combined recall is {strict['recall']:.2%} versus text-only "
              f"{base['recall']:.2%}, a {(strict['recall']-base['recall'])*100:.2f} percentage-point gain; "
              f"precision falls from {base['precision']:.2%} to {strict['precision']:.2%}. "
              "No tested threshold reaches the text point's precision. The justified production choice "
              "is to retain shadow mode; its active image-recall gain is zero. Enabling the measured "
              "points would require accepting more permanent false-positive routes or revising the image rule."]
    (OUT/'image_calibration.md').write_text('\n'.join(lines)+'\n',encoding='utf-8', newline="\n")


if __name__=='__main__':
    main()
