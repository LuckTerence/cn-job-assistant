# Changelog

本仓库遵循 [语义化版本](https://semver.org/lang/zh-CN/) 的宽松约定。  
**1.0.0** 起：默认国内闭环能力视为稳定；破坏性变更会升主版本或在条目标明。

## [1.2.2] — 2026-07-17

### P2 收尾：投递提示写分 + Release 脚本 + flow gate 透传

- **`apply_assist`**：semi/auto/manual 提示带上 `--match-score` 与 `quality_gate` / `match-outcome`
- **`make release-gh`** / `publish_github_release.sh`：按 `skill.json` 版本选 notes（优先 `docs/github-release-vX.Y.Z.md`）
- **`flow gate`**：透传 `--min-score` / `--min-coverage` / `--no-salary` / `--zh-only`
- **weekly-report**：下周建议含 `match-outcome`
- **ats-gate 文档**：诚信 high/medium 分级说明

```bash
make release-gh   # 需先: gh auth login
python tools/flow.py gate --resume r.md --jd j.md --min-score 50 --zh-only
```

## [1.2.1] — 2026-07-17

### 门禁误杀修复 + 安全/性能/1.2 接线补全

| 修复 | 说明 |
|------|------|
| **诚信** | `metric_not_in_profile` → medium（不再 HARD_FAIL 误杀真实简历）；支持 `99.95%` 等小数 |
| **serve** | 状态更新改为 **exact** company/role/channel，禁止子串批量误改 |
| **flow --skip-import** | 有 `--jobs` 时也真正跳过 import |
| **rank --write-fit** | 仅写当前 status 过滤行；帮助文案同步 match_* |
| **import --limit** | 按成功写入计数，不按原始循环 |
| **性能** | rank/day-plan 复用 (cv,jd,track) 打分缓存；画像期望薪资读一次 |
| **看板** | 匹配分×结果卡片；demo 写入 match_score + gate + match-outcome |
| **CLI** | `update --match-channel`；quality_gate 错误 profile 路径 exit 3 |
| **文档** | 根 `SKILL.md` / outcome 表头对齐 1.2 |

```bash
python tools/quality_gate.py --resume r.md --jd j.md   # 量化缺画像不再硬拦
python tools/tracker.py serve                          # 精确一行改状态
```

## [1.2.0] — 2026-07-17

### 投前质量门禁 + AI/ATS 过筛 + 匹配归因

| 能力 | 说明 |
|------|------|
| **`quality_gate.py`** | 一键：匹配报告 + 画像诚信 + ATS 文本层；SOFT/HARD 退出码 |
| **`flow gate`** | 薄封装同上 |
| **改这 3 条** | `match report` / `align` 输出可执行 bullet 改写清单（禁止虚构） |
| **tracker `match_*`** | 列 `match_score` / `match_coverage` / `match_verdict`；`rank --write-fit` 回写 |
| **`match-outcome`** | 匹配分 × 进面/拒/不投 归因（质量飞轮） |
| **ATS 清单** | `export_resume_pdf --ats-checklist`；双格式 md=粘贴 / pdf=上传 |
| **`/apply-zh`** | Step 4 强制门禁；tracker 预填匹配分 |

```bash
python tools/quality_gate.py --resume r.md --jd j.md --pdf r.pdf --out gate.json
python tools/match_resume.py align --resume r.md --jd j.md
python tools/tracker.py match-outcome
# 文档：docs/ats-gate.zh.md
```

**兼容**：旧 CSV 缺 `match_*` 列时读入自动补空，写出时带齐表头。

## [1.1.1] — 2026-07-17

### 看板一键改状态 + Typst 第二套模板

- **`tracker serve`**：本机 `127.0.0.1:8765` 打开看板，下拉状态 **直接写 CSV**  
- **`dashboard` 离线**：表内「改状态」复制 `tracker update` 命令（file:// 友好）  
- **Typst `compact` 模板**：青绿头栏、更密排版  
  `python tools/export_resume_pdf.py -i resume.md --template compact`

```bash
python tools/tracker.py serve
# 浏览器打开 http://127.0.0.1:8765/
python tools/export_resume_pdf.py -i documents/zh/resume_x.md --template compact
```

## [1.1.0] — 2026-07-17

### 向竞品学人性化（合法复用接口/模式，不 vendor 逆向）

| 学了谁 | 落地 |
|--------|------|
| career-ops | [COMMAND_MAP](./docs/COMMAND_MAP.zh.md) 技能模式表 + 日常节奏；`weekly-report` 人话战报 |
| boss-agent-cli (MIT) | `normalize_job_export.py` 解 JSON 信封；`flow ingest` / `shortlist --raw`；catalog 说明 |
| 社区翻车案例 | `check_profile_resume.py` 画像↔简历诚信检查；`/apply-zh` 强制跑 |
| ATS 实践 | `export_resume_pdf --verify-text`（可选 pdftotext） |

```bash
python tools/normalize_job_export.py -i boss_raw.json -o jobs.json
python tools/flow.py shortlist --raw boss_raw.json --track internet
python tools/check_profile_resume.py --profile CLAUDE.zh.md --resume documents/zh/resume_x.md
python tools/tracker.py weekly-report
```

**仍不默认**：海投、embedding、代点发送。

## [1.0.2] — 2026-07-17

### 发版与仓库卫生

- `tools/check_release_ready.py` + `make release-ready`：版本/文档清单门禁  
- `scripts/publish_github_release.sh`：`gh auth login` 后一键建 Release  
- `dist/`、打包 zip 写入 `.gitignore`  
- README 文档地图与路线图收口到 1.0 验证期叙事  
- `make check` 含 release-ready  

## [1.0.1] — 2026-07-17

### 新人路径与验证期收口

- **[docs/QUICKSTART.zh.md](./docs/QUICKSTART.zh.md)**：15 分钟上手 + 卡点表  
- **[docs/AGENT_PROMPT.zh.md](./docs/AGENT_PROMPT.zh.md)**：无 slash 时一键提示词  
- README 首屏「新人从这里开始」；`/setup-zh` 强制期望薪资 + tracker init + 1.0 下一步  
- 分发/Release 素材已齐（`github-release-v1.0.0.md` · `dist-notes-1.0.zh.md`）  
- `lint_zh_refs` 纳入 QUICKSTART / flow / split_jds  

## [1.0.0] — 2026-07-17

### 国内 Agent 求职最小可靠闭环

能力面齐备（0.10～0.13 累积），并加上 **1.0 发版门禁**：

- `bash scripts/smoke_cn.sh` / `make smoke`：离线产品路径冒烟（demo · split_jds · import · funnel · flow · 匹配/薪资）
- `make check`：单测 + smoke
- 发版说明：[docs/RELEASE-1.0.zh.md](./docs/RELEASE-1.0.zh.md)
- CI domestic-loop 增加 smoke 步骤

**承诺**：本地优先 · 默认 manual · 可量化匹配 · 可追踪 · Agent 可编排。  
**不承诺**：offer 结果 · 默认海投 · 默认 embedding · 云端同步。

社区验证（≥5 人 × ≥3 岗）仍欢迎 [我在用 Issue](https://github.com/LuckTerence/cn-job-assistant/issues/new?template=using.yml)，不挡能力发版。

## [0.13.0] — 2026-07-17

### 决策可信

- **`tracker funnel`**：to_apply → 已投 → 面试 → Offer → 入职 快照漏斗；dashboard 卡片
- **真缺口 vs 同义词已对齐**：`keywords.synonym_hit` + 中文摘要分块说明
- **`tools/split_jds.py`**：多段粘贴 JD → 拆文件 + `jobs_stub.json` → `import-jobs`
- **`/apply-zh`**：多岗粘贴引导；有短名单时先 `rank` / `day-plan` / `funnel` 再生成

```bash
python tools/split_jds.py -i pasted.txt -o documents/zh/inbox
python tools/tracker.py import-jobs documents/zh/inbox/jobs_stub.json
python tools/tracker.py funnel
python tools/tracker.py rank && python tools/tracker.py day-plan
```

## [0.12.0] — 2026-07-17

### 短名单丝滑

- **`tools/flow.py shortlist`**：薄编排 `import-jobs → rank → day-plan`（不重写业务）
- **import 硬化**：缺 company 时打印列名 + Boss/门户字段别名提示
- **`expected_salary` 列** + `list --salary-flag` / `day-plan --expected-salary`（✅/⚠️/❌）
- **轻量语料 IDF**：`config/idf.default.json` 缓解 n=2 动态 IDF 退化（可 `config/idf.json` 覆盖）
- **semi**：剪贴板失败时按 OS 给出排障提示；强调不代点发送

```bash
python tools/flow.py shortlist --jobs jobs.json --track internet --limit 3
python tools/tracker.py list --open-only --salary-flag --expected-salary '25-40K'
```

## [0.11.0] — 2026-07-17

### 今天投谁（体验 + 管道）

- **`tracker day-plan`**：面试 → 建议跟进 → 今日 top N 条 `to_apply`（默认可带匹配分）
- **`tracker rank`**：对 `to_apply`（可改 `--status`）批打分排序；可选 `--write-fit` 写回 `fit_rating`
- 需本地 `cv_file` + `source`（JD 文件）；纯 URL 会标 unscored 并提示先落盘

### 匹配

- **`--track`**：`internet|soe|foreign|civil|freshgrad` 叠加赛道同义词簇  
  （见 `config/synonyms.default.json` → `tracks`）
- **`match_resume batch`**：JSON manifest 多对简历/JD 批打分（CI / 外部编排）

### 看板

- HTML **状态 / 城市筛选**（纯前端，无服务端）
- 城市分布 chips；文案链到 `day-plan` / `rank`

### 工程

- 黄金回归：`tests/test_golden_v011.py`（薪资、同义词、batch、day-plan、rank、filter）

## [0.10.0] — 2026-07-17

### 决策层（零爬虫 / 零 embedding）

- **期望薪资 vs JD 区间**：`tools/match_resume.py salary`；`report` 摘要增加「薪资对照」✅/⚠️/❌  
  - 期望来源：`--expected-salary` 或 `CLAUDE.zh.md` 的「薪资期望」  
  - JD 本地正则解析（`25-40K`、`30-50万/年`、面议等）  
  - 偏低时可提示 `tracker skipped --skip-reason salary_low`
- **同义词表**：`config/synonyms.default.json`（高并发↔大流量、微服务↔分布式架构 …）  
  - 可选本地覆盖 `config/synonyms.json`（gitignore）  
  - 原文表面形式 + token 双路径，减少 false miss  
  - `--no-synonyms` / `--synonyms path` 可调试

### 搜岗 → 追踪

- **`tracker import-jobs`**：JSON / NDJSON / CSV 批量入库，默认 `to_apply`，按 company+role+channel 去重  
- 样例：`examples/demo/jobs_sample.json`

### 投递闭环与验证信号

- **`skip_reason` 列** + `tracker skip-stats`（样本≥10 且单一原因≥40% 提示 Phase 2）  
- **`/outcome`** 支持 skipped、国内路径、飞轮引导；`update --notes-append`  
- **`/apply-zh`** Step 7C 不投记原因；Step 8 串联 outcome / skip-stats  
- Issue 模板：**我在用** / **痛点多选**  
- README 用户故事 + 公开路线「验证期」

### Demo

- 看板含不投信号；`skip_stats.txt` / `import_jobs.txt` / `salary_compare.txt`  
- `bash scripts/demo.sh` 覆盖匹配 + 薪资 + 导入 + tracker

### 其它

- `skill.json` → 0.10.0  
- 单测扩展：tracker import/skip、match 同义词与薪资、demo 脚本  

## [0.9.x] — 2026-07

- 闭环收尾：`/apply-zh` 确认写 tracker、看板待办、city/salary 列  
- 冷静 UX 文案、投递三档 `apply_assist`、Typst PDF 等（见 git log）
