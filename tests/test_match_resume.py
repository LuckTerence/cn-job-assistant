"""Unit tests for tools/match_resume.py."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT / "tools"))

import match_resume as m  # noqa: E402


class MatchResumeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.jd = (FIX / "jd_backend_sample.md").read_text(encoding="utf-8")
        self.good = (FIX / "resume_backend_good.md").read_text(encoding="utf-8")
        self.weak = (FIX / "resume_backend_weak.md").read_text(encoding="utf-8")
        self.cover = (FIX / "cover_backend.md").read_text(encoding="utf-8")

    def test_tokenize_bilingual(self) -> None:
        tokens = m.tokenize("精通 Spring Boot 与 微服务 Kafka")
        joined = " ".join(tokens)
        self.assertIn("spring", joined)  # or spring boot phrase
        self.assertTrue(any("微服务" in t or t == "微服务" for t in tokens))
        self.assertTrue(any("kafka" == t for t in tokens))

    def test_good_scores_higher_than_weak(self) -> None:
        good = m.match_texts(self.good, self.jd)
        weak = m.match_texts(self.weak, self.jd)
        self.assertGreater(good.score, weak.score)
        self.assertGreaterEqual(good.score, 45)
        self.assertLess(weak.score, 40)
        self.assertIn(good.verdict, ("strong_match", "moderate_match", "partial_match"))
        self.assertEqual(weak.verdict, "weak_match")

    def test_keyword_hits_include_core_stack(self) -> None:
        result = m.match_texts(self.good, self.jd)
        hit_set = set(result.keywords.hit)
        # At least some stack terms should hit
        stack = {"java", "redis", "mysql", "kafka", "docker", "微服务", "高并发"}
        self.assertTrue(len(hit_set & stack) >= 3, msg=f"hits={hit_set}")
        self.assertTrue(result.keywords.miss or result.keyword_coverage < 100)

    def test_quality_report_combined(self) -> None:
        report = m.quality_report(self.good, self.jd, self.cover)
        self.assertIn("summary", report)
        self.assertGreaterEqual(report["summary"]["combined_score"], report["summary"]["resume_score"] - 5)
        self.assertIsInstance(report["suggestions"], list)
        self.assertTrue(len(report["suggestions"]) >= 1)
        self.assertIn("brief_zh", report)
        self.assertEqual(len(report["brief_zh"]["edit_top3"]), 3)
        brief = m.format_zh_brief(report["brief_zh"])
        self.assertIn("匹配摘要", brief)
        self.assertIn("别硬写", brief)

    def test_diff_reports_flywheel(self) -> None:
        weak = m.quality_report(self.weak, self.jd)
        good = m.quality_report(self.good, self.jd, self.cover)
        diff = m.diff_reports(weak, good)
        self.assertGreater(diff["score_delta"], 0)
        self.assertIn("miss_resolved", diff)

    def test_cli_score_json(self) -> None:
        rc = m.main(
            [
                "score",
                "--json",
                "--resume",
                str(FIX / "resume_backend_good.md"),
                "--jd",
                str(FIX / "jd_backend_sample.md"),
            ]
        )
        self.assertEqual(rc, 0)

    def test_cli_report_writes_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.json"
            rc = m.main(
                [
                    "report",
                    "--json",
                    "--resume",
                    str(FIX / "resume_backend_good.md"),
                    "--jd",
                    str(FIX / "jd_backend_sample.md"),
                    "--cover",
                    str(FIX / "cover_backend.md"),
                    "--out",
                    str(out),
                ]
            )
            self.assertEqual(rc, 0)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertIn("summary", data)

    def test_keywords_command(self) -> None:
        ranked = m.extract_jd_keywords(self.jd, top_k=15)
        self.assertTrue(len(ranked) >= 5)
        terms = [t for t, _ in ranked]
        # 岗位描述 should surface backend-ish terms
        self.assertTrue(
            any(t in terms for t in ("java", "kafka", "redis", "mysql", "docker", "微服务")),
            msg=terms,
        )


if __name__ == "__main__":
    unittest.main()
