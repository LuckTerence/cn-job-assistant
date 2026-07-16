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

    def test_integrity_hard_fail(self) -> None:
        # Resume invents a metric and phone not in sparse profile
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


if __name__ == "__main__":
    unittest.main()
