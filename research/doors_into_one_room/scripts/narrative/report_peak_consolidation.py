"""Generate the top-activity peak report, including incomplete coverage honestly."""
import csv
import json
import math

from audit_liveness_brief import OUT,ROOT
from history_cache import Cache,readonly,utc
from preregister_peak_consolidation import PATH


def quantiles(values):
    values=sorted(values)
    def q(p):
        if not values:return None
        position=(len(values)-1)*p;lower=math.floor(position);upper=math.ceil(position)
        return values[lower]+(values[upper]-values[lower])*(position-lower)
    return {name:q(p) for name,p in [('p25',.25),('p50',.5),('p75',.75),('p90',.9),('p99',.99),('max',1)]}


def ratio(a,b):return a/b if b else None
def percent(value):return 'undefined' if value is None else f'{100*value:.2f}%'
def number(value):return 'unknown' if value is None else f'{value:,.3f}'


def split_metrics(groups):
    total=sum(g['total_gross_inflow_lamports'] for g in groups)
    peak=sum(g['peak_pooled_lamports'] for g in groups)
    stock=sum(g['current_pooled_lamports'] for g in groups)
    gross_copy=sum(g['copy_gross_inflow_lamports'] for g in groups)
    return {'clusters':len(groups),'gross_inflow_lamports':total,'summed_peak_weights_lamports':peak,
        'c_peak_weighted':ratio(sum(g['peak_pooled_lamports']*g['c_gross'] for g in groups if g['c_gross'] is not None),peak),
        'c_gross_pooled':ratio(gross_copy,total),
        'c_gross_fixed_stock_leader':ratio(sum(g['copy_gross_fixed_stock_leader_lamports'] for g in groups),total),
        'c_stock_same_subset':ratio(sum(g['current_copy_lamports'] for g in groups),stock),
        'current_reserve_lamports':stock,'retained_share':ratio(stock,total),
        'distribution':quantiles([g['c_gross'] for g in groups if g['c_gross'] is not None])}


def main():
    cache=Cache();pr=json.loads(PATH.read_text(encoding='utf-8'))
    selection=json.loads((OUT/'peak_search_selection.json').read_text(encoding='utf-8'))
    ranking=json.loads((OUT/'peak_activity_ranking.json').read_text(encoding='utf-8'))
    stock=json.loads((OUT/'consolidation_value.json').read_text(encoding='utf-8'))
    by_root={g['root_mint']:g for g in pr['groups']}
    records=[]
    for root in selection['root_mints']:
        result=cache.study('top20_measured:'+root)
        fetched=cache.study('top20_fetched:'+root)
        records.append(result or {'root_mint':root,'status':'missing_history' if fetched and not fetched['complete'] else 'not_measured',
                                  'missing_transactions':fetched.get('missing_transactions') if fetched else None})
    complete=[g for g in records if g['status']=='complete']
    remainder=[g for g in pr['groups'] if not g['completed'] and g['root_mint'] not in selection['root_mints']]
    all_done=len(complete)==len(records)
    thresholds=stock['thresholds']
    counts={t['label']:sum(g['peak_pooled_lamports']>=t['threshold_lamports'] and g['max_individual_peak_lamports']<t['threshold_lamports'] for g in complete) for t in thresholds}
    metrics=split_metrics(complete)
    old_c=stock['distributions']['copy_clusters_both_statuses']['weighted_mean']
    a=metrics['c_peak_weighted'];b=metrics['c_gross_pooled'];d=metrics['c_gross_fixed_stock_leader'];s=metrics['c_stock_same_subset']
    gap=None
    weighting_note='Both weightings remain undefined until complete histories are available.'
    if all(x is not None for x in (a,b,d,s)):
        gap={'weighting_points':100*(a-b),'leader_definition_points':100*(b-d),
             'differential_retention_points':100*(d-s),'cohort_selection_points':100*(s-old_c),
             'total_points':100*(a-old_c)}
        assert abs(sum(v for k,v in gap.items() if k!='total_points')-gap['total_points'])<1e-8
        if a>b:
            weighting_note=f'The peak-weighted share exceeds the pooled-inflow ratio by {100*(a-b):.2f} percentage points. Higher-copy-share clusters contribute relatively more accumulated peak capital per SOL of gross turnover.'
        elif b>a:
            weighting_note=f'The pooled-inflow ratio exceeds the peak-weighted share by {100*(b-a):.2f} percentage points. Higher-copy-share clusters contribute relatively more gross turnover per SOL of accumulated peak capital.'
        else:weighting_note='The two weighting schemes give the same aggregate share.'
    drawdowns=[ratio(g['peak_pooled_lamports'],g['current_pooled_lamports']) for g in complete]
    infinite=any(g['current_pooled_lamports']==0 and g['peak_pooled_lamports']>0 for g in complete)
    finite=[x for x in drawdowns if x is not None]
    multiplier=max(finite,default=None)
    largest=max(remainder,key=lambda g:sum(m['stock_reserve_lamports'] for m in g['members'])) if remainder else None
    largest_current=sum(m['stock_reserve_lamports'] for m in largest['members']) if largest else 0
    envelope=None if infinite or multiplier is None else multiplier*largest_current
    edge_start=min(json.loads(line)['block_time'] for line in (OUT/'pump_launches.jsonl').read_text(encoding='utf-8').splitlines() if line.strip())
    edge={}
    for name,groups in [('all_copy_clusters',pr['groups']),('uncompleted_candidates',[g for g in pr['groups'] if not g['completed']]),('selected_top20',[by_root[r] for r in selection['root_mints']])]:
        offsets=[g['root_launch_time']-edge_start for g in groups]
        edge[name]={'clusters':len(groups),'earliest_in_window_offsets_seconds':quantiles(offsets),
            'near_edge_counts':{str(t):sum(0<=x<=t for x in offsets) for t in pr['edge_diagnostics_seconds']},
            'near_edge_shares':{str(t):ratio(sum(0<=x<=t for x in offsets),len(offsets)) for t in pr['edge_diagnostics_seconds']}}
    members=[m for g in complete for m in g['member_retention']]
    nonroot_gross=sum(g['non_root_timing']['gross_inflow_lamports'] for g in complete)
    nonroot_first=sum(g['non_root_timing']['first_root_hour_lamports'] for g in complete)
    cdfs=quantiles([x for g in complete for x in g['copy_launch_lags_seconds']])
    with readonly() as db:
        method_counts=dict(db.execute('SELECT method,COUNT(*) FROM rpc GROUP BY method').fetchall())
        attempts=db.execute('SELECT COUNT(*),SUM(received_bytes),MIN(started),MAX(finished) FROM attempts').fetchone()
        http429=db.execute('SELECT COUNT(*) FROM attempts WHERE http_status=429').fetchone()[0]
        tx_range=db.execute("SELECT MIN(started),MAX(finished) FROM rpc WHERE method='getTransaction'").fetchone()
    result={'generated_at_utc':utc(),'all_top20_measured':all_done,'selected_clusters':len(records),'completed_measurements':len(complete),
        'scope':'top-activity subset of uncompleted multi-member v1 SOL clusters; not a population census',
        'already_completed_copy_clusters_excluded':sum(g['completed'] for g in pr['groups']),
        'remainder_clusters':len(remainder),'additional_counts_measured':counts if complete else {label:None for label in counts},
        'observed_additional_count_lower_bounds':counts,
        'spec_full_eligible_count_bounds':[counts['spec default'],counts['spec default']+len(remainder)+len(records)-len(complete)],
        'primary_c_metrics':metrics,'funded':split_metrics([g for g in complete if g['funded_at_10k_peak']]),
        'dust':split_metrics([g for g in complete if not g['funded_at_10k_peak']]),
        'stock_reference_c':old_c,'gap_decomposition_points':gap,
        'weighting_divergence_interpretation':weighting_note,
        'drawdown':{'measured_peak_current_ratios':quantiles(finite),'infinite_ratio_observed':infinite,
            'largest_remainder_current_lamports':largest_current,'largest_remainder_root':largest['root_mint'] if largest else None,
            'conditional_envelope_lamports':envelope,'conditional_envelope_below_spec':envelope<pr['trigger_lamports'] if envelope is not None else None,
            'unconditional_peak_upper_bound':None,'assumption':'Every remainder cluster has peak/current no greater than the largest measured ratio; not established by this sample.'},
        'copy_launch_lags_seconds':cdfs,'non_root_first_hour_inflow_share':ratio(nonroot_first,nonroot_gross),
        'member_retained_share_distribution':quantiles([m['retained_share'] for m in members if m['retained_share'] is not None]),
        'prewindow_truncated_root_count':None,'window_edge_diagnostics':edge,
        'signature_count_distribution':quantiles([g['total_signature_count'] for g in ranking['ranking']]),
        'signature_total_references':sum(g['total_signature_count'] for g in ranking['ranking']),
        'successful_signature_total_references':sum(g['successful_signature_references'] for g in ranking['ranking']),
        'rpc_observations':method_counts,'http_attempts':attempts[0],'http_429_attempts':http429,
        'received_bytes':attempts[1],'collection_start_utc':attempts[2],'collection_last_utc':attempts[3],
        'transaction_observation_range_utc':tx_range,'ranking_elapsed_seconds':ranking['elapsed_seconds'],
        'transaction_collection':cache.study('top20_collection'),'transaction_progress':cache.study('top20_transaction_progress'),
        'required_unique_transactions':cache.study('top20_required_unique_transactions'),
        'price_source':pr['price_source'],'thresholds':thresholds,'clusters':records}
    (OUT/'peak_consolidation.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    fields=['rank','root_mint','status','member_count','peak_pooled_sol','max_individual_peak_sol','current_pooled_sol','gross_inflow_sol','c_gross','spec_additional_crossing']
    with (OUT/'peak_consolidation_clusters.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader()
        for rank,g in enumerate(records,1):
            row={'rank':rank,'root_mint':g['root_mint'],'status':g['status']}
            if g['status']=='complete':
                row.update({k:g[k] for k in ('member_count','c_gross','spec_additional_crossing')})
                row.update({target:g[source]/1e9 for target,source in [('peak_pooled_sol','peak_pooled_lamports'),('max_individual_peak_sol','max_individual_peak_lamports'),('current_pooled_sol','current_pooled_lamports'),('gross_inflow_sol','total_gross_inflow_lamports')]})
            writer.writerow(row)
    title=(f'**Measured result: {counts["spec default"]} additional spec-threshold crossings in the selected top 20.**' if all_done else f'**Measurement pending: {len(complete)}/20 selected clusters have complete validated histories. No population verdict is available.**')
    lines=['<!-- generated by scripts/narrative/report_peak_consolidation.py -->','# Peak consolidation: top-activity existence search','',
        '**Pre-registered rules:** lifetime c below 25%, or zero/near-zero additional peak-pooled graduations, rejects the consolidation claim on this evidence. Near-zero was fixed at at most 2 of the original 283 clusters. Missing history is unknown.', '',title,'',
        f'The owner amended this run before full transactions to the top 20 of 248 uncompleted multi-member clusters, ranked by complete total signature counts across members, including failed transactions. The 35 copy clusters with a completed member already graduated under fragmentation and contribute no extra graduation. Exclude 743 non-SOL launches and 731 SOL singletons. The selected subset is not an estimate of all 283 clusters or the full population.', '',
        f'Fixed trigger: {pr["trigger_lamports"]/1e9:.9f} SOL. Price: ${float(pr["price_source"]["response"]["data"]["amount"]):.3f}/SOL observed {pr["price_source"]["fetched_at_utc"]}. Each history ends at its original atomic stock cutoff; the source snapshot slots span {stock["balance_slot_range"]}.', '',
        '| Rank | Root mint | Pooled peak SOL | Largest individual peak SOL | Lifetime c | Spec crossing |','|---:|---|---:|---:|---:|---|']
    for rank,g in enumerate(records,1):
        if g['status']=='complete':lines.append(f'| {rank} | `{g["root_mint"]}` | {g["peak_pooled_lamports"]/1e9:.9f} | {g["max_individual_peak_lamports"]/1e9:.9f} | {percent(g["c_gross"])} | {g["spec_additional_crossing"]} |')
        else:lines.append(f'| {rank} | `{g["root_mint"]}` | {g["status"]} | unknown | unknown | unknown |')
    lines+=['','## Count and decision','',f'Observed crossing lower bounds from {len(complete)} validated clusters: {counts}. These compare the maximum simultaneous pooled reserve with the maximum individual reserve ever reached, using each threshold separately. The count in the fixed 248-cluster in-window eligible cohort is bounded by {result["spec_full_eligible_count_bounds"]}; these bounds do not assert the original near-zero decision rule for the whole cohort. An incomplete collection supplies no negative population verdict.', '',
        'A positive crossing is an existence witness under fixed historical behaviour, not proof of the product’s causal effect. A zero in these 20 supports the negative result for this activity-selected subset; unmeasured clusters remain unknown. No remaining full transactions will be collected after the requested top-20 search without further authorization.', '',
        '## Lifetime inflow and retention','',f'Primary peak-reserve-weighted c: **{percent(a)}**. Pooled gross-inflow ratio: **{percent(b)}**. Same-subset current-stock c: {percent(s)}; original 283-cluster stock c: {percent(old_c)}. This is a top-activity subset, not full-population lifetime c. Gross inflow sums positive reserve changes on buys; it never subtracts sells or treats retained balances as lifetime spending.', '',
        f'Funded cut stays $10,000 at peak pooled reserve. Funded: {result["funded"]["clusters"]} clusters, weighted c {percent(result["funded"]["c_peak_weighted"])}. Dust: {result["dust"]["clusters"]} clusters, weighted c {percent(result["dust"]["c_peak_weighted"])}. Empty or zero-weight categories are undefined, not zero.', '',
        weighting_note+' These are different allocations of weights across clusters, not conflicting measurements of one quantity.', '',
        f'Per-cluster c distribution: {metrics["distribution"]}. Gap from original stock c, in percentage points: {gap}. The decomposition adds weighting, leader reassignment, differential retention with a fixed stock leader, and cohort selection. Only the retention term describes the gross-versus-retained accounting gap; none is a causal estimate of consolidation.', '',
        f'Overall retained/gross: {percent(metrics["retained_share"])}. Member retention distribution: {result["member_retained_share_distribution"]}. Full per-member gross buys, sell outflows and net retained reserves are in the machine-readable results. Every completed trajectory reconciles gross buys minus sell outflows to its own cached terminal reserve.', '',
        '## Timing and the unmeasured remainder','',f'Non-root launch lag distribution in seconds: {cdfs}. Non-root inflow in the first root hour: {percent(result["non_root_first_hour_inflow_share"])}. Root time uses its on-chain CreateEvent where available. These describe the selected subset; they are not matcher recall or a production grace-window counterfactual.', '',
        f'Measured peak/current ratios: {result["drawdown"]["measured_peak_current_ratios"]}; infinite ratio observed: {infinite}. Largest remainder current reserve: {largest_current/1e9:.9f} SOL. Conditional empirical envelope: {number(envelope/1e9 if envelope is not None else None)} SOL; below spec trigger: {result["drawdown"]["conditional_envelope_below_spec"]}.', '',
        '**Stopping limit:** that envelope assumes the remainder never drew down more than the worst measured cluster. No observed maximum establishes this assumption. Zero-current clusters can have positive past peaks. There is no finite certified upper bound on the remainder from these stock reads and the selected drawdowns, so this calculation cannot prove that the rest cannot qualify. Collection stops at 20 because that is the owner’s authorized negative-search scope.', '',
        f'True pre-window root count: **unknown**. Earliest in-window member offsets and near-edge counts: `{edge}`. These are risk diagnostics. A median copy lag near 188 seconds is not a maximum; the edge counts cannot bound the true truncation count. Missing siblings can hide pooled crossings; an older completed sibling could also change whether a cluster belongs in the additional-count cohort. The direction of the final count bias is therefore not certified. No backward metadata catalogue was collected.', '',
        '## Collection and reproducibility','',f'Full signature-count distribution across 248 eligible clusters: {result["signature_count_distribution"]}. Total references: {result["signature_total_references"]:,}; successful references: {result["successful_signature_total_references"]:,}. The capped first page is never used as a total count.', '',
        f'Cached RPC replies by method: {method_counts}. HTTP attempts: {attempts[0]:,}; HTTP 429s: {http429:,}; observed span {attempts[2]} to {attempts[3]}. Ranking elapsed {ranking["elapsed_seconds"]:.1f} seconds. Transaction-stage telemetry: `{result["transaction_collection"] or result["transaction_progress"]}`. Batch pacing counts logical calls, not just HTTP posts. `SOLANA_RPC_URL` is the provider override; this run uses the official public mainnet endpoint.', '',
        'Restore raw history with `python scripts/narrative/archive_peak_cache.py --restore`, then rerun `report_peak_consolidation.py`; the archive manifest records response counts and SHA-256 checks. Resume ranking with `rank_peak_candidates.py`, or selected transaction collection with `collect_peak_transactions.py`. The working SQLite file is excluded from Git; verified compressed archive parts retain raw query parameters, timestamps, responses and attempt telemetry. Event schemas are pinned to the official Pump IDL commit recorded in `peak_event_sources.json`.', '',
        'Run `python scripts/narrative/measure_peak_consolidation.py --offline` to recompute the measurements from cached raw transactions. Every reserve delta must equal the emitted trade amount, and each terminal reserve must match its stock snapshot. Ambiguous member ordering uses finalized block signatures. A slot-local sum of maxima is used only to prune slots that cannot beat an already observed pooled peak; it is never reported as a simultaneous peak. Other ordering that could change the peak is resolved exactly. The event JSONL files retain slot/signature/instruction keys and do not claim lexicographic signature order is chain execution order.', '',
        '## Corrections and limitations','',
        '- Owner rescope: an activity-selected existence search supersedes a full census and the earlier size-selected time budget. Full-population lifetime c is not measured by this run.',
        '- Signature pages cap at 1,000. Full pagination to the known creation signature is required before ranking; failed signatures affect activity rank but have no executed reserve changes.',
        '- The creation slot is retained in full; signature-list ordering within that slot does not decide which transactions existed after creation. Actual reserve changes use finalized block execution order.',
        '- First-hour inflow uses age strictly below 3,600 seconds, matching the v1 grace gate. USD thresholds round upward to the next whole lamport, matching the stock study; the prototype used nearest-integer rounding.',
        '- Indexed successful signatures can have null direct transaction lookups. The collector attempts recovery from raw finalized blocks at their advertised slots, records the block and transaction index as provenance, and stops if any body remains missing. Missing signatures are never silently excluded.',
        '- Public RPC returned -32015 for transaction version 1 when the prototype requested version 0. Requests now allow version 1 and reuse usable earlier responses. The [official JSON format documentation](https://solana.com/docs/rpc/json-structures) also specifies this setting. A trial at 3 logical calls/second encountered throttling; collection resumed at 0.8, honoring Retry-After and retrying only unresolved items.',
        '- The bulk-history probe on the official endpoint was throttled, so support is unestablished. A single known historical transaction returned null from the documented keyless Solana Tracker endpoint; it was not used as a replacement history source. Probe details are retained in peak_provider_probe.json and its compressed cache.',
        '- Median lag is not a maximum, and observed drawdown is not a universal cap. Neither requested heuristic is presented as a certified upper bound.',
        '- Current reserve is a lower bound on a member’s historical peak. Completed groups are excluded for already having graduated, not because zero migrated curve balances are missing data.',
        '- This is one 1.72-hour Halloween launch window. Strict v1 folded text grouping is unchanged; no semantic labels, simulated buyers or broader grouping were introduced.',
        '- With historical flows fixed, simultaneous pooled reserve is an accounting upper bound under perfect matcher capture. It is not an empirical upper bound when buyer/seller behaviour changes. Slippage, selling and routing can change.', '']
    (ROOT/'PEAK_CONSOLIDATION_VALUE.md').write_text('\n'.join(lines),encoding='utf-8',newline='\n')
    print(json.dumps({'complete':all_done,'measured':len(complete),'counts':counts,'primary_c':a},indent=2))


if __name__=='__main__':main()
