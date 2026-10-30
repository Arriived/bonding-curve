"""Validate Phase 1 evidence and arithmetic using the unmodified legacy ledger.

This is not an A-D model implementation or an economic Monte Carlo experiment.
Run from the repository root with its existing Python environment.
"""
from datetime import datetime, timezone
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from bonding_lab.engine import Curve, Parameters, precise  # noqa: E402


@precise
def arithmetic_witnesses():
    def market():
        curve = Curve(Parameters(p0=".01", k=".0001", coupling="0", fee_rate="0"))
        curve.create_token("EXAMPLE")
        for name in ("alice", "bob", "attacker", "victim"):
            curve.create_wallet(name, 1000)
        return curve

    curve = market()
    curve.execute("alice", 0, 500, "buy")
    curve.execute("bob", 0, 500, "buy")
    reserve = curve.reserve
    cap = curve.price(0) * curve.supplies[0]
    terminal_each = reserve / 2
    d = Decimal(".05") * curve.price(0) / curve.params.k
    depth, _ = curve.quote(0, d, "sell")
    first = curve.execute("alice", 0, 500, "sell").gross
    second = curve.execute("bob", 0, 500, "sell").gross
    curve.assert_invariants()
    assert (reserve, cap, terminal_each, first, second, depth) == (
        Decimal("60"), Decimal("110"), Decimal("30"),
        Decimal("42.5"), Decimal("17.5"), Decimal("5.89875"))
    assert curve.reserve == 0 and first + second == reserve

    control = market()
    control.execute("alice", 0, 1000, "buy")
    victim_control = control.execute("victim", 0, 1000, "buy").gross
    control.assert_invariants()
    attacked = market()
    attacked.execute("alice", 0, 1000, "buy")
    starting_cash = attacked.wallets["attacker"].cash
    outlay = attacked.execute("attacker", 0, 1000, "buy").gross
    victim_attacked = attacked.execute("victim", 0, 1000, "buy").gross
    proceeds = attacked.execute("attacker", 0, 1000, "sell").gross
    profit = attacked.wallets["attacker"].cash - starting_cash
    attacked.assert_invariants()
    assert (outlay, proceeds, profit, victim_attacked - victim_control) == (
        Decimal("160"), Decimal("260"), Decimal("100"), Decimal("100"))
    assert attacked.wallets["attacker"].holdings[0] == 0

    low, high = Fraction(2, 5), Fraction(3, 5)
    threshold = low / high
    threshold_with_loss = (low + Fraction(1, 10)) / high
    assert threshold == Fraction(2, 3) and threshold_with_loss == Fraction(5, 6)
    assert Fraction(1, 2) * high - low == -Fraction(1, 10)

    return {
        "scope": "Exact analytical examples, zero fees/costs, abstract quote units; not research outcome estimates",
        "reserve_vs_cap": {"reserve": str(reserve), "market_cap": str(cap)},
        "terminal_vs_early_exit": {"terminal_each": str(terminal_each),
                                   "early": str(first), "late": str(second)},
        "sell_depth_5pct": str(depth),
        "migration_ordering": {"attacker_outlay": str(outlay),
                               "attacker_proceeds": str(proceeds),
                               "complete_exit_profit": str(profit),
                               "victim_extra_cost": str(victim_attacked - victim_control)},
        "illustrative_acceptance_thresholds": [str(threshold), str(threshold_with_loss)],
    }


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    failures = []
    manifest = json.loads((OUT / "preservation_manifest.json").read_text(encoding="utf-8"))
    for name, row in manifest["files"].items():
        path = ROOT / name
        if not path.is_file() or digest(path) != row["sha256"]:
            failures.append(f"Original file changed or missing: {name}")

    docs = ("PRIOR_ART.md", "MECHANISM_DESIGNS.md", "ECONOMIC_INVARIANTS.md", "RESEARCH_PLAN.md")
    for name in docs:
        path = ROOT / name
        content = path.read_text(encoding="utf-8")
        if len(content.split()) < 500:
            failures.append(f"Document unexpectedly incomplete: {name}")
        if content.count("```") % 2:
            failures.append(f"Unclosed code fence: {name}")
        for target in re.findall(r"\]\(([^)]+)\)", content):
            if target.startswith(("https://", "http://", "#")):
                continue
            local = unquote(target.split("#", 1)[0])
            if not (path.parent / local).exists():
                failures.append(f"Missing local link in {name}: {target}")

    baseline_path = OUT / "baseline_pytest.xml"
    baseline = {}
    if not baseline_path.exists():
        failures.append("Existing-suite baseline XML missing")
    else:
        suites = list(ET.parse(baseline_path).getroot().iter("testsuite"))
        baseline = {key: sum(int(s.attrib.get(key, 0)) for s in suites)
                    for key in ("tests", "failures", "errors", "skipped")}
        baseline["passed"] = baseline["tests"] - sum(baseline[k] for k in ("failures", "errors", "skipped"))
        baseline["duration_seconds"] = sum(float(s.attrib.get("time", 0)) for s in suites)
        baseline["xml_sha256"] = digest(baseline_path)
        if baseline["tests"] == 0 or baseline["failures"] or baseline["errors"] or baseline["skipped"]:
            failures.append(f"Baseline gate failed: {baseline}")
        run_path = OUT / "baseline_run.json"
        if not run_path.exists() or json.loads(run_path.read_text(encoding="utf-8")).get("exit_code") != 0:
            failures.append("Baseline runner did not finish successfully")
        (OUT / "baseline_summary.json").write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")

    probe = json.loads((OUT / "data_access_probe.json").read_text(encoding="utf-8"))
    if probe["paid_spend"] != 0 or probe["calibrated_parameters"]:
        failures.append("Data probe exceeds documented scope")
    for request in probe["requests"]:
        if request["status"] == "snapshot_only":
            if digest(OUT / request["raw_response"]) != request["response_sha256"]:
                failures.append(f"Data snapshot hash mismatch: {request['query']}")

    witnesses = arithmetic_witnesses()
    result = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not failures else "failed",
        "phase": "Phase 1 only; no new A-D simulation engine executed",
        "original_files_verified": len(manifest["files"]),
        "existing_test_baseline": baseline,
        "document_sha256": {name: digest(ROOT / name) for name in docs},
        "phase1_script_sha256": {path.name: digest(path) for path in sorted(OUT.glob("*.py"))},
        "preservation_manifest_sha256": digest(OUT / "preservation_manifest.json"),
        "arithmetic_witnesses": witnesses,
        "data_status": {r["query"]: r["status"] for r in probe["requests"]},
        "failures": failures,
    }
    (OUT / "phase1_validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
