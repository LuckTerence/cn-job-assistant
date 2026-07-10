---
name: bosszhipin-search
version: 1.0.0
description: >
  国内求职平台"Boss直聘"的岗位检索与打招呼。本技能复用开源项目 boss-cli
  （许可证未声明，逆向 API 实现的 BOSS 直聘 CLI）完成搜索/推荐/打招呼，而非自行实现。
  触发词：Boss直聘、直聘、BOSS、找工作、岗位搜索、职位描述、打招呼。
context: fork
allowed-tools: Bash(boss *), Bash(python*), Bash(pip*), Read, Glob, Grep, WebFetch, WebSearch, AskUserQuestion
---

# Boss直聘 搜索技能（复用 boss-cli）

> **不要重复造轮子**：Boss直聘 的搜索/打招呼已有成熟开源实现
> [jackwener/boss-cli](https://github.com/jackwener/boss-cli)（许可证未声明，通过逆向 API 实现；复用前请确认授权）。
> 本技能直接复用它，不自行实现爬虫或接口。

## 复用关系

| 能力 | 由谁实现 | 说明 |
|------|----------|------|
| 搜索岗位 | **boss-cli** `boss search` | 逆向 API，支持城市/薪资/经验/学历/行业筛选 |
| 查看推荐 | **boss-cli** `boss recommend` | 推荐流 |
| 打招呼 | **boss-cli** `boss greet` / `batch-greet` | 单发或批量 |
| 导出 JD | **boss-cli** `boss export` / `boss detail` | CSV/JSON |
| AI 话术生成 | **本仓库** `09-da-zhaohu-zh.md` + `/打招呼` | 生成文本后由用户粘贴进 `boss greet` |

> 浏览器注入方案另见 [yangfeng20/ai-job](https://github.com/yangfeng20/ai-job)（油猴脚本 + Spring Boot +
> DeepSeek，拦截 BOSS 直聘 Protobuf 协议）；MCP 方案见 [mergedao/mcp-jobs](https://github.com/mergedao/mcp-jobs)。

## 同类 Boss 轮子（按需选用，不重复实现）

| 项目 | 形态 | 协议 | 特点 | 适用 |
|------|------|------|------|------|
| **boss-cli**（本技能主用） | 命令行 CLI | 未声明（参考使用，复用前请确认授权） | 逆向 API，`search/recommend/greet/export` | agent 编排、脚本化 |
| [Ocyss/boss-helper](https://github.com/Ocyss/boss-helper) | 浏览器扩展（WXT+Vue3） | 非商用 | UI 去广告、批量投递、高级筛选、GPT 自动打招呼、多账号 | 人工界面操作、可视化 |
| [yangfeng20/ai-job](https://github.com/yangfeng20/ai-job) | 油猴脚本 + Spring AI | — | 拦截 Protobuf、接 DeepSeek 自动聊 | 浏览器内 AI 辅助 |
| [yangfeng20/boss_batch_push](https://github.com/yangfeng20/boss_batch_push) | 批量推送脚本 | — | 批量投简历 + 自定义招呼语 | 轻量批量 |
| [Frrrrrrrrank/auto_job__find__chatgpt__rpa](https://github.com/Frrrrrrrrank/auto_job__find__chatgpt__rpa) | RPA 自动化 | — | ChatGPT + RPA 自动找岗/投递 | 全自动 RPA |
| [noBaldAaa/find-job](https://github.com/noBaldAaa/find-job) | 自动投递 | — | 自动找岗投递 | 全自动 |

> 选型建议：**agent 编排/脚本化优先 boss-cli**；**人工可视化优先 boss-helper**；全自动 RPA 类（auto_job_find、
> find-job）自动化程度高但风控与合规风险更大，启用前须知悉平台协议。本项目默认不自动投递。

## 安装 boss-cli

```bash
pip install boss-cli        # 详见 boss-cli 仓库 README（以 PyPI 实际包名为准）
boss --version
```

## 认证（cookie / zp_token）

boss-cli 从浏览器自动提取 Cookie，或用二维码登录：

```bash
boss login --qrcode         # 终端输出二维码，用 BOSS 直聘 App 扫描
boss status                 # 确认 search_authenticated / recommend_authenticated
```

> 认证依赖 `zp_token`（取自 `bst` Cookie）与 JS 生成的 `__zp_stoken__` 反爬令牌；Cookie 约 7 天 TTL，
> 过期后需重新登录。详见 boss-cli 仓库说明。

## 命令（来自 boss-cli，直接复用）

```bash
# 搜索：关键词 + 城市 + 薪资 + 经验
boss search "golang" --city 杭州 --salary 20-30K --exp 3-5年

# 查看上一条搜索的第 3 个岗位详情
boss show 3
boss detail <securityId> --json

# 导出为 CSV / JSON
boss export "Python" -n 50 -o jobs.csv

# 单发打招呼
boss greet <securityId>

# 批量打招呼（内置 1.5s 延迟，--dry-run 仅预览）
boss batch-greet "golang" --city 杭州 -n 5 --dry-run
```

完整命令集（含 `recommend` / `history` / `applied` / `me` 等）见 boss-cli README。

## 工作流（本技能如何编排）

1. 用户给出目标（岗位 + 城市 + 薪资），调用 `boss search` 检索。
2. 用 `boss detail` / `boss export` 提取 JD 结构化字段（公司/岗位/薪资/要求/职责）。
3. 将 JD 交给本仓库 `job-application-assistant` 做匹配评估与**中文简历/话术生成**。
4. 生成的话术文本，由用户复制进 `boss greet <securityId>` 或 `boss batch-greet`（或粘贴进
   ai-job / get_jobs 的 AI 招呼语配置）。

## 合规与边界

- **许可证提示**：经核验，boss-cli 上游仓库**未声明许可证**（GitHub 无 LICENSE 文件）。本技能仅作
  **参考性复用**，实际分发/修改前须向作者确认授权，避免侵权。
- boss-cli 为逆向 API 实现，使用须遵守 Boss直聘 用户协议；本技能仅做**个人求职辅助**。
- **本仓库统一不自动投递**：话术由用户手动发送（粘贴进 `boss greet` 或 App），以规避风控。
- 逆向工程类工具可能被平台风控；如触发限流/环境异常，按 boss-cli 指引重新登录。
- 薪资/岗位以平台实时为准，生成内容前建议用户自行核对。

## 与其他技能的配合

- 评估匹配度 → `04-job-evaluation.md`
- 中文简历 → `08-resume-zh.md`
- 打招呼话术 → `09-da-zhaohu-zh.md` + `/打招呼`
- 其他平台（智联/猎聘/51job/拉勾）→ 统一由 `get_jobs`（见 `domestic-jobs-search`）覆盖，
  或 `mcp-jobs`（MCP）
