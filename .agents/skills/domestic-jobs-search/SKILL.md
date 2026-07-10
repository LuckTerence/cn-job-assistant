---
name: domestic-jobs-search
version: 1.0.0
description: >
  国内综合招聘平台（智联招聘、前程无忧 51job、猎聘、拉勾）的岗位检索与自动投递。
  本技能复用开源项目 get_jobs（loks666/get_jobs，禁商用协议）统一覆盖上述平台，
  而非逐个平台自行实现。触发词：智联、51job、前程无忧、猎聘、拉勾、全平台投递、自动投简历。
context: fork
allowed-tools: Read, Glob, Grep, WebFetch, WebSearch, AskUserQuestion
---

# 国内综合平台搜索技能（复用 get_jobs）

> **不要重复造轮子**：智联 / 51job / 猎聘 / 拉勾 的检索与投递已被成熟开源项目
> [loks666/get_jobs](https://github.com/loks666/get_jobs)（Java + Spring Boot + Playwright 浏览器自动化）
> 统一覆盖。本技能直接复用它，不自行实现各平台接口。

## 复用关系

| 平台 | 由谁实现（get_jobs 内部类） | 现状备注（来自 get_jobs README） |
|------|------------------------------|----------------------------------|
| Boss直聘 | `Boss.java` | 每日打招呼上限已放宽至 150；AI 智能匹配 + 自动写打招呼语（仅 Boss） |
| 猎聘 | `Liepin.java` | 默认打招呼无上限，主动发消息有上限；量大，较推荐 |
| 51job | `Job51.java` | 投递有上限、限制搜索量；作者称"已烂掉，不建议" |
| 智联招聘 | `ZhiLian.java` | 投递上限约 100；作者称"烂掉了，不要用" |
| 拉勾 | 同体系 | get_jobs 亦覆盖 |

> Boss直聘 另有更轻量的 CLI 方案 **boss-cli**（见 `bosszhipin-search`）；本技能聚焦智联/猎聘/51job/拉勾。

> **校招 / 实习平台覆盖（可选参考）**：get_jobs 与 boss-cli 主要覆盖社招主流平台；
> 实习僧 / 牛客 / 应届生求职网 等校招渠道可参考
> **[gototrip1/Automated-resume-submission-Agent](https://github.com/gototrip1/Automated-resume-submission-Agent)**
> （覆盖 Boss / 实习僧 / 牛客 / 应届生 / 智联 / 51job / 拉勾 / 猎聘 共 8 站，LangGraph + Playwright）。
> ⚠️ 该仓库**未声明许可证**，且为自动投递 Agent；本分支坚持"不自动投递"政策，仅作平台覆盖参考，不集成其代码。

## get_jobs 技术要点（来自其 README，便于对接）

- **技术栈**：Java 21 + Gradle + Spring Boot；自动下载 chromedriver 做浏览器自动化。
- **AI 集成**：OpenAI 兼容接口（`BASE_URL` / `API_KEY` / `MODEL`），默认 `gpt-5-nano`，
  经中转可接**任意模型**（含国产 DeepSeek / 通义 / 智谱，详见本仓库 `MODELS.zh.md`）。
- **核心能力**：AI 检测岗位匹配度、按 JD 自动写个性化打招呼语（Boss）、图片简历、
  智能过滤（不活跃 HR / 猎头 / 薪资）、企业微信通知、黑名单、持久登录（Cookie 约每周扫码一次）。
- **协议**：已改为**禁止商业化**的开源协议，请勿用于商业服务。

## 安装与运行（摘要，以 get_jobs 仓库为准）

```bash
git clone https://github.com/loks666/get_jobs.git
cd get_jobs
# 环境：JDK 21 + Gradle；自动下载 chromedriver
# 网页 GUI 修改配置（地区 / 岗位 / AI 的 BASE_URL+API_KEY+MODEL），运行 GetJobsApplication
```

AI 配置（`.env`）：

```
HOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
BASE_URL=https://api.openai.com      # 或国产模型中转地址
API_KEY=sk-xxx
MODEL=gpt-5-nano                     # 可换 DeepSeek / 通义 / 智谱
```

## 工作流（本技能如何编排）

1. 用户在 get_jobs GUI 配置地区、目标岗位、筛选条件，并填入国产模型 API（BASE_URL/KEY/MODEL）。
2. get_jobs 负责检索、AI 匹配、自动打招呼/投递（全平台）。
3. 本仓库 `job-application-assistant` 的**中文简历模板**（08-resume-zh.md）与**话术指南**
   （09-da-zhaohu-zh.md）可作为 get_jobs 的"简历/招呼语素材源"——先把简历与话术在本仓库生成好，
   再导入 get_jobs 使用。
4. 匹配评估如需更深分析，可回到本仓库 `04-job-evaluation.md` 做结构化评估。

## 合规与边界

- get_jobs 为浏览器自动化工具，使用须遵守各平台用户协议；本仓库统一**仅作个人求职辅助**。
- **本仓库不自动投递**：与 get_jobs 的自动化能力并列，用户可自行决定是否启用自动投递；
  启用前须知悉平台风控与协议风险。
- 国产模型 API Key 属敏感凭证，优先本地/私有部署，避免泄露（PIPL）。

## 与其他技能的配合

- Boss直聘（轻量 CLI）→ `bosszhipin-search`（boss-cli）
- 评估匹配度 → `04-job-evaluation.md`
- 中文简历 → `08-resume-zh.md`
- 打招呼话术 → `09-da-zhaohu-zh.md` + `/打招呼`
- MCP 原生方案 → `mergedao/mcp-jobs`（猎聘/Boss/智联/51job，自然语言调用）
- 校招 / 实习平台（可选参考）→ gototrip1/Automated-resume-submission-Agent（实习僧 / 牛客 / 应届生；未声明许可，不集成）
