"""Exact simultaneous curve-reserve peaks and reserve-directed lifetime inflow.

Only the owner-selected, uncompleted clusters are measured. Program-emitted
post-trade reserve counters are used, never wallet balances or summed member
peaks. Ambiguous transaction ordering is resolved against finalized blocks.
"""
import collections
import argparse
import concurrent.futures
import gzip
import json
from decimal import Decimal,ROUND_CEILING

from audit_liveness_brief import OUT
from history_cache import utc
from peak_events import Decoder
from peak_rpc import transaction_hit
from preregister_peak_consolidation import PATH

BLOCK_OPTIONS={'commitment':'finalized','transactionDetails':'signatures','rewards':False,'maxSupportedTransactionVersion':0}
NATIVE={'11111111111111111111111111111111','So11111111111111111111111111111111111111112'}


def block_order(cache,slot):
    block=cache.call('getBlock',[slot,BLOCK_OPTIONS])
    assert block and block.get('signatures'), f'missing finalized block {slot}'
    return {signature:index for index,signature in enumerate(block['signatures'])}


def reserve_fields(fields):
    # Legacy SOL instructions use the original SOL fields. General-quote v2/v3
    # instructions may populate the appended quote fields instead.
    if fields.get('quote_mint') is not None:
        assert fields['quote_mint'] in NATIVE, 'non-native quote in SOL cohort'
    old=fields.get('real_sol_reserves');new=fields.get('real_quote_reserves')
    if old is None and new is None:raise AssertionError('missing core reserve field')
    if old and new:assert old==new, 'disagreeing SOL and native-quote reserve fields'
    return new if new else old if old is not None else new


def trajectory(events,members,order_provider):
    """Resolve per-member order first; lazily resolve other slots only if needed.

    The sum of slot-local member maxima is used solely to prune slots that
    cannot beat an already observed simultaneous peak. It is never a measured
    pooled peak. A block order is fetched for every ambiguous member slot and
    every remaining slot whose upper bound could improve the result.
    """
    by_slot=collections.defaultdict(list)
    for e in events:by_slot[e['slot']].append(e)
    orders={}
    for slot,rows in by_slot.items():
        by_mint=collections.defaultdict(set)
        for e in rows:by_mint[e['mint']].add(e['signature'])
        if any(len(s)>1 for s in by_mint.values()):orders[slot]=order_provider(slot)
    def ordered(rows,order):
        assert all(e['signature'] in order for e in rows), 'transaction absent from finalized block'
        return sorted(rows,key=lambda e:(order[e['signature']],e['outer'],e['inner']))
    def replay_slot(rows,start,order):
        state=dict(start);total=sum(state.values());peak=total;witness=None
        for e in ordered(rows,order):
            total+=e['reserve_lamports']-state[e['mint']];state[e['mint']]=e['reserve_lamports']
            if total>peak:peak=total;witness={k:e[k] for k in ('slot','signature','outer','inner')}
        return peak,witness,state
    state={m:0 for m in members};individual={m:0 for m in members}
    gross={m:0 for m in members};sell={m:0 for m in members};buy_events=[]
    peak=0;witness=None;candidates=[];slot_bounds=[];amount_checks=collections.Counter()
    for slot,rows in sorted(by_slot.items()):
        start=dict(state);by_mint=collections.defaultdict(list)
        for e in rows:by_mint[e['mint']].append(e)
        upper=sum(start.values())
        for mint,own in by_mint.items():
            order=orders.get(slot) or {own[0]['signature']:0}
            own=ordered(own,order);local_max=state[mint]
            for e in own:
                after=e['reserve_lamports'];delta=after-state[mint]
                assert (delta>=0 if e['is_buy'] else delta<=0), f'inconsistent reserve direction {mint} {e["signature"]}'
                if e['is_buy']:
                    gross[mint]+=delta;buy_events.append({**e,'gross_inflow_lamports':delta})
                else:sell[mint]-=delta
                amount_checks[str(abs(delta)==e.get('quoted_amount'))]+=1
                state[mint]=after;local_max=max(local_max,after);individual[mint]=max(individual[mint],after)
            upper+=local_max-start[mint]
        signatures={e['signature'] for e in rows}
        if slot in orders or len(signatures)==1:
            order=orders.get(slot) or {next(iter(signatures)):0}
            value,where,end=replay_slot(rows,start,order)
            assert end==state
            if value>peak:peak=value;witness=where
        else:
            # Slot boundaries are real simultaneous states, even before the
            # ordering of the slot's internal transactions is resolved.
            boundary=max(sum(start.values()),sum(state.values()))
            if boundary>peak:
                peak=boundary;witness={'slot':slot,'boundary':'start' if sum(start.values())>=sum(state.values()) else 'end'}
            candidates.append((upper,slot,rows,start))
        slot_bounds.append({'slot':slot,'start_lamports':sum(start.values()),'end_lamports':sum(state.values()),'upper_lamports':upper})
    pruned=0
    for upper,slot,rows,start in sorted(candidates,key=lambda x:(-x[0],x[1])):
        if upper<=peak:pruned+=1;continue
        order=order_provider(slot);orders[slot]=order
        value,where,_=replay_slot(rows,start,order)
        if value>peak:peak=value;witness=where
    return {'peak_pooled_lamports':peak,'peak_witness':witness,
        'individual_peak_lamports':individual,'terminal_lamports':state,
        'gross_inflow_lamports':gross,'sell_outflow_lamports':sell,'buy_events':buy_events,
        'ordering_blocks_required':sorted(orders),'ambiguous_slots_pruned':pruned,
        'slot_count':len(by_slot),'event_amount_matches_reserve_delta':dict(amount_checks)}


def measure_group(cache,group,histories):
    decoder=Decoder();members={m['mint']:m for m in group['members']}
    rows={r['signature']:r for mint in members for r in histories[mint] if r['err'] is None}
    events=[];creation={};issues=[];trade_calls=0;readonly_transactions=0
    for signature,row in rows.items():
        hit=transaction_hit(cache,signature);tx=hit.get('result') if hit else None
        parsed=decoder.transaction(signature,tx)
        if parsed['status']!='decoded':issues.append({'signature':signature,'status':parsed['status']});continue
        assert tx['slot']==row['slot']<=group['cutoff_slot']
        if not parsed['inner_metadata_recorded'] and any(m['curve'] in parsed['writable_keys'] for m in members.values()):
            issues.append({'signature':signature,'status':'missing_inner_metadata_for_writable_curve'})
        if any(c['name']=='unknown_instruction' and any(m['curve'] in c['accounts'] for m in members.values()) for c in parsed.get('program_calls',[])):
            issues.append({'signature':signature,'status':'unknown_pump_instruction_for_curve'})
        own=[e for e in parsed['events'] if e['fields'].get('mint') in members]
        for e in own:
            f=e['fields'];mint=f['mint']
            if e['kind']=='CreateEvent':creation[mint]=f.get('timestamp')
            if e['kind'] in {'CompleteEvent','CompletePumpAmmMigrationEvent'}:
                issues.append({'signature':signature,'status':'unexpected_completed_member','mint':mint})
            if e['kind']!='TradeEvent':continue
            assert all(k in f for k in ('mint','is_buy','timestamp')), 'missing core trade fields'
            amount=f.get('quote_amount') or f.get('sol_amount')
            events.append({'mint':mint,'signature':signature,'slot':tx['slot'],'outer':e['outer'],'inner':e['inner'],
                'timestamp':f['timestamp'],'is_buy':f['is_buy'],'reserve_lamports':reserve_fields(f),
                'quoted_amount':amount,'event_sha256':e['event_sha256']})
        trades=[e for e in own if e['kind']=='TradeEvent']
        if not trades:readonly_transactions+=1
        for call in parsed.get('program_calls',[]):
            if not (call['name'].startswith(('buy','sell')) or call['name']=='multi_hop_curve_swap'):continue
            curve_accounts=[value for name,value in call.get('named_accounts',{}).items() if 'bonding_curve' in name]
            relevant=[m for m in members.values() if m['curve'] in curve_accounts]
            for m in relevant:
                trade_calls+=1
                matched=[e for e in trades if e['fields']['mint']==m['mint'] and e['outer']==call['outer']
                         and e['parent_instruction_inner']==call['inner']]
                # A multi-hop wrapper may call public buy/sell instructions;
                # those inner calls are checked individually instead.
                nested=call['name']=='multi_hop_curve_swap' and any(
                    c['outer']==call['outer'] and c['inner']>call['inner'] and c['depth']>call['depth']
                    and c['name'].startswith(('buy','sell')) and m['curve'] in c['accounts']
                    for c in parsed.get('program_calls',[]))
                if not matched and not nested:
                    issues.append({'signature':signature,'status':'trade_call_without_event','mint':m['mint'],'call':call})
        if parsed.get('unparsed'):issues.append({'signature':signature,'status':'event_parse_error','details':parsed['unparsed']})
    result={'root_mint':group['root_mint'],'status':'incomplete' if issues else 'complete',
        'member_count':len(members),'unique_successful_transactions':len(rows),'trade_events':len(events),
        'matched_trade_calls':trade_calls,'transactions_without_own_trade':readonly_transactions,
        'issues':issues,'cutoff_slot':group['cutoff_slot'],'cutoff_utc':group['cutoff_utc'],'measured_at_utc':utc()}
    if issues:return result
    try:
        slots=collections.defaultdict(lambda:collections.defaultdict(set))
        for event in events:slots[event['slot']][event['mint']].add(event['signature'])
        required=[slot for slot,mints in slots.items() if any(len(signatures)>1 for signatures in mints.values())]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda slot:block_order(cache,slot),required))
        path=trajectory(events,members,lambda slot:block_order(cache,slot))
        assert not path['event_amount_matches_reserve_delta'].get('False',0), 'reserve delta differs from emitted trade amount; accounting review required'
        expected={mint:m['stock_reserve_lamports'] for mint,m in members.items()}
        assert path['terminal_lamports']==expected, f'terminal reserve mismatch: {path["terminal_lamports"]} != {expected}'
        assert all(path['gross_inflow_lamports'][m]-path['sell_outflow_lamports'][m]==expected[m] for m in members)
    except Exception as error:
        result['status']='incomplete';result['issues'].append({'status':'trajectory_validation_failure','error':str(error)});return result
    buys=path.pop('buy_events');gross=path['gross_inflow_lamports'];total=sum(gross.values())
    leader=min(members,key=lambda m:(-gross[m],m));stock_leader=min(members,key=lambda m:(-expected[m],m))
    root_time=creation.get(group['root_mint']) or group['root_launch_time']
    copy_mints=set(members)-{group['root_mint']};outside=set(members)-{leader}
    def timing(mints):
        den=sum(gross[m] for m in mints)
        first=sum(e['gross_inflow_lamports'] for e in buys if e['mint'] in mints and 0<=e['timestamp']-root_time<3600)
        return {'gross_inflow_lamports':den,'first_root_hour_lamports':first,'first_root_hour_share':first/den if den else None}
    thresholds={'spec':json.loads(PATH.read_text(encoding='utf-8'))['trigger_lamports']}
    price=Decimal(json.loads(PATH.read_text(encoding='utf-8'))['price_source']['response']['data']['amount'])
    thresholds.update({str(usd)+'_usd':int((Decimal(usd)*Decimal(10**9)/price).to_integral_value(rounding=ROUND_CEILING)) for usd in (10000,50000,100000)})
    max_individual=max(path['individual_peak_lamports'].values(),default=0)
    result.update(path)
    result.update({'largest_gross_member':leader,'largest_stock_member':stock_leader,'total_gross_inflow_lamports':total,
        'copy_gross_inflow_lamports':total-gross[leader],'c_gross':(total-gross[leader])/total if total else None,
        'copy_gross_fixed_stock_leader_lamports':total-gross[stock_leader],
        'current_pooled_lamports':sum(expected.values()),'current_copy_lamports':sum(expected.values())-expected[stock_leader],
        'max_individual_peak_lamports':max_individual,
        'additional_crossings':{name:path['peak_pooled_lamports']>=threshold and max_individual<threshold for name,threshold in thresholds.items()},
        'threshold_lamports':thresholds,'funded_at_10k_peak':path['peak_pooled_lamports']>=thresholds['10000_usd'],
        'root_timestamp':root_time,'root_timestamp_source':'CreateEvent' if creation.get(group['root_mint']) else 'launch blockTime',
        'copy_launch_lags_seconds':[(creation.get(m) if creation.get(m) is not None else members[m]['launch_time'])-root_time for m in sorted(copy_mints)],
        'creation_event_members':len(creation),
        'non_root_timing':timing(copy_mints),'outside_largest_timing':timing(outside),
        'member_retention':[{'mint':m,'gross_inflow_lamports':gross[m],'sell_outflow_lamports':path['sell_outflow_lamports'][m],
            'retained_lamports':expected[m],'retained_share':expected[m]/gross[m] if gross[m] else None} for m in sorted(members)]})
    result['spec_additional_crossing']=result['additional_crossings']['spec']
    folder=OUT/'peak_trades';folder.mkdir(exist_ok=True)
    payload=''.join(json.dumps(e,sort_keys=True,separators=(',',':'))+'\n' for e in sorted(events,key=lambda e:(e['slot'],e['signature'],e['outer'],e['inner'])))
    (folder/(group['root_mint']+'.jsonl.gz')).write_bytes(gzip.compress(payload.encode(),mtime=0))
    (folder/(group['root_mint']+'.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    return result


def main():
    from collect_peak_transactions import selected_groups
    from history_cache import Cache,RPCError
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline',action='store_true',help='fail rather than requesting an uncached observation')
    args=parser.parse_args()
    class OfflineCache(Cache):
        def call(self,method,params):
            hit=self.get(method,params)
            if hit is None:raise RuntimeError('uncached offline request: '+method)
            if 'error' in hit:raise RPCError(hit['error'])
            return hit['result']
    cache=OfflineCache() if args.offline else Cache(qps=.8)
    groups,histories=selected_groups(cache)
    complete=0
    for group in groups:
        signatures={r['signature'] for m in group['members'] for r in histories[m['mint']] if r['err'] is None}
        missing=[s for s in signatures if (transaction_hit(cache,s) or {}).get('result') is None]
        if missing:
            print(json.dumps({'root_mint':group['root_mint'],'status':'missing_history','missing_transactions':len(missing)}));continue
        result=measure_group(cache,group,histories)
        cache.put_study('top20_measured:'+group['root_mint'],result)
        complete+=result['status']=='complete'
        print(json.dumps({k:result.get(k) for k in ('root_mint','status','peak_pooled_lamports','spec_additional_crossing')}))
    print(f'Validated {complete}/20 selected clusters.')
    if complete!=20:raise SystemExit(2)


if __name__=='__main__':main()
