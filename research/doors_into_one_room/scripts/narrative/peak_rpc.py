"""History request compatibility, retaining usable earlier observations."""
TX_OPTIONS={'encoding':'json','commitment':'finalized','maxSupportedTransactionVersion':1}


def transaction_hit(cache,signature):
    missing=None
    for version in (1,0):
        options={**TX_OPTIONS,'maxSupportedTransactionVersion':version}
        hit=cache.get('getTransaction',[signature,options])
        if hit is not None and 'result' in hit:
            if hit['result'] is not None:return hit
            missing=hit
    return missing
