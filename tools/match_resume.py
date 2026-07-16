#!/usr/bin/env python3
"""Lightweight local 简历↔岗位描述 matcher (stdlib only).

Design (inspired by Resume Matcher / classic IR, not a reimplementation of
sentence-transformers):

  1. Tokenize bilingual text (English tech tokens + CJK bigrams/terms)
  2. Build TF–IDF vectors for résumé and 岗位描述
  3. Cosine similarity → overall score 0–100
  4. Keyword hit / miss / extra classification (weighted by posting text)
  5. Optional generation-quality report (résumé + 打招呼/求职信 vs 岗位描述)

No embedding model download, no Streamlit, no network.

Usage (repo root):
  python tools/match_resume.py score --resume path.md --jd path_or_text
  python tools/match_resume.py keywords --jd path
  python tools/match_resume.py report --resume path --jd path [--cover path]
  python tools/match_resume.py salary --jd path --expected '25-40K'
  python tools/match_resume.py score --resume path --jd path --json

Synonyms: config/synonyms.default.json (+ optional config/synonyms.json).
Salary: local parse only — 期望 from --expected / CLAUDE.zh.md; JD from text. No crawl.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SYNONYMS = ROOT / "config" / "synonyms.default.json"
USER_SYNONYMS = ROOT / "config" / "synonyms.json"
DEFAULT_PROFILE = ROOT / "CLAUDE.zh.md"

# ---------------------------------------------------------------------------
# Lexicon: high-signal skills / role terms (EN + 中文). Not exhaustive —
# unknown tokens still enter TF–IDF via general tokenization.
# ---------------------------------------------------------------------------

SKILL_TERMS: frozenset[str] = frozenset(
    s.lower()
    for s in """
    python java golang go rust c++ c# javascript typescript nodejs node.js
    react vue angular spring springboot django flask fastapi kafka redis
    mysql postgresql mongodb elasticsearch docker kubernetes k8s kubernetes
    aws azure gcp linux git ci cd devops sre terraform ansible
    machine learning deep learning llm pytorch tensorflow spark hadoop
    microservices rest api graphql grpc rpc
    算法 数据结构 分布式 微服务 高并发 高可用 中间件 消息队列
    后端 前端 全栈 客户端 安卓 鸿蒙 测试 运维 产品 运营 数据分析
    机器学习 深度学习 大模型 推荐系统 搜索 广告 量化
    熟悉 精通 掌握 负责 主导 落地 优化 重构 架构 设计
    bachelor master phd 本科 硕士 博士 应届 社招 实习
    英语 六级 四级 托福 雅思 政治面貌 党员
    """.split()
)

# Phrases kept as single tokens when present (case-insensitive for Latin).
PHRASE_TERMS: tuple[str, ...] = (
    "machine learning",
    "deep learning",
    "spring boot",
    "node.js",
    "c++",
    "c#",
    "ci/cd",
    "rest api",
    "大模型",
    "推荐系统",
    "消息队列",
    "高并发",
    "高可用",
    "微服务",
    "数据结构",
)

STOPWORDS: frozenset[str] = frozenset(
    """
    a an the and or of to for in on with by from as is are was were be been
    this that these those it its we you they their our your i me my at
    的 了 和 与 或 及 等 在 为 对 把 被 是 有 也 就 都 而 其 该 各
    我们 你们 他们 以及 通过 进行 相关 工作 岗位 职位 公司 团队 业务
    要求 优先 加分 职责 描述 以上 以下 具备 具有 能够 可以 需要 希望
    熟悉 精通 掌握 了解 任职 资格 以上学历 年 以上 经验 者 优先
    负责 参与 推动 保障 编写 优化 良好 基础 流畅 读写 本科 学历
    """.split()
)

# Verbs / glue never promoted to "岗位关键词" even if frequent
KEYWORD_BLOCKLIST: frozenset[str] = frozenset(
    """
    熟悉 精通 掌握 了解 具备 具有 优先 加分 要求 职责 描述 任职 资格
    负责 参与 推动 保障 编写 进行 相关 工作 岗位 职位 公司 团队
    经验 学历 以上 以下 能够 可以 需要 希望 良好 基础 者 等 及
    设计 开发 落地 优化 重构 能力 系统 服务 业务 代码 接口 性能
    year years experience preferred plus strong good etc
    demo sample placeholder TODO
    """.split()
)

CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
LATIN_TECH_RE = re.compile(
    r"[a-zA-Z][a-zA-Z0-9+#./_-]{0,40}(?:\+\+|#)?"
)
WS_RE = re.compile(r"\s+")


def read_text(source: str) -> str:
    """Read file path if it exists; otherwise treat as literal 岗位描述 text."""
    path = Path(source)
    if path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")
    # Also try relative to repo root
    alt = ROOT / source
    if alt.is_file():
        return alt.read_text(encoding="utf-8", errors="replace")
    return source


# ---------------------------------------------------------------------------
# Synonyms (reduce false miss: 高并发 ↔ 大流量)
# ---------------------------------------------------------------------------


def _norm_syn_term(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip().lower())


def load_synonym_map(extra_paths: list[Path] | None = None) -> dict[str, set[str]]:
    """Build term → full synonym cluster (including self).

    Loads default + optional user override + any --synonyms paths.
    """
    paths: list[Path] = []
    if DEFAULT_SYNONYMS.is_file():
        paths.append(DEFAULT_SYNONYMS)
    if USER_SYNONYMS.is_file():
        paths.append(USER_SYNONYMS)
    if extra_paths:
        paths.extend(extra_paths)

    groups: list[list[str]] = []
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        raw_groups = data.get("groups") if isinstance(data, dict) else data
        if not isinstance(raw_groups, list):
            continue
        for g in raw_groups:
            if isinstance(g, list) and len(g) >= 2:
                terms = [_norm_syn_term(str(x)) for x in g if str(x).strip()]
                terms = [t for t in terms if t]
                if len(terms) >= 2:
                    groups.append(terms)

    syn: dict[str, set[str]] = {}
    for terms in groups:
        cluster = set(terms)
        for t in cluster:
            syn.setdefault(t, set()).update(cluster)
    return syn


def expand_token_set(tokens: set[str], synonym_map: dict[str, set[str]] | None) -> set[str]:
    """Expand tokens with synonym clusters for hit/miss classification."""
    if not synonym_map:
        return set(tokens)
    out: set[str] = set()
    for t in tokens:
        tl = t.lower() if not CJK_RE.fullmatch(t) else t
        # try both original and lower for latin
        out.add(t)
        out.add(tl)
        cluster = synonym_map.get(tl) or synonym_map.get(t) or synonym_map.get(_norm_syn_term(t))
        if cluster:
            out.update(cluster)
    return out


def expand_resume_coverage(
    resume_text: str,
    tokens: set[str],
    synonym_map: dict[str, set[str]] | None,
) -> set[str]:
    """Expand résumé tokens + surface forms found in raw text (synonyms may not tokenize).

    Example: resume says「大流量」which is not in the skill lexicon, but is a synonym
    of「高并发」— substring scan still activates the cluster.
    """
    expanded = expand_token_set(tokens, synonym_map)
    if not synonym_map or not resume_text:
        return expanded
    lower = resume_text.lower()
    # Longest-first so multi-word latin phrases match before fragments
    for term in sorted(synonym_map.keys(), key=len, reverse=True):
        if not term:
            continue
        if term in lower or term in resume_text:
            expanded.update(synonym_map[term])
    return expanded


def term_covered(term: str, expanded_resume: set[str], synonym_map: dict[str, set[str]] | None) -> bool:
    """True if JD term (or any synonym) appears in expanded résumé token set."""
    tl = _norm_syn_term(term)
    if term in expanded_resume or tl in expanded_resume:
        return True
    if not synonym_map:
        return False
    cluster = synonym_map.get(tl) or synonym_map.get(term) or set()
    return bool(cluster & expanded_resume)


# ---------------------------------------------------------------------------
# Salary: expected vs JD range (local parse only)
# ---------------------------------------------------------------------------

# Capture ranges like 25-40K, 20k~35k, 15-25k·14薪, 30-50万/年, 30000-50000
SALARY_RANGE_RE = re.compile(
    r"(?P<a>\d+(?:\.\d+)?)\s*[-~～—至到]+\s*(?P<b>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>k|K|千|万|/月|元/月|元|w|W)?\s*(?P<period>/年|年薪|每年|k/月|K/月)?",
    re.I,
)
SALARY_SINGLE_RE = re.compile(
    r"(?P<a>\d+(?:\.\d+)?)\s*(?P<unit>k|K|千|万)\s*(?:\+|以上|起)?",
    re.I,
)
FACE_RE = re.compile(r"面议|薪资面议|待遇面议", re.I)
PROFILE_EXPECT_RE = re.compile(
    r"薪资期望[：:\s]*\*?\*?([^\n*]+)",
    re.I,
)


@dataclass
class SalaryRange:
    """Monthly salary in 元 (CNY). None bounds mean open-ended."""

    low: float | None
    high: float | None
    raw: str
    unit_hint: str = ""  # monthly | yearly | unknown


def _to_monthly_yuan(value: float, unit: str, period: str) -> tuple[float, str]:
    """Normalize a numeric salary token to monthly 元."""
    u = (unit or "").lower()
    p = (period or "").lower()
    yearly = "年" in p or p in ("/年", "年薪", "每年")
    if u in ("万", "w"):
        yuan = value * 10000.0
        if yearly or (not u and yearly):
            return yuan / 12.0, "yearly"
        # bare 万 in CN job posts is usually monthly package mid: treat as monthly 万
        return yuan, "monthly"
    if u in ("k",) or u == "千":
        yuan = value * 1000.0
        if yearly:
            return yuan / 12.0, "yearly"
        return yuan, "monthly"
    if u in ("元/月", "/月"):
        return value, "monthly"
    if u == "元":
        if yearly or value >= 100000:
            return (value / 12.0 if value >= 80000 else value), "yearly" if value >= 80000 else "monthly"
        return value, "monthly"
    # no unit: if both numbers < 200 assume K/month; if > 1000 assume 元
    if value <= 200:
        return value * 1000.0, "monthly"
    if value >= 1000:
        return value, "monthly"
    return value * 1000.0, "monthly"


def parse_salary_text(text: str) -> SalaryRange | None:
    """Parse a salary snippet into monthly 元 range."""
    s = (text or "").strip()
    if not s or s in ("[范围，可选]", "可选", "-", "n/a", "N/A"):
        return None
    if FACE_RE.search(s):
        return SalaryRange(low=None, high=None, raw=s, unit_hint="face")

    m = SALARY_RANGE_RE.search(s)
    if m:
        a = float(m.group("a"))
        b = float(m.group("b"))
        unit = m.group("unit") or ""
        period = m.group("period") or ""
        # 万/年 often written as 30-50万/年
        if "万" in s and ("年" in s or "/年" in s):
            low, high = a * 10000 / 12.0, b * 10000 / 12.0
            if low > high:
                low, high = high, low
            return SalaryRange(low=low, high=high, raw=m.group(0), unit_hint="yearly")
        # if unit only appears once in the snippet, apply to both ends
        if not unit and re.search(r"[kKwW万千]", s):
            um = re.search(r"[kKwW万千]", s)
            unit = um.group(0) if um else unit
        la, _ = _to_monthly_yuan(a, unit, period)
        lb, _ = _to_monthly_yuan(b, unit, period)
        low, high = min(la, lb), max(la, lb)
        return SalaryRange(low=low, high=high, raw=m.group(0).strip(), unit_hint="monthly")

    m2 = SALARY_SINGLE_RE.search(s)
    if m2:
        a = float(m2.group("a"))
        unit = m2.group("unit") or "k"
        val, hint = _to_monthly_yuan(a, unit, "年" if "年" in s else "")
        # "25K+" → low=25k, high open
        if re.search(r"\+|以上|起", s):
            return SalaryRange(low=val, high=None, raw=m2.group(0), unit_hint=hint)
        return SalaryRange(low=val * 0.9, high=val * 1.1, raw=m2.group(0), unit_hint=hint)
    return None


def extract_jd_salary(jd_text: str) -> SalaryRange | None:
    """Best-effort salary extraction from JD body (no network)."""
    if not jd_text:
        return None
    if FACE_RE.search(jd_text) and not SALARY_RANGE_RE.search(jd_text):
        # only face, no numbers
        for line in jd_text.splitlines():
            if FACE_RE.search(line):
                return SalaryRange(low=None, high=None, raw=line.strip()[:40], unit_hint="face")
    # Prefer lines that mention 薪/月/k
    candidates: list[str] = []
    for line in jd_text.splitlines():
        if re.search(r"薪|月薪|年薪|package|k\b|K\b|万", line):
            candidates.append(line)
    blob = "\n".join(candidates) if candidates else jd_text[:800]
    # Try each match, pick first sensible range
    for m in SALARY_RANGE_RE.finditer(blob):
        parsed = parse_salary_text(m.group(0))
        if parsed and (parsed.low or parsed.high):
            return parsed
    return parse_salary_text(blob[:200])


def extract_expected_from_profile(profile_text: str) -> str | None:
    """Pull 薪资期望 line from CLAUDE.zh.md-style profile."""
    if not profile_text:
        return None
    m = PROFILE_EXPECT_RE.search(profile_text)
    if not m:
        return None
    val = m.group(1).strip().strip("*").strip()
    if not val or val.startswith("[") or "可选" in val:
        return None
    return val


def format_monthly_k(yuan: float | None) -> str:
    if yuan is None:
        return "?"
    k = yuan / 1000.0
    if abs(k - round(k)) < 0.05:
        return f"{int(round(k))}K"
    return f"{k:.1f}K"


def compare_salary(
    expected: SalaryRange | None,
    offered: SalaryRange | None,
) -> dict:
    """Compare expected vs JD salary. Pure local decision signal."""
    if offered and offered.unit_hint == "face":
        return {
            "verdict": "face",
            "signal": "⚠️",
            "label": "面议",
            "summary": "JD 写面议，无法自动比价；面试时再问。",
            "expected_raw": expected.raw if expected else "",
            "offered_raw": offered.raw if offered else "面议",
            "expected_monthly": None,
            "offered_monthly": None,
        }
    if not expected and not offered:
        return {
            "verdict": "unknown",
            "signal": "·",
            "label": "未填写",
            "summary": "未提供期望薪资，JD 也未解析到区间；可在 CLAUDE.zh.md 填「薪资期望」或 --expected。",
            "expected_raw": "",
            "offered_raw": "",
            "expected_monthly": None,
            "offered_monthly": None,
        }
    if not expected:
        return {
            "verdict": "jd_only",
            "signal": "·",
            "label": "仅 JD",
            "summary": (
                f"JD 约 {format_monthly_k(offered.low)}–{format_monthly_k(offered.high)}/月"
                f"（原文 {offered.raw}）；画像未填期望，无法对比。"
            ),
            "expected_raw": "",
            "offered_raw": offered.raw if offered else "",
            "expected_monthly": None,
            "offered_monthly": {
                "low": offered.low if offered else None,
                "high": offered.high if offered else None,
            },
        }
    if not offered:
        return {
            "verdict": "expect_only",
            "signal": "·",
            "label": "仅期望",
            "summary": (
                f"期望 {format_monthly_k(expected.low)}–{format_monthly_k(expected.high)}/月"
                f"；JD 未解析到薪资数字。"
            ),
            "expected_raw": expected.raw,
            "offered_raw": "",
            "expected_monthly": {"low": expected.low, "high": expected.high},
            "offered_monthly": None,
        }

    e_lo = expected.low if expected.low is not None else 0.0
    e_hi = expected.high if expected.high is not None else e_lo * 1.2 if e_lo else 0.0
    o_lo = offered.low if offered.low is not None else 0.0
    o_hi = offered.high if offered.high is not None else o_lo

    # JD entirely below expected floor
    if o_hi and e_lo and o_hi < e_lo * 0.95:
        return {
            "verdict": "low",
            "signal": "❌",
            "label": "偏低",
            "summary": (
                f"JD {format_monthly_k(o_lo)}–{format_monthly_k(o_hi)}/月 "
                f"低于期望 {format_monthly_k(e_lo)}–{format_monthly_k(e_hi)}/月。"
            ),
            "expected_raw": expected.raw,
            "offered_raw": offered.raw,
            "expected_monthly": {"low": expected.low, "high": expected.high},
            "offered_monthly": {"low": offered.low, "high": offered.high},
        }
    # Overlap or JD at/above expectation
    overlap = o_hi >= e_lo and o_lo <= e_hi
    if overlap or (o_lo and e_hi and o_lo >= e_lo * 0.9):
        if o_lo and e_lo and o_lo >= e_hi * 0.95:
            label, verdict, signal = "高于或贴齐期望", "high_ok", "✅"
        else:
            label, verdict, signal = "区间有交集", "overlap", "✅"
        return {
            "verdict": verdict,
            "signal": signal,
            "label": label,
            "summary": (
                f"期望 {format_monthly_k(e_lo)}–{format_monthly_k(e_hi)}/月 · "
                f"JD {format_monthly_k(o_lo)}–{format_monthly_k(o_hi)}/月 → {label}。"
            ),
            "expected_raw": expected.raw,
            "offered_raw": offered.raw,
            "expected_monthly": {"low": expected.low, "high": expected.high},
            "offered_monthly": {"low": offered.low, "high": offered.high},
        }
    # JD floor below expectation but ceiling may reach
    if o_hi and e_lo and o_hi >= e_lo and o_lo < e_lo:
        return {
            "verdict": "partial",
            "signal": "⚠️",
            "label": "可能触底",
            "summary": (
                f"JD 下限 {format_monthly_k(o_lo)} 低于期望 {format_monthly_k(e_lo)}，"
                f"上限 {format_monthly_k(o_hi)} 或可谈；建议问清档位。"
            ),
            "expected_raw": expected.raw,
            "offered_raw": offered.raw,
            "expected_monthly": {"low": expected.low, "high": expected.high},
            "offered_monthly": {"low": offered.low, "high": offered.high},
        }
    return {
        "verdict": "unclear",
        "signal": "⚠️",
        "label": "需人工判断",
        "summary": (
            f"期望 {format_monthly_k(e_lo)}–{format_monthly_k(e_hi)} · "
            f"JD {format_monthly_k(o_lo)}–{format_monthly_k(o_hi)}，自动规则无法定论。"
        ),
        "expected_raw": expected.raw,
        "offered_raw": offered.raw,
        "expected_monthly": {"low": expected.low, "high": expected.high},
        "offered_monthly": {"low": offered.low, "high": offered.high},
    }


def resolve_salary_compare(
    jd_text: str,
    *,
    expected_raw: str | None = None,
    profile_path: str | Path | None = None,
) -> dict:
    """Build salary compare dict from JD + expected string or profile file."""
    offered = extract_jd_salary(jd_text)
    exp_str = (expected_raw or "").strip() or None
    if not exp_str and profile_path:
        p = Path(profile_path)
        if not p.is_file():
            p = ROOT / str(profile_path)
        if p.is_file():
            exp_str = extract_expected_from_profile(
                p.read_text(encoding="utf-8", errors="replace")
            )
    if not exp_str and DEFAULT_PROFILE.is_file():
        exp_str = extract_expected_from_profile(
            DEFAULT_PROFILE.read_text(encoding="utf-8", errors="replace")
        )
    expected = parse_salary_text(exp_str) if exp_str else None
    result = compare_salary(expected, offered)
    result["expected_input"] = exp_str or ""
    return result


def normalize(text: str) -> str:
    text = text.replace("\u3000", " ")
    text = WS_RE.sub(" ", text)
    return text.strip()


def _cjk_tokens(run: str) -> list[str]:
    """Conservative CJK tokens: whole short runs + lexicon hits only.

    Sliding bigrams over long sentences create noise (e.g. 发系/验者优) and
    drown real skills in TF–IDF. We only emit:
      - the full run if 2–6 chars
      - 2/3/4-char windows that are in SKILL_TERMS or PHRASE_TERMS
    """
    out: list[str] = []
    n = len(run)
    if 2 <= n <= 6:
        out.append(run)
    skill_phrases = SKILL_TERMS | {p for p in PHRASE_TERMS if CJK_RE.search(p)}
    for i in range(n):
        for width in (2, 3, 4):
            if i + width <= n:
                piece = run[i : i + width]
                if piece in skill_phrases:
                    out.append(piece)
    return out


def tokenize(text: str) -> list[str]:
    """Bilingual tokenizer → list of lowercase tokens."""
    text = normalize(text)
    if not text:
        return []
    lower = text.lower()
    tokens: list[str] = []

    # Multi-word phrases first (mark spans to avoid double-count noise)
    marked = lower
    for phrase in sorted(PHRASE_TERMS, key=len, reverse=True):
        p = phrase.lower()
        if p in marked:
            tokens.append(p)
            marked = marked.replace(p, " ")

    # Latin / tech tokens
    for m in LATIN_TECH_RE.finditer(marked):
        tok = m.group(0).lower().strip(".-_/")
        if len(tok) < 2 or tok in STOPWORDS:
            continue
        tokens.append(tok)

    # CJK runs on original (case irrelevant)
    for m in CJK_RE.finditer(text):
        run = m.group(0)
        for t in _cjk_tokens(run):
            if t in STOPWORDS or len(t) < 2:
                continue
            tokens.append(t)

    return tokens


def term_frequency(tokens: list[str]) -> Counter[str]:
    return Counter(tokens)


def build_idf(docs: list[Counter[str]]) -> dict[str, float]:
    n = len(docs)
    df: Counter[str] = Counter()
    for doc in docs:
        for term in doc:
            df[term] += 1
    # smooth idf
    return {t: math.log((1 + n) / (1 + df[t])) + 1.0 for t in df}


def tfidf_vector(tf: Counter[str], idf: dict[str, float]) -> dict[str, float]:
    if not tf:
        return {}
    max_f = max(tf.values())
    vec: dict[str, float] = {}
    for term, freq in tf.items():
        # sublinear tf
        w = (0.5 + 0.5 * freq / max_f) * idf.get(term, 1.0)
        vec[term] = w
    return vec


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    keys = set(a) | set(b)
    dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (na * nb)))


def _is_latin_tech(term: str) -> bool:
    return bool(re.fullmatch(r"[a-z][a-z0-9+#./_-]{1,40}", term))


def extract_jd_keywords(jd_text: str, top_k: int = 40) -> list[tuple[str, float]]:
    """Rank 岗位描述 tokens; prefer tech/skill terms over requirement glue words."""
    tokens = tokenize(jd_text)
    tf = term_frequency(tokens)
    if not tf:
        return []

    req_boost: Counter[str] = Counter()
    for line in jd_text.splitlines():
        if re.search(r"要求|任职|资格|优先|技能|skills?|requirements?", line, re.I):
            for t in tokenize(line):
                req_boost[t] += 2

    phrase_set = {p.lower() for p in PHRASE_TERMS}
    scores: dict[str, float] = {}
    max_f = max(tf.values())
    for term, freq in tf.items():
        if term in STOPWORDS or term in KEYWORD_BLOCKLIST:
            continue
        if len(term) < 2:
            continue
        base = freq / max_f
        boost = 1.0
        if term in SKILL_TERMS or term in phrase_set:
            boost += 2.5
        if _is_latin_tech(term):
            boost += 2.0  # stack names in 岗位描述 are high signal even once
        if req_boost[term]:
            boost += 0.5 * min(req_boost[term], 3)
        is_cjk = bool(CJK_RE.fullmatch(term))
        if is_cjk and term not in SKILL_TERMS and term not in phrase_set:
            # Non-lexicon Chinese only if short & repeated
            if len(term) > 4 or freq < 2:
                continue
            boost *= 0.4
        scores[term] = base * boost

    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    kept: list[tuple[str, float]] = []
    for term, sc in ranked:
        if any(
            term != k and term in k and CJK_RE.fullmatch(term or "")
            for k, _ in kept
        ):
            continue
        kept.append((term, sc))
        if len(kept) >= top_k:
            break
    return kept


@dataclass
class KeywordBreakdown:
    hit: list[str] = field(default_factory=list)
    miss: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)  # in résumé but not 岗位描述 (top signal)


@dataclass
class MatchResult:
    score: float  # 0–100
    cosine: float  # 0–1
    keyword_coverage: float  # 0–100, % of top 岗位描述 keywords present in résumé
    keywords: KeywordBreakdown = field(default_factory=KeywordBreakdown)
    jd_keyword_count: int = 0
    resume_token_count: int = 0
    jd_token_count: int = 0
    verdict: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


def classify_verdict(score: float, coverage: float) -> str:
    if score >= 70 and coverage >= 60:
        return "strong_match"
    if score >= 50 and coverage >= 40:
        return "moderate_match"
    if score >= 35 or coverage >= 30:
        return "partial_match"
    return "weak_match"


def match_texts(
    resume_text: str,
    jd_text: str,
    top_k: int = 30,
    synonym_map: dict[str, set[str]] | None = None,
) -> MatchResult:
    if synonym_map is None:
        synonym_map = load_synonym_map()
    r_tokens = tokenize(resume_text)
    j_tokens = tokenize(jd_text)
    r_tf = term_frequency(r_tokens)
    j_tf = term_frequency(j_tokens)
    idf = build_idf([r_tf, j_tf])
    r_vec = tfidf_vector(r_tf, idf)
    j_vec = tfidf_vector(j_tf, idf)
    cos = cosine(r_vec, j_vec)

    jd_kw = extract_jd_keywords(jd_text, top_k=top_k)
    jd_terms = [t for t, _ in jd_kw]
    r_set = set(r_tokens)
    r_expanded = expand_resume_coverage(resume_text, r_set, synonym_map)
    hit = [t for t in jd_terms if term_covered(t, r_expanded, synonym_map)]
    miss = [t for t in jd_terms if not term_covered(t, r_expanded, synonym_map)]
    # extra: high-freq résumé skill-like tokens not in 岗位描述
    jd_expanded = expand_resume_coverage(jd_text, set(jd_terms), synonym_map)
    extra_candidates = [
        t
        for t, _ in r_tf.most_common(50)
        if t not in jd_expanded and (t in SKILL_TERMS or not CJK_RE.fullmatch(t))
    ][:15]

    coverage = (100.0 * len(hit) / len(jd_terms)) if jd_terms else 0.0
    # Blend cosine (semantic bag-of-words) with keyword coverage
    score = 100.0 * (0.55 * cos + 0.45 * (coverage / 100.0))
    score = round(min(100.0, max(0.0, score)), 1)
    coverage = round(coverage, 1)

    return MatchResult(
        score=score,
        cosine=round(cos, 4),
        keyword_coverage=coverage,
        keywords=KeywordBreakdown(hit=hit, miss=miss, extra=extra_candidates),
        jd_keyword_count=len(jd_terms),
        resume_token_count=len(r_tokens),
        jd_token_count=len(j_tokens),
        verdict=classify_verdict(score, coverage),
    )


def quality_report(
    resume_text: str,
    jd_text: str,
    cover_text: str | None = None,
    top_k: int = 30,
    synonym_map: dict[str, set[str]] | None = None,
    expected_salary: str | None = None,
    profile_path: str | Path | None = None,
    salary_compare: bool = True,
) -> dict:
    """Generation quality: résumé (+ optional cover) vs 岗位描述."""
    if synonym_map is None:
        synonym_map = load_synonym_map()
    base = match_texts(resume_text, jd_text, top_k=top_k, synonym_map=synonym_map)
    combined = resume_text
    cover_part: MatchResult | None = None
    if cover_text and cover_text.strip():
        cover_part = match_texts(
            cover_text, jd_text, top_k=top_k, synonym_map=synonym_map
        )
        combined = resume_text + "\n" + cover_text
    combined_result = match_texts(
        combined, jd_text, top_k=top_k, synonym_map=synonym_map
    )

    # Keywords still missing after combining materials
    still_miss = combined_result.keywords.miss
    # Keywords only in cover, not résumé
    cover_only: list[str] = []
    if cover_part:
        r_expanded = expand_resume_coverage(
            resume_text, set(tokenize(resume_text)), synonym_map
        )
        cover_only = [
            t
            for t in cover_part.keywords.hit
            if not term_covered(t, r_expanded, synonym_map)
        ]

    suggestions: list[str] = []
    if base.keyword_coverage < 50:
        suggestions.append(
            "简历里岗位关键词偏少；会的话写进经历里，不会的别硬凑。"
        )
    if still_miss:
        suggestions.append(
            "JD 里还有一些词材料没写到；会的再补，不会的当差距，别编。"
        )
    if cover_part and cover_part.score < 40:
        suggestions.append("打招呼写短一点也没关系，但最好点名公司和岗位，别像群发。")
    if cover_only:
        suggestions.append(
            "有些词只写在打招呼里、简历正文没有；一般还是简历更重要，能写进去就写。"
        )
    if base.verdict in ("strong_match", "moderate_match") and not suggestions:
        suggestions.append("分数还行，自己再核对一下经历是不是都属实。")

    salary: dict | None = None
    if salary_compare:
        salary = resolve_salary_compare(
            jd_text,
            expected_raw=expected_salary,
            profile_path=profile_path,
        )
        if salary.get("verdict") == "low":
            suggestions.insert(
                0,
                "薪资可能低于期望（见摘要「薪资对照」）；不投可记 tracker skipped --skip-reason salary_low。",
            )

    brief = build_zh_brief(
        combined_result=combined_result,
        still_miss=still_miss,
        cover_only=cover_only,
        suggestions=suggestions,
        jd_text=jd_text,
        salary=salary,
    )

    return {
        "resume": base.to_dict(),
        "cover": cover_part.to_dict() if cover_part else None,
        "combined": combined_result.to_dict(),
        "still_missing": still_miss,
        "cover_only_hits": cover_only,
        "suggestions": suggestions,
        "salary": salary,
        "brief_zh": brief,
        "summary": {
            "resume_score": base.score,
            "combined_score": combined_result.score,
            "keyword_coverage_combined": combined_result.keyword_coverage,
            "verdict": combined_result.verdict,
            "missing_count": len(still_miss),
            "hit_count": len(combined_result.keywords.hit),
            "salary_verdict": (salary or {}).get("verdict"),
            "salary_signal": (salary or {}).get("signal"),
        },
    }


VERDICT_ZH = {
    "strong_match": "匹配较强",
    "moderate_match": "匹配中等",
    "partial_match": "部分匹配",
    "weak_match": "匹配偏弱",
}


def _split_miss_core_nice(miss_terms: list[str], jd_text: str = "") -> tuple[list[str], list[str]]:
    """Heuristic: split miss terms into core hard-skills vs nice-to-have.

    v1 heuristic (no model, testable):
      - term ∈ miss_core if:
          1. term.lower() in SKILL_TERMS or PHRASE_TERMS
          2. looks like a Latin tech token (matches LATIN_TECH_RE)
          3. CJK term of length >= 2 that appears in the first 40% of JD text
             (responsibility/requirement sections tend to be earlier)
      - otherwise miss_nice
    """
    phrase_set = {p.lower() for p in PHRASE_TERMS}
    jd_head = jd_text[: int(len(jd_text) * 0.4)] if jd_text else ""
    core: list[str] = []
    nice: list[str] = []
    for t in miss_terms:
        tl = t.lower()
        is_core = False
        if tl in SKILL_TERMS or tl in phrase_set:
            is_core = True
        elif LATIN_TECH_RE.fullmatch(t):
            is_core = True
        elif CJK_RE.fullmatch(t) and len(t) >= 2:
            if t in jd_head:
                is_core = True
        if is_core:
            core.append(t)
        else:
            nice.append(t)
    return core[:6], nice[:6]


def _tone_open(score: float) -> str:
    if score >= 70:
        return "这份和你挺匹配的。"
    if score >= 40:
        return "有一定匹配度，重点看下面缺口是否属实。"
    return "这个岗位要求和你当前画像有距离——投了当练手也行，别抱太大期望；也可以想想是不是方向不太对。"


def _action_by_band(score: float) -> str:
    if score >= 80:
        return "这份很匹配，重点准备面试就行。"
    if score >= 60:
        return "基本匹配，建议把上面「核心硬技能」里你确实会的补进简历；不会的别编。"
    if score >= 40:
        return "有一定匹配但缺口不少，可以投但别抱太大期望；或再找更贴近画像的岗位。"
    return "匹配度较低，投了权当练手；建议优先找和你画像更接近的岗位。"


def build_zh_brief(
    *,
    combined_result: MatchResult,
    still_miss: list[str],
    cover_only: list[str],
    suggestions: list[str],
    jd_text: str = "",
    salary: dict | None = None,
) -> dict:
    """One-page Chinese brief: gaps / no-fiction / top 3 edit tips."""
    top_miss = still_miss[:8]
    top_hit = combined_result.keywords.hit[:8]
    miss_core, miss_nice = _split_miss_core_nice(top_miss, jd_text=jd_text)
    score = combined_result.score
    tone = _tone_open(score)
    action = _action_by_band(score)

    edit_tips: list[str] = []
    for tip in suggestions:
        if tip not in edit_tips:
            edit_tips.append(tip)
        if len(edit_tips) >= 3:
            break
    if len(edit_tips) < 3 and miss_core:
        edit_tips.append(
            f"如果确实会，可以优先补这几个核心词：{'、'.join(miss_core[:3])}。"
        )
    if len(edit_tips) < 3 and miss_nice:
        edit_tips.append(
            f"锦上添花项如果属实可以补：{'、'.join(miss_nice[:3])}。"
        )
    if len(edit_tips) < 3:
        edit_tips.append("简历和话术里写上公司名、岗位名，别写成万能模板。")
    if len(edit_tips) < 3:
        edit_tips.append("经历里尽量带数字，比空泛形容词好用。")

    return {
        "tone_open": tone,
        "headline": (
            f"综合 {score}/100（{VERDICT_ZH.get(combined_result.verdict, combined_result.verdict)}），"
            f"关键词覆盖 {combined_result.keyword_coverage}%"
        ),
        "still_missing": top_miss,
        "miss_core": miss_core,
        "miss_nice": miss_nice,
        "already_hit": top_hit,
        "cover_only": cover_only[:5],
        "edit_top3": edit_tips[:3],
        "action_by_band": action,
        "salary": salary,
        "compliance": "不会的技能别硬写上去刷分。",
        "score_note": "分数只是本地关键词对齐程度，不代表能不能拿到面试。同义词表会减少「明明会却 miss」。",
    }


def format_zh_brief(brief: dict) -> str:
    lines = [
        "【匹配摘要】",
        brief.get("tone_open", ""),
        brief.get("headline", ""),
        "",
        "已经对上的词：",
        "  " + ("、".join(brief.get("already_hit") or []) or "（没有）"),
        "",
        "JD 提到但你简历没写的词（不会的别硬编）：",
    ]
    miss_core = brief.get("miss_core") or []
    miss_nice = brief.get("miss_nice") or []
    if miss_core or miss_nice:
        if miss_core:
            lines.append("  · 核心硬技能（会再补，不会别编）：" + "、".join(miss_core))
        if miss_nice:
            lines.append("  · 其他要求（锦上添花）：" + "、".join(miss_nice))
    else:
        lines.append("  （没有，挺好）")
    lines.append("")
    salary = brief.get("salary")
    if salary:
        lines.append(
            f"薪资对照：{salary.get('signal', '·')} {salary.get('label', '')} — "
            f"{salary.get('summary', '')}"
        )
        lines.append("")
    if brief.get("cover_only"):
        lines += [
            "只写在打招呼里、简历正文没有的：",
            "  " + "、".join(brief["cover_only"]),
            "",
        ]
    lines.append("如果属实，可以改的方向：")
    for i, tip in enumerate(brief.get("edit_top3") or [], 1):
        lines.append(f"  {i}. {tip}")
    lines += [
        "",
        "【下一步建议】",
        brief.get("action_by_band", ""),
        "",
        brief.get("compliance", ""),
        brief.get("score_note", ""),
    ]
    return "\n".join(lines)


def diff_reports(before: dict, after: dict) -> dict:
    """Compare two quality_report dicts (v1 → v2 coverage flywheel)."""
    b = before.get("summary") or {}
    a = after.get("summary") or {}
    b_miss = set(before.get("still_missing") or [])
    a_miss = set(after.get("still_missing") or [])
    return {
        "score_before": b.get("combined_score"),
        "score_after": a.get("combined_score"),
        "score_delta": round(
            float(a.get("combined_score") or 0) - float(b.get("combined_score") or 0), 1
        ),
        "coverage_before": b.get("keyword_coverage_combined"),
        "coverage_after": a.get("keyword_coverage_combined"),
        "coverage_delta": round(
            float(a.get("keyword_coverage_combined") or 0)
            - float(b.get("keyword_coverage_combined") or 0),
            1,
        ),
        "miss_resolved": sorted(b_miss - a_miss),
        "miss_new": sorted(a_miss - b_miss),
        "miss_still": sorted(a_miss & b_miss),
        "verdict_before": b.get("verdict"),
        "verdict_after": a.get("verdict"),
    }


def format_diff_human(diff: dict) -> str:
    lines = [
        "=== 质量飞轮 · 报告对比 (v1 → v2) ===",
        f"综合分:   {diff['score_before']} → {diff['score_after']}  (Δ {diff['score_delta']:+})",
        f"覆盖率:   {diff['coverage_before']}% → {diff['coverage_after']}%  (Δ {diff['coverage_delta']:+})",
        f"verdict:  {diff['verdict_before']} → {diff['verdict_after']}",
        "",
        f"已补上的关键词 ({len(diff['miss_resolved'])}):",
        "  " + (", ".join(diff["miss_resolved"]) if diff["miss_resolved"] else "（无）"),
        f"新出现的缺口 ({len(diff['miss_new'])}):",
        "  " + (", ".join(diff["miss_new"]) if diff["miss_new"] else "（无）"),
        f"仍未覆盖 ({len(diff['miss_still'])}):",
        "  " + (", ".join(diff["miss_still"]) if diff["miss_still"] else "（无）"),
        "",
        "提示：Δ 变好不代表可以虚构；只统计文本对齐度。",
    ]
    return "\n".join(lines)


def format_score_human(result: MatchResult, title: str = "Match report") -> str:
    lines = [
        f"=== {title} ===",
        f"Score:              {result.score}/100  ({result.verdict})",
        f"Cosine (TF–IDF):    {result.cosine:.4f}",
        f"Keyword coverage:   {result.keyword_coverage}%  "
        f"({len(result.keywords.hit)}/{result.jd_keyword_count} 岗位描述 keywords)",
        f"Tokens:             résumé={result.resume_token_count}  jd={result.jd_token_count}",
        "",
        f"HIT ({len(result.keywords.hit)}):",
        "  " + (", ".join(result.keywords.hit) if result.keywords.hit else "(none)"),
        "",
        f"MISS ({len(result.keywords.miss)}):",
        "  " + (", ".join(result.keywords.miss) if result.keywords.miss else "(none)"),
        "",
        f"EXTRA on résumé (signal, not in 岗位描述 top):",
        "  " + (", ".join(result.keywords.extra) if result.keywords.extra else "(none)"),
    ]
    return "\n".join(lines)


def format_report_human(report: dict, *, zh_first: bool = True) -> str:
    s = report["summary"]
    lines: list[str] = []
    brief = report.get("brief_zh")
    if zh_first and brief:
        lines.append(format_zh_brief(brief))
        lines.append("")
        lines.append("--- 详细指标 ---")
    lines += [
        "=== Generation quality report ===",
        f"Résumé score:       {s['resume_score']}/100",
        f"Combined score:     {s['combined_score']}/100  ({s['verdict']})",
        f"Combined coverage:  {s['keyword_coverage_combined']}%  "
        f"({s['hit_count']} hit / {s['missing_count']} still missing)",
        "",
        format_score_human(
            MatchResult(**{**report["resume"], "keywords": KeywordBreakdown(**report["resume"]["keywords"])}),
            title="Résumé vs 岗位描述",
        ),
    ]
    if report.get("cover"):
        lines.append("")
        lines.append(
            format_score_human(
                MatchResult(
                    **{
                        **report["cover"],
                        "keywords": KeywordBreakdown(**report["cover"]["keywords"]),
                    }
                ),
                title="Cover / 打招呼 vs 岗位描述",
            )
        )
    lines.append("")
    lines.append("Still missing after combining materials:")
    lines.append(
        "  " + (", ".join(report["still_missing"]) if report["still_missing"] else "(none)")
    )
    if report.get("cover_only_hits"):
        lines.append("Hits only in cover (not résumé):")
        lines.append("  " + ", ".join(report["cover_only_hits"]))
    lines.append("")
    lines.append("Suggestions:")
    for i, tip in enumerate(report["suggestions"], 1):
        lines.append(f"  {i}. {tip}")
    lines.append("")
    lines.append(
        "Note: scores are local TF–IDF + keyword overlap (no neural embedding). "
        "Do not fabricate missing skills."
    )
    return "\n".join(lines)


def _synonym_map_from_args(args: argparse.Namespace) -> dict[str, set[str]]:
    extra: list[Path] = []
    path = getattr(args, "synonyms", None) or ""
    if path:
        extra.append(Path(path))
    if getattr(args, "no_synonyms", False):
        return {}
    return load_synonym_map(extra or None)


def cmd_score(args: argparse.Namespace) -> int:
    resume = read_text(args.resume)
    jd = read_text(args.jd)
    syn = _synonym_map_from_args(args)
    result = match_texts(resume, jd, top_k=args.top_k, synonym_map=syn)
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(format_score_human(result))
    return 0


def cmd_keywords(args: argparse.Namespace) -> int:
    jd = read_text(args.jd)
    ranked = extract_jd_keywords(jd, top_k=args.top_k)
    if args.json:
        print(json.dumps([{"term": t, "weight": round(w, 4)} for t, w in ranked], ensure_ascii=False, indent=2))
    else:
        print(f"Top {len(ranked)} 岗位描述 keywords:")
        for i, (t, w) in enumerate(ranked, 1):
            print(f"  {i:2}. {t:20}  {w:.3f}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    resume = read_text(args.resume)
    jd = read_text(args.jd)
    cover = read_text(args.cover) if args.cover else None
    syn = _synonym_map_from_args(args)
    report = quality_report(
        resume,
        jd,
        cover,
        top_k=args.top_k,
        synonym_map=syn,
        expected_salary=getattr(args, "expected_salary", None) or None,
        profile_path=getattr(args, "profile", None) or None,
        salary_compare=not getattr(args, "no_salary", False),
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if getattr(args, "zh_only", False):
            print(format_zh_brief(report["brief_zh"]))
        else:
            print(format_report_human(report, zh_first=not getattr(args, "no_zh", False)))
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nWrote JSON → {out}", file=sys.stderr)
    # Optional side-car brief
    if getattr(args, "brief_out", ""):
        bout = Path(args.brief_out)
        bout.parent.mkdir(parents=True, exist_ok=True)
        bout.write_text(format_zh_brief(report["brief_zh"]) + "\n", encoding="utf-8")
        print(f"Wrote brief → {bout}", file=sys.stderr)
    return 0


def cmd_salary(args: argparse.Namespace) -> int:
    jd = read_text(args.jd) if args.jd else ""
    result = resolve_salary_compare(
        jd,
        expected_raw=args.expected or None,
        profile_path=args.profile or None,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"薪资对照：{result.get('signal', '·')} {result.get('label', '')}\n"
            f"{result.get('summary', '')}"
        )
        if result.get("expected_input"):
            print(f"期望原文：{result['expected_input']}")
        if result.get("offered_raw"):
            print(f"JD 原文：{result['offered_raw']}")
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    before = json.loads(Path(args.before).read_text(encoding="utf-8"))
    after = json.loads(Path(args.after).read_text(encoding="utf-8"))
    diff = diff_reports(before, after)
    if args.json:
        print(json.dumps(diff, ensure_ascii=False, indent=2))
    else:
        print(format_diff_human(diff))
    if args.out:
        Path(args.out).write_text(
            json.dumps(diff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="match_resume",
        description="Lightweight local 简历↔岗位描述 matcher (TF–IDF cosine + keywords).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--top-k", type=int, default=30, help="岗位关键词列表长度")
        sp.add_argument("--json", action="store_true", help="machine-readable output")
        sp.add_argument(
            "--synonyms",
            default="",
            help="extra synonyms JSON (merged with config/synonyms.default.json)",
        )
        sp.add_argument(
            "--no-synonyms",
            action="store_true",
            help="disable synonym expansion (debug / A-B)",
        )

    sc = sub.add_parser("score", help="score résumé against 岗位描述 (job posting)")
    add_common(sc)
    sc.add_argument("--resume", required=True, help="path to résumé file")
    sc.add_argument("--jd", required=True, help="path to 岗位描述 file or literal text")
    sc.set_defaults(func=cmd_score)

    kw = sub.add_parser("keywords", help="extract ranked 岗位描述 keywords")
    add_common(kw)
    kw.add_argument("--jd", required=True)
    kw.set_defaults(func=cmd_keywords)

    rp = sub.add_parser("report", help="generation quality report (résumé + optional cover)")
    add_common(rp)
    rp.add_argument("--resume", required=True)
    rp.add_argument("--jd", required=True)
    rp.add_argument("--cover", default="", help="path to 打招呼/求职信 markdown")
    rp.add_argument("--out", default="", help="optional JSON report path")
    rp.add_argument("--brief-out", default="", help="write Chinese one-page brief to path")
    rp.add_argument("--zh-only", action="store_true", help="print only Chinese brief")
    rp.add_argument("--no-zh", action="store_true", help="skip Chinese brief header")
    rp.add_argument(
        "--expected-salary",
        default="",
        dest="expected_salary",
        help="your expected range e.g. 25-40K (overrides profile)",
    )
    rp.add_argument(
        "--profile",
        default="",
        help="profile markdown to read 薪资期望 (default: CLAUDE.zh.md if present)",
    )
    rp.add_argument(
        "--no-salary",
        action="store_true",
        help="skip expected vs JD salary block",
    )
    rp.set_defaults(func=cmd_report)

    sal = sub.add_parser(
        "salary",
        help="compare expected salary vs JD range (local parse, no crawl)",
    )
    sal.add_argument("--jd", default="", help="path to JD or literal text")
    sal.add_argument("--expected", default="", help="e.g. 25-40K or 30-50万/年")
    sal.add_argument("--profile", default="", help="CLAUDE.zh.md path for 薪资期望")
    sal.add_argument("--json", action="store_true")
    sal.set_defaults(func=cmd_salary)

    df = sub.add_parser("diff", help="compare two report JSON files (v1 → v2 flywheel)")
    df.add_argument("--before", required=True, help="older match_report.json")
    df.add_argument("--after", required=True, help="newer match_report.json")
    df.add_argument("--json", action="store_true")
    df.add_argument("--out", default="")
    df.set_defaults(func=cmd_diff)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
