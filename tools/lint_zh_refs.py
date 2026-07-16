#!/usr/bin/env python3
"""Lint domestic (China) workflow path references.

Ensures /apply-zh, /da-zhaohu, /setup-zh, and related guides point at files
that exist — catches empty zh/ directories and broken template paths.

Run: python tools/lint_zh_refs.py
Exit 0 on success, 1 with failures.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors: list[str] = []

# Files that must exist for the domestic loop to be usable.
REQUIRED_PATHS = [
    "CLAUDE.zh.md",
    "MODELS.zh.md",
    "README.zh.md",
    "docs/QUICKSTART.zh.md",
    "docs/AGENT_PROMPT.zh.md",
    "docs/RELEASE-1.0.zh.md",
    ".claude/commands/apply-zh.md",
    ".claude/commands/da-zhaohu.md",
    ".claude/commands/setup-zh.md",
    ".claude/commands/outcome.md",
    "tools/flow.py",
    "tools/split_jds.py",
    ".claude/skills/job-application-assistant/04-job-evaluation.md",
    ".claude/skills/job-application-assistant/08-resume-zh.md",
    ".claude/skills/job-application-assistant/09-da-zhaohu-zh.md",
    "templates/zh/resume_internet.md",
    "templates/zh/resume_soe.md",
    "templates/zh/resume_foreign.md",
    "templates/zh/resume_civil.md",
    "templates/zh/resume_freshgrad.md",
    "templates/zh/da-zhaohu-examples.md",
    "documents/zh/.gitkeep",
    "tools/tracker.py",
    "tools/install_domestic_search.py",
    "tools/match_resume.py",
    ".agents/skills/bosszhipin-search/SKILL.md",
    ".agents/skills/domestic-jobs-search/SKILL.md",
    ".agents/skills/application-tracker/SKILL.md",
    ".agents/skills/resume-match/SKILL.md",
    "tests/fixtures/jd_backend_sample.md",
    "tests/fixtures/resume_backend_good.md",
]

# Paths that commands / guides commonly mention as relative repo paths.
SCAN_FILES = [
    ".claude/commands/apply-zh.md",
    ".claude/commands/da-zhaohu.md",
    ".claude/commands/setup-zh.md",
    ".claude/skills/job-application-assistant/08-resume-zh.md",
    ".claude/skills/job-application-assistant/09-da-zhaohu-zh.md",
    ".agents/skills/bosszhipin-search/SKILL.md",
    ".agents/skills/domestic-jobs-search/SKILL.md",
    ".agents/skills/application-tracker/SKILL.md",
]

# Explicit repo-relative path tokens we care about (not every bare word).
PATH_RE = re.compile(
    r"(?:"
    r"\.claude/(?:commands|skills)/[A-Za-z0-9_./\-]+\.md"
    r"|templates/zh/[A-Za-z0-9_./\-]+\.md"
    r"|documents/zh/"
    r"|tools/[A-Za-z0-9_./\-]+\.py"
    r"|CLAUDE\.zh\.md"
    r"|MODELS\.zh\.md"
    r")"
)


def check_required() -> None:
    for rel in REQUIRED_PATHS:
        path = ROOT / rel
        if not path.exists():
            errors.append(f"missing required path: {rel}")


def check_scanned_refs() -> None:
    for rel in SCAN_FILES:
        path = ROOT / rel
        if not path.is_file():
            errors.append(f"scan target missing: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        for match in PATH_RE.findall(text):
            token = match.rstrip("/")
            # documents/zh/ is a directory; allow with or without trailing files
            if token == "documents/zh" or token.startswith("documents/zh/"):
                if not (ROOT / "documents" / "zh").is_dir():
                    errors.append(f"{rel}: references documents/zh/ but directory missing")
                continue
            # templates with track placeholder — skip dynamic
            if "<" in token or "*" in token:
                continue
            candidate = ROOT / token
            if not candidate.exists():
                errors.append(f"{rel}: broken path reference {token!r}")


def check_no_misleading_empty_zh() -> None:
    """job-application-assistant/zh/ was historically empty and confusing."""
    empty_trap = ROOT / ".claude/skills/job-application-assistant/zh"
    if empty_trap.is_dir():
        contents = [p for p in empty_trap.iterdir() if p.name != ".gitkeep"]
        if not contents:
            errors.append(
                ".claude/skills/job-application-assistant/zh/ exists but is empty — "
                "08/09 live in the parent directory; remove the empty zh/ folder "
                "to avoid README/agent confusion"
            )


def check_catalog_optional_moved() -> None:
    """Heavy optional skills should not pretend to be runnable core skills."""
    # Core domestic skills that must remain in .agents/skills
    for name in (
        "bosszhipin-search",
        "domestic-jobs-search",
        "application-tracker",
        "resume-match",
    ):
        if not (ROOT / ".agents/skills" / name / "SKILL.md").is_file():
            errors.append(f"core skill missing from .agents/skills: {name}")
    # Catalog should exist after Phase-1 reorg
    catalog = ROOT / "integrations" / "catalog"
    if not catalog.is_dir():
        errors.append("integrations/catalog/ missing — optional heavy skills should live there")
        return
    readme = catalog / "README.md"
    if not readme.is_file():
        errors.append("integrations/catalog/README.md missing")
    if not (ROOT / "ARCHITECTURE.zh.md").is_file():
        errors.append("ARCHITECTURE.zh.md missing (core vs catalog map)")
    # Defer detailed catalog allowlist to lint_skill_surface.py


def main() -> int:
    check_required()
    check_scanned_refs()
    check_no_misleading_empty_zh()
    check_catalog_optional_moved()
    if errors:
        print(f"lint_zh_refs: {len(errors)} failure(s)")
        for err in errors:
            print(f"  - {err}")
        return 1
    print(
        f"lint_zh_refs: OK ({len(REQUIRED_PATHS)} required paths, "
        f"{len(SCAN_FILES)} files scanned)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
