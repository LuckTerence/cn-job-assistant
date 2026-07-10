---
name: resume-build
version: 1.0.0
description: '中文简历的构建与导出。本技能复用成熟开源简历构建器 Reactive-Resume （MIT，可 Docker 自托管，隐私优先，16+
  模板，导出 PDF/JSON/DOCX，内置 AI）， 而非自行实现 .docx/PDF 生成。JD→简历的智能生成另见 AitoResume。 触发词：做简历、生成简历、导出简历、简历模板、简历
  PDF、简历 DOCX、Reactive Resume。

  '
context: fork
optional: true
tier: catalog
setup_cost: medium
requires: Docker (self-host) or third-party SaaS account
os: any
default_alternative: '`/apply-zh` Markdown in documents/zh/ + any editor export PDF/DOCX'
upstream: https://github.com/AmruthPillai/Reactive-Resume
license_note: MIT
allowed-tools: Read, Glob, Grep, WebFetch, WebSearch, AskUserQuestion
---

> ⚠️ **已移出核心 skill 面**：本文件现位于 `integrations/catalog/`，供可选自托管参考，**不是**开箱可跑的 agent 工具。国内最小闭环见 `README.zh.md`、`ARCHITECTURE.zh.md` 与 `tools/{install_domestic_search,tracker,match_resume}.py`。

# 简历构建技能（复用 Reactive-Resume）

> **不要重复造轮子**：简历构建器（实时预览、多模板、PDF/DOCX 导出、AI 润色）已被成熟开源项目
> [AmruthPillai/Reactive-Resume](https://github.com/AmruthPillai/Reactive-Resume)（**MIT**，约 36k★，隐私优先、可自托管）
> 完整实现。本技能直接复用它做"构建 + 导出"，不再手写 .docx 生成逻辑。


## 真实搭建成本（Phase 3 标注）

| 项 | 值 |
|----|-----|
| 成本档 | `medium` |
| 预估首次搭建 | 30–120 min Docker; or minutes on hosted |
| 依赖 / 资源 | Docker (self-host) or third-party SaaS account |
| 操作系统 | any |
| 内存 / 磁盘 | Docker ~512MB–1GB |
| 上游 | https://github.com/AmruthPillai/Reactive-Resume |
| 许可证 | MIT |
| **默认请用** | `/apply-zh` Markdown in documents/zh/ + any editor export PDF/DOCX |

> 本仓库 **CI 不部署、不测试** 本条目的上游服务。启用前请自行评估运维与合规成本。

## 复用关系

| 能力 | 由谁实现 | 说明 |
|------|----------|------|
| 模板选择 | **Reactive-Resume** 16+ 模板（Azurill / Pikachu / Lapras 等） | 支持 A4/Letter、颜色/字体/间距自定义 |
| 实时预览 | **Reactive-Resume** | 输入即刷新，拖拽排序板块 |
| 导出 | **Reactive-Resume** | **PDF / JSON / DOCX** 一键导出（国内 HR 用 WPS，优先 DOCX） |
| AI 润色 | **Reactive-Resume** 内置 AI（OpenAI / Gemini / Claude）或 v5.2+ Application Copilot | 可在自托管实例内启用 |
| 自托管 | **Reactive-Resume** Docker（`docker compose up -d`） | 数据本地化，符合 PIPL |
| JD→简历生成 | **AitoResume**（[buynonsense/AitoResume](https://github.com/buynonsense/AitoResume)） | 按岗位描述自动生成/优化简历，支持本地 Ollama |

> 本仓库 `08-resume-zh.md` 的**分赛道结构规则**（互联网/国企/外企/体制内/应届）与**一页纸约束**
> 仍作为"内容规范"使用：先用它定结构，再粘贴进 Reactive-Resume 做样式与导出。

## 为什么选 Reactive-Resume（而非手写导出）

- **隐私优先 + 可自托管**：默认无跟踪、无广告；可 `docker compose up -d` 部署在自有服务器，简历数据不出本地——契合
  《个人信息保护法》（PIPL，2021-11-01 施行）对个人简历数据的本地化要求。
- **导出格式齐全**：原生支持 **DOCX**（国内 ATS 多用 Word 文本层解析，优先 DOCX）、PDF、JSON；无需自己维护排版。
- **导入标准**：支持从 **JSON Resume** 格式导入，便于与本仓库 Markdown 源文件互转。
- **协议友好**：MIT，"do whatever you want"，可自由集成与再分发（须保留版权声明）。

## 工作流（本技能如何编排）

1. 用本仓库 `08-resume-zh.md` + `templates/zh/resume_<track>.md` 确定**内容与结构**（赛道、板块顺序、一页纸预算）。
2. 将内容录入/导入 **Reactive-Resume**（自托管实例），选模板、调样式、实时预览。
3. 可选：启用其 AI 助手做润色，或先用 **AitoResume** 按 JD 生成初稿再导入。
4. 导出 **DOCX**（投递用）与 **PDF**（留档）到 `documents/cv-zh/`。
5. 占位/匹配度评估回到本仓库 `04-job-evaluation.md`；开场话术回到 `09-da-zhaohu-zh.md` + `/打招呼`。

## 安装与运行（摘要，以 Reactive-Resume 仓库为准）

```bash
# 自托管（推荐，数据本地化）
git clone https://github.com/AmruthPillai/Reactive-Resume.git
cd Reactive-Resume
docker compose up -d          # 启动后访问本地端口，注册即用

# 或直接使用其公开服务 / 文档：见仓库 README 与 docs.reactiveresume.com
```

AI 配置（自托管实例内）：在设置中填入 OpenAI / Gemini / Claude 的 API Key；亦可接国产模型中转（见本仓库 `MODELS.zh.md`）。

## 合规与边界

- 简历含姓名、电话、教育等个人信息，优先**自托管**部署，谨慎分享，遵守 PIPL。
- AI 生成/润色不得虚构经历或业绩；缺口诚实表述（与本仓库 `08-resume-zh.md` 一致）。
- 投递格式以目标平台要求为准；国内平台优先 `.docx`，避免纯图片 PDF（解析器易丢弃）。

## 与其他技能的配合

- 内容规范 → `08-resume-zh.md` + `templates/zh/`
- 匹配评估 → `04-job-evaluation.md`
- 打招呼话术 → `09-da-zhaohu-zh.md` + `/打招呼`
- 岗位检索 → `bosszhipin-search`（boss-cli）/ `domestic-jobs-search`（get_jobs）
- 端到端投递（可选）→ 见 `README.zh.md` 中 claude-apply / claude-job-auto-apply 参考
