# Changelog

本仓库遵循 [语义化版本](https://semver.org/lang/zh-CN/) 的宽松约定。  
**1.0.0** 起：默认国内闭环能力视为稳定；破坏性变更会升主版本或在条目标明。

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
