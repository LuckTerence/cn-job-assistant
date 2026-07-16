#!/usr/bin/env python3
"""Local application tracker — CSV as source of truth, optional SQLite + HTML.

Stdlib only. Aligns with /outcome and the job_search_tracker.csv schema:

  date,company,sector,role,role_type,channel,status,contact_person,
  fit_rating,notes,cv_file,cover_letter_file,source,
  salary,city,education,experience,skip_reason,expected_salary,
  match_score,match_coverage,match_verdict

Usage (from repo root):
  python tools/tracker.py init
  python tools/tracker.py add --company 字节 --role 后端 --channel Boss直聘 --status applied
  python tools/tracker.py add --company X --role Y --status skipped --skip-reason salary_low
  python tools/tracker.py list [--status applied] [--salary-flag]
  python tools/tracker.py update --company 字节 --role 后端 --status interview
  python tools/tracker.py show --company 字节
  python tools/tracker.py export --format html|sqlite|csv
  python tools/tracker.py dashboard   # writes job_search_tracker.html
  python tools/tracker.py today       # daily cockpit
  python tools/tracker.py day-plan    # 今天投谁：面试 / 跟进 / to_apply 短名单
  python tools/tracker.py rank        # 对 to_apply 批打分排序（需 cv_file + source 本地文件）
  python tools/tracker.py skip-stats  # 不投原因分布（产品信号）
  python tools/tracker.py match-outcome  # 匹配分 × 结果归因（质量飞轮）
  python tools/tracker.py import-jobs jobs.json   # 搜岗结果批量入库（默认 to_apply）
  python tools/tracker.py suggest-add --company X --role Y ...
  python tools/flow.py shortlist --jobs jobs.json   # v0.12 薄编排
  python tools/quality_gate.py --resume r.md --jd j.md  # 投前门禁
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
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
    "expected_salary",
    "match_score",
    "match_coverage",
    "match_verdict",
]

# Outcome buckets for match-score correlation (quality flywheel)
POSITIVE_OUTCOMES = frozenset(
    {
        "interview",
        "interview_1",
        "interview_2",
        "interview_final",
        "offer",
        "hired",
        # screening stays open-pipeline, not "进面+" for match-outcome
    }
)
NEGATIVE_OUTCOMES = frozenset({"rejected", "no_response", "withdrawn", "offer_declined"})

# Shown when import cannot map a company field
IMPORT_FIELD_HINT = """\
提示：每条至少需要公司名。可用字段别名（任选其一）：
  company ← company / company_name / brand / brandName / corp
  role    ← role / title / job_title / jobName / position / positionName
  channel ← channel / platform / site
  source  ← source / url / link / jobUrl / pcUrl
  city    ← city / location / cityName
  salary  ← salary / salary_desc / salaryDesc
Boss 导出 CSV 常见：brandName, jobName, cityName, salaryDesc, jobUrl
样例：examples/demo/jobs_sample.json
"""

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
    *,
    channel: str | None = None,
    exact: bool = False,
) -> list[tuple[int, dict[str, str]]]:
    """Find rows by company/role(/channel).

    exact=False (default, CLI-friendly): substring match on company/role.
    exact=True (serve / safe write): case-insensitive equality.
    channel: if set, require channel equality (case-insensitive).
    """
    hits: list[tuple[int, dict[str, str]]] = []
    company_l = (company or "").lower().strip()
    role_l = (role or "").lower().strip()
    channel_l = (channel or "").lower().strip()
    for i, row in enumerate(rows):
        rc = (row.get("company") or "").lower()
        rr = (row.get("role") or "").lower()
        if company_l:
            if exact:
                if company_l != rc:
                    continue
            elif company_l not in rc:
                continue
        if role_l:
            if exact:
                if role_l != rr:
                    continue
            elif role_l not in rr:
                continue
        if channel_l and channel_l != (row.get("channel") or "").lower():
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
    row["expected_salary"] = getattr(args, "expected_salary", None) or ""
    row["match_score"] = str(getattr(args, "match_score", None) or "")
    row["match_coverage"] = str(getattr(args, "match_coverage", None) or "")
    row["match_verdict"] = str(getattr(args, "match_verdict", None) or "")
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
    show_sal = bool(getattr(args, "salary_flag", False))
    exp_default = (getattr(args, "expected_salary", None) or "").strip() or None
    head = f"{'#':>3}  {'date':10}  {'status':14}  {'company':16}  {'role':20}  channel"
    if show_sal:
        head += "  pay"
    print(head)
    print("-" * (100 if show_sal else 90))
    for i, r in enumerate(rows, 1):
        line = (
            f"{i:>3}  {r['date'][:10]:10}  {r['status'][:14]:14}  "
            f"{r['company'][:16]:16}  {r['role'][:20]:20}  {r['channel']}"
        )
        if show_sal:
            flag = salary_flag_for_row(r, default_expected=exp_default)
            sal = (r.get("salary") or "")[:12]
            line += f"  {flag} {sal}"
        print(line)
    print(f"\n{len(rows)} row(s)  ← {path}")
    if show_sal:
        print("pay 列：期望 vs JD 薪资（✅交集 ⚠️触底/面议 ❌偏低 ·未知）")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    path = _csv_path(args.csv)
    rows = read_rows(path)
    match_channel = getattr(args, "match_channel", None)
    hits = match_rows(
        rows,
        args.company,
        args.role,
        channel=(match_channel or None) or None,
    )
    if not hits:
        print("error: no matching row", file=sys.stderr)
        return 1
    if len(hits) > 1 and not args.all:
        print(
            "error: multiple matches; narrow with --role / --match-channel or pass --all",
            file=sys.stderr,
        )
        for i, r in hits:
            print(
                f"  [{i}] {r['company']} / {r['role']} / {r.get('channel','')} / {r['status']}"
            )
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
        "expected_salary": args.expected_salary,
        "match_score": args.match_score,
        "match_coverage": args.match_coverage,
        "match_verdict": args.match_verdict,
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


# Funnel stage order for conversion display (v0.13)
FUNNEL_STAGES: tuple[str, ...] = (
    "to_apply",
    "applied",
    "screening",
    "interview",
    "offer",
    "hired",
)
# Map fine-grained statuses into funnel buckets
FUNNEL_BUCKET: dict[str, str] = {
    "to_apply": "to_apply",
    "applied": "applied",
    "in_progress": "applied",
    "screening": "screening",
    "interview": "interview",
    "interview_1": "interview",
    "interview_2": "interview",
    "interview_final": "interview",
    "offer": "offer",
    "hired": "hired",
    "rejected": "rejected",
    "no_response": "closed_other",
    "withdrawn": "closed_other",
    "offer_declined": "closed_other",
    "interview_only": "closed_other",
    "expired": "closed_other",
    "skipped": "skipped",
}


def compute_funnel(rows: list[dict[str, str]]) -> dict:
    """Pipeline counts + simple conversion rates (snapshot, not cohort)."""
    counts: dict[str, int] = {s: 0 for s in FUNNEL_STAGES}
    counts["rejected"] = 0
    counts["skipped"] = 0
    counts["closed_other"] = 0
    counts["other"] = 0
    for r in rows:
        st = (r.get("status") or "").strip().lower()
        bucket = FUNNEL_BUCKET.get(st, "other")
        counts[bucket] = counts.get(bucket, 0) + 1

    def rate(num: int, den: int) -> str:
        if den <= 0:
            return "—"
        return f"{round(100.0 * num / den, 1)}%"

    # Conversion: of rows that ever left to_apply pool (applied+), share that reached stage
    applied_plus = (
        counts["applied"]
        + counts["screening"]
        + counts["interview"]
        + counts["offer"]
        + counts["hired"]
        + counts["rejected"]
        + counts["closed_other"]
    )
    interview_plus = counts["interview"] + counts["offer"] + counts["hired"]
    offer_plus = counts["offer"] + counts["hired"]
    return {
        "counts": counts,
        "total": len(rows),
        "rates": {
            "to_apply_share": rate(counts["to_apply"], len(rows)),
            "applied_of_active": rate(
                counts["applied"] + counts["screening"] + interview_plus,
                max(1, len(rows) - counts["skipped"]),
            ),
            "interview_of_applied": rate(interview_plus, applied_plus),
            "offer_of_interview": rate(offer_plus, max(1, interview_plus)),
            "hired_of_offer": rate(counts["hired"], max(1, offer_plus)),
            "skip_share": rate(counts["skipped"], len(rows)),
        },
        "note": "快照漏斗（非同期群）；skipped 不计入 applied 转化分母旁路展示。",
    }


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


def _resolve_local_path(raw: str) -> Path | None:
    """Return Path if raw points to an existing local file (cwd or repo root)."""
    s = (raw or "").strip()
    if not s or s.startswith("http://") or s.startswith("https://"):
        return None
    p = Path(s)
    if p.is_file():
        return p
    alt = ROOT / s
    if alt.is_file():
        return alt
    return None


def _load_match_resume():
    tools_dir = Path(__file__).resolve().parent
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    import match_resume as m  # noqa: WPS433

    return m


_PROFILE_EXPECTED_CACHE: str | None | bool = False  # False = unset
_SCORE_PAIR_CACHE: dict[tuple[str, str, str], dict] = {}


def _profile_expected_cached(m) -> str:
    global _PROFILE_EXPECTED_CACHE
    if _PROFILE_EXPECTED_CACHE is not False:
        return str(_PROFILE_EXPECTED_CACHE or "")
    exp = ""
    if m.DEFAULT_PROFILE.is_file():
        exp = (
            m.extract_expected_from_profile(
                m.DEFAULT_PROFILE.read_text(encoding="utf-8", errors="replace")
            )
            or ""
        )
    _PROFILE_EXPECTED_CACHE = exp
    return exp


def salary_flag_for_row(
    row: dict[str, str],
    *,
    default_expected: str | None = None,
) -> str:
    """Return short flag ✅/⚠️/❌/· for JD salary vs expected (local parse)."""
    m = _load_match_resume()
    offered_raw = (row.get("salary") or "").strip()
    exp_raw = (row.get("expected_salary") or "").strip() or (default_expected or "").strip()
    if not exp_raw:
        exp_raw = _profile_expected_cached(m)
    if not offered_raw and not exp_raw:
        return "·"
    offered = m.parse_salary_text(offered_raw) if offered_raw else None
    expected = m.parse_salary_text(exp_raw) if exp_raw else None
    if not offered and offered_raw:
        # might be plain text without numbers
        offered = None
    cmp_ = m.compare_salary(expected, offered)
    return str(cmp_.get("signal") or "·")


def score_tracker_rows(
    rows: list[dict[str, str]],
    *,
    status_filter: str = "to_apply",
    track: str | None = None,
    limit: int = 0,
) -> list[dict]:
    """Score rows that have local cv_file + source; return ranked dicts.

    Caches by (cv_path, jd_path, track) within process to avoid double work
    when rank + day-plan run back-to-back (flow shortlist).
    """
    m = _load_match_resume()
    syn = m.load_synonym_map(track=track)
    track_key = (track or "").strip()
    want = (status_filter or "").strip().lower()
    candidates = [
        r
        for r in rows
        if not want or (r.get("status") or "").lower() == want
    ]
    results: list[dict] = []
    for r in candidates:
        company = r.get("company", "")
        role = r.get("role", "")
        cv_p = _resolve_local_path(r.get("cv_file", ""))
        jd_p = _resolve_local_path(r.get("source", ""))
        base = {
            "company": company,
            "role": role,
            "channel": r.get("channel", ""),
            "city": r.get("city", ""),
            "salary": r.get("salary", ""),
            "status": r.get("status", ""),
            "cv_file": r.get("cv_file", ""),
            "source": r.get("source", ""),
            "fit_rating": r.get("fit_rating", ""),
        }
        if not cv_p or not jd_p:
            results.append(
                {
                    **base,
                    "score": None,
                    "keyword_coverage": None,
                    "verdict": "unscored",
                    "error": "need local cv_file + source (JD file)",
                }
            )
            continue
        cache_key = (str(cv_p.resolve()), str(jd_p.resolve()), track_key)
        cached = _SCORE_PAIR_CACHE.get(cache_key)
        if cached is not None:
            results.append(
                {
                    **base,
                    "score": cached["score"],
                    "keyword_coverage": cached["keyword_coverage"],
                    "verdict": cached["verdict"],
                    "miss_top": list(cached.get("miss_top") or []),
                    "error": "",
                    "stored_score": r.get("match_score", ""),
                    "from_cache": True,
                }
            )
            continue
        try:
            result = m.match_texts(
                cv_p.read_text(encoding="utf-8", errors="replace"),
                jd_p.read_text(encoding="utf-8", errors="replace"),
                synonym_map=syn,
            )
            payload = {
                "score": result.score,
                "keyword_coverage": result.keyword_coverage,
                "verdict": result.verdict,
                "miss_top": result.keywords.miss[:5],
            }
            _SCORE_PAIR_CACHE[cache_key] = payload
            results.append(
                {
                    **base,
                    **payload,
                    "error": "",
                    "stored_score": r.get("match_score", ""),
                }
            )
        except OSError as e:
            results.append(
                {
                    **base,
                    "score": None,
                    "keyword_coverage": None,
                    "verdict": "unscored",
                    "error": str(e),
                }
            )
    scored = [x for x in results if x.get("score") is not None]
    unscored = [x for x in results if x.get("score") is None]
    scored.sort(key=lambda x: float(x["score"] or 0), reverse=True)
    ordered = scored + unscored
    if limit and limit > 0:
        ordered = ordered[:limit]
    return ordered


def build_day_plan(
    rows: list[dict[str, str]],
    *,
    today: date | None = None,
    apply_limit: int = 3,
    track: str | None = None,
    with_scores: bool = True,
) -> dict:
    """Build today's plan: interviews, follow-ups, top to_apply (optionally ranked)."""
    today = today or date.today()
    actions = build_action_items(rows, today)
    to_apply = [r for r in rows if (r.get("status") or "").lower() == "to_apply"]
    ranked: list[dict] = []
    if with_scores and to_apply:
        ranked = score_tracker_rows(to_apply, status_filter="to_apply", track=track)
        # Prefer scored order; pad with unscored to_apply
        pick: list[dict] = []
        seen: set[tuple[str, str, str]] = set()
        for item in ranked:
            key = (
                item.get("company", "").lower(),
                item.get("role", "").lower(),
                item.get("channel", "").lower(),
            )
            if key in seen:
                continue
            seen.add(key)
            pick.append(item)
            if len(pick) >= apply_limit:
                break
        focus_apply = pick
    else:
        focus_apply = [
            {
                "company": r.get("company", ""),
                "role": r.get("role", ""),
                "channel": r.get("channel", ""),
                "city": r.get("city", ""),
                "salary": r.get("salary", ""),
                "status": r.get("status", ""),
                "score": None,
                "verdict": "",
                "error": "",
            }
            for r in to_apply[:apply_limit]
        ]
    return {
        "date": today.isoformat(),
        "interviews": actions["interviews"],
        "follow_ups": actions["follow_ups"],
        "reviews": actions["reviews"],
        "focus_apply": focus_apply,
        "to_apply_total": len(to_apply),
    }


STATUS_EDIT_OPTIONS = (
    "to_apply",
    "applied",
    "screening",
    "interview",
    "interview_1",
    "interview_2",
    "offer",
    "hired",
    "rejected",
    "no_response",
    "skipped",
    "withdrawn",
)


def export_html(csv_path: Path, html_path: Path, *, live: bool = False) -> None:
    """Write dashboard HTML.

    live=True: for tracker serve — status select POSTs to /api/update.
    live=False: offline file — select copies update command to clipboard.
    """
    rows = read_rows(csv_path)
    today = date.today()
    actions = build_action_items(rows, today)
    stats = compute_stats(rows, today)
    skip_stats = compute_skip_stats(rows)
    funnel = compute_funnel(rows)
    match_outcome = compute_match_outcome(rows)
    open_rows = [r for r in rows if r["status"].lower() not in CLOSED_STATUSES]
    closed_rows = [r for r in rows if r["status"].lower() in CLOSED_STATUSES]
    encouragement = _pick_encouragement(rows, today)

    # City histogram for open rows (decision glance)
    city_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for r in rows:
        st = (r.get("status") or "unknown").strip() or "unknown"
        status_counts[st] = status_counts.get(st, 0) + 1
    for r in open_rows:
        c = (r.get("city") or "（未填城市）").strip() or "（未填城市）"
        city_counts[c] = city_counts.get(c, 0) + 1
    cities_sorted = sorted(city_counts.items(), key=lambda x: (-x[1], x[0]))[:12]
    statuses_sorted = sorted(status_counts.items(), key=lambda x: (-x[1], x[0]))

    visible_cols = [c for c in HEADER if any(r.get(c, "").strip() for r in rows)] or HEADER
    # Prefer showing match columns when any score exists (quality flywheel)
    for col in ("match_score", "match_coverage", "match_verdict"):
        if any((r.get(col) or "").strip() for r in rows) and col not in visible_cols:
            visible_cols.append(col)

    def esc(s: str) -> str:
        return html.escape(str(s or ""))

    def render_match_outcome_card() -> str:
        if match_outcome.get("scored", 0) <= 0:
            return ""
        rows_html = []
        for b in match_outcome.get("bands") or []:
            if not b.get("n"):
                continue
            avg = b.get("avg_score")
            avg_s = "—" if avg is None else f"{avg:.0f}"
            rows_html.append(
                f"<tr><td><code>{esc(b['band'])}</code></td>"
                f"<td>{b['n']}</td><td>{esc(avg_s)}</td>"
                f"<td>{b['positive']}</td><td>{b['negative']}</td>"
                f"<td>{esc(b.get('positive_rate_closed') or '—')}</td></tr>"
            )
        if not rows_html:
            return ""
        ready = (
            "样本可粗判策略"
            if match_outcome.get("signal_ready")
            else "分数样本仍少，继续 gate 后写入 match_score"
        )
        return (
            '<div class="card card-match">'
            f'<div class="card-title">🎯 匹配分 × 结果（有分 {match_outcome["scored"]}/{match_outcome["total"]}）</div>'
            '<table class="mini"><thead><tr>'
            "<th>band</th><th>n</th><th>avg</th><th>进面+</th><th>拒/无</th><th>关闭进面率</th>"
            "</tr></thead><tbody>"
            + "".join(rows_html)
            + "</tbody></table>"
            f'<div class="card-hint">{esc(ready)} · CLI: tracker match-outcome</div>'
            "</div>"
        )

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

    def render_funnel() -> str:
        if not rows:
            return ""
        c = funnel["counts"]
        r = funnel["rates"]
        stages = [
            ("to_apply", "待投", c.get("to_apply", 0)),
            ("applied", "已投", c.get("applied", 0) + c.get("screening", 0)),
            ("interview", "面试", c.get("interview", 0)),
            ("offer", "Offer", c.get("offer", 0)),
            ("hired", "入职", c.get("hired", 0)),
        ]
        parts = []
        for i, (_, lab, n) in enumerate(stages):
            parts.append(
                f'<div class="funnel-step"><span class="funnel-label">{esc(lab)}</span>'
                f'<span class="funnel-n"><b>{n}</b></span></div>'
            )
            if i < len(stages) - 1:
                parts.append('<div class="funnel-arrow">→</div>')
        return (
            '<div class="card card-funnel">'
            '<div class="card-title">📉 投递漏斗（快照）</div>'
            f'<div class="funnel-row">{"".join(parts)}</div>'
            f'<div class="card-hint">面试/已投≈{esc(r["interview_of_applied"])} · '
            f'Offer/面试≈{esc(r["offer_of_interview"])} · '
            f'跳过 {c.get("skipped", 0)} · 拒绝 {c.get("rejected", 0)} · '
            f'CLI: tracker.py funnel</div>'
            f'<div class="card-hint">{esc(funnel["note"])}</div>'
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

        funnel_card = render_funnel()
        if funnel_card:
            cards.insert(0, funnel_card)
        match_card = render_match_outcome_card()
        if match_card:
            cards.append(match_card)
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

    def status_select(r: dict[str, str]) -> str:
        st = (r.get("status") or "").strip()
        opts = []
        seen = set()
        for s in STATUS_EDIT_OPTIONS:
            seen.add(s)
            sel = " selected" if s == st.lower() or s == st else ""
            opts.append(f'<option value="{esc(s)}"{sel}>{esc(s)}</option>')
        if st and st.lower() not in seen:
            opts.insert(0, f'<option value="{esc(st)}" selected>{esc(st)}</option>')
        return (
            f'<select class="status-edit" '
            f'data-company="{esc(r.get("company", ""))}" '
            f'data-role="{esc(r.get("role", ""))}" '
            f'data-channel="{esc(r.get("channel", ""))}" '
            f'title="改状态">'
            f'{"".join(opts)}</select>'
        )

    def render_table(title: str, subset: list[dict[str, str]], *, closed: bool = False) -> str:
        if not subset:
            return ""
        head = "".join(f"<th>{esc(h)}</th>" for h in visible_cols)
        head += "<th>改状态</th>"
        body_parts = []
        for r in subset:
            cells = "".join(f"<td>{esc(r.get(c, ''))}</td>" for c in visible_cols)
            cells += f"<td class=\"td-action\">{status_select(r)}</td>"
            st = r.get("status", "").lower()
            city = (r.get("city") or "").strip()
            cls = "data-row"
            if st in INTERVIEW_STATUSES:
                cls += " row-iv"
            elif st in REVIEW_STATUSES or st in CLOSED_STATUSES:
                cls += " row-closed"
            body_parts.append(
                f'<tr class="{cls}" data-status="{esc(st)}" data-city="{esc(city)}">{cells}</tr>'
            )
        table_html = (
            f'<table class="jobs-table"><thead><tr>{head}</tr></thead>'
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

    def render_filter_bar() -> str:
        if not rows:
            return ""
        status_opts = "".join(
            f'<option value="{esc(s)}">{esc(s)} ({n})</option>'
            for s, n in statuses_sorted
        )
        city_opts = "".join(
            f'<option value="{esc(c)}">{esc(c)} ({n})</option>'
            for c, n in cities_sorted
        )
        city_chips = "".join(
            f'<span class="chip">{esc(c)} <b>{n}</b></span>' for c, n in cities_sorted[:8]
        )
        return f"""
  <div class="filter-bar">
    <div class="filter-row">
      <label>状态
        <select id="filter-status">
          <option value="">全部状态</option>
          {status_opts}
        </select>
      </label>
      <label>城市
        <select id="filter-city">
          <option value="">全部城市</option>
          {city_opts}
        </select>
      </label>
      <button type="button" id="filter-reset" class="btn-reset">重置</button>
      <span class="filter-meta" id="filter-count"></span>
    </div>
    <div class="city-chips" title="进行中岗位的城市分布">{city_chips or '<span class="chip muted">暂无城市字段</span>'}</div>
  </div>
  <script>
  (function() {{
    const st = document.getElementById('filter-status');
    const ct = document.getElementById('filter-city');
    const reset = document.getElementById('filter-reset');
    const countEl = document.getElementById('filter-count');
    function apply() {{
      const sv = (st && st.value || '').toLowerCase();
      const cv = (ct && ct.value || '');
      let vis = 0, total = 0;
      document.querySelectorAll('tr.data-row').forEach(function(tr) {{
        total++;
        const rs = (tr.getAttribute('data-status') || '').toLowerCase();
        const rc = tr.getAttribute('data-city') || '';
        const okS = !sv || rs === sv;
        const okC = !cv || rc === cv;
        const show = okS && okC;
        tr.style.display = show ? '' : 'none';
        if (show) vis++;
      }});
      if (countEl) countEl.textContent = '显示 ' + vis + ' / ' + total + ' 行';
    }}
    if (st) st.addEventListener('change', apply);
    if (ct) ct.addEventListener('change', apply);
    if (reset) reset.addEventListener('click', function() {{
      if (st) st.value = '';
      if (ct) ct.value = '';
      apply();
    }});
    apply();
  }})();
  </script>
"""

    def render_status_editor_js() -> str:
        live_js = "true" if live else "false"
        return f"""
  <div id="toast" class="toast" hidden></div>
  <script>
  (function() {{
    const LIVE = {live_js};
    const toast = document.getElementById('toast');
    function showToast(msg, ok) {{
      if (!toast) return;
      toast.hidden = false;
      toast.textContent = msg;
      toast.className = 'toast ' + (ok ? 'ok' : 'err');
      setTimeout(function() {{ toast.hidden = true; }}, 2800);
    }}
    function buildCmd(company, role, channel, status) {{
      let c = 'python tools/tracker.py update --company ' + JSON.stringify(company)
        + ' --role ' + JSON.stringify(role)
        + ' --status ' + status;
      if (channel) c += ' --channel ' + JSON.stringify(channel);
      if (status === 'skipped') c += ' --skip-reason other';
      return c;
    }}
    document.querySelectorAll('select.status-edit').forEach(function(sel) {{
      sel.addEventListener('change', function() {{
        const company = sel.getAttribute('data-company') || '';
        const role = sel.getAttribute('data-role') || '';
        const channel = sel.getAttribute('data-channel') || '';
        const status = sel.value;
        if (LIVE) {{
          fetch('/api/update', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{company: company, role: role, channel: channel, status: status}})
          }}).then(function(r) {{ return r.json().then(function(j) {{ return {{ok: r.ok, j: j}}; }}); }})
            .then(function(x) {{
              if (x.ok) {{
                showToast('已更新: ' + company + ' → ' + status, true);
                setTimeout(function() {{ location.reload(); }}, 500);
              }} else {{
                showToast((x.j && x.j.error) || '更新失败', false);
              }}
            }}).catch(function(e) {{ showToast(String(e), false); }});
        }} else {{
          const cmd = buildCmd(company, role, channel, status);
          if (navigator.clipboard && navigator.clipboard.writeText) {{
            navigator.clipboard.writeText(cmd).then(function() {{
              showToast('已复制 update 命令，到终端粘贴执行', true);
            }}).catch(function() {{
              prompt('复制此命令到终端执行:', cmd);
            }});
          }} else {{
            prompt('复制此命令到终端执行:', cmd);
          }}
        }}
      }});
    }});
  }})();
  </script>
"""

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
  .card-funnel {{ border-left-color: #0d9488; }}
  .card-match {{ border-left-color: #7c3aed; }}
  .card-match table.mini {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; margin-top: 0.4rem; }}
  .card-match table.mini th, .card-match table.mini td {{
    text-align: left; padding: 0.2rem 0.35rem; border-bottom: 1px solid var(--border);
  }}
  .funnel-row {{ display: flex; flex-wrap: wrap; align-items: center; gap: 0.35rem; margin: 0.4rem 0; }}
  .funnel-step {{ background: rgba(13,148,136,.12); padding: 0.35rem 0.6rem; border-radius: 8px;
                  text-align: center; min-width: 3.2rem; }}
  .funnel-label {{ display: block; font-size: 0.7rem; color: var(--muted); }}
  .funnel-n b {{ font-size: 1.1rem; }}
  .funnel-arrow {{ color: var(--muted); font-size: 0.9rem; }}
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
  .filter-bar {{ background: var(--card-bg); padding: 0.85rem 1rem; border-radius: 10px;
                 box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 1.25rem; }}
  .filter-row {{ display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: end; }}
  .filter-row label {{ font-size: 0.8rem; color: var(--muted); display: flex; flex-direction: column; gap: 0.25rem; }}
  .filter-row select {{ min-width: 9rem; padding: 0.35rem 0.5rem; border-radius: 6px;
                        border: 1px solid var(--border); background: var(--bg); color: inherit; }}
  .btn-reset {{ padding: 0.4rem 0.75rem; border-radius: 6px; border: 1px solid var(--border);
                background: transparent; color: inherit; cursor: pointer; font-size: 0.85rem; }}
  .filter-meta {{ font-size: 0.8rem; color: var(--muted); margin-left: auto; }}
  .city-chips {{ display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.65rem; }}
  .chip {{ font-size: 0.75rem; padding: 0.2rem 0.55rem; border-radius: 999px;
           background: rgba(128,128,128,.12); }}
  .chip b {{ margin-left: 0.2rem; }}
  .chip.muted {{ color: var(--muted); }}
  .td-action {{ white-space: nowrap; min-width: 7.5rem; }}
  select.status-edit {{ max-width: 9rem; padding: 0.25rem 0.35rem; border-radius: 6px;
                        border: 1px solid var(--border); background: var(--bg); color: inherit;
                        font-size: 0.78rem; }}
  .toast {{ position: fixed; bottom: 1.2rem; right: 1.2rem; z-index: 50;
            padding: 0.7rem 1rem; border-radius: 8px; font-size: 0.85rem;
            box-shadow: 0 4px 16px rgba(0,0,0,.18); max-width: 22rem; }}
  .toast.ok {{ background: #065f46; color: #ecfdf5; }}
  .toast.err {{ background: #991b1b; color: #fef2f2; }}
  .live-banner {{ background: #0f766e; color: #ecfdf5; padding: 0.5rem 1rem; border-radius: 8px;
                  font-size: 0.85rem; margin-bottom: 1rem; }}
</style>
</head>
<body>
  <h1>求职投递看板</h1>
  <p class="meta">Source of truth: <code>{esc(str(csv_path.name))}</code>
     · generated {esc(today.isoformat())} by <code>tools/tracker.py {"serve" if live else "dashboard"}</code>
     · do not commit (personal data)
     · 今日: <code>day-plan</code> · 批打分: <code>rank</code>
     · {"一键改状态已启用" if live else "file 模式：改状态下拉会复制 update 命令"}</p>
  {'<div class="live-banner">🟢 本地服务模式：下拉改状态会直接写 CSV（仅本机 127.0.0.1）</div>' if live else ""}
  {stats_html}
  {body_content}
  {weekend_hint}
  {encourage_html}
  {render_filter_bar() if rows else ""}
  {tables_html}
  {render_status_editor_js() if rows else ""}
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
    export_html(path, dest, live=False)
    print(f"dashboard → {dest}")
    print("提示: 表内「改状态」会复制 update 命令；要一键写盘请用:")
    print("  python tools/tracker.py serve")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """Local-only HTTP dashboard with one-click status update (stdlib)."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import json as _json

    path = _csv_path(args.csv)
    ensure_csv(path)
    host = args.host or "127.0.0.1"
    port = int(args.port or 8765)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *a) -> None:
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % a))

        def _send(self, code: int, body: bytes, content_type: str = "text/html; charset=utf-8") -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path.split("?")[0] in ("/", "/index.html", "/dashboard"):
                import tempfile

                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".html", delete=False, encoding="utf-8"
                ) as tmp:
                    tmp_path = Path(tmp.name)
                try:
                    export_html(path, tmp_path, live=True)
                    body = tmp_path.read_bytes()
                finally:
                    tmp_path.unlink(missing_ok=True)
                self._send(200, body)
                return
            if self.path.startswith("/api/health"):
                self._send(200, b'{"ok":true}', "application/json")
                return
            self._send(404, b"not found")

        def do_POST(self) -> None:  # noqa: N802
            if self.path.split("?")[0] != "/api/update":
                self._send(404, b'{"error":"not found"}', "application/json")
                return
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b"{}"
            try:
                data = _json.loads(raw.decode("utf-8"))
            except _json.JSONDecodeError:
                self._send(400, b'{"error":"bad json"}', "application/json")
                return
            company = str(data.get("company") or "").strip()
            role = str(data.get("role") or "").strip()
            channel = str(data.get("channel") or "").strip()
            status = str(data.get("status") or "").strip()
            if not company or not status:
                self._send(
                    400,
                    b'{"error":"company and status required"}',
                    "application/json",
                )
                return
            rows = read_rows(path)
            # Exact match only — never bulk-update substring hits (P0 safety)
            hits = match_rows(
                rows,
                company,
                role or None,
                channel=channel or None,
                exact=True,
            )
            if not hits:
                self._send(404, b'{"error":"no matching row"}', "application/json")
                return
            if len(hits) > 1:
                self._send(
                    400,
                    _json.dumps(
                        {
                            "error": "multiple matches; refine company/role/channel",
                            "count": len(hits),
                        },
                        ensure_ascii=False,
                    ).encode(),
                    "application/json",
                )
                return
            skip_reason = ""
            if status.lower() == "skipped":
                skip_reason = normalize_skip_reason(
                    str(data.get("skip_reason") or "other")
                )
                err = validate_skip_fields(status, skip_reason)
                if err:
                    self._send(
                        400,
                        _json.dumps({"error": err}).encode(),
                        "application/json",
                    )
                    return
            i, _ = hits[0]
            rows[i]["status"] = status
            if status.lower() == "skipped":
                rows[i]["skip_reason"] = skip_reason
            else:
                rows[i]["skip_reason"] = ""
            write_rows(path, rows)
            body = _json.dumps(
                {"ok": True, "company": company, "status": status, "updated": 1},
                ensure_ascii=False,
            ).encode()
            self._send(200, body, "application/json")

    server = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}/"
    print(f"tracker serve → {url}")
    print(f"CSV: {path}")
    print("仅监听本机；Ctrl+C 结束。改状态下拉会直接写盘。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    finally:
        server.server_close()
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
    print("  python tools/tracker.py day-plan    # 今天投谁（短名单）")
    print("  python tools/tracker.py rank        # to_apply 批打分排序")
    print("  python tools/tracker.py list --open-only")
    print("  python tools/tracker.py dashboard   # 打开 HTML 看板看待办卡片")
    print("  python tools/tracker.py skip-stats  # 不投原因分布（产品信号）")
    return 0


def cmd_day_plan(args: argparse.Namespace) -> int:
    """Print today's focus list: interviews → follow-ups → top to_apply."""
    path = _csv_path(args.csv)
    rows = read_rows(path)
    if not rows:
        print("还没有投递记录。先 import-jobs 或 /apply-zh，再来 day-plan。")
        return 0

    limit = args.limit if args.limit and args.limit > 0 else 3
    track = (args.track or "").strip() or None
    plan = build_day_plan(
        rows,
        apply_limit=limit,
        track=track,
        with_scores=not args.no_score,
    )

    print(f"【今日计划 · {plan['date']}】")
    print()

    exp_default = (getattr(args, "expected_salary", None) or "").strip() or None

    def line_row(r: dict, prefix: str = "") -> None:
        extra = ""
        if r.get("city"):
            extra += f" · {r['city']}"
        if r.get("salary"):
            flag = salary_flag_for_row(r, default_expected=exp_default)
            extra += f" · {flag}{r['salary']}"
        score = r.get("score")
        score_s = f"  分={score}" if score is not None else ""
        if r.get("error") and score is None and (
            r.get("status") == "to_apply" or r.get("verdict") == "unscored"
        ):
            score_s = "  （缺本地简历/JD，无法打分）"
        print(
            f"  {prefix}{r.get('company','')} / {r.get('role','')}"
            f" · {r.get('channel') or '渠道未填'}{extra}{score_s}"
        )

    print(f"1) 面试相关（{len(plan['interviews'])}）")
    if plan["interviews"]:
        for r in plan["interviews"]:
            line_row(r, prefix=f"[{r.get('status','')}] ")
    else:
        print("  暂无")
    print()

    print(f"2) 建议跟进 ≥{FOLLOW_UP_DAYS} 天（{len(plan['follow_ups'])}）")
    if plan["follow_ups"]:
        for r in plan["follow_ups"]:
            line_row(r)
    else:
        print("  暂无")
    print()

    print(
        f"3) 建议今天推进的待投 to_apply"
        f"（展示 {len(plan['focus_apply'])} / 共 {plan['to_apply_total']}）"
    )
    if plan["focus_apply"]:
        for i, r in enumerate(plan["focus_apply"], 1):
            line_row(r, prefix=f"{i}. ")
    else:
        print("  暂无 to_apply。可用 import-jobs 入库或 /apply-zh 生成后记 to_apply。")
    print()

    if plan["to_apply_total"] > limit:
        print(f"其余 to_apply 用: python tools/tracker.py rank --limit {limit * 3}")
    print("投完用 /outcome 或 tracker update；不投: --status skipped --skip-reason …")
    print("看板: python tools/tracker.py dashboard")
    return 0


def cmd_rank(args: argparse.Namespace) -> int:
    """Batch-score tracker rows (default: to_apply) and print ranking."""
    path = _csv_path(args.csv)
    rows = read_rows(path)
    status = (args.status or "to_apply").strip()
    track = (args.track or "").strip() or None
    limit = args.limit if args.limit and args.limit > 0 else 0
    ranked = score_tracker_rows(
        rows, status_filter=status, track=track, limit=limit
    )
    if not ranked:
        print(f"没有 status={status} 的记录。")
        print("先: python tools/tracker.py import-jobs jobs.json")
        return 0

    if args.json:
        print(json.dumps({"results": ranked}, ensure_ascii=False, indent=2))
    else:
        print(f"【批打分排序 · status={status} · {len(ranked)} 条】")
        print(f"{'#':>3}  {'score':>6}  {'cov%':>5}  {'verdict':16}  company / role")
        print("-" * 78)
        for i, r in enumerate(ranked, 1):
            if r.get("score") is None:
                print(
                    f"{i:>3}  {'—':>6}  {'—':>5}  {'unscored':16}  "
                    f"{r.get('company')} / {r.get('role')}  "
                    f"({r.get('error','')})"
                )
            else:
                print(
                    f"{i:>3}  {float(r['score']):6.1f}  "
                    f"{float(r.get('keyword_coverage') or 0):5.1f}  "
                    f"{str(r.get('verdict',''))[:16]:16}  "
                    f"{r.get('company')} / {r.get('role')}"
                    f"{' · ' + r['city'] if r.get('city') else ''}"
                )
        scored_n = sum(1 for r in ranked if r.get("score") is not None)
        print()
        print(f"已打分 {scored_n} · 未打分 {len(ranked) - scored_n}")
        print("提示: cv_file 与 source 需为本地简历/JD 路径才能打分；URL 请先落盘。")
        print("今日短名单: python tools/tracker.py day-plan")

    if args.write_fit:
        # Write score into fit_rating + dedicated match_* columns (status-scoped)
        want_st = status.lower()
        by_key = {
            (
                (r.get("company") or "").lower(),
                (r.get("role") or "").lower(),
                (r.get("channel") or "").lower(),
            ): r
            for r in ranked
            if r.get("score") is not None
        }
        scored_total = len(by_key)
        changed = 0
        for row in rows:
            if want_st and (row.get("status") or "").lower() != want_st:
                continue
            key = (
                row.get("company", "").lower(),
                row.get("role", "").lower(),
                row.get("channel", "").lower(),
            )
            hit = by_key.get(key)
            if hit:
                row["fit_rating"] = str(hit["score"])
                row["match_score"] = str(hit["score"])
                cov = hit.get("keyword_coverage")
                row["match_coverage"] = "" if cov is None else str(cov)
                row["match_verdict"] = str(hit.get("verdict") or "")
                changed += 1
        if changed:
            write_rows(path, rows)
            extra = ""
            if limit and scored_total and changed < scored_total:
                extra = f"（limit={limit}，仅写入本页排序结果）"
            print(
                f"已写入 fit_rating + match_score/coverage/verdict"
                f"（{changed}/{scored_total} 行{extra}）→ {path}",
                file=sys.stderr,
            )
    if args.out:
        Path(args.out).write_text(
            json.dumps({"results": ranked}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote → {args.out}", file=sys.stderr)
    return 0


def cmd_funnel(args: argparse.Namespace) -> int:
    """Print application funnel snapshot (v0.13)."""
    path = _csv_path(args.csv)
    rows = read_rows(path)
    funnel = compute_funnel(rows)
    if args.json:
        print(json.dumps(funnel, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("还没有投递记录。")
        return 0
    c = funnel["counts"]
    r = funnel["rates"]
    print(f"【投递漏斗 · 快照】共 {funnel['total']} 条  ← {path}")
    print("-" * 48)
    print(f"  待投 to_apply     {c.get('to_apply', 0):>4}  （占全部 {r['to_apply_share']}）")
    print(f"  已投 applied+     {c.get('applied', 0) + c.get('screening', 0):>4}")
    print(f"  面试 interview+   {c.get('interview', 0):>4}  （/已投系 {r['interview_of_applied']}）")
    print(f"  Offer             {c.get('offer', 0):>4}  （/面试系 {r['offer_of_interview']}）")
    print(f"  入职 hired        {c.get('hired', 0):>4}")
    print(f"  拒绝 rejected     {c.get('rejected', 0):>4}")
    print(f"  不投 skipped      {c.get('skipped', 0):>4}  （{r['skip_share']}）")
    print(f"  其他关闭          {c.get('closed_other', 0):>4}")
    print("-" * 48)
    print(funnel["note"])
    print("看板卡片: python tools/tracker.py dashboard")
    print("人话周报: python tools/tracker.py weekly-report")
    return 0


def cmd_weekly_report(args: argparse.Namespace) -> int:
    """Human weekly battle report (career-ops style narrative, local only)."""
    path = _csv_path(args.csv)
    rows = read_rows(path)
    today = date.today()
    stats = compute_stats(rows, today)
    funnel = compute_funnel(rows)
    skip = compute_skip_stats(rows)
    actions = build_action_items(rows, today)
    c = funnel["counts"]

    if args.json:
        print(
            json.dumps(
                {
                    "stats": stats,
                    "funnel": funnel,
                    "skip": {
                        "total": skip["total_skipped"],
                        "top": skip.get("top_reason"),
                        "ranked": skip.get("ranked"),
                    },
                    "interviews": len(actions["interviews"]),
                    "follow_ups": len(actions["follow_ups"]),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if not rows:
        print("【本周求职战报】还没有记录。先 /apply-zh 或 import-jobs 记一笔。")
        return 0

    print(f"【本周求职战报 · {today.isoformat()}】")
    print()
    print(
        f"本周记了 {stats['week_applied']} 条投递向记录；"
        f"累计已投口径 {stats['total_applied']}，面试阶段 {stats['total_interviews']}，"
        f"面试率 {stats['interview_rate']}。"
    )
    print(
        f"管道快照：待投 {c.get('to_apply', 0)} · "
        f"已投+筛 {c.get('applied', 0) + c.get('screening', 0)} · "
        f"面试 {c.get('interview', 0)} · Offer {c.get('offer', 0)} · "
        f"入职 {c.get('hired', 0)} · 拒 {c.get('rejected', 0)} · 不投 {c.get('skipped', 0)}。"
    )
    if actions["interviews"]:
        print(f"进行中的面试 {len(actions['interviews'])} 场——优先准备 /interview。")
    if actions["follow_ups"]:
        print(
            f"有 {len(actions['follow_ups'])} 条 ≥{FOLLOW_UP_DAYS} 天无进展，"
            "适合 /outcome 记跟进或无回复。"
        )
    if skip["total_skipped"] and skip.get("ranked"):
        top_k, top_n = skip["ranked"][0]
        label = SKIP_REASONS.get(top_k, top_k)
        print(f"不投原因最高频：{label}（{top_k}×{top_n}）。筛岗标准可以更早用这个挡。")
    print()
    print("建议下周：")
    print("  1. python tools/tracker.py day-plan --limit 5")
    print("  2. 对 day-plan 前 1～2 名跑 /apply-zh（不要群发）")
    print("  3. 状态变化立刻 /outcome 或 tracker update")
    print()
    print("（战报为本地快照叙事，不是官方转化率。）")
    return 0


def _parse_match_score(row: dict[str, str]) -> float | None:
    raw = (row.get("match_score") or row.get("fit_rating") or "").strip()
    if not raw:
        return None
    # fit_rating may be "72" or "72/100" or "strong"
    m = re.search(r"(\d+(?:\.\d+)?)", raw)
    if not m:
        return None
    try:
        v = float(m.group(1))
    except ValueError:
        return None
    if v > 100:
        return None
    return v


def score_band(score: float | None) -> str:
    if score is None:
        return "unscored"
    if score >= 70:
        return "high"
    if score >= 40:
        return "mid"
    return "low"


def compute_match_outcome(rows: list[dict[str, str]]) -> dict:
    """Correlate stored match_score with application outcomes (quality flywheel)."""
    bands = ("high", "mid", "low", "unscored")
    empty = {
        b: {
            "n": 0,
            "positive": 0,
            "negative": 0,
            "open": 0,
            "skipped": 0,
            "other": 0,
            "scores": [],
        }
        for b in bands
    }
    for r in rows:
        score = _parse_match_score(r)
        band = score_band(score)
        st = (r.get("status") or "").strip().lower()
        bucket = empty[band]
        bucket["n"] += 1
        if score is not None:
            bucket["scores"].append(score)
        if st in POSITIVE_OUTCOMES:
            bucket["positive"] += 1
        elif st in NEGATIVE_OUTCOMES:
            bucket["negative"] += 1
        elif st == "skipped":
            bucket["skipped"] += 1
        elif st in OPEN_STATUSES or st in ("applied", "to_apply", "in_progress"):
            bucket["open"] += 1
        else:
            bucket["other"] += 1

    def rate(num: int, den: int) -> str:
        if den <= 0:
            return "—"
        return f"{num * 100.0 / den:.0f}%"

    summary = []
    for b in bands:
        d = empty[b]
        scored_closed = d["positive"] + d["negative"]
        summary.append(
            {
                "band": b,
                "n": d["n"],
                "avg_score": (
                    round(sum(d["scores"]) / len(d["scores"]), 1) if d["scores"] else None
                ),
                "positive": d["positive"],
                "negative": d["negative"],
                "open": d["open"],
                "skipped": d["skipped"],
                "positive_rate_closed": rate(d["positive"], scored_closed),
                "hint": {
                    "high": "高匹配应优先准备面试；若 negative 偏多→检查内容是否空/AI 腔",
                    "mid": "中匹配重点看「改这 3 条」是否补上核心词",
                    "low": "低匹配宜 skipped 或练手；持续投低分岗浪费时间",
                    "unscored": "补跑 quality_gate / rank --write-fit 写入 match_score",
                }.get(b, ""),
            }
        )
    scored_n = sum(1 for r in rows if _parse_match_score(r) is not None)
    return {
        "total": len(rows),
        "scored": scored_n,
        "bands": summary,
        "signal_ready": scored_n >= 8,
    }


def cmd_match_outcome(args: argparse.Namespace) -> int:
    """Print match_score × outcome correlation (content quality flywheel)."""
    path = _csv_path(args.csv)
    rows = read_rows(path)
    data = compute_match_outcome(rows)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("还没有投递记录。先 /apply-zh 或 import-jobs。")
        return 0
    print(f"【匹配分 × 结果归因】共 {data['total']} 条 · 有分数 {data['scored']}  ← {path}")
    print("-" * 64)
    print(
        f"{'band':8}  {'n':>4}  {'avg':>6}  {'进面+':>5}  {'拒/无':>5}  "
        f"{'开放':>4}  {'不投':>4}  关闭进面率"
    )
    for b in data["bands"]:
        avg = "—" if b["avg_score"] is None else f"{b['avg_score']:.0f}"
        print(
            f"{b['band']:8}  {b['n']:4}  {avg:>6}  {b['positive']:5}  "
            f"{b['negative']:5}  {b['open']:4}  {b['skipped']:4}  "
            f"{b['positive_rate_closed']}"
        )
    print("-" * 64)
    for b in data["bands"]:
        if b["n"] and b.get("hint"):
            print(f"  · {b['band']}: {b['hint']}")
    print()
    if data["signal_ready"]:
        print("样本足够做粗判断：对照 high vs low 的进面率，决定要不要改简历策略。")
    else:
        need = max(0, 8 - data["scored"])
        print(
            f"信号未就绪（建议 ≥8 条带 match_score；还差约 {need}）。"
            " 写入：quality_gate 后 tracker add --match-score … "
            "或 rank --write-fit"
        )
    print("不是因果证明；只帮助发现「分高却无回复」或「总投低分岗」。")
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
    for job in jobs:
        # limit = max successful mutations (add/fill/force), not raw loop count
        if limit is not None and (
            stats["added"] + stats["filled"] + stats["forced"]
        ) >= limit:
            break
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
        # Help map boss / portal column names
        sample_keys: list[str] = []
        for raw in raw_list[:3]:
            if isinstance(raw, dict):
                sample_keys.extend(str(k) for k in raw.keys())
        if sample_keys:
            uniq = sorted(set(sample_keys))
            print(f"  columns seen: {', '.join(uniq[:24])}", file=sys.stderr)
        print(IMPORT_FIELD_HINT, file=sys.stderr)
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
    if stats["invalid"] and stats["added"] == 0 and stats["filled"] == 0 and not args.dry_run:
        print(IMPORT_FIELD_HINT, file=sys.stderr)
    elif stats["invalid"]:
        print(
            f"  note: {stats['invalid']} row(s) skipped (no company / bad skip fields).",
            file=sys.stderr,
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
    print("  next: python tools/tracker.py rank && python tools/tracker.py day-plan")
    print("    or: python tools/flow.py shortlist --jobs …   # import+rank+day-plan")
    print("        python tools/tracker.py list --open-only --salary-flag")
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
    match_score = getattr(args, "match_score", None) or ""
    match_coverage = getattr(args, "match_coverage", None) or ""
    match_verdict = getattr(args, "match_verdict", None) or ""

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
    if match_score:
        parts.append(f"--match-score {match_score}")
    if match_coverage:
        parts.append(f"--match-coverage {match_coverage}")
    if match_verdict:
        parts.append(f"--match-verdict {match_verdict}")
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
    if match_score:
        print(f"  匹配分: {match_score}  覆盖: {match_coverage or '—'}  {match_verdict or ''}")
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
    print("# 匹配分来自 quality_gate / match report，便于日后 match-outcome 归因")
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
    add_p.add_argument(
        "--expected-salary",
        default="",
        dest="expected_salary",
        help="your expected range for this row e.g. 25-40K",
    )
    add_p.add_argument(
        "--match-score",
        default="",
        dest="match_score",
        help="from quality_gate / match report e.g. 72",
    )
    add_p.add_argument(
        "--match-coverage",
        default="",
        dest="match_coverage",
        help="keyword coverage %% e.g. 55",
    )
    add_p.add_argument(
        "--match-verdict",
        default="",
        dest="match_verdict",
        help="strong_match|moderate_match|partial_match|weak_match",
    )
    add_p.add_argument("--date", default="")
    add_p.add_argument("--force", action="store_true", help="allow duplicate company+role")
    add_p.set_defaults(func=cmd_add)

    list_p = sub.add_parser("list", help="list applications")
    list_p.add_argument("--status", default="")
    list_p.add_argument("--open-only", action="store_true")
    list_p.add_argument(
        "--salary-flag",
        action="store_true",
        help="show ✅/⚠️/❌ for JD salary vs expected (row or --expected-salary / profile)",
    )
    list_p.add_argument(
        "--expected-salary",
        default="",
        dest="expected_salary",
        help="default expected range when row.expected_salary empty e.g. 25-40K",
    )
    list_p.set_defaults(func=cmd_list)

    up_p = sub.add_parser("update", help="update matching row(s)")
    up_p.add_argument("--company", required=True)
    up_p.add_argument("--role", default="")
    up_p.add_argument(
        "--match-channel",
        default=None,
        dest="match_channel",
        help="disambiguate row by channel (select filter; not the same as --channel write)",
    )
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
    up_p.add_argument(
        "--expected-salary",
        default=None,
        dest="expected_salary",
        help="your expected range e.g. 25-40K",
    )
    up_p.add_argument(
        "--match-score",
        default=None,
        dest="match_score",
        help="from quality_gate / match report",
    )
    up_p.add_argument(
        "--match-coverage",
        default=None,
        dest="match_coverage",
    )
    up_p.add_argument(
        "--match-verdict",
        default=None,
        dest="match_verdict",
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

    srv_p = sub.add_parser(
        "serve",
        help="local HTTP dashboard with one-click status update (127.0.0.1 only)",
    )
    srv_p.add_argument("--host", default="127.0.0.1")
    srv_p.add_argument("--port", type=int, default=8765)
    srv_p.set_defaults(func=cmd_serve)

    today_p = sub.add_parser("today", help="daily cockpit: interviews / follow-ups / closed")
    today_p.set_defaults(func=cmd_today)

    day_p = sub.add_parser(
        "day-plan",
        help="v0.11: today's focus — interviews / follow-ups / top to_apply",
    )
    day_p.add_argument("--limit", type=int, default=3, help="how many to_apply to show (default 3)")
    day_p.add_argument(
        "--track",
        default="",
        help="synonym track for scoring: internet|soe|foreign|civil|freshgrad",
    )
    day_p.add_argument(
        "--no-score",
        action="store_true",
        help="do not call match_resume (faster; order = CSV order)",
    )
    day_p.add_argument(
        "--expected-salary",
        default="",
        dest="expected_salary",
        help="for pay flags next to JD salary e.g. 25-40K",
    )
    day_p.set_defaults(func=cmd_day_plan)

    rank_p = sub.add_parser(
        "rank",
        help="v0.11: batch-score rows (default to_apply) via match_resume",
    )
    rank_p.add_argument("--status", default="to_apply", help="status filter (default to_apply)")
    rank_p.add_argument("--track", default="", help="synonym track for scoring")
    rank_p.add_argument("--limit", type=int, default=0, help="max rows to show (0=all)")
    rank_p.add_argument("--json", action="store_true")
    rank_p.add_argument("--out", default="", help="write ranked JSON")
    rank_p.add_argument(
        "--write-fit",
        action="store_true",
        help="write score into fit_rating + match_score/coverage/verdict (status-scoped)",
    )
    rank_p.set_defaults(func=cmd_rank)

    fun_p = sub.add_parser(
        "funnel",
        help="v0.13: application funnel snapshot (to_apply→…→hired)",
    )
    fun_p.add_argument("--json", action="store_true")
    fun_p.set_defaults(func=cmd_funnel)

    wr_p = sub.add_parser(
        "weekly-report",
        help="human weekly battle report (local narrative)",
    )
    wr_p.add_argument("--json", action="store_true")
    wr_p.set_defaults(func=cmd_weekly_report)

    skip_p = sub.add_parser(
        "skip-stats",
        help="Phase 1: distribution of skip_reason (why you chose not to apply)",
    )
    skip_p.set_defaults(func=cmd_skip_stats)

    mo_p = sub.add_parser(
        "match-outcome",
        help="correlate match_score with outcomes (quality flywheel)",
    )
    mo_p.add_argument("--json", action="store_true")
    mo_p.set_defaults(func=cmd_match_outcome)

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
    sug_p.add_argument("--match-score", default="", dest="match_score")
    sug_p.add_argument("--match-coverage", default="", dest="match_coverage")
    sug_p.add_argument("--match-verdict", default="", dest="match_verdict")
    sug_p.set_defaults(func=cmd_suggest_add)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
