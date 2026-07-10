---
name: AI求职助理
description: 帮你在本地做求职材料：按岗位描述定制中文简历与 Boss 话术，导出可投 PDF，看匹配度，记录投了哪些公司。默认你自己点发送；需要时再开半自动复制话术或全自动（风险自担）。适合用 Agent / 命令行的求职者。
---

# AI求职助理

本地求职工作流：按岗位描述改中文简历与打招呼话术 → 导出可投 PDF → 看匹配度 → 记投递进度。  
**默认你自己在 App 里点发送**；需要时再开半自动（复制话术）或全自动（风险自担）。

完整仓库与更新：https://github.com/LuckTerence/cn-job-assistant

## 何时使用

用户提到：求职、找工作、改简历、中文简历、PDF 简历、打招呼、求职信、Boss 直聘、智联、猎聘、岗位匹配、投递进度、半自动投递、全自动投递、apply-zh、setup-zh。

## 快速开始

```bash
# 1. 解压后进入本技能目录
cd AI求职助理   # 或你的解压路径

# 2. 试跑（无需登录）
bash scripts/demo.sh
# 或: make demo

# 3. 在 Agent 里
# /setup-zh   → 填画像（可粘贴旧简历）
# /apply-zh   → 贴岗位全文 → 出简历 PDF + 话术 + 匹配摘要
```

单独导出 PDF（推荐安装 Typst：`brew install typst`）：

```bash
python3 tools/export_resume_pdf.py --which
python3 tools/export_resume_pdf.py -i documents/zh/resume_公司.md
```

投递模式（选择权在用户）：

```bash
python3 tools/apply_assist.py explain
python3 tools/apply_assist.py status
python3 tools/apply_assist.py set-mode manual   # 默认
python3 tools/apply_assist.py set-mode semi     # 打开页面 + 复制话术
# auto 需配置风险确认 + --i-understand-ban-risk + --execute
# 定制话术请用 semi；auto-greet 的 --text-file 仅在 boss-cli 支持时生效
```

记进度：

```bash
python3 tools/tracker.py today
python3 tools/tracker.py dashboard
```

## 交付约定

| 文件 | 用途 |
|------|------|
| `resume_*.md` | 源文件，方便改 |
| **`resume_*.pdf`** | **投递用**（必须生成） |
| 话术 / 求职信 | 手动或半自动粘贴发送 |
| `job_search_tracker.csv` | 本地投递记录（勿提交公网） |

## 能力边界

- 默认 **manual**，不静默自动投；auto 有多重门禁
- 匹配分是本地关键词对齐，不是录用预测
- 不会的技能别硬写进简历
- 个人数据遵守 PIPL，敏感文件已 gitignore

## 目录指引

- 命令：`.claude/commands/`（`setup-zh` / `apply-zh` / `da-zhaohu`）
- 中文模板：`templates/zh/`
- 工具：`tools/`（export_resume_pdf / match_resume / tracker / apply_assist）
- 样例：`examples/demo/`
- 详解：`README.md`、`docs/resume-pdf-reuse.zh.md`

## 许可证

MIT。上游与 NOTICE 见仓库 `LICENSE`、`NOTICE`。
