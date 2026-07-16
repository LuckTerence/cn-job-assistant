---
name: boss-agent-cli
description: >
  可选：对接 MIT 开源 boss-agent-cli（面向 AI Agent 的 Boss 直聘 assisted CLI，JSON 信封）。
  本仓库不内嵌其代码；用 tools/normalize_job_export.py 把对方 stdout 转为 import-jobs。
optional: true
tier: catalog
setup_cost: medium
requires: uv or pip; patchright/chromium for login (upstream); separate install
os: any
default_alternative: '粘贴 JD + tools/split_jds.py · 或 install_domestic_search + 旧 boss-cli'
upstream: https://github.com/can4hou6joeng4/boss-agent-cli
license_note: MIT — 可合法对接；勿把 Research Mode 设为本仓默认
---

> ⚠️ **已移出核心 skill 面**：本文件位于 `integrations/catalog/`，**不是**开箱必装。  
> 国内默认闭环仍用 `tools/tracker.py` · `flow.py` · `/apply-zh`。

# catalog · boss-agent-cli（可选）

| 字段 | 值 |
|------|-----|
| 上游 | https://github.com/can4hou6joeng4/boss-agent-cli |
| 许可证 | **MIT** |
| 本仓角色 | **发现岗位**的外部 CLI；投递仍 manual/semi |
| 适配器 | `python tools/normalize_job_export.py -i raw.json -o jobs.json` |

## 推荐串联

```bash
# 1) 在 boss-agent-cli 环境搜岗（以对方 README 为准），保存 JSON
# 2) 本仓归一化 + 短名单
python tools/normalize_job_export.py -i raw.json -o jobs.json --default-channel Boss直聘
python tools/flow.py shortlist --jobs jobs.json --track internet
# 或: python tools/flow.py shortlist --raw raw.json --track internet
```

## 合规

- 对方默认 **Assisted Mode**（与本仓「默认不海投」一致）。  
- 打招呼/投递回官网或本仓 `apply_assist semi`。  
- 不要把 Research Mode 设成产品默认。

## 为何不 vendor

- 上游浏览器依赖重、迭代快；本仓保持 **薄适配 + 短名单闭环**。
