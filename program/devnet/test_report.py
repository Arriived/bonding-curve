"""The public report must emit UTF-8 even with a Windows legacy stdout encoding."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

PROGRAM = Path(__file__).resolve().parents[1]
FIXTURE = PROGRAM / "verification/devnet/paired-4437e58-resume"


class ReportEncoding(unittest.TestCase):
    def test_report_checks_complete_with_cp1252_environment(self):
        result = subprocess.run(
            [sys.executable, str(PROGRAM / "devnet/report.py"),
             str(FIXTURE), str(FIXTURE / "svm_report.json"), "saved fixture", "--check"],
            env=dict(os.environ, PYTHONIOENCODING="cp1252"), capture_output=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("ascii", errors="replace"))
        report = result.stdout.decode("utf-8")
        self.assertIn("checks passed", report)
        self.assertIn("\u2212", report)


if __name__ == "__main__":
    unittest.main()
