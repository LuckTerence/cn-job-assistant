# /apply-zh - 国内求职一站式编排（中文简历 + 打招呼话术）

你正在为一个**中国大陆市场的中文岗位**编排完整投递材料。岗位信息由 `$ARGUMENTS` 提供
（Boss直聘 / 智联 / 51job / 猎聘 / 拉勾 的链接或粘贴的 岗位描述 文本）。

本命令是 `/apply` 的国内显式入口：强制 `MARKET=domestic`，走中文流程，不走 LaTeX。
严格按以下步骤执行，不要跳步。

---

## Step 0: 解析输入

- 若 `$ARGUMENTS` 是 URL，用 `WebFetch` 提取 岗位描述 正文；若是文本，直接使用。
- **多岗粘贴**（一次贴了多个 JD，中间有 `---` 或多个 `#` 标题）：
  ```bash
  # 先落盘 pasted.txt，再拆分
  python tools/split_jds.py -i pasted.txt -o documents/zh/inbox --resume <母版可选>
  python tools/tracker.py import-jobs documents/zh/inbox/jobs_stub.json
  python tools/tracker.py rank --track internet
  python tools/tracker.py day-plan
  ```
  然后请用户**选 1 个公司/岗位**再继续本命令；不要一口气生成 N 份完整材料。
- 抽取以下字段（记在心里，后续 Step 7 传给 tracker）：
  - **必填**：公司名、岗位名、渠道（Boss直聘/智联/51job/猎聘/拉勾）
  - **结构化可选**：城市、薪资区间（如 "25-40K"）、学历要求（如 "本科"）、经验要求（如 "3-5年"）
  - 内容字段：硬性技能、岗位职责
- 若平台是 Boss直聘，标记为"短话术模式"；否则标记为"正式求职信模式"。
- **落盘岗位描述**：写入 `documents/zh/jd_<company>_<role>.md`（纯文本即可；文件名里的 `jd_` 表示岗位描述）。

### Step 0b: 短名单优先级（v0.13）

若 `job_search_tracker.csv` 里已有多条 `to_apply`，**先**提示用户可看排序再决定本岗是否值得做材料：

```bash
python tools/tracker.py rank --track internet
python tools/tracker.py day-plan --limit 5
python tools/tracker.py funnel
```

- 若本岗不在 rank 前列且用户也认同「先放放」→ 可只 `skipped` + 原因，不必强行 `/apply-zh` 全套。
- 若用户明确「就是要投这个」→ 继续 Step 1。

---

## Step 1: 匹配评估

读取画像与框架：
- **画像** → `CLAUDE.zh.md`（**不要**读英文 `01-candidate-profile.md`）
- **评估方法论** → `.claude/skills/job-application-assistant/04-job-evaluation.md`

按 04 给出 5 维评估与 1–3 个最强匹配点 / 诚实缺口。

若已有母版简历，可预检：

```bash
python tools/match_resume.py report --zh-only \
  --resume <母版> --jd documents/zh/jd_<company>_<role>.md \
  --profile CLAUDE.zh.md
```

摘要里区分：**同义词已对齐** vs **真缺口**（不会的别编）。

询问用户是否继续生成。

---

## Step 2: 中文简历草稿 + **可投递 PDF（必须）**

- 读 `08-resume-zh.md`，按赛道选 `templates/zh/resume_<track>.md`。
- 写入 `documents/zh/resume_<company>.md`（源文件，便于改）。
- **只写真实具备的技能**；可参考 `match_resume.py keywords --jd …`。
- **国内投递默认交付物是 PDF**，不是 Markdown。生成 md 后**必须**导出：

```bash
# 推荐本机安装 Typst：brew install typst（版式优先）
python tools/export_resume_pdf.py \
  --input documents/zh/resume_<company>.md \
  --output documents/zh/resume_<company>.pdf
# 查看后端：python tools/export_resume_pdf.py --which
```

- 向用户明确：上传平台时用 **`.pdf`**；md 只是源文件。
- 后端优先级：**Typst → pandoc → Chrome**；无 Typst 时自动回退 Chrome 打印。
- 都没有时会写 HTML，指导「打印 → 存 PDF」。
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
  --profile CLAUDE.zh.md \
  --out documents/zh/match_report_<company>.json \
  --brief-out documents/zh/match_brief_<company>.txt
# 若用户口头给了期望薪资，加：--expected-salary '25-40K'
# 同义词默认开启（config/synonyms.default.json）；调试可 --no-synonyms
```

向用户**优先展示中文一页摘要**（命令默认已含【一页摘要 · 人话版】，或读 `match_brief_*.txt`）：
- 还差什么（still_missing；同义词已对齐的不再算 miss）
- **同义词已对齐** vs **真缺口**
- **薪资对照**（期望 vs JD 区间，✅/⚠️/❌；偏低可建议 skipped + salary_low）
- 建议改哪 3 条
- **禁止虚构**合规句

**诚信检查（强制，对标社区 AI 乱改简历事故）：**

```bash
python tools/check_profile_resume.py \
  --profile CLAUDE.zh.md \
  --resume documents/zh/resume_<company>.md
```

若出现 ❌ 高严重度（联系方式不一致、可疑量化数字），**停下来与用户确认**，不得直接鼓励投递。

规则：真实具备的 miss → 回 Step 2/3 补一版；不具备 → 诚实标注。

若用户是在改第二版，可对比飞轮：

```bash
python tools/match_resume.py diff \
  --before documents/zh/match_report_<company>_v1.json \
  --after documents/zh/match_report_<company>.json
```

---

## Step 5: 合规自检

- [ ] 无虚构经历/技能（已跑 `check_profile_resume`）
- [ ] 点名公司与岗位
- [ ] 已出 match 报告 + 人话摘要
- [ ] PDF 导出建议加 `--verify-text`（有 pdftotext 时）
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
3. **自定义话术优先 semi**（主流 `boss greet <id>` 往往不支持自定义文案；
   `apply_assist` 若探测到不支持会**拒绝** `--text-file`，避免假执行）：
   ```bash
   python tools/apply_assist.py semi \
     --url "<岗位链接>" \
     --text-file documents/zh/<话术>.md \
     --company <公司> --role <岗位>
   ```
4. 若用户仍要 auto（平台默认招呼），真正发送前必须 dry-run，再由用户加 `--execute`：
   ```bash
   python tools/apply_assist.py auto-greet \
     --security-id <id> \
     --company <公司> \
     --i-understand-ban-risk
   # 用户确认后再：
   python tools/apply_assist.py auto-greet … --i-understand-ban-risk --execute
   ```
   多 ID：`--security-id id1,id2`（受 `auto.max_batch` 限制）。
5. Agent **不得**静默加 `--execute`。

也可用统一入口（auto 不会在此静默发送）：

```bash
python tools/apply_assist.py after-generate \
  --url "…" --text-file "…" --company "…" --role "…"
```

---

## Step 7: Tracker（**Agent 主动执行，不是只打印命令**）

### 7A. 先用 suggest-add 预填并展示摘要

**直接运行**以下命令（把占位符替换为 Step 0 抽取的真实值；城市/薪资/学历/经验如果 JD 里有就传，没有就不传）：

```bash
python tools/tracker.py suggest-add \
  --company <公司> \
  --role <岗位> \
  --channel <渠道> \
  --cv documents/zh/resume_<公司>.md \
  --cover documents/zh/<da-zhaohu或cover文件>.md \
  --source documents/zh/jd_<公司>_<岗位>.md \
  --city <城市，可选> \
  --salary <薪资区间，可选> \
  --education <学历要求，可选> \
  --experience <经验要求，可选>
```

向用户展示 suggest-add 输出的**预填摘要**（公司/岗位/渠道/状态/城市薪资等）。

### 7B. 询问用户意图，确认后写入

**必须明确询问**用户以下选择（**禁止静默写入 CSV**）：

> 要把这条记录写入 tracker 吗？
> - **to_apply**：还没投，先占个位（默认安全选项）
> - **applied**：已经投了
> - **skipped（不投）**：评估后决定不投——**仍写入**，并选一个原因（产品信号）
> - **稍后**：先不记，稍后自己 `tracker add`

根据用户回答执行对应 add 命令（把 suggest-add 输出的命令里 `--status` 改成用户选的值；
若用户说"已经投了/已投递"才用 `--status applied`；其他情况默认 `to_apply`）：

```bash
python tools/tracker.py add \
  --company <公司> --role <岗位> --channel <渠道> \
  --status <to_apply|applied> \
  --cv documents/zh/resume_<公司>.md \
  --cover documents/zh/<话术文件>.md \
  --source documents/zh/jd_<公司>_<岗位>.md \
  [--city <城市> --salary <薪资> --education <学历> --experience <经验>]
```

### 7C. 用户选「不投 / skipped」时（Phase 1 信号）

**必须再问一次原因**（单选，写入 `--skip-reason`；禁止只记 skipped 不写原因）：

| 键 | 含义 |
|----|------|
| `salary_low` | 薪资偏低 |
| `location` | 地点不合适 |
| `low_match` | 匹配度低 / 技能差太多 |
| `unknown_company` | 不了解公司 |
| `other` | 其他（可在 `--notes` 写一句） |

```bash
python tools/tracker.py add \
  --company <公司> --role <岗位> --channel <渠道> \
  --status skipped \
  --skip-reason <salary_low|location|low_match|unknown_company|other> \
  --cv documents/zh/resume_<公司>.md \
  --source documents/zh/jd_<公司>_<岗位>.md \
  [--notes "一句话补充"] \
  [--city <城市> --salary <薪资>]
```

若用户说「稍后 / 先不记」→ **不执行 add**，告知随时可 `tracker add`。

**规则**：
- 用户没明确说"已经投了" → 默认 `to_apply`，不要自作主张标 applied
- **不投也值得记**：`skipped` + `skip_reason` 帮助后续看「为什么总筛掉这类岗」；可 `python tools/tracker.py skip-stats`
- 若发现已有同公司+岗位+渠道的记录，tracker 会提示 duplicate，用 `update` 改状态即可
- 写入成功后告诉用户：日常用 `python tools/tracker.py today` 或 `dashboard` 看进度
- **首次庆祝**：如果这是本会话第一次成功写入 tracker（add 命令返回成功），在告诉用户进度查看方式**之前**，加一句：
  > ✅ 第一份材料准备好了！这是最难的一步——接下来会越来越顺。
  （用「本会话是否已 add 过」判断即可；不必读 CSV 判断是否全局首次。）

---

## Step 8: 呈现与交付 + 「然后呢」引导

### 8A. 交付汇总（缺一不可说清楚）

- `documents/zh/resume_<company>.md`（源）
- **`documents/zh/resume_<company>.pdf`（投递用，必须生成）**
- 话术 / 求职信、岗位描述、匹配报告
- 当前投递模式 + tracker 是否已写入（7B 的结果）

闭环确认：搜岗 → 生成材料 → **导出 PDF** → 按模式投 → tracker 记一笔。

### 8B. 「然后呢」——下一步引导（**固定输出，不要省略**）

交付汇总后，**必须**输出以下引导块（用自然的人话，不要生硬照搬标题）：

```text
📌 接下来你可以：

  • 投完/等回复阶段
    - 3–7 天没消息可以回来用 /outcome 记「待跟进」或「无回复」
    - 拿到面试 / offer / 拒信，都回来 /outcome 更新状态
    - 日常看进度：python tools/tracker.py today （终端） 或 dashboard （HTML看板，有卡片待办）

  • 若本岗选择了不投（skipped）
    - 原因会进 skip_reason；汇总：python tools/tracker.py skip-stats
    - 之后想改状态或补笔记：/outcome <公司>

  • 想改简历（v2、v3）
    - 改完 md 后重新跑 match_resume.py report 生成新报告
    - 拒信/无回复后更建议跑 diff（/outcome 也会提醒）：
        python tools/match_resume.py diff \
          --before documents/zh/match_report_<公司>_v1.json \
          --after documents/zh/match_report_<公司>.json

  • 继续投下一个
    - 直接 /apply-zh <新岗位链接或JD>，流程同上
```

**规则**：
- 引导块是「固定结构 + 人话填充」，不要死板复制格式，但三块内容（跟进/结果、改简历diff、继续投）必须覆盖
- 如果用户已经说了"已投"，重点提醒"3-7天没消息回来跟进"；如果是 to_apply，重点提醒"投完回来改状态"
- 不要在交付时丢一堆命令就结束——让用户清楚知道工具不是"生成完PDF就完了"，而是持续用的
