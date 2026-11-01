"""Resumable public-RPC snapshots for every launch in the existing sample.

python3 collect_consolidation_outcomes.py --collect
No transactions are sent. Account states are current observations, never final
or historical peaks. Raw bytes, finalized context slots and request times are
retained. A normal run resumes the same input/run without refreshing old rows.
"""
import argparse
import base64
import collections
import datetime
import hashlib
import json
import struct
import time
import urllib.error
import urllib.request

import calibrate_text as T
from audit_liveness_brief import OUT
from collect_pump_launches import PUMP,b58e
from liveness_reads import BC_DISC,bonding_curve

RPC='https://api.mainnet-beta.solana.com'
SOL_QUOTES={'11111111111111111111111111111111','So11111111111111111111111111111111111111112'}
DATA=OUT/'consolidation_outcomes.jsonl'
SOURCES=OUT/'consolidation_sources.json'
RUN=OUT/'consolidation_collection.json'


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


def request(url,payload=None):
    headers={'User-Agent':'bonding-curve-research/1.0','Accept':'application/json'}
    body=None
    if payload is not None:
        body=json.dumps(payload).encode()
        headers['Content-Type']='application/json'
    delay=1
    for attempt in range(6):
        try:
            req=urllib.request.Request(url,data=body,headers=headers)
            with urllib.request.urlopen(req,timeout=25) as response:
                data=response.read()
                date=response.headers.get('Date')
            result=json.loads(data)
            if isinstance(result,dict) and 'error' in result:
                raise RuntimeError(str(result['error']))
            return result,data,date
        except (urllib.error.URLError,TimeoutError,ConnectionError,RuntimeError):
            if attempt==5:
                raise
            time.sleep(delay)
            delay=min(delay*2,15)


def rpc(method,params):
    result,_,_=request(RPC,{'jsonrpc':'2.0','id':1,'method':method,'params':params})
    return result['result']


def sources():
    if SOURCES.exists():
        return json.loads(SOURCES.read_text(encoding='utf-8'))
    commit,_,_=request('https://api.github.com/repos/pump-fun/pump-public-docs/commits/main')
    sha=commit['sha']
    url=f'https://raw.githubusercontent.com/pump-fun/pump-public-docs/{sha}/idl/pump.json'
    idl,raw,_=request(url)
    curve=next(t for t in idl['types'] if t['name']=='BondingCurve')
    account=next(t for t in idl['accounts'] if t['name']=='BondingCurve')
    offsets={}
    offset=8
    lengths={'u64':8,'i64':8,'u8':1,'bool':1,'pubkey':32,'u16':2,'u32':4}
    for field in curve['type']['fields']:
        offsets[field['name']]=offset
        offset+=lengths[field['type']]
    assert offsets['real_quote_reserves']==32 and offsets['complete']==48 and offsets['quote_mint']==83
    assert bytes(account['discriminator'])==BC_DISC
    price,price_raw,http_date=request('https://api.coinbase.com/v2/prices/SOL-USD/spot')
    assert price['data']['base']=='SOL' and price['data']['currency']=='USD'
    output={'fetched_at_utc':utc(),'pump_commit':sha,'pump_idl_url':url,
        'pump_idl_sha256':hashlib.sha256(raw).hexdigest(),'curve_type':curve,
        'curve_discriminator':account['discriminator'],'field_offsets':offsets,
        'sol_usd':{'source_url':'https://api.coinbase.com/v2/prices/SOL-USD/spot',
            'fetched_at_utc':utc(),'http_date':http_date,'response':price,
            'response_sha256':hashlib.sha256(price_raw).hexdigest()}}
    write(SOURCES,output)
    return output


def decode(account):
    if account is None:
        return {'status':'account_absent','real_quote_reserves_raw':None,'quote_mint':None,'complete':None}
    if account['owner']!=PUMP:
        return {'status':'unexpected_owner','real_quote_reserves_raw':None,'quote_mint':None,'complete':None}
    raw=base64.b64decode(account['data'][0],validate=True)
    if raw[:8]!=BC_DISC or len(raw)<115 or raw[48] not in (0,1):
        return {'status':'unrecognised_layout','real_quote_reserves_raw':None,'quote_mint':None,'complete':None}
    quote=b58e(raw[83:115])
    return {'status':'decoded','real_quote_reserves_raw':struct.unpack_from('<Q',raw,32)[0],
        'real_token_reserves_raw':struct.unpack_from('<Q',raw,24)[0],
        'quote_mint':quote,'sol_quoted':quote in SOL_QUOTES,'complete':bool(raw[48]),
        'creator':b58e(raw[49:81]),'is_mayhem_mode':bool(raw[81]),
        'account_data_len':len(raw),'account_data_sha256':hashlib.sha256(raw).hexdigest(),
        'migration_status':'not_verified_by_curve_complete_flag'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collect',action='store_true')
    parser.add_argument('--batch-size',type=int,default=100)
    parser.add_argument('--pause',type=float,default=1.0)
    args=parser.parse_args()
    if not args.collect:
        parser.error('Use --collect for explicitly requested network observations; analysis is a separate script.')
    if not 1<=args.batch_size<=100 or args.pause<0:
        parser.error('batch size must be 1..100 and pause nonnegative')
    source_path=OUT/'pump_launches.jsonl'
    source_hash=hashlib.sha256(source_path.read_bytes()).hexdigest()
    launches=T.load(source_path)
    provenance=sources()
    run=json.loads(RUN.read_text(encoding='utf-8')) if RUN.exists() else {
        'started_at_utc':utc(),'rpc':RPC,'commitment':'finalized','source_launch_sha256':source_hash,
        'source_launches':len(launches),'batch_size':args.batch_size,'batches':[],
        'note':'Sequential finalized account snapshots, not an atomic snapshot or historical peaks.'}
    assert run['source_launch_sha256']==source_hash and run['rpc']==RPC
    cached={}
    if DATA.exists():
        for line in DATA.read_text(encoding='utf-8').splitlines():
            row=json.loads(line)
            assert row['source_launch_sha256']==source_hash
            assert row['mint'] not in cached
            cached[row['mint']]=row
    pending=[r for r in launches if r['mint'] not in cached]
    if not pending and run.get('complete'):
        print(f'Already cached {len(cached)}/{len(launches)}; no network reads or timestamp changes.')
        return
    for start in range(0,len(pending),args.batch_size):
        batch=pending[start:start+args.batch_size]
        before=utc()
        keys=[bonding_curve(r['mint']) for r in batch]
        result=rpc('getMultipleAccounts',[keys,{'encoding':'base64','commitment':'finalized'}])
        after=utc()
        slot=result['context']['slot']
        assert len(result['value'])==len(batch)
        batch_rows=[]
        for r,key,account in zip(batch,keys,result['value']):
            row={'mint':r['mint'],'curve':key,'launch_slot':r['slot'],'launch_time':r['block_time'],
                'source_launch_sha256':source_hash,'context_slot':slot,
                'request_started_at_utc':before,'received_at_utc':after,'account':account,**decode(account)}
            batch_rows.append(row)
            cached[r['mint']]=row
        with DATA.open('a',encoding='utf-8',newline='\n') as handle:
            for row in batch_rows:
                handle.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
        run['batches'].append({'context_slot':slot,'mints':[r['mint'] for r in batch],
                              'started_at_utc':before,'received_at_utc':after})
        run['cached_launches']=len(cached)
        write(RUN,run)
        print(f"Cached {len(cached)}/{len(launches)}; finalized slot {slot}",flush=True)
        time.sleep(args.pause)
    run['finished_at_utc']=utc()
    run['complete']=len(cached)==len(launches)
    run['statuses']=dict(collections.Counter(r['status'] for r in cached.values()))
    run['sol_quoted']=sum(r.get('sol_quoted') is True for r in cached.values())
    run['other_quote']=sum(r.get('sol_quoted') is False for r in cached.values())
    run['completed_flags']=sum(r.get('complete') is True for r in cached.values())
    write(RUN,run)
    print(json.dumps({k:v for k,v in run.items() if k!='batches'},indent=2))


if __name__=='__main__':
    main()
