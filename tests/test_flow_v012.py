"""v0.12: flow shortlist, corpus IDF, import hints, expected_salary flags."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "tools"))

import match_resume as m  # noqa: E402
import tracker  # noqa: E402


class FlowV012Tests(unittest.TestCase):
    def test_corpus_idf_loads_and_blends(self) -> None:
        idf = m.load_corpus_idf(force_reload=True)
        self.assertIn("kafka", idf)
        self.assertIn("高并发", idf)
        # corpus weight should differ from pure n=2 dynamic for rare skills
        docs = [m.term_frequency(["kafka", "java"]), m.term_frequency(["java"])]
        dyn = m.build_idf(docs, use_corpus=False)
        blend = m.build_idf(docs, use_corpus=True)
        self.assertNotEqual(blend.get("kafka"), dyn.get("kafka"))

    def test_import_missing_company_prints_hint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv = Path(tmp) / "t.csv"
            bad = Path(tmp) / "bad.json"
            bad.write_text(
                json.dumps([{"title": "Backend", "url": "https://x.example/1"}]),
                encoding="utf-8",
            )
            tracker.main(["--csv", str(csv), "init"])
            err = io.StringIO()
            with redirect_stderr(err):
                rc = tracker.main(["--csv", str(csv), "import-jobs", str(bad)])
            self.assertEqual(rc, 2)
            self.assertIn("company", err.getvalue().lower())
            self.assertIn("brandName", err.getvalue())

    def test_expected_salary_column_and_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv = Path(tmp) / "t.csv"
            tracker.main(["--csv", str(csv), "init"])
            tracker.main(
                [
                    "--csv",
                    str(csv),
                    "add",
                    "--company",
                    "PayCo",
                    "--role",
                    "BE",
                    "--status",
                    "to_apply",
                    "--salary",
                    "15-20K",
                    "--expected-salary",
                    "30-40K",
                ]
            )
            rows = tracker.read_rows(csv)
            self.assertEqual(rows[0]["expected_salary"], "30-40K")
            flag = tracker.salary_flag_for_row(rows[0])
            self.assertEqual(flag, "❌")
            buf = io.StringIO()
            with redirect_stdout(buf):
                tracker.main(
                    ["--csv", str(csv), "list", "--salary-flag", "--expected-salary", "30-40K"]
                )
            self.assertIn("❌", buf.getvalue())

    def test_flow_shortlist_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv = Path(tmp) / "t.csv"
            jobs = Path(tmp) / "jobs.json"
            jobs.write_text(
                json.dumps(
                    {
                        "jobs": [
                            {
                                "company": "FlowCo",
                                "title": "BE",
                                "platform": "Boss直聘",
                                "salary": "25-40K",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "flow.py"),
                    "--csv",
                    str(csv),
                    "shortlist",
                    "--jobs",
                    str(jobs),
                    "--limit",
                    "2",
                    "--track",
                    "internet",
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("今日计划", proc.stdout)
            self.assertTrue(csv.is_file())
            rows = tracker.read_rows(csv)
            self.assertTrue(any(r["company"] == "FlowCo" for r in rows))

    def test_header_has_expected_salary(self) -> None:
        self.assertIn("expected_salary", tracker.HEADER)
        self.assertIn("match_score", tracker.HEADER)
        self.assertEqual(len(tracker.HEADER), 22)


if __name__ == "__main__":
    unittest.main()
