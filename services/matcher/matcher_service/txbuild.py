"""Build the launch transaction the matcher co-signs.

The deployed program does not verify a detached "decision" message. It requires the matcher authority
to be a *signer of the launch transaction itself* (`matcher: Signer` in CreateRoom/OpenDoor) and
requires the launch instruction to be top level. So the decision the matcher signs is the entire
transaction message:

  - the launcher's pubkey (fee payer and `user`),
  - the metadata, first buy, slippage and fee cap (`Launch` instruction data),
  - the routing (`create_room` + room-id nonce, or `open_door` into a specific room with a signed door nonce,
    and the SlugLock / old-holder accounts),
  - the compute budget and optional priority fee,
  - and a recent blockhash, which is the expiry: the runtime rejects the transaction once the
    blockhash is older than 150 slots (`MAX_PROCESSING_AGE`). The service only ever builds messages
    from a recent blockhash and never with a durable-nonce advance instruction, which would remove
    that expiry.

Instruction layouts come from idl/doors_v1.deployed.json, the IDL of the deployed program.
"""
import json
import os
import struct

from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.message import Message, MessageV0
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import Transaction, VersionedTransaction

from .chain import pda

IDL_PATH = os.path.join(os.path.dirname(__file__), "..", "idl", "doors_v1.deployed.json")
T22 = Pubkey.from_string("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")
CLASSIC = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
WSOL = Pubkey.from_string("So11111111111111111111111111111111111111112")
ATA = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
SYSTEM = Pubkey.from_string("11111111111111111111111111111111")
PACKET_LIMIT = 1232


class TxTooLarge(Exception):
    pass


def load_idl(path=IDL_PATH):
    with open(path) as f:
        return json.load(f)


def _flatten(accounts, prefix=""):
    for a in accounts:
        if "accounts" in a:
            yield from _flatten(a["accounts"], prefix + a["name"] + ".")
        else:
            yield prefix + a["name"], a


def _borsh_str(s):
    b = s.encode()
    return struct.pack("<I", len(b)) + b


MAX_LAUNCH_WINDOW_SLOTS = 150  # programs/doors_v1/src/state.rs; the runtime's blockhash window


def encode_launch(name, symbol, uri, first_buy, min_tokens_out, matcher_version, rule, face, max_fee,
                  terms_hash: bytes, door_nonce, expires_at_slot):
    if len(terms_hash) != 32:
        raise ValueError("expected_terms_hash must be 32 bytes")
    return (_borsh_str(name) + _borsh_str(symbol) + _borsh_str(uri)
            + struct.pack("<QQHBIQ", first_buy, min_tokens_out, matcher_version, rule, face, max_fee)
            + terms_hash + struct.pack("<QQ", door_nonce, expires_at_slot))


def ata(owner, mint, program):
    return Pubkey.find_program_address([bytes(owner), bytes(program), bytes(mint)], ATA)[0]


class Builder:
    def __init__(self, program_id, idl=None):
        self.program = Pubkey.from_string(program_id)
        self.idl = idl or load_idl()
        if self.idl["address"] != program_id:
            raise ValueError(f"IDL address {self.idl['address']} != program {program_id}")
        self.ix = {i["name"]: i for i in self.idl["instructions"]}

    def p(self, *seeds):
        return pda(list(seeds), str(self.program))

    def _instruction(self, name, values, data):
        spec = self.ix[name]
        metas = []
        for path, a in _flatten(spec["accounts"]):
            key = values.get(path)
            if key is None and a.get("optional"):
                metas.append(AccountMeta(self.program, False, False))  # Anchor's "None" placeholder
                continue
            if key is None and "address" in a:
                key = Pubkey.from_string(a["address"])
            if key is None:
                raise ValueError(f"{name}: no value for account {path}")
            metas.append(AccountMeta(key, bool(a.get("signer")), bool(a.get("writable"))))
        return Instruction(self.program, bytes(spec["discriminator"]) + data, metas)

    def room_accounts(self, room_id):
        room = self.p(b"room", struct.pack("<Q", room_id))
        return room, {
            "reserve": self.p(b"reserve", bytes(room)), "fees": self.p(b"fees", bytes(room)),
            "room_mint": self.p(b"room_mint", bytes(room)), "room_vault": self.p(b"room_vault", bytes(room)),
            "retired": self.p(b"retired", bytes(room)),
        }

    def door_accounts(self, room, nonce):
        """Door PDAs are seeded by the signed door nonce (0 for door 0), never by door_count."""
        n = struct.pack("<Q", nonce)
        door = self.p(b"door", bytes(room), n)
        mint = self.p(b"door_mint", bytes(room), n)
        return {"door": door, "door_mint": mint, "door_vault": self.p(b"door_vault", bytes(door)),
                "backing": self.p(b"door_room_vault", bytes(door))}

    def create_room_ix(self, user, matcher, room_id, identity, old_holder_room_id, launch_data,
                       name_key: bytes | None = None, old_name_holder_room_id=None):
        """`name_key`: the NameLock key (rules.name_lock_key), or None for a launch without one."""
        if name_key is not None and len(name_key) != 16:
            raise ValueError("name_key must be 16 bytes")
        if name_key is None and old_name_holder_room_id is not None:
            raise ValueError("an old name holder needs a name key")
        room, r = self.room_accounts(room_id)
        d = self.door_accounts(room, 0)
        values = {"user": user, "matcher": matcher, "config": self.p(b"config"), "room": room,
                  "grad_payer": self.p(b"grad_payer", bytes(room)), "slug": self.p(b"slug", identity),
                  "fee_wsol": self.p(b"fee_wsol", bytes(room)), "user_token": ata(user, d["door_mint"], T22),
                  "old_holder": (None if old_holder_room_id is None
                                 else self.p(b"room", struct.pack("<Q", old_holder_room_id))),
                  "name_lock": None if name_key is None else self.p(b"name", name_key),
                  "old_name_holder": (None if old_name_holder_room_id is None
                                      else self.p(b"room", struct.pack("<Q", old_name_holder_room_id))),
                  **r, **d}
        data = struct.pack("<Q", room_id) + launch_data + (b"\x00" if name_key is None else b"\x01" + name_key)
        return self._instruction("create_room", values, data), room, d

    def open_door_ix(self, user, matcher, room_id, door_nonce, identity, old_holder_room_id, launch_data):
        room, r = self.room_accounts(room_id)
        d = self.door_accounts(room, door_nonce)
        values = {"user": user, "matcher": matcher, "core.config": self.p(b"config"), "core.room": room,
                  **{"core." + k: v for k, v in r.items()}, "slug": self.p(b"slug", identity),
                  "user_token": ata(user, d["door_mint"], T22),
                  "old_holder": (None if old_holder_room_id is None
                                 else self.p(b"room", struct.pack("<Q", old_holder_room_id))),
                  **d}
        return self._instruction("open_door", values, launch_data), room, d


def build_message(launch_ix, payer, blockhash, cu_limit, cu_price, lookup_table=None):
    ixs = [set_compute_unit_limit(cu_limit)]
    if cu_price:
        ixs.append(set_compute_unit_price(cu_price))
    ixs.append(launch_ix)
    if lookup_table is not None:
        return MessageV0.try_compile(payer, ixs, [lookup_table], Hash.from_string(blockhash))
    return Message.new_with_blockhash(ixs, payer, Hash.from_string(blockhash))


def wire_size(message):
    signatures = [Signature.default()] * message.header.num_required_signatures
    return len(bytes(VersionedTransaction.populate(message, signatures)))


def assemble(message, matcher_pubkey, matcher_signature: bytes):
    """Wire transaction with the matcher's signature in place and the launcher's slot empty."""
    signers = list(message.account_keys[: message.header.num_required_signatures])
    sigs = [Signature.default()] * len(signers)
    sigs[signers.index(matcher_pubkey)] = Signature.from_bytes(matcher_signature)
    tx_type = VersionedTransaction if isinstance(message, MessageV0) else Transaction
    tx = tx_type.populate(message, sigs)
    wire = bytes(tx)
    if len(wire) > PACKET_LIMIT:
        raise TxTooLarge(f"transaction is {len(wire)} bytes > {PACKET_LIMIT}; shorten the metadata")
    return tx, wire
