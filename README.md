<p align="center">
  <img src="docs/assets/demo-loop.gif" alt="CN Job Assistant demo loop" width="720">
</p>

<h1 align="center">CN Job Assistant · 国内 AI 求职助手</h1>

<p align="center">
  <strong>本地优先 · 按 JD 定制 · 可量化 · 不自动投递</strong><br>
  把你的 AI Agent 变成「搜岗 → 改简历 / 打招呼 → 打分 → 手动投 → 追踪」的求职工作台
</p>

<p align="center">
  <a href="https://github.com/LuckTerence/cn-job-assistant/actions/workflows/ci.yml"><img src="https://github.com/LuckTerence/cn-job-assistant/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT">
  <img src="https://img.shields.io/badge/market-China-red.svg" alt="China">
  <img src="https://img.shields.io/badge/auto--apply-No-lightgrey.svg" alt="No auto apply">
  <img src="https://img.shields.io/badge/python-3.10+-green.svg" alt="Python">
</p>

<p align="center">
  <a href="#三分钟上手"><strong>三分钟上手</strong></a> ·
  <a href="#它解决什么问题"><strong>解决什么问题</strong></a> ·
  <a href="#和别人有什么不同"><strong>差异点</strong></a> ·
  <a href="./ARCHITECTURE.zh.md"><strong>架构</strong></a> ·
  <a href="./MODELS.zh.md"><strong>国产模型</strong></a>
</p>

<p align="center">
  <em>English:</em> A local-first AI job-search <strong>framework</strong> for the Chinese market
  (Boss Zhipin / 51job / Liepin …). Not a SaaS, not a mass auto-apply bot.
  Fork → fill profile → generate tailored materials → you submit manually.
</p>

---

## 它解决什么问题

国内求职者常见的真实痛点：

| 痛点 | 市面上常见做法 | 本仓库怎么做 |
|------|----------------|--------------|
| 一份简历群发 N 家 | 批量自动投 / 同文案 | **按 JD 定制**中文简历 + Boss 打招呼话术 |
| 不知道改得好不好 | 凭感觉 | **本地打分**：关键词 hit/miss + 匹配分（无模型下载） |
| 投了就忘 | 表格手记 / 重型 Docker 看板 | **零依赖 Tracker**（CSV + HTML 看板） |
| 工具要登录云、简历外传 | 各类在线 AI 简历站 | **本地优先**，个人数据 gitignore |
| 全自动触发风控 | 各种「一键海投」 | **默认不自动投递**，合规立场写进产品 |

> 这不是又一个「帮你海投」的脚本合集，而是 **Agent 可读可跑的求职工作流**。

---

## 30 秒看懂闭环

```text
  装搜岗工具          填画像            丢一份 JD
       │                │                  │
       ▼                ▼                  ▼
 install_domestic   /setup-zh      /apply-zh <JD>
       │                │                  │
       └────────────────┴──────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
     中文简历草稿    打招呼 / 求职信    匹配质量报告
   documents/zh/     documents/zh/    match_report.json
           │               │               │
           └───────────────┴───────────────┘
                           │
                           ▼
              你在 App 里手动投递（关键）
                           │
                           ▼
              tracker.py 记一笔 / /outcome 更新状态
```

**开箱可跑的 4 个本地组件**（不装 Docker、不拉百 MB 向量模型）：

1. `tools/install_domestic_search.py` — Boss / 多平台搜岗安装  
2. `/apply-zh` · `/da-zhaohu` — 中文简历与话术（Agent 命令）  
3. `tools/match_resume.py` — 匹配分 + 关键词命中/缺失  
4. `tools/tracker.py` — 投递追踪与 HTML 看板  

---

## 先看一眼产出（无需填简历 / 无需登录）

上方 GIF：**JD → 生成材料 → 打分 → Tracker**（约 30 秒循环）。  
clone 后一条命令，离线生成同样产物（虚构数据）：

```bash
git clone https://github.com/LuckTerence/cn-job-assistant.git
cd cn-job-assistant
bash scripts/demo.sh
# 或: make demo
```

```bash
open examples/demo/output/job_search_tracker.html   # macOS 看板
open docs/assets/demo-loop.gif                      # 动图
```

| 演示产物 | 路径 |
|----------|------|
| 循环动图 | [`docs/assets/demo-loop.gif`](./docs/assets/demo-loop.gif) |
| 中文人话摘要 | [`examples/demo/output/match_brief_zh.txt`](./examples/demo/output/match_brief_zh.txt) |
| 匹配报告 JSON | [`examples/demo/output/match_report.json`](./examples/demo/output/match_report.json) |
| HTML 投递看板 | [`examples/demo/output/job_search_tracker.html`](./examples/demo/output/job_search_tracker.html) |
| 今日工作台 | [`examples/demo/output/tracker_today.txt`](./examples/demo/output/tracker_today.txt) |
| 互联网 vs 国企 | [`examples/demo/tracks/`](./examples/demo/tracks/) |
| 质量飞轮 diff | [`examples/demo/output/match_diff_v1_v2.txt`](./examples/demo/output/match_diff_v1_v2.txt) |

样例说明：[examples/demo/README.md](./examples/demo/README.md) · Agent 安装：[docs/INSTALL.agents.zh.md](./docs/INSTALL.agents.zh.md)

---

## 三分钟上手（真实求职）

### 0. 前置

- Python **3.10+**
- 任意能读仓库 skills/commands 的 AI Agent  
  （Claude Code / Cursor / 支持 OpenAI 兼容 API 的国产模型 Agent 等，见 [MODELS.zh.md](./MODELS.zh.md)）

```bash
git clone https://github.com/LuckTerence/cn-job-assistant.git
cd cn-job-assistant
# 建议先: bash scripts/demo.sh
```

### 1. （可选）装 Boss 搜岗

```bash
python tools/install_domestic_search.py install-boss
python tools/install_domestic_search.py status
```

> 个人求职用途；boss-cli 上游许可证请自行确认。智联/猎聘等见 `install-get-jobs`（禁商用协议）。

### 2. 在 Agent 里初始化画像

```text
/setup-zh
```

### 3. 丢一份 JD，生成材料 + 打分

```text
/apply-zh
（粘贴 Boss/智联 JD 链接或全文）
```

会写入 `documents/zh/`：简历草稿、话术、JD 原文、**match_report_*.json**。

### 4. 你去 App 里手动投；回来记一笔

```bash
python tools/tracker.py init
python tools/tracker.py add \
  --company 示例科技 --role 后端 --channel Boss直聘 --status applied
python tools/tracker.py dashboard   # 浏览器打开 job_search_tracker.html
```

---

## 你得到什么（诚实清单）

| ✅ 已落地 | 说明 |
|----------|------|
| 一键 Demo | `bash scripts/demo.sh` / 动图 / 预生成看板 |
| 中文简历分赛道模板 + **双赛道样例** | 互联网 vs 国企产出对比 |
| Boss 打招呼 + 正式求职信 | `/da-zhaohu` · `/apply-zh` |
| 匹配打分 + **人话一页摘要** | `report --zh-only`；禁止虚构写进摘要 |
| 质量飞轮 | `match_resume.py diff` 对比 v1→v2 |
| Tracker + **每日工作台** | `tracker.py today` / `suggest-add` 挂钩 apply-zh |
| `/setup-zh` 粘贴旧简历 | 冷启动减负 |
| 国产模型友好 | 见 MODELS.zh.md |
| Issue 赛道模板 | 互联网 / 国企 / 校招反馈 |
| CI | demo 脚本 + tracker / match / lint |

| ⚠️ 明确不做 / 降级 | 说明 |
|-------------------|------|
| 默认自动投递 | 产品原则；第三方自动化需你自担风险 |
| 假装「18 个技能都可跑」 | 重依赖已进 [integrations/catalog](./integrations/catalog/README.md)，带**真实搭建成本** |
| 替你保证拿到 offer | 分数是启发式，不是录用预测 |

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
- 要投 **Boss / 智联 / 猎聘** 等，需要**按 JD 改中文材料**  
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

---

## 产品路线（公开）

| 阶段 | 状态 | 内容 |
|------|------|------|
| Phase 1 | ✅ | 搜岗安装器 + 本地 Tracker + skill 面诚实化 |
| Phase 2 | ✅ | 本地匹配引擎 + `/apply-zh` 强制质量报告 |
| Phase 3 | ✅ | Catalog 成本卡 + skill allowlist 治理 |
| **P0 增长资产** | ✅ | Demo + 动图 + Issue 模板 + 一键脚本 |
| **P1 体验** | ✅ | 人话报告 / tracker 挂钩 / setup 粘贴简历 / 分赛道样例 / `today` |
| **P2 分发** | 进行中 | Agent 安装文档已出；话题与社区内容待你发布 |
| **暂缓** | — | 自动投 / 自研爬虫 / 强制 SaaS / 堆 catalog 重应用 |

---

## 合规（写进产品，不是附录）

- **不自动投递**为默认策略，降低平台风控与协议风险  
- 简历与投递记录含个人信息 → 本地处理，遵守 **PIPL**  
- **禁止为刷匹配分虚构经历**；`match_resume` 的 miss 列表只作对齐提示  
- 第三方工具（boss-cli / get_jobs 等）许可证与 ToS 以各自仓库为准；本仓库面向**个人求职**  

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
