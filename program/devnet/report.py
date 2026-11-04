"""Markdown tables from one run_deploy.sh output directory, against the VM baseline of the same ELF.

Usage: python3 devnet/report.py <out_dir> <svm_report.json> <cluster label>
Prints markdown. Every number comes from the JSON files; nothing is typed in.
"""
import json
import sys
from pathlib import Path

VM_NAME = {"initialize_config": "initialize_config", "create_room": "create_room", "open_door": "open_door",
           "buy_door0": "buy_door", "buy_door1": "buy_door", "sell_door0": "sell_door",
           "convert_door0_to_door1": "convert", "buy_room_token": "buy_room", "retire_pending": "retire_pending",
           "claim_door_fees": "claim_door_fees"}


def main():
    out, svm_path, label = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    vm = json.load(open(svm_path))["cu"]
    deploy = json.load(open(out / "deploy.json"))
    show = json.load(open(out / "program_show.json"))
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
         f"| deploy slot (`lastDeploySlot`) | {show['lastDeploySlot']:,} |",
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
    L += ["", "**Transactions, live CU against the VM measurement of the same ELF:**", "",
          "| step | signature | slot | live program CU | VM min–max CU (same ELF) | live − VM max |",
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
        L.append(f"| door {d['index']} backing vault vs circulating door supply | {d['room_token_backing_vault_balance']} vs {d['circulating_door_supply']} → {'equal' if d['backing_exactly_equals_circulating'] else ('covers' if d['backing_covers_circulating'] else '**SHORT**')} |")
    L += [f"| reserve vs curve integral of `sold` | {v['reserve']} vs {v['curve_integral_of_sold']} → {'covers' if v['reserve_covers_curve_integral'] else '**SHORT**'} |",
          f"| ReserveVault lamports − rent vs `reserve` | {int(v['reserve_vault_lamports']) - v['zero_data_rent']} vs {v['reserve']} → {'covers' if v['reserve_vault_covers_reserve'] else '**SHORT**'} |",
          f"| RoomVault vs unsold supply | {v['room_vault_balance']} vs U − {v['sold']} → {'covers' if v['room_vault_covers_unsold'] else '**SHORT**'} |",
          f"| fee counters vs 60/40 split of every Trade event's fee | expected {fs['expected_from_trade_events']}; on-chain {fs['on_chain_counters_before_retire_and_claim']} → {'match' if fs['match'] else '**MISMATCH**'} |",
          f"| retire_pending | pending {v['after_retire']['pending_reserve_sol']}, reserve +{v['after_retire']['reserve_increase']} |",
          f"| claim_door_fees (door 0) | accrued {v['after_claim']['door0_accrued_sol']}, claimed {v['after_claim']['door0_claimed_sol']} |"]
    print("\n".join(L))


if __name__ == "__main__":
    main()
