#!/usr/bin/env python3
"""
Salary Benchmark Lookup Tool — upstream / Denmark-oriented (legacy)

**国内主路径默认不可用。** 本脚本随上游 ai-job-search 保留：模糊匹配公司名时
处理 A/S、ApS 等丹麦法律后缀与 øæå 字符。国内求职闭环不依赖本工具。

- 数据：需自备仓库根目录 `salary_data.json`（见 tools/README_SALARY_TOOL.md）
- 国内谈薪方法论（无数据爬取）：integrations/catalog/salary-negotiate/
- 入口兼容：仓库根 `salary_lookup.py` 仅作薄转发 shim

Usage:
    python3 integrations/legacy/salary_lookup.py "Company Name"
    python3 integrations/legacy/salary_lookup.py "Company Name" --city "København"
    python3 salary_lookup.py "Company Name"   # root shim → 本文件
"""

import json
import sys
import re
import argparse
import unicodedata
from pathlib import Path

# Prefer repo-root salary_data.json (gitignore); allow colocated for tests.
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]  # integrations/legacy → repo root
DATA_FILE = _ROOT / "salary_data.json"
if not DATA_FILE.exists():
    alt = _HERE / "salary_data.json"
    if alt.exists():
        DATA_FILE = alt

# Common Danish <-> anglicized spelling variants
SPELLING_VARIANTS = {
    "ø": "o", "æ": "ae", "å": "aa",
    "ö": "o", "ä": "ae", "ü": "u",
}

# Legal suffixes and noise to strip when matching company names
STRIP_PATTERNS = [
    r"\ba/s\b", r"\baps\b", r"\bi/s\b", r"\bp/s\b", r"\bk/s\b",
    r"\bivs\b", r"\bamba\b", r"\ba\.m\.b\.a\.\b",
    r"\(vg\)", r"\(.*?\)",  # (VG) and other parentheticals
    r"\bdanmark\b", r"\bdenmark\b", r"\bscandinavia\b", r"\bnordic\b",
    r"\bgroup\b", r"\bholding\b",
    r",\s*.*$",  # everything after comma (sub-entities)
]


def load_data():
    if not DATA_FILE.exists():
        print("Error: salary_data.json not found.", file=sys.stderr)
        print("", file=sys.stderr)
        print("This tool requires a salary data file.", file=sys.stderr)
        print("See tools/README_SALARY_TOOL.md for setup instructions.", file=sys.stderr)
        print("", file=sys.stderr)
        print("If you don't have salary data, the salary lookup", file=sys.stderr)
        print("step will be skipped during /apply.", file=sys.stderr)
        sys.exit(1)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize(s):
    """Normalize string for robust fuzzy matching."""
    s = s.lower().strip()
    for pat in STRIP_PATTERNS:
        s = re.sub(pat, "", s)
    s = re.sub(r"[^a-zæøåöäü0-9]", "", s)
    return s.strip()


def anglicize(s):
    """Convert Danish/Nordic characters to anglicized equivalents."""
    s = s.lower()
    for danish, english in SPELLING_VARIANTS.items():
        s = s.replace(danish, english)
    return s


def extract_core_words(s):
    """Extract meaningful words from a company name, ignoring noise."""
    s = s.lower()
    for pat in STRIP_PATTERNS:
        s = re.sub(pat, "", s)
    words = re.findall(r"[a-zæøåöäü0-9]+", s)
    return [w for w in words if len(w) > 1]


def match_score(query, entry_name):
    """Compute a match score between 0 and 100 for ranking results."""
    q_norm = normalize(query)
    n_norm = normalize(entry_name)

    if not q_norm or not n_norm:
        return 0

    if q_norm == n_norm:
        return 100

    # Substring match (either direction). For very short queries that are only
    # a fragment of a longer name, require real word overlap to avoid false
    # positives (e.g. "sas" must not match "saxo bank").
    if q_norm in n_norm or n_norm in q_norm:
        shorter = min(len(q_norm), len(n_norm))
        longer = max(len(q_norm), len(n_norm))
        ratio = shorter / longer
        if shorter <= 4 and ratio < 0.5:
            q_words = set(extract_core_words(query))
            n_words = set(extract_core_words(entry_name))
            if not (q_words & n_words):
                return 0
        return 80 + int(ratio * 10)

    q_ang = anglicize(q_norm)
    n_ang = anglicize(n_norm)
    if q_ang == n_ang:
        return 85
    if q_ang in n_ang or n_ang in q_ang:
        shorter = min(len(q_ang), len(n_ang))
        longer = max(len(q_ang), len(n_ang))
        if shorter <= 4 and shorter / longer < 0.5:
            q_words_ang = {anglicize(w) for w in extract_core_words(query)}
            n_words_ang = {anglicize(w) for w in extract_core_words(entry_name)}
            if q_words_ang & n_words_ang:
                return 75
        else:
            return 75

    q_words = set(extract_core_words(query))
    n_words = set(extract_core_words(entry_name))
    if not q_words or not n_words:
        return 0

    overlap = q_words & n_words
    if not overlap:
        q_words_ang = {anglicize(w) for w in q_words}
        n_words_ang = {anglicize(w) for w in n_words}
        overlap = q_words_ang & n_words_ang

    if overlap:
        if len(q_words) == 1:
            q_word = list(q_words)[0]
            if q_word in n_words or anglicize(q_word) in {anglicize(w) for w in n_words}:
                return 70
            else:
                return 0

        coverage = len(overlap) / len(q_words)
        return int(30 + coverage * 40)

    return 0


def search_company(data, query, city=None):
    """Search for a company by name. Returns matching entries sorted by relevance."""
    companies = data.get("companies", [])
    scored = []

    for entry in companies:
        if city:
            city_lower = city.lower()
            entry_city = entry.get("city", "").lower()
            if city_lower not in entry_city and anglicize(city_lower) not in anglicize(entry_city):
                continue

        score = match_score(query, entry["company"])
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: (-x[0], x[1]["company"]))

    min_score = 30
    return [entry for score, entry in scored if score >= min_score]


def format_entry(entry, metadata):
    """Format a single company entry for display."""
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"  {entry['company']}")
    if entry.get("city"):
        lines.append(f"  Location: {entry['city']}")
    lines.append(f"{'='*60}")

    # Get category data (everything except company/city fields)
    categories = entry.get("categories", {})
    if not categories:
        # Fallback: treat any numeric fields as categories
        skip_keys = {"company", "city", "categories"}
        for key, value in entry.items():
            if key not in skip_keys and isinstance(value, dict):
                categories[key] = value

    if categories:
        index_label = metadata.get("index_label", "Index")
        baseline = metadata.get("index_baseline", 100)

        lines.append(f"  {'Category':<22} {'Count':>6} {index_label:>8}  {'vs Baseline':>10}")
        lines.append(f"  {'-'*50}")

        for label, data in categories.items():
            display_label = label.replace("_", " ").title()
            count = data.get("count")
            index = data.get("index")
            if count is not None or index is not None:
                count_str = str(count) if count is not None else "-"
                if isinstance(index, (int, float)):
                    diff = index - baseline
                    sign = "+" if diff >= 0 else ""
                    index_str = f"{index:.1f}"
                    diff_str = f"{sign}{diff:.1f}%"
                elif index is not None:
                    index_str = str(index)
                    diff_str = ""
                else:
                    index_str = "N/A*"
                    diff_str = ""
                lines.append(f"  {display_label:<22} {count_str:>6} {index_str:>8}  {diff_str:>10}")

        lines.append(f"\n  * N/A = Too few employees to publish (privacy)")
        if metadata.get("baseline_description"):
            lines.append(f"  {metadata['baseline_description']}")
        else:
            lines.append(f"  {index_label} {baseline} = baseline")
    else:
        # Simple format: just show all non-standard fields
        skip_keys = {"company", "city", "categories"}
        for key, value in entry.items():
            if key not in skip_keys:
                display_key = key.replace("_", " ").title()
                lines.append(f"  {display_key}: {value}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Salary Benchmark Lookup")
    parser.add_argument("company", nargs="?", help="Company name to search for")
    parser.add_argument("--city", help="Filter by city name")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--list-all", action="store_true", help="List all companies")
    args = parser.parse_args()

    data = load_data()
    metadata = data.get("metadata", {})
    companies = data.get("companies", [])

    if args.list_all:
        for entry in companies:
            city = entry.get("city", "")
            city_str = f" ({city})" if city else ""
            print(f"{entry['company']}{city_str}")
        return

    if not args.company:
        parser.print_help()
        sys.exit(1)

    results = search_company(data, args.company, args.city)

    if not results:
        print(f"No results found for '{args.company}'")
        if args.city:
            print(f"  (filtered by city: {args.city})")
        print("\nTry a shorter or different name. Company names in the dataset")
        print("may include legal suffixes like 'A/S' or 'ApS'.")
        sys.exit(1)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(f"\nFound {len(results)} match(es) for '{args.company}':")
        for entry in results:
            print(format_entry(entry, metadata))
        print()


if __name__ == "__main__":
    main()
