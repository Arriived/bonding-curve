"""Render the measured paired-doors SBF evidence as Markdown."""
import argparse
import hashlib
import io
import json
import os
import re
from contextlib import redirect_stdout
from pathlib import Path

REFERENCE_PAYOUT = {(0, False): 8.10, (10, False): 7.33, (50, False): 6.15, (50, True): 3.12}
REFERENCE_MULTIPLES = {10: (2.39, 1.85, 1.00, 1.85), 50: (1.62, 1.43, 1.00, 1.43)}
DEFAULT = Path(__file__).resolve().parents[1] / "verification"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path, nargs="?", default=DEFAULT)
    parser.add_argument("--live", type=Path, help="JSON from the paired devnet runner")
    parser.add_argument("--before", type=Path, default=DEFAULT / "paired_doors_before_review.json")
    parser.add_argument("--report", type=Path, help="update the generated tables in the prototype report")
    args = parser.parse_args()

    def load(name):
        return json.loads((args.evidence / name).read_text(encoding="utf-8"))

    scenarios = load("paired_doors.json")
    limits = load("paired_limits.json")
    launch_trace = load("trace_budget.json")["rows"]
    spl = load("paired-spl.json")
    print("# Paired doors prototype measurements")
    print(f"\nPinned SPL bytes verified offline; original snapshot slot {spl['context_slot']:,}.")
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

    cu_table = render_cu_table(args.evidence, launch_trace, limits["trades"])
    print("\n## Compute and trace by fixture\n")
    print(cu_table)
    comparison = render_comparison(args.evidence, args.before, limits["rent"])
    print("\n## Creation before and after the review\n")
    print(comparison)

    heap_path = args.evidence / "heap_headroom.json"
    if heap_path.exists():
        heap = load(heap_path.name)
        print("\n## Heap headroom\n")
        print(f"Measured additional allocation in {heap['resolution_bytes']}-byte steps.")
        print("\n| Shape | Additional bytes that fit |")
        print("|---|---:|")
        for shape, size in heap["free_heap_at_end_bytes_at_least"].items():
            print(f"| {shape} | {size:,} |")

    if args.report:
        text = args.report.read_text(encoding="utf-8")
        status = render_status(args.evidence)
        for marker, block in (("CU", cu_table), ("CREATION", comparison), ("STATUS", status)):
            begin = f"<!-- BEGIN GENERATED {marker} -->"
            end = f"<!-- END GENERATED {marker} -->"
            head, tail = text.split(begin, 1)
            _, tail = tail.split(end, 1)
            text = head + begin + "\n" + block + "\n" + end + tail
        args.report.write_text(text, encoding="utf-8", newline="\n")

    if args.live:
        live = json.loads(args.live.read_text(encoding="utf-8"))
        print_live(live, scenarios, limits["trades"], launch_trace)


def render_status(directory):
    build = json.loads((directory / "build.json").read_text(encoding="utf-8"))
    spl = json.loads((directory / "paired-spl.json").read_text(encoding="utf-8"))
    property_run = json.loads((directory / "svm_report.json").read_text(encoding="utf-8"))
    log = (directory / "svm.log").read_text(encoding="utf-8")
    tests = re.search(r"test result: ok\. (\d+) passed; 0 failed", log)
    assert tests, "passing full SBF suite required"
    client_log = (directory / "devnet-client-tests.log").read_text(encoding="utf-8")
    assert "smoke_name_key_equals_the_service_vectors ... ok" in client_log
    assert re.search(r"test result: ok\. [1-9][0-9]* passed; 0 failed", client_log)
    elf = hashlib.sha256((directory.parent / "target/deploy/doors_v1.so").read_bytes()).hexdigest()
    run_id = os.environ.get("GITHUB_RUN_ID")
    source = f"Source commit `{build['git_commit']}`."
    if run_id:
        source += f" [Linux verification](https://github.com/Arriived/bonding-curve/actions/runs/{run_id})."
    return (source + f"\n\nThe SBF suite passed {tests[1]} tests, including "
            f"{property_run['property_iterations']:,} property iterations and "
            f"{property_run['executed_transactions']:,} executed transactions. "
            "The standalone devnet client tests also passed.\n\n"
            f"The deployed Token-2022, SPL Token and ATA binary hashes matched the pinned capture. "
            f"Their verification read was at finalized slot {spl['context_slot']:,}.\n\n"
            f"Compiled ELF SHA-256 is `{elf}`.")


def render_cu_table(directory, launches, trades):
    rows = []
    for row in launches:
        rows.append({"fixture": "launch_instruction_trace_budget", "shape": row["instruction"],
                     "prefunded": row["prefunded"], "priority": row["priority_fee_instruction"],
                     "program": row.get("program_cu"), "transaction": row["transaction_cu"],
                     "trace": row["logged_invocations"]})
    for row in trades:
        rows.append({"fixture": "paired_door_trade_limits_and_launch_rent", "shape": row["shape"],
                     "prefunded": row["prefunded"], "priority": row["priority_fee"],
                     "program": row.get("program_cu"), "transaction": row["transaction_cu"],
                     "trace": row["trace_entries"]})
    marker = "PAIRED_DOORS_TAKEOVER_LIMIT "
    for line in (directory / "svm.log").read_text(encoding="utf-8").splitlines():
        if marker in line:
            row = json.loads(line.split(marker, 1)[1])
            rows.append({"fixture": f"takeover_heap_case / {row['uri_bytes']}-byte URI", "shape": row["shape"],
                         "prefunded": row["prefunded"], "priority": row["priority_fee"],
                         "program": row["program_cu"], "transaction": row["transaction_cu"],
                         "trace": row["trace_entries"]})
    selected = {}
    for row in rows:
        key = row["fixture"], row["shape"]
        if key not in selected or row["transaction"] > selected[key]["transaction"]:
            selected[key] = row
    property_run = json.loads((directory / "svm_report.json").read_text(encoding="utf-8"))
    for shape in ("create_room", "open_door", "buy_door", "sell_door", "swap_doors",
                  "claim_door_swap_fees", "claim_protocol_swap_fees"):
        if cu := property_run["cu"].get(shape):
            selected["mixed_10000_sbf_operations_and_cu_report", shape] = {
                "fixture": "mixed_10000_sbf_operations_and_cu_report", "shape": shape,
                "prefunded": False, "priority": False, "program": cu["max"],
                "transaction": None, "trace": None,
            }
    output = io.StringIO()
    number = lambda value: "—" if value is None else f"{value:,}"
    with redirect_stdout(output):
        print("Each row is the maximum CU sample for that fixture and instruction. Program CU includes CPIs.")
        print("Transaction CU also includes the compute-budget instructions. Property-run samples record program CU.")
        print("\n| SBF fixture | Instruction | Prefunded | Priority fee | Program CU | Transaction CU | Trace entries |")
        print("|---|---|---|---|---:|---:|---:|")
        for key in sorted(selected):
            row = selected[key]
            print(f"| {row['fixture']} | {row['shape']} | {row['prefunded']} | {row['priority']} | "
                  f"{number(row['program'])} | {number(row['transaction'])} | {number(row['trace'])} |")
        print(f"\nMaximum measured transaction CU was {max(r['transaction'] for r in rows):,}.")
        programs = [r["program"] for r in selected.values() if r["program"] is not None]
        print(f"Maximum measured program CU was {max(programs):,}.")
    return output.getvalue().strip()


def render_comparison(directory, before_path, rent):
    before = json.loads(before_path.read_text(encoding="utf-8"))
    heap = json.loads((directory / "heap_headroom.json").read_text(encoding="utf-8"))
    prior = before["create_room"]
    actual = heap["worst_launch_cu"]["create_room"]
    rows = [
        ("Additional heap bytes", "heap_probe_worst_case_launches / create_room", prior["heap_bytes"],
         heap["free_heap_at_end_bytes_at_least"]["create_room"]),
        ("Program CU", "heap_probe_worst_case_launches / create_room, instrumented build", prior["probe_program_cu"], actual["program_cu"]),
        ("Transaction CU", "heap_probe_worst_case_launches / create_room, instrumented build", prior["probe_transaction_cu"], actual["tx_cu"]),
        ("Room creation including door 0 rent, lamports", "paired_door_trade_limits_and_launch_rent", prior["room_with_door_0_rent_lamports"], rent["room_with_door_0_lamports"]),
    ]
    output = io.StringIO()
    with redirect_stdout(output):
        print(f"Before is [{before['commit'][:7]}]({before['run_url']}). After is {heap['measured_commit'][:7]}.")
        print("The heap fixture uses maximum metadata and prefunded accounts. Rent uses the same rent-only metadata in both runs.")
        print("\n| Measurement | Fixture | Before | After | Change |")
        print("|---|---|---:|---:|---:|")
        for measurement, fixture, previous, current in rows:
            print(f"| {measurement} | {fixture} | {previous:,} | {current:,} | {current - previous:+,} |")
        print(f"\nAn additional door uses {rent['additional_door_lamports']:,} lamports of rent.")
        if vault_rent := rent.get("first_swap_vault_lamports"):
            print(f"The first swapping user pays {vault_rent:,} lamports for the room-token fee vault.")
    return output.getvalue().strip()


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
