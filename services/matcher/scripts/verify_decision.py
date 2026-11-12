"""Independently recompute a matcher decision from public chain data and report agreement.

Usage:
  python3 scripts/verify_decision.py <decision_id> --rpc URL (--service URL | --db PATH) [--json]

What it checks, without trusting the service's snapshot:
  1. Record integrity: the store's hash chain (with --db), and the record's own fields.
  2. Signature: the matcher signature verifies over the recorded transaction message, and the signing
     key equals Config.matcher_authority *as of the decision slot* (replayed from ConfigChanged events).
  3. Transaction content: the instruction is create_room/open_door with exactly the recorded room,
     door nonce and address, expires_at_slot, SlugLock, old holder, NameLock key and account, old name holder and
     Launch arguments (decoded from the message bytes). The name key is recomputed from the research matcher's
     own normalisation, not the service's code.
  4. State at the decision slot, rebuilt from the program's own events and block times:
     every room that could have matched (any door face equal under T3/T2n now; faces are immutable and
     only ever added), the candidate's SlugLock holder and its NameLock holder. Rooms are replayed from creation to the slot:
     RoomCreated -> creation; DoorOpened -> faces, door_count; Trade -> reserve, status, liveness
     buckets (Room::record semantics, amount = curve_lamports); PendingRetired.
     Timestamps: `created_at` is immutable, so it is read exactly from the Room account. The program's
     Clock at a trade is not in any event, and a transaction's block time is only an estimate of it: on
     devnet they differed by 1 s (localnet: equal). So `last_trade_at` and bucket starts are rebuilt from
     block times and compared within BLOCK_TIME_TOLERANCE seconds, and the decision is recomputed at both
     ends of that tolerance. If the outcome depends on it, the result is INCONCLUSIVE (exit 2), never a
     false AGREE or DISAGREE.
  5. Decision: recomputed with the *research* matcher (research/.../matcher.py decide()) for the text
     rule, liveness and ties, plus the program's floor semantics, using Config thresholds at the slot.
     Compared with the recorded kind, rule, room and old holder.
  6. Outcome: whether a transaction carrying this matcher signature landed, and whether it succeeded.
Exit code 0 on agreement, 1 on any disagreement, 2 if the check could not be completed or is inconclusive.
"""
import argparse
import base64
import hashlib
import importlib.util
import json
from math import isqrt
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from matcher_service import rules  # noqa: E402  (program fold/identity port only)
from matcher_service.chain import RpcClient, RpcError, pda  # noqa: E402
from matcher_service.layouts import decode_door, decode_mint_face, decode_room  # noqa: E402
from matcher_service.layouts import ROOM_LEN, DOOR_LEN  # noqa: E402
from matcher_service.store import Store  # noqa: E402
from solders.message import Message  # noqa: E402
from solders.pubkey import Pubkey  # noqa: E402
from solders.signature import Signature  # noqa: E402

REPO = HERE.parent.parent.parent
RESEARCH = REPO / "research/doors_into_one_room/scripts/narrative/matcher.py"
COMPUTE_BUDGET = "ComputeBudget111111111111111111111111111111"


def research():
    spec = importlib.util.spec_from_file_location("research_matcher", RESEARCH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def disc(kind, name):
    return hashlib.sha256(f"{kind}:{name}".encode()).digest()[:8]


EVENTS = {disc("event", n): n for n in ("RoomCreated", "DoorOpened", "Trade", "PendingRetired", "SlugReleased",
                                        "NameReleased", "ConfigChanged", "DoorsSwapped", "SwapFeesClaimed")}
NAME_KEY_DOMAIN = b"doors-v1:name-key:v1"


_CONF = json.loads((HERE.parent / "data" / "confusables_ascii.json").read_text(encoding="utf-8"))["map"]


def _pre(s):
    """Rules B and C, step 1: NFKC, Unicode confusables to ASCII, '|' to 'l', then anyascii for every remaining
    non-ASCII letter or digit (CORRECTIONS §18, §20)."""
    import unicodedata
    from anyascii import anyascii
    s = unicodedata.normalize("NFKC", s)
    s = "".join(_CONF.get(ch, ch) for ch in s).replace("|", "l")
    return "".join(anyascii(ch) if ord(ch) > 127 and unicodedata.category(ch)[0] in "LN" else ch for ch in s)


def research_keys(rm, name, symbol):
    """(symbol key, name key, key class string) from the research matcher's own fold plus rules A, B, C and I,
    written here independently of services/matcher rules.py. B and C rewrite characters first; I joins every letter
    of the name and folds once (L into I after folding, per B), then strips a leading THE/OFFICIAL while 4+ letters
    remain and any trailing COIN/TOKEN/OFFICIAL/SOLANA/CTO; A decides the key class on the name before stripping."""
    import re
    li = lambda x: x.replace("L", "I")  # noqa: E731
    raw = re.split(r"[^0-9a-z\u00c0-\uffff]+", rm._base(_pre(name)))
    full = li(rm._fold("".join(ch for t in raw for ch in t if ch.isalnum())))
    lead = [li(w) for w in ("THE", "OFFICIAL")]
    trail = sorted((li(w) for w in ("COIN", "TOKEN", "OFFICIAL", "SOLANA", "CTO")), key=len, reverse=True)
    nk, again = full, True
    while again:
        again = False
        for w in trail:   # trailing first, so "Theory Coin" keys like "Theory"
            if nk.endswith(w) and len(nk) > len(w):
                nk, again = nk[: -len(w)], True
        for w in lead:
            if nk.startswith(w) and len(nk) - len(w) >= 4:
                nk, again = nk[len(w):], True
    sk = li(rm.symbol_key(_pre(symbol)))
    if nk and len(full) >= rm.DEFAULTS["name_equal_min_len"]:
        return sk, nk, ("N", nk)
    if nk and sk:
        return sk, nk, ("P", sk + "\x00" + nk)
    return sk, nk, None


def name_key_research(rm, name, symbol):
    """The NameLock key, from research_keys. Must equal services/matcher rules.name_lock_key."""
    k = research_keys(rm, name, symbol)[2]
    if k is None:
        return None
    return hashlib.sha256(NAME_KEY_DOMAIN + b"\x00" + k[0].encode() + b"\x00" + k[1].encode()).digest()[:16]


class R:
    """Little-endian Borsh reader."""

    def __init__(self, b):
        self.b, self.o = b, 0

    def take(self, n):
        v = self.b[self.o:self.o + n]
        self.o += n
        return v

    def pk(self):
        return str(Pubkey.from_bytes(self.take(32)))

    def u(self, fmt):
        v = struct.unpack_from("<" + fmt, self.b, self.o)[0]
        self.o += struct.calcsize(fmt)
        return v

    def u128(self):
        lo, hi = struct.unpack_from("<QQ", self.b, self.o)
        self.o += 16
        return lo + (hi << 64)

    def s(self):
        n = self.u("I")
        return self.take(n).decode()


def decode_event(data):
    name = EVENTS.get(data[:8])
    if not name:
        return None
    r = R(data[8:])
    if name == "RoomCreated":
        out = {"room": r.pk(), "room_id": r.u("Q"), "identity": r.take(32).hex(), "founder": r.pk()}
        r.u("H"), r.u("H"), r.u("B"), r.u("I")          # founder_share_bps, matcher_version, rule, face
        out["name_key"] = (r.take(16).hex() if r.u("B") else None) if r.o < len(r.b) else None
        return name, out
    if name == "DoorOpened":
        return name, {"room": r.pk(), "door": r.pk(), "index": r.u("I"), "mint": r.pk()}
    if name == "Trade":
        room = r.pk()
        door = r.pk() if r.u("B") else None
        user, buy = r.pk(), bool(r.u("B"))
        tokens, room_tokens, curve_lamports, fee, sold_after, reserve = (r.u("Q") for _ in range(6))
        return name, {"room": room, "door": door, "buy": buy, "curve_lamports": curve_lamports,
                      "room_tokens": room_tokens, "fee": fee, "sold_after": sold_after,
                      "reserve": reserve, "status": r.u("B")}
    if name == "DoorsSwapped":
        return name, {"room": r.pk(), "from": r.pk(), "to": r.pk(),
                      "door_tokens_in":r.u('Q'), "door_tokens_out":r.u('Q'),
                      "room_tokens":r.u('Q'), "fee":r.u('Q')}
    if name == "SwapFeesClaimed":
        return name, {"room":r.pk(), "door":r.pk() if r.u('B') else None,
                      "recipient":r.pk(), "room_tokens":r.u('Q')}
    if name == "PendingRetired":
        return name, {"room": r.pk(), "lamports": r.u("Q"), "retired": r.u("Q")}
    if name == "SlugReleased":
        return name, {"identity": r.take(32).hex(), "room": r.pk()}
    if name == "NameReleased":
        return name, {"key": r.take(16).hex(), "room": r.pk()}
    if name == "ConfigChanged":
        admin, matcher, _fs = r.pk(), r.pk(), r.u("H")
        s = {"protocol_fee_recipient": r.pk(), "fee_bps": r.u("H"), "door_share_bps": r.u("H"),
             "door_fee_lamports": r.u("Q"), "room_fee_lamports": r.u("Q"), "convert_fee_lamports": r.u("Q"),
             "v_sol_lamports": r.u("Q"), "v_tok": r.u("Q"), "supply": r.u("Q"), "r_star_lamports": r.u("Q"),
             "meteora_dynamic_config": r.pk(), "graduation_trigger_lamports": r.u("Q"), "paused": bool(r.u("B")),
             "matcher_authority": r.pk(), "live_min_reserve_lamports": r.u("Q"), "live_max_idle_seconds": r.u("Q"),
             "live_new_seconds": r.u("Q"), "live_min_volume_lamports": r.u("Q")}
        return name, {"admin": admin, "matcher": matcher, "settings": s}
    return None


class History:
    def __init__(self, rpc):
        self.rpc = rpc
        self._tx = {}
        self._block_order = {}

    def signatures(self, address, upto_slot):
        out, before = [], None
        while True:
            params = {"limit": 1000, "commitment": "confirmed"}
            if before:
                params["before"] = before
            page = self.rpc.call("getSignaturesForAddress", [str(address), params])
            if not page:
                break
            out += [s for s in page if s["slot"] <= upto_slot and s.get("err") is None]
            before = page[-1]["signature"]
            if len(page) < 1000:
                break
        return self._ordered(out)

    def _ordered(self, sigs):
        by_slot = {}
        for s in sigs:
            by_slot.setdefault(s["slot"], []).append(s["signature"])
        ordered = []
        for slot in sorted(by_slot):
            group = by_slot[slot]
            if len(group) > 1:  # several transactions in one slot: use the block's own order
                if slot not in self._block_order:
                    blk = self.rpc.call("getBlock", [slot, {"transactionDetails": "signatures", "rewards": False,
                                                            "commitment": "confirmed",
                                                            "maxSupportedTransactionVersion": 0}])
                    self._block_order[slot] = {s: i for i, s in enumerate(blk["signatures"])}
                group.sort(key=lambda s: self._block_order[slot].get(s, 1 << 30))
            ordered += [(slot, s) for s in group]
        return ordered

    def tx(self, sig):
        if sig not in self._tx:
            self._tx[sig] = self.rpc.call("getTransaction", [sig, {"encoding": "json", "commitment": "confirmed",
                                                                   "maxSupportedTransactionVersion": 0}])
        return self._tx[sig]

    def events(self, sig):
        t = self.tx(sig)
        out = []
        for line in (t["meta"].get("logMessages") or []):
            if line.startswith("Program data: "):
                ev = decode_event(base64.b64decode(line[len("Program data: "):]))
                if ev:
                    out.append(ev)
        return t["blockTime"], out


BLOCK_TIME_TOLERANCE = 5   # seconds between a block time and the Clock the program read


def first_buy_quote(curve, gross):
    """Independent integer derivation, including pre-buy anchoring and fee settlement."""
    if not gross or curve['status'] != 0:
        return None
    vs, vt = curve['v_sol_lamports'], curve['v_tok']
    old = curve['sold']
    anchor = max(1, 30_000_000_000 * (vt - old)**2 // (vs * vt))
    settled = min(curve['pending_reserve_sol'], curve['graduation_trigger_lamports'] - curve['reserve'])
    available = curve['graduation_trigger_lamports'] - curve['reserve'] - settled
    if available <= 0:
        return None
    if settled:
        old = vt - vs * vt // (vs * old // (vt - old) + settled + vs + 1) - 1
    net = min(gross * 10000 // (10000 + curve['fee_bps']), available)
    end = vt - vs * vt // (vs * old // (vt - old) + net + vs + 1) - 1
    room_out = end - old
    if room_out <= 0 or end > curve['supply']:
        return None
    target = room_out + 1
    door_out = (target * 1_073_025_606_000_000 - 1) // (anchor + target)
    return door_out if 0 < door_out <= 10**15 else None


def record_amount(buckets, now, amount):
    """Room::record: hourly ring of 25 tagged buckets."""
    start = now // 3600 * 3600
    i = start // 3600 % 25
    if buckets[i][0] != start:
        buckets[i] = [start, 0]
    buckets[i][1] += amount


def replay_room(hist, room_pk, trigger, upto_slot, faces_by_mint, immutable=None):
    st = None
    for slot, sig in hist.signatures(room_pk, upto_slot):
        when, evs = hist.events(sig)
        # create_room emits door 0's DoorOpened before RoomCreated: apply RoomCreated first.
        evs = sorted(evs, key=lambda ev: ev[0] != "RoomCreated")
        for name, e in evs:
            if e.get("room") != room_pk:
                continue
            if name == "RoomCreated":
                st = {"room_id": e["room_id"], "status": 0, "created_at": when, "reserve": 0, "last_trade_at": when,
                      "buckets": [[0, 0] for _ in range(25)], "faces": [], "door_count": 0, "identity": e["identity"],
                      "trade_times": [], "sold":0, "pending_reserve_sol":0,
                      **(immutable or {})}
            elif st is None:
                continue
            elif name == "DoorOpened":
                st["door_count"] += 1
                st["faces"].append(faces_by_mint[e["mint"]])
            elif name == "Trade":
                st['sold'] = e['sold_after']
                if e['door'] is None:
                    st['pending_reserve_sol'] += e['fee'] * st['door_share_bps'] // 10000
                st["reserve"], st["status"] = e["reserve"], e["status"]
                st["last_trade_at"] = when
                st["trade_times"].append(when)
                record_amount(st["buckets"], when, e["curve_lamports"])
            elif name == "PendingRetired":
                st['pending_reserve_sol'] -= e['lamports']
                vs, vt = st['v_sol_lamports'], st['v_tok']
                base = vs * st['sold'] // (vt - st['sold'])
                st['sold'] = vt - vs * vt // (base + e['lamports'] + vs + 1) - 1
                st["reserve"] += e["lamports"]
                st["status"] = 1 if st["reserve"] == trigger else st["status"]
    return st


def config_at(hist, config_key, upto_slot):
    cfg = None
    for slot, sig in hist.signatures(config_key, upto_slot):
        for name, e in hist.events(sig)[1]:
            if name == "ConfigChanged":
                cfg = e["settings"]
    return cfg


def lock_holder_at(hist, lock_pda, identity, upto_slot):
    holder = None
    for slot, sig in hist.signatures(lock_pda, upto_slot):
        for name, e in hist.events(sig)[1]:
            if name == "RoomCreated" and e["identity"] == identity:
                holder = e["room_id"]
            elif name == "SlugReleased" and e["identity"] == identity:
                holder = None
    return holder


def name_holder_at(hist, lock_pda, key_hex, upto_slot):
    holder = None
    for slot, sig in hist.signatures(lock_pda, upto_slot):
        for name, e in hist.events(sig)[1]:
            if name == "RoomCreated" and e.get("name_key") == key_hex:
                holder = e["room_id"]
            elif name == "NameReleased" and e["key"] == key_hex:
                holder = None
    return holder


def decode_launch_ix(msg, program, idl_path):
    idl = json.load(open(idl_path))
    names = {bytes(i["discriminator"]): i for i in idl["instructions"]}
    keys = [str(k) for k in msg.account_keys]
    launches = [ix for ix in msg.instructions if keys[ix.program_id_index] == program]
    others = [keys[ix.program_id_index] for ix in msg.instructions if keys[ix.program_id_index] not in (program, COMPUTE_BUDGET)]
    if len(launches) != 1 or others:
        raise ValueError(f"message must hold exactly one doors instruction and only compute-budget others; got {others}")
    ix = launches[0]
    data = bytes(ix.data)
    legacy_launches = {hashlib.sha256(f"global:{i['name']}".encode()).digest()[:8]: i
                       for i in idl["instructions"] if i["name"] in ("create_room", "open_door")}
    legacy = data[:8] in legacy_launches
    spec = (legacy_launches if legacy else names)[data[:8]]
    def flat(accs, p=""):
        for a in accs:
            if "accounts" in a:
                yield from flat(a["accounts"], p + a["name"] + ".")
            else:
                yield p + a["name"]
    accounts = dict(zip(flat(spec["accounts"]), [keys[i] for i in ix.accounts]))
    r = R(data[8:])
    room_id = r.u("Q") if spec["name"] == "create_room" else None
    launch = {"name": r.s(), "symbol": r.s(), "uri": r.s(), "first_buy_lamports": r.u("Q"),
              "min_tokens_out": r.u("Q"), "matcher_version": r.u("H"), "rule": r.u("B"), "face": r.u("I"),
              "max_fee_lamports": r.u("Q"), "expected_terms_hash": r.take(32).hex(),
              "door_nonce": r.u("Q"), "expires_at_slot": r.u("Q")}
    if legacy:
        launch["max_room_price"] = r.u128()
    else:
        launch["max_reserve_lamports"] = r.u("Q")
    if spec["name"] == "create_room":
        launch["name_key"] = r.take(16).hex() if r.u("B") else None
    if r.o != len(r.b):
        raise ValueError("unexpected trailing launch instruction bytes")
    return spec["name"], room_id, accounts, launch


def recompute(rm, rooms, holder_id, cfg, now, name, symbol, name_holder_id=None):
    """Program floor semantics, the key-based text rule (rules A and B, research fold), research liveness and ties."""
    params = {k: cfg[k] for k in ("live_min_reserve_lamports", "live_max_idle_seconds", "live_new_seconds",
                                  "live_min_volume_lamports")}
    def keyed_faces(faces):
        # Only faces carrying the room's own name key (door 0's) are matchable (face-laundering fix, CORRECTIONS
        # §17); the key comes from the research matcher's ident(), independently of the service. Door 0 stays first.
        if not faces:
            return faces
        k = name_key_research(rm, faces[0]["name"], faces[0]["symbol"])
        return [f for f in faces if name_key_research(rm, f["name"], f["symbol"]) == k] if k else faces[:1]

    def research_room(r):
        return {"room_id": r["room_id"], "status": r["status"], "faces": keyed_faces(r["faces"]),
                "created_at": r["created_at"],
                "reserve": r["reserve"], "last_trade_at": r["last_trade_at"],
                "liveness_buckets": [{"start": s, "amount": a} for s, a in r["buckets"] if s or a]}
    p = dict(rm.DEFAULTS, **params)
    old_holder = None
    live_slug = None
    if holder_id is not None:
        h = rooms[holder_id]
        if h['status'] > 1: return {'kind':'refuse','rule':'graduated_identity'}
        if rm.is_live(research_room(h),now,p)[0]: live_slug=holder_id
        else: old_holder=holder_id
    old_name_holder = None
    live_name = None
    if name_holder_id is not None:
        h=rooms[name_holder_id]
        if h['status'] > 1: return {'kind':'refuse','rule':'graduated_name'}
        if rm.is_live(research_room(h),now,p)[0]: live_name=name_holder_id
        else: old_name_holder=name_holder_id
    csk,_,ckey=research_keys(rm,name,symbol)
    if live_slug is not None:
        if ckey is not None and live_slug != live_name:
            return {'kind':'refuse','rule':'slug_name_conflict'}
        return {'kind':'door','rule':'floor','room_id':live_slug,'old_holder':None,'old_name_holder':None}
    if live_name is not None:
        h=rooms[live_name]
        if not h['faces'] or research_keys(rm,h['faces'][0]['name'],h['faces'][0]['symbol'])[2]!=ckey:
            return {'kind':'refuse','rule':'inconsistent_state'}
        same=keyed_faces(h['faces'])
        t3=bool(csk) and any(research_keys(rm,f['name'],f['symbol'])[0]==csk for f in same)
        return {'kind':'door','rule':'T3' if t3 else 'T2n','room_id':live_name,
                'old_holder':old_holder,'old_name_holder':None}
    return {'kind':'new_room','rule':'new_room','room_id':None,'old_holder':old_holder,
            'old_name_holder':old_name_holder}


def verify(record, rpc_url, chain_ok=True):
    rpc = RpcClient(rpc_url, timeout=30)
    hist = History(rpc)
    rm = research()
    checks = []
    def check(name, ok, detail="", inconclusive=False):
        checks.append({"check": name, "ok": bool(ok), "detail": detail, "inconclusive": bool(inconclusive)})
    req, dec, txr, state = record["request"], record["decision"], record["transaction"], record["state"]
    program = record["program"]
    check("store hash chain", chain_ok)
    check("unicode tables match the service's", rm.unicodedata.unidata_version == record["service"]["unicode"],
          f"verifier {rm.unicodedata.unidata_version}, service {record['service']['unicode']}")

    # 2. signature
    msg_bytes = base64.b64decode(txr["message_base64"])
    msg = Message.from_bytes(msg_bytes)
    matcher = Pubkey.from_string(txr["matcher"])
    sig = Signature.from_string(record["id"])
    check("matcher signature verifies over the recorded message", sig.verify(matcher, msg_bytes))
    slot = state["slot"]
    cfg = config_at(hist, record["config_account"], slot)
    check("Config at the decision slot replayed from ConfigChanged", cfg is not None)
    if cfg is None:
        return checks, None
    check("signer equals Config.matcher_authority at the decision slot", cfg["matcher_authority"] == str(matcher),
          cfg["matcher_authority"])
    check("message fee payer is the launcher", str(msg.account_keys[0]) == req["launcher"])
    check("message blockhash is the recorded one", str(msg.recent_blockhash) == txr["blockhash"])

    # 3. instruction content
    name, room_id, acc, launch = decode_launch_ix(msg, program, HERE.parent / "idl/doors_v1.paired.json")
    want = "create_room" if dec["kind"] == "new_room" else "open_door"
    check("instruction matches the decision kind", name == want, name)
    for k in ("name", "symbol", "uri", "first_buy_lamports", "max_fee_lamports"):
        check(f"Launch.{k} equals the request", launch[k] == req[k], repr(launch[k]))
    # min_tokens_out: the request's own value, or (omitted) the recorded quote less its slippage. The quote
    # is independently recomputed below from replayed sold amounts and pending fee splits.
    fbq = record.get("first_buy_quote")
    want_min = req["min_tokens_out"] if req.get("min_tokens_out") is not None else (
        fbq["min_tokens_out"] if fbq else 0)
    check("Launch.min_tokens_out equals the request, or the recorded quote less max_slippage_bps",
          launch["min_tokens_out"] == want_min == record.get("launch_min_tokens_out", want_min)
          and (fbq is None or req.get("min_tokens_out") is not None
               or want_min == max(1, fbq["tokens"] * (10000 - fbq["max_slippage_bps"]) // 10000))
          and (req["first_buy_lamports"] == 0 or want_min > 0), repr(launch["min_tokens_out"]))
    check("Launch.rule and face equal the decision", (launch["rule"], launch["face"]) ==
          (dec["rule_code"], dec["face"]), f"{launch['rule']},{launch['face']}")
    room_key = acc.get("room") or acc.get("core.room")
    check("room account equals the decision", room_key == dec["room"], room_key)
    if room_id is not None:
        check("room-id nonce equals the decision", str(room_id) == dec["room_id"])
    check("door account equals the decision", acc["door"] == dec["door"])
    check("door account is the PDA of the signed door nonce",
          acc["door"] == str(pda([b"door", bytes(Pubkey.from_string(room_key)), struct.pack("<Q", launch["door_nonce"])], program))
          and str(launch["door_nonce"]) == dec["door_nonce"] and (launch["door_nonce"] == 0) == (name == "create_room"))
    check("Launch.expires_at_slot is the recorded expiry, within 150 slots of the blockhash slot",
          launch["expires_at_slot"] == txr["expires_at_slot"]
          and 0 <= launch["expires_at_slot"] - txr["blockhash_slot"] <= 150, str(launch["expires_at_slot"]))
    check("SlugLock account equals the candidate identity's PDA", acc["slug"] == dec["slug_lock"] ==
          str(pda([b"slug", rules.program_identity(req["name"], req["symbol"])], program)))
    oh = acc.get("old_holder")
    want_oh = program if dec["old_holder_room_id"] is None else str(pda([b"room", struct.pack("<Q", int(dec["old_holder_room_id"]))], program))
    check("old holder account equals the decision", oh == want_oh, oh)
    # Both new rooms and door routes depend on the current candidate NameLock.
    # Only create_room carries that key in its instruction; replay must derive
    # it independently for open_door as well.
    want_key = name_key_research(rm, req["name"], req["symbol"])
    if name == "create_room":
        check("Launch name_key is the research matcher's key for the request",
              launch["name_key"] == (want_key.hex() if want_key else None) == dec.get("name_key"), launch["name_key"])
        want_nl = program if want_key is None else str(pda([b"name", want_key], program))
        check("NameLock account equals the key's PDA", acc.get("name_lock") == want_nl
              and (want_key is None or dec.get("name_lock") == want_nl), acc.get("name_lock"))
        onh = acc.get("old_name_holder")
        want_onh = program if dec.get("old_name_holder_room_id") is None else str(
            pda([b"room", struct.pack("<Q", int(dec["old_name_holder_room_id"]))], program))
        check("old name holder account equals the decision", onh == want_onh, onh)

    # 4. state at the slot, rebuilt from events
    current_rooms = [decode_room(d) | {"pubkey": k} for k, d in
                     rpc.program_accounts(program, "Room", ROOM_LEN)[1]]
    current_doors = [decode_door(d) for _, d in rpc.program_accounts(program, "Door", DOOR_LEN)[1]]
    mints = sorted({d["mint"] for d in current_doors})
    faces_by_mint = {}
    for i in range(0, len(mints), 100):
        r = rpc.call("getMultipleAccounts", [mints[i:i + 100], {"encoding": "base64"}])
        for m, v in zip(mints[i:i + 100], r["value"]):
            f = decode_mint_face(base64.b64decode(v["data"][0]))
            faces_by_mint[m] = {"name": f["name"], "symbol": f["symbol"]}
    c = rm.ident(req["name"], req["symbol"])
    room_of_door = {}
    for d in current_doors:
        room_of_door.setdefault(d["room"], []).append(faces_by_mint[d["mint"]])
    identity = rules.program_identity(req["name"], req["symbol"]).hex()
    lock = str(pda([b"slug", bytes.fromhex(identity)], program))
    holder = lock_holder_at(hist, lock, identity, slot)
    name_holder = None
    if want_key is not None:
        name_holder = name_holder_at(hist, str(pda([b"name", want_key], program)), want_key.hex(), slot)
    relevant = {}
    for r in current_rooms:
        faces = room_of_door.get(r["pubkey"], [])
        if any(rm.text_tier(c, rm.ident(f["name"], f["symbol"]), rm.DEFAULTS, fuzzy=False)[0] in ("T3", "T2n")
               for f in faces) or r["room_id"] in (holder, name_holder):
            relevant[r["pubkey"]] = r
    rebuilt = {}
    for pk, r in relevant.items():
        acct = rpc.account(pk)[1]
        trig = struct.unpack_from("<Q", acct, 184)[0]
        immutable = {k:r[k] for k in ('v_sol_lamports','v_tok','supply','graduation_trigger_lamports','fee_bps','door_share_bps')}
        st = replay_room(hist, pk, trig, slot, faces_by_mint, immutable)
        if st is not None:
            st["created_at"] = struct.unpack_from("<q", acct, 288)[0]   # immutable: exact from the account
            rebuilt[st["room_id"]] = st
    now = rpc.call("getBlockTime", [state["slots"]["clock"]])
    check("decision clock equals the block time of the clock-read slot", now == state["clock_unix"],
          f"chain {now}, record {state['clock_unix']}")
    recorded = {r["room_id"]: r for r in state["rooms"]}
    for rid, st in rebuilt.items():
        rec = recorded.get(rid)
        matched_then = rid in (holder, name_holder) or any(
            rm.text_tier(c, rm.ident(f["name"], f["symbol"]), rm.DEFAULTS, fuzzy=False)[0] in ("T3", "T2n")
            for f in st["faces"])
        if rec is None:
            # Faces only grow, so a room matching only through a later door did not match at the slot.
            check(f"room {rid} was considered by the service", not matched_then,
                  "matched at the decision slot but absent from the record")
            continue
        got = {"status": st["status"], "created_at": st["created_at"], "reserve": st["reserve"],
               "last_trade_at": st["last_trade_at"], "door_count": st["door_count"],
               "buckets": sorted([s, str(a)] for s, a in st["buckets"] if s or a), "faces": st["faces"]}
        want = {k: rec[k] for k in ("status", "created_at", "reserve", "last_trade_at", "door_count", "faces")}
        want["buckets"] = sorted(rec["buckets"])
        tol = BLOCK_TIME_TOLERANCE
        diffs = [k for k in got if got[k] != want[k]
                 and not (k == "last_trade_at" and abs(got[k] - want[k]) <= tol)]
        near_hour = any(min(t % 3600, 3600 - t % 3600) <= tol for t in st["trade_times"])
        timing_only = diffs == ["buckets"] and near_hour and \
            sum(int(a) for _, a in got["buckets"]) == sum(int(a) for _, a in want["buckets"])
        check(f"room {rid} state at slot {slot} equals the recorded state "
              f"(timestamps within {tol} s of block time)", not diffs or timing_only,
              ", ".join(f"{k}: chain {got[k]} vs record {want[k]}" for k in diffs), inconclusive=timing_only)

    # 5. decision
    if fbq:
        if dec['kind'] == 'new_room':
            curve = {k:cfg[k] for k in ('v_sol_lamports','v_tok','supply','graduation_trigger_lamports','fee_bps')}
            curve.update(sold=0, reserve=0, pending_reserve_sol=0, status=0)
        else:
            curve = rebuilt[int(dec['room_id'])]
        independently_quoted = first_buy_quote(curve, req['first_buy_lamports'])
        check('first-buy quote independently replays both curves in door tokens',
              independently_quoted == fbq['tokens'], str(independently_quoted))
    if 'max_room_price' in launch:
        # Historical signed messages used an absolute u128 price threshold.
        requested = req.get('max_room_price')
        if requested is None and fbq:
            slip = fbq['price_slippage_bps']
            expected_bound = (curve['v_sol_lamports'] * curve['v_tok'] * 10**18 * (10_000 + slip)
                              // ((curve['v_tok'] - curve['sold'])**2 * 10_000))
        else:
            expected_bound = int(requested or 0)
        field = 'max_room_price'
    else:
        requested = req.get('max_reserve_lamports')
        if requested is None and fbq:
            slip = fbq['reserve_slippage_bps']
            v_sol = curve['v_sol_lamports']
            threshold = isqrt((v_sol + curve['reserve'])**2 * (10_000 + slip) // 10_000) - v_sol
            expected_bound = min(curve['graduation_trigger_lamports'], max(1, threshold))
        else:
            expected_bound = int(requested or 0)
        field = 'max_reserve_lamports'
    check(f'Launch.{field} equals the requested or slippage-derived bound',
          launch[field] == expected_bound == int(record[f'launch_{field}']))
    expect = recompute(rm, rebuilt, holder, cfg, now, req["name"], req["symbol"], name_holder)
    def shifted(d):
        return {k: dict(v, last_trade_at=v["last_trade_at"] + d) for k, v in rebuilt.items()}
    robust = all(recompute(rm, shifted(d), holder, cfg, now, req["name"], req["symbol"], name_holder) == expect
                 for d in (-BLOCK_TIME_TOLERANCE, BLOCK_TIME_TOLERANCE))
    check(f"the recomputed decision does not depend on block-time precision (±{BLOCK_TIME_TOLERANCE} s)",
          robust, "the outcome changes within the tolerance: a liveness boundary", inconclusive=not robust)
    got = {"kind": dec["kind"], "rule": dec["rule"],
           "room_id": None if dec["kind"] == "new_room" else int(dec["room_id"]),
           "old_holder": None if dec["old_holder_room_id"] is None else int(dec["old_holder_room_id"]),
           "old_name_holder": (None if dec.get("old_name_holder_room_id") is None
                               else int(dec["old_name_holder_room_id"]))}
    check("independent recomputation agrees with the decision", expect == got,
          f"recomputed {expect}, recorded {got}")

    # 6. outcome
    landed = None
    target = dec["room"]
    for _, s in hist.signatures(target, 1 << 62):
        t = hist.tx(s)
        if record["id"] in t["transaction"]["signatures"]:
            landed = {"signature": s, "slot": t["slot"], "ok": t["meta"]["err"] is None, "err": t["meta"]["err"]}
            break
    return checks, landed


def main():
    rules.check_unicode()   # the verifier must fold with the same pinned Unicode tables as the service
    ap = argparse.ArgumentParser()
    ap.add_argument("decision_id")
    ap.add_argument("--rpc", required=True)
    ap.add_argument("--service")
    ap.add_argument("--db")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    chain_ok = True
    try:
        if a.db:
            st = Store(a.db)
            chain_ok = st.verify_chain()[0]
            row = st.get(a.decision_id)
        else:
            import httpx
            r = httpx.get(f"{a.service.rstrip('/')}/decision/{a.decision_id}", timeout=30)
            row = r.json() if r.status_code == 200 else None
        if row is None:
            print("decision not found")
            sys.exit(2)
        checks, landed = verify(row["record"], a.rpc, chain_ok)
    except (RpcError, OSError, KeyError, ValueError) as e:
        print(f"could not complete verification: {type(e).__name__}: {e}")
        sys.exit(2)
    failed = [c for c in checks if not c["ok"] and not c["inconclusive"]]
    unsure = [c for c in checks if c["inconclusive"]]
    verdict = "DISAGREE" if failed else ("INCONCLUSIVE" if unsure else "AGREE")
    if a.json:
        print(json.dumps({"decision_id": a.decision_id, "verdict": verdict, "agree": verdict == "AGREE",
                          "checks": checks, "landed": landed}, indent=1))
    else:
        for c in checks:
            tag = "PASS" if c["ok"] and not c["inconclusive"] else ("UNSURE" if c["inconclusive"] else "FAIL")
            print(f"{tag}  {c['check']}{'  [' + c['detail'] + ']' if c['detail'] and tag != 'PASS' else ''}")
        print(f"landed: {landed}")
        print(verdict)
    sys.exit({"AGREE": 0, "DISAGREE": 1, "INCONCLUSIVE": 2}[verdict])


if __name__ == "__main__":
    main()
