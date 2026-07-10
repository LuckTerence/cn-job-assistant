"""Ensure scripts/demo.sh stays green offline."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO_SH = ROOT / "scripts" / "demo.sh"
OUT = ROOT / "examples" / "demo" / "output"


class DemoScriptTests(unittest.TestCase):
    def test_demo_script_runs(self) -> None:
        self.assertTrue(DEMO_SH.is_file())
        proc = subprocess.run(
            ["bash", str(DEMO_SH)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=proc.stdout + "\n" + proc.stderr,
        )
        self.assertTrue((OUT / "match_report.json").is_file())
        self.assertTrue((OUT / "job_search_tracker.html").is_file())
        self.assertTrue((OUT / "job_search_tracker.csv").is_file())
        html = (OUT / "job_search_tracker.html").read_text(encoding="utf-8")
        self.assertIn("星云科技", html)


if __name__ == "__main__":
    unittest.main()
