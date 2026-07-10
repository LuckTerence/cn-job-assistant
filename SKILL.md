---
name: AI求职助理
description: "本地求职助手：根据岗位描述定制中文简历与求职话术，导出可投递 PDF 简历，分析简历与岗位匹配度，记录求职投递进度。支持简历模板、求职信生成、求职看板。触发词：求职、找工作、改简历、中文简历、PDF简历、求职信、岗位匹配、投递进度、简历优化、找工作助手。"
---

# AI求职助理

本地求职工作流助手：根据岗位描述定制中文简历与求职话术 → 导出可投递 PDF 简历 → 分析简历岗位匹配度 → 记录投递进度。

完整仓库与更新：https://github.com/LuckTerence/cn-job-assistant

## 何时使用

用户提到以下任一需求时使用本技能：

- 求职、找工作、投递简历
- 定制/修改中文简历、优化简历
- 生成 PDF 格式简历
- 撰写求职信、求职话术
- 分析简历与岗位匹配度
- 记录求职投递进度、面试管理
- 简历模板、求职信模板

## 快速开始

```bash
# 1. 解压后进入本技能目录
cd ai-job-assistant

# 2. 试跑（无需登录，查看示例）
bash scripts/demo.sh
# 或: make demo

# 3. 在 Agent 里
# /setup-zh   → 填写个人画像（可粘贴旧简历）
# /apply-zh   → 粘贴岗位描述 → 生成简历 PDF + 求职话术 + 匹配摘要
```

导出 PDF 简历（推荐安装 Typst：`brew install typst`，未安装时自动使用 HTML 预览）：

```bash
python3 tools/export_resume_pdf.py --which
python3 tools/export_resume_pdf.py -i documents/zh/resume_公司.md
```

求职模式选择：

```bash
python3 tools/apply_assist.py explain
python3 tools/apply_assist.py status
python3 tools/apply_assist.py set-mode manual   # 默认：生成材料，用户手动粘贴发送
python3 tools/apply_assist.py set-mode semi     # 半自动：打开页面并复制话术到剪贴板
# auto 需风险确认 + --i-understand-ban-risk + --execute（定制话术请用 semi）
```

投递进度管理：

```bash
python3 tools/tracker.py today
python3 tools/tracker.py dashboard
```

## 核心功能

| 能力 | 说明 |
|------|------|
| 简历定制 | 根据岗位描述关键词优化简历内容 |
| PDF 导出 | 生成排版精美的可投递 PDF 简历 |
| 匹配分析 | 本地 TF-IDF 算法分析简历与岗位匹配度，给出优化建议 |
| 话术生成 | 生成针对性的求职沟通文案 |
| 进度追踪 | 本地 CSV 记录投递状态、面试进度、Offer 管理 |
| 求职看板 | 生成单文件 HTML 可视化求职看板 |
| 模板库 | 互联网/国企/外企/应届生等多场景中文简历模板 |

## 命令示例

```bash
# 分析简历与岗位匹配度
python3 tools/match_resume.py report \
  --resume documents/zh/resume_示例.md \
  --jd path/to/job_description.md \
  --brief-out match_summary.txt

# 添加投递记录
python3 tools/tracker.py add \
  --company 示例科技 --role 后端工程师 \
  --channel 招聘平台 --status applied \
  --city 杭州 --salary 25-40K

# 查看今日待办（跟进/面试/复盘）
python3 tools/tracker.py today

# 生成可视化看板
python3 tools/tracker.py dashboard
```

## 交付约定

| 文件 | 用途 |
|------|------|
| `resume_*.md` | 简历源文件，方便编辑修改 |
| **`resume_*.pdf`** | **投递用简历（推荐交付格式）** |
| 求职话术/求职信 | 生成文案供用户复制粘贴使用 |
| `job_search_tracker.csv` | 本地投递记录文件（数据存储在本地） |

## 能力边界

- 默认生成求职材料，所有发送操作由用户手动完成
- 匹配度分析基于关键词算法，仅供参考，不代表录用概率
- 请如实填写简历信息，不虚构工作经历或技能
- 个人数据仅存储在本地，保护隐私

## 目录指引

- 斜杠命令：`.claude/commands/`（`setup-zh` / `apply-zh` / `da-zhaohu` 等）
- 中文简历模板：`templates/zh/`
- 工具脚本：`tools/`（export_resume_pdf / match_resume / tracker / apply_assist）
- 使用示例：`examples/demo/`
- 详细说明：`README.md`、`README.zh.md`

## 许可证

MIT。详见仓库 `LICENSE`、`NOTICE` 文件。
