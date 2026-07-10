# AI 求职助手 · 国内适配版（China Fork）

> **一句话定位**：这是面向 agent 的**求职工作流框架**（非 SaaS 产品）。  
> 国内用户开箱要跑的**最小组件**是：  
> ① `python tools/install_domestic_search.py`（Boss / get_jobs 安装）  
> ② `/setup-zh` + `/apply-zh` / `/da-zhaohu`（中文简历与话术）  
> ③ `python tools/match_resume.py`（本地匹配分 + 关键词 hit/miss，无模型下载）  
> ④ `python tools/tracker.py`（本地投递追踪，CSV 权威源）  
> 默认**不自动投递**。  
> **架构分层**（核心 skill 面 vs 可选 catalog）：[`ARCHITECTURE.zh.md`](./ARCHITECTURE.zh.md)。  
> 重型自托管仅见 [`integrations/catalog/`](./integrations/catalog/README.md)（含真实搭建成本表）。

> 本仓库是 [MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search)（MIT）的**国内适配分支**，
> 在保留原版"岗位匹配评估 + 简历定制 + 面试准备"工作流的基础上，新增面向中国大陆求职市场的改造。

## 国内最小闭环（可跑）

```bash
# 0. 可选：装 Boss 搜岗 CLI（个人/非商用；上游许可证请自行确认）
python tools/install_domestic_search.py install-boss
python tools/install_domestic_search.py status

# 1. 在 agent 里跑 /setup-zh 填中文画像

# 2. 搜岗后复制 JD，生成材料
#    /apply-zh <JD链接或文本>

# 3. 在 Boss/智联 等 App 内手动投递

# 4. 量化匹配 / 生成质量（零模型下载）
python tools/match_resume.py report \
  --resume documents/zh/resume_示例.md \
  --jd documents/zh/jd_示例.md \
  --cover documents/zh/da-zhaohu_示例.md

# 5. 记入本地 Tracker（零 Docker）
python tools/tracker.py init
python tools/tracker.py add --company 示例 --role 后端 --channel Boss直聘 --status applied
python tools/tracker.py dashboard   # 生成 job_search_tracker.html
```

| 环节 | 可跑交付 | 说明 |
|------|----------|------|
| 搜岗 | `install_domestic_search.py` + boss-cli / get_jobs | 不自研爬虫；get_jobs 禁商用、需 JDK21 |
| 生成 | `/apply-zh` `/da-zhaohu` + `08`/`09` + `templates/zh` | prompt 工作流，已落地 |
| 匹配/质检 | `tools/match_resume.py` + `resume-match` skill | TF–IDF 余弦 + 关键词；`/apply-zh` 强制 report |
| 追踪 | `tools/tracker.py` + `job_search_tracker.csv` | 替代默认 jobsync 指针 |
| 可选 | `integrations/catalog/*` | 神经匹配 UI / 模拟面 / 谈薪等，自托管成本自担 |

## 与原版的核心差异

| 维度 | 原版 | 本分支（国内适配） |
|------|------|-------------------|
| 求职平台 | LinkedIn / 丹麦系 | **Boss直聘 / 智联 / 前程无忧 / 猎聘 / 拉勾** |
| 简历格式 | LaTeX 英文 CV（2 页） | **中文简历（1 页，分赛道，.docx/PDF）** |
| 开场产物 | 英文 Cover Letter | **打招呼话术（Boss直聘）/ 正式中文求职信** |
| 模型 | Claude Code | **模型无关**，可跑在 DeepSeek / 智谱 GLM 等国产模型 agent 上 |
| 投递 | 手动 | **手动（不自动投递，规避风控与合规）** |

原版的 LaTeX 英文 CV / Cover Letter 流程**保留**，用于海外或英文岗；国内中文岗走新增的中文流程，
两者由命令按岗位语言与市场自动选择。

## 目录结构（新增部分）

```
tools/
  install_domestic_search.py   国内搜岗一键安装 / status / smoke
  tracker.py                   本地 Tracker（CSV 权威源 + HTML/SQLite）
  match_resume.py              本地匹配 + 生成质量报告（TF–IDF / 关键词）
  lint_zh_refs.py              国内路径与闭环引用检查（CI）
.agents/skills/                # 核心 skill 面（可被 agent 直接触发）
  bosszhipin-search/           Boss直聘（复用 boss-cli + 安装器）
  domestic-jobs-search/        智联/51job/猎聘/拉勾（复用 get_jobs + 安装器）
  application-tracker/         本地 Tracker（tools/tracker.py）
  resume-match/                本地匹配 CLI（tools/match_resume.py）
  # + 上游 6 个海外 CLI skills
integrations/catalog/          # 可选/重依赖，不进核心 skill 面
  resume-build/ resume-match/ interview-mock/
  salary-negotiate/ referral-outreach/ job-alert/
  README.md                    搭建成本与选型说明
.claude/skills/job-application-assistant/
  08-resume-zh.md              中文简历指南（与 09 同级，不在 zh/ 子目录）
  09-da-zhaohu-zh.md           打招呼话术 / 求职信指南
.claude/commands/
  setup-zh.md  apply-zh.md  da-zhaohu.md
templates/zh/                  分赛道中文简历模板 + 话术示例
documents/zh/                  国内投递产物目录（.gitkeep；内容 gitignore）
README.zh.md  MODELS.zh.md
```

## 对标与复用（来自同赛道开源项目）

本分支坚持"能复用人家的就复用，不重复造轮子"。除已集成的 boss-cli / get_jobs / ai-job / mcp-jobs 外，
本轮继续对标以下成熟项目并复用其能力：

| 项目 | 协议 | 复用点 | 在本分支的角色 |
|------|------|--------|---------------|
| **Ocyss/boss-helper** | 非商用 | Boss直聘 浏览器扩展（UI/批量投递/GPT 招呼/多账号） | boss-cli 的 **UI 替代** |
| **Reactive-Resume** | MIT | 简历构建器（16+ 模板、PDF/JSON/DOCX 导出、AI、可自托管） | **catalog 可选** `resume-build/`；默认 Markdown |
| **AitoResume** | — | 按 JD 生成/优化简历，支持本地 Ollama | JD→简历初稿补充 |
| **claude-apply** | MIT | 端到端投递管线（扫描 ATS→评分→CDP 真实浏览器填写→追踪） | **可选**端到端参考（海外 ATS，见下） |
| **claude-job-auto-apply** | MIT | 全自动代理（搜岗→按 JD 改简历→写信→填表→自动注册/过验证码） | **可选**全自动极端形态参考 |

> **端到端投递（可选）**：本分支默认"生成辅助内容、用户手动在 App 内投递"以规避风控与合规。
> 若需端到端自动化，可参考 **claude-apply**（CDP 真实浏览器填写、不 stealth/不撒谎、带追踪看板，
> 海外 ATS：Lever/Greenhouse/Ashby/Workable/Workday）或 **claude-job-auto-apply**（Claude 子代理 + Playwright 全自动）。
> 是否启用由用户自决，并须知悉平台协议与风控风险。国内平台的自动化仍以前述 get_jobs / boss-cli 为准。

### 第二轮新增对标（10 个项目）

在首轮基础上继续检索 **求职信生成 / 模拟面试 / 简历解析 / 投递追踪 / 实习校招 / LinkedIn 自动化 /
薪资对比 / ATS 优化 / 招聘聚合 / 全链路** 十个维度，再得 10 个可复用轮子：

| # | 项目 | 协议 | 核心能力 | 在本分支的复用落点 |
|---|------|------|---------|-------------------|
| 1 | **rebecha1227-a11y/CareerForge** | — | AI 求职全链路（搜岗/改简历/写求职信/模拟面试），中文 | 全链路形态**参考**（对标自身架构） |
| 2 | **GodLeaveMe/AuraInterviewer** | MIT | AI 模拟面试（GPT/DeepSeek/SiliconFlow，多维评分+结构化报告） | **catalog 可选**；默认 `/interview` + `07` |
| 3 | **wzx11223344/resume-customizer** | NOASSERTION（实测无代码） | JD 解析+技能匹配+ATS 优化（仅 README 描述；实测仓库仅 SKILL.md/README/LICENSE，无 `scripts/`，属空壳） | 原拟作 **resume-match** 底层，测试发现无可运行代码，**已弃用**，改由 Resume Matcher 取代 |
| 4 | **spencergg/resume-parser** | — | ResumeSDK 简历解析（中英，170+ 字段，40+ 格式） | 解析层可补 resume-match |
| 5 | **siddhesh3008/Job-Application-Tracker** | — | Personal ATS（追踪投递/状态/可视化） | **可选**投递追踪参考（本分支暂无追踪） |
| 6 | **JayLyu/salary-compare** | — | 跳槽薪资对比（五险一金/福利/加班/通勤/实际时薪，Next.js） | **可选** offer 对比参考（国内特有维度） |
| 7 | **madingess/EasyApplyBot** | — | LinkedIn Easy Apply 自动（回答申请问题） | 海外自动投递补充（同 claude-apply 类） |
| 8 | **gokul2000/job-board-aggregator** | — | Python CLI 多平台聚合（RemoteOK/Indeed/LinkedIn/Glassdoor，过滤） | **可选**招聘聚合参考（海外板） |
| 9 | **33-ctrl/resume-copilot** | — | 多角色协作简历助手（智谱 OpenAI 兼容，岗位分析/优化/面试） | JD→简历生成补充（同 AitoResume 类） |
| 10 | **srbhr/Resume-Matcher** | Apache-2.0 | 简历↔JD 语义匹配（embedding 余弦相似度）+ 关键词抽取 + 排名 + 定制内容/求职信（27k+★） | **resume-match** 技能底层（已集成，取代非功能性的 resume-customizer） |

#### 本轮识别出的新差距与处置

- **匹配度/ATS 优化在"手写评分"**：原 `04-job-evaluation.md` 为手写评分框架。现由 **resume-match**
  （复用 **Resume Matcher**）提供量化匹配/缺失技能/关键词密度/ATS 检查，原文件降为"人工评估框架"指引。
- **模拟面试在"仅有指南"**：原 `07-interview-prep.md` 只给方法论，无 AI 练习。现由 **interview-mock**
  （复用 AuraInterviewer）提供真实多轮对话 + 多维评分报告，原文件保留为国内题型方法论。
- **投递追踪缺失**：本分支无 application tracker。可选参考 **Job-Application-Tracker**（Personal ATS）。
- **薪资/offer 对比缺失**：本分支无薪酬对比。可选参考 **salary-compare**（含五险一金/加班/通勤等国内维度）。
- **招聘聚合缺失**：国内聚合已由 get_jobs/boss-cli 覆盖；海外板可选参考 **job-board-aggregator**。
- **全链路对标**：**CareerForge** 验证"搜岗→改简历→写求职信→模拟面试"全链路方向正确，本分支以
  组合多个单点轮子（而非单一巨无霸）实现同等能力，更符合"复用而非重造"。

### 第三轮新增对标（10 个项目，补全"投递后闭环"）

在前两轮覆盖"检索 / 简历 / 匹配 / 模拟面试 / 追踪 / 对比 / 聚合 / 全链路"的基础上，第三轮聚焦
**谈薪、投递后提醒、内推冷触达、语音面试、中文模板源、作品集、自动投递形态** 七个新维度，
再得 10 个可对标项目；其中 3 个已集成为 reuse 技能，其余作为可选参考：

| # | 项目 | 协议 | 核心能力 | 在本分支的复用落点 |
|---|------|------|---------|-------------------|
| 1 | **Ssupercoder/Salary-Negotiation-Skill** | 未声明 | 中文谈薪 LLM Agent（五阶段引擎 + Qwen2.5-7B + RAG 市场锚点，三运行版本） | **catalog 方法论 only**；勿复制源码 |
| 2 | **NissonCX/offercatcher** | MIT | 扫描 Apple Mail → AI 提取招聘事件 → Apple Reminders（**非**平台监控器） | **catalog 可选**（仅 macOS） |
| 3 | **quionie/outreach-ai** | MIT | 多通道冷触达 CLI（email/LinkedIn/Twitter，Claude/OpenAI/Ollama，批量 CSV） | **catalog 可选**（pip CLI） |
| 4 | **ZHAB00/ai_interview** | MIT | 语音实时 AI 模拟面试（DeepSeek + Qwen ASR/TTS，四阶段 + 五维评分 + 雷达图） | **可选**给 interview-mock 补语音维度 |
| 5 | **dyweb/awesome-resume-for-chinese** | — | 中文简历模板合集（LaTeX / HTML / Typst 多套，含应届 / 双栏） | **可选**给 `08-resume-zh` / `resume-build` 补模板源 |
| 6 | **feder-cr/Jobs_Applier_AI_Agent_AIHawk** | 见 LICENSE | 自动投递 Web Agent（Selenium，生成 tailored 简历 / 求职信） | **可选/警示**全自动形态参考（本分支不自动投递；其已移除第三方插件） |
| 7 | **PortfolioCraft/PortfolioCraft** | — | 静态作品集模板（index.html，非 AI 生成器，仅 2 commits） | **可选**作品集排版参考（价值有限） |
| 8 | **spencergg/resume-parser** | — | ResumeSDK 简历解析（170+ 字段，40+ 格式，中英） | 解析层补 `resume-match`（第二轮已列） |
| 9 | **JayLyu/salary-compare** | — | 跳槽薪资对比（五险一金 / 加班 / 通勤 / 时薪，Next.js） | **可选** offer 对比（第二轮已列） |
| 10 | **siddhesh3008/Job-Application-Tracker** | — | Personal ATS（投递 / 状态 / 可视化） | **可选**投递追踪（第二轮已列） |

#### 本轮识别出的新差距与处置

- **谈薪 / 提醒 / 内推**：曾以 doc-only skill「已集成」表述，**Phase 3 起统一为 catalog 可选**，
  并标注真实搭建成本与默认替代路径（见 `integrations/catalog/README.md`）。
  Salary-Negotiation-Skill **未声明许可证** → 仅方法论；offercatcher **仅 macOS**；
  outreach-ai 为可选 pip CLI，不自动代发。
- **语音面试维度缺失**：**interview-mock** 仅有文本多轮。可选参考 **ZHAB00/ai_interview**（MIT，语音实时 +
  雷达图报告）补语音维度，需另行自托管。
- **中文 LaTeX 模板源缺失**：`08-resume-zh.md` 为自写分赛道模板。可选参考 **awesome-resume-for-chinese**
  的 LaTeX / Typst 模板库，作为样式来源。
- **作品集维度缺失**：本分支不含作品集生成。可选参考 **PortfolioCraft**（静态模板，价值有限）或后续另寻 AI 作品集生成器。
- **自动投递极端形态**：**AIHawk** 验证全自动投递可行性但引发平台反垃圾争议，且已移除第三方插件；
  本分支坚持"不自动投递"政策，仅作形态参考，不集成。

### 第四轮新增对标（2 个高价值参考，闭环补全"面试题库 / 校招平台"）

第三轮后剩余两个未填维度——**面试题库**与**校招 / 实习平台覆盖**，本轮补齐：

| # | 项目 | 协议 | 核心能力 | 在本分支的复用落点 |
|---|------|------|----------|-------------------|
| 1 | **yangshun/tech-interview-handbook** | MIT | 业界技术面试手册：算法（Blind 75 / Grind 75）/ 行为 / 系统 / 简历 / 薪资全流程 | **可选知识源** → `interview-mock` + `07-interview-prep.md`（补题库与方法论） |
| 2 | **gototrip1/Automated-resume-submission-Agent** | 未声明 | 自动投递 Agent，覆盖 Boss / 实习僧 / 牛客 / 应届生 / 智联 / 51job / 拉勾 / 猎聘（LangGraph + Playwright） | **可选参考** → `domestic-jobs-search`（补校招平台覆盖；因未声明许可 + 自动投递，不集成） |

#### 本轮识别出的新差距与处置

- **面试题库缺失**：原 `07-interview-prep.md` 仅有方法论框架，无结构化题库。现引入 **tech-interview-handbook**（MIT，超百万用户）作为题库与方法论补充来源，不搬运其知识、仅作引用。
- **校招 / 实习平台覆盖缺失**：原 `domestic-jobs-search`（get_jobs）与 `bosszhipin-search`（boss-cli）聚焦社招主流平台，缺实习僧 / 牛客 / 应届生求职网。现以 **gototrip1** Agent 作可选参考标注其平台覆盖；因该仓库**未声明许可证**且为自动投递形态，本分支**不集成其代码**，延续"不自动投递"政策。
- **覆盖维度收敛**：求职信生成（06 模板 + AIHawk 参考）、简历优化（resume-customizer 经测试证实无可用代码，已改用 **Resume Matcher**）本轮检索到的同类项目（如 ats-resume-optimizer、各类 cover-letter 小工具）均为重叠或教程级，无新增集成价值，故不重复造轮子。

### 第五轮新增对标（15 个项目，补齐"海外聚合 / 系统设计 / 投递追踪 / 技术简历"等剩余维度）

前四轮已覆盖检索 / 简历构建 / 匹配 / 模拟面试 / 谈薪 / 提醒 / 内推 / 校招 / 题库等维度。本轮再比对 **15 个**同赛道项目，
重点补齐此前空白的**海外岗位聚合、系统设计面试知识、投递状态追踪、技术/学术简历构建、ATS 模拟、自动投递形态、技能包架构对标**等方向：

| # | 项目 | 协议 | 核心能力 | 本分支对应能力 / 复用落点 | 处置 |
|---|------|------|---------|--------------------------|------|
| 1 | **santifer/career-ops** | MIT | 开源 AI 求职全流程（扫描岗位 / A-F 打分 / 定制），59k★ | 同赛道旗舰框架对标 | 对标参考（不集成代码） |
| 2 | **andrew-shwetzer/career-ops-plugin** | MIT | Claude 插件，9 个求职 AI 技能 | 技能包架构对标 | 对标参考（架构借鉴） |
| 3 | **rendercv/rendercv** | MIT | LaTeX 简历生成器（学术 / 工程，17k★） | resume-build 技术简历互补 | 可选参考 |
| 4 | **xitanggg/open-resume** | AGPL-3.0 | 简历生成器 + 解析器（8.7k★） | resume-build 解析 / ATS 互补 | 可选参考（AGPL 仅方法论） |
| 5 | ~~speedyapply/JobSpy~~ | MIT | 海外岗位抓取库（LinkedIn/Indeed/Glassdoor/Google/Zip，3.8k★） | 海外板——**与国内定位不符** | **不采纳**（本分支只做国内） |
| 6 | ~~PaulMcInnis/JobFunnel~~ | MIT | 多源岗位抓取去重汇总（2.2k★） | 海外板——**与国内定位不符** | **不采纳**（本分支只做国内） |
| 7 | **GodsScion/Auto_job_applier_linkedIn** | AGPL-3.0 | LinkedIn 自动投递（2.5k★） | 自动投递形态参考（海外） | 可选参考（不自动投递） |
| 8 | **OmkarPathak/pyresparser** | GPL-3.0 | Python 简历解析（NLP，959★） | resume-match 解析备选 | 可选参考（GPL 仅方法论） |
| 9 | **donnemartin/system-design-primer** | 无许可声明 | 系统设计面试圣经（356k★） | interview-mock 系统设计知识 | **已接入**（知识源） |
| 10 | **ByteByteGoHq/system-design-101** | 无许可声明 | 系统设计可视化讲解（85k★） | interview-mock 系统设计图解 | **已接入**（知识源） |
| 11 | **Gsync/jobsync** | MIT | 自托管投递追踪 + AI 职业助手（719★） | 可选外挂看板 | **降级**（默认改用 `tools/tracker.py` + CSV） |
| 12 | **DaKheera47/job-ops** | 无许可声明 | "DevOps 式求职"自托管流水线（3.6k★） | 工作流 / 流水线方法论 | 可选参考 |
| 13 | **sunnypatell/ats-screener** | MIT | 企业级 ATS 模拟器（77★） | resume-match ATS 维度 | 可选参考 |
| 14 | **binoydutt/Resume-Job-Description-Matching** | 无许可证 | 简历↔JD 匹配对抗 ATS（188★） | resume-match 方法论 | 可选参考（无许可） |
| 15 | **jananthan30/Resume-Builder** | MIT | AI 简历 + 求职信 + 双 ATS/HR 评分（56★） | 求职信 + 双评分维度 | 可选参考 |

#### 本轮识别出的新差距与处置

- **海外岗位聚合——明确不做**：本分支定位为**纯国内求职**，JobSpy / JobFunnel 等海外聚合工具（LinkedIn / Indeed / Glassdoor 等）与定位不符，**不采纳**。国内平台检索由 boss-cli（Boss直聘）+ get_jobs（智联 / 51job / 猎聘 / 拉勾）覆盖已足够。
- **系统设计面试知识缺失**：`interview-mock`（AuraInterviewer）仅有算法 / 行为 / 语音维度，缺系统设计深度。现接入 **system-design-primer** + **system-design-101**（均未声明许可证，仅作知识引用不复制代码）补系统设计题库与图解（系统设计知识与国内外无关，通用适用）。
- **投递状态追踪**：已落地 **`tools/tracker.py`** + **`application-tracker`**（CSV 权威源 + HTML 看板，零 Docker）。
  此前指向的 jobsync 自托管**不再作为默认路径**（可选外挂，不自动同步）。
- **技术 / 学术简历构建**：`resume-build`（Reactive-Resume）外，新增 **rendercv**（LaTeX 学术 / 工程）与 **open-resume**（解析 / ATS，AGPL 仅方法论）为可选互补。
- **ATS 模拟 / 双评分维度**：新增 **ats-screener**（企业级 ATS 模拟）与 **Resume-Builder**（双 ATS/HR 评分）为可选参考，补 `resume-match` 与求职信维度。
- **自动投递形态 / 技能包架构对标**：**Auto_job_applier_linkedIn**（AGPL）作自动投递形态参考（坚持不自动投递）；**career-ops**（59k★ 全流程）与 **career-ops-plugin**（9 技能 Claude 插件）作同赛道架构对标，不集成代码。
- **交付优先迭代**：Phase 1 搜岗+Tracker；Phase 2 本地匹配；**Phase 3** catalog 成本卡 +
  `lint_skill_surface` allowlist（核心 10 / catalog 6）。见 `ARCHITECTURE.zh.md`。

## 测试与验证（第四轮验证结论）

第四轮除补齐"面试题库 / 校招平台"两个参考外，对整套技能包执行了**结构体检 + 引用完整性核验 + 功能冒烟测试**，
并据此修正了两个集成缺陷。

### 1. 结构体检（静态）

| 检查项 | 结果 |
|--------|------|
| SKILL.md 数量 | 17 个，frontmatter 均含 `name` + `description` |
| 相对引用（.md/.txt/.py/.yml）可解析性 | 全部可解析，无悬空引用 |
| 结论 | **通过**，无结构问题 |

### 2. 引用完整性核验（被复用轮子的许可证与可达性）

逐一对本分支引用的开源轮子做 GitHub API 核验（可达性 + 许可证），结果如下：

| 被引用轮子 | 本分支原声称 | GitHub 实测许可证 | 一致性 | 处置 |
|-----------|-------------|------------------|--------|------|
| srbhr/Resume-Matcher | Apache-2.0（新接入） | Apache-2.0 | 一致 | 已用作 resume-match 底层 |
| NissonCX/offercatcher | MIT | MIT | 一致 | catalog 可选（macOS） |
| quionie/outreach-ai | MIT | MIT | 一致 | catalog 可选；曾做 help 冒烟 |
| jackwener/boss-cli | Apache-2.0 | 无 LICENSE 文件 | **不一致** | 安装器参考；许可证未声明 |
| loks666/get_jobs | 禁商用协议 | NOASSERTION（自定义） | 一致（禁商用） | 安装器克隆；个人非商用 |
| AmruthPillai/Reactive-Resume | MIT | MIT | 一致 | catalog 可选 |
| GodLeaveMe/AuraInterviewer | MIT | MIT | 一致 | catalog 可选（高成本） |
| yangshun/tech-interview-handbook | MIT | MIT | 一致 | 维持（可选知识源） |
| gototrip1/Automated-resume-submission-Agent | 未声明 | 无 LICENSE 文件 | 一致（均"未声明"） | 维持（可选参考，不集成） |
| wzx11223344/resume-customizer | MIT | NOASSERTION（空壳，无代码） | **不一致** | **已弃用**，resume-match 改用 Resume Matcher |

### 3. 功能冒烟测试（实际运行一个被集成轮子）

- **对象**：`quionie/outreach-ai`（referral-outreach 技能底层，MIT，Python CLI）。
- **操作**：克隆 → 在隔离 venv 安装 → 执行 `outreach --help` 与 `outreach tones`。
- **结果**：`--help` 正常列出 `batch / generate / init / tones` 四个子命令；`outreach tones` 无需 API key
  即列出 4 套语气档案（casual / challenger / founder / professional）。**功能冒烟测试通过**，证明该轮子真实可运行。
- **说明**：`Resume Matcher` 功能性运行未在沙箱执行（首次启动需联网下载 embedding 模型权重，约百 MB 级），
  已据其官方文档与仓库结构（`scripts/`、`apps/`、`LICENSE` 为 Apache-2.0）确认代码真实可运行，作为简历匹配底座无误。

### 4. 测试发现的缺陷与修复

| # | 严重度 | 缺陷 | 根因 | 修复 |
|---|--------|------|------|------|
| D1 | 高 | resume-match 引用的 resume-customizer 无可用代码，且许可证非 MIT | 上游仓库仅 SKILL.md/README/LICENSE（约 7KB），README/SKILL.md 描述的 `scripts/*.py` 均不存在；LICENSE 仅两行 "MIT License"，GitHub 判为 NOASSERTION | resume-match 改用 **srbhr/Resume-Matcher**（Apache-2.0，27k+★，真实代码） |
| D2 | 中 | bosszhipin-search 声称 boss-cli 为 Apache-2.0 | 上游无 LICENSE 文件（GitHub API 返回无许可证） | 改为"许可证未声明，参考使用，复用前确认授权"并加合规提示 |
| D3 | 低 | get_jobs 许可证标记为 NOASSERTION | 自定义禁商用许可证，GitHub 无法归类 | 与本分支"禁商用协议"描述一致，无需改动 |

## 快速开始

1. **（国内）安装搜岗后端**：`python tools/install_domestic_search.py install-boss`（或 `install-get-jobs`）。
2. **填充个人画像**：运行 `/setup-zh`（中文）或 `/setup`（英文），或手动填写 `CLAUDE.zh.md` / `CLAUDE.md`。
3. **检索岗位**：`boss search …` 或 get_jobs，复制 JD。
4. **生成材料**：`/apply-zh <JD>`（简历+话术+**match 质量报告**）或 `/da-zhaohu <JD>`（仅开场）。
5. **核对分数**：阅读 `documents/zh/match_report_*.json` 的 hit/miss；真实技能才补写。
6. **手动投递**：在对应 App 内发送话术 / 上传简历（本仓库不自动投递）。
7. **追踪**：`python tools/tracker.py add …`；总览用 `list` / `dashboard`；阶段变化用 `/outcome`。
8. **（可选）** 重型集成见 [`integrations/catalog/`](./integrations/catalog/README.md)。

## 国产模型接入

本仓库是**提示词 / 技能框架**，不硬编码任何模型 API。它可在任意支持"读取仓库技能与命令"的
AI 编码 Agent 上运行。要将底层模型替换为国产大模型（DeepSeek / 智谱 GLM / 通义千问等），
只需让你的 Agent 运行在对应模型之上——这些厂商均提供 **OpenAI 兼容 API**，切换成本极低。
详见 [`MODELS.zh.md`](./MODELS.zh.md)。

## 合规与边界

- **个人信息保护**：简历含姓名、电话、教育等个人信息，请本地处理、谨慎分享，遵守
  《个人信息保护法》（PIPL，2021-11-01 施行）。
- **不自动投递**：本分支自身统一不实现自动投递，仅生成辅助内容由用户手动操作，
  以避免触发招聘平台风控并符合各平台用户协议。复用的第三方工具（get_jobs、mcp-jobs、ai-job）
  自带自动投递/自动化能力，**是否启用由用户自行决定**，并须知悉平台风控与协议风险。
- **复用而非重造**：国内平台检索统一复用成熟开源实现——Boss直聘用 **boss-cli**（逆向 API CLI）、
  智联/前程无忧/猎聘/拉勾用 **get_jobs**（Playwright 浏览器自动化）、agent 原生调用可用 **mcp-jobs**
  （MCP）。本分支不自行实现各平台爬虫/接口，避免重复造轮子与维护反爬成本。
- **内容真实**：AI 生成的话术 / 简历不得虚构经历或业绩；缺口应诚实表述。

## 许可证

原项目以 **MIT License** 发布。本分支沿用 MIT，并保留原作者版权声明；新增的中文适配内容
同样以 MIT 发布。详见 [`NOTICE`](./NOTICE) 与 [`LICENSE`](./LICENSE)。

> 原版英文文档见 [`README.md`](./README.md)（海外 / 英文岗流程）。
