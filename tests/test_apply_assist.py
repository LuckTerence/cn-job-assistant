"""Tests for tools/apply_assist.py (no network, no real boss)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import apply_assist as aa  # noqa: E402


def _auto_cfg(max_batch: int = 5) -> str:
    return (
        "mode: auto\n"
        "risk_acknowledgement:\n"
        "  platform_tos: true\n"
        "  account_ban: true\n"
        "  personal_use_only: true\n"
        "auto:\n"
        f"  max_batch: {max_batch}\n"
        "  default_dry_run: true\n"
    )


class ApplyAssistTests(unittest.TestCase):
    def test_default_mode_manual(self) -> None:
        with mock.patch.object(aa, "CONFIG", Path("/nonexistent/apply_mode.yaml")):
            with mock.patch.dict("os.environ", {}, clear=False):
                # ensure no env override
                import os

                os.environ.pop("CN_JOB_APPLY_MODE", None)
                os.environ.pop("CN_JOB_APPLY_CONFIG", None)
                cfg = aa.load_config()
        self.assertEqual(cfg["mode"], "manual")
        self.assertFalse(aa.risks_all_acked(cfg))

    def test_explain_and_status(self) -> None:
        self.assertEqual(aa.main(["explain"]), 0)
        self.assertEqual(aa.main(["status"]), 0)

    def test_set_mode_semi(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "apply_mode.yaml"
            with mock.patch.object(aa, "CONFIG", cfg_path):
                with mock.patch.object(aa, "CONFIG_DIR", Path(tmp)):
                    with mock.patch.object(aa, "EXAMPLE", ROOT / "config" / "apply_mode.example.yaml"):
                        rc = aa.main(["set-mode", "semi"])
                        self.assertEqual(rc, 0)
                        self.assertTrue(cfg_path.is_file())
                        text = cfg_path.read_text(encoding="utf-8")
                        self.assertIn("mode: semi", text)

    def test_auto_greet_blocked_without_mode(self) -> None:
        with mock.patch.object(aa, "CONFIG", Path("/nonexistent/x.yaml")):
            rc = aa.main(
                [
                    "auto-greet",
                    "--security-id",
                    "abc",
                    "--i-understand-ban-risk",
                    "--execute",
                ]
            )
        self.assertEqual(rc, 2)

    def test_auto_greet_blocked_without_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "apply_mode.yaml"
            cfg_path.write_text(_auto_cfg(), encoding="utf-8")
            with mock.patch.object(aa, "CONFIG", cfg_path):
                rc = aa.main(["auto-greet", "--security-id", "abc"])
        self.assertEqual(rc, 2)

    def test_auto_greet_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "apply_mode.yaml"
            cfg_path.write_text(_auto_cfg(), encoding="utf-8")
            with mock.patch.object(aa, "CONFIG", cfg_path):
                with mock.patch.object(aa.shutil, "which", return_value="/usr/bin/boss"):
                    rc = aa.main(
                        [
                            "auto-greet",
                            "--security-id",
                            "sec123",
                            "--i-understand-ban-risk",
                        ]
                    )
        self.assertEqual(rc, 0)

    def test_auto_greet_text_file_rejected_when_cli_has_no_message_flag(self) -> None:
        """Honest fail: do not pretend --text-file is passed to boss."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "apply_mode.yaml"
            cfg_path.write_text(_auto_cfg(), encoding="utf-8")
            text_f = Path(tmp) / "greet.md"
            text_f.write_text("你好，这是定制话术", encoding="utf-8")
            fake_help = mock.Mock(
                returncode=0,
                stdout="Usage: boss greet <securityId> [--json]\n",
                stderr="",
            )
            with mock.patch.object(aa, "CONFIG", cfg_path):
                with mock.patch.object(aa.shutil, "which", return_value="/usr/bin/boss"):
                    with mock.patch.object(aa.subprocess, "run", return_value=fake_help):
                        rc = aa.main(
                            [
                                "auto-greet",
                                "--security-id",
                                "sec123",
                                "--text-file",
                                str(text_f),
                                "--i-understand-ban-risk",
                            ]
                        )
        self.assertEqual(rc, 2)

    def test_auto_greet_text_file_passed_when_cli_supports_message_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "apply_mode.yaml"
            cfg_path.write_text(_auto_cfg(), encoding="utf-8")
            text_f = Path(tmp) / "greet.md"
            text_f.write_text("定制话术正文", encoding="utf-8")
            fake_help = mock.Mock(
                returncode=0,
                stdout="Usage: boss greet <id> [--message-file PATH] [--json]\n",
                stderr="",
            )
            with mock.patch.object(aa, "CONFIG", cfg_path):
                with mock.patch.object(aa.shutil, "which", return_value="/usr/bin/boss"):
                    with mock.patch.object(aa.subprocess, "run", return_value=fake_help):
                        rc = aa.main(
                            [
                                "auto-greet",
                                "--security-id",
                                "sec123",
                                "--text-file",
                                str(text_f),
                                "--i-understand-ban-risk",
                            ]
                        )
        self.assertEqual(rc, 0)

    def test_auto_greet_max_batch_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "apply_mode.yaml"
            cfg_path.write_text(_auto_cfg(max_batch=2), encoding="utf-8")
            with mock.patch.object(aa, "CONFIG", cfg_path):
                with mock.patch.object(aa.shutil, "which", return_value="/usr/bin/boss"):
                    rc = aa.main(
                        [
                            "auto-greet",
                            "--security-id",
                            "a,b,c",
                            "--i-understand-ban-risk",
                        ]
                    )
        self.assertEqual(rc, 2)

    def test_parse_security_ids(self) -> None:
        self.assertEqual(aa.parse_security_ids("a, b;c"), ["a", "b", "c"])
        self.assertEqual(aa.parse_security_ids(""), [])

    def test_copy_to_clipboard_windows_powershell(self) -> None:
        fake = mock.Mock(returncode=0)

        def which(name: str):
            if name in ("pbcopy", "wl-copy", "xclip", "xsel", "clip"):
                return None
            if name in ("powershell", "pwsh"):
                return f"/mock/{name}"
            return None

        with mock.patch.object(aa.sys, "platform", "win32"):
            with mock.patch.object(aa.shutil, "which", side_effect=which):
                with mock.patch.object(aa.subprocess, "run", return_value=fake) as run:
                    ok = aa.copy_to_clipboard("你好话术")
        self.assertTrue(ok)
        self.assertTrue(run.called)
        args = run.call_args[0][0]
        self.assertIn("Set-Clipboard", " ".join(args))

    def test_semi_with_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            text_f = Path(tmp) / "greet.md"
            text_f.write_text("你好，这是演示话术", encoding="utf-8")
            with mock.patch.object(aa, "copy_to_clipboard", return_value=True):
                with mock.patch.object(aa.webbrowser, "open", return_value=True):
                    rc = aa.main(
                        [
                            "semi",
                            "--url",
                            "https://example.com/job/1",
                            "--text-file",
                            str(text_f),
                            "--company",
                            "示例",
                        ]
                    )
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
