---
name: referral-outreach
version: 1.0.0
description: '内推 / 冷触达序列生成（邮件/LinkedIn/Twitter）。本技能复用开源 CLI outreach-ai （quionie，MIT）：单命令生成多通道个性化冷邮件/DM，支持
  Claude/OpenAI/Ollama， 批量 CSV + 语气档案。而非自行实现冷邮件生成器。触发词：内推、冷邮件、cold email、 触达、找人内推、outreach、referral、找校友内推。

  '
context: fork
optional: true
tier: catalog
setup_cost: low
requires: Python + pip; Claude/OpenAI/Ollama API key
os: any
default_alternative: Write referral notes manually; track in tools/tracker.py
upstream: https://github.com/quionie/outreach-ai
license_note: MIT
allowed-tools: Read, Glob, Grep, WebFetch, WebSearch, AskUserQuestion
---

> ⚠️ **已移出核心 skill 面**：本文件现位于 `integrations/catalog/`，供可选自托管参考，**不是**开箱可跑的 agent 工具。国内最小闭环见 `README.zh.md`、`ARCHITECTURE.zh.md` 与 `tools/{install_domestic_search,tracker,match_resume}.py`。

# 内推 / 冷触达技能（复用 outreach-ai）

> **不要重复造轮子**：多通道冷触达（email / LinkedIn / Twitter 序列、A/B 变体、语气档案、批量 CSV、
> LinkedIn 资料抓取做个性化）已被成熟开源 CLI [quionie/outreach-ai](https://github.com/quionie/outreach-ai)（**MIT**）完整实现。
> 本技能直接复用它生成"内推 / 冷触达"文案序列，不再手写邮件模板引擎。


## 真实搭建成本（Phase 3 标注）

| 项 | 值 |
|----|-----|
| 成本档 | `low` |
| 预估首次搭建 | 15–30 min (`pip` + API key) |
| 依赖 / 资源 | Python + pip; Claude/OpenAI/Ollama API key |
| 操作系统 | any |
| 内存 / 磁盘 | light CLI |
| 上游 | https://github.com/quionie/outreach-ai |
| 许可证 | MIT |
| **默认请用** | Write referral notes manually; track in tools/tracker.py |

> 本仓库 **CI 不部署、不测试** 本条目的上游服务。启用前请自行评估运维与合规成本。

## 复用关系

| 能力 | 由谁实现 | 说明 |
|------|----------|------|
| 多通道序列 | outreach-ai `outreach generate` | email(4步) / LinkedIn(3步) / Twitter(2步) 序列 |
| A/B 变体 | outreach-ai `--variants` | 每步最多 3 个变体 |
| 语气档案 | outreach-ai tones（professional / casual / founder / challenger，可自定义 YAML） | 控制语气 |
| 批量触达 | outreach-ai `outreach batch`（CSV，并发） | 百量级 prospect 批量 |
| 个性化 | outreach-ai LinkedIn 抓取 | 真实 prospect 数据注入 |
| 多模型 | Claude / OpenAI / Ollama(本地) | 无 vendor lock-in |
| 投递 | SMTP / SendGrid；HubSpot / Salesforce CRM | 发送与归档 |

## 技术要点（来自其 README）

- **协议**：MIT。
- **安装**：`git clone` + `pip install -e .`（暂未上 PyPI）。
- **模型**：默认 `claude-sonnet-4`；可切 OpenAI(`gpt-4o`)、Ollama(`llama3.1` 本地)。
- **输出**：Markdown / JSON；Rich 终端展示。
- **配置**：`.outreachai.yml`（API key 用 `${ENV}` 引用）。

## 通道序列结构

- **Email（4 步）**：Initial → Follow-up 1(Day 3) → Follow-up 2(Day 5) → Breakup(Day 7)。
- **LinkedIn（3 步）**：Connection request(<300 字) → First message → Follow-up。
- **Twitter/X（2 步）**：Ice-breaker → Value DM。

## 工作流（本技能如何编排）

1. 用户想找目标公司的人内推 / 冷触达（recruiter、目标团队、校友）。
2. 用 outreach-ai 生成序列：`outreach generate --name/--company/--role/--product/--value-prop --channels email,linkedin --tone professional`。
3. 把"产品 / 价值主张"替换为用户求职诉求（如"希望内推贵司 X 岗位，附简历"），话术由用户审核后**手动发送**——
   本分支统一不自动代发，规避平台协议与骚扰风险。
4. 批量场景用 `outreach batch` 喂 CSV（name / company / role / linkedin_url / notes）。
5. 触达对象来自本分支的岗位检索（boss-cli / get_jobs）或用户自有名单。

## 安装与运行（摘要，以 outreach-ai 仓库为准）

```bash
git clone https://github.com/quionie/outreach-ai.git
cd outreach-ai
pip install -e .
export ANTHROPIC_API_KEY="..."

outreach generate \
  --name "Sarah Chen" --company "Stripe" --role "Eng Manager" \
  --product "内推申请" --value-prop "3 年 X 经验，附简历，盼内推 Y 岗" \
  --channels email,linkedin --tone professional
```

## 合规与边界

- **不自动代发**：本分支统一"生成文案、用户手动发送"，避免触发 LinkedIn / 邮箱反垃圾与平台协议风险。
- 内推 / 冷触达须真实、不夸大、不骚扰；遵守各平台反垃圾规则与 GDPR / PIPL 对个人信息的约束。
- API Key 属敏感凭证，用环境变量注入，勿写入仓库。

## 与其他技能的配合

- 岗位 / 公司来源 → `bosszhipin-search` / `domestic-jobs-search`
- 简历附件 → `integrations/catalog/resume-build/`（可选）/ `08-resume-zh.md`
- 话术衔接 → `09-da-zhaohu-zh.md` + `/打招呼`（内推开场可复用其结构）
- 谈薪衔接 → `integrations/catalog/salary-negotiate/`（拿到面试 / offer 后）
