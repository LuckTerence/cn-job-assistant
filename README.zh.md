# 中文文档入口

> **GitHub 首页主文档已统一为 [README.md](./README.md)**（产品介绍 + 三分钟上手 + 诚实能力清单）。  
> 请直接阅读该页；本文件仅作中文入口与文档索引，避免两份 README 长期漂移。

## 快速链接

| 你想… | 去这里 |
|--------|--------|
| 了解产品、立刻上手 | [README.md](./README.md) |
| **1.0 发版说明** | [docs/RELEASE-1.0.zh.md](./docs/RELEASE-1.0.zh.md) |
| **1.0 门禁冒烟** | `make check` 或 `bash scripts/smoke_cn.sh` |
| **先看演示产出（一条命令）** | `bash scripts/demo.sh` → [examples/demo/](./examples/demo/) |
| Agent 安装（Claude / Cursor） | [docs/INSTALL.agents.zh.md](./docs/INSTALL.agents.zh.md) |
| 分赛道样例（互联网 vs 国企） | [examples/demo/tracks/](./examples/demo/tracks/) |
| 看架构分层（核心 vs catalog） | [ARCHITECTURE.zh.md](./ARCHITECTURE.zh.md) |
| 接 DeepSeek / 智谱 / 通义 | [MODELS.zh.md](./MODELS.zh.md) |
| 可选重应用的真实搭建成本 | [integrations/catalog/README.md](./integrations/catalog/README.md) |
| 对标调研与历史决策（工程向） | [docs/competitive-research.zh.md](./docs/competitive-research.zh.md) |
| **闭环优化方案（Phase 0–2；验证期进行中）** | [docs/optimization-plan-close-the-loop.zh.md](./docs/optimization-plan-close-the-loop.zh.md) |
| **冷静 UX 文案开发规格（match/today/看板）** | [docs/dev-calmer-ux-copy.zh.md](./docs/dev-calmer-ux-copy.zh.md) |
| 登记「我在用」/ 痛点反馈 | [Issue 模板](./.github/ISSUE_TEMPLATE/) |

## 国内最小命令备忘

```bash
bash scripts/demo.sh   # 离线演示：匹配报告 + 人话摘要 + 看板 + 赛道对比
python tools/install_domestic_search.py status
# Agent: /setup-zh（可粘贴旧简历）→ /apply-zh <岗位描述>
python tools/match_resume.py report --zh-only --resume … --jd … --cover …
python tools/tracker.py suggest-add --company … --role … --channel Boss直聘
python tools/tracker.py today
python tools/tracker.py skip-stats   # 不投原因分布（Phase 1 信号）
python tools/tracker.py import-jobs examples/demo/jobs_sample.json  # 搜岗 JSON → to_apply
python tools/tracker.py rank --track internet   # to_apply 批打分排序
python tools/tracker.py day-plan                # 今天投谁
python tools/flow.py shortlist --jobs examples/demo/jobs_sample.json --track internet
python tools/tracker.py list --open-only --salary-flag --expected-salary '25-40K'
python tools/tracker.py funnel                  # 投递漏斗快照
python tools/split_jds.py -i pasted.txt -o documents/zh/inbox   # 多岗粘贴拆分
python tools/tracker.py dashboard               # 看板：漏斗 + 筛选
```

## 合规三句话

1. **默认不自动投递**  
2. **数据本地优先**，遵守 PIPL  
3. **不虚构经历**刷匹配分  

许可：MIT（上游 + 本分支适配）。详见 [NOTICE](./NOTICE)、[LICENSE](./LICENSE)。
