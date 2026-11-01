"""Offline social-link audit of the existing launch sample; never imported by v1.

Default reads the checked-in, byte-hashed metadata snapshot. --extract refreshes
that snapshot from the original local cache only, without network requests.
Every replay is a conditional metadata benchmark, not a financial-state replay.
"""
import argparse
import collections
import concurrent.futures
import csv
import hashlib
import ipaddress
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import calibrate_text as T
import matcher as M
from audit_liveness_brief import OUT, ROOT
from label_dependency import metadata_text_routes
from calibration_common import ground_truth

CACHE = ROOT.parents[1] / '.tmp/narrative_images'
SNAPSHOT = OUT / 'social_metadata_snapshot.json'
TIERS = ('x_post', 'x_account', 'website_domain', 'telegram')
WEB_FIELDS = {'website', 'external_url', 'homepage', 'url'}
SOCIAL_FIELDS = WEB_FIELDS | {'twitter', 'x', 'telegram', 'tg', 'discord', 'github',
    'reddit', 'medium', 'youtube', 'tiktok', 'instagram', 'facebook', 'coin_community'}
PLACEHOLDERS = {'', '-', '--', '#', 'null', 'none', 'undefined', 'n/a', 'na',
                'tbd', 'coming soon', 'comingsoon', 'false', '0'}
PLACEHOLDER_HOSTS = {'example.com', 'example.org', 'example.net', 'yourwebsite.com',
                     'website.com', 'yourdomain.com', 'domain.com', 'localhost'}
SHORTENERS = {'t.co', 'bit.ly', 'tinyurl.com', 'shorturl.at', 'cutt.ly', 'rb.gy',
              'ow.ly', 'buff.ly', 'lnkd.in', 'goo.gl'}
X_RESERVED = {'home', 'explore', 'search', 'intent', 'share', 'i', 'settings',
              'login', 'signup', 'hashtag', 'compose', 'messages', 'notifications'}


def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n',
                    encoding='utf-8', newline='\n')


def alternatives(uri):
    p = urlsplit(uri)
    tail = None
    if p.scheme == 'ipfs':
        tail = (p.netloc + p.path).removeprefix('ipfs/')
    elif '/ipfs/' in p.path:
        tail = p.path.split('/ipfs/', 1)[1]
    return list(dict.fromkeys(([f'https://pump.mypinata.cloud/ipfs/{tail}',
        f'https://gateway.pinata.cloud/ipfs/{tail}'] if tail else []) + [uri]))


def extract():
    """Preserve original JSON text so its SHA256 can be verified without caches."""
    manifest = [json.loads(s) for s in (OUT/'token_images.jsonl').read_text(encoding='utf-8').splitlines()]
    by_uri = collections.defaultdict(list)
    for row in manifest:
        by_uri[row['metadata_uri']].append(row)

    def read(item):
        uri, records = item
        expected = {r['metadata_sha256'] for r in records if r.get('metadata_sha256')}
        resolved = [r['metadata_resolved_uri'] for r in records if r.get('metadata_resolved_uri')]
        for url in dict.fromkeys(resolved + alternatives(uri)):
            p = CACHE/hashlib.sha256(url.encode()).hexdigest()
            if not p.is_file():
                continue
            data = p.read_bytes()
            sha = hashlib.sha256(data).hexdigest()
            if expected and expected != {sha}:
                raise ValueError('STOP: cached metadata differs from recorded hash: ' + uri)
            try:
                raw = data.decode('utf-8')
                obj = json.loads(raw)
                if not isinstance(obj, dict):
                    raise ValueError('metadata is not an object')
            except (UnicodeError, ValueError) as error:
                return uri, {'error': str(error)}
            return uri, {'resolved_uri': url, 'sha256': sha, 'raw_json': raw,
                         'fetched_at_utc': records[0]['fetched_at_utc'],
                         'previous_manifest_hash': bool(expected)}
        return uri, {'error': 'no cached metadata JSON',
                     'original_fetch_error': records[0].get('error')}

    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as pool:
        records = dict(pool.map(read, sorted(by_uri.items())))
    dump(SNAPSHOT, {'source': 'existing fetch_token_images.py local cache; no new requests',
                    'records': records})


def leaves(obj, prefix=''):
    for key, value in obj.items():
        path = f'{prefix}.{key}' if prefix else key
        if isinstance(value, dict):
            yield from leaves(value, path)
        elif isinstance(value, list):
            # Preserve a named social field even if its type is malformed.
            if key.lower() in SOCIAL_FIELDS:
                yield path, value
        else:
            yield path, value


def normalize(value, field):
    """Return (canonical URL parts, exclusion reason); no redirect resolution."""
    if value is None:
        return None, 'null'
    if not isinstance(value, str):
        return None, 'malformed_type'
    value = value.strip()
    if not value:
        return None, 'empty'
    if value.lower() in PLACEHOLDERS:
        return None, 'placeholder'
    if field.split('.')[-1].lower() in {'twitter', 'x'} and re.fullmatch(r'@[A-Za-z0-9_]{1,15}', value):
        value = 'https://x.com/' + value[1:]
    if value.startswith('//'):
        value = 'https:' + value
    if '://' not in value:
        value = 'https://' + value
    if any(ch.isspace() or ord(ch) < 32 for ch in value) or '\\' in value:
        return None, 'malformed_url'
    try:
        p = urlsplit(value)
        host = (p.hostname or '').lower().removeprefix('www.').rstrip('.')
        host = host.encode('idna').decode('ascii')
        if p.scheme.lower() not in {'http', 'https'} or p.username or p.password or p.port not in (None, 80, 443):
            return None, 'malformed_url'
        if not re.fullmatch(r'(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}', host):
            return None, 'malformed_host'
        try:
            ipaddress.ip_address(host)
            return None, 'malformed_host'
        except ValueError:
            pass
        if host in PLACEHOLDER_HOSTS or host.endswith('.example'):
            return None, 'placeholder'
        host = {'twitter.com': 'x.com', 'mobile.twitter.com': 'x.com',
                'mobile.x.com': 'x.com', 'telegram.me': 't.me', 'telegram.dog': 't.me'}.get(host, host)
        path = p.path.rstrip('/')
        if host in {'x.com', 't.me'} and not path:
            return None, 'placeholder_platform_home'
        return {'url': host + path, 'host': host, 'path': path}, None
    except (ValueError, UnicodeError):
        return None, 'malformed_url'


def signals(parts, field):
    host, path = parts['host'], parts['path']
    out = {}
    if host == 'x.com':
        post = re.fullmatch(r'/(?:[A-Za-z0-9_]{1,15}/status|i/web/status)/([1-9][0-9]*)(?:/(?:photo|video)/[0-9]+)?', path)
        if post:
            out['x_post'] = 'x.com/status/' + post[1]
        account = path.split('/')[1] if path.startswith('/') else ''
        if re.fullmatch(r'[A-Za-z0-9_]{1,15}', account) and account.lower() not in X_RESERVED:
            if post or re.fullmatch(r'/[A-Za-z0-9_]{1,15}(?:/(?:with_replies|media|highlights))?', path):
                out['x_account'] = 'x.com/' + account.lower()
    if host == 't.me':
        if re.fullmatch(r'/\+[A-Za-z0-9_-]+', path):
            out['telegram'] = host + path  # invite tokens are case-sensitive
        elif re.fullmatch(r'/joinchat/[A-Za-z0-9_-]+', path):
            out['telegram'] = host + '/+' + path.split('/')[-1]
        else:
            m = re.fullmatch(r'/(?:s/)?([A-Za-z][A-Za-z0-9_]{3,31})(?:/[0-9]+)?', path)
            if m and m[1].lower() not in {'share', 'proxy', 'socks', 'login', 'joinchat', 'addstickers', 'addemoji'}:
                out['telegram'] = host + '/' + m[1].lower()
    if field.split('.')[-1].lower() in WEB_FIELDS:
        out['website_domain'] = host
    return out


def load_inputs():
    snapshot = json.loads(SNAPSHOT.read_text(encoding='utf-8'))['records']
    rows = T.load(OUT/'pump_launches.jsonl')
    objects = {}
    for uri, record in snapshot.items():
        if 'raw_json' in record:
            assert hashlib.sha256(record['raw_json'].encode('utf-8')).hexdigest() == record['sha256'], uri
            objects[uri] = json.loads(record['raw_json'])
    fields = collections.defaultdict(collections.Counter)
    keys = collections.Counter()
    shorteners = collections.Counter()
    for row in rows:
        row['social'] = {tier: set() for tier in TIERS}
        row['social_urls'] = {}
        obj = objects.get(row['uri'])
        if obj is None:
            continue
        keys.update(obj.keys())
        for path, value in leaves(obj):
            if path.split('.')[-1].lower() not in SOCIAL_FIELDS:
                continue
            count = fields[path]
            count['present'] += 1
            count['populated'] += int(value is not None and (not isinstance(value, str) or bool(value.strip())))
            parts, reason = normalize(value, path)
            count[reason or 'valid_url'] += 1
            if parts:
                row['social_urls'][path] = parts['url']
                if parts['host'] in SHORTENERS:
                    shorteners[parts['host']] += 1
                extracted = signals(parts, path)
                count['valid_url_without_tested_tier'] += int(not extracted)
                for tier, key in extracted.items():
                    count['eligible_'+tier] += 1
                    row['social'][tier].add(key)
    for count in fields.values():
        count['absent_from_available_json'] = sum(r['uri'] in objects for r in rows) - count['present']
    return rows, objects, snapshot, fields, keys, shorteners


def text_group(row, index):
    if row['nk'] and len(row['nk']) >= M.DEFAULTS['name_equal_min_len']:
        return ('name', row['nk'])
    if row['nk'] and row['sk']:
        return ('identity', row['nk'], row['sk'])
    return ('unmatchable', index)


def frequency(rows, tier):
    values = collections.defaultdict(list)
    for j, row in enumerate(rows):
        for value in row['social'][tier]:
            values[value].append(j)
    return [{'value': key, 'launches': len(js),
             'identities': len({T.vkey(rows[j]) for j in js}),
             'text_groups': len({text_group(rows[j], j) for j in js}),
             'members': js} for key, js in sorted(values.items(), key=lambda kv: (-len(kv[1]), kv[0]))]


def social_hit(a, b, tier, allowed):
    common = a['social'][tier] & b['social'][tier] & allowed
    # Tier 2 excludes the stronger same-specific-post relation.
    if tier == 'x_account' and a['social']['x_post'] & b['social']['x_post']:
        return set()
    return common


def replay(rows, tier=None, cap=None, combined=False):
    """Actual ordered metadata only; no reserve/volume or invented trade states.

    Prefix frequency cap counts distinct text groups including this candidate;
    it never consults future launches. Text tiers precede the experimental tier.
    """
    rooms, routes = [], []
    text_index, social_index = collections.defaultdict(set), collections.defaultdict(set)
    groups = collections.defaultdict(set)
    for j, row in enumerate(rows):
        if tier:
            for value in row['social'][tier]:
                groups[value].add(text_group(row, j))
        allowed = {v for v in row['social'].get(tier, ()) if cap is None or len(groups[v]) <= cap}
        candidate_rooms = set()
        tk = text_group(row, j)
        if combined or tier is None:
            candidate_rooms.update(text_index[tk])
        for v in allowed:
            candidate_rooms.update(social_index[v])
        best = None
        for rid in sorted(candidate_rooms):
            faces = rooms[rid]
            hits = []
            for i in faces:
                if combined or tier is None:
                    t, _ = M.text_tier(row, rows[i], M.DEFAULTS, fuzzy=False)
                    if t in {'T3', 'T2n'}:
                        hits.append((M.TIER_RANK[t], -i, t, None))
                if tier:
                    common = social_hit(row, rows[i], tier, allowed)
                    if common:
                        hits.append((1, -i, tier, sorted(common)[0]))
            if hits:
                hit = max(hits)
                key = (hit[0], -rid)
                if best is None or key > best[0]:
                    best = key, rid, hit
        if best is None:
            rooms.append([j])
            rid = len(rooms)-1
        else:
            _, rid, hit = best
            routes.append({'candidate': j, 'root': rooms[rid][0], 'face': -hit[1],
                           'rule': hit[2], 'value': hit[3]})
            rooms[rid].append(j)
        text_index[tk].add(rid)
        if tier:
            for v in row['social'][tier]:
                social_index[v].add(rid)
    return routes, len(rooms)


def labels():
    result = {}
    for filename in ['labels_assistant.csv', 'labels_social_assistant.csv']:
        path = ROOT/'scripts/narrative'/filename
        if path.is_file():
            for row in csv.DictReader(path.open(encoding='utf-8', newline='')):
                if row['label'] in {'S', 'D', 'U'}:
                    result[tuple(sorted((row['a'], row['b'])))] = row['label']
    return result


def judgement(a, b, labs):
    if (a['uri'] and a['uri'] == b['uri']) or (a['nk'] and a['sk'] and T.vkey(a) == T.vkey(b)):
        return 'definition_positive'
    return labs.get(T.pair_key(a, b), 'unlabelled')


def anchors(rows):
    seen_identity, seen_uri, copies, uri_copies = set(), set(), set(), set()
    for j, r in enumerate(rows):
        identity = T.vkey(r) if r['nk'] and r['sk'] else None
        if (identity and identity in seen_identity) or (r['uri'] and r['uri'] in seen_uri):
            copies.add(j)
        if r['uri'] and r['uri'] in seen_uri:
            uri_copies.add(j)
        if identity:
            seen_identity.add(identity)
        if r['uri']:
            seen_uri.add(r['uri'])
    return copies, uri_copies


def post_anchor(rows):
    seen, copies = set(), set()
    for j, row in enumerate(rows):
        if seen & row['social']['x_post']:
            copies.add(j)
        seen.update(row['social']['x_post'])
    return copies


def metric(rows, routes, labs, copy_anchor, uri_anchor, baseline=None):
    counts = collections.Counter(judgement(rows[r['root']], rows[r['candidate']], labs) for r in routes)
    good = counts['definition_positive'] + counts['S']
    unknown = counts['U'] + counts['unlabelled']
    n = len(routes)
    in_anchor = [r for r in routes if r['candidate'] in copy_anchor]
    anchor_counts = collections.Counter(judgement(rows[r['root']], rows[r['candidate']], labs) for r in in_anchor)
    a_good = anchor_counts['definition_positive'] + anchor_counts['S']
    a_unknown = anchor_counts['U'] + anchor_counts['unlabelled']
    strict_uri = sum(r['candidate'] in uri_anchor and bool(rows[r['candidate']]['uri']) and
                     rows[r['candidate']]['uri'] == rows[r['root']]['uri'] for r in routes)
    posts = post_anchor(rows)
    strict_post = sum(r['candidate'] in posts and bool(rows[r['root']]['social']['x_post'] &
                      rows[r['candidate']]['social']['x_post']) for r in routes)
    lower, upper = ((good/n, (good+unknown)/n) if n else (None, None))
    judged = good + counts['D']
    out = {'routed': n, 'judgements': dict(counts), 'conditional_precision_bound': [lower, upper],
           'decided_only_precision': good/judged if judged else None,
           'copy_anchor_correct_bound': [a_good, a_good+a_unknown],
           'copy_anchor_recall_bound': [a_good/len(copy_anchor), (a_good+a_unknown)/len(copy_anchor)],
           'strict_uri_root_successes': strict_uri,
           'strict_uri_root_recall': strict_uri/len(uri_anchor),
           'specific_post_root_successes': strict_post,
           'specific_post_root_recall': strict_post/len(posts) if posts else None,
           'production_precision': None, 'production_recall': None,
           'all_copy_semantic_recall': None}
    if baseline is not None:
        base = {r['candidate']: r for r in baseline}
        new = [r for r in routes if r['candidate'] not in base]
        removed = set(base) - {r['candidate'] for r in routes}
        changed = sum(r['candidate'] in base and r['root'] != base[r['candidate']]['root'] for r in routes)
        new_counts = collections.Counter(judgement(rows[r['root']], rows[r['candidate']], labs) for r in new)
        new_good = new_counts['definition_positive'] + new_counts['S']
        current = {r['candidate']: r for r in routes}
        delta_low = delta_high = 0
        def interval(route):
            if route is None:
                return 0, 0
            lab = judgement(rows[route['root']], rows[route['candidate']], labs)
            if lab in {'definition_positive', 'S'}:
                return 1, 1
            return (0, 0) if lab == 'D' else (0, 1)
        for j in copy_anchor:
            old, now = base.get(j), current.get(j)
            if old and now and old['root'] == now['root']:
                continue  # the same uncertain correctness cancels exactly
            lo0, hi0 = interval(old)
            lo1, hi1 = interval(now)
            delta_low += lo1-hi0
            delta_high += hi1-lo0
        out.update({'incremental_routes': len(new), 'lost_baseline_routes': len(removed),
                    'changed_baseline_roots': changed, 'incremental_judgements': dict(new_counts),
                    'incremental_correct_bound': [new_good, new_good+new_counts['U']+new_counts['unlabelled']],
                    'incremental_copy_anchor_candidates': sum(r['candidate'] in copy_anchor for r in new),
                    'copy_anchor_recall_change_points_bound': [100*delta_low/len(copy_anchor),
                                                               100*delta_high/len(copy_anchor)]})
    return out


def percent(value):
    return 'unmeasured' if value is None else f'{100*value:.2f}%'


def interval_text(values):
    return '–'.join(percent(v) for v in values)


def render(report):
    rows = report['launches']
    lines = ['<!-- generated by scripts/narrative/calibrate_social.py -->',
        '# Social-link measurement and v1 decision', '',
        '**Recommendation: reject all social tiers for v1 on the available evidence.** '
        'None demonstrates the text operating point with nonzero incremental routing. '
        'This is an evidence threshold decision, not a claim that every tier has low true precision. '
        'The production matcher, tie order, liveness thresholds and worked examples remain unchanged.', '',
        '## Scope and corrections', '',
        '**The brief’s “JSON is already fetched, so it costs nothing” premise conflicts with the '
        'current launch path.** JSON was fetched for the historical image research; v1 deliberately '
        'does no metadata-host requests. Adoption would require a new metadata-fetch/input provenance '
        'path, timeouts and reproducible content evidence. That premise is recorded rather than '
        'silently used to enable a third condition. No network calls were made for this audit.', '',
        f"The existing sample has {rows} launches; cached JSON is available for "
        f"{report['available_metadata_launches']} ({report['available_metadata_launches']/rows:.2%}); "
        f"{report['metadata_unavailable_launches']} have no cached JSON. The snapshot contains "
        f"{report['unique_available_metadata_uris']} available original metadata URIs and "
        f"{report['unique_metadata_hashes']} distinct byte hashes. Original UTF-8 JSON text, SHA256, "
        'resolved URI and recorded fetch timestamp are preserved in `social_metadata_snapshot.json`. '
        'Missing cached metadata is unavailable evidence, never an empty-link cluster. '
        'The snapshot is a later fetch, not proof of launch-time mutable-URI contents.', '',
        'Existing semantic labels cover text-selected pairs, not a random sample of social matches. '
        'Transferring their stratum rates to new social-only pairs would be an unsupported estimate. '
        'No new semantic labels were invented for this audit. Unlabelled/U pairs stay unknown; '
        'shared social links are not themselves used as semantic labels. A shared specific X post '
        'is strong evidence of the same referenced subject and is reported independently, but it '
        'does not prove the same narrative/market: the existing assistant labels contain a '
        'different-narrative pair with the same post. This conflict stops adoption, not the audit.', '',
        'All route counts below come from the actual stored launches in historical slot/signature '
        'benchmark order, with every room treated as live. There are no invented reserve/idle/volume '
        'states or synthetic launch measurements. Missing state histories and within-slot ordering '
        'still prevent production precision, production recall and true incremental recall measurement. '
        'For comparison only, these speculative social replays put identity equality before name '
        'equality before the single tested social tier, then use the earliest room for ties. '
        'SOL-depth ties cannot be reconstructed. Each route joins its selected room and later '
        'launches see those actual metadata faces, so root contamination is charged downstream.', '',
        '## Field availability and exclusions', '',
        '| JSON field | present | populated | valid URL | empty | null | placeholder | malformed | absent from available JSON |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for field, count in report['fields'].items():
        bad = sum(v for k,v in count.items() if k.startswith('malformed'))
        placeholder = sum(v for k,v in count.items() if k.startswith('placeholder'))
        lines.append(f"| {field} | {count['present']} | {count['populated']} | {count.get('valid_url',0)} | "
            f"{count.get('empty',0)} | {count.get('null',0)} | {placeholder} | {bad} | {count['absent_from_available_json']} |")
    lines += ['', 'Counts are per launch, including genuine repeated metadata. Populated means '
        'non-null/nonempty before validation, so a malformed populated value is still excluded. '
        'A valid URL can still be ineligible for every tested tier, such as an X community URL; '
        'per-field eligible-tier counts are in JSON. Unavailable JSON is separate from a field '
        'absent in available JSON. Named social fields '
        'are inspected recursively, including `extensions`; other discovered link fields '
        '`coin_community` and `external_url` are included. `createdOn`/`created_on` identify the '
        'launch platform; image/video and `properties.files`/`mind` media are inventoried in the '
        'snapshot but are not narrative social fields. Descriptions are prose, not a link field. '
        'Every top-level key and occurrence count is in `metadata_key_counts` in the JSON report.', '',
        '## Normalisation and tier definitions', '',
        '- HTTP/HTTPS and bare host URLs use a common host/path key; hosts are lowercased, IDNA '
        'encoded and stripped of `www.` and a terminal dot. Query strings, fragments and trailing '
        'slashes are removed. Credentials, unexpected ports, whitespace, invalid hosts, non-HTTP '
        'schemes and explicit placeholder values/hosts are excluded. There is no wildcard empty key.',
        '- X/Twitter host aliases are canonicalised. Specific posts use their numeric status ID '
        'independent of the username; X handles are lowercased. Bare `@handle` is accepted only in '
        'a Twitter/X field. Non-post X routes such as communities/trending are not mistaken for accounts.',
        '- X-account matching requires the same account with different or absent posts; a pair '
        'sharing a specific post is excluded from this weaker tier. Separate same-account and '
        'same-post runs are never collapsed into one social rule.',
        '- Website domain means the normalised **hostname** in website/external-URL fields, '
        'including nested extensions. Subdomains remain distinct; this is not a registrable-domain '
        'or public-suffix collapse. Generic platform hosts remain in the uncapped measurement.',
        '- Telegram aliases, public target case, `/s/` message paths and invite URL forms are '
        'canonicalised. Invite tokens remain case-sensitive. Equality is of a public target or '
        'invite token; without network reads, channel/group/user type and two different invites '
        'to the same group cannot be verified. Share/proxy/utility URLs do not count.',
        '- URL classification uses all discovered social fields for X/Telegram, not just the '
        'field named twitter/telegram. No shortener is expanded: there is no cached redirect '
        'mapping, and resolving one would require a network request. Shortener URLs remain '
        'literal URLs and cannot become X-post/account/Telegram evidence.', '',
        'Unexpanded recognised shortener host occurrences: ' +
        (', '.join(f'{k}: {v}' for k,v in sorted(report['unexpanded_shorteners'].items())) or 'none') + '.', '',
        '## How to read precision and recall', '',
        f"The archived strict-text point is {report['archived_text_precision']:.2%} estimated precision "
        f"and {report['archived_text_recall']:.2%} estimated recall. These use legacy assistant labels "
        'and text-stratum extrapolations; neither is production precision/recall. The text rule is unchanged.', '',
        '**Conditional evidence bounds** below assume the published folded-identity/nonempty-URI '
        'positive definition and the existing assistant S/D judgements. U and unlabelled routes '
        'range from incorrect to correct; no stratum extrapolation is applied. These intervals '
        'are not confidence intervals or bounds on unknown real-world semantic truth. Precision '
        'is scored against the selected room’s root, including later launches that inherit a '
        'contaminated room. They are deliberately not presented as measured semantic point estimates.', '',
        f"The fixed copy anchor contains {report['copy_anchor_size']} launches with an earlier "
        'nonempty identical metadata URI or nonempty folded identity. Missing URI never contributes. '
        'Recall is conditional root-correctness within this definition-selected anchor, not recall '
        'of every actual copy. Newly discovered social-only copies can lie outside it. The independent '
        f"strict URI-to-root column uses the {report['nonempty_uri_anchor_size']} nonempty URI-copy "
        'cases; it measures string-root recovery, not semantic correctness. A shared specific X '
        'post and all raw equality/frequency/route counts are label-independent observations. '
        'Semantic bounds, chosen frequency operating points and any recommendation about correctness '
        'depend on the identity policy, assistant labels and disclosed unknowns.', '',
        f"The independent repeated-specific-post anchor has {report['specific_post_anchor_size']} "
        f"launches. Text alone selects a root referencing that same post for "
        f"{report['baseline']['specific_post_root_successes']} of them "
        f"({percent(report['baseline']['specific_post_root_recall'])}); the uncapped X-post tier alone "
        f"does so for {report['uncapped_post_root_successes']} "
        f"({percent(report['uncapped_post_root_recall'])}). This is reference-to-post recovery, "
        'a close-to-ground-truth subject anchor independent of assistant labels, not general '
        'semantic precision. A public link is self-asserted and does not authenticate the launcher.', '',
        '| standalone tier / cap | routes | precision bound | copy-anchor recall bound | strict URI-to-root recall |',
        '|---|---:|---|---|---|']
    for tier in TIERS:
        cap = report['tier_decisions'][tier]['comparison_cap']
        for x in report['experiments']:
            if x['tier']==tier and not x['combined_with_text'] and x['cap_text_groups'] in (None,cap):
                lines.append(f"| {tier} / {x['cap_text_groups'] or 'none'} | {x['routed']} | "
                    f"{interval_text(x['conditional_precision_bound'])} | {interval_text(x['copy_anchor_recall_bound'])} | "
                    f"{percent(x['strict_uri_root_recall'])} |")
    lines += ['', '| text plus one tier / cap | total routes | new routes over text | new-route correctness bound | combined precision bound | copy-anchor recall bound | net anchor recall change (points) |',
        '|---|---:|---:|---|---|---|---|',
        f"| text baseline | {report['baseline']['routed']} | — | — | {interval_text(report['baseline']['conditional_precision_bound'])} | "
        f"{interval_text(report['baseline']['copy_anchor_recall_bound'])} | — |"]
    for tier in TIERS:
        cap = report['tier_decisions'][tier]['comparison_cap']
        for x in report['experiments']:
            if x['tier']==tier and x['combined_with_text'] and x['cap_text_groups'] in (None,cap):
                gain = x['copy_anchor_recall_change_points_bound']
                correctness = '–'.join(str(v) for v in x['incremental_correct_bound'])
                lines.append(f"| {tier} / {x['cap_text_groups'] or 'none'} | {x['routed']} | {x['incremental_routes']} | "
                    f"{correctness} | {interval_text(x['conditional_precision_bound'])} | "
                    f"{interval_text(x['copy_anchor_recall_bound'])} | {gain[0]:+.2f}–{gain[1]:+.2f} |")
    lines += ['', '“New routes” is a label-independent count of launches text alone leaves as new rooms. '
        'It is not a true-positive count or a measured recall gain. Net anchor changes include '
        'changed roots and lost baseline routes, rather than adding new matches to a fixed room '
        'assignment. Correctness uncertainty cancels where the root is unchanged. All per-route '
        'metrics are retained for every cap. The JSON also retains baseline assignments and '
        'candidate/root/face evidence for social-fired routes and changed/new roots at the uncapped '
        'and comparison-cap points. Every assignment regenerates from the byte-hashed inputs.', '',
        'Uncapped standalone evidence breakdown (not a sampled precision estimate):', '',
        '| tier | identity/nonempty-URI definition positive | assistant S | assistant D | assistant U | unlabelled |',
        '|---|---:|---:|---:|---:|---:|']
    for tier in TIERS:
        x = next(x for x in report['experiments'] if x['tier']==tier and x['cap_text_groups'] is None and not x['combined_with_text'])
        c = x['judgements']
        lines.append(f"| {tier} | {c.get('definition_positive',0)} | {c.get('S',0)} | {c.get('D',0)} | {c.get('U',0)} | {c.get('unlabelled',0)} |")
    lines += ['', 'The existing D-labelled same-post route is directly auditable (an assistant judgement, not human review):', '',
              '| root identity | candidate identity | common specific post | root mint | candidate mint |',
              '|---|---|---|---|---|']
    for row in report['same_post_label_conflicts']:
        lines.append(f"| {row['root_name']} / {row['root_symbol']} | {row['candidate_name']} / {row['candidate_symbol']} | "
                     f"`{row['post']}` | `{row['root_mint']}` | `{row['candidate_mint']}` |")
    lines += ['',
        '## Frequency distribution and caps', '',
        'A high number of copies can share a legitimate link. Caps therefore count distinct '
        '**v1 text groups**, not launch volume and not claimed “unrelated narratives”. Each key '
        'has full launch, folded-identity and text-group counts in the JSON. Distinct text groups '
        'are an observable diversity proxy, not semantic labels. The cap uses only groups observed '
        'up to and including the candidate, never future sample frequencies. Earlier merges are '
        'not undone when a key later crosses the cap. All observed prefix diversity levels '
        'are swept, alongside no cap; this is in-sample exploration, not a held-out optimisation.', '',
        '| tier | eligible launches | distinct values | repeated values | maximum launches/value | maximum text groups/value | first cap with incremental routes |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for tier, values in report['frequency_distributions'].items():
        decision = report['tier_decisions'][tier]
        lines.append(f"| {tier} | {decision['eligible_launches']} | {len(values)} | "
            f"{sum(v['launches']>1 for v in values)} | {max((v['launches'] for v in values),default=0)} | "
            f"{max((v['text_groups'] for v in values),default=0)} | {decision['comparison_cap']} |")
    lines += ['', 'Frequency histograms count values, not launches. The full value/member listing is in JSON.', '',
              '| tier | occurrences per value → number of values | text groups per value → number of values |',
              '|---|---|---|']
    for tier, values in report['frequency_distributions'].items():
        occurrence_hist = collections.Counter(v['launches'] for v in values)
        diversity_hist = collections.Counter(v['text_groups'] for v in values)
        lines.append(f"| {tier} | " + ', '.join(f'{k}→{v}' for k,v in sorted(occurrence_hist.items())) +
                     ' | ' + ', '.join(f'{k}→{v}' for k,v in sorted(diversity_hist.items())) + ' |')
    lines += ['', 'For the compact comparison, the selected cap is the **first observed cap that '
        'adds any route**, giving the tightest nonredundant diversity window. A stricter cap adds '
        'no route beyond text for any tier. This is a diagnostic choice, not a deployed parameter. '
        'The full cap sweep follows; it prevents selecting a favourable result without showing '
        'the alternatives.', '',
        '| tier / cap | standalone routes | standalone precision bound | new combined routes | combined precision bound |',
        '|---|---:|---|---:|---|']
    for x in report['experiments']:
        if not x['combined_with_text']:
            y = next(y for y in report['experiments'] if y['tier']==x['tier'] and y['cap_text_groups']==x['cap_text_groups'] and y['combined_with_text'])
            lines.append(f"| {x['tier']} / {x['cap_text_groups'] or 'none'} | {x['routed']} | "
                f"{interval_text(x['conditional_precision_bound'])} | {y['incremental_routes']} | "
                f"{interval_text(y['conditional_precision_bound'])} |")
    lines += ['', 'Most frequent values (all values and exact launch members are in JSON):', '',
        '| tier | value | launches | folded identities | text groups |', '|---|---|---:|---:|---:|']
    for tier, values in report['frequency_distributions'].items():
        for v in values[:5]:
            lines.append(f"| {tier} | `{v['value']}` | {v['launches']} | {v['identities']} | {v['text_groups']} |")
    lines += ['', '## Decision and remaining evidence', '',
        '| tier | decision | reason |', '|---|---|---|']
    for tier in TIERS:
        lines.append(f"| {tier} | {report['tier_decisions'][tier]['recommendation']} | "
            'No nonredundant cap demonstrates both standalone and combined precision at the archived text point under the stated bounds. |')
    lines += ['', 'A post-ID equality observation is close to ground truth **for which post is '
        'referenced**, not independent ground truth for irrevocable market absorption. Domain '
        'and account equality are weaker still. The original text-selected assistant labels do '
        'not justify a precision estimate for unseen social populations. `social_routes_to_review.csv` '
        f"lists {report['review_pairs']} distinct identity pairs requiring semantic judgement, "
        f"including {report['unlabelled_review_pairs']} without an existing assistant label; "
        'it is an exhaustive audit queue across the swept policies, not a random calibration sample.', '',
        'Before reconsidering, label root/candidate narrative meaning independently of the social '
        'equality being tested, including all incremental routes and changed-root descendants. '
        'Use a representative held-out sample and human review, with U/missing cases disclosed. '
        'Capture metadata bytes at decision time and the ordered room-state histories needed for '
        'the full gate. No tier has earned a third stage-1 condition or a place in the tie order. '
        'If a later tier qualifies, the existing matcher signature already covers its routing '
        'decision; this audit needs no on-chain change. Images, including shadow processing, '
        'remain excluded; rejected symbol-only/fuzzy rules remain excluded. The launcher never '
        'chooses the room or door, and founder-share plumbing defaults to 0 bps (no founder payout in v1). The shared historical text '
        'reader/writer now uses explicit UTF-8/LF for Windows reproduction; its archived calibration '
        'figures and copy inputs remain unchanged.', '',
        '## Reproduce', '', '```bash',
        'python3 scripts/narrative/calibrate_social.py',
        '# Optional: rebuild byte-hashed snapshot from the original local cache; never fetches:',
        'python3 scripts/narrative/calibrate_social.py --extract',
        '```', '', 'The default run requires only the standard library and checked-in inputs. '
        'It regenerates this report, JSON results, review queue and the social document blocks.']
    text = '\n'.join(lines)+'\n'
    (OUT/'social_calibration.md').write_text(text, encoding='utf-8', newline='\n')
    doc_path = ROOT/'NARRATIVE_DETECTION.md'
    doc = doc_path.read_text(encoding='utf-8')
    correction = '\n\n'.join(line for line in lines if line.startswith((
        '**The brief’s', 'Existing semantic labels')))
    document_report = '\n'.join('##' + line if line.startswith('## ') else line for line in lines[2:])
    for name, content in [('SOCIAL CORRECTION', correction),
                           ('SOCIAL MEASUREMENT', document_report)]:
        begin, end = f'<!-- BEGIN GENERATED {name} -->', f'<!-- END GENERATED {name} -->'
        if begin in doc:
            before, tail = doc.split(begin, 1)
            _, after = tail.split(end, 1)
            doc = before+begin+'\n'+content.strip()+'\n'+end+after
    doc_path.write_text(doc, encoding='utf-8', newline='\n')


def write_review(rows, experiments, labs):
    pairs = {}
    for experiment in experiments:
        for route in experiment['routes']:
            a, b = rows[route['root']], rows[route['candidate']]
            if judgement(a, b, labs) == 'definition_positive':
                continue
            key = T.pair_key(a, b)
            pairs.setdefault(key, {'a': key[0], 'b': key[1], 'label': labs.get(key, ''),
                'root_name': a['name'], 'root_symbol': a['symbol'],
                'candidate_name': b['name'], 'candidate_symbol': b['symbol'],
                'root_mint': a['mint'], 'candidate_mint': b['mint'], 'tiers': set()})
            pairs[key]['tiers'].add(experiment['tier'])
    with (OUT/'social_routes_to_review.csv').open('w', encoding='utf-8', newline='') as f:
        fields = ['a','b','label','root_name','root_symbol','candidate_name','candidate_symbol','root_mint','candidate_mint','tiers']
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        for key, row in sorted(pairs.items()):
            writer.writerow({**row, 'tiers': ';'.join(sorted(row['tiers']))})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extract', action='store_true')
    args = parser.parse_args()
    if args.extract:
        extract()
    rows, objects, snapshot, fields, keys, shorteners = load_inputs()
    labs = labels()
    copies, uris = anchors(rows)
    baseline, rooms = replay(rows)
    original, original_rooms = metadata_text_routes(rows)
    assert [(r['candidate'],r['root']) for r in baseline] == [(r['candidate'],r['root']) for r in original]
    assert rooms == original_rooms
    base = metric(rows, baseline, labs, copies, uris)
    legacy_probability, _, legacy_population, _ = ground_truth(rows, ROOT/'scripts/narrative/labels_assistant.csv')
    legacy_correct = sum(legacy_probability(rows[r['root']], rows[r['candidate']]) for r in baseline)
    distributions = {tier: frequency(rows, tier) for tier in TIERS}
    experiments = []
    for tier in TIERS:
        # Every integer up to the observed maximum occurs in a real prefix of
        # at least one link, even when its final count skips that level.
        caps = [None] + list(range(1, 1+max((f['text_groups'] for f in distributions[tier]), default=0)))
        for cap in caps:
            for combined in (False, True):
                routes, new_rooms = replay(rows, tier, cap, combined)
                experiments.append({'tier': tier, 'cap_text_groups': cap,
                    'combined_with_text': combined, 'new_rooms': new_rooms,
                    **metric(rows, routes, labs, copies, uris, baseline), 'routes': routes})
    write_review(rows, experiments, labs)
    review_rows = list(csv.DictReader((OUT/'social_routes_to_review.csv').open(encoding='utf-8',newline='')))
    conflicts = []
    post_run = next(x for x in experiments if x['tier']=='x_post' and x['cap_text_groups'] is None and not x['combined_with_text'])
    for route in post_run['routes']:
        a,b = rows[route['root']],rows[route['candidate']]
        shared = a['social']['x_post'] & b['social']['x_post']
        if shared and judgement(a,b,labs)=='D':
            conflicts.append({'root_name':a['name'],'root_symbol':a['symbol'],
                'candidate_name':b['name'],'candidate_symbol':b['symbol'],
                'root_mint':a['mint'],'candidate_mint':b['mint'],'post':sorted(shared)[0]})
    decisions = {}
    for tier in TIERS:
        candidates = [x for x in experiments if x['tier']==tier and x['combined_with_text']
                      and x['cap_text_groups'] is not None and x['incremental_routes']]
        qualifying = []
        for combined in candidates:
            alone = next(x for x in experiments if x['tier']==tier and not x['combined_with_text']
                         and x['cap_text_groups']==combined['cap_text_groups'])
            if min(alone['conditional_precision_bound'][0],combined['conditional_precision_bound'][0]) >= legacy_correct/len(baseline):
                qualifying.append(combined['cap_text_groups'])
        decisions[tier] = {'comparison_cap': min(x['cap_text_groups'] for x in candidates) if candidates else None,
            'eligible_launches': sum(bool(r['social'][tier]) for r in rows),
            'qualifying_caps': qualifying, 'recommendation': 'reject' if not qualifying else 'further validation required'}
    if any(d['qualifying_caps'] for d in decisions.values()):
        raise ValueError('STOP: changed evidence reaches the threshold; reassess the v1 decision before publishing a rejection.')
    report = {'scope': 'conditional all-live metadata benchmark; no production gate replay',
        'launches': len(rows), 'available_metadata_launches': sum(r['uri'] in objects for r in rows),
        'unique_available_metadata_uris': len(objects),
        'metadata_unavailable_launches': sum(r['uri'] not in objects for r in rows),
        'unique_metadata_hashes': len({r['sha256'] for r in snapshot.values() if 'sha256' in r}),
        'metadata_key_counts': dict(sorted(keys.items())),
        'fields': {k:dict(v) for k,v in sorted(fields.items())}, 'unexpanded_shorteners': dict(shorteners),
        'copy_anchor_size': len(copies), 'nonempty_uri_anchor_size': len(uris),
        'specific_post_anchor_size': len(post_anchor(rows)),
        'uncapped_post_root_successes': next(x['specific_post_root_successes'] for x in experiments if x['tier']=='x_post' and x['cap_text_groups'] is None and not x['combined_with_text']),
        'uncapped_post_root_recall': next(x['specific_post_root_recall'] for x in experiments if x['tier']=='x_post' and x['cap_text_groups'] is None and not x['combined_with_text']),
        'review_pairs': len(review_rows), 'unlabelled_review_pairs': sum(not r['label'] for r in review_rows),
        'same_post_label_conflicts': conflicts,
        'baseline': base, 'baseline_new_rooms': rooms,
        'archived_text_precision': legacy_correct/len(baseline),
        'archived_text_recall': legacy_correct/legacy_population,
        'frequency_distributions': distributions,
        'tier_decisions': decisions,
        'experiments': experiments,
        'recommendation': 'reject for v1; no demonstrated nonredundant qualifying tier'}
    # Retain complete metrics for every cap, plus compact audit evidence for the
    # uncapped and first nonredundant cap. Unchanged baseline assignments are
    # reconstructible from baseline_routes; avoid repeating them in every run.
    baseline_map = {r['candidate']:r['root'] for r in baseline}
    report['launch_order'] = [r['mint'] for r in rows]
    report['baseline_routes'] = [[r['candidate'],r['root']] for r in baseline]
    report['route_evidence_scope'] = ('For uncapped and comparison-cap runs: all social-fired routes '
        'and every changed/new root, with actual candidate/root/face indices into launch_order. '
        'Other cap aggregates regenerate from the same byte-hashed inputs.')
    for x in experiments:
        routes = x.pop('routes')
        if x['cap_text_groups'] in (None,decisions[x['tier']]['comparison_cap']):
            x['route_evidence'] = [r for r in routes if r['rule'] in TIERS or
                                  baseline_map.get(r['candidate']) != r['root']]
    dump(OUT/'social_calibration.json', report)
    render(report)
    print(json.dumps({'launches':len(rows),'decisions':decisions,'recommendation':report['recommendation']}, indent=2))


if __name__ == '__main__':
    main()
