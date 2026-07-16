---
name: resume-match
version: 2.3.0
description: >
  本地轻量简历↔岗位描述 匹配与生成质量报告。使用 tools/match_resume.py（stdlib：TF–IDF 余弦
  + 关键词命中/缺失 + 同义词表 + 期望薪资 vs JD 区间，无 embedding 下载）。触发词：匹配度、
  岗位匹配、关键词、简历诊断、skills gap、薪资对照、同义词、quality report、ATS 关键词。
context: fork
allowed-tools: Bash(python* tools/match_resume.py *), Bash(python3 tools/match_resume.py *), Read, Glob, Grep, AskUserQuestion
---

# 简历匹配技能（本地轻量 CLI）

> **思路复用 Resume Matcher，依赖不复用其重栈。**  
> [srbhr/Resume-Matcher](https://github.com/srbhr/Resume-Matcher)（Apache-2.0）用
> sentence-transformers + 余弦相似度做语义匹配；本仓库取同一思路的**可本地、零模型下载**
> 版本：`TF–IDF 向量 + 余弦 + 岗位关键词命中/缺失`，见 `tools/match_resume.py`。  
> 需要完整 UI / 神经 embedding 时，见可选集成
> `integrations/catalog/resume-match/`（上游 Streamlit 应用，百 MB 级权重）。

## 复用关系

| 能力 | 实现 | 说明 |
|------|------|------|
| 向量相似度 | **本仓库** TF–IDF 余弦 | 无网络、无模型权重 |
| 关键词 hit/miss | **本仓库** 岗位描述 加权抽取 | 中英双语 + **同义词簇** |
| 期望 vs JD 薪资 | **本仓库** 本地解析 | 画像 `薪资期望` 或 `--expected-salary`；**不爬站** |
| 生成质量报告 | **本仓库** `report` 子命令 | 简历 + 打招呼/求职信 vs 岗位描述 |
| 人工「是否投」框架 | `04-job-evaluation.md` | 动机、文化、硬性否决项 |
| 重型语义匹配 UI | catalog Resume Matcher | 可选，非默认 |

## 命令

```bash
# 简历 vs 岗位描述 打分（默认读 config/synonyms.default.json）
python tools/match_resume.py score \
  --resume documents/zh/resume_示例.md \
  --jd /path/to/jd.md

# 只抽 岗位关键词
python tools/match_resume.py keywords --jd /path/to/jd.md

# 生成质量报告（中文摘要含薪资对照）
python tools/match_resume.py report \
  --resume documents/zh/resume_示例.md \
  --jd /path/to/jd.md \
  --cover documents/zh/da-zhaohu_示例_后端.md \
  --profile CLAUDE.zh.md \
  --expected-salary '25-40K' \
  --out documents/zh/match_report_示例.json \
  --brief-out documents/zh/match_brief_示例.txt

# 只要人话摘要
python tools/match_resume.py report --zh-only --resume … --jd … --cover …

# 单独比薪资（零爬虫）
python tools/match_resume.py salary --jd path/to/jd.md --expected '25-40K'

# 质量飞轮：对比两版报告
python tools/match_resume.py diff \
  --before documents/zh/match_report_v1.json \
  --after documents/zh/match_report_v2.json

# 只要「改这 3 条」（JD 用词对齐，禁止虚构）
python tools/match_resume.py align --resume … --jd …

# 投前一键门禁（匹配 + 诚信 + ATS）
python tools/quality_gate.py --resume … --jd … --pdf … --profile CLAUDE.zh.md
# 或：python tools/flow.py gate --resume … --jd …

# JSON（agent 可读）
python tools/match_resume.py score --resume … --jd … --json
# 关闭同义词（A/B）：加 --no-synonyms
# 赛道同义词：--track internet|soe|foreign|civil|freshgrad

# 多对批打分（manifest JSON）
python tools/match_resume.py batch --manifest pairs.json --track internet --out ranked.json
```

## 同义词

- 默认：`config/synonyms.default.json`（高并发↔大流量、微服务↔分布式架构 …）
- **赛道**：同文件 `tracks.internet` / `tracks.soe` … 或 `config/synonyms.track.<name>.json`
- 本地覆盖：复制 `config/synonyms.example.json` → `config/synonyms.json`（gitignore）
- 簇内任一词出现在简历原文或 token 中，JD 同簇词计为 **hit**

短名单批打分也可：`python tools/tracker.py rank`（读 tracker 的 cv_file + source）。

## 输出字段（摘要）

| 字段 | 含义 |
|------|------|
| `score` 0–100 | 0.55×余弦 + 0.45×关键词覆盖 |
| `keyword_coverage` | 命中 岗位关键词占比（含同义词） |
| `keywords.hit` / `miss` | 命中 / 缺失关键词 |
| `verdict` | strong / moderate / partial / weak_match |
| `still_missing`（report） | 合并简历+话术后仍缺的词 |
| `salary`（report） | 期望 vs JD：`signal` ✅/⚠️/❌、`verdict`、`summary` |
| `suggestions` | 可操作建议（**禁止**据此虚构经历） |
| `action_checklist` | 最多 3 条「改这 3 条」（term + 写法 + fiction_forbidden） |

## 工作流（agent）

1. 用户提供 岗位描述 与简历（或 `/apply-zh` 刚写出的 `documents/zh/resume_*.md`）。
2. 跑 `report` 或 `align`，展示 **【改这 3 条】** 与 hit/miss。
3. 在**真实具备**的前提下，建议把 miss 词写入经历要点；不具备的明确标为缺口。
4. **投前必须** `quality_gate`（SOFT 默认阻断，HARD 诚信阻断）。
5. 人工是否投递仍看 `04-job-evaluation.md`（动机、通勤、文化、硬性否决项等 TF–IDF 评不了）。
6. 过筛说明见 `docs/ats-gate.zh.md`。

## 合规

- 匹配分是**启发式**，不是录用预测；勿对用户夸大精度。
- 不得为提高分数编造技能或业绩。
- 简历数据本地处理，遵守 PIPL。

## 配合

- 生成材料 → `/apply-zh`、`/da-zhaohu`
- 追踪 → `tools/tracker.py`
- 可选神经匹配 → `integrations/catalog/resume-match/`
