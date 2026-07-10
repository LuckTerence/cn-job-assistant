# 可选集成目录（非核心 skill 面）

> **定位**：这里的条目是「自托管 / 重依赖 / 平台专属」的可选集成说明，**不是**开箱可跑的 agent 技能。
> Agent 的核心 skill 面只保留：海外 6 个 CLI + 国内搜岗（boss-cli / get_jobs）+ 本地 Tracker。
> 中文简历/话术生成走 `.claude/commands` 的 `/apply-zh` `/da-zhaohu`（prompt 工作流，已落地）。

## 为什么移出 `.agents/skills/`

原先 9 个国内 skill 中有 6 个只有 `SKILL.md`、0 代码，却带 `allowed-tools`，会让 agent 误判为「可执行工具」，
实际只能「建议你去 clone 外部仓库」。为避免文档承诺 > 可跑面，这些条目降级到本目录。

## 目录与真实搭建成本

| 条目 | 上游 | 协议 | 真实成本 | 建议 |
|------|------|------|----------|------|
| `resume-match/` | srbhr/Resume-Matcher | Apache-2.0 | embedding 权重（百 MB）+ Streamlit | 可选重型；**默认**用核心 `tools/match_resume.py` |
| `resume-build/` | AmruthPillai/Reactive-Resume | MIT | Docker 自托管 或 官方 SaaS | 可选；`/apply-zh` 已产出 Markdown 草稿 |
| `interview-mock/` | GodLeaveMe/AuraInterviewer | MIT | **Java 18 + MySQL + Redis** 微服务 | 可选；日常用 `/interview` + `07-interview-prep.md` |
| `salary-negotiate/` | Ssupercoder/Salary-Negotiation-Skill | 未声明 | LLM Agent + 可选本地模型 | **仅方法论**；勿复制未授权源码 |
| `referral-outreach/` | quionie/outreach-ai | MIT | `pip` CLI + API key | 可选；生成文案后手动发送 |
| `job-alert/` | NissonCX/offercatcher | MIT | **仅 macOS**（Apple Mail → Reminders） | 可选；非平台监控器 |

## 核心闭环（请用这些，不要先装上表）

```text
1. python tools/install_domestic_search.py install-boss   # 或 install-get-jobs
2. /setup-zh
3. 搜岗（boss search / get_jobs）→ 复制 JD
4. /apply-zh <JD>   # 内含 match_resume 质量报告
   # 或手动：python tools/match_resume.py report --resume … --jd … --cover …
5. 手动在 App 内投递
6. python tools/tracker.py add --company … --role … --channel Boss直聘
7. python tools/tracker.py dashboard   # 本地 HTML 看板
8. /outcome <company>                  # 状态变更时
```

jobsync / AuraInterviewer 等重应用**不再**作为默认 Tracker / 模拟面试路径。

## 使用方式

1. 阅读子目录内原 `SKILL.md`（保留完整安装说明与合规边界）。
2. 自行 clone/部署上游；本仓库不 vendoring 其代码、不在 CI 中跑其服务。
3. 部署成功后，可把产物路径记入 `job_search_tracker.csv`（`tools/tracker.py`）。

## 合规

- 本仓库默认**不自动投递**。
- 各上游许可证与平台 ToS 以各自仓库为准；`get_jobs` 禁商用；`boss-cli` 上游未声明许可证。
- 个人求职数据优先本地，遵守 PIPL。
