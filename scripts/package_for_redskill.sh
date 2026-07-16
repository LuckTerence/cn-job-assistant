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
SKILL_NAME = "ai-job-assistant"
NAME_EXPECTED = "AI求职助理"
DESC_EXPECTED = (
    "本地求职助手：根据岗位描述定制中文简历与求职话术，导出可投递 PDF 简历，分析简历与岗位匹配度，"
    "记录求职投递进度。支持简历模板、求职信生成、求职看板。触发词：求职、找工作、改简历、中文简历、"
    "PDF简历、求职信、岗位匹配、投递进度、简历优化、找工作助手。"
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

INCLUDE_FILES = [
    "SKILL.md",
    "skill.json",
    "LICENSE",
    "NOTICE",
    "Makefile",
]

INCLUDE_DIRS = [
    "assets",
    "tools",
    "templates",
    "examples",
]

SAFE_TOOLS = {
    "tracker.py",
    "match_resume.py",
    "export_resume_pdf.py",
    "apply_assist.py",
    "flow.py",
    "split_jds.py",
    "install_domestic_search.py",
    "normalize_job_export.py",
    "check_profile_resume.py",
}

def copy_file(rel: str) -> None:
    src = ROOT / rel
    if not src.exists() or not src.is_file():
        return
    dest = staging / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)

def copy_tree_safe(rel: str) -> None:
    src = ROOT / rel
    if not src.exists() or not src.is_dir():
        return
    dest = staging / rel
    if rel == "tools":
        dest.mkdir(parents=True, exist_ok=True)
        for f in SAFE_TOOLS:
            fpath = src / f
            if fpath.exists():
                shutil.copy2(fpath, dest / f)
        return
    if rel == "examples":
        dest.mkdir(parents=True, exist_ok=True)
        for item in ["tracks"]:
            s = src / item
            d = dest / item
            if s.exists():
                shutil.copytree(s, d, dirs_exist_ok=True)
        for f in ["resume_星云科技.md", "jd_星云科技_后端.md", "README.md"]:
            fp = src / f
            if fp.exists():
                shutil.copy2(fp, dest / f)
        return
    shutil.copytree(
        src, dest,
        ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", ".pytest_cache", "node_modules",
            ".git", ".workbuddy", "_gif_frames",
        ),
        dirs_exist_ok=True,
    )

for f in INCLUDE_FILES:
    copy_file(f)

for d in INCLUDE_DIRS:
    copy_tree_safe(d)

for p in list(staging.rglob("*")):
    if p.is_dir() and p.name in {"__pycache__", ".pytest_cache", "node_modules", ".git", "output"}:
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
        info.flag_bits |= 0x800
        zf.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)

shutil.copy2(zip_out, desktop)

with zipfile.ZipFile(zip_out) as z:
    names = z.namelist()
    roots = {n.split("/")[0] for n in names}
    assert roots == {SKILL_NAME}, roots
    assert f"{SKILL_NAME}/SKILL.md" in names, "SKILL.md missing"
    assert f"{SKILL_NAME}/skill.json" in names, "skill.json missing"
    assert f"{SKILL_NAME}/assets/icon.svg" in names, "assets/icon.svg missing"
    skill = z.read(f"{SKILL_NAME}/SKILL.md").decode("utf-8")
    fm2 = re.match(r"^---\n(.*?)\n---", skill, re.S).group(1)
    name2 = re.search(r"(?m)^name:\s*(.+)$", fm2).group(1).strip()
    desc2 = re.search(r"(?m)^description:\s*(.+)$", fm2).group(1).strip().strip("\"'")
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
print()
print("ZIP 内容清单：")
for n in sorted(names):
    print(f"  {n}")
PY
