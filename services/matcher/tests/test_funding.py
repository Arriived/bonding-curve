"""Compare the funds check with actual account sizes created by the compiled program."""
import json
from pathlib import Path

import pytest

from matcher_service.funding import creation_rent_sizes


def test_rent_budget_covers_the_compiled_programs_actual_accounts():
    path = Path(__file__).resolve().parents[3] / "program/verification/launch_rent_accounts.json"
    if not path.exists():
        pytest.skip("run the compiled SBF regression first; CI requires this artifact")
    measured = json.loads(path.read_text())
    budgeted = creation_rent_sizes(measured["name"], measured["symbol"], measured["uri"],
                                  measured["room"], measured["program"], measured["first_buy"])
    assert sorted(budgeted) == measured["sizes"]
