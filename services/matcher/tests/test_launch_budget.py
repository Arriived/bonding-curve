"""The launch budget must include drift headroom in the signed transaction."""
import struct

import pytest
from solders.instruction import Instruction
from solders.pubkey import Pubkey

from matcher_service import config, txbuild


@pytest.mark.parametrize("override,expected", [(None, 500_000), ("600000", 600_000)])
def test_launch_budget_default_and_override_reach_the_message(monkeypatch, override, expected):
    env = {"MATCHER_RPC_URL": "https://rpc.invalid"}
    if override is not None:
        env["MATCHER_CU_LIMIT"] = override
    monkeypatch.setattr(config.os, "environ", env)
    cfg = config.load()
    assert cfg.cu_limit == expected
    payer = Pubkey.new_unique()
    launch = Instruction(Pubkey.new_unique(), b"launch", [])
    message = txbuild.build_message(launch, payer, "11111111111111111111111111111111",
                                    cfg.cu_limit, 10_000)
    assert bytes(message.instructions[0].data) == b"\x02" + struct.pack("<I", expected)
