#!/usr/bin/env bash
# Domestic product-path offline smoke — no network, no Boss login.
# Does NOT re-run the full unit suite (use: make test && make smoke).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"
cd "$ROOT"

echo "=========================================="
echo " CN Job Assistant · smoke_cn (1.0 product path)"
echo "=========================================="

if ! command -v "$PY" >/dev/null 2>&1; then
  echo "error: need python3" >&2
  exit 1
fi

echo "▶ CLI help surfaces"
"$PY" tools/tracker.py --help >/dev/null
"$PY" tools/match_resume.py --help >/dev/null
"$PY" tools/flow.py --help >/dev/null
"$PY" tools/split_jds.py --help >/dev/null
"$PY" tools/apply_assist.py explain >/dev/null

echo "▶ linters (domestic surface)"
"$PY" tools/lint_zh_refs.py
"$PY" tools/lint_skill_surface.py

echo "▶ product demo (offline)"
bash scripts/demo.sh >/tmp/cn_demo_smoke.log 2>&1 || {
  echo "demo failed; last lines:" >&2
  tail -50 /tmp/cn_demo_smoke.log >&2
  exit 1
}
test -f examples/demo/output/funnel.txt
test -f examples/demo/output/day_plan.txt
test -f examples/demo/output/job_search_tracker.html
grep -q "漏斗" examples/demo/output/funnel.txt
grep -q "filter-status" examples/demo/output/job_search_tracker.html

echo "▶ split_jds + import + funnel + flow (temp)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cat >"$TMP/pasted.txt" <<'EOF'
# 冒烟甲 · 后端
薪资：25-40K
要求 Java 微服务 高并发

---

# 冒烟乙 · 数据
公司：冒烟乙
岗位：数据开发
要求 Python Spark
EOF

"$PY" tools/split_jds.py -i "$TMP/pasted.txt" -o "$TMP/inbox" --channel 粘贴
test -f "$TMP/inbox/jobs_stub.json"
CSV="$TMP/tracker.csv"
"$PY" tools/tracker.py --csv "$CSV" init --force
"$PY" tools/tracker.py --csv "$CSV" import-jobs "$TMP/inbox/jobs_stub.json"
"$PY" tools/tracker.py --csv "$CSV" funnel | tee "$TMP/funnel.txt"
grep -q "漏斗" "$TMP/funnel.txt"
"$PY" tools/match_resume.py score --json \
  --resume tests/fixtures/resume_backend_good.md \
  --jd tests/fixtures/jd_backend_sample.md >"$TMP/good.json"
"$PY" - <<PY
import json
g=json.load(open("$TMP/good.json"))
assert g["score"] >= 45, g
print("  match score OK", g["score"])
PY
"$PY" tools/match_resume.py salary --jd tests/fixtures/jd_backend_sample.md \
  --expected '25-40K' | tee "$TMP/salary.txt"
grep -q "薪资对照" "$TMP/salary.txt"
"$PY" tools/flow.py --csv "$CSV" shortlist --limit 2 --track internet \
  >"$TMP/flow.txt" 2>"$TMP/flow.err" || {
  cat "$TMP/flow.err" "$TMP/flow.txt" >&2
  exit 1
}
grep -q "今日计划" "$TMP/flow.txt"

echo "▶ version"
VER="$("$PY" -c "import json; print(json.load(open('skill.json'))['version'])")"
echo "  skill.json = $VER"
test "$VER" = "1.0.0"

echo "=========================================="
echo " smoke_cn OK ✓  (pair with: make test)"
echo "=========================================="
