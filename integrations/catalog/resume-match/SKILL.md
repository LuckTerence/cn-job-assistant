---
name: resume-match
version: 1.1.0
description: >
  简历与 JD 的匹配度分析、关键词提取与定制建议。本技能复用开源项目 Resume Matcher
  （srbhr/Resume-Matcher，Apache-2.0，27k+★ 的简历↔JD 匹配器，基于 embedding 的语义匹配 +
  关键词抽取 + 排名 + 定制内容/求职信生成），而非自行实现评分脚本。触发词：匹配度、JD 匹配、关键词、
  简历诊断、skills gap、简历定制、简历优化。
context: fork
allowed-tools: Read, Glob, Grep, WebFetch, WebSearch, AskUserQuestion, Bash(python*), Bash(uv*), Bash(pip*)
---
> ⚠️ **可选重型集成**：默认请用核心 skill **`resume-match`** → `python tools/match_resume.py`
> （本地 TF–IDF，无模型下载）。本目录描述的是上游 **Resume Matcher** 全量应用
> （sentence-transformers + UI，首次需下 embedding 权重），仅在需要神经语义匹配时自托管。


# 简历匹配与优化技能（复用 Resume Matcher）

> **不要重复造轮子**：JD↔简历的语义匹配、关键词抽取、匹配度排名、按 JD 定制内容，已由成熟开源项目
> [srbhr/Resume-Matcher](https://github.com/srbhr/Resume-Matcher)（**Apache-2.0**，27k+★，4.9k forks）
> 完整实现——它基于句向量（sentence-transformers）做简历与 JD 的余弦相似度匹配，抽取关键词并排序，
> 还能生成定制内容与求职信。本技能直接复用它，不再手写 `04-job-evaluation.md` 里的评分脚本逻辑；
> 本仓库 `04-job-evaluation.md` 降为**人工评估框架**指引（何时打分、看哪些维度）。

## 关于上游选型的诚实说明（测试发现的修正）

- **原参考 `wzx11223344/resume-customizer` 不可用**：经克隆核验，该仓库仅含 `LICENSE` / `README.md` /
  `SKILL.md` 三个文件（约 7 KB），其 README 与 SKILL.md 中描述的 `scripts/parse_resume.py`、
  `skill_match.py`、`ats_optimizer.py` 等脚本**在仓库中并不存在**，且 GitHub 返回的许可证为
  `NOASSERTION`（其 LICENSE 文件仅两行 "MIT License"，无完整文本）。该仓库属"仅有提示词、无可运行代码"
  的空壳，故**已弃用**为匹配轮子。
- **现改用 `srbhr/Resume-Matcher`**：Apache-2.0、含真实可运行代码（`scripts/`、`apps/`）、社区活跃，
  是同类项目中最成熟的实现，作为本技能的复用底座。

## 复用关系

| 能力 | 由谁实现 | 说明 |
|------|----------|------|
| 简历↔JD 语义匹配 | **Resume Matcher**（embedding 余弦相似度） | 简历与 JD 向量化后计算匹配度，输出排名 |
| 关键词抽取与排名 | **Resume Matcher** | 从 JD 抽取关键词并与简历比对，给出缺失/命中关键词 |
| 定制内容生成 | **Resume Matcher**（上传母版简历 + 粘贴 JD） | AI 生成针对性改进建议与定制内容 |
| 求职信 / 面试准备 | **Resume Matcher**（可选） | 针对该岗位生成 cover letter 与面试题准备 |
| 导出 | **Resume Matcher** | 导出为专业 PDF（多模板） |
| 人工评估框架 | **本仓库** `04-job-evaluation.md` | 何时评估、看哪些维度（保留为方法论） |

## 技术要点（来自其官方文档）

- **协议**：Apache-2.0（明确声明，非 NOASSERTION）。
- **形态**：本地运行的 Python 应用（基于 sentence-transformers + Streamlit/FastAPI），数据不出本地。
- **输入**：母版简历 PDF / DOCX；目标 JD 以文本粘贴。
- **输出**：匹配度排名、关键词清单、定制内容、求职信、可导出 PDF。
- **依赖**：需本地 Python 环境与向量模型（首次运行会下载 embedding 模型权重）。

## 工作流（本技能如何编排）

1. 用户提供母版简历（PDF/DOCX）与目标 JD（文本）。
2. 用 **Resume Matcher** 得到**匹配度排名**与**关键词命中/缺失清单**（即"匹配度"的量化依据）。
3. 依据排名与缺失关键词，给出**定制建议**（哪些经历要突出、补哪些 JD 关键词）。
4. 定制后的内容交给 `resume-build`（Reactive-Resume）做样式与导出；人工侧评估回到
   `04-job-evaluation.md`（何时投、风险判断）。

## 安装与运行（摘要，以 Resume Matcher 仓库为准）

```bash
git clone https://github.com/srbhr/Resume-Matcher.git
cd Resume-Matcher
# 官方推荐用 uv 启动其应用（Streamlit UI）
uv run app
# 详见仓库 README / SETUP.md（含 data/ 目录放简历、粘贴 JD 等步骤）
```

> 注：Resume Matcher 为带 UI 的本地应用，首次运行需下载 embedding 模型权重（联网一次）。
> 精确命令与目录约定以其仓库文档为准，本技能不臆造 CLI 参数。

## 合规与边界

- 简历含个人信息，本地运行优先，谨慎分享，遵守 PIPL。
- AI 定制不得虚构经历/业绩；缺失技能如实标注，不硬凑。
- 关键词自然融入，不堆砌（ATS 会降权）。

## 与其他技能的配合

- 人工评估框架 → `04-job-evaluation.md`
- 简历构建/导出 → `resume-build`（Reactive-Resume）
- 分赛道结构规范 → `08-resume-zh.md` + `templates/zh/`
- 模拟面试 → `interview-mock`（AuraInterviewer）
- 岗位检索 → `bosszhipin-search` / `domestic-jobs-search`
