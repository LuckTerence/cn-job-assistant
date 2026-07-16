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
        self.assertTrue((OUT / "skip_stats.txt").is_file())
        html = (OUT / "job_search_tracker.html").read_text(encoding="utf-8")
        self.assertIn("星云科技", html)
        self.assertIn("不投信号", html)
        csv_text = (OUT / "job_search_tracker.csv").read_text(encoding="utf-8")
        self.assertIn("skip_reason", csv_text)
        self.assertIn("salary_low", csv_text)
        skip_out = (OUT / "skip_stats.txt").read_text(encoding="utf-8")
        self.assertIn("salary_low", skip_out)
        self.assertIn("location", skip_out)
        self.assertTrue((OUT / "import_jobs.txt").is_file())
        import_out = (OUT / "import_jobs.txt").read_text(encoding="utf-8")
        self.assertIn("added=", import_out)
        self.assertIn("云梯科技", csv_text)
        self.assertTrue((OUT / "salary_compare.txt").is_file())
        salary_out = (OUT / "salary_compare.txt").read_text(encoding="utf-8")
        self.assertIn("薪资对照", salary_out)
        brief = (OUT / "match_brief_zh.txt").read_text(encoding="utf-8")
        self.assertIn("薪资对照", brief)
        self.assertTrue((OUT / "rank.txt").is_file())
        self.assertTrue((OUT / "day_plan.txt").is_file())
        self.assertIn("今日计划", (OUT / "day_plan.txt").read_text(encoding="utf-8"))
        self.assertIn("filter-status", html)
        if (OUT / "flow_shortlist.txt").is_file():
            self.assertIn("今日计划", (OUT / "flow_shortlist.txt").read_text(encoding="utf-8"))
        if (OUT / "funnel.txt").is_file():
            self.assertIn("漏斗", (OUT / "funnel.txt").read_text(encoding="utf-8"))
        self.assertIn("投递漏斗", html)


if __name__ == "__main__":
    unittest.main()
