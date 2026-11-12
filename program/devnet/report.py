"""Markdown tables from one run_deploy.sh output directory, compared with the VM observations of the same ELF
(observed maxima from LiteSVM's Agave 4.3.2 at fixed addresses: not upper bounds).

Usage: python3 devnet/report.py <out_dir> <svm_report.json> <cluster label> [--check]
Prints markdown. Every number comes from the JSON files; nothing is typed in.
With --check it also asserts every end-to-end condition, prints PASS/FAIL per
check and exits 1 if any fails.
"""
import json
import sys
from pathlib import Path

VM_NAME = {"initialize_config": "initialize_config", "create_room": "create_room", "open_door": "open_door",
           "buy_door0": "buy_door", "buy_door1": "buy_door", "sell_door0": "sell_door",
           "swap_door0_to_door1": "swap_doors", "buy_room_token": "buy_room", "retire_pending": "retire_pending",
           "claim_door_fees": "claim_door_fees"}


def main():
    # Reports are UTF-8 artifacts, including when redirected on Windows where
    # the inherited legacy encoding cannot represent the mathematical symbols.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    out, svm_path, label = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    vm = json.load(open(svm_path))["cu"]
    deploy = json.load(open(out / "deploy.json"))
    show = json.load(open(out / "program_show.json"))
    upgrade = json.load(open(out / "upgrade.json")) if (out / "upgrade.json").exists() else None
    init = json.load(open(out / "init.json"))["transactions"]
    smoke = json.load(open(out / "smoke.json"))
    fails = json.load(open(out / "failures.json"))["cases"]
    config = json.load(open(out / "config.json"))
    elf = (out / "elf.sha256").read_text().split()[0]
    onchain = (out / "onchain.sha256").read_text().split()[0]
    L = [f"### {label}", "",
         "| item | value |", "|---|---|",
         f"| program ID | `{deploy['programId']}` |",
         f"| deploy signature | `{deploy['signature']}` |",
         *([f"| upgrade signature (`devnet/upgrade.sh`) | `{upgrade['signature']}` |"] if upgrade else []),
         f"| {'last upgrade' if upgrade else 'deploy'} slot (`lastDeploySlot`) | {show['lastDeploySlot']:,} |",
         f"| ProgramData account | `{show['programdataAddress']}` |",
         f"| upgrade authority | `{show['authority']}` |",
         f"| ProgramData lamports | {show['lamports']:,} |",
         f"| local ELF SHA-256 | `{elf}` |",
         f"| on-chain bytes SHA-256 (first ELF-length bytes of `solana program dump`) | `{onchain}` |",
         f"| on-chain bytes equal local ELF | {'yes' if elf == onchain else '**NO**'} |",
         f"| Config account | `{config['config']}` (read at slot {config['slot']:,}, {config['data_len']} bytes) |",
         f"| Config fields differing from settings | {config['mismatches']} of {len(config['fields'])} |", "",
         "**Config read back against the generated settings:**", "",
         "| field | on-chain | expected | match |", "|---|---|---|---|"]
    for f in config["fields"]:
        L.append(f"| `{f['field']}` | `{f['on_chain']}` | `{f['expected']}` | {'yes' if f['match'] else '**NO**'} |")
    L += ["", "**Transactions, live CU against the VM observations of the same ELF** (VM figures are observed "
          "values from LiteSVM's Agave 4.3.2 at fixed addresses, not upper bounds; a positive last column is "
          "expected, not a failure):", "",
          "| step | signature | slot | live program CU | VM observed min–max CU (same ELF) | live − VM observed max |",
          "|---|---|---|---|---|---|"]
    for t in init + smoke["transactions"]:
        n = t["name"]
        v = vm.get(VM_NAME.get(n, ""), None)
        cu = t.get("program_cu")
        vmr = f"{v['min']:,}–{v['max']:,} (n={v['count']:,})" if v else "not measured"
        diff = f"{cu - v['max']:+,}" if (v and cu is not None) else "—"
        L.append(f"| {n} | `{t['signature']}` | {t['slot']:,} | {cu if cu is None else f'{cu:,}'} | {vmr} | {diff} |")
    L += ["", "ATA rows are client setup (Associated Token program), not doors program CU.", "",
          "**Expected failures:**", "",
          "| case | landed on-chain | signature | slot | error |", "|---|---|---|---|---|"]
    for f in fails:
        if f.get("landed"):
            err = (f.get("error_log") or f.get("error") or "").replace("|", "\\|")
            L.append(f"| {f['name']} | yes | `{f['signature']}` | {f['slot']:,} | {f['error']}; `{err}` |")
        else:
            msg = json.loads(f["rpc_error"].split("sendTransaction: ", 1)[1])
            L.append(f"| {f['name']} | no: rejected before execution | — | — | `{msg['data']['err']}`: {msg['message']} |")
    v = smoke["verify"]
    fs = v["fee_split"]
    L += ["", "**On-chain state checks after the sequence:**", "",
          "| check | result |", "|---|---|",
          f"| room mint `{v['room_mint']['mint']}`: supply, mint/freeze/metadata authorities | {v['room_mint']['supply']}, {v['room_mint']['mint_authority']}, {v['room_mint']['freeze_authority']}, {v['room_mint']['metadata_update_authority']} → {'ok' if v['room_mint']['ok'] else '**FAIL**'} |"]
    for d in v["doors"]:
        m = d["mint"]
        L.append(f"| door {d['index']} mint `{m['mint']}`: supply, authorities | {m['supply']}, {m['mint_authority']}, {m['freeze_authority']}, {m['metadata_update_authority']} → {'ok' if m['ok'] else '**FAIL**'} |")
        L.append(f"| door {d['index']} backing vault vs curve integral | {d['room_token_backing_vault_balance']} vs {d['curve_integral']} → {'covers' if d['backing_covers_curve_integral'] else '**SHORT**'} |")
    L += [f"| reserve vs curve integral of `sold` | {v['reserve']} vs {v['curve_integral_of_sold']} → {'covers' if v['reserve_covers_curve_integral'] else '**SHORT**'} |",
          f"| ReserveVault lamports − rent vs `reserve` | {int(v['reserve_vault_lamports']) - v['zero_data_rent']} vs {v['reserve']} → {'covers' if v['reserve_vault_covers_reserve'] else '**SHORT**'} |",
          f"| RoomVault vs unsold supply | {v['room_vault_balance']} vs U − {v['sold']} → {'covers' if v['room_vault_covers_unsold'] else '**SHORT**'} |",
          f"| fee counters vs 60/40 split of every Trade event's fee | expected {fs['expected_from_trade_events']}; on-chain {fs['on_chain_counters_before_retire_and_claim']} → {'match' if fs['match'] else '**MISMATCH**'} |",
          f"| retire_pending | pending {v['after_retire']['pending_reserve_sol']}, reserve +{v['after_retire']['reserve_increase']} |",
          f"| claim_door_fees (door 0) | accrued {v['after_claim']['door0_accrued_sol']}, claimed {v['after_claim']['door0_claimed_sol']} |"]
    print("\n".join(L))
    if "--check" in sys.argv:
        sys.exit(check(out, deploy, show, init, smoke, fails, config, elf, onchain))


# Expected outcome of each failure case: (lands on-chain, error that must appear).
EXPECTED_FAILURES = {
    "create_room_without_matcher_signature": (True, '{"Custom":3010}'),      # AccountNotSigner
    "open_door_without_matcher_signature": (True, '{"Custom":3010}'),
    "create_room_signature_over_different_routing_data": (False, "SignatureFailure"),
    "open_door_signature_over_different_routing_data": (False, "SignatureFailure"),
    "sell_exceeding_balance": (True, '{"Custom":1}'),                        # Token-2022 InsufficientFunds
    "claim_door_fees_by_non_recipient": (True, '{"Custom":6006}'),          # doors Authority
}
SMOKE_STEPS = ["create_room", "open_door", "buy_door0", "buy_door1", "sell_door0", "swap_door0_to_door1",
               "buy_room_token", "retire_pending", "claim_door_fees"]


def check(out, deploy, show, init, smoke, fails, config, elf, onchain):
    v = smoke["verify"]
    fs = v["fee_split"]
    done = {t["name"]: t for t in smoke["transactions"]}
    results = [
        ("deployed bytes equal the pinned ELF", elf == onchain),
        ("program ID matches the deploy output", deploy["programId"] == smoke["program"] == show["programId"]
         == json.load(open(out / "upgrade.json" if (out / "upgrade.json").exists() else out / "deploy.json"))["programId"]),
        ("upgrade authority is set (not the deploy wallet)", show["authority"] not in ("", None, "none")),
        ("initialize_config succeeded", all(t["ok"] for t in init)),
        ("every Config field matches the settings", config["mismatches"] == 0),
        ("Config matcher_authority equals the smoke matcher",
         next(f["on_chain"] for f in config["fields"] if f["field"] == "matcher_authority") == smoke["matcher"]),
    ]
    for step in SMOKE_STEPS:
        t = done.get(step)
        results.append((f"smoke step {step} landed and succeeded with program CU recorded",
                        bool(t and t["ok"] and t["program_cu"])))
    if "name_lock" in v:   # runs of a program with the NameLock (H-1)
        results += [("NameLock holds the smoke room under the matcher's name key", v["name_lock"]["ok"])]
    results += [("room mint: 1B supply, no mint/freeze/metadata authority", v["room_mint"]["ok"])]
    for d in v["doors"]:
        results += [(f"door {d['index']} mint: 1B supply, no mint/freeze/metadata authority", d["mint"]["ok"]),
                    (f"door {d['index']} backing vault covers curve integral", d["backing_covers_curve_integral"])]
    results += [
        ("reserve covers the curve integral of sold", v["reserve_covers_curve_integral"]),
        ("ReserveVault lamports minus rent cover reserve", v["reserve_vault_covers_reserve"]),
        ("RoomVault covers unsold supply", v["room_vault_covers_unsold"]),
        ("fee counters equal the 60/40 split of every Trade fee", fs["match"]),
        ("FeeVault lamports minus rent cover all fee counters", fs["fee_vault_covers_counters"]),
        ("retire_pending moved all pending into reserve",
         v["after_retire"]["pending_reserve_sol"] == 0
         and int(v["after_retire"]["reserve_increase"]) == fs["on_chain_counters_before_retire_and_claim"]["pending_reserve"]),
        ("claim_door_fees paid door 0 exactly its accrued fees",
         v["after_claim"]["door0_accrued_sol"] == 0
         and v["after_claim"]["door0_claimed_sol"] == fs["on_chain_counters_before_retire_and_claim"]["door0"]),
    ]
    by_name = {f["name"]: f for f in fails}
    for name, (lands, needle) in EXPECTED_FAILURES.items():
        f = by_name.get(name)
        if f is None:
            results.append((f"failure case {name} ran", False))
            continue
        text = (f.get("error") or "") + (f.get("rpc_error") or "")
        ok = bool(f.get("landed")) == lands and needle in text
        if lands:
            ok = ok and f.get("ok") is False
        results.append((f"failure case {name} rejected with {needle}", ok))
    print()
    failed = 0
    for name, ok in results:
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    print(f"\n{len(results) - failed} of {len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    main()
