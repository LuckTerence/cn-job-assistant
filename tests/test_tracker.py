"""Unit tests for tools/tracker.py (stdlib only, temp CSV)."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import tracker  # noqa: E402


class TrackerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.csv = Path(self.tmp.name) / "job_search_tracker.csv"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_init_and_add_list(self) -> None:
        self.assertEqual(tracker.main(["--csv", str(self.csv), "init"]), 0)
        self.assertTrue(self.csv.exists())
        self.assertEqual(
            tracker.main(
                [
                    "--csv",
                    str(self.csv),
                    "add",
                    "--company",
                    "Acme",
                    "--role",
                    "Backend",
                    "--channel",
                    "Boss直聘",
                    "--status",
                    "applied",
                ]
            ),
            0,
        )
        rows = tracker.read_rows(self.csv)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["company"], "Acme")
        self.assertEqual(rows[0]["channel"], "Boss直聘")
        self.assertEqual(tracker.main(["--csv", str(self.csv), "list"]), 0)

    def test_duplicate_blocked_without_force(self) -> None:
        tracker.main(["--csv", str(self.csv), "init"])
        args = [
            "--csv",
            str(self.csv),
            "add",
            "--company",
            "Acme",
            "--role",
            "Backend",
        ]
        self.assertEqual(tracker.main(args), 0)
        self.assertEqual(tracker.main(args), 1)
        self.assertEqual(tracker.main(args + ["--force"]), 0)
        self.assertEqual(len(tracker.read_rows(self.csv)), 2)

    def test_update_status(self) -> None:
        tracker.main(["--csv", str(self.csv), "init"])
        tracker.main(
            [
                "--csv",
                str(self.csv),
                "add",
                "--company",
                "字节",
                "--role",
                "前端",
                "--status",
                "applied",
            ]
        )
        self.assertEqual(
            tracker.main(
                [
                    "--csv",
                    str(self.csv),
                    "update",
                    "--company",
                    "字节",
                    "--role",
                    "前端",
                    "--status",
                    "interview",
                ]
            ),
            0,
        )
        rows = tracker.read_rows(self.csv)
        self.assertEqual(rows[0]["status"], "interview")

    def test_export_sqlite_and_html(self) -> None:
        tracker.main(["--csv", str(self.csv), "init"])
        tracker.main(
            [
                "--csv",
                str(self.csv),
                "add",
                "--company",
                "Foo",
                "--role",
                "Bar",
                "--status",
                "applied",
            ]
        )
        db = Path(self.tmp.name) / "t.db"
        html = Path(self.tmp.name) / "t.html"
        self.assertEqual(
            tracker.main(
                ["--csv", str(self.csv), "export", "--format", "sqlite", "--out", str(db)]
            ),
            0,
        )
        conn = sqlite3.connect(db)
        n = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        conn.close()
        self.assertEqual(n, 1)
        self.assertEqual(
            tracker.main(
                ["--csv", str(self.csv), "export", "--format", "html", "--out", str(html)]
            ),
            0,
        )
        text = html.read_text(encoding="utf-8")
        self.assertIn("Foo", text)
        self.assertIn("求职投递看板", text)

    def test_header_schema(self) -> None:
        self.assertIn("date", tracker.HEADER)
        self.assertIn("company", tracker.HEADER)
        self.assertIn("source", tracker.HEADER)
        self.assertEqual(len(tracker.HEADER), 13)


if __name__ == "__main__":
    unittest.main()
