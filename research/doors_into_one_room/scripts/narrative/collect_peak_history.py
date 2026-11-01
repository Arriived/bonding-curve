"""Two-stage, resumable history collection. Stage one fetches signature pages only."""
import argparse
import concurrent.futures
import json
import time

from audit_liveness_brief import OUT
from history_cache import Cache,RPCError,utc
from preregister_peak_consolidation import PATH


def next_anchor(cache,slot):
    for offset in range(1,40):
        try:
            block=cache.call('getBlock',[slot+offset,{'commitment':'finalized','transactionDetails':'signatures','rewards':False,'maxSupportedTransactionVersion':0}])
        except RPCError as e:
            if e.error.get('code') in {-32007,-32009}:continue
            raise
        if block and block.get('signatures'):
            return {'slot':slot+offset,'signature':block['signatures'][0]}
    raise RuntimeError('No next-block signature for the fixed snapshot cutoff')


def census(cache,protocol,workers):
    started=cache.study('census_started') or {'utc':utc(),'unix':time.time()}
    cache.put_study('census_started',started)
    end=started['unix']+protocol['signature_census_budget_seconds']
    anchors={}
    for slot in sorted({g['cutoff_slot'] for g in protocol['groups']}):
        anchors[slot]=next_anchor(cache,slot)
    work=[]
    for g in protocol['groups']:
        for m in g['members']:
            for kind in ('curve','pool','quote_vault'):
                if not m.get(kind):continue
                params=[m[kind],{'commitment':'finalized','limit':1000,'before':anchors[g['cutoff_slot']]['signature']}]
                key=f"census:{g['root_mint']}:{m['mint']}:{kind}"
                work.append((key,params,{'root_mint':g['root_mint'],'member_count':g['member_count'],
                    'mint':m['mint'],'kind':kind,'address':m[kind],'cutoff_slot':g['cutoff_slot'],
                    'launch_slot':m['launch_slot'],'launch_signature':m['launch_signature']}))
    def run(job):
        key,params,info=job
        old=cache.study(key)
        if old and old.get('status')=='observed':return old
        if time.time()>=end:return None
        try:
            rows=cache.call('getSignaturesForAddress',params)
            assert all(r['slot']<=info['cutoff_slot'] for r in rows), 'cutoff anchor leaked future transactions'
            info={**info,'params':params,'page_count':len(rows),'successful_signatures':sum(r.get('err') is None for r in rows),
                  'page_full':len(rows)==1000,'creation_in_page':any(r['signature']==info['launch_signature'] for r in rows),
                  'oldest_slot':min((r['slot'] for r in rows),default=None),'newest_slot':max((r['slot'] for r in rows),default=None),
                  'status':'observed','finished_at_utc':utc()}
        except Exception as error:
            info={**info,'status':'request_failed','error':str(error),'finished_at_utc':utc()}
        cache.put_study(key,info)
        return info
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        results=[]
        for result in pool.map(run,work):
            if result:results.append(result)
            if len(results) and len(results)%100==0:print(f'Signature census {len(results)}/{len(work)}',flush=True)
    finish={'started_at_utc':started['utc'],'finished_at_utc':utc(),'elapsed_seconds':time.time()-started['unix'],
        'requested_addresses':len(work),'observed_addresses':sum(r['status']=='observed' for r in results),
        'failed_addresses':sum(r['status']!='observed' for r in results),'deadline_reached':time.time()>=end,
        'results':results}
    cache.put_study('census_report',finish)
    (OUT/'peak_signature_census.json').write_text(json.dumps(finish,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in finish.items() if k!='results'},indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',choices=['census'],default='census')
    parser.add_argument('--qps',type=float,default=3)
    parser.add_argument('--workers',type=int,default=3)
    args=parser.parse_args()
    protocol=json.loads(PATH.read_text(encoding='utf-8'))
    cache=Cache(qps=args.qps)
    try:census(cache,protocol,args.workers)
    finally:cache.checkpoint()


if __name__=='__main__':main()
