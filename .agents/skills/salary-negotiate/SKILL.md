---
name: salary-negotiate
version: 1.0.0
description: >
  薪资谈判 / 谈薪话术生成与策略。本技能复用开源中文谈薪技能 Salary-Negotiation-Skill
  （Ssupercoder，LLM Agent 架构，谈薪五阶段引擎 + Qwen2.5-7B + RAG 市场锚点，含 codex/openclaw 无代码版本），
  而非自行实现谈判策略引擎。触发词：谈薪、薪资谈判、offer 谈判、要价、薪酬博弈、salary negotiation。
context: fork
allowed-tools: Read, Glob, Grep, WebFetch, WebSearch, AskUserQuestion
---

# 谈薪技能（复用 Salary-Negotiation-Skill）

> **不要重复造轮子**：谈薪策略（分阶段博弈、话术卡片、市场锚点 RAG、薪酬结构/公司政策对齐）已被成熟开源中文项目
> [Ssupercoder/Salary-Negotiation-Skill](https://github.com/Ssupercoder/Salary-Negotiation-Skill) 完整实现
> （LLM Agent 架构，**谈薪五阶段引擎 + SQLite 记忆 + Qwen2.5-7B-Instruct + RAG 向量库**）。
> 本技能直接复用它做"策略 + 话术"，不再手写谈薪逻辑；本仓库不内置任何谈判脚本。

## 复用关系

| 能力 | 由谁实现 | 说明 |
|------|----------|------|
| 意图识别 | Salary-Negotiation-Skill 级联分类器（规则→0.5B→7B 兜底） | 识别用户谈薪场景 |
| 核心对话 | **Qwen2.5-7B-Instruct**（vLLM INT8） | 生成专业化谈薪咨询 |
| 谈薪五阶段引擎 | 状态机 + SQLite 记忆 | 分阶段博弈流程控制 |
| 薪资预估 | 规则引擎 + OfferShow 历史数据 | 锚定市场区间（部分版本跳过） |
| RAG 检索 | 薪酬结构 / 公司政策 / 市场锚点 向量库 | 个性化策略依据 |
| 安全过滤 | 规则引擎 + 敏感词库 + 二次校验 | 合规护栏 |
| 多模态输入 | Web Speech API + Whisper-base + PDF.js | 语音 / PDF 简历解析（可选） |

## 三个可用版本（选一复用，按运行环境）

- **谈薪skill**：需要 Python 本地部署，可本地解析简历。
- **谈薪skill_easy**：可在 **Codex** 中直接运行，无需代码。
- **salary-negotiation-openclaw-skill-main**：可在 **OpenClaw** 中直接运行，无需代码。
- 另有免费版 **OpenCode** 可尝试。

## 技术要点（来自其 README）

- **架构**：用户端（H5 / 微信小程序，语音 / PDF / 文字输入）→ 服务层（Serverless / 轻量 VPS）。
- **模型**：Qwen2.5-7B-Instruct，INT8 量化，vLLM 部署。
- **阶段**：谈薪五阶段引擎（状态机）+ SQLite 记忆。
- **RAG**：薪酬结构 / 公司政策 / 市场锚点向量库。
- **在线演示**：http://123.56.46.172:5000

## 工作流（本技能如何编排）

1. 用户进入谈薪场景（拿到 offer / 准备 counter / 被压价 / 校招定价）。
2. 调用 **Salary-Negotiation-Skill**（按用户环境选 codex / openclaw / 本地 python 版），现现阶段策略与话术卡片。
3. 结合本分支的 **resume-match**（匹配度）与 **salary-compare**（五险一金 / 加班 / 通勤等 offer 对比，见 README 对标表）做锚点对齐。
4. 话术产出由用户在与 HR / 猎头沟通中使用；**不虚构薪酬数据**，锚点以真实市场与自身期望为准。

## 合规与边界

- **许可证**：⚠️ 该仓库 README / 页面**未声明明确许可证**（未见 LICENSE 标注）。复用前需向作者确认授权范围，
  或仅作方法论参考，不要直接分发其代码。本分支以"策略参考"方式接入，不复制其源码进仓库。
- 不得虚构薪酬流水 / 背景以抬价；锚点须真实。
- 谈薪话术仅作策略辅助，最终以用户真实意愿与判断为准。

## 与其他技能的配合

- 匹配度锚定 → `resume-match`（底层 Resume Matcher）
- offer 多维对比（可选）→ `salary-compare`（见 README 对标表）
- 简历 → `resume-build`（Reactive-Resume）/ `08-resume-zh.md`
- 面试 → `interview-mock`（AuraInterviewer）
