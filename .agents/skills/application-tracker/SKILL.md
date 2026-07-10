---
name: application-tracker
version: 1.0.0
description: >
  投递状态追踪与求职看板。本技能复用开源项目 jobsync
  （Gsync/jobsync，MIT，自托管 Job Application Tracker + AI 职业助手）作为"投递后状态管理"底座，
  而非自行实现追踪数据库。触发词：投递追踪、申请状态、面试进度、求职看板、track application、offer 管理。
context: fork
allowed-tools: Read, Glob, Grep, WebFetch, WebSearch, AskUserQuestion, Bash(docker*), Bash(git*)
---

# 投递追踪技能（复用 jobsync）

> **不要重复造轮子**：投递后的状态追踪（已投 / 面试中 / offer / 拒信）、可视化看板、
> 与 AI 职业助手，已被成熟开源项目
> [Gsync/jobsync](https://github.com/Gsync/jobsync)（**MIT**，719★，自托管）完整实现。
> 本技能直接复用它做"状态管理"，不自行实现追踪库；本仓库 `job-application-assistant` 工作流
> 的"投递后闭环"段指向本技能作为状态追踪落点。

## 复用关系

| 能力 | 由谁实现 | 说明 |
|------|----------|------|
| 投递记录 | **jobsync** | 岗位 / 公司 / 渠道 / 状态（已投·面试·offer·拒）结构化存储 |
| 状态看板 | **jobsync** | 可视化追踪多岗位进度 |
| AI 职业助手 | **jobsync** | 基于已投数据给下一步建议 |
| 状态人工记录 | **本仓库** 工作流 | 用户手动维护，或由 job-alert 提醒驱动更新 |

## 技术要点（来自其 README，便于对接）

- **协议**：MIT（明确声明，可自托管 / 可改）。
- **形态**：TypeScript 自托管应用（含前端看板）；需本地/私有部署（Docker）。
- **数据**：投递数据存于自托管实例，优先私有，遵守 PIPL。

## 工作流（本技能如何编排）

1. 用户在 `job-application-assistant` 完成检索 / 简历 / 话术 / 手动投递。
2. 每完成一次投递，在自托管 **jobsync** 中记录岗位 + 状态（已投）。
3. 面试 / offer / 拒信等状态变化，由用户更新，或由 `job-alert` 的提醒驱动回填。
4. 用 jobsync 看板掌握整体进度，决定优先级（先面哪家中、哪家中需催跟进）。

## 安装与运行（摘要，以 jobsync 仓库为准）

```bash
git clone https://github.com/Gsync/jobsync.git
cd jobsync
# 自托管部署（详见其 README / docker 配置）
```

> 注：jobsync 为需自托管的应用，精确部署步骤以其仓库文档为准；本技能不臆造部署命令。
> 如不愿自托管，本分支此前多轮仅将其标记为"可选参考"，本轮正式接入为状态追踪落点。

## 与仓库内置 `job_search_tracker.csv` 的关系（定位澄清）

本仓库的命令链（`/scrape`、`/rank`、`/outcome`、`/interview`、`/upskill`）维护一份
`job_search_tracker.csv`，作为**命令链内部状态机的 source of truth**：去重
（`/scrape` 的 `seen_jobs.json` + `/rank` 幂等排除）、归档（`/outcome` 写入且永不覆盖）、
面试匹配与复盘都依赖它。这是轻量、本地、零依赖的进度账本。

**jobsync 是可选的外部看板，不是同一份数据。** 两者定位不同：

| 追踪器 | 角色 | 数据形态 | 适用 |
|--------|------|----------|------|
| `job_search_tracker.csv` | 命令链内部状态机（**权威源**） | 本地 CSV，由命令自动读写 | 跑通 `/scrape→/rank→/apply→/outcome` 流水线 |
| jobsync | 可选可视化看板 / AI 助手 | 自托管 Web 应用（Docker） | 想要图形化进度、AI 下一步建议 |

**如何选 / 互通：**
- **二选一即可**：只跑命令链就用 CSV，不要两份进度互相打架；想要图形界面再上 jobsync。
- **CSV → jobsync（手动镜像）**：每完成一次投递 / 状态变化，在 jobsync 中同样记一笔
  （公司 / 岗位 / 渠道 / 状态），保持两者一致。命令链**不会**自动同步到 jobsync。
- **避免歧义**：以 `job_search_tracker.csv` 为权威；jobsync 视为其可视化镜像，不双写造成冲突。

## 合规与边界

- 投递含敏感求职数据，优先自托管 / 私有部署，遵守 PIPL。
- 状态由用户如实维护，不虚构面试 / offer 进度。
- AI 建议仅供参考，最终决策由用户作出。

## 与其他技能的配合

- 检索 → `bosszhipin-search` / `domestic-jobs-search`
- 匹配评估 → `resume-match`（Resume Matcher）/ `04-job-evaluation.md`
- 简历 → `resume-build`（Reactive-Resume）
- 投递后提醒 → `job-alert`（offercatcher）
- 谈薪 / 内推 → `salary-negotiate` / `referral-outreach`
