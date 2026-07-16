# 优化方案：先把闭环做透（Phase 0 → 1 → 2）

> **状态**：至 **v0.12「短名单丝滑」**（2026-07-17）：  
> flow shortlist、expected_salary 旗标、语料 IDF、import 字段提示、day-plan/rank。  
> 仍建议并行分发验证；再往后：boss 适配加厚 / embedding catalog / 可选 Web。  
> **原则**：产品成熟度 = 闭环完成度 × 用户反馈验证数，不是功能数。  
> **定位**：Agent 可读可跑的本地求职工作流（非 SaaS、默认不自动投）。  
> **相关**：[`pm-review-2026-07-10.zh.md`](./pm-review-2026-07-10.zh.md)、[`ARCHITECTURE.zh.md`](../ARCHITECTURE.zh.md)、  
> **情绪/节奏文案层（闭环之后）**：[`dev-calmer-ux-copy.zh.md`](./dev-calmer-ux-copy.zh.md)

---

## 0. 一句话决策

**现在不开** `flow.py` / Web 服务端看板 / 语义 embedding / 国内薪资爬库。  
**现在只做**：把已有 `/apply-zh` 主路径的「最后一公里」做丝滑，再用最低成本收集真实痛点信号，有信号再开 Phase 2 的 0–2 项。

---

## 1. 对标与差距（简表）

| 对标 | 可借鉴 | 本项目不照搬 |
|------|--------|----------------|
| career-ops | 全流程叙事 + 社区证明 | 不堆海投自动化 |
| Resume-Matcher | 匹配深度可选 | 默认不拉 embedding |
| Reactive-Resume | 所见即所得 | 不先做重 GUI/SaaS |
| AIHawk 等 | 效率上限 | 默认 manual，合规优先 |

| 维度 | 现状（约） | 缺口 |
|------|------------|------|
| 编排 | `/apply-zh` Step 0–8 已是 Agent 层 flow | **不是**缺 `flow.py` |
| 材料 | PDF + 话术 + match 报告强制 | 基本够用 |
| 收尾 | Step 7 只打印 `suggest-add` | **执行摩擦** → tracker 留存差 |
| 飞轮 | 有 `/outcome`、`match_resume diff` | **无串联引导** |
| 看板 | CSV + HTML + `today` | 表格有，**「下一步待办」弱** |
| 决策字段 | tracker 无 city/salary 等 | 无法按城市/薪资粗看分布 |
| 验证 | 功能多、反馈少 | Phase 1 要补信号，不是补功能 |

---

## 2. 用户与主路径

### 2.1 用户分层

| 类型 | 是谁 | 策略 |
|------|------|------|
| **A 核心** | 用 Claude Code / Cursor 等 Agent 的技术向求职者 | **主投入**：做透 `/apply-zh` 闭环 |
| **B 小众** | 纯 CLI、不用 Agent | 不单独造品牌入口；Phase 2 有信号再薄封装 |
| **C 未来** | 非技术、要网页 | 先 HTML 增强；有同步需求再谈服务端 |

### 2.2 国内最小闭环（已存在）

```text
搜岗 / 粘贴 JD
    → /apply-zh（编排）
        → 简历 PDF + 话术 + match 报告
    → 用户在 App 投递（manual / semi；auto 有门禁）
    → tracker 记一笔
    → /outcome 更新结果
    →（可选）改简历 v2 + match_resume diff
```

### 2.3 真缺口（不是「缺功能列表」）

1. **Tracker 最后一公里断**：Step 7 只打印命令，用户懒得敲 → 记录丢失。  
2. **投完没有「然后呢」**：Step 8 结束即止，跟进 / 复盘 / diff 飞轮不转。  
3. **看板偏「档案」不偏「待办」**：打开 HTML 不知道今天该干什么。  
4. **决策维度薄**：城市/薪资/学历/经验未进 tracker，统计与筛选受限。  
5. **扩功能无证据**：Web / 语义 / 薪资库都是假设痛，未用反馈验证。

---

## 3. 明确不做（直到 Phase 2 触发）

| 项 | 为何现在不做 |
|----|----------------|
| 独立品牌 `tools/flow.py` | A 用户已有 `/apply-zh`；B 用户量未验证 |
| FastAPI / 多端 Web | 已有 HTML；换产品形态、运维面扩大 |
| 默认路径 embedding 语义匹配 | 破坏零依赖卖点；先同义词即可试探 |
| 国内薪资爬库 / 第三方库 | 合规与维护重；先「期望 vs JD 区间」 |

**已止血、不在本方案重复建设**（2026-07 已落地）：

- auto-greet 自定义话术：探测失败则拒绝，引导 semi  
- `salary_lookup` → `integrations/legacy/`，国内主路径不承诺  
- semi Windows 剪贴板  
- `max_batch` 对多 security-id 生效  

---

## 4. 三阶段总览

```text
Phase 0（0–1 周）  做透收尾与待办     → 新用户不问「然后呢？」
Phase 1（1–4 周）  只收集信号         → 5–10 真实用户 / 痛点聚类
Phase 2（4 周+）   按信号选 0–2 项    → 最小可行，禁止四个一起开
```

---

## 5. Phase 0：把现有闭环做丝滑（优先落地）

> **目标**：第一次走完 `/apply-zh` 后，自动具备材料 + 预填追踪 + 明确下一步。  
> **约束**：不做新大功能；改 prompt / 轻改 `tracker.py` 为主。  
> **原则**：tracker **禁止静默写成 `applied`**；必须用户确认意图后再写入。

### 5.1 交付标准（DoD）

新用户用 `/apply-zh` 完成**第一个岗位**后，应同时满足：

| # | 标准 |
|---|------|
| D1 | 有可投递 **PDF** 简历 |
| D2 | 有 **人话版** match 摘要（`brief` / 一页摘要） |
| D3 | Agent **已执行** `suggest-add`（或等价预填），用户 **确认一次** 即可写入 tracker |
| D4 | 用户清楚：等回复 → `/outcome`；有结果记一笔；改简历可 `diff` |
| D5 | `dashboard` HTML 顶部有 **下一步待办**（有数据时可见，无则隐藏） |
| D6 | 若 Agent 抽到城市/薪资等，可写入 tracker **可选列**（允许空） |

### 5.2 工作项明细

#### P0.1 强化 `/apply-zh` Step 7：预填 tracker，确认后写入

| 项 | 内容 |
|----|------|
| **问题** | 只打印 `suggest-add`，复制粘贴摩擦高 |
| **做法** | ① Agent **直接运行** `python tools/tracker.py suggest-add …`（预填公司/岗位/渠道/文件路径）<br>② 向用户展示预填摘要，并**明确询问**状态意图：`to_apply`（还没投）/ `applied`（已投）/ 稍后<br>③ 用户确认后，Agent 再执行 `tracker.py add … --status <确认值>`<br>④ 未确认则**不写入** CSV |
| **改哪些** | 主要：`.claude/commands/apply-zh.md` Step 7 文案与强制步骤<br>可选：`suggest-add` 输出更「可一键 add」的完整命令行（`tools/tracker.py` 小改） |
| **不改** | 不新增第二套编排 CLI；不默认 `applied` |
| **可复用** | 现有 `suggest-add` / `add`；零新依赖 |
| **是否自研** | 否（编排提示 + 现有工具） |
| **风险** | Agent 误写 applied → 用确认门禁；重复 add → 沿用现有 company+role+channel 幂等更新逻辑 |
| **验收** | 人工走一遍 `/apply-zh`：未说 yes 时 CSV 无新行；说 yes 后有一行且字段正确 |

#### P0.2 Step 8 收尾：下一步引导 + 飞轮提示

| 项 | 内容 |
|----|------|
| **问题** | 投完即结束；`/outcome` 与 `diff` 无人发现 |
| **做法** | Step 8 固定输出「下一步」块，至少包含：<br>• **已投/待投**：3 天无回复可 `/outcome` 记跟进；面试/offer/拒信也来记<br>• **改简历 v2 后**：主动问是否 `match_resume.py diff --before … --after …`<br>• **日常**：`tracker.py today` / `dashboard` |
| **改哪些** | `.claude/commands/apply-zh.md` Step 8 |
| **可选** | `.claude/commands/outcome.md` 文末链回「改简历 → diff」一句 |
| **是否自研** | 否（prompt only） |
| **验收** | 交付回复中必含「然后呢」三节之一（跟进 / 结果 / 改进） |

#### P0.3 `dashboard` HTML 增加「下一步待办」区

| 项 | 内容 |
|----|------|
| **问题** | 看板是表格档案，不是工作台 |
| **做法** | 在 `export_html` 顶部增加卡片区（纯静态 HTML，无服务端）： |
| **规则（建议 v1，可解释）** | |
| | 📅 **近期面试**：`status` ∈ interview* 且 notes/约定字段含日期（**无日期则不展示「明天」类文案**，改为「进行中的面试：N」） |
| | ⏰ **建议跟进**：`status` ∈ {applied, screening, to_apply…} 且 `date` 距今 ≥ **7 天**，仍 open |
| | 📝 **建议复盘**：`status` ∈ {rejected, no_response, withdrawn, offer_declined} 近 **30 天** |
| | 与 `tracker today` 分组语义尽量一致，避免两套逻辑长期分叉（抽取共享 helper 更佳） |
| **改哪些** | `tools/tracker.py` → `export_html`（及必要时 `cmd_today` 共用函数） |
| **测试** | `tests/test_tracker.py`：构造固定日期的 fixture 行，断言 HTML 含/不含卡片 |
| **可复用** | 现有 HTML export；stdlib |
| **是否自研** | 是（轻量规则 UI，无成熟轮子值得引入） |
| **验收** | `dashboard` 打开可见待办；空数据不报错、不显示假面试 |

#### P0.4 JD 结构化字段：Agent 抽取 + tracker 可选列

| 项 | 内容 |
|----|------|
| **问题** | 无法按城市/薪资粗看投递结构 |
| **做法** | • Step 0 已要求 Agent 抽：薪资/城市/学历/经验 → **写入 suggest-add / add 可选参数**<br>• `HEADER` 增 4 列（均允许空）：`salary` / `city` / `education` / `experience`<br>• **不写复杂正则 JD 解析器**（CLI-only 路径列可为空） |
| **改哪些** | `tools/tracker.py` HEADER + add/update/suggest-add 参数 + HTML 表头可选展示<br>`apply-zh.md` Step 0/7 传参说明<br>`tests/test_tracker.py` 兼容旧 CSV（缺列填空） |
| **兼容** | `read_rows` 已对缺失 key 填空；扩展 HEADER 时旧文件应仍可读，写回时带新列 |
| **可复用** | Agent 抽取；无新依赖 |
| **是否自研** | schema 扩展是；解析不自研 |
| **验收** | 旧 CSV 不炸；新 add 可带 city/salary；list/html 可见或可忽略空列 |

### 5.3 Phase 0 推荐实施顺序

```text
P0.1（apply-zh Step 7）
  → P0.2（Step 8 引导）
  → P0.3（HTML 待办）
  → P0.4（四列 + 传参）
```

P0.1 + P0.2 可同一 PR（纯/主 prompt）。  
P0.3、P0.4 建议分 PR，便于测试与回滚。

### 5.4 Phase 0 非目标

- 不实现 `/feedback` 命令体（属 Phase 1）  
- 不上 Web 服务、不同步多设备  
- 不改匹配算法、不上同义词表（除非 Phase 1 信号触发）  
- 不引入国内薪资数据源  

---

## 6. Phase 1：验证期（不写大功能，只收集信号）

> **目标**：用最低成本回答「用户真痛在哪」，避免闭门造车。  
> **时长建议**：1–4 周或凑齐触发条件为止。

### 6.1 工作项

| ID | 做什么 | 产出 | 状态 |
|----|--------|------|------|
| **P1.1** | 轻量反馈通道 | Issue 模板 `pain.yml`：命令太多 / 匹配不准 / 不知薪资 / 要网页 / … | ✅ 2026-07-16 |
| **P1.2** | tracker：`skipped` + **原因枚举** | 列 `skip_reason`；CLI `skip-stats`；`/apply-zh` 7C；看板不投卡片 | ✅ 2026-07-16 |
| **P1.3** | README 前置「用户故事」 | README「一个用户故事」+ demo 路径 | ✅ 2026-07-16 |
| **P1.4** | 「我在用」Issue 模板 | `using.yml`：年限 / 岗位 / 城市 / 已投数量 / Agent | ✅ 2026-07-16 |

> **验证期仍在继续**：工具已齐，等 **5–10 名非作者用户** 与可聚类痛点；未达触发条件不开 Phase 2 大功能。

### 6.2 Phase 2 触发条件（满足 **任意 1–2 条** 再开）

| 条件 | 阈值 |
|------|------|
| ≥ **5–10** 名**非作者**用户走完 ≥ **3** 个岗位闭环 | 有真实留存 |
| 同一痛点被 ≥ **3** 人明确提出（反馈或 Issue） | 痛点可复现 |
| tracker「不投原因」某一项占比 ≥ **40%**（样本量建议 ≥ 10 条 skipped） | 功能优先级有数据 |

**软约束**：Phase 2 **一次只开 1 个主项**（最多「1 主 + 1 顺手小改」），做完再看下一批信号。

### 6.3 Phase 1 明确不做

- 不实现完整 `/feedback` 分析后台  
- 不强制用户上传反馈到公网  
- 不为了「好看」先做 Web  

---

## 7. Phase 2：扩圈期（按信号选 0–2 项）

| 信号 | 做啥 | 最小可行（MVP） | 明确不做 |
|------|------|-----------------|----------|
| ≥3 人「命令太多」且 **不用 Agent、纯 CLI** | 薄 `tools/flow.py apply` | 子进程顺序调：export → match report → suggest-add；与 `/apply-zh` 对齐，**不另立产品名** | 不重写业务逻辑 |
| ≥3 非技术用户要「网页看进度」 | **加强现有 HTML** | 状态展示优化、本地可编辑若必要用最简方式；**仍不起服务** | 不上 FastAPI，除非明确「多设备同步」 |
| ≥5 人「匹配 miss 胡扯」 | **同义词表** | ✅ 已落地：`config/synonyms.default.json` + 可选 `synonyms.json` | 默认仍不上 sentence-transformers |
| ≥5 人「不知薪资不敢投」 | **期望 vs JD 区间** | ✅ 已落地：`match_resume salary` + report 摘要（✅/⚠️/❌） | 不爬职友集/看准 |
| 搜岗 → 手记摩擦（工程已先落地） | **`import-jobs`** | ✅ JSON/NDJSON/CSV → `to_apply` + 去重 | 不自研新爬虫 |

语义 embedding、国内薪资库、服务端看板：仅当 MVP 仍不够 **且** 信号持续时，再单独立项评估。

---

## 8. 可复用轮子 vs 自研

| 能力 | 策略 |
|------|------|
| 编排 | 复用 `/apply-zh`，不自研 workflow 引擎 |
| 追踪 | 复用 `tracker.py` CSV 权威源 |
| 匹配 | 复用 `match_resume.py`；同义词后期轻扩 |
| 看板 | 复用 `export_html`；规则待办自研（小） |
| 反馈 | Issue 模板 / 本地文件，不自研问卷平台 |
| 鉴权/队列/向量库等 | **禁止**为本阶段引入 |

---

## 9. 成功指标（建议）

| 阶段 | 指标 | 目标感 |
|------|------|--------|
| Phase 0 | 内部走通 DoD D1–D6 | 作者/同伴 1 次完整演示无「然后呢」 |
| Phase 0 | tracker 写入率（apply 后） | 相对「只打印命令」明显上升（质性即可） |
| Phase 1 | 外部用户数 | 5–10 人完成 ≥3 岗 |
| Phase 1 | 可聚类痛点 | 至少 1 个痛点 ≥3 票 或 skipped 原因 ≥40% |
| Phase 2 | 只做一个主项且可测 | 有前后对比（吐槽减少或使用率） |

---

## 10. 风险与合规

| 风险 | 缓解 |
|------|------|
| Agent 误记 applied | 强制确认；默认倾向 `to_apply` 若用户未明说已投 |
| HTML 待办规则误导 | 无日期不说「明天」；文案用「建议」非「必须」 |
| schema 扩展破坏旧 CSV | 缺列填空；测试覆盖 |
| Phase 1 无用户导致空转 | 并行 P1.3/1.4 分发；不因空反馈开大功能 |
| 合规 | 不改变「默认不自动投」；个人数据本地、gitignore 不变 |

---

## 11. 文档与代码落点清单（实施时用，本阶段不改代码）

| 落点 | Phase |
|------|--------|
| `.claude/commands/apply-zh.md` | 0.1、0.2、0.4 |
| `.claude/commands/outcome.md`（可选一句） | 0.2 |
| `tools/tracker.py` + `tests/test_tracker.py` | 0.3、0.4、1.2 |
| `examples/demo/` 或 README 故事段 | 1.3 |
| `.github/ISSUE_TEMPLATE/` | 1.1 轻量 / 1.4 |
| `tools/flow.py`（仅触发时） | 2 |
| `match_resume` + synonyms（仅触发时） | 2 |
| brief 薪资对比（仅触发时） | 2 |

---

## 12. 与历史评审的关系

| 来源 | 采纳 | 调整 |
|------|------|------|
| PM 四维评审中的 P0 缺陷修复 | 已在工程止血中处理 | — |
| 原「P1 flow.py」 | 降为 Phase 2 条件项 | 编排以 `/apply-zh` 为准 |
| 原「P2 Web / 语义 / 薪资」 | 降为信号驱动 MVP | 先 HTML / 同义词 / 期望对比 |
| 本方案核心增量 | **收尾 + 待办 + 轻量 schema + 验证** | 成熟度公式优先于功能清单 |

---

## 13. 批准与下一步

| 项 | 状态 |
|----|------|
| 方案文档 | ✅ 已写入本文件 |
| 产品代码 | ⏸ **按决策暂不修改** |
| 建议下一动作 | 人工批准 Phase 0 范围后，按 **0.1 → 0.2 → 0.3 → 0.4** 开 PR 实施 |

**批准人签字栏（可选）**

- 产品：________  日期：________  
- 工程：________  日期：________  

---

## 附录 A：Step 7 交互示意（实施时写入 apply-zh）

```text
[Agent 已执行]
  python tools/tracker.py suggest-add --company … --role … --channel … \
    --cv … --cover … --source … [--city … --salary …]

[预填摘要]
  公司 / 岗位 / 渠道 / 文件路径 / 可选城市薪资
  建议状态：to_apply（尚未确认已投）或 applied（你已说明投了）

[问用户]
  是否写入 tracker？状态选：to_apply / applied / 跳过

[仅当用户确认]
  python tools/tracker.py add … --status <选择>
```

## 附录 B：不投原因枚举（Phase 1.2 草案）

| 值 | 含义 |
|----|------|
| `salary_low` | 薪资不满足 |
| `location` | 地点/通勤不合适 |
| `low_match` | 匹配度不够 / 不会硬性要求 |
| `unknown_company` | 不了解公司 / 风险感 |
| `other` | 其他（notes 自由填写） |

状态建议：`skipped`（或 `passed`），归入 CLOSED 或单独 OPEN 外集合，避免污染「在途投递」统计。
