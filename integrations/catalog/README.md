# 可选集成目录（Phase 3 · 非核心 skill 面）

> **定位**：自托管 / 重依赖 / 平台专属 / 许可证敏感 的**参考说明**，不是开箱 agent 工具。  
> Agent 核心面与默认可跑路径见 [`ARCHITECTURE.zh.md`](../../ARCHITECTURE.zh.md) 与 [`README.zh.md`](../../README.zh.md)。

本目录的每个子目录含 `SKILL.md`，frontmatter 强制字段（由 `tools/lint_skill_surface.py` 校验）：

| 字段 | 含义 |
|------|------|
| `optional: true` | 非核心 |
| `tier: catalog` | 目录层级 |
| `setup_cost` | `low` / `medium` / `high` / `methodology_only` |
| `requires` | 真实依赖 |
| `os` | 操作系统约束 |
| `default_alternative` | **默认请用**的本仓库路径 |
| `upstream` / `license_note` | 上游与许可 |

## 成本一览（决策用）

| 条目 | 成本档 | OS | 关键依赖 | 预估首次搭建 | 默认请用（本仓库） |
|------|--------|-----|----------|--------------|-------------------|
| **resume-match/** | high | any | embedding 百 MB + Streamlit/UV | 20–60 min + 下载 | `python tools/match_resume.py` |
| **resume-build/** | medium | any | Docker 或 SaaS | 30–120 min | `/apply-zh` → `documents/zh/*.md` 任意导出 |
| **interview-mock/** | high | any | **Java 18 + MySQL + Redis**（微服务） | 2–6 h | `/interview` + `07-interview-prep.md` |
| **salary-negotiate/** | methodology_only | n/a | 上游**未声明许可证** | 0（只读） | 画像期望薪资 + 人工谈薪；**勿复制源码** |
| **referral-outreach/** | low | any | pip CLI + API key | 15–30 min | 手写内推话术 + `tracker.py` 记一笔 |
| **job-alert/** | medium | **macOS only** | Apple Mail → Reminders | 30–90 min | 系统日历/提醒 + `/outcome` |
| **boss-agent-cli/** | medium | any | 上游 MIT CLI（uv/patchright） | 15–45 min | `normalize_job_export` + 粘贴 JD；**投递仍 manual** |

### 另：不再作为默认的外挂

| 能力 | 曾指向 | 现状 |
|------|--------|------|
| 投递看板 | Gsync/jobsync（Docker） | **默认** `tools/tracker.py` + CSV；jobsync 可自行部署，不进 catalog 技能名 |
| 神经匹配 UI | Resume Matcher 全量 | catalog `resume-match/`；默认本地 TF–IDF |

## 为什么必须留在 catalog

1. **只有 SKILL.md、无本仓库代码** → 放进 `.agents/skills/` 会让 agent 误判为可执行工具。  
2. **搭建成本与目标用户错位**（普通求职者不会先装 Java 微服务）。  
3. **合规**：禁商用 / 未声明许可证 / 平台 ToS — 必须显式标注，不能 internally「假装已集成」。

## 核心闭环（请先跑通，再考虑上表）

```text
python tools/install_domestic_search.py install-boss   # 或 install-get-jobs
/setup-zh
搜岗 → /apply-zh <岗位描述>     # 含 match_resume 质量报告
手动投递
python tools/tracker.py add|list|dashboard
/outcome <company>
```

## 使用方式（若坚持自托管）

1. 读对应子目录 `SKILL.md` 的**真实搭建成本**表与合规段。  
2. 自行 clone 上游；**本仓库不 vendor、CI 不启服务**。  
3. 产物路径可记入 `job_search_tracker.csv`（`tools/tracker.py`）。  
4. 成功后也**不要**把上游二进制塞回 `.agents/skills/`，以免破坏 skill 面 allowlist。

## 治理与 CI

```bash
python tools/lint_skill_surface.py   # 核心 allowlist + catalog 元数据
python tools/lint_zh_refs.py
```

新增可选集成时：

1. 只加在 `integrations/catalog/<name>/`  
2. 填齐 frontmatter 字段 + 非核心横幅  
3. 更新本 README 成本表与 `tools/lint_skill_surface.py` 的 `CATALOG_ENTRIES`  
4. **禁止**在未交付可跑代码前加入 `.agents/skills/`

## 合规（总则）

- 默认**不自动投递**。  
- `get_jobs` 禁商用；`boss-cli` 上游许可证未声明；`salary-negotiate` 上游未声明许可。  
- 个人求职数据本地优先，遵守 PIPL。
