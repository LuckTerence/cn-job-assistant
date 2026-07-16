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
        self.assertIn("action_checklist", report)
        self.assertEqual(len(report["action_checklist"]), 3)
        self.assertTrue(all(item.get("fiction_forbidden") for item in report["action_checklist"]))
        brief = m.format_zh_brief(report["brief_zh"])
        self.assertIn("匹配摘要", brief)
        self.assertIn("别硬写", brief)
        self.assertIn("改这 3 条", brief)

    def test_cli_align(self) -> None:
        rc = m.main(
            [
                "align",
                "--json",
                "--resume",
                str(FIX / "resume_backend_good.md"),
                "--jd",
                str(FIX / "jd_backend_sample.md"),
            ]
        )
        self.assertEqual(rc, 0)

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
                    "--expected-salary",
                    "25-40K",
                ]
            )
            self.assertEqual(rc, 0)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertIn("summary", data)
            self.assertIn("salary", data)
            self.assertIn(data["salary"]["verdict"], ("overlap", "high_ok", "partial", "low"))

    def test_synonym_reduces_false_miss(self) -> None:
        """Resume says 大流量; JD says 高并发 → should hit with synonyms on."""
        jd = "负责高并发系统与微服务架构"
        resume_syn = "有大流量系统与分布式架构经验"
        with_syn = m.match_texts(resume_syn, jd, synonym_map=m.load_synonym_map())
        without = m.match_texts(resume_syn, jd, synonym_map={})
        # 高并发 should be miss without synonyms if only 大流量 present
        self.assertIn("高并发", without.keywords.miss + without.keywords.hit)
        self.assertIn("高并发", with_syn.keywords.hit)
        self.assertNotIn("高并发", with_syn.keywords.miss)
        self.assertGreaterEqual(with_syn.keyword_coverage, without.keyword_coverage)

    def test_parse_and_compare_salary(self) -> None:
        r = m.parse_salary_text("25-40K")
        self.assertIsNotNone(r)
        assert r is not None
        self.assertAlmostEqual(r.low or 0, 25000, delta=1)
        self.assertAlmostEqual(r.high or 0, 40000, delta=1)

        yearly = m.parse_salary_text("30-50万/年")
        self.assertIsNotNone(yearly)
        assert yearly is not None
        self.assertGreater(yearly.low or 0, 20000)
        self.assertLess(yearly.high or 0, 50000)

        jd = (FIX / "jd_backend_sample.md").read_text(encoding="utf-8")
        offered = m.extract_jd_salary(jd)
        self.assertIsNotNone(offered)
        low = m.compare_salary(m.parse_salary_text("50-60K"), offered)
        self.assertEqual(low["verdict"], "low")
        self.assertEqual(low["signal"], "❌")
        ok = m.compare_salary(m.parse_salary_text("25-35K"), offered)
        self.assertIn(ok["verdict"], ("overlap", "high_ok", "partial"))
        self.assertEqual(ok["signal"], "✅")

    def test_extract_expected_from_profile(self) -> None:
        text = "### 求职方向\n- **薪资期望：** 28-40K\n- **城市偏好：** 杭州\n"
        self.assertEqual(m.extract_expected_from_profile(text), "28-40K")
        self.assertIsNone(m.extract_expected_from_profile("- **薪资期望：** [范围，可选]\n"))

    def test_cli_salary(self) -> None:
        rc = m.main(
            [
                "salary",
                "--jd",
                str(FIX / "jd_backend_sample.md"),
                "--expected",
                "50-60K",
                "--json",
            ]
        )
        self.assertEqual(rc, 0)

    def test_keywords_command(self) -> None:
        ranked = m.extract_jd_keywords(self.jd, top_k=15)
        self.assertTrue(len(ranked) >= 5)
        terms = [t for t, _ in ranked]
        # 岗位描述 should surface backend-ish terms
        self.assertTrue(
            any(t in terms for t in ("java", "kafka", "redis", "mysql", "docker", "微服务")),
            msg=terms,
        )


class CalmerBriefTests(unittest.TestCase):
    """Tests for UX-P1: calmer match brief (calmer-ux-copy spec)."""

    def _build_brief(self, *, score: float, miss: list[str], jd: str = "") -> dict:
        result = m.MatchResult(
            score=score,
            cosine=0.0,
            verdict=("strong_match" if score >= 70 else
                     "moderate_match" if score >= 50 else
                     "partial_match" if score >= 30 else "weak_match"),
            keywords=m.KeywordBreakdown(hit=["python"], miss=miss, extra=[]),
            jd_keyword_count=10,
            resume_token_count=100,
            jd_token_count=100,
            keyword_coverage=round(100.0 * 1 / max(1, 1 + len(miss)), 1),
        )
        return m.build_zh_brief(
            combined_result=result,
            still_miss=miss,
            cover_only=[],
            suggestions=[],
            jd_text=jd,
        )

    def test_high_score_has_positive_tone_and_interview_action(self) -> None:
        brief = self._build_brief(score=85, miss=["kafka"])
        self.assertIn("挺匹配", brief["tone_open"])
        self.assertIn("面试", brief["action_by_band"])

    def test_low_score_has_practice_or_pivot_language(self) -> None:
        brief = self._build_brief(score=20, miss=["kafka", "redis", "微服务", "高并发"])
        combined = brief["tone_open"] + brief["action_by_band"]
        self.assertTrue("有距离" in combined or "练手" in combined, msg=combined)
        self.assertIn("练手", brief["action_by_band"])

    def test_miss_split_core_vs_nice(self) -> None:
        miss = ["kafka", "redis", "团队协作", "沟通能力", "责任心", "抗压"]
        core, nice = m._split_miss_core_nice(miss)
        self.assertIn("kafka", core)
        self.assertIn("redis", core)

    def test_brief_contains_no_shaming_title(self) -> None:
        brief = self._build_brief(score=30, miss=["a", "b", "c", "d", "e", "f"])
        text = m.format_zh_brief(brief)
        self.assertNotIn("还差", text)
        self.assertIn("不会的别硬编", text)

    def test_brief_has_compliance_sentence(self) -> None:
        brief = self._build_brief(score=50, miss=[])
        text = m.format_zh_brief(brief)
        self.assertIn("别硬", text)

    def test_brief_has_next_action_section(self) -> None:
        brief = self._build_brief(score=65, miss=["docker"])
        text = m.format_zh_brief(brief)
        self.assertIn("下一步建议", text)
        self.assertTrue(brief.get("action_by_band"))

    def test_brief_json_backward_compat(self) -> None:
        brief = self._build_brief(score=60, miss=["kafka"])
        self.assertIn("still_missing", brief)
        self.assertIn("miss_core", brief)
        self.assertIn("miss_nice", brief)

    def test_float_score_accepted(self) -> None:
        brief = self._build_brief(score=54.9, miss=["大模型"])
        self.assertIn("有一定匹配度", brief["tone_open"])


if __name__ == "__main__":
    unittest.main()
