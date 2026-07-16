#!/usr/bin/env python3
"""Split a pasted multi-JD text file into per-job files + import stub JSON (v0.13).

No network. Separators (any of):
  - a line that is only --- or ===
  - a markdown heading line starting with # 
  - a line matching 「公司：」/「【」 style blocks when previous block ended

Usage:
  python tools/split_jds.py -i pasted.txt -o documents/zh/inbox
  python tools/tracker.py import-jobs documents/zh/inbox/jobs_stub.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SEP_LINE = re.compile(r"^\s*(?:-{3,}|={3,}|\*{3,})\s*$")
HEADING = re.compile(r"^\s*#{1,3}\s+\S")
COMPANY_LINE = re.compile(
    r"^\s*(?:公司|企业|用人单位)\s*[:：]\s*(.+)$",
    re.M,
)
ROLE_LINE = re.compile(
    r"^\s*(?:岗位|职位|招聘)\s*[:：]\s*(.+)$",
    re.M,
)
SALARY_LINE = re.compile(
    r"(?:薪资|月薪|年薪)\s*[:：]?\s*([0-9].{0,20})",
    re.I,
)
CITY_LINE = re.compile(
    r"(?:城市|地点|工作地点)\s*[:：]\s*([^\n，,]+)",
    re.I,
)


def split_blocks(text: str) -> list[str]:
    """Split pasted text into JD blocks."""
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return []
    lines = text.split("\n")
    blocks: list[list[str]] = [[]]
    for line in lines:
        if SEP_LINE.match(line) and blocks[-1]:
            blocks.append([])
            continue
        if HEADING.match(line) and blocks[-1] and any(x.strip() for x in blocks[-1]):
            blocks.append([line])
            continue
        blocks[-1].append(line)
    out: list[str] = []
    for b in blocks:
        body = "\n".join(b).strip()
        if len(body) >= 40:  # skip tiny crumbs
            out.append(body)
    # single block if nothing split
    if not out and text.strip():
        out = [text.strip()]
    return out


def guess_meta(block: str, index: int) -> dict[str, str]:
    company = ""
    role = ""
    m = COMPANY_LINE.search(block)
    if m:
        company = m.group(1).strip()[:40]
    m = ROLE_LINE.search(block)
    if m:
        role = m.group(1).strip()[:40]
    # heading fallback: # 星云科技 · 后端
    hm = re.search(r"^\s*#\s+(.+)$", block, re.M)
    if hm and (not company or not role):
        title = hm.group(1).strip()
        if "·" in title or "|" in title or "-" in title:
            parts = re.split(r"[·|\-—]+", title, maxsplit=1)
            if len(parts) == 2:
                company = company or parts[0].strip()[:40]
                role = role or parts[1].strip()[:40]
            else:
                company = company or title[:40]
        else:
            company = company or title[:40]
    if not company:
        company = f"JD_{index:03d}"
    if not role:
        role = "待定岗位"
    city = ""
    cm = CITY_LINE.search(block)
    if cm:
        city = cm.group(1).strip()[:20]
    salary = ""
    sm = SALARY_LINE.search(block)
    if sm:
        salary = sm.group(1).strip()[:24]
    return {
        "company": company,
        "role": role,
        "city": city,
        "salary": salary,
    }


def safe_slug(s: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", s, flags=re.U)
    s = re.sub(r"_+", "_", s).strip("_")
    return (s or "x")[:48]


def run_split(
    text: str,
    out_dir: Path,
    *,
    channel: str = "粘贴",
    default_resume: str = "",
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    blocks = split_blocks(text)
    jobs: list[dict] = []
    written: list[str] = []
    for i, block in enumerate(blocks, 1):
        meta = guess_meta(block, i)
        slug_c = safe_slug(meta["company"])
        slug_r = safe_slug(meta["role"])
        fname = f"jd_{slug_c}_{slug_r}.md"
        # collision
        path = out_dir / fname
        n = 2
        while path.exists():
            path = out_dir / f"jd_{slug_c}_{slug_r}_{n}.md"
            n += 1
        header = (
            f"# {meta['company']} · {meta['role']}\n\n"
            f"<!-- split_jds.py auto · channel={channel} -->\n\n"
        )
        path.write_text(header + block + "\n", encoding="utf-8")
        written.append(str(path))
        job: dict = {
            "company": meta["company"],
            "role": meta["role"],
            "channel": channel,
            "source": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "city": meta["city"],
            "salary": meta["salary"],
            "status": "to_apply",
        }
        if default_resume:
            job["cv"] = default_resume
            job["cv_file"] = default_resume
        jobs.append(job)

    stub_path = out_dir / "jobs_stub.json"
    stub_path.write_text(
        json.dumps({"jobs": jobs}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "count": len(jobs),
        "files": written,
        "stub": str(stub_path),
        "jobs": jobs,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Split pasted multi-JD text into files + import stub.")
    p.add_argument("-i", "--input", required=True, help="pasted text file path")
    p.add_argument(
        "-o",
        "--out-dir",
        default=str(ROOT / "documents" / "zh" / "inbox"),
        help="output directory (default documents/zh/inbox)",
    )
    p.add_argument("--channel", default="粘贴", help="default channel for stub")
    p.add_argument(
        "--resume",
        default="",
        help="optional master resume path to attach as cv_file in stub",
    )
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    src = Path(args.input)
    if not src.is_file():
        alt = ROOT / args.input
        if alt.is_file():
            src = alt
        else:
            print(f"error: input not found: {args.input}", file=sys.stderr)
            return 2
    text = src.read_text(encoding="utf-8", errors="replace")
    result = run_split(
        text,
        Path(args.out_dir),
        channel=args.channel,
        default_resume=args.resume,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"split {result['count']} JD(s) → {args.out_dir}")
        for f in result["files"][:8]:
            print(f"  · {f}")
        if result["count"] > 8:
            print(f"  … +{result['count'] - 8} more")
        print(f"import stub: {result['stub']}")
        print("next:")
        print(f"  python tools/tracker.py import-jobs {result['stub']}")
        print("  python tools/flow.py shortlist --limit 3")
        print("  # or /apply-zh after rank")
    return 0 if result["count"] else 1


if __name__ == "__main__":
    # Path.is_relative_to is 3.9+
    if not hasattr(Path, "is_relative_to"):

        def _is_relative_to(self: Path, other: Path) -> bool:  # type: ignore[misc]
            try:
                self.relative_to(other)
                return True
            except ValueError:
                return False

        Path.is_relative_to = _is_relative_to  # type: ignore[attr-defined]

    sys.exit(main())
