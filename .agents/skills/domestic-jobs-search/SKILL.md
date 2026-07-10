---
name: domestic-jobs-search
version: 1.1.0
description: >
  国内综合招聘平台（智联招聘、前程无忧 51job、猎聘、拉勾）的岗位检索。
  本技能复用开源项目 get_jobs（loks666/get_jobs，禁商用协议），经
  tools/install_domestic_search.py 克隆到 third_party/。触发词：智联、51job、
  前程无忧、猎聘、拉勾、全平台检索。
context: fork
allowed-tools: Bash(python* tools/install_domestic_search.py *), Bash(python3 tools/install_domestic_search.py *), Bash(git*), Read, Glob, Grep, WebFetch, WebSearch, AskUserQuestion
---

# 国内综合平台搜索技能（复用 get_jobs）

> **不要重复造轮子**：智联 / 51job / 猎聘 / 拉勾 的检索能力由
> [loks666/get_jobs](https://github.com/loks666/get_jobs)（Java + Spring Boot + Playwright）覆盖。
> 本技能只做**安装与编排指引**，不自行实现各平台接口。

## 一键安装（本仓库）

```bash
python tools/install_domestic_search.py status
python tools/install_domestic_search.py install-get-jobs
# 克隆位置默认：third_party/get_jobs（已 gitignore）
```

**许可证：禁止商业化**。本仓库面向个人求职；商用勿用 get_jobs。

## 运行成本（诚实说明）

| 项 | 要求 |
|----|------|
| 运行时 | **JDK 21 + Gradle** + chromedriver（上游自动下载） |
| 配置 | 上游 GUI / `.env`（`BASE_URL` / `API_KEY` / `MODEL`） |
| 自动投递 | get_jobs 支持自动化；**本仓库默认不自动投递**，仅用其检索/导出能力时更安全 |

轻量路径：Boss 岗优先 `bosszhipin-search`（boss-cli），不必上 get_jobs。

## 安装后步骤（以 get_jobs README 为准）

```bash
cd third_party/get_jobs
# 配置地区 / 岗位 / 模型 API，运行 GetJobsApplication
```

国产模型接入说明见仓库根目录 `MODELS.zh.md`。

## 工作流

1. `install-get-jobs` 克隆上游。
2. 在 get_jobs 中配置筛选；导出或复制目标岗位描述。
3. 本仓库 `/apply-zh` / `/da-zhaohu` 生成中文简历与话术。
4. **用户在 App 内手动投递**。
5. `python tools/tracker.py add … --channel 智联|猎聘|51job|拉勾`。

## 合规与边界

- 遵守各平台用户协议与 get_jobs 禁商用协议。
- 启用 get_jobs 自动投递前须知悉风控风险；默认推荐手动投递。
- API Key 本地保存，勿提交仓库。

## 与其他技能的配合

- Boss直聘轻量 CLI → `bosszhipin-search`
- 追踪 → `application-tracker` / `tools/tracker.py`
- 可选重应用 → `integrations/catalog/`
