---
name: job-alert
version: 1.0.0
description: >
  招聘事件提醒（面试/笔试/测评/截止）同步到 Apple 提醒。本技能复用开源工具 offercatcher
  （NissonCX，MIT）：扫描本地 Apple Mail → AI 提取招聘事件 → 写入 Reminders.app。
  不做招聘平台监控，仅做"邮件→提醒"的本地桥接。触发词：投递提醒、面试提醒、招聘邮件、
  笔试提醒、offer deadline、job alert、别漏面试。
context: fork
allowed-tools: Read, Glob, Grep, WebFetch, WebSearch, AskUserQuestion, Bash(python*)
---

# 招聘事件提醒技能（复用 offercatcher）

> **不要重复造轮子**："把招聘邮件里的面试 / 笔试 / 测评时间同步进提醒" 已被成熟开源工具
> [NissonCX/offercatcher](https://github.com/NissonCX/offercatcher)（**MIT**）完整实现——它扫描本地 Apple Mail，
> 用 LLM 理解任意语言 / 格式的邮件，提取招聘事件并写入 Reminders.app（经 iCloud 跨 iPhone/iPad/Mac 同步）。
> 本技能直接复用它，不再手写邮件解析 / 提醒同步逻辑。

> **事实澄清**：部分第三方博客将该项目描述为"国内招聘平台监控器（Boss / 猎聘 / 拉勾状态追踪）"。
> 经核对仓库源码与 README，**offercatcher 实际是一个本地邮件解析 → Apple 提醒工具，并非外部招聘平台监控器**。
> 本技能严格按其真实功能描述，不夸大其能力边界。

## 复用关系

| 能力 | 由谁实现 | 说明 |
|------|----------|------|
| 邮件扫描 | offercatcher `recruiting_sync.py` | 扫描 Apple Mail 指定账户 / 邮箱，输出邮件 JSON |
| AI 事件提取 | offercatcher（LLM，OpenClaw 调用） | 理解任意格式 / 语言，输出结构化事件 JSON |
| 提醒同步 | offercatcher `apple_reminders_bridge.py` | `remindctl`(Swift+EventKit) 优先，AppleScript 回退 |
| 手动建事件 | offercatcher `manual_event.py` | 无邮件时手工补一条提醒 |
| 邮件源列举 | offercatcher `list_mail_sources.py` | 列出可用账户 / 邮箱 |

## 支持的事件类型

`interview` / `ai_interview` / `written_exam` / `assessment` / `authorization` / `deadline`

## 技术要点（来自其 README）

- **协议**：MIT。
- **平台**：macOS（依赖 Apple Mail 与 Reminders.app）。
- **运行时**：Python 3.11+；可选 OpenClaw 做心跳调度。
- **原生桥接**：`remindctl`（Swift + EventKit，brew 安装）或 AppleScript（osascript）。
- **配置**：YAML（`~/.openclaw/offercatcher.yaml`），环境变量前缀 `OFFERCATCHER_*`。
- **多语言**：中 / 英 / 日等。

## 工作流（本技能如何编排）

1. 用户希望不再漏掉面试 / 笔试 / 测评 / 截止时间。
2. 在 macOS 上部署 offercatcher（git clone / 一行脚本 / ClawHub 三选一），配置邮件账户。
3. 运行扫描：先 `list_mail_sources.py` 确认账户，再 `recruiting_sync.py --scan-only`（JSON 供 LLM 解析），
   由 OpenClaw 或 `--apply-events` 写入 Reminders。
4. 提醒经 iCloud 同步到 iPhone / iPad / Mac；无邮件的关键节点用 `manual_event.py` 补录。
5. 投递状态的人工侧记录可结合本分支 README 对标表中的 **Job-Application-Tracker**（可选）。

## 安装与运行（摘要，以 offercatcher 仓库为准）

```bash
git clone https://github.com/NissonCX/offercatcher.git
cd offercatcher
brew install steipete/tap/remindctl && remindctl authorize

python3 scripts/list_mail_sources.py
python3 scripts/recruiting_sync.py --scan-only
python3 scripts/recruiting_sync.py --apply-events /tmp/events.json
# 手动补事件
python3 scripts/manual_event.py --title "Google Interview" --due "2026-04-15 14:00"
```

## 合规与边界

- 仅本地处理用户自己的 Apple Mail，不上传第三方；遵守 PIPL（邮件含个人信息）。
- 是"邮件→提醒"桥接，**不是**招聘平台爬虫 / 监控；不替代各平台官方通知。
- 自动写入提醒前建议先用 `--scan-only` / `--dry-run` 预览，避免误建。

## 与其他技能的配合

- 投递状态追踪（可选）→ `Job-Application-Tracker`（见 README 对标表）
- 岗位检索 → `bosszhipin-search` / `domestic-jobs-search`
- 面试准备 → `interview-mock`（AuraInterviewer）
