# 在 Agent 里怎么用

这不是网页产品。把仓库 clone 下来，用 Claude Code / Cursor 等打开这个文件夹即可。

```bash
git clone https://github.com/LuckTerence/cn-job-assistant.git
cd cn-job-assistant
make check             # 1.0：单测 + 离线产品冒烟（推荐）
# 或分步: bash scripts/demo.sh
```

完整 15 分钟路径：[QUICKSTART.zh.md](./QUICKSTART.zh.md)。  
没有 `/setup-zh` 时复制：[AGENT_PROMPT.zh.md](./AGENT_PROMPT.zh.md)。

然后在 Agent 里跑 `/setup-zh`、`/apply-zh`。  
短名单：`python tools/flow.py shortlist --jobs …` · 日常：`day-plan` / `funnel`。  
DeepSeek / 智谱等接法见 [MODELS.zh.md](./MODELS.zh.md)。  
发版边界见 [RELEASE-1.0.zh.md](./RELEASE-1.0.zh.md)。

## Claude Code

```bash
cd cn-job-assistant
claude
```

命令在 `.claude/commands/`，技能在 `.claude/skills/` 和 `.agents/skills/`。

## Cursor

打开本仓库文件夹，聊天时可以说按 `apply-zh` 那套步骤来，或直接引用 `.claude/commands/apply-zh.md`，把岗位全文贴进去。

需要跑本地命令时：

```bash
python tools/match_resume.py report --zh-only --resume … --jd …
python tools/tracker.py today
```

## 注意

- 重型可选工具在 `integrations/catalog/`，默认装完不能直接当核心功能用
- 别把带手机号的简历、投递表 commit 上去
