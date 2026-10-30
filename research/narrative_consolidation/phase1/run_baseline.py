"""Run the unchanged test suite with workspace-local temporary files and logs."""
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import sys


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
TASK_TMP = ROOT / ".tmp" / "narrative_baseline_runtime"
TASK_TMP.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(TASK_TMP)
sys.path.insert(0, str(ROOT))


class Progress:
    def pytest_runtest_logstart(self, nodeid, location):
        with (OUT / "baseline_progress.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"event": "start", "test": nodeid}) + "\n")

    def pytest_runtest_logreport(self, report):
        with (OUT / "baseline_progress.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"event": report.when, "test": report.nodeid,
                                     "outcome": report.outcome}) + "\n")


def main():
    import pytest
    (OUT / "baseline_progress.jsonl").write_text("", encoding="utf-8")
    metadata = {"started_at_utc": datetime.now(timezone.utc).isoformat(),
                "purpose": "Unchanged existing test suite, workspace-local temporary directory",
                "earlier_attempt": "Default-temp run interrupted after 102 completed tests; no final XML. Collection succeeded separately. Workspace temp retry retains diagnostics.",
                "temp_directory": str(TASK_TMP)}
    with (OUT / "baseline_pytest.log").open("w", encoding="utf-8") as log:
        with redirect_stdout(log), redirect_stderr(log):
            code = pytest.main(["-q", "-p", "no:cacheprovider", "-o",
                                "faulthandler_timeout=45", "--junitxml=" + str(OUT / "baseline_pytest.xml")],
                               plugins=[Progress()])
    metadata.update(exit_code=int(code), finished_at_utc=datetime.now(timezone.utc).isoformat())
    (OUT / "baseline_run.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    print((OUT / "baseline_pytest.log").read_text(encoding="utf-8")[-5000:])
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())
