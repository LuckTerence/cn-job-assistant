# Changelog

本仓库遵循 [语义化版本](https://semver.org/lang/zh-CN/) 的宽松约定：  
`0.x` 阶段允许在次版本加入能力；破坏性变更会在条目里标明。

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
