# /reset - Reset Candidate Profile Data

You are resetting parts of the job search framework back to a blank state so the user can start fresh with `/setup`.

**This command is destructive.** Nothing is deleted until the user explicitly confirms. Follow these steps exactly in order.

---

## Step 0: Parse Scope from Arguments

Check `$ARGUMENTS` for a scope keyword:

- `profile` — clears candidate profile data from skill files only
- `documents` — deletes user-provided files from the `documents/` folder only
- `all` — both of the above

If `$ARGUMENTS` is empty or does not contain a recognized scope keyword, ask:

> **What would you like to reset?**
>
> - **`profile`** — Clears candidate data from the skill files (profile, behavioral, STAR examples, profile statements). The framework structure and writing rules are preserved. Use this to re-run `/setup` from scratch.
>
> - **`documents`** — Deletes all files you've placed in the `documents/` folder (CV PDFs, LinkedIn export, diplomas, references, past applications). The folder structure and `README.md` are preserved.
>
> - **`all`** — Both of the above.
>
> Reply with `profile`, `documents`, or `all`.

Wait for the user's response before continuing.

---

## Step 1: Show Exactly What Will Be Cleared

Before doing anything, show the user precisely what will be wiped.

### If scope includes `profile`:

Read the current state of these files and report whether each has content or is already empty:

- `.claude/skills/job-application-assistant/01-candidate-profile.md`
- `.claude/skills/job-application-assistant/02-behavioral-profile.md`
- `CLAUDE.zh.md` *(domestic 中文画像，由 /setup-zh 填充 — 仅清空候选专属板块，保留结构与指引)*
- `.claude/skills/job-application-assistant/05-cv-templates.md` *(profile statements section only — framework structure is preserved)*
- `.claude/skills/job-application-assistant/07-interview-prep.md` *(STAR examples and STAR candidates sections only — framework structure is preserved)*

Present as:

```
## Profile reset will clear:

- 01-candidate-profile.md — [has content / already empty]
  Full file will be replaced with a blank template.

- 02-behavioral-profile.md — [has content / already empty]
  Full file will be replaced with a blank template.

- CLAUDE.zh.md — [has content / already empty]
  Domestic 中文画像。候选专属板块（身份信息 / 教育背景 / 工作经历 / 专业技能 / 证书与荣誉 / 行为风格 / 求职方向）将还原为 `[占位符]` 形式，其余结构、注释与指引保留。

- 05-cv-templates.md — [has profile statements / already blank]
  Profile statement templates will be cleared. LaTeX structure and tailoring guidelines are preserved.

- 07-interview-prep.md — [has STAR examples / already blank]
  STAR examples and any STAR candidate stubs will be cleared. Framework, tough questions, and roleplay guidelines are preserved.

The following files are NOT touched (they contain framework rules, not candidate data):
  - 03-writing-style.md
  - 04-job-evaluation.md
  - 06-cover-letter-templates.md
```

### If scope includes `documents`:

Use Glob to list all files present in `documents/cv/`, `documents/linkedin/`, `documents/diplomas/`, `documents/references/`, `documents/zh/`, and `documents/applications/`. Present as:

```
## Documents reset will delete:

documents/cv/
  - [filename] or "(empty)"

documents/linkedin/
  - [filename] or "(empty)"

documents/diplomas/
  - [filename] or "(empty)"

documents/references/
  - [filename] or "(empty)"

documents/zh/
  - [filename] or "(empty)"  (domestic 中文简历 / 打招呼话术 — gitignored PII)

documents/applications/
  - [subfolder/filename] or "(empty)"

documents/README.md — NOT deleted (instructions file)
```

If all document subfolders are already empty, state "All document subfolders are already empty — nothing to delete." and skip the confirmation step for this scope.

---

## Step 2: Require Explicit Confirmation

Present the confirmation prompt:

> **This cannot be undone.**
>
> Type **`RESET`** (all caps) to confirm, or anything else to cancel.

Wait for the user's response.

- If the user types exactly `RESET`: proceed to Step 3.
- If the user types anything else: abort and tell them "Reset cancelled. Nothing was changed."

---

## Step 3: Execute the Reset

### Profile reset

**For `01-candidate-profile.md`**, replace the file content with:

```markdown
# Candidate Profile

<!-- Run /setup to populate this file -->

## Identity

## Education

## Professional Experience

## Independent Projects

## Technical Skills

## Publications

## Awards

## References
```

**For `02-behavioral-profile.md`**, replace the file content with:

```markdown
# Behavioral Profile

<!-- Run /setup to populate this file -->

## Overview

## Strongest Behavioral Traits

## How I Work Best

## Growth Areas

## Mapping to Job Posting Language

## Management Style Preferences

## Using This in Applications
```

**For `CLAUDE.zh.md`** (domestic 中文画像), replace only the candidate-specific sections with their `[占位符]` form — leave all headings, the `<!-- SETUP -->` comment, the 角色定位 / 国内岗位工作流 / 核查清单 sections, and the repository-structure note intact:

```markdown
### 身份信息
- **姓名：** [你的姓名]
- **所在地：** [城市]
- **语言：** [中文 / 英语等级 / 其他]
- **政治面貌：** [中共党员 / 共青团员 / 群众]（国企/体制内岗位重要）
- **求职状态：** [在职看机会 / 离职 / 应届]

### 教育背景
<!-- 倒序，最新在前 -->
- **[学历] [专业]** ([入学年]-[毕业年]) - [学校]
  - 主修课程 / GPA / 排名：[要点]

### 工作经历
<!-- 倒序，最新在前 -->
- **[职位]** ([起始月/年] - [结束月/年]) - **[公司]** ([城市])
  - [核心职责 1]
  - [量化业绩]

### 专业技能
- **主攻：** [你的核心技能]
- **次攻：** [次要技能]
- **领域：** [行业/领域专长]
- **工具：** [软件/工具]

### 证书与荣誉
- **[证书名]** - [机构] ([日期])
- **[荣誉名]** - [活动] ([年份])

### 行为风格
- **[特质 1]** - [描述]
- **优势：** [你的优势]
- **成长点：** [待提升处]

### 求职方向
- **目标行业：** [行业 1] / [行业 2]
- **目标岗位：** [岗位类型]
- **目标赛道：** [互联网 / 国企央企 / 外企 / 体制内 / 应届（可多选）]
- **薪资期望：** [范围，可选]
- **城市偏好：** [城市 1] / [城市 2]
```

**For `05-cv-templates.md`**, locate the section that begins with `**Profile statement templates` and extends through the role-specific template blocks. Replace only that section with:

```markdown
**Profile statement templates:**

<!-- Run /setup to populate role-specific profile statements -->
```

Leave all other content in `05-cv-templates.md` intact.

**For `07-interview-prep.md`**, locate and remove:
- The entire `## Ready-Made STAR Examples` section and all numbered STAR examples under it
- Any `## STAR Candidates (Complete Manually)` section added by `/setup` Path A

Replace with:

```markdown
## Ready-Made STAR Examples

<!-- Run /setup to populate STAR examples from your actual experience -->
```

Leave all other content in `07-interview-prep.md` intact (STAR format explanation, tough questions, questions to ask interviewers, phone/video tips, follow-up etiquette, roleplay guidelines).

### Documents reset

For each non-empty document subfolder, delete all files within it using Bash `rm`. Do not delete the folder itself, and do not delete `documents/README.md`.

```bash
rm -f documents/cv/*
rm -f documents/linkedin/*
rm -f documents/diplomas/*
rm -f documents/references/*
rm -f documents/zh/*
rm -rf documents/applications/*/
```

---

## Step 4: Confirm What Was Done and Next Steps

After the reset is complete, report:

```
## Reset complete

### Cleared
[List each file/folder that was actually modified or cleared]

### Unchanged
[List anything that was already empty or was intentionally preserved]
```

Then tell the user what to do next based on what was reset:

**If profile was reset:**
> Your candidate profile is now blank. Run `/setup` to repopulate it. The command auto-detects any files in your `documents/` folder and offers to read from there; otherwise it walks you through a CV import or interactive interview.

**If documents were reset:**
> The `documents/` folder is now empty. Add your career documents and run `/setup` to populate your profile. See `documents/README.md` for instructions on what to put where.

**If both were reset:**
> Both your profile files and documents folder are now empty. Add documents to `documents/` (or skip and use the CV import / interview path), then run `/setup`.
