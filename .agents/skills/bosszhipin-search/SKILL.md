---
name: bosszhipin-search
version: 1.1.0
description: >
  国内求职平台"Boss直聘"的岗位检索与打招呼。本技能复用开源项目 boss-cli
  （许可证未声明，逆向 API 实现的 BOSS 直聘 CLI）完成搜索/推荐/打招呼，而非自行实现。
  通过 tools/install_domestic_search.py 一键安装与冒烟。触发词：Boss直聘、直聘、BOSS、
  找工作、岗位搜索、职位描述、打招呼。
context: fork
allowed-tools: Bash(boss *), Bash(python* tools/install_domestic_search.py *), Bash(python3 tools/install_domestic_search.py *), Bash(python*), Bash(pip*), Read, Glob, Grep, WebFetch, WebSearch, AskUserQuestion
---

# Boss直聘 搜索技能（复用 boss-cli）

> **不要重复造轮子**：Boss直聘 的搜索/打招呼已有成熟开源实现
> [jackwener/boss-cli](https://github.com/jackwener/boss-cli)（许可证未声明，通过逆向 API 实现；复用前请确认授权）。
> 本技能直接复用它，不自行实现爬虫或接口。**缺口是交付（安装器），不是算法。**

## 一键安装（本仓库）

```bash
# 状态
python tools/install_domestic_search.py status

# 安装 boss-cli（pip；失败时按上游 README 从源码装）
python tools/install_domestic_search.py install-boss

# 离线友好冒烟（CI / 本地）：校验安装器 + tracker；若已装 boss 则跑 --help
python tools/install_domestic_search.py smoke
```

个人 / 非商用场景使用。上游 **未声明许可证**；分发或修改前须自行确认授权。

## 复用关系

| 能力 | 由谁实现 | 说明 |
|------|----------|------|
| 安装 / 状态 | **本仓库** `tools/install_domestic_search.py` | 打包交付层 |
| 搜索岗位 | **boss-cli** `boss search` | 逆向 API，城市/薪资/经验等筛选 |
| 查看推荐 | **boss-cli** `boss recommend` | 推荐流 |
| 打招呼 | **boss-cli** `boss greet` / `batch-greet` | 仅 **auto 模式**且用户完成风险确认后，经 `apply_assist.py` 调用；自定义话术请用 **semi**（多数 greet 无自定义文案参数） |
| 导出 岗位描述 | **boss-cli** `boss export` / `boss detail` | CSV/JSON |
| AI 话术生成 | **本仓库** `09-da-zhaohu-zh.md` + `/da-zhaohu` | 生成文本 |
| 投递模式开关 | **本仓库** `tools/apply_assist.py` | manual / semi / auto，默认 manual |

## 认证

```bash
boss login --qrcode
boss status
```

Cookie / `zp_token` 约 7 天 TTL，过期需重登。详见 boss-cli 仓库。

## 命令示例

```bash
boss search "golang" --city 杭州 --salary 20-30K --exp 3-5年
boss show 3
boss detail <securityId> --json
boss export "Python" -n 50 -o jobs.csv
# 自定义话术 → semi（复制到剪贴板，你点发送）
python tools/apply_assist.py semi --url '…' --text-file documents/zh/da-zhaohu_….md --company …
# 全自动（平台默认招呼）请走门禁；不要直接 boss greet，除非用户已选 auto
python tools/apply_assist.py status
python tools/apply_assist.py auto-greet --security-id <id> --i-understand-ban-risk
# 确认后再加 --execute；--text-file 仅当 boss-cli 支持时才会传入，否则拒绝
```

## 工作流

1. `python tools/install_domestic_search.py status`  
   **或** 安装 MIT 的 [boss-agent-cli](https://github.com/can4hou6joeng4/boss-agent-cli)（默认 assisted，见 `integrations/catalog/boss-agent-cli/`）
2. 搜岗并导出 JSON/CSV（boss-agent 为 `{ok,data,…}` 信封也可）
3. **归一化 + 批量进 tracker**（默认 `to_apply`）：
   ```bash
   python tools/normalize_job_export.py -i raw.json -o jobs.json --default-channel Boss直聘
   python tools/flow.py shortlist --raw raw.json --track internet
   # 或: import-jobs jobs.json
   ```
4. `day-plan` / `rank` 挑岗 → `/apply-zh` 或 `/da-zhaohu`
5. 按用户模式投递（**默认 manual**）：
   - **manual**：用户在 App 里自己点
   - **semi**：`python tools/apply_assist.py semi --url … --text-file …`（仍须用户点发送）
   - **auto**：`apply_assist.py set-mode auto` + 配置风险项 + `auto-greet … --execute`
6. `/outcome` · `weekly-report` · `funnel`

## 合规与边界

- 仅作**个人求职辅助**；遵守 Boss直聘 用户协议与 PIPL。
- **默认 manual，不自动投**；semi / auto 由用户显式打开。
- auto 可能限流/封号，后果用户自负；Agent 不得静默 `--execute`。
- 逆向工具可能触发风控；按 boss-cli 指引处理。

## 与其他技能的配合

- 其他平台 → `domestic-jobs-search`（get_jobs）
- 追踪 → `application-tracker` / `tools/tracker.py`
- 可选重应用 → `integrations/catalog/`
