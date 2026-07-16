"""Release packaging consistency for 1.0.x."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class ReleaseReadyTests(unittest.TestCase):
    def test_check_release_ready(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "check_release_ready.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("OK", proc.stdout)


if __name__ == "__main__":
    unittest.main()
