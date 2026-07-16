---
name: AI求职助理
description: "本地求职助手：定制中文简历与话术、导出 PDF、投前质量门禁(quality_gate)、匹配归因、求职看板。触发词：求职、改简历、岗位匹配、投前门禁、求职看板、投递进度。"
---

# AI求职助理

本地求职工作流：定制中文简历/话术 → **投前质量门禁** → 双格式交付（md 粘贴 / pdf 上传）→ 记录进度与匹配归因。

完整仓库：https://github.com/LuckTerence/cn-job-assistant

## 何时使用

- 求职、投递、改中文简历、PDF 简历
- 岗位匹配、**过 AI/ATS 筛**、改这 3 条
- 投递进度、面试管理、求职看板

## 快速开始

```bash
cd ai-job-assistant
bash scripts/demo.sh   # 或 make check
# Agent: /setup-zh → /apply-zh（强制 quality_gate）
```

```bash
# 投前一键门禁（匹配 + 诚信 + ATS）
python3 tools/quality_gate.py --resume r.md --jd j.md --pdf r.pdf
python3 tools/match_resume.py align --resume r.md --jd j.md   # 改这 3 条
python3 tools/export_resume_pdf.py -i r.md --ats-checklist

# 短名单 / 看板
python3 tools/flow.py shortlist --jobs jobs.json --track internet
python3 tools/tracker.py day-plan
python3 tools/tracker.py match-outcome
python3 tools/tracker.py serve   # 本机一键改状态
```

## 核心功能

| 能力 | 说明 |
|------|------|
| 简历定制 | 按 JD 关键词改写（禁止虚构） |
| 双格式 | **md=粘贴稿** · **pdf=上传稿**（单栏 ATS 友好） |
| 投前门禁 | `quality_gate`：SOFT/HARD 退出码 |
| 改这 3 条 | `match report` / `align` 行动清单 |
| 匹配分析 | TF–IDF + 同义词 + 薪资对照 |
| 匹配归因 | tracker `match_*` + `match-outcome` |
| 进度/看板 | CSV · funnel · skip-stats · serve |
| 模板 | 互联网/国企/外企/应届等 |

## 交付约定

| 文件 | 用途 |
|------|------|
| `resume_*.md` | 粘贴 / 改稿源 |
| **`resume_*.pdf`** | 上传附件 |
| `gate_*.json` | 门禁结果 |
| `job_search_tracker.csv` | 本地进度（含 match_score） |

说明：`docs/ats-gate.zh.md` · `docs/COMMAND_MAP.zh.md` · `docs/QUICKSTART.zh.md`

## 能力边界

- 默认手动投递；匹配分不是录用预测
- 禁止虚构经历；诚信硬阻断优先于刷分
- 数据仅本地

## 许可证

MIT。见 `LICENSE`、`NOTICE`。
