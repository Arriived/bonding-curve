"""Read and validate the immutable launch address table."""
import base64
from binascii import Error as Base64Error

from solders.address_lookup_table_account import AddressLookupTable, AddressLookupTableAccount
from solders.pubkey import Pubkey

from .chain import pda
from .txbuild import ATA, CLASSIC, SYSTEM, T22, WSOL

ALT_PROGRAM = Pubkey.from_string("AddressLookupTab1e1111111111111111111111111")
ACTIVE = (1 << 64) - 1


class LookupTableError(ValueError):
    pass


def expected_addresses(program):
    return [pda([b"config"], program), T22, CLASSIC, WSOL, ATA, SYSTEM]


def load_frozen_table(rpc, address, program):
    result = rpc.call("getAccountInfo", [str(address), {"encoding": "base64", "commitment": "finalized"}])
    try:
        account = result["value"]
        slot = result["context"]["slot"]
        if account is None or account["owner"] != str(ALT_PROGRAM) or account["executable"]:
            raise LookupTableError("launch lookup table is missing or has the wrong owner")
        data = base64.b64decode(account["data"][0], validate=True)
        state = AddressLookupTable.deserialize(data)
    except LookupTableError:
        raise
    except (KeyError, TypeError, ValueError, IndexError, Base64Error) as e:
        raise LookupTableError("invalid launch lookup table data") from e
    if state.meta.authority is not None or state.meta.deactivation_slot != ACTIVE:
        raise LookupTableError("launch lookup table must be frozen and active")
    if not isinstance(slot, int) or isinstance(slot, bool) or slot <= state.meta.last_extended_slot:
        raise LookupTableError("launch lookup table is still warming up")
    if list(state.addresses) != expected_addresses(program):
        raise LookupTableError("launch lookup table does not match the expected ordered addresses")
    return AddressLookupTableAccount(address, state.addresses), slot


def loaded_addresses(message, table):
    """Return the exact v0 runtime order for a launch that references the validated table."""
    lookups = message.address_table_lookups
    if len(lookups) != 1 or lookups[0].account_key != table.key:
        raise LookupTableError("expected one launch lookup table")
    lookup = lookups[0]
    try:
        return ([table.addresses[i] for i in lookup.writable_indexes],
                [table.addresses[i] for i in lookup.readonly_indexes])
    except IndexError as e:
        raise LookupTableError("launch lookup index is outside the table") from e
