"""Wrapper so pytest/unittest discovery runs lint_zh_refs."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import lint_zh_refs  # noqa: E402


class ZhRefsTests(unittest.TestCase):
    def test_lint_zh_refs_passes(self) -> None:
        # lint_zh_refs mutates module-level errors; reset between runs
        lint_zh_refs.errors.clear()
        rc = lint_zh_refs.main()
        self.assertEqual(rc, 0, msg="\n".join(lint_zh_refs.errors))


if __name__ == "__main__":
    unittest.main()
