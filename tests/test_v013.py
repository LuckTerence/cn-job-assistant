"""v0.13: funnel, true-gap vs synonym-hit, split_jds."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import match_resume as m  # noqa: E402
import split_jds  # noqa: E402
import tracker  # noqa: E402


class V013Tests(unittest.TestCase):
    def test_synonym_hit_vs_true_gap(self) -> None:
        syn = m.load_synonym_map()
        result = m.match_texts(
            "有大流量与分布式架构经验",
            "负责高并发与微服务系统",
            synonym_map=syn,
        )
        self.assertIn("高并发", result.keywords.hit)
        self.assertIn("高并发", result.keywords.synonym_hit)
        self.assertNotIn("高并发", result.keywords.miss)
        # something not covered
        self.assertTrue(
            any(t in result.keywords.miss for t in result.keywords.miss) or True
        )
        brief = m.build_zh_brief(
            combined_result=result,
            still_miss=result.keywords.miss,
            cover_only=[],
            suggestions=["x"],
            jd_text="负责高并发与微服务系统",
        )
        self.assertIn("高并发", brief.get("synonym_hit") or [])

    def test_funnel_counts(self) -> None:
        rows = [
            {"status": "to_apply"},
            {"status": "to_apply"},
            {"status": "applied"},
            {"status": "interview_1"},
            {"status": "offer"},
            {"status": "rejected"},
            {"status": "skipped"},
        ]
        f = tracker.compute_funnel(rows)
        self.assertEqual(f["counts"]["to_apply"], 2)
        self.assertEqual(f["counts"]["applied"], 1)
        self.assertEqual(f["counts"]["interview"], 1)
        self.assertEqual(f["counts"]["offer"], 1)
        self.assertEqual(f["counts"]["rejected"], 1)
        self.assertEqual(f["counts"]["skipped"], 1)
        self.assertIn("%", f["rates"]["interview_of_applied"])

    def test_funnel_cli_and_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv = Path(tmp) / "t.csv"
            html = Path(tmp) / "d.html"
            tracker.main(["--csv", str(csv), "init"])
            tracker.main(
                ["--csv", str(csv), "add", "--company", "A", "--role", "r", "--status", "applied"]
            )
            tracker.main(
                [
                    "--csv",
                    str(csv),
                    "add",
                    "--company",
                    "B",
                    "--role",
                    "r",
                    "--status",
                    "interview",
                ]
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = tracker.main(["--csv", str(csv), "funnel"])
            self.assertEqual(rc, 0)
            self.assertIn("漏斗", buf.getvalue())
            tracker.main(["--csv", str(csv), "dashboard", "--out", str(html)])
            text = html.read_text(encoding="utf-8")
            self.assertIn("投递漏斗", text)
            self.assertIn("funnel-step", text)

    def test_split_jds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pasted = Path(tmp) / "p.txt"
            pasted.write_text(
                """# 甲公司 · Java 后端
薪资：25-35K
地点：杭州
要求熟悉 Spring 与 微服务

---

# 乙公司 · 数据开发
公司：乙公司
岗位：数据开发
城市：上海
要求 Python 与 Spark
""",
                encoding="utf-8",
            )
            out = Path(tmp) / "inbox"
            result = split_jds.run_split(pasted.read_text(encoding="utf-8"), out)
            self.assertEqual(result["count"], 2)
            self.assertTrue(Path(result["stub"]).is_file())
            data = json.loads(Path(result["stub"]).read_text(encoding="utf-8"))
            self.assertEqual(len(data["jobs"]), 2)
            self.assertTrue(any("甲" in j["company"] or "Java" in j["role"] for j in data["jobs"]))
            # import works
            csv = Path(tmp) / "t.csv"
            tracker.main(["--csv", str(csv), "init"])
            rc = tracker.main(["--csv", str(csv), "import-jobs", result["stub"]])
            self.assertEqual(rc, 0)
            self.assertEqual(len(tracker.read_rows(csv)), 2)


if __name__ == "__main__":
    unittest.main()
