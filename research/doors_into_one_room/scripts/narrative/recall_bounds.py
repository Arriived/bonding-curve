"""Evidence bounds for fixed historical proxy targets, not a production room replay.

Only confirmed trade snapshots count as observed reserves. Zero placeholders from
non-trade/missing reads remain unknown. No state is invented and no RPC is used.
"""
import json

from audit_liveness_brief import OUT, SOL_QUOTES
from matcher import DEFAULTS


def mature_proxy_status(members, reads, quotes, now, params):
    """Classify the pre-graduation, sum-of-independent-SOL-curves proxy only."""
    sol_members = {m['mint'] for m in members if quotes.get(m['mint']) in SOL_QUOTES}
    unknown_quotes = {m['mint'] for m in members if quotes.get(m['mint']) is None}
    by_mint = {r['mint']: r for r in reads}
    verified = [by_mint[m] for m in sol_members if m in by_mint
                and by_mint[m].get('is_trade') is True and by_mint[m].get('sig')
                and by_mint[m].get('slot') is not None and by_mint[m].get('time') is not None
                and by_mint[m]['time'] <= now]
    complete = not unknown_quotes and len(verified) == len(sol_members)
    reserve_lower = sum(r['real_sol_reserves'] for r in verified)
    latest = max((r['time'] for r in verified), default=None)
    if complete and reserve_lower < params['live_min_reserve_lamports']:
        result, reason = False, 'complete confirmed snapshots: proxy reserve below floor'
    elif complete and latest is not None and now-latest > params['live_max_idle_seconds']:
        result, reason = False, 'complete confirmed snapshots: proxy idle above limit'
    elif reserve_lower >= params['live_min_reserve_lamports'] and latest is not None and now-latest <= params['live_max_idle_seconds']:
        result, reason = True, 'confirmed reserve lower bound and recent trade pass without volume'
    else:
        result, reason = None, 'incomplete confirmed trade snapshots; reserve/idle not established'
    return {'without_volume': result, 'with_volume': False if result is False else None,
            'reason': reason, 'complete_confirmed_sol_snapshots': complete,
            'confirmed_sol_reads': len(verified), 'known_sol_members': len(sol_members),
            'unknown_quote_members': sorted(unknown_quotes),
            'confirmed_proxy_reserve_lower_bound': reserve_lower,
            'last_confirmed_trade_time': latest, 'volume_history_supplied': False}


def retention(rows, grace, field):
    statuses = [True if row['age'] < grace else row['mature'][field] for row in rows]
    return {'pass_lower': statuses.count(True), 'pass_upper': len(rows)-statuses.count(False),
            'fail_lower': statuses.count(False), 'fail_upper': len(rows)-statuses.count(True)}


def main():
    history = json.loads((OUT/'liveness_reads.json').read_text(encoding='utf-8'))
    quotes = json.loads((OUT/'liveness_quote_mints.json').read_text(encoding='utf-8'))['quote_mint']
    copies = {c['copy_sig']: c for c in json.loads((OUT/'copies.json').read_text(encoding='utf-8'))}
    rows = []
    for snap in history['part_a_copies']:
        sol_reads = [r for r in snap['reads'] if quotes.get(r['mint']) in SOL_QUOTES]
        if not sol_reads:
            continue
        members = copies[snap['copy_sig']]['members']
        sol_members = [m for m in members if quotes.get(m['mint']) in SOL_QUOTES]
        first = min(sol_members, key=lambda m: m['launch_time'])
        rows.append({'copy_signature': snap['copy_sig'], 'copy_time': snap['copy_time'],
                     'target_first_sol_mint': first['mint'], 'age': snap['copy_time']-first['launch_time'],
                     'stored_read_slots': sorted({r['slot'] for r in sol_reads if r.get('slot') is not None}),
                     'mature': mature_proxy_status(members, snap['reads'], quotes, snap['copy_time'], DEFAULTS)})
    grace = DEFAULTS['live_new_seconds']
    n = len(rows)
    older = [r for r in rows if r['age'] >= grace]
    bounds = []
    for field in ('without_volume', 'with_volume'):
        current, old = retention(rows, grace, field), retention(rows, 7200, field)
        lower_loss = max(0, old['pass_lower']-current['pass_upper'])
        upper_loss = max(0, old['pass_upper']-current['pass_lower'])
        bounds.append({'variant': field, 'one_hour': current, 'two_hour': old,
                       'one_hour_loss_copies_lower': lower_loss, 'one_hour_loss_copies_upper': upper_loss,
                       'one_hour_loss_pp_lower': 100*lower_loss/n, 'one_hour_loss_pp_upper': 100*upper_loss/n,
                       'outside_grace_recoveries_lower': sum(r['mature'][field] is True for r in older),
                       'outside_grace_recoveries_upper': sum(r['mature'][field] is not False for r in older)})
    result = {'scope': 'fixed earliest-observed SOL target; pre-graduation curve-sum proxy only',
              'production_end_to_end': {'status': 'unmeasured', 'precision': None, 'recall': None,
                                        'one_vs_two_hour_routing_recall_cost': None},
              'n': n, 'young': n-len(older), 'older': len(older), 'bounds': bounds, 'targets': rows}
    (OUT/'recall_bounds.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    lines = ['<!-- generated by scripts/narrative/recall_bounds.py -->', '# Available recall evidence and bounds', '',
             '**Production-equivalent end-to-end precision, recall and the routing-recall cost of grace '
             'shortening are unmeasured.** These are conditional fixed-target proxy bounds, not a sequential '
             'replay, a product across populations, or bounds on full-cohort production routing.', '',
             f"Anchor: {n} SOL-quoted copy targets with stored historical reads. Under the "
             f"earliest-observed-SOL-member creation proxy, {n-len(older)} are inside "
             f"the {grace/3600:g} h grace and {len(older)} are outside it. "
             'A real room could have an unobserved earlier ancestor. The reserve proxy sums independent '
             'pump curves; it is not observed reserve of the proposed shared room.', '',
             '| proxy gate variant | 1 h retention lower–upper | 2 h retention lower–upper | older targets recovered lower–upper | lost targets lower–upper | loss in retention points lower–upper |',
             '|---|---|---|---|---|---|']
    for b in bounds:
        cur, old = b['one_hour'], b['two_hour']
        lines.append(f"| {b['variant'].replace('_',' ')} | {cur['pass_lower']}/{n}–{cur['pass_upper']}/{n} "
                     f"({cur['pass_lower']/n:.2%}–{cur['pass_upper']/n:.2%}) | "
                     f"{old['pass_lower']}/{n}–{old['pass_upper']}/{n} | "
                     f"{b['outside_grace_recoveries_lower']}–{b['outside_grace_recoveries_upper']} | "
                     f"{b['one_hour_loss_copies_lower']}–{b['one_hour_loss_copies_upper']} | "
                     f"{b['one_hour_loss_pp_lower']:.2f}–{b['one_hour_loss_pp_upper']:.2f} |")
    lines += ['', 'A below-floor reserve sum is conclusive for this proxy only when every relevant '
              'member has a confirmed trade snapshot and quote coverage is complete. Non-trade/missing '
              'reads contain zero placeholders and are unknown, not proof of an empty curve. This is '
              'why the former point proxy cannot be reported as an observed routing-recall cost.', '',
              '| outside-grace copy (signature prefix) | first SOL target mint (prefix) | proxy age (s) | mature proxy status without volume | reason |',
              '|---|---|---|---|---|']
    for r in older:
        status = {True: 'passes reserve/idle', False: 'fails', None: 'unknown'}[r['mature']['without_volume']]
        lines.append(f"| {r['copy_signature'][:12]}… | {r['target_first_sol_mint'][:12]}… | {r['age']} | {status} | {r['mature']['reason']} |")
    lines += ['', 'Full signatures, member identifiers, read slots and classification details are in '
              'recall_bounds.json. No mature target is verified to pass reserve/idle in this subset, '
              'so none can be identified as a proven volume-only rejection. Volume could still affect '
              'the indeterminate targets; the data cannot determine whether it does.', '',
              'The same fixed-target age proxy alone permits recovery of any outside-grace target '
              'in a hypothetical real room. That looser sensitivity interval is not a production '
              'recall bound either: live-gate decisions alter subsequent room formation, target '
              'identities and ties. The full cohort cannot inherit the subset bounds without an '
              'explicit extrapolation, which is not used as the headline.', '',
              'To measure it later, collect room/door and SlugLock state at the replay boundary; '
              'ordered per-room reserve, status and last-trade updates; every gross-volume increment '
              'needed to rebuild trailing buckets; pool identity and cumulative LP-fee checkpoint '
              'history after graduation; and actual routing/first-buy events. Preserve slots, '
              'transaction indices within slots, timestamps and configuration versions. A pump-only '
              'backfill additionally needs an explicit, disclosed pump-to-room proxy. More launch '
              'metadata or a longer metadata-only window does not provide these state histories.']
    report = '\n'.join(lines)+'\n'
    (OUT/'recall_bounds.md').write_text(report, encoding='utf-8', newline='\n')
    print(report)


if __name__ == '__main__':
    main()
