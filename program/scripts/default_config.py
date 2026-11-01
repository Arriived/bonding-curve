"""Generate deployment defaults from the existing verified research outputs.

Only public keys are inputs. This prints JSON; it never signs or sends anything.
"""
import argparse,json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research/doors_into_one_room/scripts/narrative'))
from matcher import DEFAULTS

def main():
    p=argparse.ArgumentParser();p.add_argument('--matcher',required=True);p.add_argument('--recipient',required=True);a=p.parse_args()
    q=json.loads((ROOT/'research/doors_into_one_room/outputs/curve_quantities.json').read_text())
    settings={'protocol_fee_recipient':a.recipient,'fee_bps':100,'door_share_bps':6000,
        'founder_share_bps':0,'door_fee_lamports':0,'room_fee_lamports':0,'convert_fee_lamports':0,
        'v_sol_lamports':q['v_sol_lamports'],'v_tok':q['v_tok_base'],'supply':10**15,
        'r_star_lamports':q['r_star'],'meteora_dynamic_config':'11111111111111111111111111111111',
        'graduation_trigger_lamports':q['trigger'],'paused':False,'matcher_authority':a.matcher}
    settings.update({k:v for k,v in DEFAULTS.items() if k in ['live_min_reserve_lamports','live_max_idle_seconds','live_new_seconds','live_min_volume_lamports','pool_min_window_lp_fee']})
    # Decimal strings keep u64 exact across JavaScript JSON parsing.
    u64={k for k in settings if k.endswith('_lamports') or k.endswith('_seconds')}|{'v_tok','supply','pool_min_window_lp_fee'}
    print(json.dumps({k:str(v) if k in u64 else v for k,v in settings.items()},indent=2))
if __name__=='__main__':main()
