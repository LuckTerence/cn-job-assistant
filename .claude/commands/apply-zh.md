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
- **落盘 JD**：写入 `documents/zh/jd_<company>_<role>.md`（纯文本即可）。

---

## Step 1: 匹配评估

读取画像与框架：
- **画像** → `CLAUDE.zh.md`（**不要**读英文 `01-candidate-profile.md`）
- **评估方法论** → `.claude/skills/job-application-assistant/04-job-evaluation.md`

按 04 给出 5 维评估与 1–3 个最强匹配点 / 诚实缺口。

若已有母版简历，可预检：

```bash
python tools/match_resume.py report --zh-only \
  --resume <母版> --jd documents/zh/jd_<company>_<role>.md
```

询问用户是否继续生成。

---

## Step 2: 中文简历草稿

- 读 `08-resume-zh.md`，按赛道选 `templates/zh/resume_<track>.md`。
- 写入 `documents/zh/resume_<company>.md`。
- **只写真实具备的技能**；可参考 `match_resume.py keywords --jd …`。
- 仅 Markdown；导出 PDF/DOCX 用户自理或见 `integrations/catalog/resume-build/`。

---

## Step 3: 打招呼 / 求职信

- 读 `09-da-zhaohu-zh.md`。
- Boss：40–80 字 → `documents/zh/da-zhaohu_<company>_<role>.md`
- 其他：正式信 → `documents/zh/cover_<company>_<role>.md`

---

## Step 4: 生成质量报告（强制）

```bash
python tools/match_resume.py report \
  --resume documents/zh/resume_<company>.md \
  --jd documents/zh/jd_<company>_<role>.md \
  --cover documents/zh/<da-zhaohu_or_cover>_<company>_<role>.md \
  --out documents/zh/match_report_<company>.json \
  --brief-out documents/zh/match_brief_<company>.txt
```

向用户**优先展示中文一页摘要**（命令默认已含【一页摘要 · 人话版】，或读 `match_brief_*.txt`）：
- 还差什么（still_missing）
- 建议改哪 3 条
- **禁止虚构**合规句

规则：真实具备的 miss → 回 Step 2/3 补一版；不具备 → 诚实标注。

若用户是在改第二版，可对比飞轮：

```bash
python tools/match_resume.py diff \
  --before documents/zh/match_report_<company>_v1.json \
  --after documents/zh/match_report_<company>.json
```

---

## Step 5: 合规自检

- [ ] 无虚构经历/技能
- [ ] 点名公司与岗位
- [ ] 已出 match 报告 + 人话摘要
- [ ] 不自动投递

---

## Step 6: Tracker 半自动挂钩（强制展示）

生成结束后，**必须**用工具打印一条可复制命令（把占位换成真实值）：

```bash
python tools/tracker.py suggest-add \
  --company <公司> \
  --role <岗位> \
  --channel <Boss直聘|智联|猎聘|51job|拉勾> \
  --cv documents/zh/resume_<公司>.md \
  --cover documents/zh/<话术或求职信文件>.md \
  --source documents/zh/jd_<公司>_<岗位>.md
```

把该命令的**完整输出**贴给用户，并说明：

1. 在 App 内**手动**投递后，终端执行上面这条（或让我代跑 `tracker add`）。
2. 每日入口：`python tools/tracker.py today`
3. 看板：`python tools/tracker.py dashboard`
4. 阶段变化：`/outcome <company>`

---

## Step 7: 呈现与交付

汇总路径：

- `documents/zh/resume_<company>.md`
- 话术 / 求职信
- `jd_*` · `match_report_*.json` · `match_brief_*.txt`
- 上方 **tracker suggest-add** 命令

国内闭环：
`install_domestic_search` → `/setup-zh` → 搜岗 → `/apply-zh` → 手动投 → `tracker.py today`。
