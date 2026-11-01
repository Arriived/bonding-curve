"""Atomic per-text-group SOL snapshots, including completed members' real AMM reserves.

Every group's curve, canonical pool and WSOL vault reads share one finalized
getMultipleAccounts context. Whole groups are packed into RPC batches. This is
read-only and resumable; no missing data is turned into a zero reserve.
"""
import argparse
import base64
import collections
import hashlib
import json
import struct
import time

import calibrate_text as T
from audit_liveness_brief import OUT
from collect_pump_launches import PUMP,b58d,b58e,find_pda
from collect_consolidation_outcomes import DATA,decode,request,rpc,utc,write
from label_dependency import metadata_text_routes
from liveness_reads import bonding_curve

AMM='pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA'
TOKEN='TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
ATA='ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL'
WSOL='So11111111111111111111111111111111111111112'
OUTPUT=OUT/'consolidation_cluster_balances.jsonl'
SCHEMA=OUT/'consolidation_pool_sources.json'
RUN=OUT/'consolidation_balance_collection.json'


def schema():
    if SCHEMA.exists():
        return json.loads(SCHEMA.read_text(encoding='utf-8'))
    sha=json.loads((OUT/'consolidation_sources.json').read_text(encoding='utf-8'))['pump_commit']
    base=f'https://raw.githubusercontent.com/pump-fun/pump-public-docs/{sha}/'
    amm,raw,_=request(base+'idl/pump_amm.json')
    pump,pump_raw,_=request(base+'idl/pump.json')
    pool=next(t for t in amm['types'] if t['name']=='Pool')
    disc=next(a['discriminator'] for a in amm['accounts'] if a['name']=='Pool')
    migrate=next(i for i in pump['instructions'] if i['name']=='migrate')
    accounts=[a for a in migrate['accounts'] if a['name'] in {'pool','pool_authority','pool_quote_token_account','pump_amm'}]
    offset=8;offsets={}
    lengths={'u8':1,'bool':1,'u16':2,'pubkey':32,'u64':8,'i128':16}
    for f in pool['type']['fields']:
        offsets[f['name']]=offset
        offset+=lengths[f['type']]
    assert amm['address']==AMM and offsets['pool_quote_token_account']==171
    # Preserve the official pool/authority/vault derivation and fee definitions.
    urls=[base+'docs/VIRTUAL_QUOTE_RESERVES_FEE_ADJUSTMENT.md',base+'docs/instructions/PUMP_SWAP_TRADE_V2.md']
    hashes={}
    import urllib.request
    for url in urls:
        with urllib.request.urlopen(url,timeout=25) as response: content=response.read()
        hashes[url]=hashlib.sha256(content).hexdigest()
    value={'fetched_at_utc':utc(),'commit':sha,'amm_idl_url':base+'idl/pump_amm.json',
        'amm_idl_sha256':hashlib.sha256(raw).hexdigest(),'pump_idl_sha256':hashlib.sha256(pump_raw).hexdigest(),
        'pool_type':pool,'discriminator':disc,'field_offsets':offsets,
        'migration_accounts':accounts,'official_fee_definition_sources':hashes,
        'real_pool_reserve':'WSOL token amount minus protocol_fees minus creator_fees; exclude virtual boost'}
    write(SCHEMA,value)
    return value


def pool_addresses(mint):
    authority=find_pda([b'pool-authority',b58d(mint)],PUMP)
    pool=find_pda([b'pool',b'\0\0',b58d(authority),b58d(mint),b58d(WSOL)],AMM)
    vault=find_pda([b58d(pool),b58d(TOKEN),b58d(WSOL)],ATA)
    return pool,vault


def decode_pool(pool_account,vault_account,mint,source):
    if pool_account is None:
        return {'status':'canonical_pool_absent','real_pool_quote_lamports':None}
    if pool_account['owner']!=AMM or vault_account is None or vault_account['owner']!=TOKEN:
        return {'status':'pool_or_vault_unverified','real_pool_quote_lamports':None}
    raw=base64.b64decode(pool_account['data'][0],validate=True)
    vault=base64.b64decode(vault_account['data'][0],validate=True)
    offsets=source['field_offsets']
    def pub(field):
        off=offsets[field]
        return b58e(raw[off:off+32])
    def integer(field,size=8,signed=False):
        off=offsets[field]
        return int.from_bytes(raw[off:off+size],'little',signed=signed) if len(raw)>=off+size else 0
    pool_key,vault_key=pool_addresses(mint)
    assert len(raw)>=203 and raw[:8]==bytes(source['discriminator'])
    assert pub('base_mint')==mint and pub('quote_mint')==WSOL
    assert pub('pool_quote_token_account')==vault_key
    assert len(vault)>=165 and b58e(vault[:32])==WSOL and b58e(vault[32:64])==pool_key
    amount=struct.unpack_from('<Q',vault,64)[0]
    protocol=integer('protocol_fees');creator=integer('creator_fees')
    virtual=integer('virtual_quote_reserves',16,True)
    real=amount-protocol-creator
    assert real>=0
    return {'status':'verified_canonical_pool','pool':pool_key,'quote_vault':vault_key,
        'vault_quote_lamports':amount,'protocol_fees_lamports':protocol,'creator_fees_lamports':creator,
        'virtual_quote_reserves_signed':virtual,'boost_quote_lamports':virtual+protocol+creator,
        'real_pool_quote_lamports':real}


def jobs():
    original={r['mint']:r for r in map(json.loads,DATA.read_text(encoding='utf-8').splitlines())}
    rows=[r for r in T.load(OUT/'pump_launches.jsonl') if original[r['mint']].get('sol_quoted') is True]
    routes,_=metadata_text_routes(rows)
    roots={r['candidate']:r['root'] for r in routes}
    groups=collections.defaultdict(list)
    for j,r in enumerate(rows):groups[roots.get(j,j)].append(r)
    return [{'root_mint':rows[root]['mint'],'members':members,
             'completed':{m['mint'] for m in members if original[m['mint']]['complete']}}
            for root,members in sorted(groups.items())]


def keys_for(job):
    keys=[bonding_curve(m['mint']) for m in job['members']]
    for mint in sorted(job['completed']): keys.extend(pool_addresses(mint))
    return keys


def observe(job,accounts,slot,before,after,source):
    new_completed={m['mint'] for m in job['members'] if decode(accounts[bonding_curve(m['mint'])]).get('complete') is True}
    missing=new_completed-job['completed']
    if missing:
        # Completion after the first census: re-read this entire group atomically
        # with its newly relevant canonical pool and vault, never mix slots.
        job={**job,'completed':job['completed']|missing}
        keys=keys_for(job)
        assert len(keys)<=100
        before=utc();result=rpc('getMultipleAccounts',[keys,{'encoding':'base64','commitment':'finalized'}]);after=utc()
        return observe(job,dict(zip(keys,result['value'])),result['context']['slot'],before,after,source)
    members=[]
    for m in job['members']:
        mint=m['mint'];curve=decode(accounts[bonding_curve(mint)])
        assert curve['status']=='decoded' and curve['sol_quoted']
        pool={}
        if curve['complete']:
            pool_key,vault_key=pool_addresses(mint)
            pool=decode_pool(accounts[pool_key],accounts[vault_key],mint,source)
        reserve=curve['real_quote_reserves_raw']
        if curve['complete']:
            if pool.get('real_pool_quote_lamports') is not None:
                reserve+=pool['real_pool_quote_lamports']
            elif reserve==0:
                reserve=None  # an unlocated migrated reserve is not zero
        members.append({'mint':mint,'curve':curve,'pool':pool,'real_sol_reserve_lamports':reserve})
    return {'root_mint':job['root_mint'],'context_slot':slot,'request_started_at_utc':before,
        'received_at_utc':after,'members':members,'accounts':accounts,
        'note':'Every account in this group was read in this single finalized RPC context.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collect',action='store_true')
    args=parser.parse_args()
    if not args.collect:parser.error('Use --collect for the authorized public-RPC observations.')
    source=schema()
    work=jobs()
    source_hash=hashlib.sha256(DATA.read_bytes()).hexdigest()
    previous=json.loads(RUN.read_text(encoding='utf-8')) if RUN.exists() else None
    if previous:assert previous['source_outcomes_sha256']==source_hash
    cached={r['root_mint']:r for r in map(json.loads,OUTPUT.read_text(encoding='utf-8').splitlines())} if OUTPUT.exists() else {}
    pending=[j for j in work if j['root_mint'] not in cached]
    if not pending:
        print(f'All {len(work)} group snapshots cached; no reads or timestamp changes.');return
    packs=[];pack=[];size=0
    for job in pending:
        n=len(keys_for(job));assert n<=100
        if pack and size+n>100:packs.append(pack);pack=[];size=0
        pack.append(job);size+=n
    if pack:packs.append(pack)
    run=previous or {'started_at_utc':utc(),'source_outcomes_sha256':source_hash,
         'group_count':len(work),'cached_groups':len(cached),'atomic_within_each_group':True}
    for pack in packs:
        keys=[key for job in pack for key in keys_for(job)]
        before=utc();result=rpc('getMultipleAccounts',[keys,{'encoding':'base64','commitment':'finalized'}]);after=utc()
        all_accounts=dict(zip(keys,result['value']))
        for job in pack:
            accounts={key:all_accounts[key] for key in keys_for(job)}
            row=observe(job,accounts,result['context']['slot'],before,after,source)
            with OUTPUT.open('a',encoding='utf-8',newline='\n') as handle:
                handle.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
            cached[job['root_mint']]=row
        run['cached_groups']=len(cached);write(RUN,run)
        print(f"Cached atomic groups {len(cached)}/{len(work)}; slot {result['context']['slot']}",flush=True)
        time.sleep(1)
    run['finished_at_utc']=utc();run['complete']=len(cached)==len(work)
    run['members']=sum(len(r['members']) for r in cached.values())
    run['unknown_member_balances']=sum(m['real_sol_reserve_lamports'] is None for r in cached.values() for m in r['members'])
    run['verified_pools']=sum(m['pool'].get('status')=='verified_canonical_pool' for r in cached.values() for m in r['members'])
    write(RUN,run)
    print(json.dumps(run,indent=2))


if __name__=='__main__':main()
