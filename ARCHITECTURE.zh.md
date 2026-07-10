# 架构说明（国内适配 · 核心面 vs 可选面）

> 一句话：**agent 框架**，不是 SaaS。默认可跑路径必须短、本地、可测；重应用进 catalog。

## 分层

```text
┌─────────────────────────────────────────────────────────────┐
│  Prompt 工作流（.claude/commands）                            │
│  /setup-zh  /apply-zh  /da-zhaohu  /outcome  /interview …   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  核心 skill 面（.agents/skills）— allowlist 锁定              │
│  海外 6 CLI │ bosszhipin │ domestic-jobs │ tracker │ match  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  本地工具（tools/，stdlib 优先，CI 覆盖）                      │
│  install_domestic_search.py │ tracker.py │ match_resume.py  │
│  lint_skills / lint_zh_refs / lint_skill_surface            │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  可选集成（integrations/catalog/）— 文档 + 成本卡，不进 agent │
│  interview-mock │ resume-build │ resume-match(UI) │ …       │
└─────────────────────────────────────────────────────────────┘
```

## 核心 `.agents/skills`（10）

| Skill | 可跑交付 |
|-------|----------|
| `jobbank-search` 等 6 个海外 CLI | TypeScript CLI + 单测 |
| `bosszhipin-search` | 安装器 + boss-cli（外部） |
| `domestic-jobs-search` | 安装器 + get_jobs 克隆（外部，禁商用） |
| `application-tracker` | `tools/tracker.py` |
| `resume-match` | `tools/match_resume.py`（非 catalog 重 UI） |

由 `tools/lint_skill_surface.py` 的 `CORE_AGENTS_SKILLS` **硬性 allowlist** 约束：新增目录必须改 lint 并说明理由。

## 可选 catalog（6）

见 [`integrations/catalog/README.md`](./integrations/catalog/README.md)。  
特征：无本仓库可执行封装、或依赖 Docker/JVM/macOS/未声明许可证。  
**默认替代路径写在每条 `default_alternative` 字段。**

同名注意：

| 路径 | 含义 |
|------|------|
| `.agents/skills/resume-match` | 本地轻量 CLI |
| `integrations/catalog/resume-match` | 上游 Resume Matcher 全量 UI |

## 国内默认数据流

```text
岗位描述 ──► documents/zh/jd_*.md
         │
         ▼
     /apply-zh ──► resume_*.md + da-zhaohu|cover_*.md
         │
         ▼
 match_resume.py report ──► match_report_*.json
         │
         ▼
    用户手动投递
         │
         ▼
 tracker.py / /outcome ──► job_search_tracker.csv
```

## 设计原则

1. **能复用不自研**（搜岗用 boss-cli/get_jobs；匹配取 IR 思路不拉百 MB 模型）。  
2. **文档承诺 ≤ 可跑面**（catalog 不得冒充核心 skill）。  
3. **不自动投递**；个人数据 gitignore。  
4. **CI 绿要覆盖国内工具**，不只海外 CLI。

## 相关文件

| 文件 | 作用 |
|------|------|
| `README.zh.md` | 用户向快速开始 |
| `integrations/catalog/README.md` | 可选集成成本表 |
| `tools/lint_skill_surface.py` | 核心与 catalog 边界校验 |
| `tools/lint_zh_refs.py` | 国内路径完整性 |
