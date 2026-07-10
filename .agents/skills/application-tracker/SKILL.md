---
name: application-tracker
version: 2.0.0
description: >
  本地投递状态追踪与求职看板。以 job_search_tracker.csv 为权威源，通过
  tools/tracker.py（stdlib：CSV / 可选 SQLite / 单文件 HTML）读写，零 Docker。
  触发词：投递追踪、申请状态、面试进度、求职看板、track application、offer 管理、tracker。
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

表头（与 `/outcome` 一致）：

```
date,company,sector,role,role_type,channel,status,contact_person,fit_rating,notes,cv_file,cover_letter_file,source
```

## 安装

无第三方依赖（Python 3.10+ 标准库）：

```bash
python tools/tracker.py init
python tools/tracker.py --help
```

## 常用命令

```bash
# 投递后记一笔
python tools/tracker.py add \
  --company 示例科技 --role 后端工程师 \
  --channel Boss直聘 --status applied \
  --source "https://…" \
  --cv documents/zh/resume_示例科技.md \
  --cover documents/zh/da-zhaohu_示例科技_后端.md

# 列表 / 仅进行中
python tools/tracker.py list
python tools/tracker.py list --open-only
python tools/tracker.py list --status interview

# 状态更新
python tools/tracker.py update --company 示例科技 --role 后端工程师 --status interview

# 详情
python tools/tracker.py show --company 示例科技

# 单文件 HTML 看板（浏览器打开）
python tools/tracker.py dashboard

# 导出 SQLite（可选查询）
python tools/tracker.py export --format sqlite
```

## 工作流（agent 编排）

1. 用户完成 `/apply-zh` 或 `/da-zhaohu` 并**手动**在 App 内投递。
2. 调用 `tracker.py add` 写入公司 / 岗位 / 渠道 / 状态 / 材料路径。
3. 面试 / offer / 拒信：优先跑 **`/outcome`**（会更新 CSV + 归档 `documents/applications/`）；
   或直接用 `tracker.py update --status …`。
4. 需要总览时：`tracker.py list --open-only` 或 `dashboard`。

## 合规与边界

- CSV / HTML / SQLite 含个人求职数据，已在 `.gitignore`（`job_search_tracker.csv` 等），勿提交。
- 状态如实维护，不虚构面试 / offer。
- 本工具不连接招聘平台、不自动投递。

## 与其他能力的配合

- 检索 → `bosszhipin-search` / `domestic-jobs-search`（先 `install_domestic_search.py`）
- 中文材料 → `/apply-zh`、`/da-zhaohu`
- 结果归档 → `/outcome`
- 重型可选集成 → `integrations/catalog/`（模拟面试 / Reactive-Resume / 谈薪方法论等）
