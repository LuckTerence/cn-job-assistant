#!/usr/bin/env python3
"""Enforce core skill surface vs optional catalog boundary (Phase 3).

Core principle: agents must not treat heavy self-hosted pointers as runnable tools.

Checks:
1. .agents/skills/* directory names ⊆ CORE_AGENTS_SKILLS (allowlist)
2. Catalog entries exist with SKILL.md + required frontmatter keys
3. Catalog items are NOT also present under .agents/skills/
4. Catalog SKILL.md contains the non-core banner
5. Core domestic skills still present

Run: python tools/lint_skill_surface.py
Exit 0 on success, 1 with failures.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("lint_skill_surface.py requires PyYAML: pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
errors: list[str] = []

# Exact allowlist for .agents/skills (directory names).
CORE_AGENTS_SKILLS = frozenset(
    {
        # Overseas portal CLIs (upstream)
        "freehire-search",
        "jobbank-search",
        "jobdanmark-search",
        "jobindex-search",
        "jobnet-search",
        "linkedin-search",
        # Domestic runnable / orchestrated
        "bosszhipin-search",
        "domestic-jobs-search",
        "application-tracker",
        "resume-match",
    }
)

# Optional catalog entries (must live ONLY under integrations/catalog/).
CATALOG_ENTRIES = frozenset(
    {
        "interview-mock",
        "job-alert",
        "referral-outreach",
        "resume-build",
        "resume-match",  # heavy upstream UI; core uses tools/match_resume.py
        "salary-negotiate",
    }
)

REQUIRED_CATALOG_FRONTMATTER = (
    "name",
    "description",
    "optional",
    "tier",
    "setup_cost",
    "requires",
    "os",
    "default_alternative",
    "upstream",
    "license_note",
)

BANNER_NEEDLE = "已移出核心 skill 面"
ALLOWED_SETUP_COST = frozenset({"low", "medium", "high", "methodology_only"})
ALLOWED_TIER = frozenset({"catalog"})


def parse_frontmatter(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        errors.append(f"{path.relative_to(ROOT)}: missing YAML frontmatter")
        return None
    end = text.find("\n---", 4)
    if end == -1:
        errors.append(f"{path.relative_to(ROOT)}: unterminated frontmatter")
        return None
    try:
        data = yaml.safe_load(text[4:end])
    except yaml.YAMLError as exc:
        errors.append(f"{path.relative_to(ROOT)}: invalid YAML: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{path.relative_to(ROOT)}: frontmatter not a mapping")
        return None
    return data


def check_core_allowlist() -> None:
    agents = ROOT / ".agents" / "skills"
    if not agents.is_dir():
        errors.append(".agents/skills/ missing")
        return
    found = {p.name for p in agents.iterdir() if p.is_dir() and not p.name.startswith(".")}
    extra = found - CORE_AGENTS_SKILLS
    missing = CORE_AGENTS_SKILLS - found
    for name in sorted(extra):
        errors.append(
            f".agents/skills/{name}/ is not on the core allowlist — "
            f"move to integrations/catalog/ or update CORE_AGENTS_SKILLS in "
            f"tools/lint_skill_surface.py deliberately"
        )
    for name in sorted(missing):
        errors.append(f"core skill missing: .agents/skills/{name}/")
    # Each core dir must have SKILL.md
    for name in sorted(found & CORE_AGENTS_SKILLS):
        if not (agents / name / "SKILL.md").is_file():
            errors.append(f".agents/skills/{name}/SKILL.md missing")


def check_catalog() -> None:
    catalog = ROOT / "integrations" / "catalog"
    if not catalog.is_dir():
        errors.append("integrations/catalog/ missing")
        return
    if not (catalog / "README.md").is_file():
        errors.append("integrations/catalog/README.md missing")

    found = {
        p.name
        for p in catalog.iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name != "__pycache__"
    }
    extra = found - CATALOG_ENTRIES
    missing = CATALOG_ENTRIES - found
    for name in sorted(extra):
        errors.append(
            f"integrations/catalog/{name}/ not in CATALOG_ENTRIES allowlist — "
            "update lint_skill_surface.py if intentional"
        )
    for name in sorted(missing):
        errors.append(f"catalog entry missing: integrations/catalog/{name}/")

    agents = ROOT / ".agents" / "skills"
    for name in sorted(found & CATALOG_ENTRIES):
        # Must not also be a core skill (except resume-match which is dual-named intentionally:
        # catalog/resume-match = heavy UI; core resume-match = local CLI)
        if name != "resume-match" and (agents / name).is_dir():
            errors.append(
                f"{name} exists in both .agents/skills/ and integrations/catalog/ — "
                "catalog-only items must not be core"
            )

        skill = catalog / name / "SKILL.md"
        if not skill.is_file():
            errors.append(f"integrations/catalog/{name}/SKILL.md missing")
            continue
        text = skill.read_text(encoding="utf-8")
        if BANNER_NEEDLE not in text:
            errors.append(
                f"integrations/catalog/{name}/SKILL.md: missing non-core banner "
                f"({BANNER_NEEDLE!r})"
            )
        data = parse_frontmatter(skill)
        if not data:
            continue
        for key in REQUIRED_CATALOG_FRONTMATTER:
            if key not in data or data[key] in (None, ""):
                errors.append(
                    f"integrations/catalog/{name}/SKILL.md: frontmatter missing {key!r}"
                )
        if data.get("optional") is not True:
            errors.append(
                f"integrations/catalog/{name}/SKILL.md: optional must be true"
            )
        if data.get("tier") not in ALLOWED_TIER:
            errors.append(
                f"integrations/catalog/{name}/SKILL.md: tier must be one of {sorted(ALLOWED_TIER)}"
            )
        if data.get("setup_cost") not in ALLOWED_SETUP_COST:
            errors.append(
                f"integrations/catalog/{name}/SKILL.md: setup_cost must be one of "
                f"{sorted(ALLOWED_SETUP_COST)}"
            )
        # Soft: description should not claim "已集成" as if core
        desc = str(data.get("description") or "")
        if "开箱即用" in desc:
            errors.append(
                f"integrations/catalog/{name}/SKILL.md: description claims 开箱即用"
            )


def check_no_catalog_in_claude_skills() -> None:
    """Catalog names should not reappear as .claude/skills dirs."""
    claude = ROOT / ".claude" / "skills"
    if not claude.is_dir():
        return
    for name in CATALOG_ENTRIES:
        if name == "resume-match":
            continue
        if (claude / name).is_dir():
            errors.append(f".claude/skills/{name}/ should not exist (catalog-only)")


def main() -> int:
    check_core_allowlist()
    check_catalog()
    check_no_catalog_in_claude_skills()
    if errors:
        print(f"lint_skill_surface: {len(errors)} failure(s)")
        for err in errors:
            print(f"  - {err}")
        return 1
    print(
        f"lint_skill_surface: OK "
        f"({len(CORE_AGENTS_SKILLS)} core agents skills, "
        f"{len(CATALOG_ENTRIES)} catalog entries)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
