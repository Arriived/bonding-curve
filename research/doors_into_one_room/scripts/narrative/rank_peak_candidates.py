"""Owner-directed existence search: rank uncompleted copy clusters by full activity.

Counts are actual complete signature lists through the fixed stock cutoff, not
1,000-entry first-page caps. Full transactions are not requested by this stage.
"""
import argparse
import concurrent.futures
import datetime
import gzip
import hashlib
import json
import time

from audit_liveness_brief import OUT,ROOT
from collect_peak_history import next_anchor
from history_cache import Cache,readonly,utc
from preregister_peak_consolidation import PATH
from peak_signatures import member_signatures


def count_member(cache,group,member,anchor):
    key='rank_signatures:'+member['mint']
    old=cache.study(key)
    if old and old.get('complete'):return old
    params=[member['curve'],{'commitment':'finalized','limit':1000,'before':anchor['signature']}]
    pages=[];signatures={};found_birth=False
    while True:
        rows=cache.call('getSignaturesForAddress',params)
        pages.append(params)
        for r in rows:
            assert r['slot']<=group['cutoff_slot']
            if r['slot']<member['launch_slot']:continue
            signatures[r['signature']]=r
            if r['signature']==member['launch_signature']:
                found_birth=True;break
        if found_birth or len(rows)<1000:break
        params=[member['curve'],{'commitment':'finalized','limit':1000,'before':rows[-1]['signature']}]
    record={'mint':member['mint'],'root_mint':group['root_mint'],'pages':pages,
        'signature_count':len(signatures),'successful_count':sum(r.get('err') is None for r in signatures.values()),
        'creation_found':found_birth,'complete':found_birth,'finished_at_utc':utc()}
    cache.put_study(key,record)
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qps',type=float,default=.8)
    parser.add_argument('--workers',type=int,default=3)
    args=parser.parse_args()
    protocol=json.loads(PATH.read_text(encoding='utf-8'))
    groups=[g for g in protocol['groups'] if not g['completed']]
    cache=Cache(qps=args.qps)
    start=cache.study('ranking_started') or {'at_utc':utc(),'unix':time.time()}
    cache.put_study('ranking_started',start)
    anchors={slot:next_anchor(cache,slot) for slot in sorted({g['cutoff_slot'] for g in groups})}
    work=[(g,m) for g in groups for m in g['members']]
    def run(item):
        g,m=item
        try:return count_member(cache,g,m,anchors[g['cutoff_slot']])
        except Exception as e:
            record={'mint':m['mint'],'root_mint':g['root_mint'],'complete':False,'error':str(e),'finished_at_utc':utc()}
            cache.put_study('rank_signatures:'+m['mint'],record);return record
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            records=[]
            for record in pool.map(run,work):
                records.append(record)
                if len(records)%50==0:print(f'Full activity counts {len(records)}/{len(work)} members',flush=True)
        by_mint={r['mint']:r for r in records}
        for g,m in work:
            record=by_mint[m['mint']]
            if not record['complete']:continue
            rows=member_signatures(cache,m,record)
            record['signature_count']=len(rows)
            record['successful_count']=sum(r.get('err') is None for r in rows)
            cache.put_study('rank_signatures:'+m['mint'],record)
        ranking=[]
        for g in groups:
            members=[by_mint[m['mint']] for m in g['members']]
            ranking.append({'root_mint':g['root_mint'],'member_count':g['member_count'],
                'total_signature_count':sum(m.get('signature_count',0) for m in members),
                'successful_signature_references':sum(m.get('successful_count',0) for m in members),
                'complete':all(m['complete'] for m in members),'members':members})
        ranking.sort(key=lambda r:(-r['total_signature_count'],r['root_mint']))
        result={'started_at_utc':start['at_utc'],'finished_at_utc':utc(),'elapsed_seconds':time.time()-start['unix'],
            'candidate_clusters':len(groups),'candidate_members':len(work),
            'fully_counted_members':sum(r['complete'] for r in records),
            'ranking_complete':all(r['complete'] for r in records),'ranking':ranking,
            'selection':'top 20 by sum of complete per-member signature counts, ties root mint; no completion-containing cluster included'}
        (OUT/'peak_activity_ranking.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
        cache.put_study('activity_ranking',result)
        if not result['ranking_complete']:raise SystemExit('STOP: incomplete address histories prevent a certified top-20 activity ranking.')
        print(json.dumps({k:v for k,v in result.items() if k!='ranking'},indent=2))
    finally:cache.checkpoint()


if __name__=='__main__':main()
