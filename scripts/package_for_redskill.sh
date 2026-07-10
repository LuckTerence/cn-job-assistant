#!/usr/bin/env bash
# 打包小红书 Red Skill 上传包（UTF-8 中文根目录 + name/description 硬校验）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 <<'PY'
from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(".").resolve()
SKILL_NAME = "AI求职助理"
NAME_EXPECTED = "AI求职助理"
DESC_EXPECTED = (
    "帮你在本地做求职材料：按岗位描述定制中文简历与 Boss 话术，导出可投 PDF，看匹配度，"
    "记录投了哪些公司。默认你自己点发送；需要时再开半自动复制话术或全自动（风险自担）。"
    "适合用 Agent / 命令行的求职者。"
)

skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
assert skill_text.startswith("---\n"), "SKILL.md 必须以 --- frontmatter 开头"
fm_m = re.match(r"^---\n(.*?)\n---\s*\n", skill_text, re.S)
assert fm_m, "SKILL.md frontmatter 解析失败"
fm = fm_m.group(1)
keys = [ln.split(":", 1)[0].strip() for ln in fm.splitlines() if re.match(r"^[a-zA-Z_]", ln)]
assert keys == ["name", "description"], f"frontmatter 只能 name+description，实际 {keys}"
name = re.search(r"(?m)^name:\s*(.+)$", fm).group(1).strip().strip("\"'")
desc = re.search(r"(?m)^description:\s*(.+)$", fm).group(1).strip().strip("\"'")
assert name == NAME_EXPECTED, f"name 不一致: {name!r} != {NAME_EXPECTED!r}"
assert desc == DESC_EXPECTED, f"description 不一致:\n文件={desc!r}\n期望={DESC_EXPECTED!r}"

stage_parent = Path(tempfile.mkdtemp())
staging = stage_parent / SKILL_NAME
staging.mkdir(parents=True)

INCLUDE = [
    "SKILL.md", "LICENSE", "NOTICE", "README.md", "README.zh.md",
    "REDSKILL_LISTING.md", "CLAUDE.zh.md", "MODELS.zh.md", "ARCHITECTURE.zh.md",
    "Makefile", ".gitignore",
    "tools", "templates", "examples", "docs", "config",
    ".claude", ".agents", "scripts", "tests",
]

def copy_item(rel: str) -> None:
    src = ROOT / rel
    if not src.exists():
        return
    dest = staging / rel
    if src.is_dir():
        shutil.copytree(
            src, dest,
            ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", ".pytest_cache", "node_modules",
                ".git", ".workbuddy", "_gif_frames",
            ),
            dirs_exist_ok=True,
        )
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

for item in INCLUDE:
    copy_item(item)

for p in list(staging.rglob("*")):
    if p.is_dir() and p.name in {"__pycache__", ".pytest_cache", "node_modules", ".git"}:
        shutil.rmtree(p, ignore_errors=True)

out_dir = ROOT / "dist"
out_dir.mkdir(exist_ok=True)
zip_out = out_dir / f"{SKILL_NAME}.zip"
desktop = Path.home() / "Desktop" / "cn-job-assistant-redskill.zip"
for z in (zip_out, desktop):
    if z.exists():
        z.unlink()

with zipfile.ZipFile(zip_out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(staging.rglob("*")):
        if path.is_dir():
            continue
        arc = path.relative_to(stage_parent).as_posix()
        info = zipfile.ZipInfo(filename=arc)
        info.flag_bits |= 0x800  # UTF-8 filenames
        zf.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)

shutil.copy2(zip_out, desktop)

with zipfile.ZipFile(zip_out) as z:
    names = z.namelist()
    roots = {n.split("/")[0] for n in names}
    assert roots == {SKILL_NAME}, roots
    skill = z.read(f"{SKILL_NAME}/SKILL.md").decode("utf-8")
    fm2 = re.match(r"^---\n(.*?)\n---", skill, re.S).group(1)
    name2 = re.search(r"(?m)^name:\s*(.+)$", fm2).group(1).strip()
    desc2 = re.search(r"(?m)^description:\s*(.+)$", fm2).group(1).strip()
    assert name2 == NAME_EXPECTED and desc2 == DESC_EXPECTED

print("PREUPLOAD_OK")
print(f"zip: {zip_out}")
print(f"desktop: {desktop}")
print(f"size_kb: {round(zip_out.stat().st_size/1024,1)}")
print(f"files: {len(names)}")
print()
print("上传表单请填：")
print(f"  名称: {NAME_EXPECTED}")
print(f"  简介: {DESC_EXPECTED}")
PY
