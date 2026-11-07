"""Bound the devnet float from the SBF scenarios and the recorded devnet rent read."""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("scenarios", type=Path, help="paired_doors.json from the Linux verification artifact")
args = parser.parse_args()
cases = json.loads(args.scenarios.read_text(encoding="utf-8"))
root = Path(__file__).resolve().parents[2]
room = json.loads((root / "research/doors_into_one_room/outputs/curve_quantities.json").read_text(encoding="utf-8"))
vs, vt = room["v_sol_lamports"], room["v_tok_base"]
k = vs * vt
sol = 10**9

def integral(sold):
    return vs * sold // (vt - sold)

def quote(sold):
    return 30*sol * (vt-sold)**2 // k

def one_case(row):
    seed = row["initial_room_sol"]
    start_sold = vt - k // (vs + seed*sol + 1) - 1 if seed else 0
    final = row["steps"][-1]
    quotes = {0: quote(0), 1: quote(start_sold), 2: quote(start_sold)}
    redeemed = sum(quotes[d["index"]] * d["door_sold_base"] // (vt - d["door_sold_base"]) for d in final["doors"])
    sold = final["room_sold_base"]
    exit_gross = integral(sold) - integral(sold - redeemed)
    reserve_left = final["room_reserve_lamports"] - exit_gross
    gross = [2*sol] + [sol]*20 + ([seed * 1_010_000_000] if seed else [])
    net = sum(x*100//101 for x in gross)
    buy_fees = sum(gross) - net
    sell_gross = net - final["room_reserve_lamports"] + exit_gross
    sale_fee_upper = sell_gross//100 + 25
    return sum(gross), reserve_left + buy_fees + sale_fee_upper

measured = [one_case(row) for row in cases]
# getMinimumBalanceForRentExemption, bracketed by finalized slot 519485996.
# ProgramData includes the 584816-byte pinned ELF and 45 bytes of metadata.
rent_slot = 519_485_996
deploy_rent = 2_971_744_120 + 833_120
account_rent = len(cases) * (32*11_054_080 + 44*1_950_720)
overhead = len(cases)*200*10_002 + sol//10
upper = max(x for x,_ in measured) + sum(loss for _,loss in measured) + deploy_rent + account_rent + overhead
print(json.dumps({"rent_read_finalized_slot":rent_slot, "cases":len(cases), "peak_buy_float_lamports":max(x for x,_ in measured),
    "total_scenario_loss_ceiling_lamports":sum(loss for _,loss in measured),
    "deploy_rent_lamports":deploy_rent, "account_rent_ceiling_lamports":account_rent,
    "network_and_admin_lamports":overhead, "budget_ceiling_lamports":upper,
    "funding_request_sol":(upper + sol - 1)//sol}, indent=2))
