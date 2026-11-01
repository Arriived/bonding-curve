"""Verify schema rent against mainnet and record a bracketing finalized slot range."""
import datetime
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import account_sizes as A

OUT=Path(__file__).resolve().parents[2]/'outputs/narrative/current_rent.json'
RPC='https://api.mainnet-beta.solana.com'


def rpc(method,params):
    request=urllib.request.Request(RPC,data=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode(),
                                   headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=20) as response:
        value=json.load(response)
    if 'error' in value:
        raise RuntimeError(value['error'])
    return value['result']


def main():
    if '--confirm' in sys.argv:
        rows=[]
        for size in (0,165):
            before=rpc('getSlot',[{'commitment':'finalized'}])
            actual=rpc('getMinimumBalanceForRentExemption',[size,{'commitment':'finalized'}])
            after=rpc('getSlot',[{'commitment':'finalized'}])
            rows.append({'method':'getMinimumBalanceForRentExemption','params':[size,{'commitment':'finalized'}],
                         'result':actual,'finalized_slot_before':before,'finalized_slot_after':after})
        report={'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'rpc':RPC,'note':'Raw rent-exemption RPC results, not account balances; method has no context slot.',
                'reads':rows}
        OUT.with_name('rent_confirmation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
        print(json.dumps(report,indent=2))
        if any(row['result']!=A.rent(row['params'][0]) for row in rows):
            raise SystemExit('Confirmed rent minima conflict with the schema; stop and record the correction.')
        return
    sizes={0,165,170,A.meme_mint(32,10,200,[(4,44)]),A.meme_mint(32,10,200,[(4,44),(4,10)])}
    sizes.update(sum(n for _,n in fields) for fields in A.LAYOUTS.values())
    before=rpc('getSlot',[{'commitment':'finalized'}])
    rows=[]
    for size in sorted(sizes):
        actual=rpc('getMinimumBalanceForRentExemption',[size,{'commitment':'finalized'}])
        rows.append({'data_bytes':size,'rpc_lamports':actual,'model_lamports':A.rent(size),'matches':actual==A.rent(size)})
        time.sleep(.25)
    after=rpc('getSlot',[{'commitment':'finalized'}])
    report={'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rpc':RPC,
            'slot_before':before,'slot_after':after,
            'note':'Rent RPC has no context slot; finalized getSlot reads bracket the requests, not an atomic snapshot.',
            'all_match':all(r['matches'] for r in rows),'rows':rows}
    OUT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report,indent=2))
    if not report['all_match']:
        raise SystemExit('Rent conflicts with schema model; stop and record the correction.')


if __name__=='__main__':
    main()
