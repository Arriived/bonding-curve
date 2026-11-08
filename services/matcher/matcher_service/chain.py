"""Chain reads: JSON-RPC client and the state snapshot decisions are computed from.

A snapshot is Config + every Room, Door and SlugLock account of the program + the Clock sysvar, each
read with its context slot, plus each door mint's TokenMetadata face. Faces are immutable (the program
revokes the metadata update authority), so they are cached once verified immutable; every mutable
account is re-read for every snapshot.

Freshness budget (enforced in `Snapshot.check_fresh`, values from config):
  - coherence: all reads of one snapshot lie within `coherence_slots` of each other;
  - lag: the snapshot slot is at most `max_lag_slots` behind the cluster's confirmed slot at the time
    the decision is signed;
  - age: the snapshot was read at most `max_age_seconds` ago (wall clock).
A decision that would use state outside the budget is refused, never computed.
"""
import base64
import struct
import threading
import time

import httpx
from solders.pubkey import Pubkey

from . import layouts

CLOCK_SYSVAR = "SysvarC1ock11111111111111111111111111111111"


class RpcError(Exception):
    """Any RPC failure: transport error, HTTP error, JSON-RPC error, or a malformed result."""


class StaleState(Exception):
    pass


class RpcClient:
    def __init__(self, url, timeout=10.0, transport=None):
        self.url = url
        self._http = httpx.Client(timeout=timeout, transport=transport)
        self.errors = 0

    RATE_LIMIT_RETRIES = 4          # 429 only; total wait capped by RATE_LIMIT_MAX_WAIT per retry
    RATE_LIMIT_MAX_WAIT = 4.0

    def call(self, method, params):
        try:
            for attempt in range(self.RATE_LIMIT_RETRIES + 1):
                r = self._http.post(self.url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
                if r.status_code != 429 or attempt == self.RATE_LIMIT_RETRIES:
                    break
                # Public RPCs (devnet) rate-limit getProgramAccounts. Back off and retry; the snapshot's slot
                # coherence and age checks still refuse anything a slow retry would make stale.
                try:
                    wait = float(r.headers.get("retry-after", ""))
                except ValueError:
                    wait = 0.5 * 2 ** attempt
                time.sleep(min(max(wait, 0.0), self.RATE_LIMIT_MAX_WAIT))
            r.raise_for_status()
            body = r.json()
        except (httpx.HTTPError, ValueError) as e:
            self.errors += 1
            # httpx embeds the request URL in exception text; provider responses
            # may echo it too. These errors reach public refusals and logs.
            status = f" (HTTP {e.response.status_code})" if isinstance(e, httpx.HTTPStatusError) else ""
            raise RpcError(f"{method}: {type(e).__name__}{status}") from None
        if "error" in body:
            self.errors += 1
            error = body['error']
            code = error.get('code') if isinstance(error, dict) else None
            suffix = f" (code {code})" if type(code) is int else ""
            raise RpcError(f"{method}: JSON-RPC error{suffix}")
        if "result" not in body:
            self.errors += 1
            raise RpcError(f"{method}: no result")
        return body["result"]

    def slot(self):
        return int(self.call("getSlot", [{"commitment": "confirmed"}]))

    def block_height(self):
        return int(self.call("getBlockHeight", [{"commitment": "confirmed"}]))

    def balance(self, pubkey):
        return int(self.call("getBalance", [str(pubkey), {"commitment": "confirmed"}])["value"])

    def min_balance(self, data_len):
        return int(self.call("getMinimumBalanceForRentExemption", [int(data_len)]))

    def latest_blockhash(self):
        r = self.call("getLatestBlockhash", [{"commitment": "confirmed"}])
        return r["value"]["blockhash"], int(r["value"]["lastValidBlockHeight"]), int(r["context"]["slot"])

    def account(self, pubkey, min_slot=None):
        cfg = {"encoding": "base64", "commitment": "confirmed"}
        if min_slot:
            cfg["minContextSlot"] = min_slot
        r = self.call("getAccountInfo", [str(pubkey), cfg])
        v = r["value"]
        return int(r["context"]["slot"]), (None if v is None else base64.b64decode(v["data"][0])), v

    def accounts(self, pubkeys, min_slot=None):
        out, slot = {}, 0
        keys = [str(k) for k in pubkeys]
        for i in range(0, len(keys), 100):
            cfg = {"encoding": "base64", "commitment": "confirmed"}
            if min_slot:
                cfg["minContextSlot"] = min_slot
            r = self.call("getMultipleAccounts", [keys[i:i + 100], cfg])
            slot = max(slot, int(r["context"]["slot"]))
            for k, v in zip(keys[i:i + 100], r["value"]):
                out[k] = None if v is None else base64.b64decode(v["data"][0])
        return slot, out

    def program_accounts(self, program, name, size, min_slot=None):
        disc = base64.b64encode(layouts.DISC[name]).decode()
        cfg = {"encoding": "base64", "commitment": "confirmed", "withContext": True,
               "filters": [{"dataSize": size}, {"memcmp": {"offset": 0, "bytes": disc, "encoding": "base64"}}]}
        if min_slot:
            cfg["minContextSlot"] = min_slot
        r = self.call("getProgramAccounts", [str(program), cfg])
        return int(r["context"]["slot"]), [(a["pubkey"], base64.b64decode(a["account"]["data"][0])) for a in r["value"]]


def pda(seeds, program):
    return Pubkey.find_program_address(seeds, Pubkey.from_string(str(program)))[0]


class Snapshot:
    def __init__(self, program_id, slots, clock_unix, config, config_key, rooms, slugs, read_wall, names=None):
        self.program_id = program_id
        self.slots = slots              # read -> context slot
        self.slot = max(slots.values())
        self.clock_unix = clock_unix    # Clock.unix_timestamp at slots["clock"]; the decision's `now`
        self.config = config
        self.config_key = config_key
        self.rooms = rooms              # room_id -> room dict (+ pubkey, faces ordered by door index)
        self.slugs = slugs              # SlugLock PDA -> holder room_id
        self.names = names or {}        # NameLock key hex -> holder room_id
        self.read_wall = read_wall

    def slug_pda(self, identity_hex):
        return str(pda([b"slug", bytes.fromhex(identity_hex)], self.program_id))

    def slug_holder(self, identity_hex):
        return self.slugs.get(self.slug_pda(identity_hex))

    def name_pda(self, key_hex):
        return str(pda([b"name", bytes.fromhex(key_hex)], self.program_id))

    def name_holder(self, key_hex):
        return self.names.get(key_hex)

    def coherent(self, coherence_slots):
        return max(self.slots.values()) - min(self.slots.values()) <= coherence_slots

    def check_fresh(self, cluster_slot, budget, now_wall=None):
        now_wall = time.time() if now_wall is None else now_wall
        if not self.coherent(budget.coherence_slots):
            raise StaleState(f"snapshot reads span {max(self.slots.values()) - min(self.slots.values())} slots "
                             f"> {budget.coherence_slots}")
        lag = cluster_slot - self.slot
        if lag > budget.max_lag_slots:
            raise StaleState(f"snapshot slot {self.slot} is {lag} slots behind the cluster > {budget.max_lag_slots}")
        age = now_wall - self.read_wall
        if age > budget.max_age_seconds:
            raise StaleState(f"snapshot is {age:.1f}s old > {budget.max_age_seconds}s")
        return {"lag_slots": lag, "age_seconds": round(age, 3)}

    def summary(self):
        return {"slots": self.slots, "slot": self.slot, "clock_unix": self.clock_unix,
                "rooms": len(self.rooms), "slug_locks": len(self.slugs), "name_locks": len(self.names)}


class ChainState:
    """Builds snapshots. Thread-safe; the HTTP app shares one instance."""

    def __init__(self, rpc: RpcClient, program_id: str):
        self.rpc = rpc
        self.program_id = program_id
        self.config_key = str(pda([b"config"], program_id))
        self._faces = {}               # door mint -> face (only immutable faces are cached)
        self._lock = threading.Lock()
        self._snapshot = None

    def current(self):
        return self._snapshot

    def refresh(self):
        """Read a complete snapshot or raise RpcError / layouts.LayoutError. Never returns partial state."""
        rpc, prog = self.rpc, self.program_id
        s_rooms, rooms_raw = rpc.program_accounts(prog, "Room", layouts.ROOM_LEN)
        s_doors, doors_raw = rpc.program_accounts(prog, "Door", layouts.DOOR_LEN, min_slot=s_rooms)
        s_slugs, slugs_raw = rpc.program_accounts(prog, "SlugLock", layouts.SLUG_LEN, min_slot=s_rooms)
        s_names, names_raw = rpc.program_accounts(prog, "NameLock", layouts.NAME_LEN, min_slot=s_rooms)
        s_cfg, cfg_data, cfg_v = rpc.account(self.config_key, min_slot=s_rooms)
        if cfg_data is None or cfg_v["owner"] != prog:
            raise RpcError(f"Config {self.config_key} missing or not owned by {prog}")
        config = layouts.decode_config(cfg_data)
        rooms = {}
        for key, data in rooms_raw:
            r = layouts.decode_room(data)
            r["pubkey"] = key
            if str(pda([b"room", struct.pack("<Q", r["room_id"])], prog)) != key:
                raise layouts.LayoutError(f"room {key} is not the PDA of room_id {r['room_id']}")
            r["faces"] = []
            rooms[r["room_id"]] = r
        by_key = {r["pubkey"]: r for r in rooms.values()}
        doors = [layouts.decode_door(d) for _, d in doors_raw]
        missing = [d["mint"] for d in doors if d["mint"] not in self._faces]
        if missing:
            _, mints = rpc.accounts(missing, min_slot=s_rooms)
            for m, data in mints.items():
                if data is None:
                    raise RpcError(f"door mint {m} not found")
                face = layouts.decode_mint_face(data)
                if not face["immutable"]:
                    raise layouts.LayoutError(f"door mint {m} still has a mint/freeze/metadata authority")
                self._faces[m] = {"name": face["name"], "symbol": face["symbol"]}
        for d in sorted(doors, key=lambda d: (d["room"], d["index"])):
            room = by_key.get(d["room"])
            if room is None:
                continue  # a door whose room was created after the room read; ignored this snapshot
            if d["index"] != len(room["faces"]):
                continue  # gap: door read is ahead of the room read; faces stay a prefix
            room["faces"].append(self._faces[d["mint"]])
        for room in rooms.values():
            if not room["faces"]:
                raise layouts.LayoutError(f"room {room['room_id']} has no door 0 in this snapshot")
        slugs = {key: layouts.decode_slug(data)["room_id"] for key, data in slugs_raw}  # lock PDA -> holder
        names = {}
        for key, data in names_raw:   # key hex -> holder; the PDA is checked, as for rooms
            n = layouts.decode_name(data)
            if str(pda([b"name", bytes.fromhex(n["key"])], prog)) != key:
                raise layouts.LayoutError(f"name lock {key} is not the PDA of its key {n['key']}")
            names[n["key"]] = n["room_id"]
        s_clock, clock_data, _ = rpc.account(CLOCK_SYSVAR, min_slot=max(s_rooms, s_doors, s_slugs, s_names, s_cfg))
        clock_unix = struct.unpack_from("<q", clock_data, 32)[0]
        snap = Snapshot(prog, {"rooms": s_rooms, "doors": s_doors, "slug_locks": s_slugs, "name_locks": s_names,
                               "config": s_cfg, "clock": s_clock}, clock_unix, config, self.config_key, rooms,
                        slugs, time.time(), names)
        with self._lock:
            self._snapshot = snap
        return snap
