"""Freeze the owner's top-activity existence-search amendment before full reads."""
import hashlib
import json

from audit_liveness_brief import OUT, ROOT
from history_cache import readonly, utc
from preregister_peak_consolidation import PATH


def main():
    target = OUT / 'peak_search_protocol.json'
    if target.exists():
        print('Existing amendment preserved.'); return
    with readonly() as db:
        assert db.execute("SELECT COUNT(*) FROM rpc WHERE method='getTransaction'").fetchone()[0] == 0
    original = json.loads(PATH.read_text(encoding='utf-8'))
    groups = [g for g in original['groups'] if not g['completed']]
    obj = {
        'locked_at_utc': utc(), 'original_protocol_sha256': hashlib.sha256(PATH.read_bytes()).hexdigest(),
        'authority': 'Owner response: top-20 existence search; no archive RPC configured.',
        'supersedes': ['completed-cluster lifecycle collection', 'whole-population c inference',
                       'ascending-size partial-subset scheduling', 'original stage time budgets'],
        'candidate_clusters': len(groups), 'candidate_members': sum(g['member_count'] for g in groups),
        'excluded_completed_clusters': sum(g['completed'] for g in original['groups']),
        'selection_size': 20,
        'selection': 'Descending total signature count across members, fully paginated from cutoff through creation; ties by root mint.',
        'ranking_includes_failed_transactions': True,
        'full_reads': 'All unique successful signatures of all members of the selected 20, through original fixed stock cutoffs.',
        'primary_result': 'Per-cluster simultaneous peak pooled reserve, and count crossing each threshold when no individual member ever crossed it.',
        'crossing_action': 'Report a verified crossing to owner; no extension beyond selected 20 without new authorization.',
        'negative_action': 'If no selected cluster crosses the spec trigger, report zero in the selected 20 and stop full-transaction collection.',
        'primary_c': 'Peak-pooled-reserve-weighted per-cluster gross-inflow share outside the largest-gross-inflow member; top-activity subset only.',
        'secondary_c': 'Pooled gross-inflow ratio, separately labelled.',
        'decision_limits': 'The original 25% and near-zero rules remain visible, but a selected top-activity subset cannot estimate or reject the full population without valid bounds.',
        'remainder_envelope': 'Report maximum observed peak/current ratio times largest remainder current reserve as a conditional empirical scenario only; no universal drawdown bound is established. Zero-current positive-peak cases have infinite ratios.',
        'prewindow_catalogue_collection': False,
        'rpc_environment_variable': 'SOLANA_RPC_URL',
        'raw_history_retention': 'Compressed responses, slots, query parameters and request telemetry; resume without refetching successful observations.',
    }
    target.write_text(json.dumps(obj, indent=2)+'\n', encoding='utf-8', newline='\n')
    text = '''# Owner amendment: top-20 peak existence search

The primary result is whether any selected uncompleted narrative crossed a graduation threshold in simultaneous pooled peak reserve while no member crossed alone. The original pre-registered rules (lifetime c below 25%, or zero/near-zero additional graduations) remain visible in the original protocol. This activity-selected subset does not estimate full-population c or certify the absence of a crossing elsewhere.

Before requesting any full transactions, the owner changed collection to the 20 most active of the 248 uncompleted multi-member clusters (1,201 members). The 35 clusters with a completed member already graduated while fragmented and contribute no additional graduation. Rank by the sum of fully paginated member signature counts, including failed signatures, with root mint as the tie-break. Fetch every successful transaction for the selected members through the original atomic stock cutoffs. Report all 20 pooled peaks, individual peaks and lifetime inflow shares. Stop after these 20; a crossing is grounds to discuss a funded extension, not permission to collect the remaining population.

The owner requested a drawdown-based stopping argument. The largest measured peak/current ratio, applied to the largest current reserve in the remainder, is a **conditional empirical envelope**, not a mathematical upper bound. Unmeasured clusters can have larger drawdowns; a zero-current cluster can have a positive historical peak. The report must state whether that conditional envelope falls below the threshold and must not convert it into a proven population-wide absence.

Lifetime c uses simultaneous peak-pooled reserve weights. Report the pooled gross-inflow ratio separately, retain the funded/dust split, and explain any divergence. Separate differential retention from leader choice, weighting and cohort-selection effects when comparing with the original 10.18% stock figure. No completed-cluster pool histories are needed for this amended subset. No pre-window catalogue extension is authorized. The true truncated-root count remains unknown; near-edge counts are diagnostics, since a median copy lag supplies no hard maximum lag.

No archive provider is configured. Future overrides use `SOLANA_RPC_URL`. Raw reads and telemetry remain cached and resumable. The machine-readable amendment records the lock time and original protocol hash.
'''
    (ROOT / 'PEAK_SEARCH_AMENDMENT.md').write_text(text, encoding='utf-8', newline='\n')
    print(json.dumps({k:obj[k] for k in ('locked_at_utc','candidate_clusters','candidate_members')}))


if __name__ == '__main__': main()
