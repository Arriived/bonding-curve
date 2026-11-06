"""Check the paired-door completion threshold against the unchanged room supply.

Run from the repository root with python program/scripts/check_paired_completion.py.
All amounts ending in _base are six-decimal token base units.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAMPORTS_PER_SOL = 10**9
DOOR_VIRTUAL_SOL = 30 * LAMPORTS_PER_SOL
DOOR_COMPLETION_SOL = 85 * LAMPORTS_PER_SOL


def main():
    room = json.loads(
        (ROOT / "research/doors_into_one_room/outputs/curve_quantities.json").read_text()
    )
    math_source = (ROOT / "program/programs/doors_v1/src/math.rs").read_text()
    supply = int(re.search(r"^pub const U: u64 = ([0-9_]+);", math_source, re.M)[1])
    vs, vt = room["v_sol_lamports"], room["v_tok_base"]
    k = vs * vt
    # The room inverse uses floor division and includes one lamport of rounding slack.
    curve_cap = vt - k // (vs + room["trigger"] + 1) - 1
    assert curve_cap == room["q_g"]
    rows = []
    for reserve_sol in (0, 10, 50):
        reserve = reserve_sol * LAMPORTS_PER_SOL
        sold = vt - k // (vs + reserve + 1) - 1 if reserve else 0
        # Invert the marginal price K / (V_tok - sold)^2. Rounding the quote
        # down gives the lower bound for an integer-rounded virtual quote.
        virtual_quote = DOOR_VIRTUAL_SOL * (vt - sold) ** 2 // k
        threshold = -(-DOOR_COMPLETION_SOL * virtual_quote // DOOR_VIRTUAL_SOL)
        rows.append({
            "room_reserve_sol": reserve_sol,
            "door_virtual_quote_base": virtual_quote,
            "door_completion_threshold_base": threshold,
            "exceeds_entire_mint": threshold > supply,
            "exceeds_curve_phase_circulation": threshold > curve_cap,
        })
    print(json.dumps({
        "room_virtual_sol_lamports": vs,
        "room_supply_base": supply,
        "room_curve_phase_cap_base": curve_cap,
        "doors": rows,
    }, indent=2))


if __name__ == "__main__":
    main()
