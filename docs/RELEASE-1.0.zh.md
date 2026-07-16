# 1.0 发版说明 · CN Job Assistant

**版本**：1.0.0  
**日期**：2026-07-17  
**一句话**：国内 Agent 求职**最小可靠闭环**已齐备——本地、默认可手动、可量化、可追踪。

---

## 1.0 承诺什么

| 承诺 | 说明 |
|------|------|
| **闭环可跑** | 搜岗/粘贴 JD → 定制材料 → 匹配摘要 → 手动/半自动投 → tracker / outcome |
| **离线可验** | `bash scripts/smoke_cn.sh` 或 `make smoke` 不依赖 Boss 登录 |
| **默认不海投** | manual 默认；auto 三重门禁 |
| **数据本地** | 简历与 CSV gitignore；PIPL 友好 |
| **诚实边界** | 匹配分 ≠ 录用预测；同义词/薪资均为本地规则，无爬库 |

## 1.0 不承诺什么

- 保证拿到 offer  
- 默认全自动打招呼/海投  
- 开箱语义 embedding（见 `integrations/catalog/`）  
- 云端多端同步 SaaS  

---

## 外人 15 分钟路径

```bash
git clone https://github.com/LuckTerence/cn-job-assistant.git
cd cn-job-assistant
bash scripts/smoke_cn.sh    # 或 make smoke
bash scripts/demo.sh
# Agent 内：/setup-zh → /apply-zh <JD>
# 日常：python tools/flow.py shortlist --jobs …  或  day-plan / rank / funnel
```

反馈：

- [🙋 我在用](https://github.com/LuckTerence/cn-job-assistant/issues/new?template=using.yml)  
- [💢 痛点](https://github.com/LuckTerence/cn-job-assistant/issues/new?template=pain.yml)  

---

## 能力清单（1.0 面）

| 能力 | 入口 |
|------|------|
| 演示 | `scripts/demo.sh` |
| 冒烟 | `scripts/smoke_cn.sh` |
| 短名单编排 | `tools/flow.py shortlist` |
| 今日计划 / 批打分 | `tracker day-plan` / `rank` |
| 漏斗 | `tracker funnel` |
| 粘贴多 JD | `tools/split_jds.py` |
| 匹配 + 真缺口 + 薪资 | `match_resume report` / `salary` |
| 同义词 / 赛道 / IDF | `config/synonyms*.json` · `idf.default.json` |
| 投递三档 | `apply_assist.py` |
| Agent 命令 | `/setup-zh` `/apply-zh` `/outcome` `/da-zhaohu` |

版本明细见 [CHANGELOG.md](../CHANGELOG.md)（0.10～0.13 → 1.0）。

---

## 1.0 质量门禁（发布前）

- [x] `bash scripts/smoke_cn.sh` 绿  
- [x] CI domestic-loop 单测 + lint  
- [x] CHANGELOG / skill.json 版本一致  
- [ ] （可选）打 git tag `v1.0.0` 并 push  
- [ ] （持续）外部用户 ≥5 人完成 ≥3 岗闭环 —— **社区验证，不挡能力发版**  

> **说明**：1.0 标记的是「产品能力面达到可对外宣称的可靠最小集」。  
> 用户规模与社会证明仍在验证期，欢迎开「我在用」Issue。

---

## 1.x 可能方向（信号驱动）

| 信号 | 方向 |
|------|------|
| 匹配仍不准 ×N | catalog 语义匹配可选层 |
| 不要终端 ×N | 加强 HTML / 极轻本地页 |
| Boss 导出列老变 | 专用适配器加厚 |
| 要多设备 | 另议；默认仍本地优先 |
