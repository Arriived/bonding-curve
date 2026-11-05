"""Capture the deployed SPL programs and loader owners at a finalized RPC slot."""
import argparse
import base64
import hashlib
import json
import urllib.request
from pathlib import Path

PROGRAMS = {
    "token-2022": "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",
    "spl-token": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    "ata": "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",
}
UPGRADEABLE = "BPFLoaderUpgradeab1e11111111111111111111111"
LOADERS = {UPGRADEABLE, "BPFLoader2111111111111111111111111111111111",
           "BPFLoader1111111111111111111111111111111111"}
BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58(raw):
    number = int.from_bytes(raw, "big")
    digits = []
    while number:
        number, remainder = divmod(number, 58)
        digits.append(BASE58[remainder])
    return "1" * (len(raw) - len(raw.lstrip(b"\0"))) + "".join(reversed(digits))


def accounts(rpc_url, keys, minimum_slot=None):
    config = {"encoding": "base64", "commitment": "finalized"}
    if minimum_slot is not None:
        config["minContextSlot"] = minimum_slot
    body = {"jsonrpc": "2.0", "id": 1, "method": "getMultipleAccounts", "params": [keys, config]}
    request = urllib.request.Request(rpc_url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if "error" in payload:
        raise RuntimeError(f"getMultipleAccounts: {payload['error']}")
    result = payload["result"]
    if len(result["value"]) != len(keys) or any(value is None for value in result["value"]):
        raise RuntimeError("RPC omitted a required deployed account")
    return result["context"]["slot"], dict(zip(keys, result["value"]))


def account_bytes(account):
    return base64.b64decode(account["data"][0], validate=True)


def executable_source(key, account):
    if not account["executable"] or account["owner"] not in LOADERS:
        raise RuntimeError(f"unexpected executable or loader for {key}")
    if account["owner"] != UPGRADEABLE:
        return key
    data = account_bytes(account)
    if len(data) != 36 or data[:4] != b"\x02\0\0\0":
        raise RuntimeError(f"{key} does not contain an upgradeable Program state")
    return b58(data[4:])


def capture(rpc_url, out):
    keys = list(PROGRAMS.values())
    discovery_slot, discovery = accounts(rpc_url, keys)
    sources = {key: executable_source(key, discovery[key]) for key in keys}
    slot, snapshot = accounts(rpc_url, list(dict.fromkeys(keys + list(sources.values()))), discovery_slot)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"context_slot": slot, "discovery_slot": discovery_slot, "commitment": "finalized", "programs": {}}
    for name, key in PROGRAMS.items():
        program = snapshot[key]
        source = executable_source(key, program)
        if source != sources[key]:
            raise RuntimeError(f"ProgramData changed for {key} during capture")
        account = snapshot[source]
        data = account_bytes(account)
        deployed_slot = None
        if source != key:
            if account["owner"] != UPGRADEABLE or account["executable"] or data[:4] != b"\x03\0\0\0":
                raise RuntimeError(f"{source} does not contain the expected ProgramData")
            deployed_slot = int.from_bytes(data[4:12], "little")
            data = data[45:]  # Upgradeable loader ProgramData metadata width
        if not data.startswith(b"\x7fELF"):
            raise RuntimeError(f"{source} does not contain an ELF")
        (out / f"{name}.so").write_bytes(data)
        manifest["programs"][name] = {"address": key, "loader": program["owner"],
                                       "executable_account": source, "deployed_slot": deployed_slot,
                                       "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rpc", default="https://api.devnet.solana.com")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(capture(args.rpc, args.out), indent=2))


if __name__ == "__main__":
    main()
