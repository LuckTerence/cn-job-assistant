"""Tests for competitor-inspired humanization (1.1 features)."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "tools"))

import check_profile_resume as cpr  # noqa: E402
import normalize_job_export as nje  # noqa: E402
import tracker  # noqa: E402


class HumanizeV11Tests(unittest.TestCase):
    def test_normalize_boss_agent_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.json"
            raw.write_text(
                json.dumps(
                    {
                        "ok": True,
                        "data": [
                            {
                                "brandName": "信封科技",
                                "jobName": "后端",
                                "cityName": "杭州",
                                "salaryDesc": "25-40K",
                                "jobUrl": "https://www.zhipin.com/job_detail/x",
                            }
                        ],
                        "error": None,
                        "hints": [],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            out = Path(tmp) / "jobs.json"
            rc = nje.main(["-i", str(raw), "-o", str(out)])
            self.assertEqual(rc, 0)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["jobs"][0]["company"], "信封科技")
            self.assertEqual(data["jobs"][0]["role"], "后端")

    def test_check_profile_flags_metrics(self) -> None:
        profile = "姓名：测\n技能：Java Redis\n"
        resume = "精通 Java\n负责系统，QPS 提升 300%，服务 100 万人日\n"
        r = cpr.check(profile, resume)
        types = {w["type"] for w in r["warnings"]}
        self.assertIn("metric_not_in_profile", types)

    def test_weekly_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv = Path(tmp) / "t.csv"
            tracker.main(["--csv", str(csv), "init"])
            tracker.main(
                [
                    "--csv",
                    str(csv),
                    "add",
                    "--company",
                    "A",
                    "--role",
                    "r",
                    "--status",
                    "applied",
                ]
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = tracker.main(["--csv", str(csv), "weekly-report"])
            self.assertEqual(rc, 0)
            self.assertIn("战报", buf.getvalue())

    def test_command_map_exists(self) -> None:
        p = ROOT / "docs" / "COMMAND_MAP.zh.md"
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        self.assertIn("day-plan", text)
        self.assertIn("boss-agent-cli", text)

    def test_flow_ingest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "r.json"
            raw.write_text(
                json.dumps(
                    {
                        "ok": True,
                        "data": [
                            {"company": "FlowIn", "title": "Dev", "platform": "Boss直聘"}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            csv = Path(tmp) / "t.csv"
            out = Path(tmp) / "j.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "flow.py"),
                    "--csv",
                    str(csv),
                    "ingest",
                    "-i",
                    str(raw),
                    "-o",
                    str(out),
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            rows = tracker.read_rows(csv)
            self.assertTrue(any(r["company"] == "FlowIn" for r in rows))


if __name__ == "__main__":
    unittest.main()
