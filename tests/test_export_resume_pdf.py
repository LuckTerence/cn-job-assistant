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
    def test_parse_and_html(self) -> None:
        md = DEMO_MD.read_text(encoding="utf-8")
        res = exp.parse_resume_md(md)
        self.assertTrue(res.name)
        self.assertGreaterEqual(len(res.sections), 1)
        html = exp.resume_to_html(res)
        self.assertIn("<h1>", html)
        self.assertIn("专业技能", html)
        self.assertIn("<ul>", html)

    def test_typst_source_generates(self) -> None:
        md = DEMO_MD.read_text(encoding="utf-8")
        res = exp.parse_resume_md(md)
        typ = exp.resume_to_typst(res)
        self.assertIn("#resume(", typ)
        self.assertIn("专业技能", typ)
        self.assertIn("#let resume", typ)

    def test_export_pdf_auto(self) -> None:
        if not exp.find_typst() and not exp.find_chrome():
            self.skipTest("no typst and no chrome")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "r.pdf"
            path, backend = exp.export_pdf(DEMO_MD, out)
            self.assertTrue(path.is_file())
            self.assertGreater(path.stat().st_size, 1000)
            self.assertTrue(path.read_bytes().startswith(b"%PDF"))
            self.assertIn(backend, ("typst", "chrome", "pandoc"))
            pages = len(re.findall(rb"/Type\s*/Page[^s]", path.read_bytes()))
            self.assertEqual(pages, 1, msg=f"backend={backend} pages={pages}")

    def test_cli_which(self) -> None:
        self.assertEqual(exp.main(["--which"]), 0)

    def test_cli_html_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "r.pdf"
            rc = exp.main(
                ["--input", str(DEMO_MD), "--output", str(out), "--html-only"]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(out.with_suffix(".html").is_file())


if __name__ == "__main__":
    unittest.main()
