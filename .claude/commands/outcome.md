# /outcome - Record the Result of an Application

You are recording what happened to a job application: progress updates (interview invitations, stages completed, offers), final resolutions (hired, rejected, no response), **and “chose not to apply” (`skipped` + reason)**.

Data lands in:

- `job_search_tracker.csv` — status (+ optional `skip_reason`, city/salary, notes) that `/scrape` / `/rank` and `tracker.py today` use
- `documents/applications/<company>_<role>/` — per-application archive (`outcome.md`, drafts, posting) that `/setup` Path A mines

`/outcome` writes the data; `/setup` interprets it. This command never edits the evaluation framework or profile files itself.

Follow these steps **in order**.

---

## Step 0: Parse Input

`$ARGUMENTS` may contain:

- Nothing → list open applications and ask which one to update
- A company name (optionally with a role), e.g. `/outcome acme` or `/outcome 星云科技 后端` → target that application
- A short phrase like `不投` / `skip` / `skipped` → still identify the row (or collect company/role), then go to the **skipped** path in Step 2

---

## Step 1: Load State and Identify the Application

1. Prefer the CLI (schema-safe) over hand-editing CSV:

   ```bash
   python tools/tracker.py list --open-only
   # or: python tools/tracker.py list
   ```

   If `job_search_tracker.csv` does not exist:

   ```bash
   python tools/tracker.py init
   ```

   Full header (18 columns; optional fields may be empty):

   ```
   date,company,sector,role,role_type,channel,status,contact_person,fit_rating,notes,
   cv_file,cover_letter_file,source,salary,city,education,experience,skip_reason
   ```

2. **With an argument:** match rows case-insensitively on company (and role, if given). One match → proceed. Several → list them and ask. None → application was made outside the workflow; collect company, role, date applied, channel, posting URL / `documents/zh/jd_*` path, then:

   ```bash
   python tools/tracker.py add --company … --role … --channel … --status to_apply|applied …
   ```

3. **Without an argument:** list rows whose status is **not** in the closed set  
   (`hired` / `rejected` / `no_response` / `withdrawn` / `offer_declined` / `interview_only` / `expired` / **`skipped`**)  
   as a numbered table (company, role, date, status, city if any) and ask which to update.  
   If every row is resolved, say so; still offer: “record a new skip?” or “add a row first?”

4. Derive archive folder: `documents/applications/<company>_<role>/` — lowercase, underscores for spaces (see `documents/README.md`). Check whether the folder and `outcome.md` already exist.

---

## Step 2: Collect What Happened

Ask the user what happened, then classify into **one** of the following.

### 2A. Progress updates (still open)

- Interview invitation / stage scheduled or completed
- Offer received (not yet accepted or declined)

Map to tracker status when appropriate: `screening` / `interview` / `interview_1` / `interview_2` / `interview_final` / `offer` / `in_progress`.

### 2B. Resolutions (application closed after applying)

| Status | Meaning |
|--------|---------|
| `hired` | accepted an offer |
| `offer_declined` | offer received, turned down |
| `rejected` | explicit rejection |
| `no_response` | no reply; if unsure, note days since last contact and let the user decide — do not impose a cutoff |
| `interview_only` | interviewed but process stalled without explicit rejection |
| `withdrawn` | user withdrew |

### 2C. Chose not to apply — `skipped` (**Phase 1 product signal**)

Use when the user evaluated the JD (often after `/apply-zh`) and **will not submit**.

1. Set tracker `status=skipped`.
2. **Required** — ask for **exactly one** `skip_reason`:

   | Key | 含义 |
   |-----|------|
   | `salary_low` | 薪资偏低 |
   | `location` | 地点不合适 |
   | `low_match` | 匹配度低 / 技能差太多 |
   | `unknown_company` | 不了解公司 |
   | `other` | 其他（put one line in `notes`） |

3. Prefer CLI (validates reason):

   ```bash
   python tools/tracker.py update \
     --company <公司> --role <岗位> \
     --status skipped \
     --skip-reason <salary_low|location|low_match|unknown_company|other> \
     --notes "YYYY-MM-DD skipped: <brief why>"
   ```

   If no row yet (never added):

   ```bash
   python tools/tracker.py add \
     --company <公司> --role <岗位> --channel <渠道> \
     --status skipped --skip-reason <…> \
     --source documents/zh/jd_<…>.md \
     --cv documents/zh/resume_<…>.md
   ```

4. Archive is optional for pure skips; if materials exist under `documents/zh/`, still archive lightly so future calibration can see “screened out” JDs.

Also collect (one or two open questions):

- Dates for stages reached
- Feedback received, verbatim when remembered
- What they'd do differently / what the company seemed to value

---

## Step 3: Archive the Application Materials

Create or update `documents/applications/<company>_<role>/`. Personal data — folder is gitignored.

1. **Submitted drafts** — copy (never move). Lookup order:
   1. Tracker columns `cv_file` / `cover_letter_file`
   2. **Domestic:** `documents/zh/resume_<company>.md` (+ `.pdf` if useful), `da-zhaohu_*` or `cover_*` → archive as `cv_draft.md` / `cover_letter.md`
   3. **International:** `cv/main_<company>.tex`, `cover_letters/cover_<company>_*.tex` → `cv_draft.tex` / `cover_letter.tex`

   Existing archive files are never overwritten (submitted snapshot wins).

2. **`job_posting.md`** — if missing: from tracker `source` URL (WebFetch), or `documents/zh/jd_*`, or user paste. Dead URL → stub “unavailable”. **Never invent a posting.**

3. **`outcome.md`** — write/update in this format (`documents/README.md` compatible):

```markdown
# Outcome: <Company> — <Role>

**Status:** in_progress | hired | offer_declined | rejected | no_response | interview_only | withdrawn | skipped

**Date resolved:** YYYY-MM-DD   <- only when resolved/skipped; omit while in_progress

**Skip reason:** salary_low | location | low_match | unknown_company | other   <- only when Status is skipped

## Interview stages reached
- [x] Phone screen (YYYY-MM-DD)
- [ ] Technical interview
- [ ] Case interview
- [ ] Final round
- [ ] Offer received

## Notes
<dated append-only notes>
```

Update rules: tick stages with dates; **append** Notes; only set final Status on resolution/skip. Re-runs are idempotent.

---

## Step 4: Update the Tracker

Prefer `tools/tracker.py` so schema and skip validation stay consistent:

```bash
python tools/tracker.py update \
  --company <公司> --role <岗位> \
  --status <new_status> \
  [--skip-reason <only if skipped>] \
  --notes-append "YYYY-MM-DD <what changed>" \
  [--city … --salary …]
```

- Prefer **`--notes-append`** so history is not wiped (`--notes` replaces the whole field).
- Never restructure the CSV, reorder rows, or touch unrelated rows.
- Leaving `skipped` for another status clears `skip_reason` automatically in the CLI.

---

## Step 5: Calibration Handoff

Count `outcome.md` files under `documents/applications/` with a **final** status  
(`hired` / `offer_declined` / `rejected` / `no_response` / `interview_only` / `withdrawn` / **`skipped`** — not `in_progress`).

- If **3+** resolved (or 2+ share a pattern), suggest `/setup` (Path A) for fit calibration and STAR mining.
- Do **not** edit `04-job-evaluation.md` yourself.

Also surface local product signal (no upload):

```bash
python tools/tracker.py skip-stats
```

If skip-stats reports **信号就绪 / 触发建议** (sample ≥10 and one reason ≥40%), mention that Phase 2 prioritization can use that signal (`docs/optimization-plan-close-the-loop.zh.md`).

---

## Step 6: Confirm + Flywheel (“然后呢”)

Summarize:

> **Outcome recorded for \<Role\> at \<Company\>.**
>
> - `documents/applications/<company>_<role>/outcome.md` — status: \<status\>[; skip_reason: …]
> - Archived: \<which files\>
> - Tracker: status → \<new status\>
>
> [Calibration suggestion from Step 5, if any]

### Always close with a short flywheel block (pick relevant bullets)

**If status is interview / offer / screening:**

> Interview coming up? `/interview <company>` builds a prep pack from this archive.

**If status is rejected / no_response / interview_only:**

> 想改进材料时：改 `documents/zh/resume_*.md` → 再跑  
> `python tools/match_resume.py report …` →  
> `python tools/match_resume.py diff --before …_v1.json --after …json`  
> 看关键词覆盖有没有真的变好（质量飞轮）。

**If status is skipped:**

> 已记入不投原因。汇总分布：`python tools/tracker.py skip-stats`  
> 日常：`python tools/tracker.py today` / `dashboard`。继续下一岗：`/apply-zh`。

**If hired / offer_declined:**

> 恭喜或尊重选择。需要时用 catalog 谈薪方法论（`integrations/catalog/salary-negotiate/`），默认不爬外部薪资站。

---

## Important Rules

1. **Write data, don't over-interpret.** Archive + tracker are outputs; calibration belongs to `/setup`.
2. **Archived version = submitted version.** Never overwrite archive drafts with newer edits.
3. **Never fabricate** postings or feedback.
4. **Schema-compatible.** Tracker 18 columns; `skipped` requires `skip_reason` via CLI validation.
5. **Idempotent updates.** Append notes/stages; no duplicate folders/rows/history.
6. **Domestic-first paths** when the user is on 中文岗: `documents/zh/` materials + `tracker.py`.
