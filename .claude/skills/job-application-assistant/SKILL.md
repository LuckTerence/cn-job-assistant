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
| `resume-build`（`.agents/skills/`） | **简历构建与导出**轮子（复用 Reactive-Resume，PDF/JSON/DOCX） |
| `resume-match`（`.agents/skills/`） | **JD↔简历匹配 + ATS 优化**轮子（复用 Resume Matcher，替代手写评分） |
| `interview-mock`（`.agents/skills/`） | **模拟面试 + 多维评分**轮子（复用 AuraInterviewer，替代手写模拟） |
| `application-tracker`（`.agents/skills/`） | **投递状态追踪 / 求职看板**轮子（复用 jobsync，MIT，自托管） |
| `salary-negotiate`（`.agents/skills/`） | **谈薪策略 + 话术**轮子（复用 Salary-Negotiation-Skill，五阶段引擎 + Qwen2.5-7B） |
| `job-alert`（`.agents/skills/`） | **招聘事件→Apple 提醒**轮子（复用 offercatcher，MIT，邮件解析桥接） |
| `referral-outreach`（`.agents/skills/`） | **内推/冷触达序列**轮子（复用 outreach-ai，MIT，多通道 + 批量） |

---

## Quick Commands

The user may also ask for individual steps without the full workflow:
- "Evaluate this job posting" - Step 1 only
- "Write a CV for [company]" - Step 2 only
- "Write a cover letter for [role] at [company]" - Step 3 only
- "Help me prepare for an interview at [company]" - Step 4 only
- "What jobs should I look for?" - Career strategy discussion using profile + evaluation framework
- "把这份中文 JD 走国内流程" - `/apply-zh <JD>`（或 `/apply` 自动识别中文市场）：中文简历 + 打招呼话术，不生成 LaTeX

---

## 中文 / 国内求职工作流（China workflow）

当岗位为**中国大陆市场、中文 JD** 时，自动切换到国内流程：

1. **检索**：直接复用成熟开源实现，不自行造轮子——
   - **Boss直聘** → `.agents/skills/bosszhipin-search`（复用 **[jackwener/boss-cli](https://github.com/jackwener/boss-cli)**，Apache-2.0，逆向 API CLI，支持 `search/recommend/greet/export`）
   - **智联招聘 / 前程无忧 51job / 猎聘 / 拉勾** → `.agents/skills/domestic-jobs-search`（复用 **[loks666/get_jobs](https://github.com/loks666/get_jobs)**，Java + Playwright 浏览器自动化，四平台统一覆盖）
   - **MCP 原生调用** → 可接 **[mergedao/mcp-jobs](https://github.com/mergedao/mcp-jobs)**（猎聘/Boss/智联/51job，自然语言触发，适合 agent 直接调用）
   - 浏览器注入方案另见 **[yangfeng20/ai-job](https://github.com/yangfeng20/ai-job)**（油猴脚本 + Spring AI + 拦截 BOSS 直聘 Protobuf）
2. **简历**：内容规范用 `08-resume-zh.md` + `templates/zh/resume_<track>.md`
   （互联网 / 国企央企 / 外企 / 体制内 / 应届 五赛道）；**实际构建与导出复用 `resume-build` 技能**
   （Reactive-Resume，导出 PDF/JSON/DOCX，优先 DOCX），停止手写 .docx 生成逻辑。
3. **开场**：用 `/打招呼 <JD>` 生成**打招呼话术**（Boss直聘）或**正式中文求职信**
   （智联/51job/猎聘），见 `09-da-zhaohu-zh.md`；生成文本由用户粘贴进 boss-cli `greet` /
   get_jobs 的 AI 招呼语配置。
4. **不自动投递**：本仓库统一策略为"生成辅助内容，用户手动在 App 内投递"，以规避平台风控与合规风险。
   （get_jobs、mcp-jobs 自身具备自动投递能力，是否启用由用户自行决定并知悉平台协议风险。）
5. **投递后闭环**：拿到面试 / offer 后，复用成熟轮子而非手写——
   - **招聘事件提醒** → `.agents/skills/job-alert`（复用 **[NissonCX/offercatcher](https://github.com/NissonCX/offercatcher)**，MIT，扫描 Apple Mail → AI 提取面试/笔试/测评/截止 → 写入 Apple Reminders；**非**平台监控器）
   - **谈薪策略与话术** → `.agents/skills/salary-negotiate`（复用 **[Ssupercoder/Salary-Negotiation-Skill](https://github.com/Ssupercoder/Salary-Negotiation-Skill)**，LLM Agent，谈薪五阶段引擎 + Qwen2.5-7B + RAG 市场锚点；**仓库未声明许可证**，仅作方法论参考）
   - **内推 / 冷触达** → `.agents/skills/referral-outreach`（复用 **[quionie/outreach-ai](https://github.com/quionie/outreach-ai)**，MIT，多通道冷邮件/DM 序列 + 批量 CSV，Claude/OpenAI/Ollama）
   - **投递状态追踪 / 看板** → `.agents/skills/application-tracker`（复用 **[Gsync/jobsync](https://github.com/Gsync/jobsync)**，MIT，自托管 Job Application Tracker + AI 职业助手；此前多轮仅作可选参考，本轮正式接入为状态追踪落点）

> 海外 / 英文岗仍走原 `05`/`06` LaTeX 流程。中文 JD 由 `/apply` 在 Step 0 自动识别市场并转入本流程
> （或显式调用 `/apply-zh`）。详见 `README.zh.md` 与 `MODELS.zh.md`。
