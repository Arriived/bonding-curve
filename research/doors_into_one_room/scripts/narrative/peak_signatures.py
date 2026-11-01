"""Recover creation-bounded signature rows from the raw paginated cache."""


def member_signatures(cache, member, record):
    assert record['complete'], 'incomplete member signature pagination'
    found = False; rows = {}; previous = None;boundary=False
    pages=list(record['pages'])
    for params in pages:
        if previous is not None: assert params[1]['before'] == previous
        response = cache.get('getSignaturesForAddress', params)
        assert response is not None and 'result' in response
        page = response['result']
        for row in page:
            if row['slot'] < member['launch_slot']:
                boundary=True;break
            assert row['signature'] not in rows, 'overlapping signature pages'
            rows[row['signature']] = row
            if row['signature'] == member['launch_signature']:found = True
        if boundary or len(page)<1000:break
        previous = page[-1]['signature']
        if params==pages[-1]:
            # Preserve the entire creation slot. Signature listing order within
            # a slot is not used as execution order or to discard sibling trades.
            following=[member['curve'],{**params[1],'before':previous}]
            cache.call('getSignaturesForAddress',following)
            pages.append(following);record['pages']=pages
    assert found, 'known creation signature absent'
    return list(rows.values())
