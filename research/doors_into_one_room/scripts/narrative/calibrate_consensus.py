"""Offline k-of-n measurement using real cached metadata/hashes and text labels.

No network, image decoding, synthetic launches or financial-state placeholders.
V1 never imports this module. The six-signal study and image-free ablation are
conditional all-live metadata benchmarks, not production full-gate measurements.
"""
import collections
import csv
import hashlib
import itertools
import json
import math
import re

import calibrate_text as T
import matcher as M
from audit_liveness_brief import OUT, ROOT
from calibrate_social import dump, load_inputs
from calibration_common import ground_truth
from label_dependency import metadata_text_routes

SIGNALS = ('name_equal','symbol_equal','x_post','image_h0','fuzzy_name','symbol_edit1')
NAME, SYMBOL, POST, IMAGE, FUZZY, EDIT = (1 << i for i in range(len(SIGNALS)))
ALL = (1 << len(SIGNALS))-1
NO_IMAGE = ALL ^ IMAGE
FUZZY_JACCARD = M.DEFAULTS['jaccard_min']
EDIT_MIN = M.DEFAULTS['symbol_edit1_min_len']


def signal_mask(a,b):
    mask = 0
    if a['nk'] and a['nk']==b['nk']:
        mask |= NAME
    if a['sk'] and a['sk']==b['sk']:
        mask |= SYMBOL
    if a['social']['x_post'] & b['social']['x_post']:
        mask |= POST
    if a['hash_int'] is not None and b['hash_int'] is not None and a['hash_int']==b['hash_int']:
        mask |= IMAGE
    common = a['nt'] & b['nt']
    union = a['nt'] | b['nt']
    if common and max(map(len,common))>=4 and len(common)/len(union)>=FUZZY_JACCARD:
        mask |= FUZZY
    if min(len(a['sk']),len(b['sk']))>=EDIT_MIN and M.damerau1(a['sk'],b['sk']):
        mask |= EDIT
    return mask


def text_rank(a,b):
    tier,_ = M.text_tier(a,b,M.DEFAULTS,fuzzy=False)
    return M.TIER_RANK[tier] if tier in {'T3','T2n'} else 0


def attach_hashes(rows,snapshot):
    manifest = {r['mint']:r for r in map(json.loads,(OUT/'token_images.jsonl').read_text(encoding='utf-8').splitlines())}
    for r in rows:
        record = manifest[r['mint']]
        cached = snapshot[r['uri']]
        if cached.get('sha256') and record.get('metadata_sha256'):
            assert cached['sha256']==record['metadata_sha256'], r['mint']
        value = record.get('phash')
        if value is not None and not re.fullmatch('[0-9a-fA-F]{16}',value):
            raise ValueError('Malformed recorded image hash: '+r['mint'])
        r['hash_int'] = int(value,16) if value is not None else None


def truth_source(a,b,labels,exclude_missing=False):
    if T.vkey(a)==T.vkey(b):
        return 'identity_definition'
    if a['uri']==b['uri'] and (a['uri'] or not exclude_missing):
        return 'uri_definition' if a['uri'] else 'legacy_empty_uri_definition'
    label = labels.get(T.pair_key(a,b))
    if label in {'S','D'}:
        return 'assistant_'+label
    if T.stratum(a,b) is None:
        return 'unsupported_zero_credit'
    return 'assistant_U_stratum_estimate' if label=='U' else 'unlabelled_stratum_estimate'


def build_pairs(rows,probability,labels):
    """Indexed union of actual launch pairs, with an implicit zero-mask remainder.

    Text index includes all original estimator-supported relations, including
    URI/floor/raw-symbol. Image/post indexes add pairs invisible to text. All
    six triggering predicates are checked exactly after candidate generation.
    """
    text_index = collections.defaultdict(list)
    by_uri, by_hash, by_post = (collections.defaultdict(list) for _ in range(3))
    pair_masks = []
    negative_hist = [0.0]*(ALL+1)
    d_hist = [0]*(ALL+1)
    source_counts = collections.Counter()
    d_identities = set()
    all_positive_weight = 0.0
    examined = 0
    for j,row in enumerate(rows):
        candidates = set(by_uri[row['uri']])
        for key in T.probe_keys(row):
            candidates.update(text_index[key])
        if row['hash_int'] is not None:
            candidates.update(by_hash[row['hash_int']])
        for post in row['social']['x_post']:
            candidates.update(by_post[post])
        masks = {}
        for i in sorted(candidates):
            a = rows[i]
            mask = signal_mask(a,row)
            p = probability(a,row)
            all_positive_weight += p
            examined += 1
            if mask:
                masks[i] = mask
                negative_hist[mask] += 1-p
                source_counts[truth_source(a,row,labels)] += 1
            if p==0 and labels.get(T.pair_key(a,row))=='D':
                d_hist[mask] += 1
                d_identities.add(T.pair_key(a,row))
        pair_masks.append(masks)
        for key in T.index_keys(row):
            text_index[key].append(j)
        by_uri[row['uri']].append(j)
        if row['hash_int'] is not None:
            by_hash[row['hash_int']].append(j)
        for post in row['social']['x_post']:
            by_post[post].append(j)
    n = len(rows)*(len(rows)-1)//2
    negative_total = n-all_positive_weight
    negative_hist[0] = negative_total-sum(negative_hist[1:])
    assert negative_hist[0]>=0
    # Independently expand every directly labelled D identity pair to all real
    # launch pairs. The D-only frame must include zero-mask pairs as well.
    identities=collections.defaultdict(list)
    for j,row in enumerate(rows):
        identities[T.vkey(row)].append(j)
    all_D=set()
    for (a,b),label in labels.items():
        if label=='D':
            for i in identities[a]:
                for j in identities[b]:
                    if i!=j and probability(rows[min(i,j)],rows[max(i,j)])==0:
                        all_D.add((min(i,j),max(i,j)))
    assert sum(d_hist)==len(all_D), 'D-labelled frame lost real zero-mask launch pairs'
    return pair_masks, {'all_earlier_launch_pairs':n,'indexed_pairs_examined':examined,
        'signal_union_pairs':sum(len(x) for x in pair_masks),
        'signal_union_truth_sources':dict(source_counts),
        'estimated_negative_pair_weight':negative_total,
        'estimated_negative_mask_histogram':negative_hist,
        'direct_D_launch_pairs':sum(d_hist),'direct_D_identity_pairs':len(d_identities),
        'direct_D_no_signal_pairs':d_hist[0],
        'direct_D_mask_histogram':d_hist}


def replay(rows,pair_masks,k=None,allowed=ALL,combined=False):
    """One face must supply k votes; votes from different faces are never pooled."""
    roots, membership, routes = [], [], []
    for j,row in enumerate(rows):
        best = None
        for i,mask in pair_masks[j].items():
            rank = text_rank(row,rows[i])
            count = (mask & allowed).bit_count()
            accept_text = rank and (combined or k is None)
            accept_votes = k is not None and count>=k
            if not accept_text and not accept_votes:
                continue
            rid = membership[i]
            # Preserve text priority in OR experiments. In standalone scoring,
            # more votes wins, then text strength, then the earliest room/face.
            key = ((rank if accept_text else 0),count,-rid,-i) if (combined or k is None) else (count,rank,-rid,-i)
            if best is None or key>best[0]:
                best = key,rid,i,mask
        if best is None:
            membership.append(len(roots))
            roots.append(j)
        else:
            _,rid,i,mask = best
            membership.append(rid)
            routes.append({'candidate':j,'root':roots[rid],'face':i,'signal_mask':mask,
                           'votes':(mask & allowed).bit_count()})
    return routes,len(roots)


def crowding(rows):
    symbols = collections.Counter(r['sk'] for r in rows if r['sk'])
    tokens = collections.Counter(t for r in rows for t in r['nt'] if len(t)>=4)
    counts = [max([symbols[r['sk']] if r['sk'] else 0]+[tokens[t] for t in r['nt'] if len(t)>=4]) for r in rows]
    ordered = sorted(counts)
    quantiles = {str(p):ordered[max(0,math.ceil(p*len(ordered))-1)] for p in (.5,.75,.9,.99)}
    cutoff = quantiles['0.75']
    groups = ['crowded' if n>=cutoff else 'distinctive' for n in counts]
    return groups, {'definition':'max(full-sample nonempty folded-symbol frequency, frequency of any name token of length >=4)',
        'cutoff':'nearest-rank p75, ties included in crowded','cutoff_launch_frequency':cutoff,
        'frequency_quantiles':quantiles,'counts':dict(collections.Counter(groups)),
        'top_symbols':symbols.most_common(10),'top_name_tokens':tokens.most_common(10)}


def score(rows,routes,probability,copy_probabilities,groups,baseline=None):
    correct = sum(probability(rows[r['root']],rows[r['candidate']]) for r in routes)
    pessimistic = sum(probability(rows[r['root']],rows[r['candidate']],True) for r in routes)
    population = sum(copy_probabilities)
    result = {'routed':len(routes),'correct_estimate':correct,
              'precision_estimate':correct/len(routes) if routes else None,
              'pessimistic_precision_estimate':pessimistic/len(routes) if routes else None,
              'recall_estimate':correct/population,'production_precision':None,'production_recall':None}
    result['theme_breakdown'] = {}
    for group in ('crowded','distinctive'):
        selected = [r for r in routes if groups[r['candidate']]==group]
        good = sum(probability(rows[r['root']],rows[r['candidate']]) for r in selected)
        denom = sum(p for p,g in zip(copy_probabilities,groups) if g==group)
        result['theme_breakdown'][group] = {'routed':len(selected),'correct_estimate':good,
            'precision_estimate':good/len(selected) if selected else None,
            'fixed_expected_copies':denom,'recall_estimate':good/denom if denom else None}
    if baseline is not None:
        base = {r['candidate']:r for r in baseline}
        new = [r for r in routes if r['candidate'] not in base]
        old_correct = sum(probability(rows[r['root']],rows[r['candidate']]) for r in baseline)
        result.update({'new_routes_over_text':len(new),
            'new_route_correct_estimate':sum(probability(rows[r['root']],rows[r['candidate']]) for r in new),
            'net_correct_change_estimate':correct-old_correct,
            'net_recall_change_points_estimate':100*(correct-old_correct)/population,
            'lost_text_routes':len(set(base)-{r['candidate'] for r in routes}),
            'changed_text_roots':sum(r['candidate'] in base and r['root']!=base[r['candidate']]['root'] for r in routes)})
    return result


def correlation_table(hist):
    n = sum(hist)
    result = []
    for i,j in itertools.combinations(range(len(SIGNALS)),2):
        a,b = 1<<i,1<<j
        m1 = sum(w for mask,w in enumerate(hist) if mask&a)
        m2 = sum(w for mask,w in enumerate(hist) if mask&b)
        joint = sum(w for mask,w in enumerate(hist) if mask&a and mask&b)
        expected = m1*m2/n if n else 0
        var = m1*(1-m1/n)*m2*(1-m2/n) if n else 0
        result.append({'signal_a':SIGNALS[i],'signal_b':SIGNALS[j],
            'negative_pair_population':n,'a_errors':m1,'b_errors':m2,'joint_errors':joint,
            'independent_expected_joint':expected,'lift':joint/expected if expected else None,
            'phi':(joint-expected)/math.sqrt(var) if var else None})
    return result


def percentage(value):
    return '—' if value is None else f'{value:.2%}'


def number(value):
    return '—' if value is None else f'{value:.6g}'


def render(report):
    base = report['baseline']
    results = report['experiments']
    pairs = report['pair_audit']
    crowd = report['crowding']
    correlation = report['error_correlation_estimator']
    direct = report['error_correlation_direct_D']
    weighted_positive = sum(x['lift'] is not None and x['lift']>1 for x in correlation)
    direct_computable = sum(x['lift'] is not None for x in direct)
    direct_positive = sum(x['lift'] is not None and x['lift']>1 for x in direct)
    image_D=sum(w for mask,w in enumerate(pairs['direct_D_mask_histogram']) if mask&IMAGE)
    image_note=(f'The image vote fires on {image_D} D-labelled launch pairs, so its correlations '
                'are undefined, not evidence of image safety.' if image_D==0 else
                f'The image vote fires on {image_D} D-labelled launch pairs; its measured correlations are above.')
    positive_names = ', '.join(x['signal_a']+' + '+x['signal_b'] for x in direct
                              if x['lift'] is not None and x['lift']>1)
    k4 = next(x for x in results if x['signals']=='six_signals' and x['k']==4 and x['combined_with_text'])
    k5 = next(x for x in results if x['signals']=='six_signals' and x['k']==5 and not x['combined_with_text'])
    clean = report['nonempty_uri_baseline']
    correction = (
        'The requested “same population and estimator” comparison reproduces the archived '
        'text benchmark exactly, including its known missing-URI definition bug. That is a '
        'historical comparison, not renewed evidence that missing metadata means copying. '
        'The separate nonempty-URI sensitivity removes that credit and recomputes the same '
        'estimator; no missing URI/social/image value can fire any scorer signal. '
        'No new semantic labels are inferred from images or social equality.\n\n'
        'There is no approved production image threshold. This offline study uses the strictest '
        'previously measured Hamming point, zero; it does not enable images or shadow processing. '
        '“Error” in the legacy-estimator table means expected wrong-route credit under that '
        'estimator, including unsupported pairs scored zero, not an independently confirmed '
        'false match. The direct-D check is shown separately. The crowding/correlation '
        'hypothesis is not uniformly confirmed, so the results do not claim it is.')
    lines = ['<!-- generated by scripts/narrative/calibrate_consensus.py -->',
        '# K-of-n routing, co-errors and crowded-theme measurement', '',
        '**Recommendation: reject k-of-n for v1.** No tested setting improves estimated recall '
        'while meeting the unchanged text precision point. The image-free ablation also has no '
        'qualifying setting. V1, its tie order, worked examples and settled liveness thresholds '
        'remain unchanged; images stay out entirely, including shadow mode.', '',
        '## Scope and corrections', '', correction, '',
        f"The study uses the same {report['launches']} actual launches, ordered by slot/signature. "
        'Every room is explicitly assumed live, as in text calibration; no reserve, idle, volume '
        'or pool states are fabricated. These are conditional metadata benchmark estimates, not '
        'production precision/recall. No pre-window rooms, synthetic launches, new network requests '
        'or image decoding are introduced. Metadata and real-image hashes are the checked-in '
        'observations; source file hashes are in the JSON report.', '',
        'The only semantic label file is `labels_assistant.csv`, exactly as requested. No image-aware '
        'or new social labels are added. Equal folded identity or URI follows the archival positive '
        'definition; direct S/D labels score one/zero; U/unlabelled pairs use their strongest '
        'text-stratum rate. Pairs without a supported stratum or direct label score zero. That '
        'last rule is estimator coverage, not proof of a false route. Recall uses the fixed '
        'text-findable expected-copy population, not newly discovered social/image-only copies.', '',
        '## Signals and deterministic benchmark policy', '',
        '| vote | predicate |', '|---|---|',
        '| name_equal | Nonempty folded name keys equal. A short name can cast a vote; the existing name-only v1 route still requires its original minimum length. |',
        '| symbol_equal | Nonempty folded symbol keys equal. |',
        '| x_post | A nonempty specific X status ID matches, using the social audit’s cached JSON and normalisation. Uncapped in this separate experiment. |',
        f"| image_h0 | Both real 64-bit pHashes exist and have Hamming distance ≤ {report['image_max_hamming']}. Missing hashes never match, including missing against missing. |",
        f"| fuzzy_name | Name-token Jaccard ≥ {report['fuzzy_jaccard_threshold']:g}, with a shared token of length ≥ 4. It can overlap exact-name equality. |",
        f"| symbol_edit1 | Exactly one Damerau–Levenshtein edit, both folded symbols length ≥ {report['symbol_edit_min_length']}. |", '',
        f"Real-image hashes cover {report['images_available']}/{report['launches']} launches; "
        f"specific-post references cover {report['specific_post_available']}/{report['launches']}. "
        'Missing features contribute no vote. Votes are independently evaluated predicates, not mutually '
        'exclusive text strata; overlapping exact and fuzzy clues can double-count the same '
        'underlying evidence. Symbol equality and edit-distance-one are mutually exclusive, so '
        'all signals cannot fire together.', '',
        'A single candidate/earlier-face pair must supply at least k votes; votes from different '
        'faces are never pooled. Standalone ties prefer more votes, then the original exact text '
        'tier, then the earliest room/face. In text-OR-k experiments, the original exact text tier '
        'precedes vote count, then the earliest room/face. SOL-depth ties cannot be reconstructed. '
        'New doors expose their real metadata faces to later launches; every correctness score is '
        'against the selected room’s root, so a mistaken merge can harm later routes. This is '
        'research policy, not a change to §5 or the on-chain floor.', '',
        '## Every k against the original text population and estimator', '',
        f"Fixed expected copies: {report['legacy_expected_copy_population']:.6f}; legacy definition "
        f"positives: {report['legacy_certain_copies']}. The baseline reproduces "
        f"{base['routed']} routes, {report['baseline_new_rooms']} rooms, "
        f"{base['precision_estimate']:.2%} estimated precision and {base['recall_estimate']:.2%} "
        'estimated recall. The unrounded baseline precision is used as the acceptance threshold.', '',
        '| six-signal k | standalone routes | precision est. | recall est. | text OR k routes | combined precision est. | combined recall est. | additional routes | net recall change (points) |',
        '|---|---:|---|---|---:|---|---|---:|---:|']
    def sweep(name):
        out = []
        for x in results:
            if x['signals']!=name or x['combined_with_text']:
                continue
            y = next(y for y in results if y['signals']==name and y['k']==x['k'] and y['combined_with_text'])
            out.append(f"| {x['k']} | {x['routed']} | {percentage(x['precision_estimate'])} | "
                f"{percentage(x['recall_estimate'])} | {y['routed']} | {percentage(y['precision_estimate'])} | "
                f"{percentage(y['recall_estimate'])} | {y['new_routes_over_text']} | "
                f"{y['net_recall_change_points_estimate']:+.4f} |")
        return out
    lines += sweep('six_signals')
    lines += ['', 'A dash means undefined precision because no routes occur, not perfect precision. '
        'Additional routes count launches left as new rooms by text alone. Net recall change '
        'includes changed roots and downstream losses; it is not additional routes divided by '
        'the denominator. Full route assignments, matched face/mask, pessimistic estimates and '
        'label-coverage decompositions are in `consensus_calibration.json`.', '',
        f"At k=4, text OR k adds {k4['new_routes_over_text']} routes and "
        f"{k4['net_recall_change_points_estimate']:.4f} estimated recall points, but precision falls "
        f"from {base['precision_estimate']:.2%} to {k4['precision_estimate']:.2%}. At k=5, standalone "
        f"precision is {k5['precision_estimate']:.2%}, recall is {k5['recall_estimate']:.2%}, and "
        f"it adds {k5['new_routes_over_text']} routes over text. The highest threshold is mechanically "
        'unreachable because symbol equality and edit-one cannot both be true.', '',
        '## Image-free ablation', '',
        'Remove the image vote, sweep every remaining threshold, and preserve the same frozen '
        'population, estimator and tie policy. This tests a candidate compatible with the v1 '
        'image ban rather than treating an offline image result as permission to enable it.', '',
        '| five-signal k | standalone routes | precision est. | recall est. | text OR k routes | combined precision est. | combined recall est. | additional routes | net recall change (points) |',
        '|---|---:|---|---|---:|---|---|---:|---:|']
    lines += sweep('image_free')
    lines += ['', '## Nonempty-URI sensitivity', '',
        'This sensitivity removes the old equal-empty-URI positive rule and re-estimates the '
        'same text strata and per-launch copy population. It does not replace the requested '
        'archival comparison silently. All scorer assignments are identical; only scoring and '
        'the denominator change. Missing data is never treated as new evidence.', '',
        f"The expected-copy denominator becomes {report['nonempty_uri_expected_copy_population']:.6f}; "
        f"definition positives become {report['nonempty_uri_certain_copies']}. The unchanged text "
        f"baseline has estimated precision {clean['precision_estimate']:.2%}, recall "
        f"{clean['recall_estimate']:.2%}. No setting qualifies in this sensitivity either.", '',
        '| signals / k | standalone precision est. | standalone recall est. | combined precision est. | combined recall est. | net recall change (points) |',
        '|---|---|---|---|---|---:|']
    for x in results:
        if x['combined_with_text']:
            continue
        y = next(y for y in results if y['signals']==x['signals'] and y['k']==x['k'] and y['combined_with_text'])
        a,b = x['nonempty_uri_sensitivity'],y['nonempty_uri_sensitivity']
        lines.append(f"| {x['signals']} / {x['k']} | {percentage(a['precision_estimate'])} | "
            f"{percentage(a['recall_estimate'])} | {percentage(b['precision_estimate'])} | "
            f"{percentage(b['recall_estimate'])} | {b['net_recall_change_points_estimate']:+.4f} |")
    lines += ['', '## Pairwise co-errors versus independence', '',
        f"The frame is every earlier/later pair of the {report['launches']} real launches: "
        f"{pairs['all_earlier_launch_pairs']} pairs. Indexed enumeration examines "
        f"{pairs['indexed_pairs_examined']} potentially supported pairs; the "
        f"{pairs['signal_union_pairs']} pairs firing any signal are explicit. All other pairs have "
        'an implicit zero mask. Estimator-supported positive relationships outside the six signals '
        'are still included when computing the negative-pair frame. Conditioning only on the '
        'signal union would itself create selection correlations, so that is not the frame.', '',
        'For each pair, negative weight w = 1 − p_same from the frozen text estimator. '
        f"Total negative weight is {pairs['estimated_negative_pair_weight']:.6f}. On that frame, "
        'signal error counts are Σw·I(signal); simultaneous errors are Σw·I(a)·I(b). Independence '
        'predicts marginal_a × marginal_b / total_negative_weight. Lift is observed/predicted; '
        'phi is Pearson correlation of the two trigger indicators on that negative-weight frame. '
        'These fractional figures are assistant-estimator extrapolations, not newly human-labelled '
        'errors, causal proof, or independent Bernoulli trials.', '',
        '| signals | simultaneous error weight | independence expected | lift | phi |',
        '|---|---:|---:|---:|---:|']
    for x in correlation:
        lines.append(f"| {x['signal_a']} + {x['signal_b']} | {number(x['joint_errors'])} | "
            f"{number(x['independent_expected_joint'])} | {number(x['lift'])} | {number(x['phi'])} |")
    lines += ['', f"The estimator shows positive association for {weighted_positive}/{len(correlation)} "
        'signal pairs. Some absence of co-errors is mechanical or definitional: equality and '
        'edit-one are mutually exclusive, and the identity-positive policy forces name+symbol '
        'joint wrong weight to zero. Neither is evidence that real semantic errors are independent.', '',
        f"Direct-D cross-check: {pairs['direct_D_launch_pairs']} actual launch pairs from "
        f"{pairs['direct_D_identity_pairs']} distinct identity pairs carry an existing D label "
        f"and are not overridden by the positive definition; {pairs['direct_D_no_signal_pairs']} "
        'fire no tested signal. Independent expansion of every labelled identity pair verifies '
        'that these zero-mask cases are included. No stratum or unsupported-zero '
        'extrapolation is used in this table. Repeated launches weight their labelled identity '
        'pair multiple times, and the original labels are a stratified text-selected sample, '
        'so this check is not representative of all social/image errors.', '',
        '| signals | simultaneous D-labelled errors | independence expected | lift | phi |',
        '|---|---:|---:|---:|---:|']
    for x in direct:
        lines.append(f"| {x['signal_a']} + {x['signal_b']} | {number(x['joint_errors'])} | "
            f"{number(x['independent_expected_joint'])} | {number(x['lift'])} | {number(x['phi'])} |")
    lines += ['', f"Only {direct_positive}/{direct_computable} computable signal-pair correlations in the direct-D frame show positive "
        f'association. {image_note} The positive direct-D pairings '
        f"are {positive_names}. Thus the broad "
        'correlated-error hypothesis has partial support and substantial label-selection limits; '
        'it is not uniformly established by this sample.', '',
        'Signal-union truth-source coverage:', '', '| source | actual launch pairs |', '|---|---:|']
    lines += [f'| {k} | {v} |' for k,v in sorted(pairs['signal_union_truth_sources'].items())]
    lines += ['', 'Unsupported-zero pairs contribute errors only by the requested estimator’s '
        'coverage rule. They must be independently labelled before interpreting their co-errors '
        'as semantic false positives. No public link or matching hash labels itself correct.', '',
        '## Crowded versus distinctive themes', '',
        'Define each launch’s density as the maximum of its nonempty folded-symbol launch '
        'frequency and its name-token launch frequencies, using tokens of length at least four. '
        'Count distinct launch records, not repeated tokens inside one name. Crowded means density '
        f"at or above the observed nearest-rank p75 cutoff, {crowd['cutoff_launch_frequency']} launches; "
        f"ties included. This yields {crowd['counts']['crowded']} crowded and "
        f"{crowd['counts']['distinctive']} distinctive launches. Full-sample frequencies define "
        'a post-hoc diagnostic only; no future information affects routing. These are lexical '
        'density groups, not human narrative-theme labels.', '',
        '| policy / k | crowded routes | crowded precision est. | distinctive routes | distinctive precision est. |',
        '|---|---:|---|---:|---|']
    def theme_row(name,x):
        a,b=x['theme_breakdown']['crowded'],x['theme_breakdown']['distinctive']
        return f"| {name} | {a['routed']} | {percentage(a['precision_estimate'])} | {b['routed']} | {percentage(b['precision_estimate'])} |"
    lines.append(theme_row('text baseline',base))
    for x in results:
        name=f"{x['signals']} {'text OR ' if x['combined_with_text'] else ''}{x['k']}"
        lines.append(theme_row(name,x))
    worse,better,equal=[],[],[]
    for x in results:
        if x['signals']!='six_signals' or x['combined_with_text']:
            continue
        a=x['theme_breakdown']['crowded']['precision_estimate']
        b=x['theme_breakdown']['distinctive']['precision_estimate']
        if a is not None and b is not None:
            (worse if a<b else better if a>b else equal).append(str(x['k']))
    lines += ['', 'Crowding does not uniformly concentrate the worst precision. In the six-signal '
        f"standalone study crowded precision is lower at k={','.join(worse)}, higher at "
        f"k={','.join(better)}, and equal at k={','.join(equal)}. "
        'The full table, rather than an assumed theme effect, determines that conclusion.', '',
        '| frequent folded symbol | launches |', '|---|---:|']
    lines += [f'| {k} | {v} |' for k,v in crowd['top_symbols']]
    lines += ['', '| frequent folded name token | launches |', '|---|---:|']
    lines += [f'| {k} | {v} |' for k,v in crowd['top_name_tokens']]
    lines += ['', '## Recommendation and label dependency', '',
        'Reject k-of-n for v1 at every tested threshold. High thresholds can reach perfect '
        'estimated precision by retaining an existing text-routed subset; that is not '
        'incremental recall. Lower thresholds add routes at a precision cost. The image-free '
        'variant does not rescue the rule. The independent social audit remains a separate '
        'negative recommendation because its semantic label coverage cannot establish the bar. '
        'This rejects the measured unweighted threshold design; it is not evidence about every '
        'possible weighted classifier or a future held-out sample.', '',
        'Raw feature availability, equality/mask counts, route counts, theme-density frequencies '
        'and which roots change are label-independent conditional benchmark observations. '
        'Every semantic precision/recall estimate, expected-copy denominator, weighted co-error '
        'and crowded-group precision uses the identity/URI policy and assistant labels or '
        'their text-stratum extrapolations. The direct-D table still uses assistant labels; '
        'none have human review. Same-post equality is close to ground truth for the referenced '
        'post, not independent truth about irreversible narrative absorption; domains are weaker.', '',
        'The review CSV lists root/candidate mint pairs requiring judgement, existing label/coverage '
        'source and affected policies. It does not create or silently load new labels. A future '
        'candidate needs independent root-level human review on held-out data and the missing '
        'ordered room-state histories before a production precision/recall claim. No new third '
        'match condition, tie tier, example route or on-chain change is justified. The existing '
        'matcher signature already covers the routing decision. The launcher never chooses '
        'the room/door; founder-share plumbing defaults to 0 bps (no founder payout in v1).', '',
        '## Reproduce', '', '```bash', 'python3 scripts/narrative/calibrate_consensus.py',
        'python3 scripts/narrative/run_revision.py', '```', '',
        'The standalone experiment uses only the standard library and checked-in JSON/CSV. '
        'It verifies original metadata byte hashes against the image manifest, consumes recorded '
        'pHashes without fetching/decoding images, and regenerates this report and its document blocks.']
    text='\n'.join(lines)+'\n'
    (OUT/'consensus_calibration.md').write_text(text,encoding='utf-8',newline='\n')
    path=ROOT/'NARRATIVE_DETECTION.md'
    doc=path.read_text(encoding='utf-8')
    content='\n'.join('##'+line if line.startswith('## ') else line for line in lines[2:])
    for name,value in [('CONSENSUS CORRECTION',correction),('CONSENSUS MEASUREMENT',content)]:
        begin,end=f'<!-- BEGIN GENERATED {name} -->',f'<!-- END GENERATED {name} -->'
        if begin in doc:
            before,tail=doc.split(begin,1)
            _,after=tail.split(end,1)
            doc=before+begin+'\n'+value.strip()+'\n'+end+after
    path.write_text(doc,encoding='utf-8',newline='\n')


def write_review(rows,experiments,labels):
    review={}
    for x in experiments:
        for route in x['routes']:
            a,b=rows[route['root']],rows[route['candidate']]
            source=truth_source(a,b,labels,exclude_missing=True)
            if source in {'identity_definition','uri_definition'}:
                continue
            key=a['mint'],b['mint']
            if key not in review:
                pk=T.pair_key(a,b)
                review[key]={'a':pk[0],'b':pk[1],'label':labels.get(pk,''),
                    'source':source,'root_name':a['name'],'root_symbol':a['symbol'],
                    'candidate_name':b['name'],'candidate_symbol':b['symbol'],
                    'root_mint':a['mint'],'candidate_mint':b['mint'],'policies':set()}
            review[key]['policies'].add(f"{x['signals']}:{x['k']}:{'OR' if x['combined_with_text'] else 'alone'}")
    fields=['a','b','label','source','root_name','root_symbol','candidate_name','candidate_symbol','root_mint','candidate_mint','policies']
    with (OUT/'consensus_routes_to_review.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n')
        writer.writeheader()
        for key,row in sorted(review.items()):
            writer.writerow({**row,'policies':';'.join(sorted(row['policies']))})
    return len(review)


def main():
    rows,_,snapshot,_,_,_ = load_inputs()
    attach_hashes(rows,snapshot)
    labels_path = ROOT/'scripts/narrative/labels_assistant.csv'
    probability,certain,population,labels,detail = ground_truth(rows,labels_path,details=True)
    clean_p,clean_certain,clean_population,_,clean_detail = ground_truth(rows,labels_path,exclude_missing_uri=True,details=True)
    masks,pair_audit = build_pairs(rows,probability,labels)
    groups,crowd = crowding(rows)
    baseline,rooms = replay(rows,masks)
    expected,expected_rooms = metadata_text_routes(rows)
    assert [(r['candidate'],r['root']) for r in baseline]==[(r['candidate'],r['root']) for r in expected]
    assert rooms==expected_rooms
    baseline_metrics = score(rows,baseline,probability,detail['copy_probabilities'],groups)
    reference = json.loads((OUT/'label_dependency.json').read_text(encoding='utf-8'))
    assert abs(baseline_metrics['precision_estimate']-reference['semantic_precision_estimate'])<1e-12
    assert abs(baseline_metrics['recall_estimate']-reference['semantic_recall_estimate'])<1e-12
    experiments = []
    for name,allowed in [('six_signals',ALL),('image_free',NO_IMAGE)]:
        for k in range(1,allowed.bit_count()+1):
            for combined in (False,True):
                routes,new_rooms = replay(rows,masks,k,allowed,combined)
                metrics = score(rows,routes,probability,detail['copy_probabilities'],groups,baseline)
                clean_metrics = score(rows,routes,clean_p,clean_detail['copy_probabilities'],groups,baseline)
                sources = collections.Counter(truth_source(rows[r['root']],rows[r['candidate']],labels) for r in routes)
                experiments.append({'signals':name,'k':k,'combined_with_text':combined,
                    'new_rooms':new_rooms,**metrics,'nonempty_uri_sensitivity':clean_metrics,
                    'route_truth_sources':dict(sources),'routes':routes})
    candidates = [x for x in experiments if x['combined_with_text'] and x['precision_estimate'] is not None
        and x['precision_estimate']>=baseline_metrics['precision_estimate'] and x['net_recall_change_points_estimate']>1e-10]
    clean_base=score(rows,baseline,clean_p,clean_detail['copy_probabilities'],groups)
    clean_candidates=[x for x in experiments if x['combined_with_text'] and
        x['nonempty_uri_sensitivity']['precision_estimate'] is not None and
        x['nonempty_uri_sensitivity']['precision_estimate']>=clean_base['precision_estimate'] and
        x['nonempty_uri_sensitivity']['net_recall_change_points_estimate']>1e-10]
    review_count=write_review(rows,experiments,labels)
    report = {'scope':'conditional all-live metadata benchmark; fixed original text population and estimator',
        'launches':len(rows),'signals':list(SIGNALS),'image_max_hamming':0,
        'fuzzy_jaccard_threshold':FUZZY_JACCARD,'symbol_edit_min_length':EDIT_MIN,
        'images_available':sum(r['hash_int'] is not None for r in rows),
        'specific_post_available':sum(bool(r['social']['x_post']) for r in rows),
        'legacy_expected_copy_population':population,'legacy_certain_copies':len(certain),
        'nonempty_uri_expected_copy_population':clean_population,'nonempty_uri_certain_copies':len(clean_certain),
        'baseline':baseline_metrics,'baseline_new_rooms':rooms,
        'nonempty_uri_baseline':clean_base,
        'pair_audit':pair_audit,'crowding':crowd,
        'error_correlation_estimator':correlation_table(pair_audit['estimated_negative_mask_histogram']),
        'error_correlation_direct_D':correlation_table(pair_audit['direct_D_mask_histogram']),
        'experiments':experiments,
        'qualifying_estimated_policies':[{k:x[k] for k in ('signals','k','precision_estimate','recall_estimate','new_routes_over_text','net_recall_change_points_estimate')} for x in candidates],
        'qualifying_nonempty_uri_policies':[{k:x[k] for k in ('signals','k')} for x in clean_candidates],
        'input_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [OUT/'pump_launches.jsonl',OUT/'token_images.jsonl',OUT/'social_metadata_snapshot.json',labels_path]},
        'label_files_used':['scripts/narrative/labels_assistant.csv'],
        'review_mint_pairs':review_count,
        'launch_order':[r['mint'] for r in rows],
        'launch_theme_group':groups,
        'recommendation':('stop and review the qualifying estimated policy' if candidates or clean_candidates else
                          'reject for v1; no estimated precision-preserving incremental-recall policy')}
    evidence,ids=[],{}
    fields=['candidate','root','face','signal_mask','votes']
    for x in experiments:
        x['route_ids']=[]
        for route in x.pop('routes'):
            key=tuple(route[f] for f in fields)
            if key not in ids:
                ids[key]=len(evidence)
                evidence.append(key)
            x['route_ids'].append(ids[key])
    report['route_evidence_fields']=fields
    report['route_evidence']=evidence
    dump(OUT/'consensus_calibration.json',report)
    if candidates or clean_candidates:
        raise ValueError('STOP: a policy clears the estimated bar; record and review adoption before publishing a rejection.')
    render(report)
    print(json.dumps({'baseline':baseline_metrics,'crowding':crowd,'qualifying':report['qualifying_estimated_policies'],
        'results':[{k:x[k] for k in ('signals','k','combined_with_text','routed','precision_estimate','recall_estimate','new_routes_over_text','net_recall_change_points_estimate')} for x in experiments]},indent=2))


if __name__=='__main__':
    main()
