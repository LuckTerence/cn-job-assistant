<h1 align="center">CN Job Assistant · 国内 AI 求职助手</h1>

<p align="center">
  <strong>本地优先 · 按岗位描述定制 · 可量化 · 投递方式你选</strong><br>
  搜岗 → 改简历/话术 → 打分 → <strong>手动 / 半自动 / 全自动（默认手动）</strong> → 记进度
</p>

<p align="center">
  <a href="https://github.com/LuckTerence/cn-job-assistant/actions/workflows/ci.yml"><img src="https://github.com/LuckTerence/cn-job-assistant/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT">
  <img src="https://img.shields.io/badge/market-China-red.svg" alt="China">
  <img src="https://img.shields.io/badge/auto--apply-No-lightgrey.svg" alt="No auto apply">
  <img src="https://img.shields.io/badge/python-3.10+-green.svg" alt="Python">
  <img src="https://img.shields.io/badge/version-1.0.1-blue.svg" alt="1.0.1">
</p>

<p align="center">
  <a href="./docs/QUICKSTART.zh.md"><strong>15 分钟上手</strong></a> ·
  <a href="#三分钟上手"><strong>三分钟上手</strong></a> ·
  <a href="#它解决什么问题"><strong>解决什么问题</strong></a> ·
  <a href="./docs/RELEASE-1.0.zh.md"><strong>1.0 发版说明</strong></a> ·
  <a href="./docs/AGENT_PROMPT.zh.md"><strong>Agent 提示词</strong></a> ·
  <a href="./ARCHITECTURE.zh.md"><strong>架构</strong></a>
</p>

<p align="center">
  <em>English:</em> A local-first AI job-search <strong>framework</strong> for the Chinese market
  (Boss Zhipin / 51job / Liepin …). Not a SaaS, not a mass auto-apply bot.
  Fork → fill profile → generate tailored materials → you submit manually.
</p>

---

## 新人从这里开始（1.0）

| 步骤 | 命令 / 动作 | 时间 |
|------|-------------|------|
| 1. 验证本机 | `make check` | ~2 min |
| 2. 看演示 | `bash scripts/demo.sh` → 打开 `examples/demo/output/job_search_tracker.html` | ~1 min |
| 3. 填画像 | Agent：`/setup-zh`（**粘贴旧简历最快**；写上**期望薪资**） | ~5 min |
| 4. 第一岗 | Agent：`/apply-zh` + 粘贴 JD → 拿 **PDF + 话术 + 匹配摘要** | ~5 min |
| 5. 投递 | App 里上传 PDF、自己点发送 → `/outcome` 或 `tracker` 记状态 | — |

详细分步、无 slash 时的提示词、卡点表：  
**[docs/QUICKSTART.zh.md](./docs/QUICKSTART.zh.md)** · **[docs/AGENT_PROMPT.zh.md](./docs/AGENT_PROMPT.zh.md)**

```bash
git clone https://github.com/LuckTerence/cn-job-assistant.git
cd cn-job-assistant && make check
```

用起来后请点一下 [🙋 我在用](https://github.com/LuckTerence/cn-job-assistant/issues/new?template=using.yml)（脱敏），这是 1.x 迭代的主要信号来源。

---

## 它解决什么问题

国内求职者常见的真实痛点：

| 痛点 | 市面上常见做法 | 本仓库怎么做 |
|------|----------------|--------------|
| 一份简历群发 N 家 | 批量自动投 / 同文案 | **按岗位描述定制**中文简历 + Boss 打招呼话术 |
| 不知道改得好不好 | 凭感觉 | **本地打分**：关键词 hit/miss + 匹配分（无模型下载） |
| 投了就忘 | 表格手记 / 重型 Docker 看板 | **零依赖 Tracker**（CSV + HTML 看板） |
| 工具要登录云、简历外传 | 各类在线 AI 简历站 | **本地优先**，个人数据 gitignore |
| 全自动触发风控 | 各种「一键海投」默认开 | **默认手动**；半自动/全自动由你显式打开并确认风险 |

> 这不是又一个「帮你海投」的脚本合集，而是 **Agent 可读可跑的求职工作流**。

---

## 30 秒看懂闭环（1.0）

```text
  粘贴/搜岗 JSON          /setup-zh 画像
         │                      │
         ▼                      ▼
  split_jds / import-jobs   母版简历
         │                      │
         └──────────┬───────────┘
                    ▼
         flow shortlist · rank · day-plan · funnel
                    │
                    ▼
              /apply-zh → PDF + 话术 + 匹配摘要
                    │
                    ▼
         你在 App 手动/半自动投（默认不代点发送）
                    │
                    ▼
         tracker / /outcome · skip-stats · dashboard
```

**开箱可跑（不装 Docker、不拉 embedding）**：

1. `bash scripts/smoke_cn.sh` / `make check` — **1.0 门禁**  
2. `tools/flow.py shortlist` · `tracker day-plan/rank/funnel`  
3. `/setup-zh` · `/apply-zh` · `/outcome`  
4. `match_resume`（同义词 · 真缺口 · 薪资对照）· `split_jds`  
5. `apply_assist` 投递三档（默认 manual）

---

## 先看一眼产出（无需填简历 / 无需登录）

clone 后一条命令，离线生成样例（虚构数据）：

```bash
git clone https://github.com/LuckTerence/cn-job-assistant.git
cd cn-job-assistant
bash scripts/demo.sh
# 或: make demo
```

```bash
open examples/demo/output/job_search_tracker.html   # macOS 打开投递看板
```

| 演示产物 | 路径 |
|----------|------|
| **可投递 PDF 简历** | [`examples/demo/output/resume_星云科技.pdf`](./examples/demo/output/resume_星云科技.pdf) |
| 匹配摘要 | [`examples/demo/output/match_brief_zh.txt`](./examples/demo/output/match_brief_zh.txt) |
| HTML 投递看板 | [`examples/demo/output/job_search_tracker.html`](./examples/demo/output/job_search_tracker.html) |
| 不投原因分布 | [`examples/demo/output/skip_stats.txt`](./examples/demo/output/skip_stats.txt) |
| 今日进度 | [`examples/demo/output/tracker_today.txt`](./examples/demo/output/tracker_today.txt) |
| 互联网 / 国企 PDF | `examples/demo/output/resume_互联网样例.pdf` · `resume_国企样例.pdf` |

样例说明：[examples/demo/README.md](./examples/demo/README.md) · Agent 安装：[docs/INSTALL.agents.zh.md](./docs/INSTALL.agents.zh.md)

---

## 一个用户故事（虚构，但流程真实）

> **阿哲**，3 年 Java，目标杭州后端。不想把简历丢进在线 SaaS，也不想一键海投被封号。

1. `bash scripts/demo.sh` —— 先看懂产出长什么样（PDF / 匹配摘要 / 看板）  
2. Agent 里 `/setup-zh`，粘贴旧简历抽出画像  
3. Boss 上看到「星云科技 · 后端」→ `/apply-zh` 粘贴岗位描述  
4. 拿到 **定制 PDF + 打招呼话术 + 人话匹配摘要**；在 App 里自己点发送  
5. Agent 问他记不记 tracker：选 `applied`；不合适的岗选 `skipped` + 原因（如 `salary_low`）  
6. 每天 `python tools/tracker.py today` 看面试 / 跟进；面试来了跑 `/outcome`  

你要复制的不是「阿哲」的简历，而是这条**可重复的闭环**。  
真实在用的话，欢迎开一个 [🙋 我在用](https://github.com/LuckTerence/cn-job-assistant/issues/new?template=using.yml) Issue（脱敏即可）。

---

## 投递三档（选择权在你）

| 模式 | 做什么 | 谁点发送 | 怎么开 |
|------|--------|----------|--------|
| **manual**（默认） | 生成材料，你在 App 里投 | 你 | 不用改，开箱即是 |
| **semi** 半自动 | 打开岗位页 + 复制话术到剪贴板 | 仍是你（最后一下） | `python tools/apply_assist.py set-mode semi` |
| **auto** 全自动 | 经 boss-cli 等代发/打招呼 | 脚本 | 见下方，**高风险** |

```bash
python tools/apply_assist.py explain    # 三档说明
python tools/apply_assist.py status     # 当前模式
python tools/apply_assist.py init-config
```

**半自动示例**（推荐多数人用这个「好用」档）：

```bash
python tools/apply_assist.py semi \
  --url 'https://www.zhipin.com/job_detail/…' \
  --text-file documents/zh/da-zhaohu_某某_后端.md \
  --company 某某 --role 后端
# 然后你在打开的页面里粘贴并自己点发送
```

**全自动**必须同时满足：配置 `mode: auto`、三项风险确认为 true、命令行 `--i-understand-ban-risk`，真正发送再加 `--execute`。默认 dry-run 只打印命令。可能封号，后果自负。

> **能力边界**：主流 `boss greet <id>` 通常只有平台默认招呼；**定制话术请用 semi**。  
> 若 `auto-greet --text-file …` 探测到 boss-cli 不支持自定义参数，会**直接拒绝**（不再假装已传入）。  
> 多 ID：`--security-id id1,id2`，数量受配置 `auto.max_batch` 限制。

```bash
python tools/apply_assist.py set-mode auto          # 需输入 YES
# 编辑 config/apply_mode.yaml 把 risk_acknowledgement 全改 true
python tools/apply_assist.py auto-greet --security-id <id> --i-understand-ban-risk
python tools/apply_assist.py auto-greet --security-id <id> --i-understand-ban-risk --execute
```

示例配置：[`config/apply_mode.example.yaml`](./config/apply_mode.example.yaml)（复制为 `config/apply_mode.yaml`，后者 gitignore）。


## 三分钟上手（真实求职）

> 更细的 15 分钟版见 [docs/QUICKSTART.zh.md](./docs/QUICKSTART.zh.md)。

### 0. 前置

- Python **3.10+**
- AI Agent（Claude Code / Cursor / 国产模型等，见 [MODELS.zh.md](./MODELS.zh.md)）

```bash
git clone https://github.com/LuckTerence/cn-job-assistant.git
cd cn-job-assistant
make check          # 推荐：单测 + 离线冒烟
# 或: bash scripts/demo.sh
```

### 1. （可选）装 Boss 搜岗

```bash
python tools/install_domestic_search.py install-boss
python tools/install_domestic_search.py status
```

> 个人求职用途；上游许可证与平台协议自负。智联/猎聘等见 `install-get-jobs`（禁商用）。

### 2. 画像

```text
/setup-zh
```

粘贴旧简历最快；**务必写入期望薪资**（如 `25-40K`）。

### 3. 一岗材料

```text
/apply-zh
（粘贴岗位全文或链接）
```

产出在 `documents/zh/`：**PDF 简历**、话术、匹配摘要（真缺口 / 同义词 / 薪资对照）。  
Agent 会询问后写入 tracker（默认 `to_apply`，已投再说 `applied`）。

```bash
# 可选：单独重导 PDF
python tools/export_resume_pdf.py -i documents/zh/resume_公司.md
```

### 4. 投递与日常

App 内上传 PDF、**自己点发送**。然后：

```bash
python tools/tracker.py day-plan --expected-salary '25-40K'
python tools/tracker.py funnel
python tools/tracker.py dashboard
# 面试/拒信/不投：/outcome
```

一批岗：

```bash
python tools/split_jds.py -i pasted.txt -o documents/zh/inbox
python tools/flow.py shortlist --jobs documents/zh/inbox/jobs_stub.json --track internet
```

---

## 你得到什么（诚实清单）

| ✅ 已落地 | 说明 |
|----------|------|
| 一键 Demo | `bash scripts/demo.sh` / 预生成看板与摘要 |
| 中文简历分赛道模板 + **双赛道样例** | 互联网 vs 国企产出对比 |
| **可投递 A4 PDF** | `export_resume_pdf.py`：优先 **Typst** 模板，回退 Chrome/pandoc（见 `docs/resume-pdf-reuse.zh.md`） |
| Boss 打招呼 + 正式求职信 | `/da-zhaohu` · `/apply-zh` |
| 匹配打分 + **人话一页摘要** | `report --zh-only`；禁止虚构写进摘要 |
| **同义词表** | `config/synonyms.default.json`；减少「明明会却 miss」 |
| **期望 vs JD 薪资** | `match_resume salary` / report 摘要；零爬虫 |
| 质量飞轮 | `match_resume.py diff` 对比 v1→v2 |
| Tracker + **每日工作台** | `tracker.py today` / `suggest-add` 挂钩 apply-zh |
| **不投原因（skip_reason）** | `skipped` 必填枚举；`skip-stats` 看分布（Phase 1 信号） |
| **搜岗 → tracker** | `import-jobs`：JSON/NDJSON/CSV 批量入库，默认 `to_apply` + 去重 |
| **今日计划 / 批打分** | `day-plan` · `rank`（to_apply 按匹配分排序） |
| **短名单编排** | `python tools/flow.py shortlist --jobs …` |
| **赛道同义词 + 语料 IDF** | `--track` · `config/idf.default.json` |
| **薪资旗标** | `list --salary-flag` · 列 `expected_salary` |
| **投递漏斗** | `tracker funnel` · 看板卡片 |
| **粘贴多 JD** | `split_jds.py` → import → rank |
| `/setup-zh` 粘贴旧简历 | 冷启动减负 |
| 国产模型友好 | 见 MODELS.zh.md |
| Issue 模板 | 赛道反馈 + **我在用** + **痛点多选** |
| CI | demo 脚本 + tracker / match / lint |

| ⚠️ 明确不做 / 降级 | 说明 |
|-------------------|------|
| 默认就全自动海投 | 默认 **manual**；auto 须配置 + 风险确认 + `--execute` |
| 假装重依赖也能开箱 | 见 [integrations/catalog](./integrations/catalog/README.md) |
| 保证拿到 offer | 匹配分只是关键词对齐，不是录用预测 |

---

## 和别人有什么不同

| | 在线 AI 简历 / 海投工具 | 本仓库 |
|--|------------------------|--------|
| 数据 | 多在云端 | **本地仓库**，敏感文件 gitignore |
| 投递 | 常主打自动/批量 | **人审后手动投** |
| 中国市场 | 大多不做或很浅 | **主战场**（Boss 话术、分赛道简历） |
| 可扩展 | 封闭产品 | Agent **skill + 命令**，可改可 fork |
| 重功能 | 一股脑塞进主路径 | 核心闭环短；可选栈标成本 |

对标调研与许可证笔记（工程向，非入门必读）：[docs/competitive-research.zh.md](./docs/competitive-research.zh.md)

---

## 适合谁 · 不适合谁

**适合**

- 正在用 AI 写代码的 Agent 用户，希望求职也同一套工作流  
- 要投 **Boss / 智联 / 猎聘** 等，需要**按岗位描述改中文材料**  
- 在意隐私、不想简历默认上传 SaaS  
- 接受「工具辅助 + 自己投递」而不是全自动黑盒  

**不适合**

- 想一键海投、完全不管内容质量  
- 不想装 Python / 不用任何 AI Agent  
- 需要 HR 级 ATS 商业服务（请用 Jobscan 等商业产品）  

---

## 文档地图

| 文档 | 什么时候看 |
|------|------------|
| **本页** | 了解产品、上手 |
| [ARCHITECTURE.zh.md](./ARCHITECTURE.zh.md) | 核心 skill 面 vs 可选 catalog |
| [MODELS.zh.md](./MODELS.zh.md) | DeepSeek / 智谱 / 通义 … 怎么接 |
| [integrations/catalog/README.md](./integrations/catalog/README.md) | 模拟面试 / Reactive-Resume 等真实成本 |
| [SETUP.md](./SETUP.md) | 上游英文 / LaTeX 环境 |
| [docs/competitive-research.zh.md](./docs/competitive-research.zh.md) | 多轮对标与决策记录 |
| [docs/resume-pdf-reuse.zh.md](./docs/resume-pdf-reuse.zh.md) | 简历 PDF 开源复用（10 项目） |
| [CHANGELOG.md](./CHANGELOG.md) | 版本变更与发版说明 |

---

## 产品路线（公开）

| 阶段 | 状态 | 内容 |
|------|------|------|
| 工程 Phase 1–3 | ✅ | 搜岗安装器 · 匹配 · Tracker · Catalog 治理 · Demo |
| **投递三档** | ✅ | `apply_assist.py`：manual / semi / auto（选择权在用户） |
| **闭环收尾** | ✅ | `/apply-zh` 确认写 tracker · 看板待办 · city/salary 列 |
| **验证期** | 🔄 | 用户故事 · Issue 反馈 · `skip_reason` / `skip-stats` · `/outcome` 飞轮 |
| **搜岗入库** | ✅ | `tracker import-jobs`（搜岗 JSON → `to_apply`，去重） |
| **决策层** | ✅ | 同义词表 + 期望 vs JD 薪资（本地解析） |
| **0.11 今天投谁** | ✅ | `day-plan` · `rank` · 看板筛选 · `--track` |
| **0.12 短名单丝滑** | ✅ | `flow shortlist` · 期望薪资列/旗标 · 语料 IDF · import 字段提示 |
| **0.13 决策可信** | ✅ | `funnel` · 真缺口/同义词分列 · `split_jds` |
| **1.0 可靠闭环** | ✅ | `smoke_cn` 门禁 · [发版说明](./docs/RELEASE-1.0.zh.md) · 能力面稳定 |
| **1.x 信号驱动** | ⏸ | embedding catalog / 本地 Web / 社区规模 —— Issue 痛点票 |
| **暂缓** | — | 自研爬虫、强制 SaaS、默认海投、未验证就上 embedding |

---

## 合规（写进产品，不是附录）

- **默认 manual**（不自动点发送）；semi / auto 由用户显式选择，auto 须风险确认  
- 简历与投递记录尽量留在本地，遵守 **PIPL**  
- 不要为刷匹配分虚构经历  
- boss-cli / get_jobs 等许可证与平台协议以各自仓库与平台为准；个人求职自负风险  

---

## 致谢与许可

基于 [MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search)（MIT）的国内适配分支。  
保留上游版权声明；本分支新增中文适配与本地工具同样以 **MIT** 发布。详见 [NOTICE](./NOTICE)、[LICENSE](./LICENSE)。

上游英文/丹麦门户能力仍可用；国际流程见历史英文文档结构与 `SETUP.md`。

---

<p align="center">
  如果这个仓库帮你少改一个周末的简历 / 少漏一次面试跟进，<br>
  请点一个 <strong>⭐ Star</strong> —— 这是开源推广里最便宜、也最有效的一票。
</p>

<p align="center">
  <a href="https://github.com/LuckTerence/cn-job-assistant">github.com/LuckTerence/cn-job-assistant</a>
</p>
