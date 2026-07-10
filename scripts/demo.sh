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

echo "▶ [1/7] 匹配质量报告（强匹配简历 vs 岗位描述）"
"$PY" tools/match_resume.py report \
  --resume "$DEMO/resume_星云科技.md" \
  --jd "$DEMO/jd_星云科技_后端.md" \
  --cover "$DEMO/da-zhaohu_星云科技_后端.md" \
  --out "$OUT/match_report.json" \
  --json > "$OUT/match_report.pretty.json"

"$PY" tools/match_resume.py report \
  --resume "$DEMO/resume_星云科技.md" \
  --jd "$DEMO/jd_星云科技_后端.md" \
  --cover "$DEMO/da-zhaohu_星云科技_后端.md" \
  | tee "$OUT/match_report.txt"

echo
echo "▶ [2/7] 对照：弱匹配简历（分数应明显更低）"
"$PY" tools/match_resume.py score \
  --resume "$DEMO/resume_弱匹配.md" \
  --jd "$DEMO/jd_星云科技_后端.md" \
  | tee "$OUT/match_weak.txt"

echo
echo "▶ [3/7] 本地 Tracker（3 条演示投递）"
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
echo "▶ [4/7] 中文人话摘要"
"$PY" tools/match_resume.py report --zh-only \
  --resume "$DEMO/resume_星云科技.md" \
  --jd "$DEMO/jd_星云科技_后端.md" \
  --cover "$DEMO/da-zhaohu_星云科技_后端.md" \
  | tee "$OUT/match_brief_zh.txt"

echo
echo "▶ [5/7] 分赛道对比（互联网 vs 国企）"
"$PY" tools/match_resume.py report --zh-only \
  --resume "$DEMO/tracks/internet/resume.md" \
  --jd "$DEMO/tracks/internet/jd.md" \
  --cover "$DEMO/tracks/internet/da-zhaohu.md" \
  --out "$OUT/track_internet_report.json" \
  --brief-out "$OUT/track_internet_brief.txt"
"$PY" tools/match_resume.py report --zh-only \
  --resume "$DEMO/tracks/soe/resume.md" \
  --jd "$DEMO/tracks/soe/jd.md" \
  --cover "$DEMO/tracks/soe/cover.md" \
  --out "$OUT/track_soe_report.json" \
  --brief-out "$OUT/track_soe_brief.txt"
echo "  internet brief → $OUT/track_internet_brief.txt"
echo "  soe brief      → $OUT/track_soe_brief.txt"

echo
echo "▶ [6/7] 质量飞轮 diff 演示（弱简历报告 vs 强简历报告）"
"$PY" tools/match_resume.py report --json --no-zh \
  --resume "$DEMO/resume_弱匹配.md" \
  --jd "$DEMO/jd_星云科技_后端.md" \
  --out "$OUT/match_report_v1_weak.json" >/dev/null
"$PY" tools/match_resume.py diff \
  --before "$OUT/match_report_v1_weak.json" \
  --after "$OUT/match_report.json" \
  | tee "$OUT/match_diff_v1_v2.txt"

echo
echo "▶ [7/7] tracker today + suggest-add + 分数断言"
"$PY" tools/tracker.py --csv "$CSV" today | tee "$OUT/tracker_today.txt"
"$PY" tools/tracker.py suggest-add \
  --company 星云科技 --role 高级后端 --channel Boss直聘 \
  --cv examples/demo/resume_星云科技.md \
  --cover examples/demo/da-zhaohu_星云科技_后端.md \
  --source examples/demo/jd_星云科技_后端.md \
  | tee "$OUT/suggest_add.txt"

"$PY" - <<'PY'
import json
from pathlib import Path
import sys
sys.path.insert(0, "tools")
import match_resume as m
out = Path("examples/demo/output")
data = json.loads((out / "match_report.json").read_text(encoding="utf-8"))
assert "brief_zh" in data and data["brief_zh"].get("edit_top3")
weak = m.match_texts(
    Path("examples/demo/resume_弱匹配.md").read_text(encoding="utf-8"),
    Path("examples/demo/jd_星云科技_后端.md").read_text(encoding="utf-8"),
)
strong = data["summary"]["combined_score"]
print(f"  strong combined_score = {strong}")
print(f"  weak score            = {weak.score}")
assert strong > weak.score
assert strong >= 45
assert weak.score < 40
print("  assertion OK: strong ≫ weak + brief_zh present")
PY

echo
echo "=========================================="
echo " Demo 完成 ✓"
echo "=========================================="
echo
echo "  打开看板: open $OUT/job_search_tracker.html"
echo "  人话摘要: $OUT/match_brief_zh.txt"
echo "  今日工作台: $OUT/tracker_today.txt"
echo "  赛道对比: $OUT/track_internet_brief.txt  vs  $OUT/track_soe_brief.txt"
echo "  飞轮 diff: $OUT/match_diff_v1_v2.txt"
echo
echo "  真实求职: /setup-zh（可粘贴旧简历）→ /apply-zh → 手动投 → tracker"
echo "  Agent 安装: docs/INSTALL.agents.zh.md"
echo "  产品说明: README.md"
echo "=========================================="
