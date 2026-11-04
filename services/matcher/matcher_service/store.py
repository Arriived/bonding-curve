"""Append-only, hash-chained decision store (SQLite).

Every signed decision is written *before* the signed transaction is returned; if the write fails, the
request fails and the signature is discarded. Each row carries sha256(prev_hash || canonical record),
so deleting or editing a row breaks every later hash (`verify_chain`). The chain head can be published
(e.g. periodically, on-chain in a memo) so outsiders can detect a rewritten history; that publication is
listed as remaining work in the README.
"""
import hashlib
import json
import sqlite3
import threading
import time

GENESIS = "0" * 64


def canonical(record) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


class Store:
    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS decisions (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            id TEXT UNIQUE NOT NULL,
            created_unix REAL NOT NULL,
            launcher TEXT NOT NULL,
            kind TEXT NOT NULL,
            record TEXT NOT NULL,
            record_sha256 TEXT NOT NULL,
            prev_sha256 TEXT NOT NULL)""")
        self.db.execute("CREATE INDEX IF NOT EXISTS by_launcher ON decisions(launcher)")
        self.db.execute("""CREATE TRIGGER IF NOT EXISTS no_update BEFORE UPDATE ON decisions
            BEGIN SELECT RAISE(ABORT, 'decisions are append-only'); END""")
        self.db.execute("""CREATE TRIGGER IF NOT EXISTS no_delete BEFORE DELETE ON decisions
            BEGIN SELECT RAISE(ABORT, 'decisions are append-only'); END""")

    def head(self):
        row = self.db.execute("SELECT record_sha256 FROM decisions ORDER BY seq DESC LIMIT 1").fetchone()
        return row[0] if row else GENESIS

    def append(self, decision_id, launcher, kind, record):
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                prev = self.head()
                h = hashlib.sha256(prev.encode() + canonical(record)).hexdigest()
                self.db.execute("INSERT INTO decisions (id, created_unix, launcher, kind, record, record_sha256, "
                                "prev_sha256) VALUES (?,?,?,?,?,?,?)",
                                (decision_id, time.time(), launcher, kind, canonical(record).decode(), h, prev))
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
        return h

    def get(self, decision_id):
        row = self.db.execute("SELECT seq, id, created_unix, record, record_sha256, prev_sha256 FROM decisions "
                              "WHERE id = ?", (decision_id,)).fetchone()
        if not row:
            return None
        return {"seq": row[0], "id": row[1], "created_unix": row[2], "record": json.loads(row[3]),
                "record_sha256": row[4], "prev_sha256": row[5]}

    def verify_chain(self):
        prev = GENESIS
        n = 0
        for seq, rec, h, p in self.db.execute("SELECT seq, record, record_sha256, prev_sha256 FROM decisions "
                                              "ORDER BY seq"):
            if p != prev or hashlib.sha256(prev.encode() + rec.encode()).hexdigest() != h:
                return False, f"chain broken at seq {seq}"
            prev, n = h, n + 1
        return True, f"{n} records, head {prev}"
