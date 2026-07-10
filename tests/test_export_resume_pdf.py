"""Tests for tools/export_resume_pdf.py."""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import export_resume_pdf as exp  # noqa: E402

DEMO_MD = ROOT / "examples" / "demo" / "resume_星云科技.md"


class ExportResumePdfTests(unittest.TestCase):
    def test_md_to_html_has_identity_and_sections(self) -> None:
        md = DEMO_MD.read_text(encoding="utf-8")
        html = exp.md_to_resume_html(md, title="测试")
        self.assertIn("<h1>", html)
        self.assertIn("专业技能", html)
        self.assertIn("<ul>", html)
        self.assertIn("PingFang", html)

    def test_export_pdf_when_chrome_available(self) -> None:
        if not exp.find_chrome():
            self.skipTest("Chrome/Chromium/Edge not installed")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "r.pdf"
            path = exp.export_pdf(DEMO_MD, out)
            self.assertTrue(path.is_file())
            self.assertGreater(path.stat().st_size, 1000)
            data = path.read_bytes()
            self.assertTrue(data.startswith(b"%PDF"))
            pages = len(re.findall(rb"/Type\s*/Page[^s]", data))
            self.assertEqual(pages, 1, msg=f"expected 1 page, got {pages}")

    def test_cli_html_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "r.pdf"
            rc = exp.main(
                ["--input", str(DEMO_MD), "--output", str(out), "--html-only"]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(out.with_suffix(".html").is_file() or Path(str(out) + ".html").is_file() or list(Path(tmp).glob("*.html")))


if __name__ == "__main__":
    unittest.main()
