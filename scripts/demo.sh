#!/usr/bin/env bash
# CN Job Assistant — one-shot local demo (no Boss login, no network required)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEMO="$ROOT/examples/demo"
OUT="$DEMO/output"
PY="${PYTHON:-python3}"

cd "$ROOT"

echo "=========================================="
echo " CN Job Assistant · Demo"
echo " 仓库: $ROOT"
echo "=========================================="
echo

if ! command -v "$PY" >/dev/null 2>&1; then
  echo "error: need python3 (or set PYTHON=...)" >&2
  exit 1
fi

mkdir -p "$OUT"

echo "▶ [1/4] 匹配质量报告（强匹配简历 vs JD）"
"$PY" tools/match_resume.py report \
  --resume "$DEMO/resume_星云科技.md" \
  --jd "$DEMO/jd_星云科技_后端.md" \
  --cover "$DEMO/da-zhaohu_星云科技_后端.md" \
  --out "$OUT/match_report.json" \
  --json > "$OUT/match_report.pretty.json"

# Human-readable to terminal + file
"$PY" tools/match_resume.py report \
  --resume "$DEMO/resume_星云科技.md" \
  --jd "$DEMO/jd_星云科技_后端.md" \
  --cover "$DEMO/da-zhaohu_星云科技_后端.md" \
  | tee "$OUT/match_report.txt"

echo
echo "▶ [2/4] 对照：弱匹配简历（分数应明显更低）"
"$PY" tools/match_resume.py score \
  --resume "$DEMO/resume_弱匹配.md" \
  --jd "$DEMO/jd_星云科技_后端.md" \
  | tee "$OUT/match_weak.txt"

echo
echo "▶ [3/4] 本地 Tracker（3 条演示投递）"
CSV="$OUT/job_search_tracker.csv"
rm -f "$CSV" "$OUT/job_search_tracker.html" "$OUT/job_search_tracker.db"
"$PY" tools/tracker.py --csv "$CSV" init --force
"$PY" tools/tracker.py --csv "$CSV" add \
  --company 星云科技 --role 高级后端 --channel Boss直聘 \
  --status applied --fit "demo-strong" \
  --cv "examples/demo/resume_星云科技.md" \
  --cover "examples/demo/da-zhaohu_星云科技_后端.md" \
  --source "examples/demo/jd_星云科技_后端.md" \
  --notes "demo: 已生成材料，待手动投递"
"$PY" tools/tracker.py --csv "$CSV" add \
  --company 青梧数据 --role 后端开发 --channel 智联 \
  --status interview --fit "demo" \
  --notes "demo: 二面中"
"$PY" tools/tracker.py --csv "$CSV" add \
  --company 北岸出行 --role 服务端 --channel 猎聘 \
  --status rejected --notes "demo: 已结束"
"$PY" tools/tracker.py --csv "$CSV" list
"$PY" tools/tracker.py --csv "$CSV" dashboard --out "$OUT/job_search_tracker.html"
"$PY" tools/tracker.py --csv "$CSV" export --format sqlite --out "$OUT/job_search_tracker.db"

echo
echo "▶ [4/4] 分数断言（强 ≫ 弱）"
"$PY" - <<'PY'
import json
from pathlib import Path
root = Path(__file__).resolve().parent if "__file__" in dir() else Path.cwd()
# script runs with cwd = ROOT
out = Path("examples/demo/output")
data = json.loads((out / "match_report.json").read_text(encoding="utf-8"))
# weak score from a fresh call
import sys
sys.path.insert(0, "tools")
import match_resume as m
weak = m.match_texts(
    Path("examples/demo/resume_弱匹配.md").read_text(encoding="utf-8"),
    Path("examples/demo/jd_星云科技_后端.md").read_text(encoding="utf-8"),
)
strong = data["summary"]["combined_score"]
print(f"  strong combined_score = {strong}")
print(f"  weak score            = {weak.score}")
assert strong > weak.score, (strong, weak.score)
assert strong >= 45, strong
assert weak.score < 40, weak.score
print("  assertion OK: strong ≫ weak")
PY

echo
echo "=========================================="
echo " Demo 完成 ✓"
echo "=========================================="
echo
echo "  打开看板（浏览器）:"
echo "    open $OUT/job_search_tracker.html    # macOS"
echo "    xdg-open $OUT/job_search_tracker.html  # Linux"
echo
echo "  匹配报告 JSON:"
echo "    $OUT/match_report.json"
echo
echo "  真实求职下一步:"
echo "    1. Agent 里跑 /setup-zh"
echo "    2. /apply-zh <你的 JD>"
echo "    3. App 内手动投递 → python tools/tracker.py add …"
echo
echo "  产品说明: README.md"
echo "=========================================="
