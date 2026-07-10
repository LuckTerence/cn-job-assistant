# /setup-zh - 国内求职中文引导（Onboarding）

你正在为**国内求职工作区**做初始化引导。目标是填充中文画像文件 `CLAUDE.zh.md`，
并让用户跑通国内最小闭环：
`install_domestic_search` → `/apply-zh` → 手动投递 → `tools/tracker.py`。
本命令是 `/setup` 的中文版入口；若你也要走海外 LaTeX 流程，可另跑英文 `/setup`。

---

## Step 0: 欢迎与选择路径

先扫描 `documents/` 文件夹（`documents/**/*`）。三种初始化方式：

> **欢迎使用国内求职助手引导！**
>
> 我会帮你填好中文画像（`CLAUDE.zh.md`），之后就能用 `/apply-zh` 一键生成中文简历 + 打招呼话术。三种开始方式：
>
> **A. 读取资料文件夹**（推荐，若有素材）—— 我把 `documents/` 下的简历 / 作品集 / 证书读一遍，交叉校验后填入画像。
> **B. 单次简历导入** —— 直接粘贴或 @ 一份中文简历，我提取要点并追问缺口。
> **C. 问答模式** —— 我按板块逐项问你，从零搭建画像。
>
> 选哪种？

---

## Path A：读取资料文件夹

1. 用 Glob 列出 `documents/cv/`、`documents/linkedin/`、`documents/diplomas/`、`documents/references/`。
2. 读取上述文件，交叉校验一致性（日期 / 职位 / 学历是否一致）。
3. 把信息映射到 `CLAUDE.zh.md` 的对应板块（身份信息 / 教育背景 / 工作经历 / 专业技能 / 证书荣誉 / 行为风格 / 求职方向）。
4. 只填充 `[占位符]`，不重写整段；已填内容不重复提议。

## Path B：单次简历导入

1. 通读用户粘贴的中文简历。
2. 提取：姓名 / 联系方式 / 教育 / 经历 / 技能 / 证书 / 求职意向。
3. 展示提取摘要，追问缺口（行为风格、求职方向、期望薪资、政治面貌等）。
4. 写入 `CLAUDE.zh.md`。

## Path C：问答模式

按板块自然提问（不要像填表），用户用自己的话回答，你负责结构化：
- **身份与联系**：姓名、城市、电话、邮箱、语言（含英语等级）、政治面貌、求职状态。
- **教育**：每段学历的层次 / 专业 / 学校 / 年份 / GPA 或排名。
- **工作经历**：倒序，每段含职责与**量化业绩**（国内简历重数据）。
- **专业技能**：主攻 / 次攻 / 领域 / 工具。
- **证书荣誉**：证书名 / 机构 / 日期；竞赛与奖项。
- **行为风格**：最强特质、优势、成长点。
- **求职方向**：目标赛道（互联网 / 国企央企 / 外企 / 体制内 / 应届）、目标岗位、期望薪资、地点偏好、deal-breaker。

---

## Step 3：补充非画像项（重要）

填充完画像后，额外确认两项国内链路必需信息：

1. **期望薪资**：记录到 `CLAUDE.zh.md` 的"求职方向"段。`/apply-zh` 用它在匹配评估里给薪资基准（替代海外向的 `salary_lookup.py`）。
2. **目标赛道**：决定 `08-resume-zh.md` 用哪套模板（`templates/zh/resume_<track>.md`）。

---

## Step 4：交付与下一步

写入 `CLAUDE.zh.md` 后，告诉用户：

> "中文画像已写入 `CLAUDE.zh.md`。国内最小闭环：
> 1. `python tools/install_domestic_search.py install-boss`（或 install-get-jobs）装搜岗后端；
> 2. 搜岗后把 JD 丢给 `/apply-zh` → 中文简历草稿 + 打招呼话术；
> 3. 在 App 内**手动**投递；
> 4. `python tools/tracker.py add --company … --role … --channel … --status applied` 记一笔；
> 5. 阶段变化用 `/outcome <company>`；总览用 `python tools/tracker.py dashboard`。
>
> 可选重应用（Reactive-Resume / 谈薪方法论 / 模拟面试等）见 `integrations/catalog/`，非开箱必装。"

可选：确认用户是否已跑过 `python tools/install_domestic_search.py status` 与 `python tools/tracker.py init`。

中文引导只填 `CLAUDE.zh.md`；海外 LaTeX 流程所需的 `01-candidate-profile.md` 等英文画像由英文 `/setup` 负责，两者各管各的市场，不冲突。
