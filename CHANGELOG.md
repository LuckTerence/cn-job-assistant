# Changelog

本仓库遵循 [语义化版本](https://semver.org/lang/zh-CN/) 的宽松约定：  
`0.x` 阶段允许在次版本加入能力；破坏性变更会在条目里标明。

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
