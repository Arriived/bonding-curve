"""Offline target identity, pinned with its interface; this is not a deployment claim."""
import json
from pathlib import Path

PROGRAM_ID = json.loads((Path(__file__).resolve().parents[1] / 'idl/doors_v1.paired.json')
                        .read_text(encoding='utf-8'))['address']
