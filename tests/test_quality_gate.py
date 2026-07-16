"""Unit tests for tools/quality_gate.py."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT / "tools"))

import quality_gate as qg  # noqa: E402


class QualityGateTests(unittest.TestCase):
    def test_good_resume_pass_or_soft(self) -> None:
        result = qg.run_gate(
            resume_path=FIX / "resume_backend_good.md",
            jd_path=FIX / "jd_backend_sample.md",
            cover_path=FIX / "cover_backend.md",
            profile_path=FIX / "profile_backend.md",
        )
        self.assertIn(result["gate_status"], ("PASS", "SOFT_FAIL"))
        self.assertIn("action_checklist", result)
        self.assertLessEqual(len(result["action_checklist"]), 3)
        self.assertGreaterEqual(result["match"]["score"], 40)
        text = qg.format_gate_human(result)
        self.assertIn("投前质量门禁", text)
        self.assertIn("改这 3 条", text)

    def test_weak_resume_soft_fail(self) -> None:
        result = qg.run_gate(
            resume_path=FIX / "resume_backend_weak.md",
            jd_path=FIX / "jd_backend_sample.md",
        )
        self.assertEqual(result["gate_status"], "SOFT_FAIL")
        self.assertTrue(result["soft_reasons"])

    def test_cli_weak_exit_1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "gate.json"
            rc = qg.main(
                [
                    "--resume",
                    str(FIX / "resume_backend_weak.md"),
                    "--jd",
                    str(FIX / "jd_backend_sample.md"),
                    "--out",
                    str(out),
                    "--zh-only",
                ]
            )
            self.assertEqual(rc, 1)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["gate_status"], "SOFT_FAIL")

    def test_cli_force_soft(self) -> None:
        rc = qg.main(
            [
                "--resume",
                str(FIX / "resume_backend_weak.md"),
                "--jd",
                str(FIX / "jd_backend_sample.md"),
                "--force",
                "--zh-only",
            ]
        )
        self.assertEqual(rc, 0)

    def test_integrity_hard_fail_on_contact(self) -> None:
        # Phone/email mismatch stays HARD; metrics alone are medium (soft)
        with tempfile.TemporaryDirectory() as tmp:
            prof = Path(tmp) / "p.md"
            res = Path(tmp) / "r.md"
            jd = Path(tmp) / "j.md"
            prof.write_text("# 画像\n只会 Python\n邮箱 a@b.com\n手机 13900000000\n", encoding="utf-8")
            res.write_text(
                "# 张\n13911111111\nz@x.com\n精通 量子 entangle\n提升 999%\nQPS 88888\n",
                encoding="utf-8",
            )
            jd.write_text("需要 Python 后端\n", encoding="utf-8")
            result = qg.run_gate(
                resume_path=res,
                jd_path=jd,
                profile_path=prof,
            )
            self.assertEqual(result["gate_status"], "HARD_FAIL")
            rc = qg.main(
                [
                    "--resume",
                    str(res),
                    "--jd",
                    str(jd),
                    "--profile",
                    str(prof),
                    "--zh-only",
                ]
            )
            self.assertEqual(rc, 2)

    def test_metric_only_is_not_hard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prof = Path(tmp) / "p.md"
            res = Path(tmp) / "r.md"
            jd = Path(tmp) / "j.md"
            prof.write_text("# 画像\nPython 后端\n邮箱 a@b.com\n手机 13900000000\n", encoding="utf-8")
            res.write_text(
                "# 测\na@b.com · 13900000000\nPython 后端 提升 50% QPS 1000\n",
                encoding="utf-8",
            )
            jd.write_text("需要 Python 后端 高并发\n", encoding="utf-8")
            result = qg.run_gate(
                resume_path=res,
                jd_path=jd,
                profile_path=prof,
            )
            self.assertNotEqual(result["gate_status"], "HARD_FAIL")
            types = {w["type"]: w["severity"] for w in result["integrity"]["warnings"]}
            if "metric_not_in_profile" in types:
                self.assertEqual(types["metric_not_in_profile"], "medium")


class MatchOutcomeTests(unittest.TestCase):
    def test_compute_match_outcome_bands(self) -> None:
        sys.path.insert(0, str(ROOT / "tools"))
        import tracker  # noqa: E402

        rows = [
            {"match_score": "80", "status": "interview"},
            {"match_score": "75", "status": "rejected"},
            {"match_score": "50", "status": "applied"},
            {"match_score": "20", "status": "skipped"},
            {"match_score": "", "status": "to_apply"},
        ]
        data = tracker.compute_match_outcome(rows)
        self.assertEqual(data["total"], 5)
        self.assertEqual(data["scored"], 4)
        bands = {b["band"]: b for b in data["bands"]}
        self.assertEqual(bands["high"]["n"], 2)
        self.assertEqual(bands["high"]["positive"], 1)
        self.assertEqual(bands["low"]["skipped"], 1)

    def test_match_rows_exact_and_channel(self) -> None:
        import tracker  # noqa: E402

        rows = [
            {"company": "Acme", "role": "后端", "channel": "Boss"},
            {"company": "Acme", "role": "高级后端", "channel": "智联"},
            {"company": "Acme", "role": "后端", "channel": "智联"},
        ]
        sub = tracker.match_rows(rows, "Acme", "后端", exact=False)
        self.assertEqual(len(sub), 3)  # substring hits 高级后端 too
        exact = tracker.match_rows(rows, "Acme", "后端", exact=True)
        self.assertEqual(len(exact), 2)
        ch = tracker.match_rows(rows, "Acme", "后端", channel="Boss", exact=True)
        self.assertEqual(len(ch), 1)

    def test_write_fit_status_scoped(self) -> None:
        import tracker  # noqa: E402

        with tempfile.TemporaryDirectory() as tmp:
            csv = Path(tmp) / "t.csv"
            fix = ROOT / "tests" / "fixtures"
            tracker.main(["--csv", str(csv), "init"])
            tracker.main(
                [
                    "--csv",
                    str(csv),
                    "add",
                    "--company",
                    "Good",
                    "--role",
                    "BE",
                    "--status",
                    "to_apply",
                    "--cv",
                    str(fix / "resume_backend_good.md"),
                    "--source",
                    str(fix / "jd_backend_sample.md"),
                ]
            )
            tracker.main(
                [
                    "--csv",
                    str(csv),
                    "add",
                    "--company",
                    "Good",
                    "--role",
                    "BE",
                    "--channel",
                    "other",
                    "--status",
                    "applied",
                    "--cv",
                    str(fix / "resume_backend_good.md"),
                    "--source",
                    str(fix / "jd_backend_sample.md"),
                    "--force",
                ]
            )
            rc = tracker.main(
                ["--csv", str(csv), "rank", "--status", "to_apply", "--write-fit"]
            )
            self.assertEqual(rc, 0)
            rows = tracker.read_rows(csv)
            by_st = {r["status"]: r for r in rows}
            self.assertTrue((by_st["to_apply"].get("match_score") or "").strip())
            # applied same company/role different channel may share key with empty channel...
            # channel "other" vs "" — different keys; applied should not be written
            self.assertFalse((by_st["applied"].get("match_score") or "").strip())


if __name__ == "__main__":
    unittest.main()
