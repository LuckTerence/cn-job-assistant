# 中文文档入口

> **GitHub 首页主文档已统一为 [README.md](./README.md)**（产品介绍 + 三分钟上手 + 诚实能力清单）。  
> 请直接阅读该页；本文件仅作中文入口与文档索引，避免两份 README 长期漂移。

## 快速链接

| 你想… | 去这里 |
|--------|--------|
| 了解产品、立刻上手 | [README.md](./README.md) |
| **先看演示产出（一条命令）** | `bash scripts/demo.sh` → [examples/demo/](./examples/demo/) |
| 30 秒循环动图 | [docs/assets/demo-loop.gif](./docs/assets/demo-loop.gif) |
| Agent 安装（Claude / Cursor） | [docs/INSTALL.agents.zh.md](./docs/INSTALL.agents.zh.md) |
| 分赛道样例（互联网 vs 国企） | [examples/demo/tracks/](./examples/demo/tracks/) |
| 看架构分层（核心 vs catalog） | [ARCHITECTURE.zh.md](./ARCHITECTURE.zh.md) |
| 接 DeepSeek / 智谱 / 通义 | [MODELS.zh.md](./MODELS.zh.md) |
| 可选重应用的真实搭建成本 | [integrations/catalog/README.md](./integrations/catalog/README.md) |
| 对标调研与历史决策（工程向） | [docs/competitive-research.zh.md](./docs/competitive-research.zh.md) |

## 国内最小命令备忘

```bash
bash scripts/demo.sh   # 离线演示：匹配报告 + 人话摘要 + 看板 + 赛道对比
python tools/install_domestic_search.py status
# Agent: /setup-zh（可粘贴旧简历）→ /apply-zh <岗位描述>
python tools/match_resume.py report --zh-only --resume … --jd … --cover …
python tools/tracker.py suggest-add --company … --role … --channel Boss直聘
python tools/tracker.py today
python tools/tracker.py dashboard
```

## 合规三句话

1. **默认不自动投递**  
2. **数据本地优先**，遵守 PIPL  
3. **不虚构经历**刷匹配分  

许可：MIT（上游 + 本分支适配）。详见 [NOTICE](./NOTICE)、[LICENSE](./LICENSE)。
