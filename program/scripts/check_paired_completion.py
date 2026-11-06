"""Check the rejected completion rule and the paired-door supply bound.

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
    # Match the room inverse, including its one-lamport rounding slack.
    def inverse(reserve):
        return vt - k // (vs + reserve + 1) - 1

    curve_cap = inverse(room["trigger"])
    assert curve_cap == room["q_g"]
    # Even granting a door the best default room price at birth and all
    # room tokens ever released at once, its token supply is not exhausted.
    min_quote = DOOR_VIRTUAL_SOL * (vt - curve_cap) ** 2 // k
    exhaust_quote = min_quote * supply // (vt - supply)
    max_door_sold = vt - min_quote * vt // (min_quote + curve_cap + 1) - 1
    assert exhaust_quote > curve_cap and max_door_sold < supply

    # This cap is legal under Settings::validate. It is a proposed test
    # fixture only. The source door can accumulate the room output first.
    stress_cap = 120 * LAMPORTS_PER_SOL
    stress_at = 100 * LAMPORTS_PER_SOL
    stress_sold = inverse(stress_at)
    stress_quote = DOOR_VIRTUAL_SOL * (vt - stress_sold) ** 2 // k
    stress_exhaust_quote = stress_quote * supply // (vt - supply)
    stress_swap_quote = stress_sold * 99 // 100
    assert 0 < stress_sold < inverse(stress_cap) <= supply
    assert stress_swap_quote > stress_exhaust_quote

    rows = []
    for reserve_sol in (0, 10, 50):
        reserve = reserve_sol * LAMPORTS_PER_SOL
        sold = inverse(reserve) if reserve else 0
        # Invert the marginal price K / (V_tok - sold)^2. Rounding the quote
        # down gives the lower bound for an integer-rounded virtual quote.
        virtual_quote = DOOR_VIRTUAL_SOL * (vt - sold) ** 2 // k
        threshold = (DOOR_COMPLETION_SOL * virtual_quote + DOOR_VIRTUAL_SOL - 1) // DOOR_VIRTUAL_SOL
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
        "default_minimum_virtual_quote_base": min_quote,
        "default_minimum_exhaustion_quote_base": exhaust_quote,
        "default_upper_bound_door_sold_base": max_door_sold,
        "stress_fixture": {
            "room_cap_lamports": stress_cap,
            "room_reserve_at_door_creation_lamports": stress_at,
            "available_room_tokens_after_swap_fee_base": stress_swap_quote,
            "door_exhaustion_quote_base": stress_exhaust_quote,
        },
        "doors": rows,
    }, indent=2))


if __name__ == "__main__":
    main()
