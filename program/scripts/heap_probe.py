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

Run from anywhere: python3 program/scripts/heap_probe.py [commit]   (default HEAD; a non-HEAD
commit writes verification/heap_headroom.<short>.json instead, for before/after comparisons)
"""
import json, os, re, shutil, subprocess, sys, tempfile
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
fn heap_probe_try(f: &mut Fixture, ix: Instruction) -> Result<(), String> {
    f.svm.expire_blockhash(); // a fresh blockhash per attempt, so retries are distinct transactions
    let tx = Transaction::new(
        &vec![&f.user, &f.matcher],
        Message::new(
            &[ComputeBudgetInstruction::set_compute_unit_limit(1_400_000), ix],
            Some(&f.user.pubkey()),
        ),
        f.svm.latest_blockhash(),
    );
    match f.svm.send_transaction(tx) {
        Ok(_) => Ok(()),
        Err(e) => {
            let oom = e.meta.logs.iter().any(|l| l.contains("out of memory"));
            if oom { Err("oom".into()) } else { panic!("non-heap failure: {:#?}", e.meta.logs) }
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
    assert!(ok(1), "worst case fails even without the probe allocation");
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
    // create_room takeover (second Room deserialised for old_holder) at the largest metadata
    // the matcher service signs in a legacy transaction: name 32, symbol 10, URI 70.
    let takeover = heap_probe_search(|units| {
        let mut f = heap_probe_fixture();
        let mut held = heap_probe_launch("Taken", 18, 0, 1);
        held.uri = "u".repeat(70);
        f.create(held, None);
        let old = f.room;
        f.time(3600);
        f.rid = 0x7d21_93be_04f5_c6a8;
        f.room = p(&[b"room", &f.rid.to_le_bytes()]);
        f.doors.clear();
        let mut l = heap_probe_launch("Taken", 18, 1_010_000_000, units);
        l.uri = "u".repeat(70);
        let ix = f.create_ix(l, Some(old));
        heap_probe_prefund(&mut f, &ix);
        heap_probe_try(&mut f, ix).is_ok()
    });
    println!("HEAP_PROBE {{\"create_room\":{create},\"open_door\":{open},\"create_room_takeover_uri70\":{takeover}}}");
}
'''


def run(cmd, cwd, **kw):
    r = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, **kw)
    if r.returncode:
        tail = "\n".join((r.stdout + r.stderr).splitlines()[-60:])
        raise SystemExit(f"{' '.join(map(str, cmd))} failed ({r.returncode}):\n{tail}")
    return r


def main():
    head = run(["git", "rev-parse", "HEAD"], REPO).stdout.strip()
    commit = run(["git", "rev-parse", sys.argv[1] if len(sys.argv) > 1 else "HEAD"], REPO).stdout.strip()
    tmp = Path(tempfile.mkdtemp(prefix="heap-probe-"))
    wt = tmp / "wt"
    run(["git", "worktree", "add", "--detach", str(wt), commit], REPO)
    try:
        lib = wt / "program/programs/doors_v1/src/lib.rs"
        s = lib.read_text()
        for nxt in ("    pub fn open_door(", "    pub fn buy("):
            i = s.index(nxt)
            j = s.rindex("        Ok(())\n    }\n", 0, i)
            s = s[:j] + PROBE + s[j:]
        lib.write_text(s)
        tests = wt / "program/programs/doors_v1/tests/svm.rs"
        tests.write_text(tests.read_text() + TEST)
        prog = wt / "program"
        env = dict(os.environ)
        run(["rustup", "override", "set", "1.99.0-x86_64-unknown-linux-gnu"], prog)
        run([str(Path.home() / ".cargo/bin/cargo-build-sbf"), "--tools-version", "v1.58"], prog, env=env)
        out = run(["cargo", "test", "--locked", "--test", "svm", "heap_probe_worst_case_launches", "--",
                   "--nocapture"], prog, env=env).stdout
        units = json.loads(re.search(r"HEAP_PROBE (\{.*\})", out)[1])
        result = {
            "measured_commit": commit,
            "measured_tree": "clean checkout of measured_commit in a temporary worktree",
            "heap_bytes": 32 * 1024,
            "method": "largest extra allocation appended at the end of the instruction that still succeeds, "
                      f"binary-searched in {STEP}-byte steps; worst case = maximum metadata, all writable "
                      "launch accounts prefunded, non-zero flat fees, atomic first buy settling a pending backlog; "
                      "create_room_takeover_uri70 adds an old_holder takeover at the largest metadata the "
                      "matcher signs in a legacy transaction (name 32, symbol 10, URI 70)",
            "free_heap_at_end_bytes_at_least": {k: v * STEP for k, v in units.items()},
            "resolution_bytes": STEP,
        }
        name = "heap_headroom.json" if commit == head else f"heap_headroom.{commit[:7]}.json"
        (HERE / "verification" / name).write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
    finally:
        run(["rustup", "override", "unset"], wt / "program")
        run(["git", "worktree", "remove", "--force", str(wt)], REPO)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
