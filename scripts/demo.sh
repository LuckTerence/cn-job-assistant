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

echo "▶ [0/8] 导出可投递 PDF（默认交付格式）"
"$PY" tools/export_resume_pdf.py \
  --input "$DEMO/resume_星云科技.md" \
  --output "$OUT/resume_星云科技.pdf" \
  --keep-html
"$PY" tools/export_resume_pdf.py \
  --input "$DEMO/tracks/internet/resume.md" \
  --output "$OUT/resume_互联网样例.pdf"
"$PY" tools/export_resume_pdf.py \
  --input "$DEMO/tracks/soe/resume.md" \
  --output "$OUT/resume_国企样例.pdf"
echo "  PDF → $OUT/resume_星云科技.pdf"

echo
echo "▶ [1/8] 匹配质量报告（强匹配 + 同义词 + 期望薪资对照）"
"$PY" tools/match_resume.py report \
  --resume "$DEMO/resume_星云科技.md" \
  --jd "$DEMO/jd_星云科技_后端.md" \
  --cover "$DEMO/da-zhaohu_星云科技_后端.md" \
  --expected-salary '25-40K' \
  --out "$OUT/match_report.json" \
  --json > "$OUT/match_report.pretty.json"

"$PY" tools/match_resume.py report \
  --resume "$DEMO/resume_星云科技.md" \
  --jd "$DEMO/jd_星云科技_后端.md" \
  --cover "$DEMO/da-zhaohu_星云科技_后端.md" \
  --expected-salary '25-40K' \
  | tee "$OUT/match_report.txt"

"$PY" tools/match_resume.py salary \
  --jd "$DEMO/jd_星云科技_后端.md" \
  --expected '25-40K' \
  | tee "$OUT/salary_compare.txt"

echo
echo "▶ [2/8] 对照：弱匹配简历（分数应明显更低）"
"$PY" tools/match_resume.py score \
  --resume "$DEMO/resume_弱匹配.md" \
  --jd "$DEMO/jd_星云科技_后端.md" \
  | tee "$OUT/match_weak.txt"

echo
echo "▶ [3/8] 本地 Tracker（投递 + 不投信号样例）"
CSV="$OUT/job_search_tracker.csv"
rm -f "$CSV" "$OUT/job_search_tracker.html" "$OUT/job_search_tracker.db" "$OUT/skip_stats.txt"
"$PY" tools/tracker.py --csv "$CSV" init --force
# 进行中 / 已投
"$PY" tools/tracker.py --csv "$CSV" add \
  --company 星云科技 --role 高级后端 --channel Boss直聘 \
  --status applied --fit "demo-strong" \
  --city 杭州 --salary 25-40K \
  --cv "examples/demo/resume_星云科技.md" \
  --cover "examples/demo/da-zhaohu_星云科技_后端.md" \
  --source "examples/demo/jd_星云科技_后端.md" \
  --notes "demo: 已生成材料，待手动投递"
"$PY" tools/tracker.py --csv "$CSV" add \
  --company 青梧数据 --role 后端开发 --channel 智联 \
  --status interview --fit "demo" \
  --city 上海 --salary 30-45K \
  --notes "demo: 二面中"
"$PY" tools/tracker.py --csv "$CSV" add \
  --company 北岸出行 --role 服务端 --channel 猎聘 \
  --status rejected --city 北京 \
  --notes "demo: 已结束 → 可 /outcome 复盘 + match diff"
# Phase 1：评估后不投（带 skip_reason，供 skip-stats / 看板「不投信号」）
"$PY" tools/tracker.py --csv "$CSV" add \
  --company 远航金融 --role 后端 --channel Boss直聘 \
  --status skipped --skip-reason salary_low \
  --city 北京 --salary 15-20K \
  --notes "demo: 薪资低于预期"
"$PY" tools/tracker.py --csv "$CSV" add \
  --company 南山制造 --role 后端 --channel 智联 \
  --status skipped --skip-reason location \
  --city 东莞 \
  --notes "demo: 地点不合适"
"$PY" tools/tracker.py --csv "$CSV" add \
  --company 极简创业 --role 全栈 --channel Boss直聘 \
  --status skipped --skip-reason low_match \
  --notes "demo: 匹配度低，材料生成后选择不投"
"$PY" tools/tracker.py --csv "$CSV" list
"$PY" tools/tracker.py --csv "$CSV" skip-stats | tee "$OUT/skip_stats.txt"
# 搜岗 → tracker：批量导入样例（默认 to_apply，去重）
"$PY" tools/tracker.py --csv "$CSV" import-jobs "$DEMO/jobs_sample.json" \
  | tee "$OUT/import_jobs.txt"
"$PY" tools/tracker.py --csv "$CSV" dashboard --out "$OUT/job_search_tracker.html"
"$PY" tools/tracker.py --csv "$CSV" export --format sqlite --out "$OUT/job_search_tracker.db"

echo
echo "▶ [4/8] 中文人话摘要"
"$PY" tools/match_resume.py report --zh-only \
  --resume "$DEMO/resume_星云科技.md" \
  --jd "$DEMO/jd_星云科技_后端.md" \
  --cover "$DEMO/da-zhaohu_星云科技_后端.md" \
  --expected-salary '25-40K' \
  | tee "$OUT/match_brief_zh.txt"

echo
echo "▶ [5/8] 分赛道对比（互联网 vs 国企）"
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
echo "▶ [6/8] 质量飞轮 diff 演示（弱简历报告 vs 强简历报告）"
"$PY" tools/match_resume.py report --json --no-zh \
  --resume "$DEMO/resume_弱匹配.md" \
  --jd "$DEMO/jd_星云科技_后端.md" \
  --out "$OUT/match_report_v1_weak.json" >/dev/null
"$PY" tools/match_resume.py diff \
  --before "$OUT/match_report_v1_weak.json" \
  --after "$OUT/match_report.json" \
  | tee "$OUT/match_diff_v1_v2.txt"

echo
echo "▶ [7/8] tracker today + suggest-add + 分数断言"
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
pdf = Path("examples/demo/output/resume_星云科技.pdf")
assert pdf.is_file() and pdf.stat().st_size > 1000, pdf
print(f"  pdf OK: {pdf} ({pdf.stat().st_size} bytes)")
PY

echo
echo "=========================================="
echo " Demo 完成 ✓"
echo "=========================================="
echo
echo "  可投递 PDF: $OUT/resume_星云科技.pdf"
echo "  打开看板: open $OUT/job_search_tracker.html"
echo "  人话摘要: $OUT/match_brief_zh.txt"
echo "  薪资对照: $OUT/salary_compare.txt"
echo "  今日工作台: $OUT/tracker_today.txt"
echo "  不投信号: $OUT/skip_stats.txt"
echo "  搜岗导入: $OUT/import_jobs.txt  (源: examples/demo/jobs_sample.json)"
echo "  赛道对比: $OUT/track_internet_brief.txt  vs  $OUT/track_soe_brief.txt"
echo "  飞轮 diff: $OUT/match_diff_v1_v2.txt"
echo
echo "👆 这就是跑完一个岗位后的完整产出。"
echo "打开看板看「待办 + 不投信号」——真实用的时候长这样。"
echo
echo "  真实求职: /setup-zh → /apply-zh → 手动投/skipped → tracker / /outcome"
echo "  不投原因: python tools/tracker.py skip-stats"
echo "  Agent 安装: docs/INSTALL.agents.zh.md"
echo "  产品说明: README.md"
echo "=========================================="
