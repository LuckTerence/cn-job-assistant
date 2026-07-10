"""Tests for tools/lint_skill_surface.py."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import lint_skill_surface  # noqa: E402


class SkillSurfaceTests(unittest.TestCase):
    def test_lint_passes(self) -> None:
        lint_skill_surface.errors.clear()
        rc = lint_skill_surface.main()
        self.assertEqual(rc, 0, msg="\n".join(lint_skill_surface.errors))

    def test_core_and_catalog_disjoint_except_resume_match(self) -> None:
        overlap = lint_skill_surface.CORE_AGENTS_SKILLS & lint_skill_surface.CATALOG_ENTRIES
        self.assertEqual(overlap, {"resume-match"})

    def test_catalog_dirs_match_allowlist(self) -> None:
        catalog = ROOT / "integrations" / "catalog"
        found = {p.name for p in catalog.iterdir() if p.is_dir() and not p.name.startswith(".")}
        self.assertEqual(found, set(lint_skill_surface.CATALOG_ENTRIES))


if __name__ == "__main__":
    unittest.main()
