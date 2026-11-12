"""Devnet qualification: real signed create, floor door and name door, with replay verification.

Requires funded smoke wallets. It never deploys, changes Config or requests an
airdrop. Every send is journaled before submission. Any mismatch stops the run.
Signing material is read locally and never written to the public report.
"""
import argparse
import base64
import hashlib
import json
import logging
import secrets
import struct
import sys
import time
from pathlib import Path

SERVICE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SERVICE))
sys.path.insert(0, str(SERVICE / "scripts"))

from fastapi.testclient import TestClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import Transaction

from matcher_service import auth
from matcher_service.app import create_app
from matcher_service.chain import ChainState, RpcClient
from matcher_service.config import Budget, Config, DEFAULT_CU_LIMIT
from matcher_service.ops import Metrics, logger
from matcher_service.program_id import PROGRAM_ID
from matcher_service.service import Service
from matcher_service.signer import KeyfileSigner
from matcher_service.store import Store
from matcher_service.txbuild import Builder, T22, ata
import verify_decision

GENESIS = "EtWTRABZaYq6iMfeYKouRu166VU2xqa1wcaWoxPkrZBG"
PIN = "fc2d615e37c63710326e18a29d157b50b0ad678ef9083e3161007bf43e8e9002"
PROGRAM = "8tPd1ZUEGxrj5zYu8aeg95cU92nmKWKYKoSaKPqFuZAZ"


def write(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    for attempt in range(100):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 99:
                raise
            time.sleep(0.05)


def wait(rpc, signature):
    for _ in range(90):
        status = rpc.call("getSignatureStatuses", [[signature], {"searchTransactionHistory": True}])["value"][0]
        if status and status["confirmationStatus"] == "finalized":
            assert status["err"] is None, status["err"]
            return status
        time.sleep(1)
    raise RuntimeError("Resolve the saved signature before any replacement transaction")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rpc", required=True)
    parser.add_argument("--keys", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    report_path = args.out / "service-e2e.json"
    assert not report_path.exists(), "Inspect existing receipts before any rerun"
    assert PROGRAM_ID == PROGRAM
    rpc = RpcClient(args.rpc, timeout=30)
    assert rpc.call("getGenesisHash", []) == GENESIS
    loader = Pubkey.from_string("BPFLoaderUpgradeab1e11111111111111111111111")
    program_data = Pubkey.find_program_address([bytes(Pubkey.from_string(PROGRAM))], loader)[0]
    _, data, _ = rpc.account(program_data)
    assert int.from_bytes(data[4:12], "little") == 520996477
    assert hashlib.sha256(data[45:]).hexdigest() == PIN
    debug = logging.getLogger("matcher.rpc.internal")
    debug.setLevel(logging.DEBUG)
    debug.propagate = False
    debug.addHandler(logging.FileHandler(args.out / "service-rpc.internal.log", encoding="utf-8"))

    def key(role):
        return Keypair.from_json((args.keys / f"{role}.json").read_text(encoding="utf-8"))

    launcher, trader = key("smoke-launcher"), key("smoke-trader")
    db_path = args.out / "decisions.sqlite3"
    assert not db_path.exists()
    cfg = Config(env="development", rpc_url=args.rpc, program_id=PROGRAM, signer="keyfile",
                 keyfile=str(args.keys / "matcher-authority.json"), gcp_key_version=None,
                 aws_key_id=None, db_path=str(db_path), matcher_version=1,
                 budget=Budget(30, 60, 15, 1), cu_limit=DEFAULT_CU_LIMIT,
                 max_cu_price=1_000_000, rate_ip_per_min=1000,
                 rate_launcher_per_min=1000, trust_forwarded_for=False)
    store = Store(str(db_path))
    service = Service(cfg, rpc, ChainState(rpc, PROGRAM), KeyfileSigner(cfg.keyfile, cfg.env),
                      store, Builder(PROGRAM), logger(), Metrics())
    client = TestClient(create_app(service, start_refresher=False))
    report = {"program": PROGRAM, "elf_sha256": PIN, "status": "running", "error": None,
              "budget": vars(cfg.budget), "decisions": [], "transactions": []}
    write(report_path, report)
    tag = secrets.token_hex(6).upper()
    name, symbol = f"Qual {tag}", f"Q{tag[:5]}"
    room_id = None
    try:
        for label, who, sym, kind, rule in (
            ("signed_new_room", launcher, symbol, "new_room", None),
            ("signed_floor_door", trader, symbol, "door", "floor"),
            ("signed_name_door", launcher, "X" + symbol[1:], "door", "T2n"),
        ):
            service.chain.refresh()
            assert client.get("/health").json()["ready"]
            request = auth.sign(who, {"launcher": str(who.pubkey()), "name": name, "symbol": sym,
                                     "uri": "https://e.invalid/q", "first_buy_lamports": 100_000_000,
                                     "max_slippage_bps": 200, "cu_price_micro_lamports": 1})
            response = client.post("/route", json=request)
            assert response.status_code == 200, response.text
            out = response.json()
            decision = out["decision"]
            assert decision["kind"] == kind
            if rule is not None:
                assert decision["rule"] == rule and decision["room_id"] == room_id
            else:
                room_id = decision["room_id"]
            record = store.get(out["id"])["record"]
            quote = record["first_buy_quote"]
            assert quote and quote["tokens"] > 0 and quote["min_tokens_out"] > 0
            assert int(record["launch_max_reserve_lamports"]) > 0
            tx = Transaction.from_bytes(base64.b64decode(out["transaction_base64"]))
            signatures = list(tx.signatures)
            assert tx.message.account_keys[0] == who.pubkey()
            signatures[0] = who.sign_message(bytes(tx.message))
            signed = Transaction.populate(tx.message, signatures)
            signed.verify()
            signature = str(signed.signatures[0])
            row = {"name": label, "signature": signature, "state": "prepared",
                   "decision_id": out["id"], "room": decision["room"],
                   "room_id": decision["room_id"], "rule": decision["rule"]}
            report["transactions"].append(row)
            report["decisions"].append({"label": label, "request": request, "response": out,
                                        "record": record})
            write(report_path, report)
            actual = rpc.call("sendTransaction", [base64.b64encode(bytes(signed)).decode(),
                              {"encoding": "base64", "preflightCommitment": "confirmed", "maxRetries": 5}])
            assert actual == signature
            status = wait(rpc, signature)
            transaction = rpc.call("getTransaction", [signature, {"encoding": "json",
                                   "commitment": "finalized", "maxSupportedTransactionVersion": 0}])
            assert transaction and transaction["meta"]["err"] is None
            token = ata(who.pubkey(), Pubkey.from_string(decision["door_mint"]), T22)
            _, raw, _ = rpc.account(token)
            received = struct.unpack_from("<Q", raw, 64)[0]
            assert received == quote["tokens"], (received, quote["tokens"])
            row.update(state="finalized", slot=status["slot"], ok=True,
                       fee_lamports=transaction["meta"]["fee"],
                       transaction_cu=transaction["meta"]["computeUnitsConsumed"],
                       quoted_door_tokens=quote["tokens"], received_door_tokens=received,
                       decision=decision)
            assert row["transaction_cu"] <= DEFAULT_CU_LIMIT
            write(report_path, report)
            print(json.dumps({k: v for k, v in row.items() if k != "decision"}), flush=True)
        ok, detail = store.verify_chain()
        assert ok, detail
        report["store_hash_chain"] = detail
        # Reuse immutable rooted transactions across independent replays. Config
        # appears in every trade, so repeating its history otherwise repeats all
        # HTTP reads. Mutable account/snapshot reads are never cached.
        rooted_slot = rpc.call("getSlot", [{"commitment": "finalized"}])
        transaction_cache = {}
        original_rpc = verify_decision.RpcClient

        class RootedTransactionCache(original_rpc):
            def call(self, method, params):
                cache_key = json.dumps([self.url, params], sort_keys=True)
                if method == "getTransaction" and cache_key in transaction_cache:
                    return transaction_cache[cache_key]
                result = super().call(method, params)
                if method == "getTransaction" and result and result["slot"] <= rooted_slot:
                    transaction_cache[cache_key] = result
                return result

        verify_decision.RpcClient = RootedTransactionCache
        try:
            for decision in report["decisions"]:
                checks, landed = verify_decision.verify(decision["record"], args.rpc, chain_ok=ok)
                failed = [c for c in checks if not c["ok"] or c.get("inconclusive")]
                decision["verification"] = {"verdict": "AGREE" if not failed else "DISAGREE",
                                           "checks": checks, "landed": landed}
                write(report_path, report)
                assert not failed, failed
                assert landed and landed["ok"]
                print(f"{decision['label']}: independent verifier AGREE, slot {landed['slot']}", flush=True)
        finally:
            verify_decision.RpcClient = original_rpc
        report["rooted_transaction_cache"] = {"rooted_slot": rooted_slot,
                                               "transactions": len(transaction_cache)}
        report["status"] = "passed"
    except BaseException as exc:
        report.update(status="stopped", error=f"{type(exc).__name__}: {exc}")
        write(report_path, report)
        raise
    finally:
        store.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        store.db.close()
    write(report_path, report)
    print("paired matcher devnet end-to-end: PASS", flush=True)


if __name__ == "__main__":
    main()
