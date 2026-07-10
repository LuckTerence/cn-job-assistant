# /apply-zh - 国内求职一站式编排（中文简历 + 打招呼话术）

你正在为一个**中国大陆市场的中文岗位**编排完整投递材料。岗位信息由 `$ARGUMENTS` 提供
（Boss直聘 / 智联 / 51job / 猎聘 / 拉勾 的链接或粘贴的 岗位描述 文本）。

本命令是 `/apply` 的国内显式入口：强制 `MARKET=domestic`，走中文流程，不走 LaTeX。
严格按以下步骤执行，不要跳步。

---

## Step 0: 解析输入

- 若 `$ARGUMENTS` 是 URL，用 `WebFetch` 提取 岗位描述 正文；若是文本，直接使用。
- 抽取：**公司名、岗位名、城市、薪资、经验要求、学历要求、硬性技能、岗位职责**。
- 若平台是 Boss直聘，标记为"短话术模式"；否则标记为"正式求职信模式"。
- **落盘岗位描述**：写入 `documents/zh/jd_<company>_<role>.md`（纯文本即可；文件名里的 `jd_` 表示岗位描述）。

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

## Step 2: 中文简历草稿 + **可投递 PDF（必须）**

- 读 `08-resume-zh.md`，按赛道选 `templates/zh/resume_<track>.md`。
- 写入 `documents/zh/resume_<company>.md`（源文件，便于改）。
- **只写真实具备的技能**；可参考 `match_resume.py keywords --jd …`。
- **国内投递默认交付物是 PDF**，不是 Markdown。生成 md 后**必须**导出：

```bash
python tools/export_resume_pdf.py \
  --input documents/zh/resume_<company>.md \
  --output documents/zh/resume_<company>.pdf
```

- 向用户明确：上传平台时用 **`.pdf`**；md 只是源文件。
- 若本机无 Chrome/Chromium/Edge，工具会报错并写出 `.html`，指导用户「打印 → 另存 PDF」。
- 不要只丢给用户一份 md 就结束本步。

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
- [ ] 投递方式按用户选择的模式执行（见 Step 6）；**未选择时默认手动**

---

## Step 6: 投递模式（选择权在用户）

先读当前模式（不要替用户改成 auto）：

```bash
python tools/apply_assist.py status
```

| 模式 | 行为 | 谁点发送 |
|------|------|----------|
| **manual**（默认） | 只给材料路径，用户去 App 操作 | 用户 |
| **semi** | 打开岗位链接 + 复制话术到剪贴板 | 用户（最后一下） |
| **auto** | 可走 boss-cli 代发；多重门禁，默认 dry-run | 脚本（高风险） |

### 6A 默认 manual

告知用户：把话术/简历粘贴到 App，自己点发送。

### 6B semi（推荐「好用」）

若用户已 `set-mode semi`，或用户说「半自动 / 帮我打开页面复制话术」，执行：

```bash
python tools/apply_assist.py semi \
  --url "<岗位链接，若有>" \
  --text-file documents/zh/<da-zhaohu或cover文件>.md \
  --company <公司> --role <岗位> --channel <渠道>
```

强调：**发送按钮仍须用户自己点**；本步不调用任何自动打招呼 API。

### 6C auto（仅当用户明确要求全自动）

1. 确认用户知道封号风险；引导其：
   ```bash
   python tools/apply_assist.py explain
   python tools/apply_assist.py set-mode auto   # 需输入 YES
   # 编辑 config/apply_mode.yaml：risk_acknowledgement 三项改为 true
   ```
2. **禁止**在未完成上述配置时调用 `boss greet` / `batch-greet`。
3. 真正发送前必须 dry-run，再由用户加 `--execute`：
   ```bash
   python tools/apply_assist.py auto-greet \
     --security-id <id> \
     --text-file documents/zh/<话术>.md \
     --company <公司> \
     --i-understand-ban-risk
   # 用户确认后再：
   python tools/apply_assist.py auto-greet … --i-understand-ban-risk --execute
   ```
4. Agent **不得**静默加 `--execute`。

也可用统一入口（auto 不会在此静默发送）：

```bash
python tools/apply_assist.py after-generate \
  --url "…" --text-file "…" --company "…" --role "…"
```

---

## Step 7: Tracker

生成结束后打印可复制命令：

```bash
python tools/tracker.py suggest-add \
  --company <公司> \
  --role <岗位> \
  --channel <Boss直聘|智联|猎聘|51job|拉勾> \
  --cv documents/zh/resume_<公司>.md \
  --cover documents/zh/<话术或求职信文件>.md \
  --source documents/zh/jd_<公司>_<岗位>.md
```

说明：投完（无论手动还是自动）都要记一笔；日常用 `tracker.py today` / `dashboard`；阶段变化 `/outcome`。

---

## Step 8: 呈现与交付

汇总路径（缺一不可说清楚）：

- `documents/zh/resume_<company>.md`（源）
- **`documents/zh/resume_<company>.pdf`（投递用，必须生成）**
- 话术 / 求职信、岗位描述、匹配报告
- 当前投递模式 + tracker 命令

闭环：搜岗 → 生成材料 → **导出 PDF** → 按模式投 → tracker。
