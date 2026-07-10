---
name: resume-match
version: 2.0.0
description: >
  本地轻量简历↔JD 匹配与生成质量报告。使用 tools/match_resume.py（stdlib：TF–IDF 余弦
  + 关键词命中/缺失，无 embedding 下载）。触发词：匹配度、JD 匹配、关键词、简历诊断、
  skills gap、生成质量、quality report、ATS 关键词。
context: fork
allowed-tools: Bash(python* tools/match_resume.py *), Bash(python3 tools/match_resume.py *), Read, Glob, Grep, AskUserQuestion
---

# 简历匹配技能（本地轻量 CLI）

> **思路复用 Resume Matcher，依赖不复用其重栈。**  
> [srbhr/Resume-Matcher](https://github.com/srbhr/Resume-Matcher)（Apache-2.0）用
> sentence-transformers + 余弦相似度做语义匹配；本仓库取同一思路的**可本地、零模型下载**
> 版本：`TF–IDF 向量 + 余弦 + JD 关键词命中/缺失`，见 `tools/match_resume.py`。  
> 需要完整 UI / 神经 embedding 时，见可选集成
> `integrations/catalog/resume-match/`（上游 Streamlit 应用，百 MB 级权重）。

## 复用关系

| 能力 | 实现 | 说明 |
|------|------|------|
| 向量相似度 | **本仓库** TF–IDF 余弦 | 无网络、无模型权重 |
| 关键词 hit/miss | **本仓库** JD 加权抽取 | 中英双语 tokenization |
| 生成质量报告 | **本仓库** `report` 子命令 | 简历 + 打招呼/求职信 vs JD |
| 人工「是否投」框架 | `04-job-evaluation.md` | 动机、文化、硬性否决项 |
| 重型语义匹配 UI | catalog Resume Matcher | 可选，非默认 |

## 命令

```bash
# 简历 vs JD 打分
python tools/match_resume.py score \
  --resume documents/zh/resume_示例.md \
  --jd /path/to/jd.md

# 只抽 JD 关键词
python tools/match_resume.py keywords --jd /path/to/jd.md

# 生成质量报告（/apply-zh 产出后必跑）
python tools/match_resume.py report \
  --resume documents/zh/resume_示例.md \
  --jd /path/to/jd.md \
  --cover documents/zh/da-zhaohu_示例_后端.md \
  --out documents/zh/match_report_示例.json

# JSON（agent 可读）
python tools/match_resume.py score --resume … --jd … --json
```

## 输出字段（摘要）

| 字段 | 含义 |
|------|------|
| `score` 0–100 | 0.55×余弦 + 0.45×关键词覆盖 |
| `keyword_coverage` | 命中 JD 关键词占比 |
| `keywords.hit` / `miss` | 命中 / 缺失关键词 |
| `verdict` | strong / moderate / partial / weak_match |
| `still_missing`（report） | 合并简历+话术后仍缺的词 |
| `suggestions` | 可操作建议（**禁止**据此虚构经历） |

## 工作流（agent）

1. 用户提供 JD 与简历（或 `/apply-zh` 刚写出的 `documents/zh/resume_*.md`）。
2. 跑 `score` 或 `report`，把 hit/miss 展示给用户。
3. 在**真实具备**的前提下，建议把 miss 词写入经历要点；不具备的明确标为缺口。
4. 人工是否投递仍看 `04-job-evaluation.md`（动机、通勤、文化、硬性否决项等 TF–IDF 评不了）。

## 合规

- 匹配分是**启发式**，不是录用预测；勿对用户夸大精度。
- 不得为提高分数编造技能或业绩。
- 简历数据本地处理，遵守 PIPL。

## 配合

- 生成材料 → `/apply-zh`、`/da-zhaohu`
- 追踪 → `tools/tracker.py`
- 可选神经匹配 → `integrations/catalog/resume-match/`
