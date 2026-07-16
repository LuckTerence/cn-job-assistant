---
name: application-tracker
version: 2.6.0
description: >
  本地投递状态追踪与求职看板。以 job_search_tracker.csv 为权威源，通过
  tools/tracker.py（stdlib：CSV / 可选 SQLite / 单文件 HTML）读写，零 Docker。
  支持 match_score 归因（match-outcome）。触发词：投递追踪、申请状态、面试进度、
  求职看板、track application、offer 管理、tracker、匹配归因。
context: fork
allowed-tools: Bash(python* tools/tracker.py *), Bash(python3 tools/tracker.py *), Read, Glob, Grep, AskUserQuestion
---

# 投递追踪技能（本地 Tracker）

> **不要指向重型自托管当默认路径**。行业标配是 Tracker，但本仓库已有
> `job_search_tracker.csv` 作为命令链权威源。本技能用 **`tools/tracker.py`**
> 把这份 CSV 做成可操作的 CLI + 可选 HTML 看板，而不是默认要求 Docker 部署 jobsync。

## 权威源

| 追踪器 | 角色 | 形态 |
|--------|------|------|
| **`job_search_tracker.csv`** | **唯一权威源** | 仓库根目录，本地 CSV，`/outcome` 与本 CLI 读写 |
| `tools/tracker.py dashboard` | 可视化镜像 | 生成 `job_search_tracker.html`（勿提交，已 gitignore） |
| jobsync 等 | **可选**外挂 | 见 `integrations/catalog/` 思路；不自动同步 |

表头（22 列；结构化列 / `skip_reason` / `expected_salary` / `match_*` 均可空，旧 CSV 缺列可读）：

```
date,company,sector,role,role_type,channel,status,contact_person,fit_rating,notes,
cv_file,cover_letter_file,source,salary,city,education,experience,skip_reason,expected_salary,
match_score,match_coverage,match_verdict
```

关闭态含 `skipped`（不投）。**Phase 1**：`status=skipped` 时**必须**填 `skip_reason` 枚举：

| 键 | 含义 |
|----|------|
| `salary_low` | 薪资偏低 |
| `location` | 地点不合适 |
| `low_match` | 匹配度低 |
| `unknown_company` | 不了解公司 |
| `other` | 其他（细节写 `notes`） |

`dashboard` / `today` 共用待办规则：面试中 · 建议跟进（≥7 天仍 open）· 建议复盘（近 30 天结束）。  
有 skipped 时展示**不投信号**分布；`skip-stats` 在样本≥10 且单一原因≥40% 时提示 Phase 2 信号就绪。

## 安装

无第三方依赖（Python 3.10+ 标准库）：

```bash
python tools/tracker.py init
python tools/tracker.py --help
```

## 常用命令

```bash
# 记一笔（已投用 applied；还没投用 to_apply）
python tools/tracker.py add \
  --company 示例科技 --role 后端工程师 \
  --channel Boss直聘 --status applied \
  --city 杭州 --salary 25-40K \
  --source "https://…" \
  --cv documents/zh/resume_示例科技.md \
  --cover documents/zh/da-zhaohu_示例科技_后端.md

# 评估后不投（必须带 --skip-reason）
python tools/tracker.py add \
  --company 某厂 --role 后端 --channel Boss直聘 \
  --status skipped --skip-reason salary_low

# 列表 / 仅进行中
python tools/tracker.py list
python tools/tracker.py list --open-only
python tools/tracker.py list --status interview

# 每日工作台（面试 / 跟进≥7天 / 复盘 / 不投信号）
python tools/tracker.py today

# v0.11 今日计划：面试 → 跟进 → top N 条 to_apply（默认可打分）
python tools/tracker.py day-plan --limit 3 --track internet

# v0.11 批打分排序（cv_file + source 需为本地文件）
python tools/tracker.py rank --status to_apply --track internet
python tools/tracker.py rank --write-fit   # 写入 fit_rating + match_score/coverage/verdict

# v0.12 薄编排 + 薪资旗标
python tools/flow.py shortlist --jobs path/to/jobs.json --track internet --limit 3
python tools/tracker.py list --open-only --salary-flag --expected-salary '25-40K'

# v0.13 漏斗 + 多岗粘贴
python tools/tracker.py funnel
python tools/split_jds.py -i pasted.txt -o documents/zh/inbox
python tools/tracker.py import-jobs documents/zh/inbox/jobs_stub.json

# 不投原因分布（Phase 1 产品信号）
python tools/tracker.py skip-stats

# 1.2 匹配分 × 结果归因（质量飞轮）
python tools/tracker.py match-outcome

# 投前质量门禁（写 match 分前建议先过）
python tools/quality_gate.py --resume r.md --jd j.md --pdf r.pdf

# 搜岗结果批量入库（JSON / NDJSON / CSV；默认 status=to_apply，按 company+role+channel 去重）
python tools/tracker.py import-jobs path/to/jobs.json --default-channel Boss直聘
python tools/tracker.py import-jobs path/to/jobs.json --dry-run
python tools/tracker.py import-jobs path/to/jobs.json --fill-empty   # 重复行只补空字段
# 样例：examples/demo/jobs_sample.json

# /apply-zh 预填：默认 --status to_apply（安全）；Agent 须问用户确认后再 add
python tools/tracker.py suggest-add \
  --company 示例科技 --role 后端 --channel Boss直聘 \
  --cv documents/zh/resume_示例科技.md \
  --city 杭州 --salary 25-40K \
  --match-score 72 --match-coverage 55 --match-verdict moderate_match

# 状态更新（可补结构化字段；改成 skipped 时补 --skip-reason）
# /outcome 优先用 --notes-append，避免覆盖历史 notes
python tools/tracker.py update --company 示例科技 --role 后端工程师 --status interview \
  --notes-append "2026-07-17 约一面"
python tools/tracker.py update --company 示例科技 --role 后端工程师 --city 上海
python tools/tracker.py update --company 某厂 --role 后端 --status skipped --skip-reason location

# 详情
python tools/tracker.py show --company 示例科技

# 单文件 HTML 看板（待办 + 漏斗 + 改状态下拉）
python tools/tracker.py dashboard
# 本机一键改状态（推荐日常用）
python tools/tracker.py serve
# 浏览器打开 http://127.0.0.1:8765/

# 导出 SQLite（可选查询）
python tools/tracker.py export --format sqlite
```

## 工作流（agent 编排）

1. `/apply-zh` 结束后：**先跑** `suggest-add` 展示预填摘要（默认 `to_apply`）。
2. **询问用户**：`to_apply` / `applied` / `skipped`（不投）/ 稍后；**禁止静默**标 `applied` 后 `add`。
3. 用户确认后再 `tracker.py add … --status <选择>`；若 **skipped** 必须带 `--skip-reason`。
4. 面试 / offer / 拒信：优先 **`/outcome`**，或 `tracker.py update --status …`。
5. 总览：`today` / `dashboard`；看不投分布：`skip-stats`。
6. 搜岗导出后：`import-jobs` 批量写入 `to_apply`，再挑岗位跑 `/apply-zh`。
## 合规与边界

- CSV / HTML / SQLite 含个人求职数据，已在 `.gitignore`（`job_search_tracker.csv` 等），勿提交。
- 状态如实维护，不虚构面试 / offer。
- 本工具不连接招聘平台、不自动投递。

## 与其他能力的配合

- 检索 → `bosszhipin-search` / `domestic-jobs-search`（先 `install_domestic_search.py`）
- 中文材料 → `/apply-zh`、`/da-zhaohu`
- 结果归档 → `/outcome`
- 重型可选集成 → `integrations/catalog/`（模拟面试 / Reactive-Resume / 谈薪方法论等）
