# 国内求职助手（cn-job-assistant）

在 Claude Code / Cursor 这类 Agent 里用的一套**本地求职流程**。  
面向 Boss 直聘、智联、猎聘等：按岗位描述改中文简历和打招呼话术，打个简单匹配分，再记一下投了哪些公司。

**不会替你自动投递。** 生成内容你自己看过，再在 App 里点发送。

基于 [MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search)（MIT）改的国内版。

<p align="center">
  <img src="docs/assets/demo-loop.gif" alt="流程示意" width="640">
</p>

[![CI](https://github.com/LuckTerence/cn-job-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/LuckTerence/cn-job-assistant/actions/workflows/ci.yml)

---

## 先跑一下 Demo（不用填自己的简历）

```bash
git clone https://github.com/LuckTerence/cn-job-assistant.git
cd cn-job-assistant
bash scripts/demo.sh
```

然后打开：

```bash
open examples/demo/output/job_search_tracker.html
```

终端里也会打出匹配摘要。样例数据都是编的，只是让你看看长什么样。

---

## 真要求职时怎么用

需要：Python 3.10+，以及一个能读本仓库的 Agent（Claude Code、Cursor 等）。  
国产模型怎么接：见 [MODELS.zh.md](./MODELS.zh.md)。Agent 怎么挂上本仓库：见 [docs/INSTALL.agents.zh.md](./docs/INSTALL.agents.zh.md)。

```bash
# 可选：装 Boss 搜岗（个人用；许可证自己看上游）
python tools/install_domestic_search.py install-boss
```

在 Agent 里：

1. `/setup-zh` — 填画像（可以直接粘贴一份旧简历）
2. `/apply-zh` — 粘贴岗位链接或全文，生成简历草稿 + 话术 + 匹配摘要
3. 自己到 Boss / 智联里投
4. 记一笔：

```bash
python tools/tracker.py add --company 某某公司 --role 后端 --channel Boss直聘 --status applied
python tools/tracker.py today          # 看看还有哪些在跟
python tools/tracker.py dashboard      # 出个本地 HTML 表
```

`/apply-zh` 跑完后也会给你一条可复制的 `tracker` 命令。

---

## 仓库里有什么（说人话）

| 你要干的事 | 用这个 |
|------------|--------|
| 试跑 / 看样例 | `bash scripts/demo.sh` |
| 装搜岗工具 | `tools/install_domestic_search.py` |
| 改简历、写打招呼 | `/apply-zh`、`/da-zhaohu` |
| 简历和岗位对得上吗 | `python tools/match_resume.py report …` |
| 投了谁、面到哪 | `python tools/tracker.py` |
| 互联网 / 国企样例对比 | `examples/demo/tracks/` |

海外英文 LaTeX 简历那套还在，需要看 [SETUP.md](./SETUP.md)。

**刻意没做成默认能力的：** 要 Docker / Java 全家桶的模拟面试、在线简历站等。说明放在 [integrations/catalog/](./integrations/catalog/README.md)，要用自己装，别指望 clone 下来就能用。

---

## 几个边界

- 默认**不自动投递**（平台风控和协议都麻烦）
- 简历和投递记录尽量留在本地，别随手 push 上去（相关路径已 gitignore）
- 匹配分是本地关键词算法，**不是**「你一定能进」
- 缺的技能如果本来就不会，别硬写上去刷分

---

## 其它文档

- [ARCHITECTURE.zh.md](./ARCHITECTURE.zh.md) — 目录怎么分层的  
- [MODELS.zh.md](./MODELS.zh.md) — DeepSeek / 智谱等  
- [examples/demo/README.md](./examples/demo/README.md) — demo 目录说明  
- [docs/competitive-research.zh.md](./docs/competitive-research.zh.md) — 以前做过的对标笔记（很长，一般不用看）

有问题可以开 Issue（按互联网 / 国企 / 校招分了模板）。

---

MIT。上游版权见 [NOTICE](./NOTICE)、[LICENSE](./LICENSE)。
