"""Tests for tools/install_domestic_search.py (no network)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import install_domestic_search as installer  # noqa: E402


class InstallDomesticSearchTests(unittest.TestCase):
    def test_status_exit_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rc = installer.main(["--vendor", tmp, "status"])
            self.assertEqual(rc, 0)

    def test_smoke_without_backends(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rc = installer.main(["--vendor", tmp, "smoke"])
            # tracker.py exists in real repo → should pass
            self.assertEqual(rc, 0)

    def test_get_jobs_status_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            st = installer.get_jobs_status(Path(tmp))
            self.assertFalse(st["installed"])

    def test_get_jobs_status_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "get_jobs"
            dest.mkdir()
            (dest / "README.md").write_text("x", encoding="utf-8")
            st = installer.get_jobs_status(Path(tmp))
            self.assertTrue(st["installed"])

    def test_install_get_jobs_requires_git(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(installer, "which", return_value=None):
                rc = installer.main(["--vendor", tmp, "install-get-jobs"])
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
