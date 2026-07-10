# /setup-zh - 国内求职中文引导（Onboarding）

你正在为**国内求职工作区**做初始化引导。目标是填充中文画像文件 `CLAUDE.zh.md`，
并让用户跑通国内最小闭环：
`install_domestic_search` → `/apply-zh` → 手动投递 → `tools/tracker.py`。
本命令是 `/setup` 的中文版入口；若你也要走海外 LaTeX 流程，可另跑英文 `/setup`。

---

## Step 0: 欢迎与选择路径

先扫描 `documents/`（含 `documents/cv/`、`documents/zh/`）。**四种**开始方式——**默认推荐 B（粘贴旧简历）**以降低冷启动：

> **欢迎使用国内求职助手引导！**
>
> 填好 `CLAUDE.zh.md` 后就能 `/apply-zh`。怎么开始？
>
> **B. 粘贴旧简历（推荐，最快）** —— 把现有中文简历全文贴过来（或 @ 文件），我抽取画像并追问缺口。  
> **A. 读取资料文件夹** —— 扫描 `documents/cv/` 等已有材料。  
> **C. 问答模式** —— 从零问你。  
> **D. 先看 Demo** —— 不填画像，先 `bash scripts/demo.sh` 看产出长什么样。
>
> 选哪种？（直接说 B / 粘贴简历 即可）

若用户一上来就贴了大段简历文本，**无需再问**，直接走 Path B。

---

## Path B：粘贴旧简历 → 抽画像（减负主路径）

1. **通读**用户粘贴或 @ 的中文简历（支持 Markdown / 纯文本；若是 PDF 请用户粘贴文本层或另存 md）。
2. **结构化提取**（输出一张摘要表给用户确认）：

   | 字段 | 提取结果 |
   |------|----------|
   | 姓名 / 城市 / 电话 / 邮箱 | |
   | 求职状态（若未写则标「待确认」） | |
   | 教育（层次/专业/学校/年份） | |
   | 工作经历（公司/岗位/时间/量化点） | |
   | 技能（主攻/工具） | |
   | 证书荣誉 | |
   | 可推断的目标岗位 | |

3. **只追问缺口**（一次最多 5 个问题，不要盘问）：
   - 目标赛道（互联网 / 国企央企 / 外企 / 体制内 / 应届）
   - 期望薪资与城市
   - 政治面貌（若目标含国企/体制内）
   - 行为风格 1～2 词（若简历完全看不出）
   - 硬约束（不接受的加班/出差/外包等）
4. 将确认后的内容写入 `CLAUDE.zh.md`：**只填 `[占位符]`，不无故删用户已有段落**。
5. 若简历与用户口头补充冲突，**以用户当场确认为准**，并在摘要里标出冲突点。

### 抽取时注意

- 量化业绩尽量保留原数字，不四舍五入编造。
- 联系方式写入画像但提醒用户：投递产物目录已 gitignore，勿把含手机号的文件强行 commit。
- 英文简历也可：提取后写入中文画像，并问是否同时要跑英文 `/setup`。

---

## Path A：读取资料文件夹

1. Glob `documents/cv/`、`documents/linkedin/`、`documents/diplomas/`、`documents/references/`、`documents/zh/`。
2. 交叉校验日期 / 职位 / 学历。
3. 映射到 `CLAUDE.zh.md`；只填占位符。

## Path C：问答模式

按板块自然提问（勿填表感）：身份与联系、教育、工作经历（量化）、技能、证书、行为风格、求职方向与硬约束。

## Path D：先看 Demo

告知用户在仓库根目录执行：

```bash
bash scripts/demo.sh
# 打开 examples/demo/output/job_search_tracker.html
```

Demo 跑完后，回到 Path B 填真实画像。

---

## Step 3：补充非画像项（重要）

1. **期望薪资** → `CLAUDE.zh.md` 求职方向段。  
2. **目标赛道** → 决定 `templates/zh/resume_<track>.md`。  
3. 可选：`python tools/tracker.py init` 创建空追踪表。

---

## Step 4：交付与下一步

> 中文画像已写入 `CLAUDE.zh.md`。下一步：
> 1. （可选）`python tools/install_domestic_search.py install-boss`
> 2. `/apply-zh <岗位描述>` → 简历 + 话术 + 匹配摘要
> 3. App 内手动投递
> 4. 使用 `/apply-zh` 给出的 `tracker suggest-add` 命令记一笔
> 5. 每日：`python tools/tracker.py today`
>
> Agent 安装说明见 `docs/INSTALL.agents.zh.md`。可选重应用见 `integrations/catalog/`。

中文引导只填 `CLAUDE.zh.md`；海外英文画像由 `/setup` 负责。
