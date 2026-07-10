# 在 AI Agent 里安装 / 使用本仓库

> 本项目是 **Agent 工作流框架**（skills + commands + 本地 Python 工具），不是在线 SaaS。  
> 把仓库放到 Agent 能读到的目录，即可调用 `/setup-zh`、`/apply-zh` 等命令。

## 通用步骤（所有 Agent）

```bash
git clone https://github.com/LuckTerence/cn-job-assistant.git
cd cn-job-assistant
bash scripts/demo.sh          # 验证本地工具（不需 API）
```

然后用你的 Agent **打开该目录作为工作区**。

| 能力 | 依赖 |
|------|------|
| demo / match / tracker | 仅 Python 3.10+ |
| `/setup-zh` `/apply-zh` | Agent + 任意大模型 |
| Boss 搜岗 | 可选 `python tools/install_domestic_search.py install-boss` |

国产模型（DeepSeek / 智谱 / 通义等）接法见 [MODELS.zh.md](./MODELS.zh.md)。

---

## Claude Code

```bash
cd cn-job-assistant
claude
# 会话内：
/setup-zh
/apply-zh
```

- 命令定义在 `.claude/commands/`
- 技能在 `.claude/skills/` 与 `.agents/skills/`
- 若使用项目 `settings`，勿随意放宽 `permissions`（见 `tools/security_guards.py`）

---

## Cursor

1. `File → Open Folder` 打开本仓库  
2. 在 Chat / Agent 中说明：「按 README 与 `.claude/commands/apply-zh.md` 执行国内求职流程」  
3. 需要跑命令时允许执行：

```bash
python tools/match_resume.py report --zh-only --resume … --jd …
python tools/tracker.py today
```

Cursor 不自动注册 `/apply-zh` 斜杠时：在对话里引用 `.claude/commands/apply-zh.md` 并粘贴 JD。

---

## 其他 OpenAI 兼容 Agent（Aider / Continue / 自建）

1. 工作目录设为仓库根  
2. 系统提示加入：「遵守 CLAUDE.zh.md 与 .claude/commands 中的国内流程；不自动投递」  
3. 工具调用允许 `python tools/*.py`  

---

## 不要做什么

- 不要把「catalog 可选集成」当成开箱技能宣传  
- 不要默认开启自动投递  
- 不要把含真实简历的 `documents/zh/**`、`job_search_tracker.csv` commit 上公网  

---

## 验证清单

- [ ] `bash scripts/demo.sh` 退出码 0  
- [ ] 能打开 `examples/demo/output/job_search_tracker.html`  
- [ ] Agent 能读到 `CLAUDE.zh.md` 与 `/apply-zh` 步骤  
- [ ] `python tools/tracker.py today` 有输出  
