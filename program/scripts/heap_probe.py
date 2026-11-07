"""Measure free SBF heap at the end of the heaviest launch paths.

The SBF bump allocator never frees, so heap use is monotonic within an instruction and the
free heap at the end of `create_room` / `open_door` is the instruction's whole margin.

Method (no change to the committed program):
  1. check out HEAD into a temporary git worktree;
  2. in that copy only, append `vec![0u8; launch.matcher_version as usize * 16]` at the end of
     `create_room` and `open_door` (matcher_version is a signed u16 the probe controls);
  3. build the SBF ELF there and binary-search the largest allocation that still succeeds in
     the worst case: maximum metadata on both mints, every writable launch account prefunded,
     non-zero flat fees, and an atomic first buy that settles a pending backlog;
  4. write program/verification/heap_headroom.json, then remove the worktree.

Run from anywhere: python3 program/scripts/heap_probe.py [commit] [--heap-frame BYTES]
(default HEAD; a non-HEAD commit writes verification/heap_headroom.<short>.json instead, for
before/after comparisons). --heap-frame adds ComputeBudgetInstruction::request_heap_frame(BYTES)
to every probe transaction and writes heap_headroom[.<short>].frame<BYTES>.json; the result also
records the whole-transaction and program CU of one worst-case create_room, to price the request.
--patch FILE applies a source patch to the checkout first (an A/B variant, e.g.
verification/ab/*.patch) and writes heap_headroom.ab_<patch stem>.json, recording the patch's sha256.
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]          # program/
REPO = HERE.parent
STEP = 16                                            # bytes per matcher_version unit

PROBE = """
    {
        // HEAP PROBE (temporary worktree only): allocate matcher_version * 16 bytes last.
        let probe = vec![0u8; launch.matcher_version as usize * 16];
        core::hint::black_box(&probe);
    }
"""

TEST = r'''
const HEAP_FRAME: u32 = __HEAP_FRAME__;
fn heap_probe_try(f: &mut Fixture, ix: Instruction) -> Result<(u64, u64), String> {
    f.svm.expire_blockhash(); // a fresh blockhash per attempt, so retries are distinct transactions
    let mut ixs = vec![ComputeBudgetInstruction::set_compute_unit_limit(1_400_000)];
    if HEAP_FRAME > 0 {
        ixs.push(ComputeBudgetInstruction::request_heap_frame(HEAP_FRAME));
    }
    let mut signers = vec![&f.user];
    if ix.accounts.iter().any(|account| account.is_signer && account.pubkey == f.matcher.pubkey()) {
        signers.push(&f.matcher);
    }
    ixs.push(ix);
    let tx = Transaction::new(
        &signers,
        Message::new(&ixs, Some(&f.user.pubkey())),
        f.svm.latest_blockhash(),
    );
    let prefix = format!("Program {ID} consumed ");
    match f.svm.send_transaction(tx) {
        Ok(m) => Ok((
            m.compute_units_consumed,
            m.logs
                .iter()
                .find_map(|l| l.strip_prefix(&prefix).and_then(|s| s.split_whitespace().next()))
                .and_then(|n| n.parse().ok())
                .unwrap_or(0),
        )),
        Err(e) => {
            let oom = e.meta.logs.iter().any(|l| l.contains("out of memory"));
            let trace = format!("{:?}", e.err).contains("MaxInstructionTraceLengthExceeded")
                || e.meta.logs.iter().any(|l| l.contains("Max instruction trace length exceeded"));
            if oom { Err("oom".into()) } else if trace { Err("trace".into()) }
            else { panic!("non-heap failure: {:#?}", e.meta.logs) }
        }
    }
}
fn heap_probe_launch(name: &str, fee: u64, buy: u64, units: u16) -> Launch {
    let mut l = launch(&format!("{name}{}", "x".repeat(32 - name.len())));
    l.symbol = "Y".repeat(10);
    l.uri = "u".repeat(200);
    l.max_fee_lamports = fee;
    l.first_buy_lamports = buy;
    l.matcher_version = units;
    l
}
fn heap_probe_fixture() -> Fixture {
    let mut f = Fixture::empty(0);
    let mut settings = defaults(f.matcher.pubkey(), f.user.pubkey());
    settings.room_fee_lamports = 7;
    settings.door_fee_lamports = 11;
    f.send(
        instr(
            a::UpdateConfig { admin: f.user.pubkey(), config: f.cfg },
            ix::UpdateConfig { settings, new_admin: f.user.pubkey() },
        ),
        false,
        "update_config",
    );
    f
}
fn heap_probe_prefund(f: &mut Fixture, ix: &Instruction) {
    let rent = f.svm.minimum_balance_for_rent_exemption(0);
    for account in &ix.accounts {
        if account.is_writable && f.svm.get_account(&account.pubkey).is_none() {
            f.svm.airdrop(&account.pubkey, rent).unwrap();
        }
    }
}
fn heap_probe_search(mut ok: impl FnMut(u16) -> bool) -> u16 {
    if !ok(1) {
        return 0; // fails even without the probe allocation
    }
    let (mut lo, mut hi) = (1u16, 4096u16); // 4096 * 16 = 64 KiB > the 32 KiB heap
    assert!(!ok(hi));
    while hi - lo > 1 {
        let mid = lo + (hi - lo) / 2;
        if ok(mid) { lo = mid } else { hi = mid }
    }
    lo
}
#[test]
fn heap_probe_worst_case_launches() {
    let create = heap_probe_search(|units| {
        let mut f = heap_probe_fixture();
        let ix = f.create_ix(heap_probe_launch("Prefunded max room", 18, 1_010_000_000, units), None);
        heap_probe_prefund(&mut f, &ix);
        heap_probe_try(&mut f, ix).is_ok()
    });
    let mut f = heap_probe_fixture();
    let mut room = launch("Probe room");
    room.max_fee_lamports = 18;
    f.create(room, None);
    f.trade(None, true, 1_010_000);
    assert!(f.r().pending_reserve_sol > 0);
    let mut prefunded = false;
    let open = heap_probe_search(|units| {
        let ix = f.open_ix(heap_probe_launch("Prefunded max door", 11, 101_000_000, units), None);
        if !prefunded { heap_probe_prefund(&mut f, &ix); prefunded = true; }
        heap_probe_try(&mut f, ix).is_ok()
    });
    // create_room takeover of a dead room's identity (old_holder) at a given URI length: 70 is the
    // largest the matcher service signs in a legacy transaction (name 32, symbol 10), 200 the
    // program's maximum, reachable in a v0 transaction (finding M-7).
    let takeover_at = |uri: usize| heap_probe_search(|units| {
        let mut f = heap_probe_fixture();
        let mut held = heap_probe_launch("Taken", 18, 0, 1);
        held.uri = "u".repeat(uri);
        f.create(held, None);
        let old = f.room;
        f.time(3600);
        f.rid = 0x7d21_93be_04f5_c6a8;
        f.room = p(&[b"room", &f.rid.to_le_bytes()]);
        f.doors.clear();
        let mut l = heap_probe_launch("Taken", 18, 1_010_000_000, units);
        l.uri = "u".repeat(uri);
        let ix = f.create_ix(l, Some(old));
        heap_probe_prefund(&mut f, &ix);
        heap_probe_try(&mut f, ix).is_ok()
    });
    let takeover = takeover_at(70);
    let takeover_200 = takeover_at(200);
    let takeover_max = u16::from(takeover_200 > 0);
    // open_door into a live room with an identity held by a dead room (old_holder), maximum metadata.
    let open_takeover = {
        let mut f = heap_probe_fixture();
        f.create(heap_probe_launch("Door identity", 18, 0, 1), None);
        let dead = f.room;
        f.time(3600);
        f.rid = 0x51c3_0aa7_9e44_1d02;
        f.room = p(&[b"room", &f.rid.to_le_bytes()]);
        f.doors.clear();
        let mut room = launch("Probe room");
        room.max_fee_lamports = 18;
        f.create(room, None);
        f.trade(None, true, 1_010_000);
        let mut prefunded = false;
        heap_probe_search(|units| {
            let ix = f.open_ix(heap_probe_launch("Door identity", 11, 101_000_000, units), Some(dead));
            if !prefunded { heap_probe_prefund(&mut f, &ix); prefunded = true; }
            heap_probe_try(&mut f, ix).is_ok()
        })
    };
    // CU of one worst-case create_room and open_door (no probe allocation), to price the heap
    // request; a launch that cannot run at all records its failure reason instead.
    let cu_of = |r: Result<(u64, u64), String>| match r {
        Ok((tx, program)) => format!("{{\"tx_cu\":{tx},\"program_cu\":{program}}}"),
        Err(why) => format!("{{\"failed\":\"{why}\"}}"),
    };
    let create_cu = {
        let mut f = heap_probe_fixture();
        let ix = f.create_ix(heap_probe_launch("Prefunded max room", 18, 1_010_000_000, 1), None);
        heap_probe_prefund(&mut f, &ix);
        cu_of(heap_probe_try(&mut f, ix))
    };
    let open_cu = {
        let mut f = heap_probe_fixture();
        let mut room = launch("Probe room");
        room.max_fee_lamports = 18;
        f.create(room, None);
        f.trade(None, true, 1_010_000);
        let ix = f.open_ix(heap_probe_launch("Prefunded max door", 11, 101_000_000, 1), None);
        heap_probe_prefund(&mut f, &ix);
        cu_of(heap_probe_try(&mut f, ix))
    };
    println!("HEAP_PROBE {{\"create_room\":{create},\"open_door\":{open},\"create_room_takeover_uri70\":{takeover},\"create_room_takeover_uri200\":{takeover_200},\"open_door_takeover\":{open_takeover},\"create_room_takeover_uri200_passes\":{takeover_max}}}");
    println!("HEAP_CU {{\"create_room\":{create_cu},\"open_door\":{open_cu}}}");
}
'''

PAIRED_TEST = r"""
#[test]
fn heap_probe_paired_door_trades() {
    let mut results = BTreeMap::new();
    for shape in ["buy_door", "sell_door", "swap_doors", "swap_doors_prefunded", "swap_doors_existing",
                  "claim_door_swap_fees", "claim_protocol_swap_fees"] {
        let units = heap_probe_search(|units| {
            let mut f = heap_probe_fixture();
            let mut room = launch("Paired heap room");
            room.max_fee_lamports = 18;
            f.create(room, None);
            let mut open = launch("Paired heap second door");
            open.max_fee_lamports = 11;
            f.open(open);
            f.trade(Some(0), true, 1_010_000_000);
            f.trade(None, true, 1_010_000_000); // settled by the next door buy
            if shape == "swap_doors_prefunded" {
                let vault = p(&[b"swap_fees", f.room.as_ref()]);
                f.svm.airdrop(&vault, f.svm.minimum_balance_for_rent_exemption(0)).unwrap();
            }
            if shape == "swap_doors_existing" || shape.starts_with("claim_") {
                f.swap(0, 1, f.balance(f.doors[0].user) / 4);
            }
            let mut ix = match shape {
                "buy_door" => f.trade_ix(Some(1), true, 1_010_000_000, 0),
                "sell_door" => f.trade_ix(Some(0), false, f.balance(f.doors[0].user) / 2, 0),
                "claim_door_swap_fees" => f.claim_swap_ix(Some(1)),
                "claim_protocol_swap_fees" => f.claim_swap_ix(None),
                _ => f.swap_ix(0, 1, f.balance(f.doors[0].user) / 2),
            };
            if shape.starts_with("claim_") {
                let mut clock = f.svm.get_sysvar::<Clock>();
                clock.slot = (units as u64) << 48;
                f.svm.set_sysvar(&clock);
            } else {
                let end = ix.data.len();
                ix.data[end - 8..].copy_from_slice(&((units as u64) << 48).to_le_bytes());
            }
            heap_probe_try(&mut f, ix).is_ok()
        });
        results.insert(shape, units);
    }
    println!("HEAP_PAIRED {}", serde_json::to_string(&results).unwrap());
}
"""


def instrument_paired(source):
    allocation = """
        let probe = vec![0u8; units * 16];
        core::hint::black_box(&probe);
"""
    for name, minimum, trade in (
        ("buy_door", "min_door_tokens_out", "trade(ctx, true, lamports_in, min_door_tokens_out)"),
        ("sell_door", "min_lamports_out", "trade(ctx, false, door_tokens_in, min_lamports_out)"),
    ):
        begin = source.index(f"    pub fn {name}(")
        end = source.index("\n    pub fn ", begin + 1)
        code = source[begin:end]
        assert trade in code
        code = code.replace(trade, f"""let units = ({minimum} >> 48) as usize;
        let {minimum} = {minimum} & ((1 << 48) - 1);
        {trade}?;""" + allocation + "        Ok(())")
        source = source[:begin] + code + source[end:]
    begin = source.index("    pub fn swap_doors(")
    end = source.index("\n    pub fn retire_pending(", begin)
    code = source[begin:end]
    code = code.replace("        let a = ctx.accounts;", """        let units = (min_out >> 48) as usize;
        let min_out = min_out & ((1 << 48) - 1);
        let a = ctx.accounts;""", 1)
    index = code.rindex("        Ok(())")
    source = source[:begin] + code[:index] + allocation + code[index:] + source[end:]
    for claim in ("true", "false"):
        original = f"claim_swap_fees(ctx, {claim})"
        assert source.count(original) == 1
        source = source.replace(original, original + "?;\n"
            + "        let units = (Clock::get()?.slot >> 48) as usize;\n"
            + allocation + "        Ok(())")
    return source


def run(cmd, cwd, **kw):
    r = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, **kw)
    if r.returncode:
        tail = "\n".join((r.stdout + r.stderr).splitlines()[-60:])
        raise SystemExit(f"{' '.join(map(str, cmd))} failed ({r.returncode}):\n{tail}")
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("commit", nargs="?", default="HEAD")
    ap.add_argument("--heap-frame", type=int, default=0)
    ap.add_argument("--patch", type=Path, default=None)
    args = ap.parse_args()
    patch = args.patch.resolve() if args.patch else None
    head = run(["git", "rev-parse", "HEAD"], REPO).stdout.strip()
    commit = run(["git", "rev-parse", args.commit], REPO).stdout.strip()
    tmp = Path(tempfile.mkdtemp(prefix="heap-probe-"))
    wt = tmp / "wt"
    run(["git", "worktree", "add", "--detach", str(wt), commit], REPO)
    try:
        if patch:
            run(["git", "apply", str(patch)], wt)
        lib = wt / "program/programs/doors_v1/src/lib.rs"
        s = lib.read_text()
        for nxt in ("    pub fn open_door(", "    pub fn buy("):
            i = s.index(nxt)
            j = s.rindex("        Ok(())\n    }\n", 0, i)
            s = s[:j] + PROBE + s[j:]
        paired = "    pub fn swap_doors(" in s
        if paired:
            s = instrument_paired(s)
        lib.write_text(s)
        tests = wt / "program/programs/doors_v1/tests/svm.rs"
        tests.write_text(tests.read_text() + TEST.replace("__HEAP_FRAME__", str(args.heap_frame))
                         + (PAIRED_TEST if paired else ""))
        prog = wt / "program"
        env = dict(os.environ)
        run(["rustup", "override", "set", "1.99.0-x86_64-unknown-linux-gnu"], prog)
        run([str(Path.home() / ".cargo/bin/cargo-build-sbf"), "--tools-version", "v1.58"], prog, env=env)
        out = run(["cargo", "test", "--locked", "--test", "svm", "heap_probe_worst_case_launches", "--",
                   "--nocapture"], prog, env=env).stdout
        units = json.loads(re.search(r"HEAP_PROBE (\{.*\})", out)[1])
        if paired:
            paired_out = run(["cargo", "test", "--locked", "--test", "svm",
                              "heap_probe_paired_door_trades", "--", "--nocapture"], prog, env=env).stdout
            units.update(json.loads(re.search(r"HEAP_PAIRED (\{.*\})", paired_out)[1]))
        cu = json.loads(re.search(r"HEAP_CU (\{.*\})", out)[1])
        full_takeover = bool(units.pop("create_room_takeover_uri200_passes"))
        result = {
            "measured_commit": commit,
            "measured_tree": "clean checkout of measured_commit in a temporary worktree"
                             + (" with variant_patch applied" if patch else ""),
            **({"variant_patch": str(patch.relative_to(REPO)),
                "variant_patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest()} if patch else {}),
            "heap_frame_requested_bytes": args.heap_frame or None,
            "allocator_heap_bytes": 32 * 1024,
            "method": "largest extra allocation appended at the end of the instruction that still succeeds, "
                      f"binary-searched in {STEP}-byte steps; worst case = maximum metadata, all writable "
                      "launch accounts prefunded, non-zero flat fees, atomic first buy settling a pending backlog; "
                      "create_room_takeover_uri70 uses an old_holder takeover with name 32, symbol 10 "
                      "and URI 70; create_room_takeover_uri200 uses the program's maximum URI; "
                      "transaction packet size is measured separately; open_door_takeover opens a maximum-metadata door "
                      "whose identity a dead room holds",
            "free_heap_at_end_bytes_at_least": {k: v * STEP for k, v in units.items()},
            "resolution_bytes": STEP,
            "create_room_takeover_uri200_passes": full_takeover,
            "worst_launch_cu": cu,
            "zero_means": "the launch fails even with no probe allocation (out of memory, or the 64-entry "
                          "instruction trace exceeded: see worst_launch_cu)",
        }
        name = "heap_headroom" + (f".ab_{patch.stem}" if patch else "" if commit == head else f".{commit[:7]}") + \
            (f".frame{args.heap_frame}" if args.heap_frame else "") + ".json"
        (HERE / "verification" / name).write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
        if paired and commit == head and not patch:
            assert all(v > 0 for v in units.values()), 'every trade and claim must fit the default heap'
            assert units["create_room"] * STEP >= 1500, (
                f"maximum-metadata create_room heap headroom is {units['create_room'] * STEP} bytes; "
                "paired doors require at least 1500"
            )
    finally:
        run(["rustup", "override", "unset"], wt / "program")
        run(["git", "worktree", "remove", "--force", str(wt)], REPO)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
