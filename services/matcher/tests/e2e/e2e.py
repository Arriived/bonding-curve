"""End-to-end test of the matcher service against the deployed doors program.

Target: the single line in tests/e2e/target.
  localnet - starts solana-test-validator with the pinned deploy ELF as an upgradeable program owned by
             the real upgrade-authority key, initialises Config with the real matcher key, then tests.
  devnet   - tests against the deployed devnet program. PENDING until it is deployed there
             (program/docs/DEPLOYMENT.md section 5): exits 3 with a PENDING message, never skips.

Usage: python3 tests/e2e/e2e.py <keys_dir>   (keys_dir as in program/docs/DEPLOYMENT.md section 2)

Sequence (every step asserts; any failure exits 1):
  1. request a decision for a new identity -> new_room; the launcher signs; the program accepts it
  2. same identity from another wallet -> door via the floor; accepted; door index 1, random door nonce
  3. same name, different symbol -> door via T2n; accepted
  3b. a door launch with a first buy and the default 2% price limit fills exactly the quoted tokens
      when nothing moves, and is rejected on-chain (Slippage) when a 1 SOL buy lands first
  4. tampered decisions are rejected: instruction data changed after the matcher signed
     (SignatureFailure), and the matcher signature stripped (AccountNotSigner, landed on-chain)
  5. replaying an accepted decision is rejected (single use)
  6. a decision submitted after its blockhash expired is rejected (localnet only: about a minute)
  7. GET /decision/{id} returns each record; the store's hash chain verifies
  8. scripts/verify_decision.py independently recomputes every accepted decision and agrees
"""
import base64
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVICE = HERE.parent.parent
REPO = SERVICE.parent.parent
sys.path.insert(0, str(SERVICE))

from fastapi.testclient import TestClient  # noqa: E402
from solders.instruction import AccountMeta, Instruction  # noqa: E402
from solders.keypair import Keypair  # noqa: E402
from solders.message import Message  # noqa: E402
from solders.pubkey import Pubkey  # noqa: E402
from solders.signature import Signature  # noqa: E402
from solders.transaction import Transaction  # noqa: E402

from matcher_service.app import create_app  # noqa: E402
from matcher_service.chain import ChainState, RpcClient, RpcError, pda  # noqa: E402
from matcher_service.config import Budget, Config  # noqa: E402
from matcher_service.ops import Metrics, logger  # noqa: E402
from matcher_service.service import Service  # noqa: E402
from matcher_service.signer import KeyfileSigner  # noqa: E402
from matcher_service.store import Store  # noqa: E402
from matcher_service.txbuild import Builder, load_idl  # noqa: E402

PROGRAM = "D7YsLsiJXoAF38vCUhFqYStepvSz6goG7EddHDe5NVJG"
PINNED = (REPO / "program/devnet/DEPLOY_ELF.sha256").read_text().split()[0]
URLS = {"localnet": "http://127.0.0.1:8899", "devnet": "https://api.devnet.solana.com"}


def kp(keys, name):
    return Keypair.from_bytes(bytes(json.loads((Path(keys) / f"{name}.json").read_text())))


def step(msg):
    print(f"== {msg}", flush=True)


def fail(msg):
    print(f"FAIL: {msg}", flush=True)
    sys.exit(1)


def settings_bytes(s):
    pk = lambda k: bytes(Pubkey.from_string(s[k]))  # noqa: E731
    u = lambda k: struct.pack("<Q", int(s[k]))      # noqa: E731
    return (pk("protocol_fee_recipient") + struct.pack("<HH", s["fee_bps"], s["door_share_bps"])
            + u("door_fee_lamports") + u("room_fee_lamports") + u("convert_fee_lamports") + u("v_sol_lamports")
            + u("v_tok") + u("supply") + u("r_star_lamports") + pk("meteora_dynamic_config")
            + u("graduation_trigger_lamports") + bytes([1 if s["paused"] else 0]) + pk("matcher_authority")
            + u("live_min_reserve_lamports") + u("live_max_idle_seconds") + u("live_new_seconds")
            + u("live_min_volume_lamports") + u("pool_min_window_lp_fee") + struct.pack("<H", s["founder_share_bps"]))


def send(rpc, tx, skip_preflight=False):
    wire = base64.b64encode(bytes(tx)).decode()
    return rpc.call("sendTransaction", [wire, {"encoding": "base64", "skipPreflight": skip_preflight,
                                                "preflightCommitment": "confirmed"}])


def confirm(rpc, sig, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = rpc.call("getSignatureStatuses", [[sig], {"searchTransactionHistory": True}])["value"][0]
        if st and st.get("confirmationStatus") in ("confirmed", "finalized"):
            return st
        time.sleep(0.5)
    fail(f"no confirmation for {sig}")


def sign_as_launcher(tx_b64, launcher):
    tx = Transaction.from_bytes(base64.b64decode(tx_b64))
    sigs = list(tx.signatures)
    sigs[0] = launcher.sign_message(bytes(tx.message))
    return Transaction.populate(tx.message, sigs)


def init_config(rpc, keys):
    upgrade, matcher, wallet = kp(keys, "upgrade-authority"), kp(keys, "matcher-authority"), kp(keys, "deploy-wallet")
    out = subprocess.run([sys.executable, str(REPO / "program/scripts/default_config.py"), "--matcher",
                          str(matcher.pubkey()), "--recipient", str(wallet.pubkey())],
                         capture_output=True, text=True, check=True).stdout
    s = json.loads(out)
    ix_spec = next(i for i in load_idl()["instructions"] if i["name"] == "initialize_config")
    program = Pubkey.from_string(PROGRAM)
    loader = Pubkey.from_string("BPFLoaderUpgradeab1e11111111111111111111111")
    metas = [AccountMeta(upgrade.pubkey(), True, True), AccountMeta(pda([b"config"], PROGRAM), False, True),
             AccountMeta(program, False, False),
             AccountMeta(Pubkey.find_program_address([bytes(program)], loader)[0], False, False),
             AccountMeta(Pubkey.from_string("11111111111111111111111111111111"), False, False)]
    ix = Instruction(program, bytes(ix_spec["discriminator"]) + settings_bytes(s), metas)
    bh = rpc.latest_blockhash()[0]
    from solders.hash import Hash
    msg = Message.new_with_blockhash([ix], upgrade.pubkey(), Hash.from_string(bh))
    tx = Transaction([upgrade], msg, Hash.from_string(bh))
    confirm(rpc, send(rpc, tx))
    return s


def start_localnet(keys):
    elf = os.environ.get("DOORS_DEPLOY_ELF", "/home/user/pv1-436c002/program/target/deploy/doors_v1.so")
    if hashlib.sha256(Path(elf).read_bytes()).hexdigest() != PINNED:
        fail(f"{elf} is not the pinned deploy ELF {PINNED}")
    ledger = tempfile.mkdtemp()
    upgrade = kp(keys, "upgrade-authority").pubkey()
    proc = subprocess.Popen(["solana-test-validator", "--ledger", ledger, "--reset", "--quiet", "--rpc-port", "8899",
                             "--upgradeable-program", PROGRAM, elf, str(upgrade)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rpc = RpcClient(URLS["localnet"])
    for _ in range(120):
        try:
            if rpc.slot() > 2:
                break
        except RpcError:
            pass
        time.sleep(1)
    for name in ("upgrade-authority", "smoke-launcher", "smoke-trader", "deploy-wallet"):
        confirm(rpc, rpc.call("requestAirdrop", [str(kp(keys, name).pubkey()), 20 * 10**9]))
    return proc, ledger, rpc


def main():
    keys = sys.argv[1]
    target = (HERE / "target").read_text().strip()
    if target not in URLS:
        fail(f"tests/e2e/target must be localnet or devnet, not {target!r}")
    proc = ledger = None
    if target == "localnet":
        proc, ledger, rpc = start_localnet(keys)
        step("Config initialised with the matcher key")
        init_config(rpc, keys)
    else:
        rpc = RpcClient(URLS["devnet"])
        info = rpc.call("getAccountInfo", [PROGRAM, {"encoding": "base64"}])["value"]
        cfg = rpc.call("getAccountInfo", [str(pda([b"config"], PROGRAM)), {"encoding": "base64"}])["value"]
        if info is None or cfg is None:
            print(f"PENDING: {PROGRAM} is not deployed and initialised on devnet yet "
                  "(program/docs/DEPLOYMENT.md section 5). Deploy it, then rerun.", flush=True)
            sys.exit(3)
    try:
        run(rpc, keys, target)
    finally:
        if proc:
            proc.terminate()
            proc.wait()
            shutil.rmtree(ledger, ignore_errors=True)


def run(rpc, keys, target):
    launcher, trader = kp(keys, "smoke-launcher"), kp(keys, "smoke-trader")
    db = tempfile.mkdtemp() + "/decisions.sqlite3"
    cfg = Config(env="development", rpc_url=URLS[target], program_id=PROGRAM, signer="keyfile",
                 keyfile=str(Path(keys) / "matcher-authority.json"), gcp_key_version=None, aws_key_id=None,
                 db_path=db, matcher_version=1, budget=Budget(30, 60, 15, 1), cu_limit=400_000,
                 max_cu_price=1_000_000, rate_ip_per_min=1000, rate_launcher_per_min=1000, trust_forwarded_for=False)
    svc = Service(cfg, rpc, ChainState(rpc, PROGRAM), KeyfileSigner(cfg.keyfile, cfg.env), Store(db),
                  Builder(PROGRAM), logger(), Metrics())
    svc.chain.refresh()
    client = TestClient(create_app(svc, start_refresher=False))
    h = client.get("/health").json()
    if not h.get("ready"):
        fail(f"service not ready: {h}")
    tag = os.urandom(3).hex().upper()
    name, symbol = f"E2E Room {tag}", f"E{tag[:4]}"
    accepted = []

    from matcher_service import auth

    issued = [0]

    def route(who, nm, sym, **extra):
        svc.chain.refresh()
        # Every /route request is signed by the launcher's key (matcher_service/auth.py, M-3). A signed
        # request is single use, so a new request identical to an earlier one advances issued_at.
        issued[0] = max(int(time.time()), issued[0] + 1)
        body = auth.sign(who, {"launcher": str(who.pubkey()), "name": nm, "symbol": sym,
                               "uri": "https://example.invalid/e2e.json", "issued_at": issued[0], **extra})
        r = client.post("/route", json=body)
        if r.status_code != 200:
            fail(f"/route {nm}/{sym}: {r.status_code} {r.text}")
        return r.json()

    def land(out, who, label):
        tx = sign_as_launcher(out["transaction_base64"], who)
        sig = send(rpc, tx)
        st = confirm(rpc, sig)
        if st.get("err"):
            fail(f"{label}: program rejected an untampered decision: {st['err']}")
        print(f"   {label}: {out['decision']['kind']} rule {out['decision']['rule']} room {out['decision']['room_id']} "
              f"door nonce {out['decision']['door_nonce']} -> landed {sig} slot {st['slot']}", flush=True)
        accepted.append(out["id"])
        return tx, sig

    step("1. new identity -> new room, accepted by the program")
    a = route(launcher, name, symbol)
    if a["decision"]["kind"] != "new_room":
        fail(f"expected new_room, got {a['decision']}")
    tx_a, _ = land(a, launcher, "new room")
    room_id = a["decision"]["room_id"]

    step("2. same identity from another wallet -> door via the floor")
    b = route(trader, name, symbol)
    if (b["decision"]["kind"], b["decision"]["rule"], b["decision"]["room_id"]) != ("door", "floor", room_id) \
            or int(b["decision"]["door_nonce"]) == 0:
        fail(f"expected a floor door with a non-zero nonce into {room_id}, got {b['decision']}")
    land(b, trader, "floor door")

    step("2b. a buy through door 0, so later verification replays a Trade (reserve, buckets, last trade)")
    from solders.hash import Hash
    from matcher_service.txbuild import T22, SYSTEM, ata
    bld = svc.builder
    rid = int(room_id)
    room_pk, core = bld.room_accounts(rid)
    d0 = bld.door_accounts(room_pk, 0)
    user_token = ata(launcher.pubkey(), d0["door_mint"], T22)
    create_ata = Instruction(Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"), bytes([1]), [
        AccountMeta(launcher.pubkey(), True, True), AccountMeta(user_token, False, True),
        AccountMeta(launcher.pubkey(), False, False), AccountMeta(d0["door_mint"], False, False),
        AccountMeta(SYSTEM, False, False), AccountMeta(T22, False, False)])
    buy = bld._instruction("buy", {"user": launcher.pubkey(), "core.config": bld.p(b"config"), "core.room": room_pk,
                                   **{"core." + k: v for k, v in core.items()}, **d0, "user_token": user_token},
                           struct.pack("<QQ", 50_000_000, 0))
    bh = rpc.latest_blockhash()[0]
    btx = Transaction([launcher], Message.new_with_blockhash([create_ata, buy], launcher.pubkey(), Hash.from_string(bh)),
                      Hash.from_string(bh))
    st = confirm(rpc, send(rpc, btx))
    if st.get("err"):
        fail(f"buy failed: {st['err']}")
    print(f"   bought 0.05 SOL through door 0 at slot {st['slot']}", flush=True)

    step("3. same name, different symbol -> door via T2n")
    c = route(launcher, name, "Z" + symbol[1:])
    if (c["decision"]["kind"], c["decision"]["rule"], c["decision"]["room_id"]) != ("door", "T2n", room_id):
        fail(f"expected T2n door into {room_id}, got {c['decision']}")
    land(c, launcher, "T2n door")

    step("3b. door first buy with the default 2% limit: exact fill when unmoved, Slippage when front-run")
    def door0_buy(lamports):
        bh_ = rpc.latest_blockhash()[0]
        ix_ = bld._instruction("buy", {"user": launcher.pubkey(), "core.config": bld.p(b"config"),
                                       "core.room": room_pk, **{"core." + k: v for k, v in core.items()},
                                       **d0, "user_token": user_token}, struct.pack("<QQ", lamports, 0))
        st_ = confirm(rpc, send(rpc, Transaction([launcher], Message.new_with_blockhash(
            [ix_], launcher.pubkey(), Hash.from_string(bh_)), Hash.from_string(bh_))))
        if st_.get("err"):
            fail(f"door 0 buy failed: {st_['err']}")
        return st_["slot"]

    def first_buy_record(out):
        rec_ = client.get(f"/decision/{out['id']}").json()["record"]
        q_ = rec_["first_buy_quote"]
        if not q_ or q_["max_slippage_bps"] != 200 or q_["min_tokens_out"] != q_["tokens"] * 9800 // 10000:
            fail(f"expected a default 2% first-buy limit, got {q_}")
        return q_

    e = route(trader, name, symbol, first_buy_lamports=100_000_000)
    q = first_buy_record(e)
    land(e, trader, "door with first buy")
    held = ata(trader.pubkey(), Pubkey.from_string(e["decision"]["door_mint"]), T22)
    got = struct.unpack_from("<Q", rpc.account(held)[1], 64)[0]
    if got != q["tokens"]:
        fail(f"first buy filled {got} base units, the quote said {q['tokens']}")
    print(f"   unmoved: filled exactly the quoted {got:,} base units (limit {q['min_tokens_out']:,})", flush=True)
    f_ = route(trader, name, symbol, first_buy_lamports=100_000_000)
    q = first_buy_record(f_)
    # A 1 SOL buy lands before the signed launch. Check, from the moved state, that the same first buy
    # would now get fewer tokens than the signed limit, i.e. the price moved further than 2%.
    moved = door0_buy(1_000_000_000)
    from matcher_service import quote as qmod
    svc.chain.refresh()
    after = qmod.first_buy_tokens(svc.chain.current().rooms[int(room_id)], 100_000_000)
    if after is None or after >= q["min_tokens_out"]:
        fail(f"front-run did not move the price past the 2% limit: {after} vs limit {q['min_tokens_out']}")
    ftx = sign_as_launcher(f_["transaction_base64"], trader)
    sig = send(rpc, ftx, skip_preflight=True)
    st = confirm(rpc, sig)
    logs = rpc.call("getTransaction", [sig, {"encoding": "json", "commitment": "confirmed",
                                              "maxSupportedTransactionVersion": 0}])["meta"]["logMessages"]
    if not st.get("err") or not any("Error Code: Slippage" in l for l in logs):
        fail(f"front-run first buy: expected Error Code: Slippage, got {st.get('err')}")
    print(f"   front-run by a 1 SOL buy at slot {moved} (quote now {after:,} < limit {q['min_tokens_out']:,}): "
          f"rejected on-chain with Slippage ({sig})", flush=True)

    step("4a. tampered decision (Launch.rule changed after the matcher signed) is rejected")
    d = route(trader, name, symbol)
    tx = Transaction.from_bytes(base64.b64decode(d["transaction_base64"]))
    m = tx.message
    ixs = list(m.instructions)
    launch_ix = ixs[-1]
    data = bytearray(bytes(launch_ix.data))
    data[-13] ^= 0x01  # Launch.rule (u8) sits before face (u32) and max_fee (u64)
    from solders.instruction import CompiledInstruction
    ixs[-1] = CompiledInstruction(launch_ix.program_id_index, bytes(data), bytes(launch_ix.accounts))
    forged = Message.new_with_compiled_instructions(m.header.num_required_signatures,
                                                    m.header.num_readonly_signed_accounts,
                                                    m.header.num_readonly_unsigned_accounts,
                                                    list(m.account_keys), m.recent_blockhash, ixs)
    sigs = list(tx.signatures)
    sigs[0] = trader.sign_message(bytes(forged))
    try:
        send(rpc, Transaction.populate(forged, sigs))
        fail("tampered decision was accepted by the RPC")
    except RpcError as e:
        if "SignatureFailure" not in str(e) and "signature verification" not in str(e):
            fail(f"tampered decision failed for the wrong reason: {e}")
        print("   rejected: matcher signature does not verify over the changed message", flush=True)

    step("4b. decision with the matcher signature stripped is rejected by the program")
    m = tx.message
    keys_ = list(m.account_keys)
    h = m.header
    n_sig, ro_sig, ro_unsig = h.num_required_signatures, h.num_readonly_signed_accounts, h.num_readonly_unsigned_accounts
    def writable(i):
        return i < n_sig - ro_sig or n_sig <= i < len(keys_) - ro_unsig
    from solders.hash import Hash
    # Same instructions, but only the launcher signs: the matcher is demoted to a non-signer account.
    rebuilt = [Instruction(keys_[ix.program_id_index], bytes(ix.data),
                           [AccountMeta(keys_[i], keys_[i] == trader.pubkey(), writable(i)) for i in bytes(ix.accounts)])
               for ix in m.instructions]
    bh = rpc.latest_blockhash()[0]
    stx = Transaction([trader], Message.new_with_blockhash(rebuilt, trader.pubkey(), Hash.from_string(bh)),
                      Hash.from_string(bh))
    sig = send(rpc, stx, skip_preflight=True)
    st = confirm(rpc, sig)
    if not st.get("err") or "3010" not in json.dumps(st["err"]):
        fail(f"stripped matcher signature: expected AccountNotSigner (3010), got {st.get('err')}")
    print(f"   rejected on-chain: {st['err']} ({sig})", flush=True)

    step("5. replaying an accepted decision is rejected")
    try:
        send(rpc, tx_a)
        fail("replay of the first decision was accepted")
    except RpcError as e:
        if "AlreadyProcessed" not in str(e) and "already been processed" not in str(e):
            fail(f"replay failed for an unexpected reason: {e}")
        print("   rejected: AlreadyProcessed", flush=True)

    if target == "localnet":
        step("6. a decision used after its blockhash expired is rejected")
        e = route(trader, name, symbol)
        lvbh = e["last_valid_block_height"]
        while rpc.block_height() <= lvbh:
            time.sleep(1)
        try:
            send(rpc, sign_as_launcher(e["transaction_base64"], trader))
            fail("expired decision was accepted")
        except RpcError as err:
            if "BlockhashNotFound" not in str(err) and "Blockhash not found" not in str(err):
                fail(f"expired decision failed for an unexpected reason: {err}")
            print(f"   rejected after block height {lvbh}: BlockhashNotFound", flush=True)

    step("6b. a matcher-signed launch past its expires_at_slot is rejected on-chain, blockhash still valid")
    from solders.hash import Hash
    from matcher_service.txbuild import MAX_LAUNCH_WINDOW_SLOTS, build_message, encode_launch
    from matcher_service import rules as _rules
    matcher_kp = kp(keys, "matcher-authority")
    snap = svc.chain.refresh()
    terms = bytes.fromhex(snap.config["launch_terms_hash"])
    ident = _rules.program_identity(name, symbol)

    def signed_open(expires, nonce_door, message_fn):
        data = encode_launch(name, symbol, "https://example.invalid/e2e.json", 0, 0, 1, 1, 0, 0, terms,
                             nonce_door, expires)
        ix, _, _ = svc.builder.open_door_ix(trader.pubkey(), matcher_kp.pubkey(), int(room_id), nonce_door, ident,
                                            None, data)
        return message_fn(ix)

    slot = rpc.slot()
    bh = rpc.latest_blockhash()[0]
    msg = signed_open(slot - 1, int.from_bytes(os.urandom(8), "little") | 1,
                      lambda ix: build_message(ix, trader.pubkey(), bh, 400_000, 0))
    etx = Transaction([trader, matcher_kp], msg, Hash.from_string(bh))
    sig = send(rpc, etx, skip_preflight=True)
    st = confirm(rpc, sig)
    logs = rpc.call("getTransaction", [sig, {"encoding": "json", "commitment": "confirmed",
                                              "maxSupportedTransactionVersion": 0}])["meta"]["logMessages"]
    if not st.get("err") or not any("Error Code: Expired" in l for l in logs):
        fail(f"expired launch: expected Error Code: Expired, got {st.get('err')}")
    print(f"   rejected on-chain: Expired ({sig})", flush=True)

    step("6c. a durable-nonce launch (no blockhash expiry) held past expires_at_slot is rejected on-chain")
    from solders import system_program as sp
    nonce_kp = Keypair()
    rent = rpc.call("getMinimumBalanceForRentExemption", [80])
    bh = rpc.latest_blockhash()[0]
    create = sp.create_nonce_account(trader.pubkey(), nonce_kp.pubkey(), trader.pubkey(), rent)
    ntx = Transaction([trader, nonce_kp], Message.new_with_blockhash(list(create), trader.pubkey(),
                                                                    Hash.from_string(bh)), Hash.from_string(bh))
    confirm(rpc, send(rpc, ntx))
    raw = base64.b64decode(rpc.call("getAccountInfo", [str(nonce_kp.pubkey()), {"encoding": "base64",
                                                                                "commitment": "confirmed"}])["value"]["data"][0])
    durable = Hash(raw[40:72])
    advance = sp.advance_nonce_account(sp.AdvanceNonceAccountParams(nonce_pubkey=nonce_kp.pubkey(),
                                                                    authorized_pubkey=trader.pubkey()))
    slot = rpc.slot()
    expires = slot + 20
    msg = signed_open(expires, int.from_bytes(os.urandom(8), "little") | 1,
                      lambda ix: Message.new_with_blockhash([advance, ix], trader.pubkey(), durable))
    held = Transaction([trader, matcher_kp], msg, durable)
    while rpc.slot() <= expires:
        time.sleep(0.5)
    sig = send(rpc, held, skip_preflight=True)
    st = confirm(rpc, sig)
    logs = rpc.call("getTransaction", [sig, {"encoding": "json", "commitment": "confirmed",
                                              "maxSupportedTransactionVersion": 0}])["meta"]["logMessages"]
    if not st.get("err") or not any("Error Code: Expired" in l for l in logs):
        fail(f"held durable-nonce launch: expected Error Code: Expired, got {st.get('err')}")
    print(f"   rejected on-chain after slot {expires}: Expired ({sig}); the durable nonce kept the transaction "
          "itself valid, the program's expiry did not", flush=True)

    step("7. decision records and the store's hash chain")
    for i in accepted:
        r = client.get(f"/decision/{i}")
        if r.status_code != 200 or r.json()["record"]["id"] != i:
            fail(f"/decision/{i}: {r.status_code}")
    ok, detail = svc.store.verify_chain()
    if not ok:
        fail(f"hash chain: {detail}")
    print(f"   {detail}", flush=True)

    step("8. independent recomputation of every accepted decision")
    for i in accepted:
        p = subprocess.run([sys.executable, str(SERVICE / "scripts/verify_decision.py"), i, "--rpc", URLS[target],
                            "--db", db], capture_output=True, text=True)
        last = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else ""
        if p.returncode != 0:
            print(p.stdout, p.stderr)
            fail(f"verify_decision {i}: exit {p.returncode}")
        print(f"   {i[:16]}...: {last}", flush=True)
    step("9. the verifier detects doctored records")
    sys.path.insert(0, str(SERVICE / "scripts"))
    import copy
    import verify_decision
    base = svc.store.get(accepted[-1])["record"]
    doctored = []
    r1 = copy.deepcopy(base)
    r1["state"]["rooms"][0]["reserve"] += 1                     # misreported room state
    r2 = copy.deepcopy(base)
    r2["decision"]["rule"] = "T3"                               # misreported rule
    r3 = copy.deepcopy(base)
    r3["request"]["name"] = r3["request"]["name"] + "X"         # request differs from the signed message
    for label, rec in (("room state", r1), ("rule", r2), ("request", r3)):
        checks, _ = verify_decision.verify(rec, URLS[target])
        bad = [c["check"] for c in checks if not c["ok"]]
        if not bad:
            fail(f"verifier accepted a record with a doctored {label}")
        print(f"   doctored {label}: DISAGREE ({bad[0]})", flush=True)
    print(f"e2e {target}: PASS", flush=True)


if __name__ == "__main__":
    main()
