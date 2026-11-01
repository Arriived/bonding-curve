"""Render the approved rent correction from recorded raw RPC results and current schema."""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import account_sizes as A

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs/narrative'


def main():
    initial=json.loads((OUT/'current_rent.json').read_text(encoding='utf-8'))
    confirmation=json.loads((OUT/'rent_confirmation.json').read_text(encoding='utf-8'))
    old_rate=initial['rows'][0]['model_lamports']//128
    rate=confirmation['reads'][0]['result']//128
    assert all(row['result']==(128+row['params'][0])*rate for row in confirmation['reads'])
    assert all(row['rpc_lamports']==(128+row['data_bytes'])*rate for row in initial['rows'])
    assert A.LAMPORTS_PER_BYTE==rate
    launch=A.per_room_rent_lamports()+A.per_door_rent_lamports()
    grad=A.graduation_rent_lamports()
    lines=[f"**Approved rent correction.** The old `(128 + bytes) × {old_rate:,}` model is stale. "
           f"The owner approved `(128 + bytes) × {rate:,}` after direct rent-exemption RPC confirmation. "
           "These are `getMinimumBalanceForRentExemption` results, not account balances. "
           "The method has no context slot; finalized slot reads bracket each request.",'',
           '| data bytes | raw minimum (lamports) | finalized slot before | finalized slot after |',
           '|---|---|---|---|']
    for row in confirmation['reads']:
        lines.append(f"| {row['params'][0]} | {row['result']:,} | {row['finalized_slot_before']:,} | {row['finalized_slot_after']:,} |")
    lines+=['',f"Additional size checks are recorded at slots {initial['slot_before']:,}–{initial['slot_after']:,} "
            "in `outputs/narrative/current_rent.json`; the confirmation is in `rent_confirmation.json`. "
            "The current schema's derived totals are:",'',
            '| quantity | old rate on revised schema | verified rate on revised schema |',
            '|---|---|---|',
            f'| launch rent, lamports | {launch*old_rate//rate:,} | {launch:,} |',
            f'| graduation rent, lamports | {grad*old_rate//rate:,} | {grad:,} |','',
            'All current rent-dependent spec figures are regenerated. The trigger remains a Config '
            'value snapshotted into each Room; a later rent/default change does not rewrite an old '
            'room\'s curve or graduation trigger. Runtime graduation uses the rent sysvar, not this '
            'calibration coefficient.']
    report='\n'.join(lines)+'\n'
    (OUT/'rent_correction.md').write_text(report,encoding='utf-8',newline='\n')
    print(report)


if __name__=='__main__':
    main()
