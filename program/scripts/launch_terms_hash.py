"""Print the signed create_room economic commitment from decoded Config JSON.

Accepts exact JSON integers or decimal strings; no RPC, signing or dependencies.
"""
import argparse
import hashlib
import json
from pathlib import Path

FIELDS = (
    ("v_sol_lamports", 8),
    ("v_tok", 8),
    ("supply", 8),
    ("r_star_lamports", 8),
    ("graduation_trigger_lamports", 8),
    ("fee_bps", 2),
    ("door_share_bps", 2),
    ("founder_share_bps", 2),
)


def launch_terms_hash(config):
    encoded = bytearray(b"doors-v1:launch-terms:v1")
    for name, width in FIELDS:
        value = config[name]
        if type(value) is not int and not (
            isinstance(value, str) and value.isascii() and value.isdecimal()
        ):
            raise ValueError(f"{name} must be an exact nonnegative integer")
        encoded.extend(int(value).to_bytes(width, "little", signed=False))
    return hashlib.sha256(encoded).digest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="Decoded Config or Settings JSON")
    args = parser.parse_args()
    digest = launch_terms_hash(json.loads(args.config.read_text(encoding="utf-8")))
    print(json.dumps({"expected_terms_hash": list(digest), "hex": digest.hex()}, indent=2))


if __name__ == "__main__":
    main()
