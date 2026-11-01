"""Cache pinned official event schemas; no transaction outcomes are requested."""
import hashlib
import json
import urllib.request

from audit_liveness_brief import OUT


def main():
    sha=json.loads((OUT/'consolidation_sources.json').read_text(encoding='utf-8'))['pump_commit']
    result={}
    for name in ('pump','pump_amm'):
        url=f'https://raw.githubusercontent.com/pump-fun/pump-public-docs/{sha}/idl/{name}.json'
        with urllib.request.urlopen(url,timeout=25) as response:raw=response.read()
        obj=json.loads(raw)
        wanted=({'TradeEvent','CreateEvent','CompleteEvent','CompletePumpAmmMigrationEvent','Shareholder'} if name=='pump' else
                {'BuyEvent','SellEvent','DepositEvent','WithdrawEvent','CreatePoolEvent','SweepPoolFeeEvent'})
        result[name]={'url':url,'sha256':hashlib.sha256(raw).hexdigest(),'program':obj['address'],
            'events':[e for e in obj['events'] if e['name'] in wanted],
            'types':[t for t in obj['types'] if t['name'] in wanted],
            'instructions':[{'name':i['name'],'discriminator':i['discriminator'],'accounts':i['accounts']} for i in obj['instructions']]}
    (OUT/'peak_event_sources.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Pinned event and instruction schemas cached.')


if __name__=='__main__':main()
