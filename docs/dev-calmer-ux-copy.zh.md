# 开发文档：求职情绪 / 节奏 / 认知 UX（冷静文案层）

> **状态**：开发规格已定稿，**待实现**（本文件仅文档）。  
> **日期**：2026-07-11  
> **类型**：不改架构、零新依赖；只调整「工具怎么说话」与呈现。  
> **前置**：闭环收尾已落地（见 [`optimization-plan-close-the-loop.zh.md`](./optimization-plan-close-the-loop.zh.md)）。  
> **相关代码**：`tools/match_resume.py`、`tools/tracker.py`、`.claude/commands/apply-zh.md`、`scripts/demo.sh`

---

## 0. 一句话目标

在用户**被拒、匹配分低、几天没动静**时，工具不说错话：  
不羞辱、不催命、不鼓励海投；给**可执行下一步**，保持诚实（不会的别编）。

**产品成熟度补丁** = 情绪安全 × 节奏稳 × 行动清晰，**不是**新功能数。

---

## 1. 背景与问题

| 层 | 现状痛点 | 用户感受 |
|----|----------|----------|
| **情绪** | brief「还差 N 个关键词」；看板一长串 `rejected` | 「我什么都不会」「全军覆没」 |
| **节奏** | `today` 全是待办压力；空列表像在怪你 | guilt、焦虑、关掉工具 |
| **认知** | 低分只有数字；error 很技术；首次成功无锚点 | 「是不是我操作错了」 |
| **温度** | 周末仍催跟进；统计只有 unfinished 视角 | 工具像催命系统，不像同伴 |

**不在本范围**：语义匹配、Web 服务、薪资库、批量海投、独立情绪 SaaS。

---

## 2. 设计原则（实现红线）

1. **诚实 > 鸡汤**  
   低匹配仍说「有距离 / 别抱太大期望」；始终保留「不会的别硬编」。
2. **质量 > 数量**  
   只出现「改好再投」；禁止「再投 10 个冲冲冲」。
3. **温度低频**  
   鼓励语按条件触发，不是每条 rejected 一句。
4. **零新依赖**  
   仍 Python stdlib；不新增配置服务、不强制新 CSV 列（鼓励计数用规则即可）。
5. **测试锁关键词，不锁死全文**  
   断言短语（如「不会的别硬编」「行动建议」），避免整段 snapshot。
6. **内部 error 可保留英文/技术**  
   只改用户高频入口的人话（`add`/`suggest-add`/`today`/`brief`/`dashboard`）。

---

## 3. 范围与优先级

### 3.1 本轮必做（Sprint A · P1–P3）

| ID | 名称 | 工作量感 | 用户触点 |
|----|------|----------|----------|
| **UX-P1** | match brief 冷静化 + 分档行动建议 | ~1h | 每次 `/apply-zh` / `match_resume report` |
| **UX-P2** | `today` 空状态人话 + 周末降调 + 正反馈统计 | ~30min | 每天打开 |
| **UX-P3** | HTML 已结束默认折叠 + 低频鼓励一句 | ~1h | 打开 dashboard |

### 3.2 本轮可选紧随（Sprint A+ · 同一 PR 或紧接着）

| ID | 名称 | 工作量感 |
|----|------|----------|
| **UX-A4** | brief 分档行动建议（并入 P1，不单独排期） | 含在 P1 |
| **UX-A5** | demo.sh 结尾人话 | ~10min |
| **UX-A6** | apply-zh 首次 tracker 写入成功庆祝句 | ~15min（prompt only） |

### 3.3 第二批（Sprint B · P1–P3 合上后再做）

| ID | 名称 |
|----|------|
| **UX-B1** | 用户路径 CLI 人话 error（`add`/`suggest-add` 缺参等） |
| **UX-B2** | dashboard / suggest-add 反海投 hint（本周>10 / 当日≥3） |
| **UX-B3** | dashboard 空状态中文（非 `empty`） |
| **UX-B4** | `/outcome` 记 rejected 时可选一句鼓励（prompt，低频） |

### 3.4 明确不做 / 缓做

| 项 | 原因 |
|----|------|
| 独立 `/encourage` 命令 | 过度产品化；挂 today/outcome 即可 |
| CSV 列 `encouragement_shown` | 第一版用「本周 rejected 数 % 3」规则足够 |
| 精确「后天面试」日历 | 缺可靠面试日期字段；notes 不规范时易胡说 |
| 批量导入 / 一键投 100 | 反产品定位 |
| 默认路径 embedding | 与零依赖冲突 |

---

## 4. UX-P1：match brief 冷静化（核心）

### 4.1 现状锚点

| 函数 | 文件 | 作用 |
|------|------|------|
| `build_zh_brief` | `tools/match_resume.py` | 生成 `brief_zh` dict |
| `format_zh_brief` | 同上 | 渲染一页中文摘要 |
| `quality_report` | 同上 | 组装 suggestions + brief |
| 用户出口 | `report --zh-only` / `--brief-out` / `format_report_human` 头部 | |

当前语气问题示例：

- suggestions：`还有 N 个岗位里的词材料里没出现`（易读成「你不行」）  
- miss 列表未分「硬技能 / 锦上添花」  
- 高分无开场肯定；低分无「练手/换方向」缓冲  
- 缺分档「下一步行动」段

### 4.2 目标输出结构（`format_zh_brief`）

```text
【匹配摘要】
{tone_open}                    # 按分数开场（见 4.4）
综合 xx/100（…），关键词覆盖 xx%

已经对上的词：
  …

JD 提到但你简历没写的词（不会的别硬编）：
  · 核心硬技能（会再补，不会别编）：a、b
  · 其他要求（锦上添花）：c、d
  （若两类皆空：没有，挺好）

[可选] 只写在打招呼里、简历正文没有的：
  …

如果属实，可以改的方向：
  1. …
  2. …
  3. …

【下一步建议】
{action_by_band}               # 按分数区间（见 4.5）

不会的技能别硬写上去刷分。
分数只是本地关键词对齐程度，不代表能不能拿到面试。
```

### 4.3 miss 二分规则（实现约定）

**目标**：把 `still_miss` 拆成：

- `miss_core`：核心硬技能  
- `miss_nice`：锦上添花  

**v1 启发式（无模型、可测）**：

```text
term ∈ miss_core  若 满足任一：
  1. term 小写 ∈ SKILL_TERMS 或 PHRASE_TERMS（已有词表）
  2. 匹配常见技术/证书形态：含英文技术栈片段、或长度≥2 的 CJK 且像技能（可复用 extract 时 is_skill 逻辑）
  3. 可选：在 JD 前 40% 正文出现（职责/要求段更靠前）→ 加权 core

term ∈ miss_nice  若 不在 miss_core
```

展示时：

- core 最多 6 个，nice 最多 6 个（总展示仍控制在可读）  
- 标签文案固定：  
  - core：`核心硬技能（会再补，不会别编）`  
  - nice：`其他要求（锦上添花）`

**禁止**：把全量 miss 叫「还差 N 个关键词」。

### 4.4 开场语气 `tone_open`（用 combined_score）

| 分数 score | 开场（示例，可微调措辞） |
|------------|--------------------------|
| **≥ 70** | `这份和你挺匹配的。`（可用 👍，注意纯文本终端兼容） |
| **40–69** | 可无单独鸡汤开场，或轻句：`有一定匹配度，重点看下面缺口是否属实。` |
| **< 40** | `这个岗位要求和你当前画像有距离——投了当练手也行，别抱太大期望；也可以想想是不是方向不太对。` |

**禁止**：`你太差了` / `匹配失败` / `不合格` 等羞辱词。

### 4.5 分档行动建议 `action_by_band`

| 分数 | 文案（固定语义，措辞可微调） |
|------|------------------------------|
| **80–100** | 这份很匹配，重点准备面试就行。 |
| **60–79** | 基本匹配，建议把上面「核心硬技能」里**你确实会的**补进简历；不会的别编。 |
| **40–59** | 有一定匹配但缺口不少，可以投但别抱太大期望；或再找更贴近画像的岗位。 |
| **< 40** | 匹配度较低，投了权当练手；建议优先找和你画像更接近的岗位。 |

写入 `brief_zh` 字段建议：

```python
{
  ...
  "tone_open": str,
  "miss_core": list[str],
  "miss_nice": list[str],
  "action_by_band": str,
  # 保留 still_missing 作兼容（= core+nice 或原列表），避免破坏 diff/旧 JSON
}
```

### 4.6 `quality_report` suggestions 文案替换

| 旧 | 新方向 |
|----|--------|
| `还有 N 个岗位里的词材料里没出现` | `JD 里还有一些词材料没写到；会的再补，不会的当差距，别编。` |
| 覆盖率 <50% 的建议 | 保持诚实，语气改为「偏少」而非「不够格」 |

### 4.7 测试（`tests/test_match_resume.py` 或新建用例）

| 用例 | 断言 |
|------|------|
| 高分 fixture | brief 含肯定语义（如「挺匹配」）+ 行动建议含「面试」 |
| 低分 / 弱简历 fixture | 含「有距离」或「练手」；**不含**「还差」羞辱式标题 |
| miss 二分 | 已知 skill miss 进 core（若词表命中） |
| 合规 | 始终含「别硬」或现有 compliance 句 |
| JSON 兼容 | `still_missing` 仍存在；新字段可选 |

### 4.8 非目标（P1）

- 不改 TF–IDF / score 计算公式  
- 不上同义词表（属 Phase 2 匹配增强）  
- 不改英文 `format_score_human` 的专业指标区（可仅中文 brief）

---

## 5. UX-P2：`tracker today` 节奏与正反馈

### 5.1 现状锚点

- `cmd_today` + `build_action_items`（`tools/tracker.py`）  
- 空待办时偏「暂无」清单感  
- 统计偏「还有多少没完成」

### 5.2 行为规格

#### 5.2.1 完全无紧急待办时

定义：**interviews 空且 follow_ups 空**（reviews 可有，但不算「紧急」）。

输出（示例）：

```text
今天没有紧急的事。投简历是马拉松，歇一天也没关系。
想投新岗位随时 /apply-zh。
```

然后再可选展示「最近结束 / 复盘」弱区块，**不要**用空列表制造失败感。

#### 5.2.2 周末降调（周六日）

当 `today.weekday() >= 5` 且存在 `follow_ups`：

- 在跟进区块前或后加一句：  
  `今天是周末，HR 大概率不上班。不急的话下周一再跟进也来得及。`  
- **不要**去掉 follow_up 列表（信息仍在），只降催促语气。

#### 5.2.3 正反馈统计行（每次 today 都可有）

在开头或结尾增加（数字为 0 也诚实显示）：

```text
本周已记录投递：W 条（status 为 applied/screening/interview*/offer 等「已行动」口径，见下）
累计已投：A 条
累计进入面试阶段：I 条
面试率：I/A = xx%（A=0 时写「暂无」不除零）
```

**口径建议（写死在代码注释 + 本文件）**：

| 指标 | 统计规则 |
|------|----------|
| **累计已投 A** | `status` 曾表达投递意图：`applied`, `screening`, `interview*`, `offer`, `hired`, `rejected`, `no_response`, … **排除** `to_apply`, `skipped` |
| **累计面试 I** | `status ∈ INTERVIEW_STATUSES` 或历史曾面试——v1 简化：当前或 closed 中 status 名含 interview / 属于 `INTERVIEW_STATUSES ∪ {interview_only}` |
| **本周已投 W** | `date` 落在本周（周一为周初）且计入 A 的集合 |
| **面试率** | `I / A`，A>0 |

v1 允许简化为「当前 CSV 快照」而非完整状态机历史。

### 5.3 测试

| 用例 | 断言 |
|------|------|
| 空 CSV / 仅 to_apply | 输出含「没有紧急」或「马拉松」类文案 |
| 构造 follow_up + mock 周末 | 含「周末」 |
| 有 applied 行 | 含「累计」或「本周」数字 |

可用 `unittest.mock` patch `date.today`。

---

## 6. UX-P3：HTML dashboard 视觉压力与低频鼓励

### 6.1 现状锚点

- `export_html`：已有待办卡片、open/closed 两表  
- closed 全量展开 → rejected 刷屏

### 6.2 已结束表折叠（纯静态 HTML）

**方案（推荐，无构建工具）**：

```html
<details class="closed-fold">
  <summary>📝 近 30 天结束 / 已结束共 N 条（点击展开）</summary>
  <!-- 原 closed table -->
</details>
```

- 默认 **折叠**（`<details>` 无 `open`）  
- summary 文案带数量  
- 进行中表 **保持展开**

可选增强：仅当 `len(closed_rows) >= 3` 才折叠；0–2 条可直接展示（避免多余点击）。**推荐：≥1 即折叠**，统一心智。

### 6.3 统计区正反馈卡片

在现有 total/open/closed/interview/to follow 旁或下增加：

| 卡片 | 含义 |
|------|------|
| 累计已投 | 同 today 口径 A |
| 面试次数 | I |
| 面试率 | I/A |

### 6.4 低频鼓励语

**触发（满足其一即可，每次 generate dashboard 最多 1 句）**：

1. 近 30 天 `rejected` + `no_response` 条数 ≥ 3，且 `count % 3 == 0`  
2. 或：本周 closed 中 rejected ≥ 3  

**文案池（v1，≥5 句，随机或稳定 hash 选 1）**：

```text
投了就比光收藏不投的人强一步。
这个岗位不合适很正常，继续找更贴的。
每次结束都是在缩小「什么适合我」的范围。
拒绝是流程的一部分，不是对你整个人的判决。
先保证每份材料有针对性，比多投一个更重要。
```

**展示位置**：待办区下方一条 `div.encourage`，灰色小字。  
**禁止**：每条 closed 行跟一句；禁止弹窗。

实现：`tools/tracker.py` 内 `ENCOURAGEMENTS: tuple[str, ...]` + `pick_encouragement(seed: str) -> str | None`。  
seed 可用 `f"{today}:{len(rejected)}"` 保证同日稳定，避免刷新乱跳。

### 6.5 空状态

| 场景 | 文案 |
|------|------|
| 0 行 | `还没有投递记录。准备好了就 /apply-zh <JD> 开始第一个。`（替换 `empty`） |
| 有 open 无 action | 待办卡已有「暂无待办」→ 可改为与 today 一致的马拉松句（短） |

### 6.6 测试

| 用例 | 断言 |
|------|------|
| 多条 rejected | HTML 含 `<details` 与「展开」类文案 |
| 空 init | 含「还没有投递」或中文空状态 |
| 3+ rejected | 可能含鼓励句之一（或 seed 稳定命中） |

---

## 7. Sprint A+ / B 简要规格

### 7.1 UX-A5 demo.sh

在脚本成功结束、打印路径之后：

```text
👆 这就是跑完一个岗位后的完整产出。
打开 examples/demo/output/job_search_tracker.html 看投递看板——你真实用的时候长这样。
```

### 7.2 UX-A6 apply-zh 首次成功

Step 8：若本会话 **首次** `tracker add` 成功：

```text
✅ 第一份材料准备好了！这是最难的一步——接下来会越来越顺。
```

Agent 用「本会话是否已 add 过」判断即可；不强制读 CSV 全局首次。

### 7.3 UX-B1 人话 error

| 入口 | 旧 | 新 |
|------|----|----|
| add 无 company | `error: --company is required` | `需要告诉我是哪家公司：加上 --company 公司名` |
| suggest-add 同理 | 同上 | 同上 |
| update 无匹配 | 可保留 error，或加「没找到这家，检查公司名？」 | |

stderr 仍 exit code 不变。

### 7.4 UX-B2 反海投

| 触点 | 条件 | 文案方向 |
|------|------|----------|
| dashboard 页脚 | 本周 A ≥ 10 | 建议慢下来，改好再投 |
| suggest-add 成功打印后 | 当日 date=today 且 A_today ≥ 3 | 今天已经记了 X 条，质量比数量重要 |

**不做**批量导入。

---

## 8. 文件改动清单

| 文件 | Sprint | 改动 |
|------|--------|------|
| `tools/match_resume.py` | A-P1 | `build_zh_brief` / `format_zh_brief` / suggestions / miss 二分 |
| `tests/test_match_resume.py` | A-P1 | brief 语气与分档 |
| `tools/tracker.py` | A-P2/P3 | `cmd_today`、`export_html`、鼓励池、统计 helper |
| `tests/test_tracker.py` | A-P2/P3 | today / html 断言 |
| `scripts/demo.sh` | A+ | 结尾人话 |
| `.claude/commands/apply-zh.md` | A+ | 首次成功句 |
| `.claude/commands/outcome.md` | B | rejected 低频鼓励（可选） |
| `docs/dev-calmer-ux-copy.zh.md` | 本文件 | 规格 |

**不改**：`ARCHITECTURE` 分层、skill allowlist、boss-cli 行为、CSV 权威源地位。

---

## 9. 实现顺序（给开发）

```text
1. match_resume: miss 二分 helper + build_zh_brief 字段扩展
2. format_zh_brief 新版式 + suggestions 文案
3. pytest match
4. tracker: stats helpers（本周/累计/面试率）
5. cmd_today 空态 + 周末 + 正反馈
6. export_html 折叠 + 统计卡 + 鼓励
7. pytest tracker
8. （可选）demo.sh + apply-zh 一句
9. 人工：跑弱简历 report、dashboard 多 rejected 样例
```

---

## 10. 验收清单（DoD）

### Sprint A

- [ ] 弱匹配 brief：**无**「还差 N 个关键词」当头；**有**「不会的别硬编」  
- [ ] 弱匹配：**有**低分行动建议（练手/换方向）  
- [ ] 强匹配：**有**肯定开场 +「准备面试」类建议  
- [ ] miss 尽量分核心 / 锦上添花两行  
- [ ] `today` 无紧急待办：人话马拉松，不 guilt  
- [ ] 周末 + 有跟进：出现周末降调句  
- [ ] `today`/dashboard：可见累计已投与面试率（有数据时）  
- [ ] dashboard closed 默认折叠  
- [ ] 多 rejected 时最多一句鼓励，非刷屏  
- [ ] `pytest` 相关全绿  
- [ ] 无新第三方依赖  

### Sprint B（另开）

- [ ] 关键 CLI 缺参人话  
- [ ] 反海投 hint 条件正确、不啰嗦  
- [ ] 空 dashboard 中文引导  

---

## 11. 风险与回滚

| 风险 | 缓解 |
|------|------|
| miss 二分误判 | 标注「启发式」；core 为空时 nice 仍展示全 miss |
| 鼓励变鸡汤 | 低频 + 诚实底线 + 池子短 |
| 面试率误导 | 注明「基于当前 tracker 快照，非官方转化率」 |
| 旧 brief JSON 消费者 | 保留 `still_missing`；新字段只增不删 |
| HTML 折叠老浏览器 | `<details>` 现代浏览器均支持；可接受 |

回滚：单文件 git revert `match_resume.py` / `tracker.py` 即可，无迁移脚本。

---

## 12. 提交信息建议

```text
feat: calmer UX copy for match brief, today, and dashboard

Rewrite Chinese match briefs with score-band tone and core/nice gaps,
soften tracker today empty/weekend messaging, add constructive stats,
and collapse closed rows on the HTML dashboard with rare encouragement.
```

---

## 13. 与既有方案关系

| 文档 | 关系 |
|------|------|
| `optimization-plan-close-the-loop.zh.md` | 闭环收尾（Phase 0）——**已实现**；本文是其上的**说话方式层** |
| `pm-review-2026-07-10.zh.md` | 工程/功能评审；本文补「情绪与节奏」维度 |
| Phase 2 flow/Web/语义/薪资 | **仍按信号触发**；本文不提前开 |

---

## 14. 批准与下一步

| 项 | 状态 |
|----|------|
| 开发文档 | ✅ 本文件 |
| 代码 | ⏸ 待按 Sprint A 开工 |
| 建议下一动作 | 实现 **UX-P1 → P2 → P3**，可选 A5/A6，再开 B |

**批准**

- 产品：________  日期：________  
- 工程：________  日期：________  
