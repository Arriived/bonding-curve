"""How much of the live-versus-VM create_room CU gap is PDA bump search?

`find_program_address` tries bumps from 255 down, and every failed try costs one `create_program_address`
(1,500 CU in Agave's compute budget). A room's addresses depend on its random room id, so every launch
pays a different number of tries, while the VM figure comes from one fixed fixture room. This script
counts the tries for the PDAs `create_room` derives, for the VM fixture and for each recorded devnet run,
and compares (live tries - VM tries) * 1,500 with the measured gap (live program CU - VM observed CU).

Derivations counted (programs/doors_v1/src): Anchor `init` of Room and Door; `create_pda` for ReserveVault,
FeeVault, GradPayer, RoomMint, RoomVault, RetiredVault, FeeWsol, SlugLock, NameLock (when the program has
it), DoorMint, DoorVault, DoorRoomVault; `door_check`'s re-derivation of the Door; the first buy's
Token-2022 ATA (found by the ATA program). It is a model of the dominant term, not a full CU account.

Usage: python3 program/scripts/bump_drift.py   (needs solders; reads git history, no RPC)
"""
import hashlib
import json
import struct
import subprocess
from pathlib import Path

from solders.keypair import Keypair
from solders.pubkey import Pubkey

HERE = Path(__file__).resolve().parents[1]
PROGRAM = Pubkey.from_string("D7YsLsiJXoAF38vCUhFqYStepvSz6goG7EddHDe5NVJG")
ATA = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
T22 = Pubkey.from_string("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")
TRY_CU = 1500


def tries(seeds, program=PROGRAM):
    return 255 - Pubkey.find_program_address(seeds, program)[1] + 1


def fold(b: bytes) -> bytes:  # state.rs `fold`, ASCII path (every name here is ASCII)
    digits = {ord("0"): ord("O"), ord("1"): ord("I"), ord("3"): ord("E"), ord("4"): ord("A"),
              ord("5"): ord("S"), ord("7"): ord("T"), ord("8"): ord("B")}
    a, out, i = b.lower(), bytearray(), 0
    while i < len(a):
        c, step = (ord("m"), 2) if a[i:i + 2] == b"rn" else (ord("w"), 2) if a[i:i + 2] == b"vv" else (a[i], 1)
        c = digits.get(c, c - 32 if 97 <= c <= 122 else c)
        if c >= 128 or chr(c).isalnum():
            out.append(c)
        i += step
    return bytes(out)


def identity(name, symbol):
    return hashlib.sha256(fold(symbol.encode()) + b"\0" + fold(name.encode())).digest()


def count(rid, user, name, symbol, name_key):
    room = Pubkey.find_program_address([b"room", struct.pack("<Q", rid)], PROGRAM)[0]
    n0 = struct.pack("<Q", 0)
    door = Pubkey.find_program_address([b"door", bytes(room), n0], PROGRAM)[0]
    mint = Pubkey.find_program_address([b"door_mint", bytes(room), n0], PROGRAM)[0]
    seeds = [[b"room", struct.pack("<Q", rid)]] + [[s, bytes(room)] for s in (
        b"reserve", b"fees", b"grad_payer", b"room_mint", b"room_vault", b"retired", b"fee_wsol")]
    seeds += [[b"slug", identity(name, symbol)], [b"door", bytes(room), n0], [b"door", bytes(room), n0],
              [b"door_mint", bytes(room), n0], [b"door_vault", bytes(door)], [b"door_room_vault", bytes(door)]]
    if name_key is not None:
        seeds.append([b"name", name_key])
    return sum(tries(s) for s in seeds) + tries([bytes(user), bytes(T22), bytes(mint)], ATA)


def fixture_name_key(name):  # tests/svm.rs Fixture::name_key: identity with a symbol that folds to nothing
    return identity(name, "~")[:16]


def git_json(commit, path):
    return json.loads(subprocess.run(["git", "show", f"{commit}:program/{path}"], cwd=HERE, check=True,
                                     capture_output=True, text=True).stdout)


def smoke_name(rid):
    tag = f"{rid & 0xFFFFFF:06X}"
    return f"Doors Smoke {tag}", f"D{tag[:5]}"


def main():
    import os
    import sys
    # The matcher service's rules (for the NameLock key) live on claude/matcher-service; point MATCHER_SERVICE at a
    # checkout of services/matcher, or run this from that branch, where it is at ../services/matcher.
    sys.path.insert(0, os.environ.get("MATCHER_SERVICE", str(HERE.parent / "services/matcher")))
    vm_user = Keypair.from_seed(bytes([11] * 32)).pubkey()
    vm_rid = 0xd35a_e081_6ab4_9c27
    # (label, commit holding that run's evidence, devnet smoke naming, program has NameLock)
    runs = [("b6fe25d deploy", "c433617", "fixed", False), ("54215ae upgrade", "1de13c9", "tagged", False),
            ("71d32f3 upgrade", "WORKTREE", "tagged", True),
            ("71d32f3 localnet, bundled programs, default features", "WORKTREE:localnet", "tagged", True),
            ("71d32f3 localnet, devnet feature set", "WORKTREE:localnet-features", "tagged", True),
            ("71d32f3 localnet, devnet features + devnet token programs", "WORKTREE:localnet-cluster-programs",
             "tagged", True)]
    print("| devnet run | live CU | VM CU | measured gap | bump tries live / VM | predicted gap | residual |")
    print("|---|---|---|---|---|---|---|")
    for label, commit, naming, has_name in runs:
        if commit.startswith("WORKTREE"):
            where = commit.partition(":")[2] or "devnet"
            smoke = json.loads((HERE / f"verification/devnet/{where}/smoke.json").read_text())
            svm = json.loads((HERE / "verification/svm_report.json").read_text())
        else:
            smoke, svm = git_json(commit, "verification/devnet/devnet/smoke.json"), git_json(commit, "verification/svm_report.json")
        rid = int(smoke["verify"]["room_id"])
        name, symbol = ("Doors Devnet Smoke", "DOORS") if naming == "fixed" else smoke_name(rid)
        key = None
        if has_name:
            from matcher_service import rules
            key = rules.name_lock_key(name, symbol)
        live_cu = next(t["program_cu"] for t in smoke["transactions"] if t["name"] == "create_room")
        vm_cu = svm["cu"]["create_room"]["max"]
        live_t = count(rid, Pubkey.from_string(smoke["launcher"]), name, symbol, key)
        vm_t = count(vm_rid, vm_user, "First room", "MEME", fixture_name_key("First room") if has_name else None)
        pred = (live_t - vm_t) * TRY_CU
        gap = live_cu - vm_cu
        print(f"| {label} | {live_cu:,} | {vm_cu:,} | {gap:+,} | {live_t} / {vm_t} | {pred:+,} | {gap - pred:+,} |")


if __name__ == "__main__":
    main()
