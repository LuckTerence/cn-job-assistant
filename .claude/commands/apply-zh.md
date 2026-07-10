# /apply-zh - 国内求职一站式编排（中文简历 + 打招呼话术）

你正在为一个**中国大陆市场的中文岗位**编排完整投递材料。岗位信息由 `$ARGUMENTS` 提供
（Boss直聘 / 智联 / 51job / 猎聘 / 拉勾 的链接或粘贴的 JD 文本）。

本命令是 `/apply` 的国内显式入口：强制 `MARKET=domestic`，走中文流程，不走 LaTeX。
严格按以下步骤执行，不要跳步。

---

## Step 0: 解析输入

- 若 `$ARGUMENTS` 是 URL，用 `WebFetch` 提取 JD 正文；若是文本，直接使用。
- 抽取：**公司名、岗位名、城市、薪资、经验要求、学历要求、硬性技能、岗位职责**。
- 若平台是 Boss直聘，标记为"短话术模式"；否则标记为"正式求职信模式"。
- **落盘 JD**（供后续量化匹配）：写入 `documents/zh/jd_<company>_<role>.md`（纯文本即可）。

---

## Step 1: 匹配评估

读取画像与框架：
- **画像（候选信息）** → `CLAUDE.zh.md`（国内中文岗由 `/setup-zh` 填充的画像源；**不要**读英文 `01-candidate-profile.md`）
- **评估方法论** → `.claude/skills/job-application-assistant/04-job-evaluation.md`（语言无关框架，照常读取）

按 04 框架给出 5 维评估（技能匹配 / 经历匹配 / 行为匹配 / 薪资基准可选 / 综合建议），
并指明 1–3 个最强匹配点与需诚实处理的缺口。

若已有母版简历（`documents/zh/` 或用户提供），可先跑量化预检：

```bash
python tools/match_resume.py score --resume <母版简历路径> --jd documents/zh/jd_<company>_<role>.md
```

询问用户是否继续生成材料。
（薪资基准 `salary_lookup.py` 面向海外，国内岗可跳过或改用画像中的期望薪资。）

---

## Step 2: 中文简历草稿（内容，非版式）

- 读取 `.claude/skills/job-application-assistant/08-resume-zh.md`，按赛道选模板
  （`templates/zh/resume_<track>.md`：互联网 / 国企央企 / 外企 / 体制内 / 应届）。
- 写入 Markdown 源文件 `documents/zh/resume_<company>.md`（中文，社招严格一页）。
- 按 JD 定制要点，遵循 08 的一页纸硬约束与分赛道差异（如国企放证件照、外企中英双语）。
- **只写入用户真实具备的技能**；可参考 `match_resume.py keywords --jd …` 的关键词列表做对齐，
  miss 列表中不具备的项**不得**硬写进简历。
- 本步骤只产出 **Markdown 草稿**（不手写 .docx）。导出 PDF/DOCX 可用任意编辑器，
  或可选自托管 Reactive-Resume（见 `integrations/catalog/resume-build/`，非核心依赖）。

---

## Step 3: 打招呼话术 / 中文求职信

- 读取 `09-da-zhaohu-zh.md` 生成：
  - Boss直聘：40–80 字短话术（身份+最强匹配+量化证据+沟通意愿）。
  - 智联/51job/猎聘：300–400 字正式中文求职信（开头→主体→结尾→落款）。
- 输出写入 `documents/zh/da-zhaohu_<company>_<role>.md` 或 `documents/zh/cover_<company>_<role>.md`。

---

## Step 4: 生成质量量化报告（强制）

对刚产出的材料跑本地匹配引擎（stdlib，无网络、无模型下载）：

```bash
python tools/match_resume.py report \
  --resume documents/zh/resume_<company>.md \
  --jd documents/zh/jd_<company>_<role>.md \
  --cover documents/zh/<da-zhaohu_or_cover>_<company>_<role>.md \
  --out documents/zh/match_report_<company>.json
```

向用户展示报告摘要：
- `summary.combined_score` / `verdict` / `keyword_coverage_combined`
- `still_missing`（合并材料后仍缺的 JD 词）
- `suggestions`

**规则**：若 `still_missing` 中有用户**真实具备**但未写入的词 → 回到 Step 2/3 补一版；
若用户不具备 → 在交付说明里诚实标注缺口，**禁止**为刷分虚构。

---

## Step 5: 合规自检（强制）

- [ ] 经历/数据真实，无虚构技能或业绩
- [ ] 简历与话术均点名公司与岗位
- [ ] 关键词仅在真实具备时对齐 JD
- [ ] 已生成 `match_report_*.json` 并解读分数局限（启发式，非录用预测）
- [ ] 不自动投递——用户手动粘贴进 App（规避平台风控）

---

## Step 6: 呈现与交付

向用户说明：

> "材料已写入 `documents/zh/`：
> - 简历 `resume_<company>.md`
> - 话术/求职信
> - JD 原文 `jd_<company>_*.md`
> - 质量报告 `match_report_<company>.json`（score / hit / miss）
>
> 请在对应 App 内**手动**投递。投递后：
> 1. `python tools/tracker.py add --company <公司> --role <岗位> --channel <渠道> --status applied --cv documents/zh/resume_<公司>.md`
> 2. 或 `/outcome <company>` 归档。
> 总览：`python tools/tracker.py list --open-only` / `dashboard`。"

国内闭环：
`install_domestic_search` → `/setup-zh` → 搜岗 → `/apply-zh`（含 match 报告）→ 手动投递 → `tracker.py`。
可选重应用见 `integrations/catalog/`。
