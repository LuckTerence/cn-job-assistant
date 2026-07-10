#!/usr/bin/env python3
"""Local application tracker — CSV as source of truth, optional SQLite + HTML.

Stdlib only. Aligns with /outcome and the job_search_tracker.csv schema:

  date,company,sector,role,role_type,channel,status,contact_person,
  fit_rating,notes,cv_file,cover_letter_file,source,
  salary,city,education,experience

Usage (from repo root):
  python tools/tracker.py init
  python tools/tracker.py add --company 字节 --role 后端 --channel Boss直聘 --status applied
  python tools/tracker.py list [--status applied]
  python tools/tracker.py update --company 字节 --role 后端 --status interview
  python tools/tracker.py show --company 字节
  python tools/tracker.py export --format html|sqlite|csv
  python tools/tracker.py dashboard   # writes job_search_tracker.html
  python tools/tracker.py today       # daily cockpit
  python tools/tracker.py suggest-add --company X --role Y ...
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
    "salary",
    "city",
    "education",
    "experience",
]

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
    "skipped",
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
    row["salary"] = args.salary or ""
    row["city"] = args.city or ""
    row["education"] = args.education or ""
    row["experience"] = args.experience or ""
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
        "salary": args.salary,
        "city": args.city,
        "education": args.education,
        "experience": args.experience,
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


INTERVIEW_STATUSES = {
    "interview",
    "interview_1",
    "interview_2",
    "interview_final",
    "screening",
    "offer",
}
FOLLOW_STATUSES = {"applied", "to_apply", "in_progress"}

REVIEW_STATUSES = {"rejected", "no_response", "withdrawn", "offer_declined", "interview_only", "expired"}
FOLLOW_UP_DAYS = 7
REVIEW_DAYS = 30


def _parse_date(s: str) -> date | None:
    s = (s or "").strip()[:10]
    if not s:
        return None
    try:
        parts = s.split("-")
        if len(parts) == 3:
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError):
        pass
    return None


def build_action_items(rows: list[dict[str, str]], today: date | None = None) -> dict:
    """Build action-item groups for dashboard/today.

    Returns dict with keys: interviews, follow_ups, reviews (each list of rows).
    Rules:
      - interviews: status ∈ INTERVIEW_STATUSES (any open interview-ish)
      - follow_ups: status ∈ FOLLOW_STATUSES AND date ≥ FOLLOW_UP_DAYS ago (still open, stale)
      - reviews: status ∈ REVIEW_STATUSES AND date within REVIEW_DAYS (recent closed)
    """
    today = today or date.today()
    interviews: list[dict[str, str]] = []
    follow_ups: list[dict[str, str]] = []
    reviews: list[dict[str, str]] = []

    for r in rows:
        st = r.get("status", "").lower()
        d = _parse_date(r.get("date", ""))
        if st in INTERVIEW_STATUSES and st not in CLOSED_STATUSES:
            interviews.append(r)
        if st in FOLLOW_STATUSES and st not in CLOSED_STATUSES:
            if d is not None:
                age = (today - d).days
                if age >= FOLLOW_UP_DAYS:
                    follow_ups.append(r)
        if st in REVIEW_STATUSES:
            if d is not None:
                age = (today - d).days
                if 0 <= age <= REVIEW_DAYS:
                    reviews.append(r)

    return {"interviews": interviews, "follow_ups": follow_ups, "reviews": reviews}


def export_html(csv_path: Path, html_path: Path) -> None:
    rows = read_rows(csv_path)
    today = date.today()
    actions = build_action_items(rows, today)
    open_rows = [r for r in rows if r["status"].lower() not in CLOSED_STATUSES]
    closed_rows = [r for r in rows if r["status"].lower() in CLOSED_STATUSES]

    visible_cols = [c for c in HEADER if any(r.get(c, "").strip() for r in rows)] or HEADER

    def esc(s: str) -> str:
        return html.escape(str(s or ""))

    def render_action_cards() -> str:
        cards: list[str] = []
        iv = actions["interviews"]
        fu = actions["follow_ups"]
        rv = actions["reviews"]

        if iv:
            items = "".join(
                f'<li><span class="badge badge-iv">{esc(r["status"])}</span> '
                f'<b>{esc(r["company"])}</b> / {esc(r["role"])}'
                f'{" · " + esc(r["channel"]) if r.get("channel") else ""}'
                f'{" · " + esc(r["city"]) if r.get("city") else ""}'
                f'</li>'
                for r in iv
            )
            cards.append(
                '<div class="card card-iv">'
                '<div class="card-title">📅 进行中的面试</div>'
                f'<ul>{items}</ul>'
                '<div class="card-hint">准备面试跑 /interview；状态变了用 tracker update</div>'
                '</div>'
            )
        if fu:
            items = "".join(
                f'<li><b>{esc(r["company"])}</b> / {esc(r["role"])}'
                f'{" · " + esc(r["channel"]) if r.get("channel") else ""}'
                f' · 投于 {esc(r["date"][:10])}'
                f'</li>'
                for r in fu
            )
            cards.append(
                '<div class="card card-fu">'
                f'<div class="card-title">⏰ 建议跟进（≥{FOLLOW_UP_DAYS}天无进展）</div>'
                f'<ul>{items}</ul>'
                '<div class="card-hint">如果已被拒/无回复，用 /outcome 记一笔</div>'
                '</div>'
            )
        if rv:
            items = "".join(
                f'<li><span class="badge badge-rv">{esc(r["status"])}</span> '
                f'<b>{esc(r["company"])}</b> / {esc(r["role"])}'
                f' · {esc(r["date"][:10])}'
                f'</li>'
                for r in rv
            )
            cards.append(
                '<div class="card card-rv">'
                f'<div class="card-title">📝 建议复盘（近{REVIEW_DAYS}天结束）</div>'
                f'<ul>{items}</ul>'
                '<div class="card-hint">跑 /outcome 总结经验，改完简历用 diff 对比改进</div>'
                '</div>'
            )

        if not cards:
            return (
                '<div class="card card-empty">'
                '<div class="card-title">✨ 暂无待办</div>'
                '<div class="card-hint">新投岗位会自动出现在这里；投完记得 tracker add 记一笔</div>'
                '</div>'
            )
        return '<div class="actions-grid">' + "".join(cards) + '</div>'

    def render_table(title: str, subset: list[dict[str, str]]) -> str:
        if not subset:
            return f"<h2>{esc(title)}</h2><p><em>empty</em></p>"
        head = "".join(f"<th>{esc(h)}</th>" for h in visible_cols)
        body_parts = []
        for r in subset:
            cells = "".join(f"<td>{esc(r.get(c, ''))}</td>" for c in visible_cols)
            st = r.get("status", "").lower()
            cls = ""
            if st in INTERVIEW_STATUSES:
                cls = ' class="row-iv"'
            elif st in REVIEW_STATUSES or st in CLOSED_STATUSES:
                cls = ' class="row-closed"'
            body_parts.append(f"<tr{cls}>{cells}</tr>")
        return (
            f"<h2>{esc(title)} ({len(subset)})</h2>"
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
  :root {{
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    color: #1a1a1a;
    --bg: #f7f7f8;
    --card-bg: #fff;
    --border: #e5e5e5;
    --accent-iv: #2563eb;
    --accent-fu: #d97706;
    --accent-rv: #059669;
    --accent-empty: #6b7280;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      color: #e5e5e7;
      --bg: #1a1a1d;
      --card-bg: #242428;
      --border: #33333a;
    }}
  }}
  body {{ max-width: 1280px; margin: 2rem auto; padding: 0 1rem; background: var(--bg); }}
  h1 {{ font-size: 1.4rem; }}
  h2 {{ font-size: 1.1rem; margin-top: 2rem; }}
  .meta {{ color: #888; font-size: 0.85rem; margin-bottom: 1rem; }}
  .stats {{ display: flex; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 1.5rem; }}
  .stat {{ background: var(--card-bg); padding: 0.65rem 1rem; border-radius: 8px;
           box-shadow: 0 1px 3px rgba(0,0,0,.08); min-width: 5.5rem; text-align: center; }}
  .stat b {{ display: block; font-size: 1.3rem; }}
  .actions-grid {{ display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); margin-bottom: 2rem; }}
  .card {{ background: var(--card-bg); border-radius: 10px; padding: 1rem 1.1rem;
           box-shadow: 0 1px 3px rgba(0,0,0,.08); border-left: 4px solid #ccc; }}
  .card-iv {{ border-left-color: var(--accent-iv); }}
  .card-fu {{ border-left-color: var(--accent-fu); }}
  .card-rv {{ border-left-color: var(--accent-rv); }}
  .card-empty {{ border-left-color: var(--accent-empty); text-align: center; padding: 1.5rem; }}
  .card-title {{ font-weight: 600; font-size: 0.95rem; margin-bottom: 0.6rem; }}
  .card ul {{ margin: 0; padding-left: 1.1rem; font-size: 0.88rem; line-height: 1.7; }}
  .card-hint {{ margin-top: 0.6rem; font-size: 0.78rem; color: #888; }}
  .badge {{ display: inline-block; font-size: 0.72rem; padding: 1px 6px; border-radius: 4px;
            color: #fff; vertical-align: middle; line-height: 1.4; }}
  .badge-iv {{ background: var(--accent-iv); }}
  .badge-rv {{ background: var(--accent-rv); }}
  table {{ border-collapse: collapse; width: 100%; background: var(--card-bg); font-size: 0.82rem;
           box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 2rem; border-radius: 6px; overflow: hidden; }}
  th, td {{ border-bottom: 1px solid var(--border); padding: 0.45rem 0.6rem; text-align: left; vertical-align: top; }}
  th {{ background: rgba(128,128,128,.1); position: sticky; top: 0; font-weight: 600; white-space: nowrap; }}
  tr:hover {{ background: rgba(128,128,128,.05); }}
  .row-iv td {{ border-left: 3px solid var(--accent-iv); }}
  .row-closed td {{ opacity: 0.65; }}
  code {{ background: rgba(128,128,128,.12); padding: 1px 5px; border-radius: 3px; font-size: 0.85em; }}
</style>
</head>
<body>
  <h1>求职投递看板</h1>
  <p class="meta">Source of truth: <code>{esc(str(csv_path.name))}</code>
     · generated {esc(today.isoformat())} by <code>tools/tracker.py dashboard</code>
     · do not commit (personal data)</p>
  <div class="stats">
    <div class="stat"><b>{len(rows)}</b>total</div>
    <div class="stat"><b>{len(open_rows)}</b>open</div>
    <div class="stat"><b>{len(closed_rows)}</b>closed</div>
    <div class="stat"><b>{len(actions["interviews"])}</b>interview</div>
    <div class="stat"><b>{len(actions["follow_ups"])}</b>to follow</div>
  </div>
  {render_action_cards()}
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


def cmd_today(args: argparse.Namespace) -> int:
    """Daily job-search cockpit: open items grouped by next action."""
    path = _csv_path(args.csv)
    rows = read_rows(path)
    if not rows:
        print("今天还没有投递记录。先：")
        print("  python tools/tracker.py init")
        print("  python tools/tracker.py add --company … --role … --status applied")
        return 0

    today = date.today()
    actions = build_action_items(rows, today)
    open_rows = [r for r in rows if r["status"].lower() not in CLOSED_STATUSES]
    closed = [r for r in rows if r["status"].lower() in CLOSED_STATUSES]

    interviews = actions["interviews"]
    follow_ups = actions["follow_ups"]
    other_open = [
        r for r in open_rows
        if r not in interviews and r not in follow_ups
    ]

    print(f"投递记录共 {len(rows)} 条，还在跟的 {len(open_rows)} 条，已结束 {len(closed)} 条")
    if follow_ups:
        print(f"⏰ 建议跟进 {len(follow_ups)} 条（≥{FOLLOW_UP_DAYS}天无进展）")
    print()

    def dump(title: str, subset: list[dict[str, str]], hint: str) -> None:
        print(f"{title}（{len(subset)}）")
        if not subset:
            print("  暂无")
        else:
            for r in subset:
                note = f"  {r['notes'][:40]}" if r.get("notes") else ""
                extra = ""
                if r.get("city"):
                    extra += f" · {r['city']}"
                if r.get("salary"):
                    extra += f" · {r['salary']}"
                print(
                    f"  [{r['status']}] {r['company']} / {r['role']} "
                    f"· {r['channel'] or '渠道未填'}{extra}{note}"
                )
        print(f"  （{hint}）")
        print()

    dump("📅 面试相关", interviews, "需要准备就跑 /interview，状态变了用 tracker update")
    dump("⏰ 建议跟进", follow_ups, f"投了≥{FOLLOW_UP_DAYS}天没消息；如已被拒/无回复用 /outcome 记一笔")
    dump("已投/待投、等回复", other_open, "新投的用 tracker add")
    dump(f"📝 最近结束的（近{REVIEW_DAYS}天）", actions["reviews"], "复盘可以用 /outcome，旧记录别删")

    print("常用：")
    print("  python tools/tracker.py list --open-only")
    print("  python tools/tracker.py dashboard   # 打开 HTML 看板看待办卡片")
    return 0


def cmd_suggest_add(args: argparse.Namespace) -> int:
    """Print a pre-filled tracker add command (for /apply-zh handoff).

    Default status is to_apply (safe default — Agent must ask user to confirm
    before writing, and must not silently mark as applied unless user says so).
    """
    company = args.company.strip()
    role = (args.role or "").strip()
    channel = (args.channel or "Boss直聘").strip()
    cv = args.cv or f"documents/zh/resume_{company}.md"
    cover = args.cover or ""
    source = args.source or ""
    salary = args.salary or ""
    city = args.city or ""
    education = args.education or ""
    experience = args.experience or ""
    status = args.status or "to_apply"

    parts = [
        "python tools/tracker.py add",
        f"--company {company!s}",
        f"--role {role!s}" if role else "",
        f"--channel {channel!s}",
        f"--status {status}",
        f"--cv {cv}",
    ]
    if cover:
        parts.append(f"--cover {cover}")
    if source:
        parts.append(f"--source {source}")
    if salary:
        parts.append(f"--salary {salary!s}")
    if city:
        parts.append(f"--city {city!s}")
    if education:
        parts.append(f"--education {education!s}")
    if experience:
        parts.append(f"--experience {experience!s}")
    cmd = " \\\n  ".join(p for p in parts if p)

    print("=" * 60)
    print("[Tracker 预填摘要]")
    print(f"  公司:   {company}")
    print(f"  岗位:   {role or '(未填)'}")
    print(f"  渠道:   {channel}")
    print(f"  状态:   {status}（默认 to_apply = 还没投；投了请改 applied）")
    if city:
        print(f"  城市:   {city}")
    if salary:
        print(f"  薪资:   {salary}")
    if education:
        print(f"  学历:   {education}")
    if experience:
        print(f"  经验:   {experience}")
    print(f"  简历:   {cv}")
    if cover:
        print(f"  话术:   {cover}")
    print("=" * 60)
    print()
    print("# 确认后执行（让 Agent 帮你跑，或自己复制到终端）：")
    print(cmd)
    print()
    print("# 如果已经投了，把 --status to_apply 改成 --status applied")
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
    add_p.add_argument("--salary", default="")
    add_p.add_argument("--city", default="")
    add_p.add_argument("--education", default="")
    add_p.add_argument("--experience", default="")
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
    up_p.add_argument("--salary", default=None)
    up_p.add_argument("--city", default=None)
    up_p.add_argument("--education", default=None)
    up_p.add_argument("--experience", default=None)
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
        help="print pre-filled add command after /apply-zh (safe default: to_apply)",
    )
    sug_p.add_argument("--company", required=True)
    sug_p.add_argument("--role", default="")
    sug_p.add_argument("--channel", default="Boss直聘")
    sug_p.add_argument("--cv", default="")
    sug_p.add_argument("--cover", default="")
    sug_p.add_argument("--source", default="")
    sug_p.add_argument("--status", default="to_apply", help="default: to_apply (safe)")
    sug_p.add_argument("--salary", default="")
    sug_p.add_argument("--city", default="")
    sug_p.add_argument("--education", default="")
    sug_p.add_argument("--experience", default="")
    sug_p.set_defaults(func=cmd_suggest_add)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
