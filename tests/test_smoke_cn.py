"""1.0 gate: product-path smoke script stays green offline."""

from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SMOKE = ROOT / "scripts" / "smoke_cn.sh"


class SmokeCnTests(unittest.TestCase):
    def test_smoke_cn_script_runs(self) -> None:
        self.assertTrue(SMOKE.is_file())
        # Avoid recursion if a future smoke re-enters unittest
        env = {**os.environ, "SMOKE_NESTED": "1"}
        proc = subprocess.run(
            ["bash", str(SMOKE)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=(proc.stdout or "")[-3000:] + "\n" + (proc.stderr or "")[-3000:],
        )
        self.assertIn("smoke_cn OK", proc.stdout)


if __name__ == "__main__":
    unittest.main()
