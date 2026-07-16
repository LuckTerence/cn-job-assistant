#!/usr/bin/env python3
"""Local application tracker — CSV as source of truth, optional SQLite + HTML.

Stdlib only. Aligns with /outcome and the job_search_tracker.csv schema:

  date,company,sector,role,role_type,channel,status,contact_person,
  fit_rating,notes,cv_file,cover_letter_file,source,
  salary,city,education,experience,skip_reason

Usage (from repo root):
  python tools/tracker.py init
  python tools/tracker.py add --company 字节 --role 后端 --channel Boss直聘 --status applied
  python tools/tracker.py add --company X --role Y --status skipped --skip-reason salary_low
  python tools/tracker.py list [--status applied]
  python tools/tracker.py update --company 字节 --role 后端 --status interview
  python tools/tracker.py show --company 字节
  python tools/tracker.py export --format html|sqlite|csv
  python tools/tracker.py dashboard   # writes job_search_tracker.html
  python tools/tracker.py today       # daily cockpit
  python tools/tracker.py skip-stats  # Phase 1: 不投原因分布（产品信号）
  python tools/tracker.py import-jobs jobs.json   # 搜岗结果批量入库（默认 to_apply）
  python tools/tracker.py suggest-add --company X --role Y ...
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import shutil
import sqlite3
import sys
from datetime import date, timedelta
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
    "skip_reason",
]

# Phase 1 product signal: why user chose not to apply (status=skipped).
# Keep keys stable — used in CSV, CLI, Issue feedback clustering.
SKIP_REASONS: dict[str, str] = {
    "salary_low": "薪资偏低",
    "location": "地点不合适",
    "low_match": "匹配度低",
    "unknown_company": "不了解公司",
    "other": "其他",
}

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


def normalize_skip_reason(raw: str | None) -> str:
    """Return canonical skip_reason key, or '' if empty/unknown.

    Accepts key or Chinese label. Unknown non-empty values map to 'other'
    so free-text does not pollute the enum (detail can live in notes).
    """
    s = (raw or "").strip()
    if not s:
        return ""
    key = s.lower().replace("-", "_").replace(" ", "_")
    if key in SKIP_REASONS:
        return key
    for k, label in SKIP_REASONS.items():
        if s == label or key == label:
            return k
    # Aliases (common agent / user phrasing)
    aliases = {
        "salary": "salary_low",
        "pay": "salary_low",
        "money": "salary_low",
        "薪资": "salary_low",
        "工资": "salary_low",
        "钱少": "salary_low",
        "地点": "location",
        "城市": "location",
        "remote": "location",
        "通勤": "location",
        "match": "low_match",
        "匹配": "low_match",
        "不匹配": "low_match",
        "company": "unknown_company",
        "公司": "unknown_company",
        "不了解": "unknown_company",
        "其他": "other",
    }
    if key in aliases:
        return aliases[key]
    if s in aliases:
        return aliases[s]
    return "other"


def validate_skip_fields(status: str, skip_reason: str) -> str | None:
    """Return error message if status/skip_reason combination is invalid."""
    st = (status or "").strip().lower()
    reason = normalize_skip_reason(skip_reason)
    if st == "skipped" and not reason:
        allowed = ", ".join(SKIP_REASONS.keys())
        return (
            f"status=skipped requires --skip-reason one of: {allowed}\n"
            "  (salary_low / location / low_match / unknown_company / other)"
        )
    if reason and st and st != "skipped":
        return (
            f"--skip-reason is only valid with --status skipped "
            f"(got status={status!r}, skip_reason={reason!r})"
        )
    return None


def compute_skip_stats(rows: list[dict[str, str]]) -> dict:
    """Aggregate skip_reason for status=skipped rows (product signal)."""
    counts: dict[str, int] = {k: 0 for k in SKIP_REASONS}
    counts["_empty"] = 0
    total = 0
    for r in rows:
        if (r.get("status") or "").strip().lower() != "skipped":
            continue
        total += 1
        key = normalize_skip_reason(r.get("skip_reason", ""))
        if not key:
            # Legacy rows written before Phase 1
            counts["_empty"] += 1
        else:
            counts[key] = counts.get(key, 0) + 1
    ranked = sorted(
        ((k, counts[k]) for k in SKIP_REASONS if counts.get(k, 0) > 0),
        key=lambda x: (-x[1], x[0]),
    )
    top_key = ranked[0][0] if ranked else ""
    top_share = (ranked[0][1] / total) if total and ranked else 0.0
    return {
        "total_skipped": total,
        "counts": counts,
        "ranked": ranked,
        "top_reason": top_key,
        "top_share": top_share,
        "signal_ready": total >= 10 and top_share >= 0.4,
    }


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
    status = (args.status or "applied").strip()
    skip_reason = normalize_skip_reason(getattr(args, "skip_reason", None) or "")
    err = validate_skip_fields(status, skip_reason)
    if err:
        print(f"error: {err}", file=sys.stderr)
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
    row["status"] = status
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
    row["skip_reason"] = skip_reason if status.lower() == "skipped" else ""
    rows.append(row)
    write_rows(path, rows)
    extra = ""
    if row["skip_reason"]:
        label = SKIP_REASONS.get(row["skip_reason"], row["skip_reason"])
        extra = f" reason={row['skip_reason']}({label})"
    print(f"added: {company} / {role or '(no role)'} [{row['status']}]{extra}")
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
        "skip_reason": args.skip_reason,
    }
    updates = {k: v for k, v in fields.items() if v is not None}
    notes_append = (getattr(args, "notes_append", None) or "").strip()
    if not updates and not notes_append:
        print(
            "error: nothing to update (pass --status / --notes / --notes-append / ...)",
            file=sys.stderr,
        )
        return 2

    if "skip_reason" in updates and updates["skip_reason"] is not None:
        updates["skip_reason"] = normalize_skip_reason(updates["skip_reason"])

    for i, _ in hits:
        merged_status = updates.get("status", rows[i].get("status", ""))
        merged_reason = updates.get(
            "skip_reason",
            rows[i].get("skip_reason", ""),
        )
        if "status" in updates or "skip_reason" in updates:
            err = validate_skip_fields(merged_status or "", merged_reason or "")
            # Allow clearing skip_reason when leaving skipped; when entering skipped, require reason
            if err and (merged_status or "").lower() == "skipped":
                print(f"error: {err}", file=sys.stderr)
                return 2
        for k, v in updates.items():
            rows[i][k] = v
        if notes_append:
            prev = (rows[i].get("notes") or "").strip()
            rows[i]["notes"] = f"{prev}\n{notes_append}".strip() if prev else notes_append
        # Clear skip_reason when status moves away from skipped
        if (rows[i].get("status") or "").lower() != "skipped":
            rows[i]["skip_reason"] = ""
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


NOT_COUNTED_STATUSES = {"to_apply", "skipped"}

ENCOURAGEMENTS: tuple[str, ...] = (
    "投了就比光收藏不投的人强一步。",
    "这个岗位不合适很正常，继续找更贴的。",
    "每次结束都是在缩小「什么适合我」的范围。",
    "拒绝是流程的一部分，不是对你整个人的判决。",
    "先保证每份材料有针对性，比多投一个更重要。",
)


def _pick_encouragement(rows: list[dict[str, str]], today: date) -> str | None:
    """Pick one encouragement line if rejection/no_response count triggers it.

    Trigger (any):
      1. rejected + no_response in last 30 days >= 3 AND count % 3 == 0
      2. rejected in this week >= 3
    Seeded by f"{today}:{len(rejected)}" so same day renders the same line (no flicker).
    """
    recent_30 = 0
    week_rejected = 0
    wk_start = _week_start(today)
    wk_end = wk_start + timedelta(days=6)
    for r in rows:
        st = r.get("status", "").lower()
        d = _parse_date(r.get("date", ""))
        if d is None:
            continue
        age = (today - d).days
        if st in ("rejected", "no_response") and 0 <= age <= 30:
            recent_30 += 1
        if st == "rejected" and wk_start <= d <= wk_end:
            week_rejected += 1

    triggered = (recent_30 >= 3 and recent_30 % 3 == 0) or week_rejected >= 3
    if not triggered:
        return None
    seed_key = f"{today.isoformat()}:{recent_30}".encode("utf-8")
    seed_val = int(hashlib.md5(seed_key).hexdigest()[:8], 16)
    return ENCOURAGEMENTS[seed_val % len(ENCOURAGEMENTS)]


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def compute_stats(rows: list[dict[str, str]], today: date | None = None) -> dict:
    """Compute positive-feedback stats for today/dashboard.

   口径：
      - total_applied (A): status not in NOT_COUNTED_STATUSES (排除 to_apply/skipped)
      - total_interviews (I): status in INTERVIEW_STATUSES
      - week_applied (W): date in current week (Mon start) AND counted in A
      - interview_rate: I/A percent string, or "暂无" if A==0
    """
    today = today or date.today()
    wk_start = _week_start(today)
    wk_end = wk_start + timedelta(days=6)

    total_applied = 0
    total_interviews = 0
    week_applied = 0
    for r in rows:
        st = r.get("status", "").lower()
        if st in NOT_COUNTED_STATUSES:
            continue
        total_applied += 1
        if st in INTERVIEW_STATUSES:
            total_interviews += 1
        d = _parse_date(r.get("date", ""))
        if d is not None and wk_start <= d <= wk_end:
            week_applied += 1

    if total_applied > 0:
        rate = round(total_interviews * 100.0 / total_applied, 1)
        rate_str = f"{rate}%"
    else:
        rate_str = "暂无"

    return {
        "total_applied": total_applied,
        "total_interviews": total_interviews,
        "week_applied": week_applied,
        "interview_rate": rate_str,
    }


def export_html(csv_path: Path, html_path: Path) -> None:
    rows = read_rows(csv_path)
    today = date.today()
    actions = build_action_items(rows, today)
    stats = compute_stats(rows, today)
    skip_stats = compute_skip_stats(rows)
    open_rows = [r for r in rows if r["status"].lower() not in CLOSED_STATUSES]
    closed_rows = [r for r in rows if r["status"].lower() in CLOSED_STATUSES]
    encouragement = _pick_encouragement(rows, today)

    visible_cols = [c for c in HEADER if any(r.get(c, "").strip() for r in rows)] or HEADER

    def esc(s: str) -> str:
        return html.escape(str(s or ""))

    def render_skip_signal() -> str:
        if skip_stats["total_skipped"] <= 0:
            return ""
        items = []
        for key, n in skip_stats["ranked"]:
            label = SKIP_REASONS.get(key, key)
            share = n * 100.0 / skip_stats["total_skipped"]
            items.append(
                f"<li><code>{esc(key)}</code> · {esc(label)} · "
                f"<b>{n}</b>（{share:.0f}%）</li>"
            )
        empty = skip_stats["counts"].get("_empty", 0)
        if empty:
            items.append(f"<li>（未填原因）· <b>{empty}</b></li>")
        signal = ""
        if skip_stats["signal_ready"]:
            top = skip_stats["top_reason"]
            signal = (
                f'<div class="card-hint">📊 信号就绪：'
                f'<code>{esc(top)}</code> ≥40% 且样本≥10，可对照 Phase 2 路线图</div>'
            )
        return (
            '<div class="card card-skip">'
            f'<div class="card-title">🚫 不投信号（{skip_stats["total_skipped"]}）</div>'
            f'<ul>{"".join(items)}</ul>'
            f"{signal}"
            '<div class="card-hint">枚举：salary_low / location / low_match / '
            "unknown_company / other · CLI: tracker.py skip-stats</div>"
            "</div>"
        )

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

        skip_card = render_skip_signal()
        if skip_card:
            cards.append(skip_card)
        if not cards:
            return (
                '<div class="card card-empty">'
                '<div class="card-title">✨ 暂无待办</div>'
                '<div class="card-hint">今天没有紧急的事，投简历是马拉松。想投新岗位随时 /apply-zh。</div>'
                '</div>'
            )
        return '<div class="actions-grid">' + "".join(cards) + '</div>'

    def render_table(title: str, subset: list[dict[str, str]], *, closed: bool = False) -> str:
        if not subset:
            return ""
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
        table_html = (
            f"<table><thead><tr>{head}</tr></thead>"
            f"<tbody>{''.join(body_parts)}</tbody></table>"
        )
        if closed:
            return (
                f'<details class="closed-fold">'
                f'<summary><h2 style="display:inline">{esc(title)} ({len(subset)})</h2>'
                f' <span class="fold-hint">（点击展开）</span></summary>'
                f"{table_html}"
                f'</details>'
            )
        return (
            f"<h2>{esc(title)} ({len(subset)})</h2>"
            f"{table_html}"
        )

    encourage_html = ""
    if encouragement:
        encourage_html = f'<div class="encourage">💬 {esc(encouragement)}</div>'

    if not rows:
        stats_html = ""
        body_content = (
            '<div class="card card-empty" style="max-width:480px;margin:3rem auto">'
            '<div class="card-title">🌱 还没有投递记录</div>'
            '<div class="card-hint">准备好了就 <code>/apply-zh &lt;JD&gt;</code> 开始第一个。</div>'
            '</div>'
        )
        tables_html = ""
    else:
        stats_html = f"""<div class="stats">
    <div class="stat"><b>{len(rows)}</b><span>total</span></div>
    <div class="stat"><b>{len(open_rows)}</b><span>open</span></div>
    <div class="stat"><b>{len(closed_rows)}</b><span>closed</span></div>
    <div class="stat"><b>{len(actions["interviews"])}</b><span>interview</span></div>
    <div class="stat"><b>{len(actions["follow_ups"])}</b><span>to follow</span></div>
    <div class="stat stat-pos"><b>{stats["total_applied"]}</b><span>累计已投</span></div>
    <div class="stat stat-pos"><b>{stats["total_interviews"]}</b><span>面试次数</span></div>
    <div class="stat stat-pos"><b>{esc(stats["interview_rate"])}</b><span>面试率</span></div>
  </div>"""
        body_content = render_action_cards()
        tables_html = (
            render_table("进行中 / Open", open_rows)
            + render_table("已结束 / Closed", closed_rows, closed=True)
        )

    is_weekend = today.weekday() >= 5
    weekend_hint = ""
    if is_weekend and actions["follow_ups"]:
        weekend_hint = (
            '<div class="weekend-hint">💡 今天是周末，HR 大概率不上班。'
            '不急的话下周一再跟进也来得及。</div>'
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
    --accent-pos: #7c3aed;
    --muted: #888;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      color: #e5e5e7;
      --bg: #1a1a1d;
      --card-bg: #242428;
      --border: #33333a;
      --muted: #999;
    }}
  }}
  body {{ max-width: 1280px; margin: 2rem auto; padding: 0 1rem; background: var(--bg); }}
  h1 {{ font-size: 1.4rem; }}
  h2 {{ font-size: 1.1rem; margin-top: 2rem; margin-bottom: 0.5rem; }}
  .meta {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 1rem; }}
  .stats {{ display: flex; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 1.5rem; }}
  .stat {{ background: var(--card-bg); padding: 0.65rem 1rem; border-radius: 8px;
           box-shadow: 0 1px 3px rgba(0,0,0,.08); min-width: 5.5rem; text-align: center; }}
  .stat b {{ display: block; font-size: 1.3rem; }}
  .stat span {{ font-size: 0.72rem; color: var(--muted); }}
  .stat-pos {{ border-top: 3px solid var(--accent-pos); }}
  .actions-grid {{ display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); margin-bottom: 2rem; }}
  .card {{ background: var(--card-bg); border-radius: 10px; padding: 1rem 1.1rem;
           box-shadow: 0 1px 3px rgba(0,0,0,.08); border-left: 4px solid #ccc; }}
  .card-iv {{ border-left-color: var(--accent-iv); }}
  .card-fu {{ border-left-color: var(--accent-fu); }}
  .card-rv {{ border-left-color: var(--accent-rv); }}
  .card-skip {{ border-left-color: #dc2626; }}
  .card-empty {{ border-left-color: var(--accent-empty); text-align: center; padding: 1.5rem; }}
  .card-title {{ font-weight: 600; font-size: 0.95rem; margin-bottom: 0.6rem; }}
  .card ul {{ margin: 0; padding-left: 1.1rem; font-size: 0.88rem; line-height: 1.7; }}
  .card-hint {{ margin-top: 0.6rem; font-size: 0.78rem; color: var(--muted); }}
  .badge {{ display: inline-block; font-size: 0.72rem; padding: 1px 6px; border-radius: 4px;
            color: #fff; vertical-align: middle; line-height: 1.4; }}
  .badge-iv {{ background: var(--accent-iv); }}
  .badge-rv {{ background: var(--accent-rv); }}
  .encourage {{ margin: 1rem 0 1.5rem; padding: 0.7rem 1rem; background: var(--card-bg);
               border-radius: 8px; color: var(--muted); font-size: 0.85rem;
               box-shadow: 0 1px 3px rgba(0,0,0,.06); border-left: 3px solid var(--accent-pos); }}
  .weekend-hint {{ margin: 0 0 1.5rem; padding: 0.6rem 1rem; background: var(--card-bg);
                   border-radius: 8px; color: var(--accent-fu); font-size: 0.85rem;
                   box-shadow: 0 1px 3px rgba(0,0,0,.06); }}
  .closed-fold {{ margin-top: 2rem; }}
  .closed-fold summary {{ cursor: pointer; list-style: none; padding: 0.5rem 0; }}
  .closed-fold summary::-webkit-details-marker {{ display: none; }}
  .closed-fold summary:hover {{ opacity: 0.8; }}
  .fold-hint {{ color: var(--muted); font-size: 0.85rem; font-weight: 400; }}
  table {{ border-collapse: collapse; width: 100%; background: var(--card-bg); font-size: 0.82rem;
           box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 2rem; border-radius: 6px; overflow: hidden; }}
  th, td {{ border-bottom: 1px solid var(--border); padding: 0.45rem 0.6rem; text-align: left; vertical-align: top; }}
  th {{ background: rgba(128,128,128,.1); position: sticky; top: 0; font-weight: 600; white-space: nowrap; }}
  tr:hover {{ background: rgba(128,128,128,.05); }}
  .row-iv td {{ border-left: 3px solid var(--accent-iv); }}
  .row-closed td {{ opacity: 0.6; }}
  code {{ background: rgba(128,128,128,.12); padding: 1px 5px; border-radius: 3px; font-size: 0.85em; }}
</style>
</head>
<body>
  <h1>求职投递看板</h1>
  <p class="meta">Source of truth: <code>{esc(str(csv_path.name))}</code>
     · generated {esc(today.isoformat())} by <code>tools/tracker.py dashboard</code>
     · do not commit (personal data)</p>
  {stats_html}
  {body_content}
  {weekend_hint}
  {encourage_html}
  {tables_html}
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
        print("还没有投递记录。准备好了就 /apply-zh <JD> 开始第一个。")
        return 0

    today = date.today()
    actions = build_action_items(rows, today)
    stats = compute_stats(rows, today)
    open_rows = [r for r in rows if r["status"].lower() not in CLOSED_STATUSES]
    closed = [r for r in rows if r["status"].lower() in CLOSED_STATUSES]

    interviews = actions["interviews"]
    follow_ups = actions["follow_ups"]
    other_open = [
        r for r in open_rows
        if r not in interviews and r not in follow_ups
    ]

    is_weekend = today.weekday() >= 5
    no_urgent = not interviews and not follow_ups

    if no_urgent:
        print("今天没有紧急的事。投简历是马拉松，歇一天也没关系。")
        print("想投新岗位随时 /apply-zh。")
        print()
    else:
        print(f"投递记录共 {len(rows)} 条，还在跟的 {len(open_rows)} 条，已结束 {len(closed)} 条")
        if follow_ups:
            print(f"⏰ 建议跟进 {len(follow_ups)} 条（≥{FOLLOW_UP_DAYS}天无进展）")
        print()

    print("── 进度 ──")
    print(f"  本周已记录投递：{stats['week_applied']} 条")
    print(f"  累计已投：{stats['total_applied']} 条")
    print(f"  累计进入面试阶段：{stats['total_interviews']} 条")
    print(f"  面试率：{stats['interview_rate']}" + ("（基于当前快照，非官方转化率）" if stats['total_applied'] > 0 else ""))
    print()

    skip_stats = compute_skip_stats(rows)
    if skip_stats["total_skipped"] > 0:
        print("── 不投信号（skipped）──")
        print(f"  合计：{skip_stats['total_skipped']} 条")
        for key, n in skip_stats["ranked"]:
            label = SKIP_REASONS.get(key, key)
            share = n * 100.0 / skip_stats["total_skipped"]
            print(f"  {key:16} {n:>3}  ({share:.0f}%)  {label}")
        empty = skip_stats["counts"].get("_empty", 0)
        if empty:
            print(f"  {'(未填原因)':16} {empty:>3}  （旧数据或未写 --skip-reason）")
        if skip_stats["signal_ready"]:
            top = skip_stats["top_reason"]
            print(
                f"  📊 信号就绪：{top} 占比 ≥40% 且样本≥10 → "
                "可考虑开 Phase 2 对应能力（见 docs/optimization-plan-close-the-loop.zh.md）"
            )
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

    if interviews:
        dump("📅 面试相关", interviews, "需要准备就跑 /interview，状态变了用 tracker update")
    if follow_ups:
        dump("⏰ 建议跟进", follow_ups, f"投了≥{FOLLOW_UP_DAYS}天没消息；如已被拒/无回复用 /outcome 记一笔")
        if is_weekend:
            print("💡 今天是周末，HR 大概率不上班。不急的话下周一再跟进也来得及。")
            print()
    if not no_urgent:
        dump("已投/待投、等回复", other_open, "新投的用 tracker add")
        dump(f"📝 最近结束的（近{REVIEW_DAYS}天）", actions["reviews"], "复盘可以用 /outcome，旧记录别删")

    print("常用：")
    print("  python tools/tracker.py list --open-only")
    print("  python tools/tracker.py dashboard   # 打开 HTML 看板看待办卡片")
    print("  python tools/tracker.py skip-stats  # 不投原因分布（产品信号）")
    return 0


def cmd_skip_stats(args: argparse.Namespace) -> int:
    """Print skip_reason distribution — Phase 1 product-signal surface."""
    path = _csv_path(args.csv)
    rows = read_rows(path)
    stats = compute_skip_stats(rows)
    total = stats["total_skipped"]
    if total == 0:
        print("还没有 status=skipped 的记录。")
        print("评估后决定不投时：")
        print(
            "  python tools/tracker.py add --company … --role … "
            "--status skipped --skip-reason salary_low|location|low_match|unknown_company|other"
        )
        print()
        print("枚举说明：")
        for k, label in SKIP_REASONS.items():
            print(f"  {k:16}  {label}")
        return 0

    print(f"不投记录：{total} 条  ← {path}")
    print("-" * 48)
    for key, n in stats["ranked"]:
        label = SKIP_REASONS.get(key, key)
        bar = "█" * n
        share = n * 100.0 / total
        print(f"  {key:16} {n:>3}  {share:5.1f}%  {label}  {bar}")
    empty = stats["counts"].get("_empty", 0)
    if empty:
        print(f"  {'(empty)':16} {empty:>3}  {empty * 100.0 / total:5.1f}%  未填原因")
    print("-" * 48)
    if stats["top_reason"]:
        top = stats["top_reason"]
        print(
            f"最高频：{top}（{SKIP_REASONS.get(top, top)}）"
            f" 占比 {stats['top_share'] * 100:.0f}%"
        )
    if stats["signal_ready"]:
        print(
            "📊 触发建议：样本≥10 且单一原因≥40% → "
            "对照 docs/optimization-plan-close-the-loop.zh.md Phase 2 选 1 项落地"
        )
    else:
        need = max(0, 10 - total)
        print(
            f"信号未就绪（建议累计 ≥10 条 skipped 再决策；还差约 {need} 条有原因的记录）"
        )
    return 0


def _first_str(raw: dict, *keys: str) -> str:
    """Return first non-empty string for any of the keys (case-insensitive key match)."""
    lower_map = {str(k).lower(): v for k, v in raw.items()}
    for key in keys:
        v = raw.get(key)
        if v is None:
            v = lower_map.get(key.lower())
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return ""


def normalize_job_record(
    raw: dict,
    *,
    default_channel: str = "",
    default_status: str = "to_apply",
) -> dict[str, str] | None:
    """Map heterogeneous job-search JSON into a tracker row dict.

    Accepts common aliases from boss export / hand-written shortlists / agent dumps.
    Returns None if company is missing (unusable row).
    """
    if not isinstance(raw, dict):
        return None
    company = _first_str(raw, "company", "company_name", "brand", "brandName", "corp")
    role = _first_str(
        raw,
        "role",
        "title",
        "job_title",
        "jobTitle",
        "job_name",
        "jobName",
        "position",
        "positionName",
    )
    channel = _first_str(
        raw,
        "channel",
        "platform",
        "source_platform",
        "site",
    ) or (default_channel or "")
    source = _first_str(
        raw,
        "source",
        "url",
        "link",
        "job_url",
        "jobUrl",
        "detail_url",
        "pcUrl",
    )
    city = _first_str(raw, "city", "location", "cityName", "area")
    salary = _first_str(raw, "salary", "salary_desc", "salaryDesc", "pay")
    education = _first_str(raw, "education", "degree", "edu")
    experience = _first_str(raw, "experience", "exp", "work_exp", "workYear")
    sector = _first_str(raw, "sector", "industry", "industryName")
    notes = _first_str(raw, "notes", "note", "remark", "desc", "description")
    status = _first_str(raw, "status") or default_status
    security_id = _first_str(raw, "security_id", "securityId", "encryptJobId", "job_id", "jobId")
    if security_id:
        tag = f"security_id={security_id}"
        notes = f"{notes}; {tag}".strip("; ").strip() if notes else tag
    if not company:
        return None
    skip_reason = normalize_skip_reason(_first_str(raw, "skip_reason", "skipReason"))
    if status.lower() != "skipped":
        skip_reason = ""
    return {
        "company": company,
        "role": role,
        "channel": channel,
        "source": source,
        "city": city,
        "salary": salary,
        "education": education,
        "experience": experience,
        "sector": sector,
        "notes": notes,
        "status": status,
        "skip_reason": skip_reason,
        "date": _first_str(raw, "date") or date.today().isoformat(),
        "contact_person": _first_str(raw, "contact", "contact_person", "hr"),
        "fit_rating": _first_str(raw, "fit", "fit_rating"),
        "cv_file": _first_str(raw, "cv", "cv_file"),
        "cover_letter_file": _first_str(raw, "cover", "cover_letter_file"),
        "role_type": _first_str(raw, "role_type", "roleType"),
    }


def load_jobs_payload(path: Path) -> list[dict]:
    """Load job list from JSON, JSON wrapper, NDJSON, or CSV."""
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        return []

    suffix = path.suffix.lower()
    if suffix == ".csv":
        rows: list[dict] = []
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(dict(row))
        return rows

    # NDJSON: multiple non-empty lines, each a JSON object
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) > 1 and lines[0].startswith("{") and not text.lstrip().startswith("["):
        try:
            objs = [json.loads(ln) for ln in lines]
            if all(isinstance(o, dict) for o in objs):
                return objs  # type: ignore[return-value]
        except json.JSONDecodeError:
            pass

    data = json.loads(text)
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("jobs", "items", "data", "results", "list", "records"):
            inner = data.get(key)
            if isinstance(inner, list):
                return [x for x in inner if isinstance(x, dict)]
        # Single job object
        return [data]
    return []


def _row_key(company: str, role: str, channel: str) -> tuple[str, str, str]:
    return (company.lower(), role.lower(), channel.lower())


def find_duplicate_index(
    rows: list[dict[str, str]],
    company: str,
    role: str,
    channel: str,
) -> int | None:
    key = _row_key(company, role, channel)
    for i, row in enumerate(rows):
        if _row_key(row.get("company", ""), row.get("role", ""), row.get("channel", "")) == key:
            return i
    return None


def import_job_rows(
    existing: list[dict[str, str]],
    jobs: list[dict[str, str]],
    *,
    on_duplicate: str = "skip",
    limit: int | None = None,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """Merge normalized jobs into existing rows.

    on_duplicate: skip | fill-empty | force
    Returns (new_rows, stats).
    """
    rows = [dict(r) for r in existing]
    stats = {"added": 0, "skipped_dup": 0, "filled": 0, "forced": 0, "invalid": 0}
    count = 0
    for job in jobs:
        if limit is not None and count >= limit:
            break
        count += 1
        company = job.get("company", "").strip()
        if not company:
            stats["invalid"] += 1
            continue
        role = job.get("role", "").strip()
        channel = job.get("channel", "").strip()
        idx = find_duplicate_index(rows, company, role, channel)
        if idx is None:
            row = {k: "" for k in HEADER}
            for k in HEADER:
                if k in job and job[k]:
                    row[k] = job[k]
            if not row.get("status"):
                row["status"] = "to_apply"
            if not row.get("date"):
                row["date"] = date.today().isoformat()
            # validate skip
            err = validate_skip_fields(row.get("status", ""), row.get("skip_reason", ""))
            if err:
                stats["invalid"] += 1
                continue
            rows.append(row)
            stats["added"] += 1
            continue

        if on_duplicate == "skip":
            stats["skipped_dup"] += 1
            continue
        if on_duplicate == "force":
            row = {k: "" for k in HEADER}
            for k in HEADER:
                if k in job and job[k]:
                    row[k] = job[k]
            if not row.get("status"):
                row["status"] = "to_apply"
            if not row.get("date"):
                row["date"] = date.today().isoformat()
            rows.append(row)
            stats["forced"] += 1
            continue
        # fill-empty: only write blank fields on existing row
        if on_duplicate == "fill-empty":
            changed = False
            for k in HEADER:
                if k in ("company", "role", "channel"):
                    continue
                new_v = (job.get(k) or "").strip()
                if new_v and not (rows[idx].get(k) or "").strip():
                    rows[idx][k] = new_v
                    changed = True
            if changed:
                stats["filled"] += 1
            else:
                stats["skipped_dup"] += 1
            continue
        stats["skipped_dup"] += 1
    return rows, stats


def cmd_import_jobs(args: argparse.Namespace) -> int:
    """Batch-import jobs from JSON/NDJSON/CSV into tracker (search → track pipeline)."""
    path = Path(args.file)
    if not path.is_file():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2

    raw_list = load_jobs_payload(path)
    if not raw_list:
        print(f"error: no job objects found in {path}", file=sys.stderr)
        return 2

    default_channel = (args.default_channel or "").strip()
    default_status = (args.default_status or "to_apply").strip()
    normalized: list[dict[str, str]] = []
    invalid = 0
    for raw in raw_list:
        job = normalize_job_record(
            raw,
            default_channel=default_channel,
            default_status=default_status,
        )
        if job is None:
            invalid += 1
            continue
        err = validate_skip_fields(job.get("status", ""), job.get("skip_reason", ""))
        if err:
            invalid += 1
            continue
        normalized.append(job)

    if not normalized and invalid:
        print(
            f"error: {invalid} row(s) invalid (need at least company); nothing to import",
            file=sys.stderr,
        )
        return 2

    on_dup = "skip"
    if args.force:
        on_dup = "force"
    elif args.fill_empty:
        on_dup = "fill-empty"

    csv_path = _csv_path(args.csv)
    existing = read_rows(csv_path)
    limit = args.limit if args.limit and args.limit > 0 else None
    new_rows, stats = import_job_rows(
        existing,
        normalized,
        on_duplicate=on_dup,
        limit=limit,
    )
    stats["invalid"] += invalid

    print(f"import from {path}")
    print(
        f"  parsed={len(raw_list)}  valid={len(normalized)}  "
        f"added={stats['added']}  filled={stats['filled']}  "
        f"dup_skipped={stats['skipped_dup']}  forced={stats['forced']}  "
        f"invalid={stats['invalid']}"
    )
    if args.dry_run:
        print("  dry-run: CSV not written")
        for j in normalized[: min(5, len(normalized))]:
            print(
                f"    · {j['company']} / {j['role'] or '(no role)'} "
                f"[{j['status']}] {j.get('city','')} {j.get('salary','')}"
            )
        if len(normalized) > 5:
            print(f"    … and {len(normalized) - 5} more")
        return 0

    write_rows(csv_path, new_rows)
    print(f"  wrote → {csv_path}  (total rows: {len(new_rows)})")
    print("  next: python tools/tracker.py list --open-only")
    print("        python tools/tracker.py today")
    print("        /apply-zh  # pick a to_apply row")
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
    print("# 若评估后不投，改成：")
    print(
        "#   --status skipped --skip-reason salary_low|location|low_match|unknown_company|other"
    )
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
    add_p.add_argument(
        "--skip-reason",
        default="",
        dest="skip_reason",
        help="required when --status skipped: salary_low|location|low_match|unknown_company|other",
    )
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
    up_p.add_argument("--notes", default=None, help="replace notes field")
    up_p.add_argument(
        "--notes-append",
        default=None,
        dest="notes_append",
        help="append a dated line to notes (preferred by /outcome)",
    )
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
    up_p.add_argument(
        "--skip-reason",
        default=None,
        dest="skip_reason",
        help="set when moving to skipped: salary_low|location|low_match|unknown_company|other",
    )
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

    skip_p = sub.add_parser(
        "skip-stats",
        help="Phase 1: distribution of skip_reason (why you chose not to apply)",
    )
    skip_p.set_defaults(func=cmd_skip_stats)

    imp_p = sub.add_parser(
        "import-jobs",
        help="batch-import search results (JSON/NDJSON/CSV) → tracker; default status to_apply",
    )
    imp_p.add_argument(
        "file",
        help="path to jobs.json / .ndjson / .csv (array, {jobs:[…]}, or one object per line)",
    )
    imp_p.add_argument(
        "--default-channel",
        default="",
        help="channel when record omits platform (e.g. Boss直聘)",
    )
    imp_p.add_argument(
        "--default-status",
        default="to_apply",
        help="status when omitted (default: to_apply — safe, not applied)",
    )
    imp_p.add_argument(
        "--fill-empty",
        action="store_true",
        help="on duplicate company+role+channel, fill blank fields only",
    )
    imp_p.add_argument(
        "--force",
        action="store_true",
        help="on duplicate, still append a new row",
    )
    imp_p.add_argument(
        "--dry-run",
        action="store_true",
        help="parse and report only; do not write CSV",
    )
    imp_p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="import at most N valid jobs (0 = no limit)",
    )
    imp_p.set_defaults(func=cmd_import_jobs)

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
