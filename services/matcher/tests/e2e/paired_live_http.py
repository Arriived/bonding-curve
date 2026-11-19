"""Run the unchanged paired_live client over HTTP with a separate verifier process.

The transport adds one altered-signature refusal before the valid first request.
All routing, signing, quotes and transaction checks remain in the prepared client.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import time

import httpx
import uvicorn

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rpc", required=True)
    ap.add_argument("--keys", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    spec = importlib.util.spec_from_file_location("prepared_paired_live", HERE / "paired_live.py")
    prepared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prepared)
    clients = []
    process = None
    verifier_error = None
    original_verify = prepared.verify_decision.verify
    report_path = args.out / "http-runner.json"
    assert not report_path.exists()
    report = {"status": "running", "pid": os.getpid(), "transport": "HTTP loopback",
              "refusal": "pending", "verifier": "separate process", "error": None}
    prepared.write(report_path, report)

    class LiveHttpClient:
        def __init__(self, app):
            self.server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=18793,
                log_level="warning", access_log=False, lifespan="off"))
            self.thread = threading.Thread(target=self.server.run, daemon=True)
            self.thread.start()
            clients.append(self)
            for _ in range(200):
                if self.server.started:
                    break
                assert self.thread.is_alive(), "Matcher HTTP server did not start"
                time.sleep(0.05)
            assert self.server.started
            self.http = httpx.Client(base_url="http://127.0.0.1:18793", timeout=60, trust_env=False)
            self.refused = False

        def get(self, path, **kwargs):
            return self.http.get(path, **kwargs)

        def post(self, path, **kwargs):
            if path == "/route" and not self.refused:
                altered = dict(kwargs["json"])
                altered["name"] += " x"
                with sqlite3.connect(args.out / "decisions.sqlite3") as db:
                    before = db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
                response = self.http.post(path, json=altered)
                with sqlite3.connect(args.out / "decisions.sqlite3") as db:
                    after = db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
                refusal = {"kind": "altered_signed_request", "request": altered,
                    "http_status": response.status_code, "response": response.json(),
                    "decision_rows_before": before, "decision_rows_after": after,
                    "transaction_signature": None, "transaction_slot": None,
                    "auth_request_signature": altered["signature"]}
                prepared.write(args.out / "live-refusal.json", refusal)
                assert response.status_code == 401 and response.json()["error"] == "unauthenticated"
                assert before == after == 0
                assert "transaction_base64" not in response.json()
                report["refusal"] = "passed"
                prepared.write(report_path, report)
                self.refused = True
                print("Live HTTP altered signed request refused: 401, no decision or transaction", flush=True)
            return self.http.post(path, **kwargs)

        def close(self):
            if hasattr(self, "http"):
                self.http.close()
            self.server.should_exit = True
            self.thread.join(10)
            assert not self.thread.is_alive(), "Matcher HTTP server did not stop"

    def verify_in_worker(record, rpc_url, chain_ok=True):
        nonlocal process, verifier_error
        if process is None:
            verifier_error = (args.out / "independent-verifier.stderr.txt").open("w", encoding="utf-8")
            process = subprocess.Popen([sys.executable, str(HERE / "paired_live_verify.py"),
                "--db", str(args.out / "decisions.sqlite3"), "--rpc", args.rpc,
                "--out", str(args.out)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=verifier_error, text=True, encoding="utf-8",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            ready = json.loads(process.stdout.readline())
            assert ready["ready"] and ready["pid"] != os.getpid()
            report["verifier_pid"] = ready["pid"]
            prepared.write(report_path, report)
        process.stdin.write(json.dumps({"decision_id": record["id"]}) + "\n")
        process.stdin.flush()
        line = process.stdout.readline()
        assert line, "Independent verifier exited without a result"
        result = json.loads(line)
        assert not result.get("error"), result.get("error")
        assert result["decision_id"] == record["id"]
        return result["checks"], result["landed"]

    prepared.TestClient = LiveHttpClient
    prepared.verify_decision.verify = verify_in_worker
    try:
        sys.argv = [str(HERE / "paired_live.py"), "--rpc", args.rpc,
                    "--keys", str(args.keys), "--out", str(args.out)]
        prepared.main()
        assert report["refusal"] == "passed" and process is not None
        process.stdin.write('{"stop": true}\n')
        process.stdin.flush()
        assert process.wait(timeout=15) == 0
        report["status"] = "passed"
    except BaseException as exc:
        report.update(status="stopped", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        prepared.verify_decision.verify = original_verify
        for client in clients:
            client.close()
        if process and process.poll() is None:
            process.stdin.close()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=15)
        if verifier_error:
            verifier_error.close()
        prepared.write(report_path, report)


if __name__ == "__main__":
    main()
