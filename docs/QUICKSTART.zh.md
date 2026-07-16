# 15 分钟上手（1.2 推荐路径）

> 目标：从 0 到「看过演示 → 填过画像 → 知道下一岗怎么投」。  
> 不需要 Boss 登录；不需要 Docker；不需要下载 embedding。

---

## 你需要什么

| 必须 | 可选 |
|------|------|
| Python **3.10+** | Typst（`brew install typst`，PDF 更好看） |
| 任意 AI Agent（Claude Code / Cursor / 国产模型 Agent） | `poppler`（`pdftotext`，ATS 文本层检查） |
| | Boss 搜岗 CLI（`install-boss`） |

---

## 第 0～3 分钟：确认本机正常

```bash
git clone https://github.com/LuckTerence/cn-job-assistant.git
cd cn-job-assistant
make check
# 等价: 单测 + bash scripts/smoke_cn.sh
```

只想看产出、先不跑全套门禁：

```bash
bash scripts/demo.sh
open examples/demo/output/job_search_tracker.html   # macOS
```

应能看到：示例 PDF、匹配摘要、漏斗/看板、今日计划类文本。

---

## 第 3～8 分钟：填画像（Agent）

在 Agent 里打开本仓库，输入：

```text
/setup-zh
```

**最快**：直接粘贴一份旧中文简历全文（或 @ 文件），按提示确认：

- 目标城市  
- **期望薪资**（如 `25-40K`，后面匹配/薪资旗标会用到）  
- 目标赛道（互联网 / 国企 / 外企 / 体制内 / 应届）  
- 硬约束  

完成后检查：`CLAUDE.zh.md` 里占位符已被替换。

没有 slash 命令时（如部分 Cursor 配置），对 Agent 说：

```text
请严格按仓库 .claude/commands/setup-zh.md 执行国内求职初始化。
下面是我的旧简历：
（粘贴）
```

---

## 第 8～15 分钟：第一份真实岗位

### 方式 A（推荐）：Agent 一站式

```text
/apply-zh
（粘贴 Boss/智联 岗位全文，或链接）
```

会生成：`documents/zh/` 下的简历 **md（粘贴）/ PDF（上传）**、话术、匹配摘要、**投前门禁**；并询问是否写入 tracker（含 match 分）。

投前也可单独跑：

```bash
python tools/quality_gate.py \
  --resume documents/zh/resume_公司.md \
  --jd documents/zh/jd_公司_岗位.md \
  --pdf documents/zh/resume_公司.pdf
# 说明：docs/ats-gate.zh.md
```

### 方式 B：先囤一批再挑

```bash
# 多段 JD 粘到 pasted.txt 后：
python tools/split_jds.py -i pasted.txt -o documents/zh/inbox
python tools/flow.py shortlist --jobs documents/zh/inbox/jobs_stub.json --track internet
python tools/tracker.py day-plan
```

再对 day-plan 里的第一条跑 `/apply-zh`。

### 投递

1. 上传 **`documents/zh/resume_*.pdf`**；表单粘贴用 **同名 `.md`**  
2. 复制打招呼话术（或 `apply_assist semi` 打开页+复制）  
3. **自己点发送**  
4. 状态变化用 `/outcome` 或：

```bash
python tools/tracker.py update --company 某某 --role 后端 --status interview
python tools/tracker.py funnel
python tools/tracker.py dashboard
```

---

## 每天 2 分钟

```bash
python tools/tracker.py day-plan --expected-salary '25-40K'   # 改成你的期望
python tools/tracker.py today
```

---

## 常见卡点

| 现象 | 处理 |
|------|------|
| `make check` 失败 | 看终端最后 30 行；确认 Python≥3.10 |
| 没有 `/setup-zh` | 用上文「没有 slash」提示词，引用 `setup-zh.md` |
| 匹配 miss 里有自己会的词 | 看摘要「同义词已对齐」；仍不对可改 `config/synonyms.json` |
| rank 全是 unscored | `cv_file` 和 `source` 必须是**本地文件路径**，不是仅 URL |
| 想自动打招呼 | 先读 `python tools/apply_assist.py explain`；默认请用 manual/semi |

---

## 反馈（帮产品迭代）

- [我在用](https://github.com/LuckTerence/cn-job-assistant/issues/new?template=using.yml)  
- [痛点](https://github.com/LuckTerence/cn-job-assistant/issues/new?template=pain.yml)  

更多边界见 [RELEASE-1.0.zh.md](./RELEASE-1.0.zh.md)。
