"""Decode real Anchor self-CPI events in execution order, from pinned IDLs."""
import hashlib
import json

from audit_liveness_brief import OUT
from collect_pump_launches import b58d,b58e

EVENT_TAG=bytes.fromhex('e445a52e51cb9a1d')


def read_value(kind,data,offset,types):
    if isinstance(kind,str):
        if kind=='pubkey':
            if len(data)<offset+32:raise EOFError
            return b58e(data[offset:offset+32]),offset+32
        if kind=='string':
            n,offset=read_value('u32',data,offset,types)
            if len(data)<offset+n:raise EOFError
            return data[offset:offset+n].decode('utf-8'),offset+n
        if kind=='bool':
            value,offset=read_value('u8',data,offset,types)
            if value not in (0,1):raise ValueError('invalid Borsh boolean')
            return bool(value),offset
        if kind[0] in 'ui' and kind[1:].isdigit():
            size=int(kind[1:])//8
            if len(data)<offset+size:raise EOFError
            return int.from_bytes(data[offset:offset+size],'little',signed=kind[0]=='i'),offset+size
        raise ValueError('unsupported primitive '+kind)
    if 'defined' in kind:
        name=kind['defined']['name'] if isinstance(kind['defined'],dict) else kind['defined']
        result={}
        for field in types[name]['fields']:
            result[field['name']],offset=read_value(field['type'],data,offset,types)
        return result,offset
    if 'vec' in kind:
        n,offset=read_value('u32',data,offset,types)
        if n>10000:raise ValueError('unreasonable vector length')
        result=[]
        for _ in range(n):
            item,offset=read_value(kind['vec'],data,offset,types);result.append(item)
        return result,offset
    if 'option' in kind:
        present,offset=read_value('u8',data,offset,types)
        if not present:return None,offset
        if present!=1:raise ValueError('invalid Borsh option')
        return read_value(kind['option'],data,offset,types)
    if 'array' in kind:
        item,n=kind['array'];result=[]
        for _ in range(n):
            value,offset=read_value(item,data,offset,types);result.append(value)
        return result,offset
    raise ValueError('unsupported Borsh shape '+repr(kind))


class Decoder:
    def __init__(self):
        source=json.loads((OUT/'peak_event_sources.json').read_text(encoding='utf-8'))
        self.events={};self.instructions={};self.types={}
        for program in source.values():
            key=program['program']
            self.types[key]={t['name']:t['type'] for t in program['types']}
            self.events[key]={bytes(e['discriminator']):e['name'] for e in program['events']}
            self.instructions[key]={bytes(i['discriminator']):i for i in program['instructions']}

    def transaction(self,signature,tx):
        if tx is None:return {'status':'missing_transaction','events':[]}
        if tx.get('meta') is None:return {'status':'missing_metadata','events':[]}
        if tx['meta'].get('err') is not None:return {'status':'failed_transaction','events':[]}
        message=tx['transaction']['message']
        keys=list(message['accountKeys'])
        if keys and isinstance(keys[0],dict):keys=[k['pubkey'] for k in keys]
        loaded=tx['meta'].get('loadedAddresses') or {}
        static_count=len(keys);header=message['header'];signed=header['numRequiredSignatures']
        writable=set(keys[:signed-header['numReadonlySignedAccounts']])
        writable.update(keys[signed:static_count-header['numReadonlyUnsignedAccounts']])
        writable.update(loaded.get('writable',[]))
        keys+=loaded.get('writable',[])+loaded.get('readonly',[])
        inner={g['index']:g['instructions'] for g in tx['meta'].get('innerInstructions') or []}
        events=[];calls=[];unparsed=[]
        for outer_index,outer in enumerate(message['instructions']):
            active={}
            trace=[(-1,outer)]+list(enumerate(inner.get(outer_index,[])))
            for inner_index,ix in trace:
                if 'programIdIndex' not in ix or 'data' not in ix:continue
                program=keys[ix['programIdIndex']]
                if program not in self.events:continue
                raw=b58d(ix['data'])
                depth=ix.get('stackHeight') or (1 if inner_index<0 else 2)
                if raw[:8]!=EVENT_TAG:
                    definition=self.instructions[program].get(raw[:8],{})
                    name=definition.get('name','unknown_instruction')
                    def account_names(definitions):
                        return [name for item in definitions for name in
                                (account_names(item['accounts']) if 'accounts' in item else [item['name']])]
                    account_keys=[keys[a] for a in ix.get('accounts',[])]
                    named_accounts=dict(zip(account_names(definition.get('accounts',[])),account_keys))
                    for key in list(active):
                        if key[1]>=depth:del active[key]
                    active[(program,depth)]=(name,inner_index)
                    calls.append({'program':program,'name':name,'outer':outer_index,'inner':inner_index,
                                  'depth':depth,'accounts':account_keys,'named_accounts':named_accounts})
                    continue
                kind=self.events[program].get(raw[8:16])
                if not kind:continue
                parents=[(h,value) for (p,h),value in active.items() if p==program and h<depth]
                parent=max(parents)[1] if parents else (None,None)
                fields={};offset=16;missing=None
                try:
                    for field in self.types[program][kind]['fields']:
                        try:value,offset=read_value(field['type'],raw,offset,self.types[program])
                        except EOFError:
                            missing=field['name'];break
                        fields[field['name']]=value
                except Exception as error:
                    unparsed.append({'kind':kind,'error':str(error),'outer':outer_index,'inner':inner_index})
                events.append({'signature':signature,'slot':tx['slot'],'block_time':tx.get('blockTime'),
                    'program':program,'kind':kind,'outer':outer_index,'inner':inner_index,'parent_instruction':parent[0],
                    'parent_instruction_inner':parent[1],
                    'fields':fields,'first_missing_trailing_field':missing,
                    'event_sha256':hashlib.sha256(raw).hexdigest()})
        return {'status':'decoded','events':events,'program_calls':calls,'unparsed':unparsed,'keys':keys,
                'writable_keys':sorted(writable),'inner_metadata_recorded':tx['meta'].get('innerInstructions') is not None}
