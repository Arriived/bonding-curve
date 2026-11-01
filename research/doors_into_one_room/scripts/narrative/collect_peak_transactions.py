"""Fetch complete successful histories for the frozen top-20 activity subset."""
import argparse
import concurrent.futures
import hashlib
import json
import time

from audit_liveness_brief import OUT
from history_cache import Cache, utc
from peak_signatures import member_signatures
from peak_rpc import TX_OPTIONS,transaction_hit,recover_missing
from preregister_peak_consolidation import PATH

SELECTION = OUT / 'peak_search_selection.json'


def selected_groups(cache):
    protocol=json.loads(PATH.read_text(encoding='utf-8'))
    amendment=json.loads((OUT/'peak_search_protocol.json').read_text(encoding='utf-8'))
    ranking_path=OUT/'peak_activity_ranking.json'
    ranking=json.loads(ranking_path.read_text(encoding='utf-8'))
    assert ranking['ranking_complete'], 'all address counts must be complete before selection'
    chosen=ranking['ranking'][:amendment['selection_size']]
    roots=[g['root_mint'] for g in chosen]
    frozen={'rank_file_sha256':hashlib.sha256(ranking_path.read_bytes()).hexdigest(),
        'rank_finished_at_utc':ranking['finished_at_utc'], 'root_mints':roots,
        'selection':'top 20 by complete total signature count; ties root mint',
        'counts':[{k:g[k] for k in ('root_mint','member_count','total_signature_count','successful_signature_references')} for g in chosen]}
    if SELECTION.exists():
        old=json.loads(SELECTION.read_text(encoding='utf-8'))
        assert old['root_mints']==roots, 'frozen top-20 membership changed'
        if old['counts']!=frozen['counts']:
            assert not any(cache.study('top20_measured:'+root) for root in roots), 'counts changed after validated outcomes'
            frozen['frozen_at_utc']=old['frozen_at_utc']
            frozen['boundary_audit']={'at_utc':utc(),'earlier_counts':old['counts'],
                'reason':'Retain the entire creation slot; within-slot signature listing is not execution order.',
                'top20_membership_changed':False,'before_any_validated_cluster_outcome':True}
            SELECTION.write_text(json.dumps(frozen,indent=2)+'\n',encoding='utf-8',newline='\n')
    else:
        frozen['frozen_at_utc']=utc()
        SELECTION.write_text(json.dumps(frozen,indent=2)+'\n',encoding='utf-8',newline='\n')
    by_root={g['root_mint']:g for g in protocol['groups']}
    groups=[by_root[root] for root in roots]
    assert all(not g['completed'] for g in groups)
    histories={}
    for g in groups:
        for member in g['members']:
            record=cache.study('rank_signatures:'+member['mint'])
            histories[member['mint']]=member_signatures(cache,member,record)
    return groups,histories


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qps',type=float,default=3)
    parser.add_argument('--batch-size',type=int,default=10)
    parser.add_argument('--workers',type=int,default=4,help='bounded in-flight requests sharing one logical rate limiter')
    parser.add_argument('--max-batches',type=int,default=0,help='optional short transport probe; zero means all')
    args=parser.parse_args(); assert 1<=args.batch_size<=20 and 1<=args.workers<=8
    cache=Cache(qps=args.qps)
    groups,histories=selected_groups(cache)
    started=cache.study('top20_transactions_started') or {'utc':utc(),'unix':time.time()}
    cache.put_study('top20_transactions_started',started)
    all_success={r['signature'] for rows in histories.values() for r in rows if r['err'] is None}
    cache.put_study('top20_required_unique_transactions',len(all_success))
    summary={'started_at_utc':started['utc'],'required_unique_successful_transactions':len(all_success),
        'selected_members':len(histories),'selected_clusters':len(groups),'logical_qps':args.qps,
        'batch_size':args.batch_size,'workers':args.workers,'clusters':[]}
    batches=0
    try:
        for rank,g in enumerate(groups,1):
            rows={r['signature']:r for member in g['members'] for r in histories[member['mint']] if r['err'] is None}
            signatures=sorted(rows,key=lambda s:(rows[s]['slot'],s))
            todo=[s for s in signatures if transaction_hit(cache,s) is None]
            print(f'Rank {rank}/20 {g["root_mint"]}: {len(signatures)} successful transactions, {len(todo)} uncached',flush=True)
            parts=[todo[offset:offset+args.batch_size] for offset in range(0,len(todo),args.batch_size)]
            if args.max_batches:parts=parts[:max(0,args.max_batches-batches)]
            def fetch(part):
                cache.call_many([('getTransaction',[s,TX_OPTIONS]) for s in part]);return len(part)
            completed=0;iterator=iter(parts)
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
                pending={pool.submit(fetch,part) for part in [next(iterator,None) for _ in range(args.workers)] if part}
                while pending:
                    finished,pending=concurrent.futures.wait(pending,return_when=concurrent.futures.FIRST_COMPLETED)
                    for future in finished:
                        completed+=future.result();batches+=1
                        progress={'rank':rank,'root_mint':g['root_mint'],'completed_current':completed,
                            'uncached_at_start':len(todo),'updated_at_utc':utc(),'elapsed_seconds':time.time()-started['unix']}
                        cache.put_study('top20_transaction_progress',progress)
                        if batches%25==0:print(json.dumps(progress),flush=True)
                        part=next(iterator,None)
                        if part:pending.add(pool.submit(fetch,part))
            if args.max_batches and batches>=args.max_batches:return
            missing=[s for s in signatures if (transaction_hit(cache,s) or {}).get('result') is None]
            if missing:
                print(f'Recovering {len(missing)} null transaction lookups from their finalized blocks.',flush=True)
                missing=recover_missing(cache,{signature:rows[signature] for signature in missing})
            record={'rank':rank,'root_mint':g['root_mint'],'unique_successful_signatures':len(signatures),
                'missing_transactions':missing,'complete':not missing,'finished_at_utc':utc()}
            cache.put_study('top20_fetched:'+g['root_mint'],record)
            summary['clusters'].append(record)
            if missing:
                from report_peak_consolidation import main as report
                report()
                raise SystemExit('STOP: successful signatures still lack transaction bodies after finalized-block recovery; history is unknown.')
            # Only fully fetched clusters are analysed. Missing observations never become zero reserves.
            if not missing:
                from measure_peak_consolidation import measure_group
                result=measure_group(cache,g,histories)
                cache.put_study('top20_measured:'+g['root_mint'],result)
                print('MEASURED '+json.dumps({k:result.get(k) for k in ('root_mint','status','peak_pooled_lamports','max_individual_peak_lamports','spec_additional_crossing')}),flush=True)
                if result.get('spec_additional_crossing'):
                    cache.put_study('top20_crossing_found',{'root_mint':g['root_mint'],'at_utc':utc(),
                        'peak_pooled_lamports':result['peak_pooled_lamports'],'max_individual_peak_lamports':result['max_individual_peak_lamports']})
                from report_peak_consolidation import main as report
                report()
                if result['status']!='complete':
                    raise SystemExit('STOP: a fully fetched cluster failed validation; review its recorded issues before further collection.')
        summary['finished_at_utc']=utc()
        summary['elapsed_seconds']=time.time()-started['unix']
        summary['all_fetched']=all(g['complete'] for g in summary['clusters'])
        (OUT/'peak_transaction_collection.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n')
        cache.put_study('top20_collection',summary)
        from report_peak_consolidation import main as report
        report()
    finally: cache.checkpoint()


if __name__=='__main__':main()
