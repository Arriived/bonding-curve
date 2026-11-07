"""Render the measured paired-doors SBF evidence as Markdown."""
import argparse
import json
from pathlib import Path

REFERENCE_PAYOUT = {(0, False): 8.10, (10, False): 7.33, (50, False): 6.15, (50, True): 3.12}
REFERENCE_MULTIPLES = {10: (2.39, 1.85, 1.00, 1.85), 50: (1.62, 1.43, 1.00, 1.43)}
DEFAULT = Path(__file__).resolve().parents[1] / "verification"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path, nargs="?", default=DEFAULT)
    parser.add_argument("--live", type=Path, help="JSON from the paired devnet runner")
    args = parser.parse_args()

    def load(name):
        return json.loads((args.evidence / name).read_text(encoding="utf-8"))

    scenarios = load("paired_doors.json")
    limits = load("paired_limits.json")
    launch_trace = load("trace_budget.json")["rows"]
    spl = load("paired-spl.json")
    print("# Paired doors prototype measurements")
    print(f"\nDeployed SPL binary read verified at finalized slot {spl['context_slot']:,}.")
    print("The supplied single-curve vamp reference is 4.95 SOL.")
    print("\n| Room SOL | Dump | A out (SOL) | Reference | Difference | After buys | After A | Cash-out | Rotation |")
    print("|---:|---|---:|---:|---:|---:|---:|---:|---:|")
    for cash in (row for row in scenarios if not row["followers_rotate"]):
        case = cash["initial_room_sol"], cash["dump"]
        rotate = next(row for row in scenarios if row["followers_rotate"]
                      and (row["initial_room_sol"], row["dump"]) == case)
        assert cash["a_payout_lamports"] == rotate["a_payout_lamports"]
        prices = {step["step"]: step["room_price_multiple"] for step in cash["steps"] + rotate["steps"]}
        actual = cash["a_payout_lamports"] / 1e9
        ref = REFERENCE_PAYOUT.get(case)
        reference = f"{ref:.2f}" if ref is not None else "—"
        delta = f"{actual / ref - 1:+.2%}" if ref is not None else "—"
        steps = ("after_followers_buy", "after_a_exits", "after_followers_cash_out", "after_followers_rotate")
        values = " | ".join(f"{prices[step]:.6f}" for step in steps)
        print(f"| {case[0]} | {case[1]} | {actual:.9f} | {reference} | {delta} | {values} |")
        if case[0] in REFERENCE_MULTIPLES and not case[1]:
            reference_values = " | ".join(f"{x:.2f}" for x in REFERENCE_MULTIPLES[case[0]])
            print(f"| {case[0]} reference | — | — | — | — | {reference_values} |")

    print("\n## FDV by door index and scenario step\n")
    print("| Room SOL | Dump | Rotate | Step | FDV by door index (SOL) |")
    print("|---:|---|---|---|---|")
    for row in scenarios:
        prefix = f"| {row['initial_room_sol']} | {row['dump']} | {row['followers_rotate']} |"
        print(f"{prefix} Source at launch | 2 = {row['source_door_launch_fdv_sol']:.6f} |")
        for step in row["steps"]:
            fdv = ", ".join(f"{d['index']} = {d['fdv_sol']:.6f}" for d in step["doors"])
            print(f"{prefix} {step['step']} | {fdv} |")

    print("\n## Additional slippage over the single-curve quote\n")
    print("| Room SOL | Dump | Rotate | Buy extra bps | Sell extra bps | First swap extra bps |")
    print("|---:|---|---|---:|---:|---:|")
    for row in scenarios:
        swap = row["first_rotation_swap_slippage"]
        swap_text = f"{swap['extra_bps']:.3f}" if swap else "—"
        print(f"| {row['initial_room_sol']} | {row['dump']} | {row['followers_rotate']} | "
              f"{row['buy_slippage']['extra_bps']:.3f} | {row['sell_slippage']['extra_bps']:.3f} | {swap_text} |")

    print("\n## Instruction limits\n")
    print("| Shape | First buy | Prefunded | Priority fee | Trace entries | Transaction CU |")
    print("|---|---|---|---|---:|---:|")
    for row in launch_trace:
        print(f"| {row['instruction']} | {row['first_buy']} | {row['prefunded']} | {row['priority_fee_instruction']} | "
              f"{row['logged_invocations']} | {row['transaction_cu']} |")
    for row in limits["trades"]:
        print(f"| {row['shape']} | — | {row['prefunded']} | {row['priority_fee']} | "
              f"{row['trace_entries']} | {row['transaction_cu']} |")
    rent = limits["rent"]
    print(f"\nFor the measured metadata, a room with door 0 used {rent['room_with_door_0_lamports']:,} "
          f"lamports of rent. An additional door used {rent['additional_door_lamports']:,} lamports.")

    heap_path = args.evidence / "heap_headroom.json"
    if heap_path.exists():
        heap = load(heap_path.name)
        print("\n## Heap headroom\n")
        print(f"Measured additional allocation in {heap['resolution_bytes']}-byte steps.")
        print("\n| Shape | Additional bytes that fit |")
        print("|---|---:|")
        for shape, size in heap["free_heap_at_end_bytes_at_least"].items():
            print(f"| {shape} | {size:,} |")

    if args.live:
        live = json.loads(args.live.read_text(encoding="utf-8"))
        print_live(live, scenarios, limits["trades"], launch_trace)


def print_live(live, scenarios, trades, launch_trace):
    print("\n## Devnet comparison\n")
    if live["error"]:
        print(f"Run stopped with `{live['error']}`.")
    print("| Room SOL | Dump | Rotate | VM A out (SOL) | Live A out (SOL) | Live sale slot |")
    print("|---:|---|---|---:|---:|---:|")
    vm_cases = {(row["initial_room_sol"], row["dump"], row["followers_rotate"]): row for row in scenarios}
    for row in live["cases"]:
        case = row["initial_room_sol"], row["dump"], row["followers_rotate"]
        vm = vm_cases[case]["a_payout_lamports"] / 1e9
        actual = row["a_payout_lamports"] / 1e9
        print(f"| {case[0]} | {case[1]} | {case[2]} | {vm:.9f} | {actual:.9f} | {row['a_exit']['slot']:,} |")
    print("\n| Instruction | VM ordinary priority CU range | Live priority CU range | Peak live slot | Trace at peak CU |")
    print("|---|---:|---:|---:|---:|")
    for shape in ("create_room", "open_door", "buy_door", "sell_door", "swap_doors"):
        vm = [r["transaction_cu"] for r in launch_trace
              if r["instruction"] == shape and r["priority_fee_instruction"] and not r["prefunded"]]
        vm += [r["transaction_cu"] for r in trades
               if r["shape"] == shape and r["priority_fee"] and not r["prefunded"]]
        rows = [r for r in live["transactions"] if r["name"] == shape and r["ok"]]
        if not rows:
            continue
        peak = max(rows, key=lambda r: r["transaction_cu"])
        live_min = min(r["transaction_cu"] for r in rows)
        print(f"| {shape} | {min(vm):,} to {max(vm):,} | {live_min:,} to {peak['transaction_cu']:,} | "
              f"{peak['slot']:,} | {peak['trace_entries']} |")
    if balance := live["payer_balance"]:
        print(f"\nDeploy wallet balance was {balance['value']:,} lamports at finalized "
              f"slot {balance['context']['slot']:,}.")


if __name__ == "__main__":
    main()
