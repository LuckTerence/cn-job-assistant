#!/usr/bin/env python3
"""Lint the repo's skill, command, and settings files.

Run from anywhere: python tools/lint_skills.py

Checks:
- Every SKILL.md (.claude/skills/*, .agents/skills/*) has YAML frontmatter that
  parses, with non-empty `name` and `description` keys
- `allowed-tools` entries of the form `Bash(bun run <path> *)` point at files
  that exist (skill paths resolve relative to the repo root and to .agents/)
- Every .claude/commands/*.md starts with a `# /<name>` title
- .claude/settings.json is valid JSON with a permissions.allow list

Exit code 0 on success, 1 with a failure list otherwise.
"""

import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("lint_skills.py requires PyYAML: pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
errors: list[str] = []

# Tokens that look command-like but are not slash commands (English words,
# path fragments, file extensions, common nouns). Keeps the /command reference
# scan from flagging prose and markdown links as broken command references.
# Real command names are auto-skipped (matched against actual command files),
# so they must NOT appear here.
COMMAND_DENYLIST = {
    "http", "https", "claude", "agents", "github", "com", "www", "path",
    "tmp", "bin", "usr", "etc", "var", "home", "opt", "srv", "mnt",
    "data", "docs", "src", "lib", "dist", "api", "node_modules",
    "users", "readme", "zh", "md", "tex", "json", "pdf", "csv", "yml",
    "yaml", "txt", "cv", "cover", "letters", "applications", "documents",
    "templates", "skills", "commands", "test", "example", "examples",
    "version", "local", "global", "system", "user", "admin", "root",
    "file", "files", "dir", "directory", "folder", "git", "bash", "sh",
    "zsh", "python", "python3", "node", "npm", "bun", "use", "using",
    "via", "per", "vs", "to", "from", "with", "for", "and", "or", "in",
    "on", "at", "by", "of", "as", "is", "it", "this", "that", "not",
    "no", "yes", "if", "else", "then", "do", "done", "end", "fi", "run",
    "set", "get", "new", "open", "close", "add", "remove", "delete",
    "update", "create", "help", "info", "list", "show", "view", "edit",
    "read", "write", "your", "my", "a", "an", "the", "you", "we", "they",
    "he", "she", "i", "me", "our", "offer", "cli",
}


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def check_skill(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        errors.append(f"{rel(path)}: missing YAML frontmatter (file must start with ---)")
        return
    end = text.find("\n---", 4)
    if end == -1:
        errors.append(f"{rel(path)}: unterminated YAML frontmatter")
        return
    try:
        data = yaml.safe_load(text[4:end])
    except yaml.YAMLError as exc:
        errors.append(f"{rel(path)}: frontmatter is not valid YAML: {exc}")
        return
    if not isinstance(data, dict):
        errors.append(f"{rel(path)}: frontmatter did not parse to a mapping")
        return
    for key in ("name", "description"):
        if not data.get(key):
            errors.append(f"{rel(path)}: frontmatter missing required key '{key}'")

    allowed = data.get("allowed-tools", "")
    if isinstance(allowed, str):
        for match in re.finditer(r"bun run ([^\s)]+)", allowed):
            target = match.group(1).rstrip("*")
            if not target or target.endswith("/"):
                continue
            # Targets may contain globs (e.g. .agents/skills/*/cli/src/cli.ts);
            # require at least one existing file to match.
            if "*" in target:
                if not list(ROOT.glob(target)) and not list((ROOT / ".agents").glob(target)):
                    errors.append(f"{rel(path)}: allowed-tools glob matches no files: {target}")
            else:
                candidates = [ROOT / target, ROOT / ".agents" / target]
                if not any(c.is_file() for c in candidates):
                    errors.append(f"{rel(path)}: allowed-tools references a missing file: {target}")


def check_command(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").lstrip().splitlines()
    first = lines[0] if lines else ""
    if not first.startswith("# /"):
        errors.append(f"{rel(path)}: command file must start with a '# /<name>' title (found: {first[:50]!r})")


def check_settings() -> None:
    path = ROOT / ".claude" / "settings.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f".claude/settings.json: {exc}")
        return
    if not isinstance(data.get("permissions", {}).get("allow"), list):
        errors.append(".claude/settings.json: expected permissions.allow to be a list")


def _command_stems() -> set[str]:
    """Command names = `.claude/commands/<stem>.md` (Claude Code keys on the
    filename, not the H1 title, which may be localized e.g. `/打招呼`)."""
    return {p.stem for p in (ROOT / ".claude" / "commands").glob("*.md")}


def _skill_names() -> set[str]:
    """Skill `name` values — skills can also be invoked by `/<name>`."""
    names: set[str] = set()
    for path in list(ROOT.glob(".claude/skills/*/SKILL.md")) + list(ROOT.glob(".agents/skills/*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        m = re.match(r"---\n(.*?)\n---", text, re.DOTALL)
        if not m:
            continue
        try:
            data = yaml.safe_load(m.group(1))
        except yaml.YAMLError:
            continue
        if isinstance(data, dict) and data.get("name"):
            names.add(str(data["name"]))
    return names


def _resolve_ref(ref: str) -> bool:
    """A referenced .md may be repo-root-relative, a bare basename living in the
    assistant skill dir, or a path relative to a skill dir. Try all."""
    if ref.startswith("/"):
        ref = ref[1:]
    candidates = [
        ROOT / ref,
        ROOT / ".claude" / ref,
        ROOT / ".agents" / ref,
        ROOT / ".claude" / "skills" / ref,
        ROOT / ".agents" / "skills" / ref,
    ]
    if "/" not in ref:
        candidates.append(ROOT / ".claude" / "skills" / "job-application-assistant" / ref)
        candidates += list(ROOT.glob(".agents/skills/*/" + ref))
    return any(c.exists() for c in candidates)


# Files that commands create at runtime (not expected to exist on disk yet).
RUNTIME_GENERATED = {
    "outcome.md", "job_posting.md", "TEMPLATE.md", "search-queries.md",
    # Domestic (`/apply-zh`) archive variants, generated by `/outcome` into
    # documents/applications/<company>_<role>/ at runtime (mirror of the
    # international cv_draft.tex / cover_letter.tex which are also runtime).
    "cv_draft.md", "cover_letter.md",
}
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def check_crossrefs(command_stems: set[str], skill_names: set[str]) -> None:
    """Cross-reference layer: catches logic bugs the structural checks miss.

    - Every `/<name>` reference across all .md files must resolve to a real
      command file OR a skill `name`. (This is what would have caught the
      "domestic profile wired to a non-existent command" class of bug.)
    - Every backticked `.md` path a command/skill tells the model to Read must
      actually exist on disk (multi-location resolution; template placeholders,
      globs, and runtime-generated filenames are skipped).
    - Every command file should be mentioned in at least one README (warning only).

    Generated CLI docs (cli/README.md, url-reference.md) are excluded — they are
    auto-generated and full of HTML closing tags that look like /commands.
    """
    invocable = command_stems | skill_names
    cmd_re = re.compile(r"(?<![A-Za-z0-9/])/([a-z][a-z0-9-]+)")
    path_re = re.compile(r"`([^`]+\.md)`")
    readmes = {p for p in ROOT.glob("README*.md")}
    mentioned: set[str] = set()

    for path in ROOT.rglob("*.md"):
        if "node_modules" in path.parts:
            continue
        # Skip auto-generated CLI docs (HTML tags / generated content).
        if path.name == "url-reference.md" or (path.name == "README.md" and "cli" in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        is_readme = path in readmes

        # 1. /command or /skill references
        for m in cmd_re.finditer(text):
            token = m.group(1)
            if token in invocable:
                if is_readme and token in command_stems:
                    mentioned.add(token)
                continue
            if token in COMMAND_DENYLIST:
                continue
            before = text[m.start() - 1] if m.start() > 0 else ""
            if before == "<":
                continue  # HTML closing tag, e.g. </li>
            after = text[m.end():m.end() + 1]
            if after in ("/", ".", ":", ">", ")"):
                continue
            errors.append(
                f"{rel(path)}: references /{token} but no command file "
                f".claude/commands/{token}.md or skill named '{token}' exists"
            )

        # 2. backticked .md file references must exist
        for m in path_re.finditer(text):
            ref = m.group(1).strip()
            if ref.startswith("http"):
                continue
            if "<" in ref or ">" in ref or "*" in ref or "{{" in ref:
                continue  # template placeholder / glob, e.g. resume_<track>.md
            if "YYYY" in ref or "MM-DD" in ref or _DATE_RE.search(ref):
                continue  # date-stamped runtime file
            if ref in RUNTIME_GENERATED:
                continue
            if not _resolve_ref(ref):
                errors.append(
                    f"{rel(path)}: references file `{ref}` but it does not exist on disk"
                )

    # 3. every command file should be documented in a README (warning only)
    for name in command_stems:
        if name not in mentioned:
            print(f"note: command /{name} is not mentioned in any README*.md")


# ---------------------------------------------------------------------------
# Domestic-awareness regression guards.
#
# This fork retrofitted a Chinese ("domestic") application flow into commands
# that were originally international-only. The recurring bug class: a command
# is made domestic-aware (handles documents/zh/ output) but still (a) only reads
# the international .tex archive, so a domestic application archived as .md is
# silently skipped, and/or (b) only reads the international profile (01/02), so
# a domestic user's profile comes back empty. /outcome and /interview both hit
# this. These guards turn that class into a lint failure.
#
# A command is "domestic-aware" if it references `documents/zh/` or its filename
# carries the `-zh` marker. International-only commands are deliberately out of
# scope (e.g. /setup reads 01/02 and must NOT be forced onto CLAUDE.zh.md).
# ---------------------------------------------------------------------------
def _is_domestic_aware(path: Path, text: str) -> bool:
    if "documents/zh/" in text:
        return True
    stem = path.stem
    if stem.endswith("-zh") or "-zh" in stem:
        return True
    return False


def check_domestic_awareness(commands) -> None:
    tex_archive = re.compile(r"cv_draft\.tex|cover_letter\.tex")
    md_archive = re.compile(r"cv_draft\.md|cover_letter\.md")
    intl_profile = re.compile(r"01-candidate-profile\.md|02-behavioral-profile\.md")
    dom_profile = "CLAUDE.zh.md"
    for path in commands:
        text = path.read_text(encoding="utf-8")
        if not _is_domestic_aware(path, text):
            continue
        if tex_archive.search(text) and not md_archive.search(text):
            errors.append(
                f"{rel(path)}: domestic-aware command reads the international "
                f".tex archive (cv_draft.tex / cover_letter.tex) but not the "
                f"domestic .md archive (cv_draft.md / cover_letter.md) - "
                f"domestic applications archived as .md would be skipped"
            )
        if intl_profile.search(text) and dom_profile not in text:
            errors.append(
                f"{rel(path)}: domestic-aware command reads the international "
                f"profile (01-candidate-profile.md / 02-behavioral-profile.md) "
                f"but not {dom_profile} - domestic profile would be empty"
            )


def main() -> int:
    skills = sorted(ROOT.glob(".claude/skills/*/SKILL.md")) + sorted(ROOT.glob(".agents/skills/*/SKILL.md"))
    commands = sorted((ROOT / ".claude" / "commands").glob("*.md"))
    if not skills:
        errors.append("no SKILL.md files found - glob roots are wrong or the tree moved")
    if not commands:
        errors.append("no command files found under .claude/commands/")

    for skill in skills:
        check_skill(skill)
    for command in commands:
        check_command(command)
    check_settings()
    check_crossrefs(_command_stems(), _skill_names())
    check_domestic_awareness(commands)

    if errors:
        print(f"lint_skills: {len(errors)} failure(s)")
        for err in errors:
            print(f"  - {err}")
        return 1
    print(f"lint_skills: OK ({len(skills)} skills, {len(commands)} commands, settings.json, crossrefs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
