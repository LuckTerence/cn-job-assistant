#!/usr/bin/env python3
"""投前质量门禁：匹配报告 + 画像诚信 + ATS 文本层（可选 PDF）。

把 /apply-zh 里散落的三步收成一次 CLI，默认弱匹配/诚信失败会阻断，
可用 --force 覆盖软失败（硬失败仍阻断，除非 --force-hard）。

Exit codes:
  0  PASS（或 --force 后放行）
  1  SOFT_FAIL（匹配偏弱 / 覆盖不足 / ATS 警告）— 可用 --force
  2  HARD_FAIL（诚信高严重度）— 需 --force-hard
  3  用法错误 / 缺文件

Usage (repo root):
  python tools/quality_gate.py \\
    --resume documents/zh/resume_x.md \\
    --jd documents/zh/jd_x.md \\
    --cover documents/zh/da-zhaohu_x.md \\
    --profile CLAUDE.zh.md \\
    --pdf documents/zh/resume_x.pdf \\
    --out documents/zh/gate_x.json

  python tools/quality_gate.py --resume r.md --jd j.md --export-pdf
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import check_profile_resume as cpr  # noqa: E402
import export_resume_pdf as exp  # noqa: E402
import match_resume as mr  # noqa: E402

# Soft gate defaults (local heuristic, not offer prediction)
DEFAULT_MIN_SCORE = 40.0
DEFAULT_MIN_COVERAGE = 25.0
WEAK_VERDICTS = frozenset({"weak_match"})
SOFT_VERDICTS = frozenset({"weak_match", "partial_match"})


def _resolve(path: str | Path | None) -> Path | None:
    if not path:
        return None
    p = Path(path)
    if p.is_file():
        return p
    alt = ROOT / path
    if alt.is_file():
        return alt
    return p  # may not exist; caller checks


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _ats_text_checks(text: str, resume_md: str = "") -> list[dict]:
    """Structured ATS parseability signals from extracted PDF text (or md fallback)."""
    checks: list[dict] = []
    compact = re.sub(r"\s+", "", text or "")
    checks.append(
        {
            "id": "text_length",
            "ok": len(compact) >= 40,
            "detail": f"{len(compact)} non-space chars",
            "hint": "文本过短可能是图片 PDF，ATS 读不到",
        }
    )
    has_cid = "cid:" in (text or "").lower() or "\ufffd" in (text or "")
    checks.append(
        {
            "id": "no_cid_garbage",
            "ok": not has_cid,
            "detail": "cid/replacement found" if has_cid else "clean",
            "hint": "出现 (cid:*) 或 � 时换 Typst/字体重导",
        }
    )
    emails = set(cpr.EMAIL_RE.findall(text or ""))
    phones = set(cpr.PHONE_RE.findall(text or ""))
    md_emails = set(cpr.EMAIL_RE.findall(resume_md or ""))
    md_phones = set(cpr.PHONE_RE.findall(resume_md or ""))
    if md_emails:
        checks.append(
            {
                "id": "email_literal",
                "ok": bool(emails & md_emails) or bool(emails),
                "detail": f"pdf={sorted(emails)[:2]} md={sorted(md_emails)[:2]}",
                "hint": "邮箱须以明文出现在 PDF 文本层，不要只放图标",
            }
        )
    if md_phones:
        checks.append(
            {
                "id": "phone_literal",
                "ok": bool(phones & md_phones) or bool(phones),
                "detail": f"pdf={sorted(phones)[:2]} md={sorted(md_phones)[:2]}",
                "hint": "手机号须以明文出现在 PDF 文本层",
            }
        )
    # Single-column proxy: many form-feed + short lines can mean multi-col mess; soft only
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    avg_len = (sum(len(ln) for ln in lines) / len(lines)) if lines else 0
    checks.append(
        {
            "id": "readable_lines",
            "ok": avg_len >= 8 or not lines,
            "detail": f"avg_line_len={avg_len:.1f}, lines={len(lines)}",
            "hint": "行过碎可能排版异常；优先单栏模板",
        }
    )
    return checks


def verify_ats(
    pdf_path: Path | None,
    resume_md: str = "",
) -> dict:
    """Run ATS checks; skip gracefully if no PDF / no pdftotext."""
    if pdf_path is None or not pdf_path.is_file():
        return {
            "status": "skip",
            "ok": True,
            "message": "无 PDF，跳过文本层（可用 --export-pdf 或 --pdf）",
            "checks": _ats_text_checks(resume_md, resume_md),
            "source": "markdown_fallback",
        }
    ok_layer, msg = exp.verify_pdf_text_layer(pdf_path)
    text = ""
    bin_ = shutil.which("pdftotext")
    if bin_:
        try:
            proc = subprocess.run(
                [bin_, "-layout", str(pdf_path), "-"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            text = proc.stdout or ""
        except (OSError, subprocess.TimeoutExpired):
            text = ""
    if msg.startswith("skip:"):
        return {
            "status": "skip",
            "ok": True,
            "message": msg,
            "checks": _ats_text_checks(resume_md, resume_md),
            "source": "markdown_fallback",
        }
    checks = _ats_text_checks(text, resume_md)
    all_ok = ok_layer and all(c["ok"] for c in checks if c["id"] != "readable_lines")
    # readable_lines is soft
    hard_ids = {"text_length", "no_cid_garbage", "email_literal", "phone_literal"}
    hard_ok = ok_layer and all(
        c["ok"] for c in checks if c["id"] in hard_ids
    )
    return {
        "status": "pass" if hard_ok else "fail",
        "ok": hard_ok,
        "message": msg,
        "checks": checks,
        "source": "pdftotext",
        "layer_ok": ok_layer,
        "all_checks_ok": all_ok,
    }


def run_gate(
    *,
    resume_path: Path,
    jd_path: Path,
    cover_path: Path | None = None,
    profile_path: Path | None = None,
    pdf_path: Path | None = None,
    export_pdf: bool = False,
    template: str = "classic",
    min_score: float = DEFAULT_MIN_SCORE,
    min_coverage: float = DEFAULT_MIN_COVERAGE,
    track: str = "",
    expected_salary: str = "",
    no_salary: bool = False,
) -> dict:
    """Execute full gate; return structured result (does not print)."""
    resume_text = _read(resume_path)
    jd_text = _read(jd_path)
    cover_text = _read(cover_path) if cover_path and cover_path.is_file() else None

    # 1) Integrity
    profile_text = ""
    profile_used = ""
    if profile_path and profile_path.is_file():
        profile_text = _read(profile_path)
        profile_used = str(profile_path)
    elif (ROOT / "CLAUDE.zh.md").is_file():
        profile_text = _read(ROOT / "CLAUDE.zh.md")
        profile_used = str(ROOT / "CLAUDE.zh.md")
    if profile_text:
        integrity = cpr.check(profile_text, resume_text)
    else:
        integrity = {
            "ok": True,
            "warning_count": 0,
            "high_count": 0,
            "warnings": [],
            "summary": "无画像文件，跳过诚信检查（建议 CLAUDE.zh.md）",
        }

    # 2) Match report
    syn = mr.load_synonym_map(track=track or None)
    report = mr.quality_report(
        resume_text,
        jd_text,
        cover_text,
        synonym_map=syn,
        expected_salary=expected_salary or None,
        profile_path=profile_used or None,
        salary_compare=not no_salary,
    )
    summary = report.get("summary") or {}
    score = float(summary.get("combined_score") or 0)
    coverage = float(summary.get("keyword_coverage_combined") or 0)
    verdict = str(summary.get("verdict") or "")
    checklist = report.get("action_checklist") or []
    if not checklist and report.get("brief_zh"):
        checklist = (report["brief_zh"] or {}).get("action_checklist") or []

    # 3) PDF / ATS
    pdf_out = pdf_path
    export_note = ""
    if export_pdf:
        out_pdf = pdf_path if pdf_path else resume_path.with_suffix(".pdf")
        try:
            pdf_out, used = exp.export_pdf(
                resume_path,
                out_pdf,
                backend="auto",
                template=template or "classic",
            )
            export_note = f"exported via {used} → {pdf_out}"
        except Exception as e:  # noqa: BLE001 — surface to gate report
            export_note = f"export failed: {e}"
            pdf_out = pdf_path if pdf_path and pdf_path.is_file() else None

    ats = verify_ats(pdf_out if pdf_out and Path(pdf_out).is_file() else None, resume_text)

    # 4) Decide
    hard_reasons: list[str] = []
    soft_reasons: list[str] = []
    if not integrity.get("ok", True):
        hard_reasons.append(
            f"诚信检查高严重度 ×{integrity.get('high_count', 0)}：{integrity.get('summary', '')}"
        )
    if verdict in WEAK_VERDICTS or score < min_score:
        soft_reasons.append(
            f"匹配偏弱：score={score}/100 verdict={verdict}（门槛 score≥{min_score}）"
        )
    if coverage < min_coverage:
        soft_reasons.append(
            f"关键词覆盖偏低：{coverage}% < {min_coverage}%"
        )
    if verdict == "partial_match" and score < 55:
        soft_reasons.append("部分匹配且分数不高，建议先按「改这 3 条」补真实经历")
    if ats.get("status") == "fail":
        soft_reasons.append(f"ATS 文本层：{ats.get('message', 'fail')}")

    if hard_reasons:
        gate_status = "HARD_FAIL"
    elif soft_reasons:
        gate_status = "SOFT_FAIL"
    else:
        gate_status = "PASS"

    deliverables = {
        "resume_md": str(resume_path),
        "jd": str(jd_path),
        "cover": str(cover_path) if cover_path else "",
        "pdf": str(pdf_out) if pdf_out else "",
        "paste_ready": str(resume_path),  # 国内平台粘贴优先 md
        "profile": profile_used,
    }

    return {
        "gate_status": gate_status,
        "ok": gate_status == "PASS",
        "hard_reasons": hard_reasons,
        "soft_reasons": soft_reasons,
        "match": {
            "score": score,
            "coverage": coverage,
            "verdict": verdict,
            "still_missing": report.get("still_missing") or [],
            "miss_core": (report.get("brief_zh") or {}).get("miss_core") or [],
            "miss_nice": (report.get("brief_zh") or {}).get("miss_nice") or [],
            "salary": report.get("salary"),
        },
        "integrity": integrity,
        "ats": ats,
        "action_checklist": checklist[:3],
        "edit_top3": (report.get("brief_zh") or {}).get("edit_top3") or [],
        "brief_zh": report.get("brief_zh"),
        "match_report": report,
        "deliverables": deliverables,
        "export_note": export_note,
        "thresholds": {
            "min_score": min_score,
            "min_coverage": min_coverage,
        },
        "compliance": "禁止为过门禁虚构技能或业绩；只会的才写进「改这 3 条」。",
    }


def format_gate_human(result: dict) -> str:
    st = result.get("gate_status", "?")
    icon = {"PASS": "✅", "SOFT_FAIL": "⚠️", "HARD_FAIL": "❌"}.get(st, "·")
    m = result.get("match") or {}
    lines = [
        f"【投前质量门禁】{icon} {st}",
        f"匹配 {m.get('score', '—')}/100 · 覆盖 {m.get('coverage', '—')}% · "
        f"{mr.VERDICT_ZH.get(str(m.get('verdict') or ''), m.get('verdict') or '—')}",
        "",
    ]
    if result.get("hard_reasons"):
        lines.append("硬阻断（诚信）：")
        for r in result["hard_reasons"]:
            lines.append(f"  ❌ {r}")
        lines.append("")
    if result.get("soft_reasons"):
        lines.append("软阻断（建议改完再投；可用 --force 放行）：")
        for r in result["soft_reasons"]:
            lines.append(f"  ⚠️ {r}")
        lines.append("")
    if st == "PASS":
        lines.append("门禁通过：材料可投（仍建议人工扫一眼真实性和公司名）。")
        lines.append("")

    # Integrity short
    integ = result.get("integrity") or {}
    lines.append(f"诚信：{integ.get('summary', '—')}")
    for w in (integ.get("warnings") or [])[:4]:
        flag = {"high": "❌", "medium": "⚠️", "low": "·"}.get(w.get("severity"), "·")
        lines.append(f"  {flag} {w.get('type')}: {w.get('hint', '')}")
    lines.append("")

    # ATS
    ats = result.get("ats") or {}
    lines.append(
        f"ATS：{ats.get('status', '—')} — {ats.get('message', '')}"
    )
    for c in (ats.get("checks") or [])[:6]:
        mark = "✅" if c.get("ok") else "❌"
        lines.append(f"  {mark} {c.get('id')}: {c.get('detail')}")
    lines.append("")

    # Action checklist — product core
    lines.append("【改这 3 条】（只写真实经历；不会的标缺口）")
    checklist = result.get("action_checklist") or []
    if checklist:
        for i, item in enumerate(checklist[:3], 1):
            if isinstance(item, dict):
                term = item.get("term") or item.get("title") or ""
                action = item.get("action") or item.get("hint") or ""
                kind = item.get("kind") or ""
                prefix = f"{term}" + (f"（{kind}）" if kind else "")
                lines.append(f"  {i}. {prefix}")
                if action:
                    lines.append(f"     → {action}")
            else:
                lines.append(f"  {i}. {item}")
    else:
        for i, tip in enumerate((result.get("edit_top3") or [])[:3], 1):
            lines.append(f"  {i}. {tip}")
    lines.append("")

    sal = m.get("salary") or (result.get("match") or {}).get("salary")
    if isinstance(sal, dict) and sal.get("summary"):
        lines.append(
            f"薪资：{sal.get('signal', '·')} {sal.get('label', '')} — {sal.get('summary')}"
        )
        lines.append("")

    d = result.get("deliverables") or {}
    lines.append("交付物：")
    lines.append(f"  · 粘贴稿（md）: {d.get('paste_ready') or d.get('resume_md') or '—'}")
    lines.append(f"  · 上传稿（pdf）: {d.get('pdf') or '（未提供/未导出）'}")
    if d.get("cover"):
        lines.append(f"  · 话术: {d.get('cover')}")
    if result.get("export_note"):
        lines.append(f"  · 导出: {result['export_note']}")
    lines.append("")
    lines.append(result.get("compliance") or "")
    lines.append(
        "分数是本地关键词对齐，不是录用预测。过门禁 ≠ 必进面。"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="quality_gate",
        description="投前质量门禁：匹配 + 诚信 + ATS（默认阻断弱匹配/诚信失败）",
    )
    p.add_argument("--resume", required=True, help="简历 md 路径")
    p.add_argument("--jd", required=True, help="岗位描述 md 路径")
    p.add_argument("--cover", default="", help="打招呼/求职信 md（可选）")
    p.add_argument("--profile", default="", help="画像 CLAUDE.zh.md（可选）")
    p.add_argument("--pdf", default="", help="已导出的 PDF 路径（可选）")
    p.add_argument(
        "--export-pdf",
        action="store_true",
        help="门禁内导出 PDF（默认 classic；见 --template）",
    )
    p.add_argument(
        "--template",
        default="classic",
        choices=("classic", "compact"),
        help="导出 PDF 时的 Typst 模板",
    )
    p.add_argument("--track", default="", help="同义词赛道 internet|soe|…")
    p.add_argument("--expected-salary", default="", dest="expected_salary")
    p.add_argument("--no-salary", action="store_true")
    p.add_argument(
        "--min-score",
        type=float,
        default=DEFAULT_MIN_SCORE,
        help=f"软门槛综合分（默认 {DEFAULT_MIN_SCORE}）",
    )
    p.add_argument(
        "--min-coverage",
        type=float,
        default=DEFAULT_MIN_COVERAGE,
        help=f"软门槛关键词覆盖%%（默认 {DEFAULT_MIN_COVERAGE}）",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="放行 SOFT_FAIL（仍阻断 HARD_FAIL）",
    )
    p.add_argument(
        "--force-hard",
        action="store_true",
        help="连诚信 HARD_FAIL 也放行（高风险，仅调试）",
    )
    p.add_argument("--out", default="", help="写入 gate JSON")
    p.add_argument("--brief-out", default="", help="写入人话摘要 txt")
    p.add_argument("--json", action="store_true", help="stdout 只打 JSON")
    p.add_argument(
        "--zh-only",
        action="store_true",
        help="stdout 只打人话门禁摘要",
    )
    args = p.parse_args(argv)

    resume = _resolve(args.resume)
    jd = _resolve(args.jd)
    if resume is None or not resume.is_file():
        print(f"error: resume not found: {args.resume}", file=sys.stderr)
        return 3
    if jd is None or not jd.is_file():
        print(f"error: jd not found: {args.jd}", file=sys.stderr)
        return 3
    cover = _resolve(args.cover) if args.cover else None
    if args.cover and (cover is None or not cover.is_file()):
        print(f"error: cover not found: {args.cover}", file=sys.stderr)
        return 3
    profile = _resolve(args.profile) if args.profile else None
    pdf = _resolve(args.pdf) if args.pdf else None
    # If --pdf given but missing and not exporting, warn later inside gate

    result = run_gate(
        resume_path=resume,
        jd_path=jd,
        cover_path=cover if cover and cover.is_file() else None,
        profile_path=profile if profile and profile.is_file() else None,
        pdf_path=pdf if pdf and pdf.is_file() else (Path(args.pdf) if args.pdf else None),
        export_pdf=bool(args.export_pdf),
        template=args.template,
        min_score=float(args.min_score),
        min_coverage=float(args.min_coverage),
        track=args.track or "",
        expected_salary=args.expected_salary or "",
        no_salary=bool(args.no_salary),
    )

    # Persist (strip heavy nested report if huge? keep full for flywheel)
    out_payload = {k: v for k, v in result.items() if k != "match_report"}
    out_payload["match_summary"] = (result.get("match_report") or {}).get("summary")
    # Keep still_missing / checklist; drop full TF-IDF dump to keep file small
    if args.out:
        outp = Path(args.out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(
            json.dumps(out_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote gate → {outp}", file=sys.stderr)
    if args.brief_out:
        bout = Path(args.brief_out)
        bout.parent.mkdir(parents=True, exist_ok=True)
        bout.write_text(format_gate_human(result) + "\n", encoding="utf-8")
        print(f"Wrote brief → {bout}", file=sys.stderr)

    if args.json:
        print(json.dumps(out_payload, ensure_ascii=False, indent=2))
    else:
        print(format_gate_human(result))
        if not args.zh_only and result.get("brief_zh"):
            print()
            print("--- 匹配一页摘要 ---")
            print(mr.format_zh_brief(result["brief_zh"]))

    st = result.get("gate_status")
    if st == "PASS":
        return 0
    if st == "HARD_FAIL":
        if args.force_hard:
            print(
                "\n⚠️ --force-hard：诚信硬失败已强制放行，请自负风险。",
                file=sys.stderr,
            )
            return 0
        print(
            "\n门禁 HARD_FAIL：先修诚信问题，或明确风险后使用 --force-hard。",
            file=sys.stderr,
        )
        return 2
    # SOFT_FAIL
    if args.force or args.force_hard:
        print(
            "\n⚠️ --force：软失败已放行。建议仍按「改这 3 条」补完再投。",
            file=sys.stderr,
        )
        return 0
    print(
        "\n门禁 SOFT_FAIL：按「改这 3 条」改简历后重跑；确认仍要投可加 --force。",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
