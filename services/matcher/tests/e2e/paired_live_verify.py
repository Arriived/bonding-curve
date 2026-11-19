"""Independent verifier worker: database + devnet RPC only, no service or signer.

Input is one JSON decision_id per line, followed by {"stop": true}. Each reply
contains the unmodified independent verifier's checks and landed transaction.
Only finalized immutable transaction responses are reused between decisions.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

SERVICE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SERVICE))
sys.path.insert(0, str(SERVICE / "scripts"))
import verify_decision as vd
from matcher_service.store import Store


def write(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    for attempt in range(100):
        try:
            tmp.replace(path)
            return
        except PermissionError:
            if attempt == 99:
                raise
            time.sleep(0.05)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument("--rpc", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    destination = args.out / "independent-verifier.json"
    assert not destination.exists(), "Inspect the previous verifier result before any rerun"
    preflight = json.loads((args.out / "preflight.json").read_text())
    assert hashlib.sha256((SERVICE / "scripts/verify_decision.py").read_bytes()).hexdigest() == preflight["verifier_sha256"]
    vd.rules.check_unicode()
    original = vd.RpcClient
    rpc = original(args.rpc, timeout=30)
    assert rpc.call("getGenesisHash", []) == "EtWTRABZaYq6iMfeYKouRu166VU2xqa1wcaWoxPkrZBG"
    root = rpc.call("getSlot", [{"commitment": "finalized"}])
    store = Store(str(args.db))
    report = {"status": "running", "pid": os.getpid(), "parent_pid": os.getppid(),
              "rooted_slot": root, "verifier_sha256": preflight["verifier_sha256"],
              "rpc_transactions_fetched": 0, "decisions": [], "error": None,
              "service_and_signer_modules_loaded": False}
    cache = {}

    class RootedRpc(original):
        def call(self, method, params):
            key = json.dumps([self.url, params], sort_keys=True)
            if method == "getTransaction" and key in cache:
                return cache[key]
            result = super().call(method, params)
            if method == "getTransaction":
                report["rpc_transactions_fetched"] += 1
                if result and result["slot"] <= root:
                    cache[key] = result
                if report["rpc_transactions_fetched"] % 25 == 0:
                    write(destination, report)
            return result

    vd.RpcClient = RootedRpc
    write(destination, report)
    print(json.dumps({"ready": True, "pid": os.getpid()}), flush=True)
    try:
        for line in sys.stdin:
            request = json.loads(line)
            if request.get("stop"):
                assert len(report["decisions"]) == 3
                assert all(x["verdict"] == "AGREE" for x in report["decisions"])
                report["status"] = "passed"
                break
            decision_id = request["decision_id"]
            ok, detail = store.verify_chain()
            assert ok, detail
            assert store.db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 3
            row = store.get(decision_id)
            assert row and row["record"]["program"] == preflight["program"]
            report["active_decision"] = decision_id
            write(destination, report)
            checks, landed = vd.verify(row["record"], args.rpc, chain_ok=ok)
            failed = [c for c in checks if not c["ok"] or c.get("inconclusive")]
            verdict = "AGREE" if not failed and landed and landed["ok"] else "DISAGREE"
            assert "matcher_service.service" not in sys.modules
            assert "matcher_service.signer" not in sys.modules
            item = {"decision_id": decision_id, "verdict": verdict,
                    "checks": checks, "landed": landed, "store_hash_chain": detail}
            report["decisions"].append(item)
            report["active_decision"] = None
            write(destination, report)
            print(json.dumps(item), flush=True)
            if verdict != "AGREE":
                raise RuntimeError("Independent verifier did not agree; stop qualification")
        else:
            raise RuntimeError("Verifier input closed before successful completion")
    except BaseException as exc:
        report.update(status="stopped", error=f"{type(exc).__name__}: {exc}")
        write(destination, report)
        print(json.dumps({"error": report["error"]}), flush=True)
        raise
    finally:
        report["cached_rooted_transactions"] = len(cache)
        write(destination, report)
        store.db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
