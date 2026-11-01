"""History request compatibility, retaining usable earlier observations."""
TX_OPTIONS={'encoding':'json','commitment':'finalized','maxSupportedTransactionVersion':1}
FULL_BLOCK_OPTIONS={'encoding':'json','commitment':'finalized','maxSupportedTransactionVersion':1,
                    'transactionDetails':'full','rewards':False}


def transaction_hit(cache,signature):
    missing=None
    for version in (1,0):
        options={**TX_OPTIONS,'maxSupportedTransactionVersion':version}
        hit=cache.get('getTransaction',[signature,options])
        if hit is not None and 'result' in hit:
            if hit['result'] is not None:return hit
            missing=hit
    fallback=cache.study('block_transaction:'+signature)
    if fallback is not None:
        hit=cache.get('getBlock',fallback['params'])
        assert hit is not None and hit.get('result') is not None,'missing raw fallback block'
        block=hit['result'];entry=block['transactions'][fallback['transaction_index']]
        assert entry['transaction']['signatures'][0]==signature,'fallback transaction index mismatch'
        return {'result':{'slot':fallback['slot'],'blockTime':block.get('blockTime'),**entry},
                'source':{'method':'getBlock',**fallback}}
    return missing


def recover_missing(cache,signature_rows):
    """Recover null direct lookups from raw finalized blocks, preserving source.

    A signature absent from its advertised block stays missing. It is never
    silently declared failed, absent from history, or a zero-reserve trade.
    """
    slots={row['slot'] for row in signature_rows.values()}
    for slot in sorted(slots):
        params=[slot,FULL_BLOCK_OPTIONS]
        block=cache.call('getBlock',params)
        if block is None:continue
        for index,entry in enumerate(block.get('transactions') or []):
            signature=entry['transaction']['signatures'][0]
            if signature not in signature_rows:continue
            assert entry.get('meta') is not None and entry['meta']['err'] is None,'successful index disagrees with finalized block'
            cache.put_study('block_transaction:'+signature,{'slot':slot,'transaction_index':index,'params':params})
    return [signature for signature in signature_rows if (transaction_hit(cache,signature) or {}).get('result') is None]
