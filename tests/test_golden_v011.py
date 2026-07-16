"""Golden / regression checks for v0.11 decision + day-plan + synonyms track."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "tools"))

import match_resume as m  # noqa: E402
import tracker  # noqa: E402


class GoldenV011Tests(unittest.TestCase):
    def test_salary_and_synonym_golden(self) -> None:
        jd = (FIX / "jd_backend_sample.md").read_text(encoding="utf-8")
        good = (FIX / "resume_backend_good.md").read_text(encoding="utf-8")
        # Salary
        cmp_ = m.resolve_salary_compare(jd, expected_raw="25-40K")
        self.assertIn(cmp_["signal"], ("✅", "⚠️", "❌", "·"))
        self.assertIn(cmp_["verdict"], ("overlap", "high_ok", "partial", "low", "face", "jd_only"))
        # Synonym surface form
        syn = m.load_synonym_map()
        hit = m.match_texts(
            "有大流量与分布式架构经验",
            "负责高并发与微服务",
            synonym_map=syn,
        )
        self.assertIn("高并发", hit.keywords.hit)
        # Track merge adds keys
        soe = m.load_synonym_map(track="soe")
        self.assertTrue(soe.get("信创") or soe.get("国产化"))

    def test_batch_manifest_ranks_good_above_weak(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            man = Path(tmp) / "m.json"
            man.write_text(
                json.dumps(
                    [
                        {
                            "id": "good",
                            "company": "G",
                            "role": "BE",
                            "resume": str(FIX / "resume_backend_good.md"),
                            "jd": str(FIX / "jd_backend_sample.md"),
                        },
                        {
                            "id": "weak",
                            "company": "W",
                            "role": "BE",
                            "resume": str(FIX / "resume_backend_weak.md"),
                            "jd": str(FIX / "jd_backend_sample.md"),
                        },
                    ]
                ),
                encoding="utf-8",
            )
            out = Path(tmp) / "out.json"
            rc = m.main(["batch", "--manifest", str(man), "--out", str(out), "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(out.read_text(encoding="utf-8"))
            scores = {r["id"]: r["score"] for r in data["results"] if r.get("score") is not None}
            self.assertGreater(scores["good"], scores["weak"])

    def test_day_plan_and_rank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv = Path(tmp) / "t.csv"
            tracker.main(["--csv", str(csv), "init"])
            tracker.main(
                [
                    "--csv",
                    str(csv),
                    "add",
                    "--company",
                    "GoodCo",
                    "--role",
                    "BE",
                    "--status",
                    "to_apply",
                    "--cv",
                    str(FIX / "resume_backend_good.md"),
                    "--source",
                    str(FIX / "jd_backend_sample.md"),
                ]
            )
            tracker.main(
                [
                    "--csv",
                    str(csv),
                    "add",
                    "--company",
                    "WeakCo",
                    "--role",
                    "BE",
                    "--status",
                    "to_apply",
                    "--cv",
                    str(FIX / "resume_backend_weak.md"),
                    "--source",
                    str(FIX / "jd_backend_sample.md"),
                ]
            )
            rc = tracker.main(["--csv", str(csv), "rank", "--json"])
            self.assertEqual(rc, 0)
            rc = tracker.main(["--csv", str(csv), "day-plan", "--limit", "2"])
            self.assertEqual(rc, 0)
            rows = tracker.read_rows(csv)
            ranked = tracker.score_tracker_rows(rows, status_filter="to_apply")
            self.assertEqual(ranked[0]["company"], "GoodCo")

    def test_dashboard_has_filter_bar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv = Path(tmp) / "t.csv"
            html = Path(tmp) / "d.html"
            tracker.main(["--csv", str(csv), "init"])
            tracker.main(
                [
                    "--csv",
                    str(csv),
                    "add",
                    "--company",
                    "C",
                    "--role",
                    "R",
                    "--status",
                    "applied",
                    "--city",
                    "杭州",
                ]
            )
            tracker.main(["--csv", str(csv), "dashboard", "--out", str(html)])
            text = html.read_text(encoding="utf-8")
            self.assertIn("filter-status", text)
            self.assertIn("data-city", text)
            self.assertIn("杭州", text)


if __name__ == "__main__":
    unittest.main()
