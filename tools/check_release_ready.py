#!/usr/bin/env python3
"""Assert 1.0.x release packaging consistency (stdlib only)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    errors: list[str] = []
    skill = json.loads((ROOT / "skill.json").read_text(encoding="utf-8"))
    ver = skill.get("version", "")
    if not re.match(r"^1\.\d+\.\d+$", ver):
        errors.append(f"skill.json version not 1.x.y: {ver!r}")

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## [{ver}]" not in changelog:
        errors.append(f"CHANGELOG.md missing section ## [{ver}]")

    required = [
        "docs/QUICKSTART.zh.md",
        "docs/AGENT_PROMPT.zh.md",
        "docs/RELEASE-1.0.zh.md",
        "docs/github-release-v1.0.0.md",
        "docs/dist-notes-1.0.zh.md",
        "scripts/smoke_cn.sh",
        "scripts/demo.sh",
        "tools/flow.py",
        "tools/split_jds.py",
        "tools/tracker.py",
        "tools/match_resume.py",
        ".claude/commands/setup-zh.md",
        ".claude/commands/apply-zh.md",
        ".github/ISSUE_TEMPLATE/using.yml",
        ".github/ISSUE_TEMPLATE/pain.yml",
    ]
    for rel in required:
        if not (ROOT / rel).is_file():
            errors.append(f"missing required release file: {rel}")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for needle in ("QUICKSTART", "make check", "1.0", "我在用"):
        if needle not in readme:
            errors.append(f"README.md missing {needle!r}")

    # synonym + idf defaults
    for rel in ("config/synonyms.default.json", "config/idf.default.json"):
        if not (ROOT / rel).is_file():
            errors.append(f"missing {rel}")

    if errors:
        print("check_release_ready: FAIL", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"check_release_ready: OK (version {ver})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
