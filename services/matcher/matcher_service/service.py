"""The /route pipeline. Every failure path raises Refusal; nothing falls back to a default routing.

  1. freshness: a snapshot inside the budget (one synchronous refresh is attempted; RPC failure refuses)
  2. key check: signer pubkey == Config.matcher_authority in that snapshot
  3. decide (pure, from the snapshot)
  4. build the transaction from a fresh blockhash, check its size with placeholder signatures
  5. sign (KMS or dev keyfile); signature verified against the key before use; the same snapshot is re-checked
     against the freshness budget after signing, and a stale decision is refused unreleased
  6. persist the decision record; only then return the partially signed transaction
"""
import base64
import hashlib
import os
import struct
import time

from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import Transaction

from . import __version__, quote, rules, txbuild
from .chain import RpcError, StaleState
from .decide import RULE_CODE, Refusal, decide
from .layouts import LayoutError
from .signer import SignerUnavailable


def _u64(name, v, lo=0):
    if not isinstance(v, int) or isinstance(v, bool) or not lo <= v < 2 ** 64:
        raise Refusal("invalid_request", f"{name} must be an integer in [{lo}, 2^64)")
    return v


def room_view(room):
    """The room state a decision depends on, as recorded for audit."""
    return {"room_id": room["room_id"], "pubkey": room["pubkey"], "status": room["status"],
            "created_at": room["created_at"], "reserve": room["reserve"], "last_trade_at": room["last_trade_at"],
            "volume_gross": str(room["volume_gross"]), "door_count": room["door_count"],
            "identity": room["identity"],
            "buckets": [[s, str(a)] for s, a in room["buckets"] if s or a], "faces": room["faces"]}


class Service:
    def __init__(self, cfg, rpc, chain, signer, store, builder, log, metrics):
        rules.check_unicode()   # name keys are permanent on-chain: never compute them on other Unicode tables
        self.cfg, self.rpc, self.chain, self.signer = cfg, rpc, chain, signer
        self.store, self.builder, self.log, self.metrics = store, builder, log, metrics

    # -- readiness -------------------------------------------------------------------------------
    def health(self):
        out = {"version": __version__, "program": self.cfg.program_id, "signer_backend": self.signer.backend}
        try:
            out["matcher_pubkey"] = str(self.signer.pubkey)
        except Exception as e:  # noqa: BLE001 - health reports, never raises
            out["matcher_pubkey"] = None
            out["signer_error"] = str(e)
        snap = self.chain.current()
        if snap is None:
            out.update(ready=False, reason="no snapshot yet")
            return out
        out["snapshot"] = snap.summary()
        try:
            out["freshness"] = snap.check_fresh(self.rpc.slot(), self.cfg.budget)
        except (StaleState, RpcError) as e:
            out.update(ready=False, reason=str(e))
            return out
        if out["matcher_pubkey"] != snap.config["matcher_authority"]:
            out.update(ready=False, reason=f"signer key {out['matcher_pubkey']} != Config.matcher_authority "
                                           f"{snap.config['matcher_authority']}")
            return out
        out["ready"] = True
        return out

    # -- route -----------------------------------------------------------------------------------
    def _fresh_snapshot(self):
        try:
            cluster_slot = self.rpc.slot()
        except RpcError as e:
            raise Refusal("rpc_unavailable", f"cannot read the cluster slot: {e}", 503)
        snap = self.chain.current()
        try:
            if snap is None:
                raise StaleState("no snapshot")
            return snap, snap.check_fresh(cluster_slot, self.cfg.budget), cluster_slot
        except StaleState:
            pass
        try:
            snap = self.chain.refresh()
            cluster_slot = self.rpc.slot()
            return snap, snap.check_fresh(cluster_slot, self.cfg.budget), cluster_slot
        except RpcError as e:
            raise Refusal("rpc_unavailable", f"cannot refresh room state: {e}", 503)
        except LayoutError as e:
            raise Refusal("inconsistent_state", f"room state failed validation: {e}", 503)
        except StaleState as e:
            raise Refusal("stale_state", f"room state outside the freshness budget: {e}", 503)

    def _signing_freshness(self, snap):
        # RPC retries, a queued worker or KMS latency can use up the budget
        # after routing. Check this same decision snapshot again; refreshing
        # here would leave a decision computed from different state.
        try:
            slot = self.rpc.slot()
            return snap.check_fresh(slot, self.cfg.budget), slot
        except RpcError as e:
            raise Refusal("rpc_unavailable", f"cannot check signing-time freshness: {e}", 503)
        except StaleState as e:
            raise Refusal("stale_state", f"room state expired during signing: {e}", 503)

    def route(self, req):
        t0 = time.monotonic()
        try:
            out = self._route(req)
            self.metrics.inc("matcher_decisions_total", kind=out["decision"]["kind"], rule=out["decision"]["rule"])
            return out
        except Refusal as r:
            self.metrics.inc("matcher_refusals_total", code=r.code)
            raise
        finally:
            self.metrics.observe(time.monotonic() - t0)

    def _route(self, req):
        try:
            launcher = Pubkey.from_string(str(req.get("launcher", "")))
        except ValueError:
            raise Refusal("invalid_request", "launcher must be a base58 public key")
        name, symbol, uri = req.get("name"), req.get("symbol"), req.get("uri", "")
        if not all(isinstance(x, str) for x in (name, symbol, uri)):
            raise Refusal("invalid_request", "name, symbol and uri must be strings")
        try:  # JSON admits lone surrogates ("\ud800"), which have no UTF-8 encoding
            for x in (name, symbol, uri):
                x.encode("utf-8")
        except UnicodeEncodeError:
            raise Refusal("invalid_metadata", "name, symbol and uri must be valid Unicode (no lone surrogates)")
        first_buy = _u64("first_buy_lamports", req.get("first_buy_lamports", 0))
        # min_tokens_out: omitted -> the snapshot quote less max_slippage_bps (default 2%); an explicit
        # 0 with a first buy is refused, so no launch buy is signed without a price limit (M-4).
        req_min_out = req.get("min_tokens_out")
        min_out = None if req_min_out is None else _u64("min_tokens_out", req_min_out)
        slippage = _u64("max_slippage_bps", req.get("max_slippage_bps", quote.DEFAULT_MAX_SLIPPAGE_BPS))
        if not 1 <= slippage <= quote.MAX_SLIPPAGE_BPS:
            raise Refusal("invalid_request", f"max_slippage_bps must be in [1, {quote.MAX_SLIPPAGE_BPS}]")
        if first_buy > 0 and min_out == 0:
            raise Refusal("invalid_request", "min_tokens_out must be > 0 when first_buy_lamports > 0; "
                                             "omit it to use the quoted price less max_slippage_bps")
        max_fee = _u64("max_fee_lamports", req.get("max_fee_lamports", 0))
        cu_price = _u64("cu_price_micro_lamports", req.get("cu_price_micro_lamports", 0))
        if cu_price > self.cfg.max_cu_price:
            raise Refusal("invalid_request", f"cu_price_micro_lamports above {self.cfg.max_cu_price}")

        snap, freshness, cluster_slot = self._fresh_snapshot()
        try:
            matcher = self.signer.pubkey
        except SignerUnavailable as e:
            raise Refusal("signer_unavailable", str(e), 503)
        except Exception as e:  # noqa: BLE001
            raise Refusal("signer_unavailable", f"{type(e).__name__}: {e}", 503)
        if str(matcher) != snap.config["matcher_authority"]:
            raise Refusal("signer_mismatch", f"signer key {matcher} is not Config.matcher_authority "
                                             f"{snap.config['matcher_authority']}", 503)
        fee_needed = snap.config["door_fee_lamports"] + snap.config["room_fee_lamports"]
        d = decide(snap, name, symbol, uri)
        if fee_needed > max_fee and d.kind == "new_room":
            raise Refusal("fee_limit", f"room+door fee {fee_needed} > max_fee_lamports {max_fee}")
        if snap.config["door_fee_lamports"] > max_fee and d.kind == "door":
            raise Refusal("fee_limit", f"door fee {snap.config['door_fee_lamports']} > max_fee_lamports {max_fee}")
        first_buy_quote = None
        requested_reserve = req.get('max_reserve_lamports')
        if requested_reserve is not None:
            try:
                if isinstance(requested_reserve, bool) or not isinstance(requested_reserve, (str, int)):
                    raise ValueError()
                max_reserve_lamports = int(requested_reserve)
                if not 0 <= max_reserve_lamports < 2**64 or str(max_reserve_lamports) != str(requested_reserve):
                    raise ValueError()
            except ValueError:
                raise Refusal('invalid_request', 'max_reserve_lamports must be a decimal u64 (0 disables the bound)')
        else:
            max_reserve_lamports = 0
        if first_buy > 0:
            curve = quote.new_room_curve(snap.config) if d.kind == "new_room" else snap.rooms[d.room_id]
            try:
                tokens = quote.first_buy_tokens(curve, first_buy)
            except ValueError:
                tokens = None
            if not tokens:
                raise Refusal("first_buy_unfillable", "the room cannot fill this first buy at the snapshot "
                                                      "(capped, complete or zero tokens)")
            if min_out is None:
                min_out = quote.min_out(tokens, slippage)
            if requested_reserve is None:
                max_reserve_lamports = quote.room_reserve_limit(curve, slippage)
            first_buy_quote = {"tokens": tokens, "max_slippage_bps": slippage if req_min_out is None else None,
                               "min_tokens_out": min_out, "snapshot_slot": snap.slot,
                               "curve": {k:curve[k] for k in ('v_sol_lamports','v_tok','supply',
                                   'graduation_trigger_lamports','fee_bps','sold','reserve','pending_reserve_sol','status')},
                               "max_reserve_lamports": str(max_reserve_lamports), "reserve_slippage_bps": slippage}
        elif min_out is None:
            min_out = 0

        try:
            blockhash, last_valid, bh_slot = self.rpc.latest_blockhash()
            height = self.rpc.block_height()
        except RpcError as e:
            raise Refusal("rpc_unavailable", f"cannot read a recent blockhash: {e}", 503)

        identity = bytes.fromhex(d.identity)
        if d.kind == "new_room":
            # No in-flight reservation: two concurrent new-room decisions for one name key or identity can
            # both be signed, and the program lets at most one land (NameLock / SlugLock, created atomically
            # with the room). The other fails on-chain; re-requesting then routes it as a door.
            room_id = self._fresh_nonce(snap)
            door_nonce = 0          # door 0 is always at nonce 0
        else:
            room_id = d.room_id
            door_nonce = self._door_nonce()   # random: concurrent doors into one room never contend
        # Explicit expiry, inside the program's 150-slot window and no later than the blockhash
        # (slots advance at least as fast as block heights, so bh_slot + 150 <= the blockhash's last slot).
        expires_at_slot = bh_slot + txbuild.MAX_LAUNCH_WINDOW_SLOTS

        launch = txbuild.encode_launch(name, symbol, uri, first_buy, min_out, self.cfg.matcher_version,
                                       RULE_CODE[d.rule], d.face, max_fee,
                                       bytes.fromhex(snap.config["launch_terms_hash"]), door_nonce, expires_at_slot,
                                       max_reserve_lamports)
        if d.kind == "new_room":
            ix, room_pk, door = self.builder.create_room_ix(
                launcher, matcher, room_id, identity, d.old_holder_room_id, launch,
                bytes.fromhex(d.name_key) if d.name_key else None, d.old_name_holder_room_id)
        else:
            ix, room_pk, door = self.builder.open_door_ix(launcher, matcher, room_id, door_nonce, identity,
                                                          d.old_holder_room_id, launch)
        message = txbuild.build_message(ix, launcher, blockhash, self.cfg.cu_limit, cu_price)
        placeholder = len(bytes(Transaction.populate(message, [Signature.default()] *
                                                      message.header.num_required_signatures)))
        if placeholder > txbuild.PACKET_LIMIT:
            raise Refusal("tx_too_large", f"transaction would be {placeholder} bytes > {txbuild.PACKET_LIMIT}; "
                                          "shorten the metadata (v0 lookup tables are not supported in v1)", 413)
        msg_bytes = bytes(message)
        freshness, cluster_slot = self._signing_freshness(snap)
        try:
            sig = self.signer.sign(msg_bytes)
        except SignerUnavailable as e:
            raise Refusal("signer_unavailable", str(e), 503)
        # Re-check the snapshot the decision was taken on: building and signing (a KMS round trip) take time, and a
        # transaction decided on state that has since left the freshness budget must not be released. The signature
        # is discarded unrecorded; nothing has been returned, so nothing can land.
        try:
            freshness_after = snap.check_fresh(self.rpc.slot(), self.cfg.budget)
        except RpcError as e:
            raise Refusal("rpc_unavailable", f"cannot re-read the cluster slot after signing: {e}", 503)
        except StaleState as e:
            raise Refusal("stale_state", f"room state left the freshness budget while signing: {e}", 503)
        tx, wire = txbuild.assemble(message, matcher, sig)
        decision_id = str(Signature.from_bytes(sig))

        considered = {r["room_id"] for r in d.evaluated}
        if d.old_holder_room_id is not None:
            considered.add(d.old_holder_room_id)
        if d.old_name_holder_room_id is not None:
            considered.add(d.old_name_holder_room_id)
        all_rooms = sorted(r["pubkey"] for r in snap.rooms.values())
        record = {
            "id": decision_id,
            "service": {"version": __version__, "matcher_version": self.cfg.matcher_version,
                        "unicode": rules.UNICODE_VERSION, "signer_backend": self.signer.backend},
            "program": self.cfg.program_id, "config_account": snap.config_key, "config": snap.config,
            "request": {"launcher": str(launcher), "name": name, "symbol": symbol, "uri": uri,
                        "first_buy_lamports": first_buy, "min_tokens_out": req_min_out,
                        "max_slippage_bps": req.get("max_slippage_bps"), "max_fee_lamports": max_fee,
                        "cu_price_micro_lamports": cu_price,
                        "max_reserve_lamports": None if requested_reserve is None else str(max_reserve_lamports)},
            "launch_max_reserve_lamports": str(max_reserve_lamports),
            "first_buy_quote": first_buy_quote,
            "launch_min_tokens_out": min_out,
            "state": {"slots": snap.slots, "slot": snap.slot, "clock_unix": snap.clock_unix,
                      "cluster_slot_at_decision": cluster_slot, "freshness": freshness,
                      "freshness_after_signing": freshness_after, "budget": vars(self.cfg.budget),
                      "rooms_total": len(all_rooms),
                      "rooms_digest": hashlib.sha256("\n".join(all_rooms).encode()).hexdigest(),
                      "rooms": [room_view(snap.rooms[i]) for i in sorted(considered)]},
            "decision": {"kind": d.kind, "rule": d.rule, "rule_code": RULE_CODE[d.rule], "room_id": str(room_id),
                         "room": str(room_pk), "door_nonce": str(door_nonce), "door": str(door["door"]),
                         "door_mint": str(door["door_mint"]), "face": d.face,
                         "old_holder_room_id": None if d.old_holder_room_id is None else str(d.old_holder_room_id),
                         "identity": d.identity, "slug_lock": snap.slug_pda(d.identity),
                         "name_key": d.name_key or None,
                         "name_lock": snap.name_pda(d.name_key) if d.name_key else None,
                         "old_name_holder_room_id": (None if d.old_name_holder_room_id is None
                                                     else str(d.old_name_holder_room_id)),
                         "candidate_keys": d.candidate_keys, "evaluated": d.evaluated},
            "transaction": {"message_base64": base64.b64encode(msg_bytes).decode(), "blockhash": blockhash,
                            "blockhash_slot": bh_slot, "expires_at_slot": expires_at_slot,
                            "last_valid_block_height": last_valid,
                            "block_height_at_signing": height, "matcher": str(matcher),
                            "matcher_signature": decision_id},
        }
        try:
            record_hash = self.store.append(decision_id, str(launcher), d.kind, record)
        except Exception as e:  # noqa: BLE001 - an unrecorded decision is never released
            raise Refusal("store_unavailable", f"decision could not be persisted: {type(e).__name__}", 503)
        self.log.info("decision", extra={"fields": {"id": decision_id, "kind": d.kind, "rule": d.rule,
                                                    "room_id": str(room_id), "slot": snap.slot,
                                                    "launcher": str(launcher)}})
        return {"id": decision_id, "record_sha256": record_hash, "decision": record["decision"],
                "state_slot": snap.slot, "transaction_base64": base64.b64encode(wire).decode(),
                "last_valid_block_height": last_valid, "expires_at_slot": expires_at_slot,
                "instructions": "sign as the fee payer (signature slot 0) and submit before "
                                "last_valid_block_height and expires_at_slot; any change to the transaction "
                                "invalidates the matcher signature"}

    def _door_nonce(self):
        while True:
            n = struct.unpack("<Q", os.urandom(8))[0]
            if n:
                return n

    def _fresh_nonce(self, snap):
        for _ in range(16):
            nonce = struct.unpack("<Q", os.urandom(8))[0]
            if nonce not in snap.rooms:
                return nonce
        raise Refusal("nonce_exhausted", "could not draw an unused room nonce", 503)
