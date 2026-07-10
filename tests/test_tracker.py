"""Unit tests for tools/tracker.py (stdlib only, temp CSV)."""

from __future__ import annotations

import io
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta
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

    def test_header_schema_has_new_columns(self) -> None:
        self.assertIn("date", tracker.HEADER)
        self.assertIn("company", tracker.HEADER)
        self.assertIn("source", tracker.HEADER)
        for col in ("salary", "city", "education", "experience"):
            self.assertIn(col, tracker.HEADER, f"missing column: {col}")
        self.assertEqual(len(tracker.HEADER), 17)

    def test_add_with_structured_fields(self) -> None:
        tracker.main(["--csv", str(self.csv), "init"])
        tracker.main(
            [
                "--csv",
                str(self.csv),
                "add",
                "--company",
                "星云科技",
                "--role",
                "后端工程师",
                "--channel",
                "Boss直聘",
                "--city",
                "北京",
                "--salary",
                "25-40K",
                "--education",
                "本科",
                "--experience",
                "3-5年",
                "--status",
                "to_apply",
            ]
        )
        rows = tracker.read_rows(self.csv)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["city"], "北京")
        self.assertEqual(rows[0]["salary"], "25-40K")
        self.assertEqual(rows[0]["education"], "本科")
        self.assertEqual(rows[0]["experience"], "3-5年")
        self.assertEqual(rows[0]["status"], "to_apply")

    def test_update_structured_fields(self) -> None:
        tracker.main(["--csv", str(self.csv), "init"])
        tracker.main(
            [
                "--csv",
                str(self.csv),
                "add",
                "--company",
                "TestCo",
                "--role",
                "Dev",
            ]
        )
        tracker.main(
            [
                "--csv",
                str(self.csv),
                "update",
                "--company",
                "TestCo",
                "--role",
                "Dev",
                "--city",
                "上海",
                "--salary",
                "30-50K",
            ]
        )
        rows = tracker.read_rows(self.csv)
        self.assertEqual(rows[0]["city"], "上海")
        self.assertEqual(rows[0]["salary"], "30-50K")

    def test_backward_compat_old_csv_missing_columns(self) -> None:
        """Old CSV without salary/city/education/experience should still read."""
        old_header = "date,company,sector,role,role_type,channel,status,contact_person,fit_rating,notes,cv_file,cover_letter_file,source\n"
        old_row = "2026-07-01,OldCo,,Engineer,,Boss直聘,applied,,,,,,\n"
        self.csv.write_text(old_header + old_row, encoding="utf-8")
        rows = tracker.read_rows(self.csv)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["company"], "OldCo")
        for col in ("salary", "city", "education", "experience"):
            self.assertEqual(rows[0].get(col, ""), "", f"col {col} should default to empty")
        tracker.main(
            [
                "--csv",
                str(self.csv),
                "add",
                "--company",
                "NewCo",
                "--role",
                "Dev",
                "--city",
                "深圳",
            ]
        )
        rows2 = tracker.read_rows(self.csv)
        self.assertEqual(len(rows2), 2)
        self.assertEqual(rows2[1]["city"], "深圳")
        header_line = self.csv.read_text(encoding="utf-8").splitlines()[0]
        for col in ("salary", "city", "education", "experience"):
            self.assertIn(col, header_line, f"after write-back, header should contain {col}")

    def test_today_and_suggest_add(self) -> None:
        tracker.main(["--csv", str(self.csv), "init"])
        tracker.main(
            [
                "--csv",
                str(self.csv),
                "add",
                "--company",
                "星云",
                "--role",
                "后端",
                "--status",
                "interview",
                "--city",
                "杭州",
            ]
        )
        self.assertEqual(tracker.main(["--csv", str(self.csv), "today"]), 0)
        self.assertEqual(
            tracker.main(
                [
                    "--csv",
                    str(self.csv),
                    "suggest-add",
                    "--company",
                    "星云",
                    "--role",
                    "后端",
                    "--channel",
                    "Boss直聘",
                    "--city",
                    "杭州",
                    "--salary",
                    "20-35K",
                ]
            ),
            0,
        )

    def test_suggest_add_default_status_to_apply(self) -> None:
        """suggest-add should default to to_apply (safe), not applied."""
        tracker.main(["--csv", str(self.csv), "init"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            tracker.main(
                [
                    "--csv",
                    str(self.csv),
                    "suggest-add",
                    "--company",
                    "SafeCo",
                    "--role",
                    "QA",
                ]
            )
        output = buf.getvalue()
        self.assertIn("--status to_apply", output)
        self.assertIn("预填摘要", output)
        self.assertIn("to_apply = 还没投", output)

    def test_build_action_items_interviews(self) -> None:
        today = date.today()
        rows = [
            {"date": today.isoformat(), "company": "A", "role": "X", "status": "interview", "channel": "", "notes": ""},
            {"date": today.isoformat(), "company": "B", "role": "Y", "status": "applied", "channel": "", "notes": ""},
        ]
        for r in rows:
            for k in tracker.HEADER:
                r.setdefault(k, "")
        actions = tracker.build_action_items(rows, today)
        self.assertEqual(len(actions["interviews"]), 1)
        self.assertEqual(actions["interviews"][0]["company"], "A")

    def test_build_action_items_follow_ups(self) -> None:
        """applied rows >= 7 days old should appear in follow_ups."""
        today = date.today()
        old_enough = (today - timedelta(days=8)).isoformat()
        recent = (today - timedelta(days=2)).isoformat()
        rows = [
            {"date": old_enough, "company": "Stale", "role": "X", "status": "applied", "channel": "", "notes": ""},
            {"date": recent, "company": "Fresh", "role": "Y", "status": "applied", "channel": "", "notes": ""},
        ]
        for r in rows:
            for k in tracker.HEADER:
                r.setdefault(k, "")
        actions = tracker.build_action_items(rows, today)
        companies = [r["company"] for r in actions["follow_ups"]]
        self.assertIn("Stale", companies)
        self.assertNotIn("Fresh", companies)

    def test_build_action_items_reviews(self) -> None:
        """rejected rows within 30 days should appear in reviews."""
        today = date.today()
        recent_rejected = (today - timedelta(days=10)).isoformat()
        old_rejected = (today - timedelta(days=40)).isoformat()
        rows = [
            {"date": recent_rejected, "company": "R1", "role": "X", "status": "rejected", "channel": "", "notes": ""},
            {"date": old_rejected, "company": "R2", "role": "Y", "status": "rejected", "channel": "", "notes": ""},
        ]
        for r in rows:
            for k in tracker.HEADER:
                r.setdefault(k, "")
        actions = tracker.build_action_items(rows, today)
        companies = [r["company"] for r in actions["reviews"]]
        self.assertIn("R1", companies)
        self.assertNotIn("R2", companies)

    def test_html_dashboard_has_action_cards(self) -> None:
        tracker.main(["--csv", str(self.csv), "init"])
        tracker.main(
            [
                "--csv",
                str(self.csv),
                "add",
                "--company",
                "CardCo",
                "--role",
                "Eng",
                "--status",
                "interview",
            ]
        )
        html = Path(self.tmp.name) / "dash.html"
        tracker.main(["--csv", str(self.csv), "dashboard", "--out", str(html)])
        text = html.read_text(encoding="utf-8")
        self.assertIn("进行中的面试", text)
        self.assertIn("CardCo", text)
        self.assertIn("prefers-color-scheme", text)

    def test_html_dashboard_empty_shows_no_todo(self) -> None:
        """Zero-row tracker should show Chinese onboarding message, not 'empty'."""
        tracker.main(["--csv", str(self.csv), "init"])
        html = Path(self.tmp.name) / "dash.html"
        tracker.main(["--csv", str(self.csv), "dashboard", "--out", str(html)])
        text = html.read_text(encoding="utf-8")
        self.assertIn("还没有投递记录", text)
        self.assertIn("/apply-zh", text)

    def test_html_dashboard_hides_empty_structured_columns(self) -> None:
        """When salary/city are empty for all rows, columns should be hidden from table."""
        tracker.main(["--csv", str(self.csv), "init"])
        tracker.main(
            [
                "--csv",
                str(self.csv),
                "add",
                "--company",
                "BareCo",
                "--role",
                "Dev",
                "--status",
                "applied",
            ]
        )
        html = Path(self.tmp.name) / "dash.html"
        tracker.main(["--csv", str(self.csv), "dashboard", "--out", str(html)])
        text = html.read_text(encoding="utf-8")
        self.assertIn("BareCo", text)
        self.assertNotIn("<th>salary</th>", text)

    def test_skipped_status_is_closed(self) -> None:
        """skipped should be treated as a closed/terminal status."""
        self.assertIn("skipped", tracker.CLOSED_STATUSES)
        tracker.main(["--csv", str(self.csv), "init"])
        tracker.main(
            [
                "--csv",
                str(self.csv),
                "add",
                "--company",
                "SkipCo",
                "--role",
                "X",
                "--status",
                "skipped",
            ]
        )
        html = Path(self.tmp.name) / "d.html"
        tracker.main(["--csv", str(self.csv), "dashboard", "--out", str(html)])
        text = html.read_text(encoding="utf-8")
        self.assertIn("已结束", text)

    def test_html_dashboard_closed_is_collapsed(self) -> None:
        """Closed rows should be wrapped in <details> for folding."""
        tracker.main(["--csv", str(self.csv), "init"])
        tracker.main([
            "--csv", str(self.csv), "add",
            "--company", "PastCo", "--role", "dev", "--channel", "Boss",
            "--status", "rejected", "--date", "2026-07-01",
        ])
        html = Path(self.tmp.name) / "d.html"
        tracker.main(["--csv", str(self.csv), "dashboard", "--out", str(html)])
        text = html.read_text(encoding="utf-8")
        self.assertIn("<details", text)
        self.assertIn("点击展开", text)

    def test_html_dashboard_positive_stats_cards(self) -> None:
        """Dashboard should include 累计已投/面试次数/面试率 stat cards."""
        tracker.main(["--csv", str(self.csv), "init"])
        tracker.main([
            "--csv", str(self.csv), "add",
            "--company", "IvCo", "--role", "eng", "--channel", "Boss",
            "--status", "interview",
        ])
        tracker.main([
            "--csv", str(self.csv), "add",
            "--company", "ApCo", "--role", "eng", "--channel", "Boss",
            "--status", "applied",
        ])
        html = Path(self.tmp.name) / "d.html"
        tracker.main(["--csv", str(self.csv), "dashboard", "--out", str(html)])
        text = html.read_text(encoding="utf-8")
        self.assertIn("累计已投", text)
        self.assertIn("面试次数", text)
        self.assertIn("面试率", text)

    def test_html_dashboard_encouragement_shown_for_rejections(self) -> None:
        """With 3+ recent rejected/no_response, an encouragement line should appear."""
        tracker.main(["--csv", str(self.csv), "init"])
        for i, c in enumerate(["A", "B", "C"]):
            tracker.main([
                "--csv", str(self.csv), "add",
                "--company", c, "--role", "dev", "--channel", "Boss",
                "--status", "rejected", "--date", date.today().isoformat(),
            ])
        html = Path(self.tmp.name) / "d.html"
        tracker.main(["--csv", str(self.csv), "dashboard", "--out", str(html)])
        text = html.read_text(encoding="utf-8")
        self.assertIn("encourage", text)
        self.assertTrue(any(p in text for p in tracker.ENCOURAGEMENTS))

    def test_compute_stats_basic(self) -> None:
        """compute_stats should exclude to_apply/skipped, count interviews, compute rate."""
        rows = [
            {"status": "applied", "date": date.today().isoformat(), "company": "A", "role": "x"},
            {"status": "to_apply", "date": "", "company": "B", "role": "x"},
            {"status": "interview", "date": date.today().isoformat(), "company": "C", "role": "x"},
            {"status": "rejected", "date": date.today().isoformat(), "company": "D", "role": "x"},
            {"status": "skipped", "date": "", "company": "E", "role": "x"},
        ]
        stats = tracker.compute_stats(rows, today=date.today())
        self.assertEqual(stats["total_applied"], 3)
        self.assertEqual(stats["total_interviews"], 1)
        self.assertIn("%", stats["interview_rate"])
        self.assertEqual(stats["week_applied"], 3)

    def test_compute_stats_empty(self) -> None:
        """Empty rows should give 0s and 暂无 rate."""
        stats = tracker.compute_stats([], today=date.today())
        self.assertEqual(stats["total_applied"], 0)
        self.assertEqual(stats["interview_rate"], "暂无")

    def test_today_empty_csv_shows_marathon(self) -> None:
        """today with 0 rows should show onboarding message, not init instructions."""
        tracker.main(["--csv", str(self.csv), "init"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            tracker.main(["--csv", str(self.csv), "today"])
        out = buf.getvalue()
        self.assertIn("还没有投递记录", out)
        self.assertIn("/apply-zh", out)

    def test_today_no_urgent_shows_marathon(self) -> None:
        """today with rows but no interviews/follow-ups should show marathon rest message."""
        tracker.main(["--csv", str(self.csv), "init"])
        tracker.main([
            "--csv", str(self.csv), "add",
            "--company", "NewCo", "--role", "dev", "--channel", "Boss",
            "--status", "applied", "--date", date.today().isoformat(),
        ])
        buf = io.StringIO()
        with redirect_stdout(buf):
            tracker.main(["--csv", str(self.csv), "today"])
        out = buf.getvalue()
        self.assertIn("马拉松", out)
        self.assertIn("累计已投", out)

    def test_today_shows_positive_stats(self) -> None:
        """today should always show 累计/本周/面试率 stats section."""
        tracker.main(["--csv", str(self.csv), "init"])
        tracker.main([
            "--csv", str(self.csv), "add",
            "--company", "X", "--role", "dev", "--channel", "Boss",
            "--status", "applied",
        ])
        buf = io.StringIO()
        with redirect_stdout(buf):
            tracker.main(["--csv", str(self.csv), "today"])
        out = buf.getvalue()
        self.assertIn("累计已投", out)
        self.assertIn("面试率", out)

    def test_today_weekend_hint_on_weekend(self) -> None:
        """When today is weekend and there are follow_ups, show weekend hint."""
        from unittest.mock import patch
        tracker.main(["--csv", str(self.csv), "init"])
        old_date = (date.today() - timedelta(days=10)).isoformat()
        tracker.main([
            "--csv", str(self.csv), "add",
            "--company", "OldCo", "--role", "dev", "--channel", "Boss",
            "--status", "applied", "--date", old_date,
        ])
        saturday = date(2026, 7, 11)
        buf = io.StringIO()
        with redirect_stdout(buf), patch("tools.tracker.date") as mock_date:
            mock_date.today.return_value = saturday
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            tracker.main(["--csv", str(self.csv), "today"])
        out = buf.getvalue()
        self.assertIn("周末", out)


if __name__ == "__main__":
    unittest.main()
