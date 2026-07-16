#!/usr/bin/env python3
"""Check generated resume does not invent facts vs CLAUDE.zh.md profile.

Lightweight trust check (inspired by community reports of AI career agents
over-writing experience). Stdlib only — no model.

Usage:
  python tools/check_profile_resume.py \\
    --profile CLAUDE.zh.md \\
    --resume documents/zh/resume_某某.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Years like 2020-2023, 2020.01, 2020/01
YEAR_RE = re.compile(r"\b(20\d{2})\b")
# Simple CN/EN company-ish tokens in **bold** or after 公司
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE_RE = re.compile(r"1[3-9]\d{9}")
# Metrics that often get hallucinated if not in profile.
# Include decimals (99.95%, 1.5倍, 12.5ms) — old pattern missed them.
METRIC_RE = re.compile(
    r"(\d+(?:\.\d+)?\s*%|\d+(?:\.\d+)?\s*倍|\d+(?:\.\d+)?\s*万\+?|"
    r"\d+\s*人日|\d+(?:\.\d+)?\s*QPS|\d+(?:\.\d+)?\s*ms)",
    re.I,
)


def read(path: str | Path) -> str:
    p = Path(path)
    if not p.is_file():
        p = ROOT / path
    return p.read_text(encoding="utf-8", errors="replace")


def extract_years(text: str) -> set[str]:
    return set(YEAR_RE.findall(text))


def extract_metrics(text: str) -> set[str]:
    return {m.group(0).replace(" ", "") for m in METRIC_RE.finditer(text)}


def extract_contacts(text: str) -> dict[str, set[str]]:
    return {
        "emails": set(EMAIL_RE.findall(text)),
        "phones": set(PHONE_RE.findall(text)),
    }


def strip_placeholders(text: str) -> str:
    # Ignore template placeholders
    return re.sub(r"\[[^\]]+\]", " ", text)


def check(profile: str, resume: str) -> dict:
    profile = strip_placeholders(profile)
    resume = strip_placeholders(resume)
    p_years = extract_years(profile)
    r_years = extract_years(resume)
    # Years in resume not in profile (weak signal — education ranges etc.)
    year_only_resume = sorted(r_years - p_years)

    p_metrics = extract_metrics(profile)
    r_metrics = extract_metrics(resume)
    metric_only_resume = sorted(r_metrics - p_metrics)

    p_c = extract_contacts(profile)
    r_c = extract_contacts(resume)
    email_mismatch = sorted(r_c["emails"] - p_c["emails"]) if p_c["emails"] else []
    phone_mismatch = sorted(r_c["phones"] - p_c["phones"]) if p_c["phones"] else []

    # Skill-ish lines: 精通/熟悉 XXX in resume — check token appears in profile
    skill_claims: list[str] = []
    for m in re.finditer(r"(?:精通|熟悉|掌握|熟练使用)\s*([^\n，,。；;]{2,40})", resume):
        claim = m.group(1).strip()
        # if none of the main tokens appear in profile, flag
        tokens = re.split(r"[\s/、与和]+", claim)
        tokens = [t for t in tokens if len(t) >= 2][:4]
        if tokens and not any(t.lower() in profile.lower() or t in profile for t in tokens):
            skill_claims.append(claim[:40])

    warnings: list[dict] = []
    if metric_only_resume:
        # medium: real profiles rarely mirror every resume number → avoid HARD_FAIL false positive
        warnings.append(
            {
                "type": "metric_not_in_profile",
                "severity": "medium",
                "items": metric_only_resume[:12],
                "hint": "简历里的量化数字未在画像中出现——请人工确认是否真实，禁止为刷分编造。"
                "（不阻断投递；联系方式不一致仍会硬阻断。）",
            }
        )
    if skill_claims:
        warnings.append(
            {
                "type": "skill_claim_not_in_profile",
                "severity": "medium",
                "items": skill_claims[:10],
                "hint": "「精通/熟悉」表述在画像中未找到对应词，请核对是否夸大。",
            }
        )
    if email_mismatch:
        warnings.append(
            {
                "type": "email_mismatch",
                "severity": "high",
                "items": email_mismatch,
                "hint": "简历邮箱与画像不一致。",
            }
        )
    if phone_mismatch:
        warnings.append(
            {
                "type": "phone_mismatch",
                "severity": "high",
                "items": phone_mismatch,
                "hint": "简历手机号与画像不一致。",
            }
        )
    if year_only_resume and len(year_only_resume) >= 3:
        warnings.append(
            {
                "type": "years_only_in_resume",
                "severity": "low",
                "items": year_only_resume[:8],
                "hint": "多个年份只在简历出现——可能正常（格式差异），请扫一眼时间线。",
            }
        )

    high = sum(1 for w in warnings if w["severity"] == "high")
    return {
        "ok": high == 0,
        "warning_count": len(warnings),
        "high_count": high,
        "warnings": warnings,
        "summary": (
            "未发现高严重度不一致"
            if high == 0
            else f"发现 {high} 类高严重度不一致，请人工复核后再投递"
        ),
    }


def format_human(result: dict) -> str:
    lines = [
        "【画像 ↔ 简历 诚信检查】",
        result["summary"],
        "",
    ]
    if not result["warnings"]:
        lines.append("未发现明显「简历有、画像无」的量化/联系方式冲突。")
        lines.append("（启发式检查，不能替代你自己核对全文。）")
        return "\n".join(lines)
    for w in result["warnings"]:
        flag = {"high": "❌", "medium": "⚠️", "low": "·"}.get(w["severity"], "·")
        lines.append(f"{flag} [{w['severity']}] {w['type']}")
        lines.append(f"   {w['hint']}")
        lines.append(f"   样例: {'；'.join(w['items'][:6])}")
        lines.append("")
    lines.append("规则：不会的技能与没做过的业绩不要写进投递稿。")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Profile vs resume fact-consistency check")
    p.add_argument("--profile", default="CLAUDE.zh.md")
    p.add_argument("--resume", required=True)
    p.add_argument("--json", action="store_true")
    p.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 if any high-severity warning",
    )
    args = p.parse_args(argv)
    try:
        profile = read(args.profile)
        resume = read(args.resume)
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    result = check(profile, resume)
    if args.json:
        import json

        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_human(result))
    if args.strict and not result["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
