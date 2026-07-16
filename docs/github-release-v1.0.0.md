# CN Job Assistant 1.0.0

国内 **Agent 求职最小可靠闭环**：本地优先 · 默认手动投 · 可量化 · 可追踪。

**仓库**：https://github.com/LuckTerence/cn-job-assistant  
**完整说明**：[docs/RELEASE-1.0.zh.md](https://github.com/LuckTerence/cn-job-assistant/blob/master/docs/RELEASE-1.0.zh.md) · [CHANGELOG](https://github.com/LuckTerence/cn-job-assistant/blob/master/CHANGELOG.md)

---

## 一分钟上手

```bash
git clone https://github.com/LuckTerence/cn-job-assistant.git
cd cn-job-assistant
make check                 # 离线门禁：单测 + 产品冒烟
bash scripts/demo.sh       # 看示例产出
# Agent 内：/setup-zh → /apply-zh <岗位描述>
```

日常短名单：

```bash
python tools/flow.py shortlist --jobs jobs.json --track internet
python tools/tracker.py day-plan
python tools/tracker.py funnel
python tools/tracker.py dashboard
```

---

## 1.0 能力面（0.10～0.13 累积）

| 能力 | 入口 |
|------|------|
| 离线演示 / 门禁 | `demo.sh` · `smoke_cn.sh` · `make check` |
| 短名单编排 | `tools/flow.py shortlist` |
| 今日计划 / 批打分 | `tracker day-plan` · `rank` |
| 投递漏斗 | `tracker funnel` + 看板卡片 |
| 粘贴多 JD | `tools/split_jds.py` |
| 匹配 · 真缺口 · 同义词 · 薪资 | `match_resume report` / `salary` |
| 搜岗入库 | `tracker import-jobs` |
| 不投原因 | `skipped` + `skip-stats` |
| 投递三档 | `apply_assist`（默认 **manual**） |
| Agent | `/setup-zh` `/apply-zh` `/outcome` `/da-zhaohu` |

---

## 承诺 / 不承诺

**承诺**：闭环可跑 · 默认不海投 · 数据本地 · 匹配可解释（非录用预测）

**不承诺**：保证 offer · 默认全自动 · 默认 embedding · 云端同步

---

## 反馈

- [🙋 我在用](https://github.com/LuckTerence/cn-job-assistant/issues/new?template=using.yml)
- [💢 痛点](https://github.com/LuckTerence/cn-job-assistant/issues/new?template=pain.yml)

感谢 fork 与 star。欢迎用真实投递路径打磨下一版。
