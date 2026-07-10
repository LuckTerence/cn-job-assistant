---
name: job-application-assistant
description: >
  Assists with job applications: evaluating job postings, tailoring CVs, writing cover letters,
  and preparing for interviews. Triggers on keywords like: job posting, job application, CV,
  cover letter, resume, interview prep, job fit, career, application, apply, ansøgning, stilling
allowed-tools: Read, Glob, Grep, WebFetch, WebSearch, Edit, Write, AskUserQuestion
---

# Job Application Assistant

---

## Workflow

When the user provides a job posting (URL or text), follow this workflow:

### Step 1: Research & Evaluate Fit
- Fetch the job posting content (use WebFetch for URLs)
- Analyze the posting for required competencies, keywords, and priorities
- Research the company (website, LinkedIn, mission, recent news)
- Score the posting against the candidate's profile using the framework in `04-job-evaluation.md`
- Present the evaluation table and verdict
- Suggest whether the candidate should call the employer before applying (see `04-job-evaluation.md` for guidance)
- Ask the user if they want to proceed with an application

### Step 2: Tailor CV
- Read the most relevant existing CV variant from `cv/` as a starting point
- Follow the guidelines in `05-cv-templates.md`
- Create `cv/main_<company>.tex` with tailored content
- Adjust: profile statement, skills section, experience bullet emphasis, section order

### Step 3: Write Cover Letter
- Follow the writing style rules in `03-writing-style.md` (critical: no em-dashes, no cliches)
- Follow the template structure in `06-cover-letter-templates.md`
- Create `cover_letters/cover_<company>_<role>.tex`
- Ensure the letter connects specific experience to the role requirements

### Step 4: Interview Preparation
- Follow the framework in `07-interview-prep.md`
- Prepare STAR-format answers for likely questions
- Identify role-specific talking points
- Draft questions the candidate should ask the interviewer

---

## Reference Files

| File | Purpose |
|------|---------|
| `01-candidate-profile.md` | Education, experience, skills, publications, awards |
| `02-behavioral-profile.md` | Behavioral assessment, strengths, ideal environments |
| `03-writing-style.md` | Tone, structure, do's and don'ts |
| `04-job-evaluation.md` | Scoring framework for job fit |
| `05-cv-templates.md` | LaTeX CV structure and tailoring rules |
| `06-cover-letter-templates.md` | LaTeX cover letter structure and tailoring rules |
| `07-interview-prep.md` | STAR examples, tough questions, roleplay guidelines |
| `08-resume-zh.md` | **中文简历**结构、分赛道模板与一页纸规则（国内岗） |
| `09-da-zhaohu-zh.md` | **打招呼话术 / 中文求职信**生成指南（国内岗，替代 Cover Letter） |
| `application-tracker`（`.agents/skills/`） | **本地投递追踪**（`tools/tracker.py` + `job_search_tracker.csv`） |
| `resume-match`（`.agents/skills/`） | **本地匹配/质检**（`tools/match_resume.py`，TF–IDF + 关键词） |
| `bosszhipin-search` / `domestic-jobs-search` | 国内搜岗（安装器：`tools/install_domestic_search.py`） |
| `integrations/catalog/*` | **可选**重依赖（Reactive-Resume / 全量 Resume Matcher / 模拟面试等） |

---

## Quick Commands

The user may also ask for individual steps without the full workflow:
- "Evaluate this job posting" - Step 1 only
- "Write a CV for [company]" - Step 2 only
- "Write a cover letter for [role] at [company]" - Step 3 only
- "Help me prepare for an interview at [company]" - Step 4 only
- "What jobs should I look for?" - Career strategy discussion using profile + evaluation framework
- "把这份中文 岗位描述 走国内流程" - `/apply-zh <岗位描述>`（或 `/apply` 自动识别中文市场）：中文简历 + 打招呼话术，不生成 LaTeX

---

## 中文 / 国内求职工作流（China workflow）

当岗位为**中国大陆市场、中文 JD** 时，自动切换到国内流程：

1. **安装搜岗后端**：`python tools/install_domestic_search.py install-boss`（或 `install-get-jobs`）。
   - **Boss直聘** → `.agents/skills/bosszhipin-search`（复用 **[jackwener/boss-cli](https://github.com/jackwener/boss-cli)**；上游许可证未声明）
   - **智联 / 51job / 猎聘 / 拉勾** → `.agents/skills/domestic-jobs-search`（复用 **[loks666/get_jobs](https://github.com/loks666/get_jobs)**，禁商用）
2. **简历**：`08-resume-zh.md` + `templates/zh/resume_<track>.md` → Markdown 草稿
   `documents/zh/resume_<company>.md`（不手写 .docx；可选导出见 `integrations/catalog/resume-build/`）。
3. **开场**：`/da-zhaohu` 或 `/apply-zh` → 打招呼话术 / 中文求职信（`09-da-zhaohu-zh.md`）。
4. **量化质检**：`python tools/match_resume.py report --resume … --jd … --cover …`
   （`/apply-zh` Step 4 强制；禁止为刷分虚构技能）。
5. **不自动投递**：用户在 App 内手动投递。
6. **追踪**：`python tools/tracker.py add/list/update/dashboard`（CSV 权威源）；阶段变化 `/outcome`。
7. **可选重应用**（非核心）：`integrations/catalog/`（神经匹配 UI / 模拟面试 / 谈薪方法论等）。

> 海外 / 英文岗仍走原 `05`/`06` LaTeX 流程。中文 岗位描述 由 `/apply` 在 Step 0 自动识别市场并转入本流程
> （或显式调用 `/apply-zh`）。详见 `README.zh.md` 与 `MODELS.zh.md`。
