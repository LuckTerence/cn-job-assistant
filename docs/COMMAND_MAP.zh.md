# 命令地图与日常节奏（1.1）

> 灵感来自 [career-ops](https://github.com/santifer/career-ops) 的「技能模式清单」：  
> 把能力收成一张表，**每天只跑固定节奏**，而不是记几十个命令。

---

## 一张图：你每天用什么

```text
早  ──► day-plan / today          今天碰谁
中  ──► /apply-zh 或 flow shortlist  产出材料 / 补短名单
投  ──► App 手动点发送（semi 可复制）
晚  ──► weekly-report / funnel / outcome  复盘与记状态
```

---

## 模式一览（对标 career-ops skill modes）

| 模式 | 你想… | 命令 / Agent |
|------|--------|----------------|
| **setup** | 冷启动画像 | `/setup-zh` · [AGENT_PROMPT](./AGENT_PROMPT.zh.md) |
| **demo** | 先看产出 | `make demo` · `make check` |
| **discover** | 找岗入库 | Boss：见下「平台」· `normalize-job-export` · `import-jobs` · `split_jds` |
| **shortlist** | 今天投谁 | `flow shortlist` · `rank` · `day-plan` |
| **apply** | 定制一份材料 | `/apply-zh` · `match report` · `check_profile_resume` |
| **send** | 发出去 | App 手动 · `apply_assist semi`（默认不代点） |
| **track** | 记进度 | `tracker add/update` · `/outcome` · `dashboard` · **`serve` 一键改状态** |
| **review** | 周复盘 | `weekly-report` · `funnel` · `skip-stats` |
| **interview** | 准备面试 | `/interview` · `07-interview-prep` |
| **negotiate** | 谈薪 | catalog `salary-negotiate`（方法论） |

---

## 平台接入（学 boss-agent-cli，不自研爬虫）

推荐（MIT、默认 assisted）：[can4hou6joeng4/boss-agent-cli](https://github.com/can4hou6joeng4/boss-agent-cli)

```bash
# 在对方工具里搜岗并导出 JSON 信封后：
python tools/normalize_job_export.py -i boss_out.json -o jobs.json --source boss-agent
python tools/tracker.py import-jobs jobs.json --default-channel Boss直聘
python tools/flow.py shortlist --track internet
```

本仓库**不内嵌**对方二进制；只做 **JSON/CSV → 本仓 schema** 适配（合法复用接口形状，不复制逆向代码）。

---

## CLI 速查

```bash
# 门禁 / 演示
make check | make demo | make quick

# 发现 → 短名单
python tools/normalize_job_export.py -i raw.json -o jobs.json
python tools/split_jds.py -i pasted.txt -o documents/zh/inbox
python tools/flow.py shortlist --jobs jobs.json --track internet --limit 5

# 匹配与诚信
python tools/match_resume.py report --resume … --jd … --profile CLAUDE.zh.md
python tools/check_profile_resume.py --profile CLAUDE.zh.md --resume documents/zh/resume_….md
python tools/export_resume_pdf.py -i … --verify-text   # 有 pdftotext 时检查 ATS 文本层

# 节奏
python tools/tracker.py day-plan --expected-salary '25-40K'
python tools/tracker.py weekly-report
python tools/tracker.py funnel
python tools/tracker.py dashboard          # 离线：改状态=复制命令
python tools/tracker.py serve              # 本机网页：改状态=直接写 CSV
python tools/export_resume_pdf.py -i r.md --template compact
```

---

## Agent 斜杠命令

| 命令 | 何时 |
|------|------|
| `/setup-zh` | 第一次 / 改画像 |
| `/apply-zh` | 每个要认真投的岗 |
| `/da-zhaohu` | 只要话术 |
| `/outcome` | 面试、拒信、不投、offer |
| `/interview` | 约了面试 |
| `/rank` | 批量评分（仓库命令，若 Agent 已加载） |

无 slash → [AGENT_PROMPT.zh.md](./AGENT_PROMPT.zh.md)。

---

## 和竞品的取舍（人性化默认）

| 学了谁 | 采用 | 不采用 |
|--------|------|--------|
| career-ops | 模式表、批处理叙事、质量优先 | 默认海量扫站 / 高 token 全自动 |
| boss-agent-cli | JSON 信封、assisted 默认、适配器 | 内嵌逆向、默认 greet 代发 |
| Resume-Matcher | 匹配可解释 + catalog 可升级 | 默认拉 embedding |
| get_jobs / JobClaw | 平台覆盖参考 | 默认批量自动投 |

**默认永远：材料助手 + 你点发送。**
