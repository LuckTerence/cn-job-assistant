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

---

## Step 1: 匹配评估

读取画像与框架：
- **画像（候选信息）** → `CLAUDE.zh.md`（国内中文岗由 `/setup-zh` 填充的画像源；**不要**读英文 `01-candidate-profile.md`）
- **评估方法论** → `.claude/skills/job-application-assistant/04-job-evaluation.md`（语言无关框架，照常读取）

按 04 框架给出 5 维评估（技能匹配 / 经历匹配 / 行为匹配 / 薪资基准可选 / 综合建议），
并指明 1–3 个最强匹配点与需诚实处理的缺口。询问用户是否继续生成材料。
（薪资基准 `salary_lookup.py` 面向海外，国内岗可跳过或改用 `/setup` 记录的期望薪资。）

---

## Step 2: 中文简历草稿（内容，非版式）

- 读取 `.claude/skills/job-application-assistant/08-resume-zh.md`，按赛道选模板
  （`templates/zh/resume_<track>.md`：互联网 / 国企央企 / 外企 / 体制内 / 应届）。
- 写入 Markdown 源文件 `documents/zh/resume_<company>.md`（中文，社招严格一页）。
- 按 JD 定制要点，遵循 08 的一页纸硬约束与分赛道差异（如国企放证件照、外企中英双语）。
- **构建与导出由用户通过 `resume-build` 技能（Reactive-Resume，自托管）完成**：
  导入该 Markdown 后导出 `.docx`（WPS/ATS 优先）或 `.pdf`。本步骤不手写 .docx。

---

## Step 3: 打招呼话术 / 中文求职信

- 调用 `/da-zhaohu <JD>`（读取 `09-da-zhaohu-zh.md`）生成：
  - Boss直聘：40–80 字短话术（身份+最强匹配+量化证据+沟通意愿）。
  - 智联/51job/猎聘：300–400 字正式中文求职信（开头→主体→结尾→落款）。
- 输出写入 `documents/zh/`。

---

## Step 4: 合规自检（强制）

- [ ] 经历/数据真实，无虚构技能或业绩
- [ ] 简历与话术均点名公司与岗位
- [ ] 关键词仅在真实具备时对齐 JD
- [ ] 不自动投递——用户手动粘贴进 App（规避平台风控）

---

## Step 5: 呈现与交付

向用户说明：

> "中文简历草稿已写入 `documents/zh/resume_<company>.md`，请在 Reactive-Resume
> （`/resume-build`）导入并导出 .docx；打招呼话术已生成于 `documents/zh/`，请手动粘贴投递。
> 投递后运行 `/outcome <company>` 记录进度。"

国内链路组合：`bosszhipin-search` / `domestic-jobs-search`（检索）+ `08-resume-zh.md`（简历）
+ `resume-build`（构建导出）+ `09-da-zhaohu-zh.md` / `/da-zhaohu`（开场）+ 手动投递。
