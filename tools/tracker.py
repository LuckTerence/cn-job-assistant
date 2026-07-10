#!/usr/bin/env python3
"""Local application tracker — CSV as source of truth, optional SQLite + HTML.

Stdlib only. Aligns with /outcome and the job_search_tracker.csv schema:

  date,company,sector,role,role_type,channel,status,contact_person,
  fit_rating,notes,cv_file,cover_letter_file,source

Usage (from repo root):
  python tools/tracker.py init
  python tools/tracker.py add --company 字节 --role 后端 --channel Boss直聘 --status applied
  python tools/tracker.py list [--status applied]
  python tools/tracker.py update --company 字节 --role 后端 --status interview
  python tools/tracker.py show --company 字节
  python tools/tracker.py export --format html|sqlite|csv
  python tools/tracker.py dashboard   # writes job_search_tracker.html
"""

from __future__ import annotations

import argparse
import csv
import html
import shutil
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = ROOT / "job_search_tracker.csv"
DEFAULT_DB = ROOT / "job_search_tracker.db"
DEFAULT_HTML = ROOT / "job_search_tracker.html"

HEADER = [
    "date",
    "company",
    "sector",
    "role",
    "role_type",
    "channel",
    "status",
    "contact_person",
    "fit_rating",
    "notes",
    "cv_file",
    "cover_letter_file",
    "source",
]

# Status vocabulary shared with /outcome and documents/README.md
OPEN_STATUSES = {
    "applied",
    "to_apply",
    "screening",
    "interview",
    "interview_1",
    "interview_2",
    "interview_final",
    "offer",
    "in_progress",
}
CLOSED_STATUSES = {
    "hired",
    "rejected",
    "no_response",
    "withdrawn",
    "offer_declined",
    "interview_only",
    "expired",
}


def _csv_path(path: Path | None) -> Path:
    return path or DEFAULT_CSV


def ensure_csv(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        writer.writeheader()


def read_rows(path: Path) -> list[dict[str, str]]:
    ensure_csv(path)
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return []
        # Tolerate extra columns; fill missing header keys.
        rows: list[dict[str, str]] = []
        for raw in reader:
            row = {k: (raw.get(k) or "").strip() for k in HEADER}
            rows.append(row)
        return rows


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in HEADER})


def match_rows(
    rows: list[dict[str, str]],
    company: str | None,
    role: str | None,
) -> list[tuple[int, dict[str, str]]]:
    hits: list[tuple[int, dict[str, str]]] = []
    company_l = (company or "").lower()
    role_l = (role or "").lower()
    for i, row in enumerate(rows):
        if company_l and company_l not in row["company"].lower():
            continue
        if role_l and role_l not in row["role"].lower():
            continue
        hits.append((i, row))
    return hits


def cmd_init(args: argparse.Namespace) -> int:
    path = _csv_path(args.csv)
    if path.exists() and not args.force:
        print(f"already exists: {path}")
        return 0
    if path.exists() and args.force:
        path.unlink()
    ensure_csv(path)
    print(f"initialized: {path}")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    path = _csv_path(args.csv)
    rows = read_rows(path)
    company = args.company.strip()
    role = (args.role or "").strip()
    if not company:
        print("error: --company is required", file=sys.stderr)
        return 2
    # Idempotent-ish: same company+role+channel → update status/notes instead of duplicate
    for row in rows:
        if (
            row["company"].lower() == company.lower()
            and row["role"].lower() == role.lower()
            and (not args.channel or row["channel"].lower() == args.channel.lower())
        ):
            if args.force:
                break
            print(
                f"duplicate found (company={row['company']!r} role={row['role']!r}). "
                "Use update, or --force to add anyway.",
                file=sys.stderr,
            )
            return 1

    row = {k: "" for k in HEADER}
    row["date"] = args.date or date.today().isoformat()
    row["company"] = company
    row["sector"] = args.sector or ""
    row["role"] = role
    row["role_type"] = args.role_type or ""
    row["channel"] = args.channel or ""
    row["status"] = args.status or "applied"
    row["contact_person"] = args.contact or ""
    row["fit_rating"] = args.fit or ""
    row["notes"] = args.notes or ""
    row["cv_file"] = args.cv or ""
    row["cover_letter_file"] = args.cover or ""
    row["source"] = args.source or ""
    rows.append(row)
    write_rows(path, rows)
    print(f"added: {company} / {role or '(no role)'} [{row['status']}]")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    path = _csv_path(args.csv)
    rows = read_rows(path)
    if args.status:
        status_l = args.status.lower()
        rows = [r for r in rows if r["status"].lower() == status_l]
    if args.open_only:
        rows = [r for r in rows if r["status"].lower() in OPEN_STATUSES or r["status"].lower() not in CLOSED_STATUSES]
        # Prefer explicit open set; treat unknown non-closed as open
        rows = [
            r
            for r in rows
            if r["status"].lower() not in CLOSED_STATUSES
        ]
    if not rows:
        print("(no rows)")
        return 0
    # Compact table
    print(f"{'#':>3}  {'date':10}  {'status':14}  {'company':16}  {'role':20}  channel")
    print("-" * 90)
    for i, r in enumerate(rows, 1):
        print(
            f"{i:>3}  {r['date'][:10]:10}  {r['status'][:14]:14}  "
            f"{r['company'][:16]:16}  {r['role'][:20]:20}  {r['channel']}"
        )
    print(f"\n{len(rows)} row(s)  ← {path}")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    path = _csv_path(args.csv)
    rows = read_rows(path)
    hits = match_rows(rows, args.company, args.role)
    if not hits:
        print("error: no matching row", file=sys.stderr)
        return 1
    if len(hits) > 1 and not args.all:
        print("error: multiple matches; narrow with --role or pass --all", file=sys.stderr)
        for i, r in hits:
            print(f"  [{i}] {r['company']} / {r['role']} / {r['status']}")
        return 1

    fields = {
        "status": args.status,
        "notes": args.notes,
        "channel": args.channel,
        "contact_person": args.contact,
        "fit_rating": args.fit,
        "cv_file": args.cv,
        "cover_letter_file": args.cover,
        "source": args.source,
        "sector": args.sector,
        "role_type": args.role_type,
    }
    updates = {k: v for k, v in fields.items() if v is not None}
    if not updates:
        print("error: nothing to update (pass --status / --notes / ...)", file=sys.stderr)
        return 2

    for i, _ in hits:
        for k, v in updates.items():
            rows[i][k] = v
        print(f"updated: {rows[i]['company']} / {rows[i]['role']} → {rows[i]['status']}")
    write_rows(path, rows)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    path = _csv_path(args.csv)
    rows = read_rows(path)
    hits = match_rows(rows, args.company, args.role)
    if not hits:
        print("error: no matching row", file=sys.stderr)
        return 1
    for _, r in hits:
        for k in HEADER:
            print(f"{k:20} {r.get(k, '')}")
        print("---")
    return 0


def export_sqlite(csv_path: Path, db_path: Path) -> None:
    rows = read_rows(csv_path)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    try:
        cols = ", ".join(f'"{c}" TEXT' for c in HEADER)
        conn.execute(f"CREATE TABLE applications ({cols})")
        placeholders = ", ".join("?" for _ in HEADER)
        conn.executemany(
            f"INSERT INTO applications VALUES ({placeholders})",
            [[r.get(c, "") for c in HEADER] for r in rows],
        )
        conn.commit()
    finally:
        conn.close()


def export_html(csv_path: Path, html_path: Path) -> None:
    rows = read_rows(csv_path)
    open_rows = [r for r in rows if r["status"].lower() not in CLOSED_STATUSES]
    closed_rows = [r for r in rows if r["status"].lower() in CLOSED_STATUSES]

    def render_table(title: str, subset: list[dict[str, str]]) -> str:
        if not subset:
            return f"<h2>{html.escape(title)}</h2><p><em>empty</em></p>"
        head = "".join(f"<th>{html.escape(h)}</th>" for h in HEADER)
        body_parts = []
        for r in subset:
            cells = "".join(f"<td>{html.escape(r.get(c, ''))}</td>" for c in HEADER)
            body_parts.append(f"<tr>{cells}</tr>")
        return (
            f"<h2>{html.escape(title)} ({len(subset)})</h2>"
            f"<table><thead><tr>{head}</tr></thead>"
            f"<tbody>{''.join(body_parts)}</tbody></table>"
        )

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>求职投递看板 · job_search_tracker</title>
<style>
  :root {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif; color: #1a1a1a; }}
  body {{ max-width: 1200px; margin: 2rem auto; padding: 0 1rem; background: #f7f7f8; }}
  h1 {{ font-size: 1.4rem; }}
  .meta {{ color: #666; font-size: 0.9rem; margin-bottom: 1.5rem; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff; font-size: 0.85rem;
           box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 2rem; }}
  th, td {{ border: 1px solid #e5e5e5; padding: 0.4rem 0.55rem; text-align: left; vertical-align: top; }}
  th {{ background: #f0f0f2; position: sticky; top: 0; }}
  tr:nth-child(even) {{ background: #fafafa; }}
  .stats {{ display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem; }}
  .stat {{ background: #fff; padding: 0.75rem 1rem; border-radius: 8px;
           box-shadow: 0 1px 3px rgba(0,0,0,.08); min-width: 6rem; }}
  .stat b {{ display: block; font-size: 1.4rem; }}
</style>
</head>
<body>
  <h1>求职投递看板</h1>
  <p class="meta">Source of truth: <code>{html.escape(str(csv_path.name))}</code>
     · generated by <code>tools/tracker.py dashboard</code>
     · do not commit (personal data)</p>
  <div class="stats">
    <div class="stat"><b>{len(rows)}</b>total</div>
    <div class="stat"><b>{len(open_rows)}</b>open</div>
    <div class="stat"><b>{len(closed_rows)}</b>closed</div>
  </div>
  {render_table("进行中 / Open", open_rows)}
  {render_table("已结束 / Closed", closed_rows)}
</body>
</html>
"""
    html_path.write_text(doc, encoding="utf-8")


def cmd_export(args: argparse.Namespace) -> int:
    path = _csv_path(args.csv)
    ensure_csv(path)
    fmt = args.format
    if fmt == "csv":
        dest = Path(args.out) if args.out else path.with_name(path.stem + "_export.csv")
        shutil.copy2(path, dest)
        print(f"exported csv → {dest}")
        return 0
    if fmt == "sqlite":
        dest = Path(args.out) if args.out else DEFAULT_DB
        export_sqlite(path, dest)
        print(f"exported sqlite → {dest}")
        return 0
    if fmt == "html":
        dest = Path(args.out) if args.out else DEFAULT_HTML
        export_html(path, dest)
        print(f"exported html → {dest}")
        return 0
    print(f"error: unknown format {fmt!r}", file=sys.stderr)
    return 2


def cmd_dashboard(args: argparse.Namespace) -> int:
    path = _csv_path(args.csv)
    dest = Path(args.out) if args.out else DEFAULT_HTML
    ensure_csv(path)
    export_html(path, dest)
    print(f"dashboard → {dest}")
    return 0


INTERVIEW_STATUSES = {
    "interview",
    "interview_1",
    "interview_2",
    "interview_final",
    "screening",
    "offer",
}
FOLLOW_STATUSES = {"applied", "to_apply", "in_progress"}


def cmd_today(args: argparse.Namespace) -> int:
    """Daily job-search cockpit: open items grouped by next action."""
    path = _csv_path(args.csv)
    rows = read_rows(path)
    if not rows:
        print("今天还没有投递记录。先：")
        print("  python tools/tracker.py init")
        print("  python tools/tracker.py add --company … --role … --status applied")
        return 0

    open_rows = [r for r in rows if r["status"].lower() not in CLOSED_STATUSES]
    interviews = [r for r in open_rows if r["status"].lower() in INTERVIEW_STATUSES]
    follow = [r for r in open_rows if r["status"].lower() in FOLLOW_STATUSES]
    other_open = [
        r
        for r in open_rows
        if r not in interviews and r not in follow
    ]
    closed = [r for r in rows if r["status"].lower() in CLOSED_STATUSES]

    print("=== 今日求职工作台 ===")
    print(f"总计 {len(rows)} 条 · 进行中 {len(open_rows)} · 已结束 {len(closed)}")
    print()

    def dump(title: str, subset: list[dict[str, str]], hint: str) -> None:
        print(f"## {title} ({len(subset)})")
        if not subset:
            print("  （空）")
        else:
            for r in subset:
                note = f" — {r['notes'][:40]}" if r.get("notes") else ""
                print(
                    f"  · [{r['status']}] {r['company']} / {r['role']} "
                    f"({r['channel'] or '—'}){note}"
                )
        print(f"  → {hint}")
        print()

    dump("面试 / Offer 跟进", interviews, "准备 /interview 或更新：tracker update --status …")
    dump("已投待回复", follow, "可跟进或标记 no_response；新投递用 tracker add")
    if other_open:
        dump("其他进行中", other_open, "核对状态是否写对")
    dump("已结束（最近）", closed[-5:], "复盘用 /outcome；勿删历史行")

    print("快捷命令：")
    print("  python tools/tracker.py list --open-only")
    print("  python tools/tracker.py dashboard")
    print("  /apply-zh <JD>   # 生成材料后再 add 一条")
    return 0


def cmd_suggest_add(args: argparse.Namespace) -> int:
    """Print a copy-paste tracker add command (for /apply-zh handoff)."""
    company = args.company.strip()
    role = (args.role or "").strip()
    channel = (args.channel or "Boss直聘").strip()
    cv = args.cv or f"documents/zh/resume_{company}.md"
    cover = args.cover or ""
    source = args.source or ""
    parts = [
        "python tools/tracker.py add",
        f"--company {company!s}",
        f"--role {role!s}" if role else "",
        f"--channel {channel!s}",
        "--status applied",
        f"--cv {cv}",
    ]
    if cover:
        parts.append(f"--cover {cover}")
    if source:
        parts.append(f"--source {source}")
    cmd = " \\\n  ".join(p for p in parts if p)
    print("# 投递后粘贴执行（或让 Agent 代跑）：")
    print(cmd)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tracker",
        description="Local job-application tracker (CSV source of truth).",
    )
    p.add_argument(
        "--csv",
        type=Path,
        default=None,
        help=f"path to tracker CSV (default: {DEFAULT_CSV.name} at repo root)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init", help="create empty tracker CSV with standard header")
    init_p.add_argument("--force", action="store_true", help="overwrite existing file")
    init_p.set_defaults(func=cmd_init)

    add_p = sub.add_parser("add", help="add an application row")
    add_p.add_argument("--company", required=True)
    add_p.add_argument("--role", default="")
    add_p.add_argument("--sector", default="")
    add_p.add_argument("--role-type", dest="role_type", default="")
    add_p.add_argument("--channel", default="")
    add_p.add_argument("--status", default="applied")
    add_p.add_argument("--contact", default="")
    add_p.add_argument("--fit", default="")
    add_p.add_argument("--notes", default="")
    add_p.add_argument("--cv", default="")
    add_p.add_argument("--cover", default="")
    add_p.add_argument("--source", default="")
    add_p.add_argument("--date", default="")
    add_p.add_argument("--force", action="store_true", help="allow duplicate company+role")
    add_p.set_defaults(func=cmd_add)

    list_p = sub.add_parser("list", help="list applications")
    list_p.add_argument("--status", default="")
    list_p.add_argument("--open-only", action="store_true")
    list_p.set_defaults(func=cmd_list)

    up_p = sub.add_parser("update", help="update matching row(s)")
    up_p.add_argument("--company", required=True)
    up_p.add_argument("--role", default="")
    up_p.add_argument("--all", action="store_true")
    up_p.add_argument("--status", default=None)
    up_p.add_argument("--notes", default=None)
    up_p.add_argument("--channel", default=None)
    up_p.add_argument("--contact", default=None)
    up_p.add_argument("--fit", default=None)
    up_p.add_argument("--cv", default=None)
    up_p.add_argument("--cover", default=None)
    up_p.add_argument("--source", default=None)
    up_p.add_argument("--sector", default=None)
    up_p.add_argument("--role-type", dest="role_type", default=None)
    up_p.set_defaults(func=cmd_update)

    show_p = sub.add_parser("show", help="show full row(s)")
    show_p.add_argument("--company", required=True)
    show_p.add_argument("--role", default="")
    show_p.set_defaults(func=cmd_show)

    exp_p = sub.add_parser("export", help="export to csv / sqlite / html")
    exp_p.add_argument("--format", choices=["csv", "sqlite", "html"], required=True)
    exp_p.add_argument("--out", default="")
    exp_p.set_defaults(func=cmd_export)

    dash_p = sub.add_parser("dashboard", help="write single-file HTML dashboard")
    dash_p.add_argument("--out", default="")
    dash_p.set_defaults(func=cmd_dashboard)

    today_p = sub.add_parser("today", help="daily cockpit: interviews / follow-ups / closed")
    today_p.set_defaults(func=cmd_today)

    sug_p = sub.add_parser(
        "suggest-add",
        help="print copy-paste add command after /apply-zh",
    )
    sug_p.add_argument("--company", required=True)
    sug_p.add_argument("--role", default="")
    sug_p.add_argument("--channel", default="Boss直聘")
    sug_p.add_argument("--cv", default="")
    sug_p.add_argument("--cover", default="")
    sug_p.add_argument("--source", default="")
    sug_p.set_defaults(func=cmd_suggest_add)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
