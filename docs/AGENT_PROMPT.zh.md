# Agent 一键提示词（无 slash 时用）

复制整段发给 Claude Code / Cursor / 其他 Agent（工作区为本仓库根目录）。

---

## 初始化画像

```text
请严格按 .claude/commands/setup-zh.md 执行国内求职初始化。
优先 Path B：从我粘贴的简历抽取画像，写入 CLAUDE.zh.md（只填占位符）。
务必确认并写入：期望薪资、目标城市、目标赛道、硬约束。
完成后用 python tools/tracker.py init 初始化追踪表（若尚无 CSV）。
下面是我的简历：

（在此粘贴）
```

---

## 投一个岗位

```text
请严格按 .claude/commands/apply-zh.md 执行。
MARKET=domestic。岗位描述如下（或链接）：

（粘贴 JD）

要求：
1. 先做匹配评估，再生成材料
2. 双格式：md=粘贴稿，必须导出 PDF=上传稿
3. match_resume report 要带 --profile CLAUDE.zh.md，展示「改这 3 条」
4. **强制**跑 quality_gate（SOFT 默认不鼓励投；HARD 诚信必须停下）
5. 摘要区分「同义词已对齐」与「真缺口」；禁止虚构
6. Step 7 用 tracker suggest-add（含 --match-score 等），询问后再写入（禁止静默 applied）
7. 交付后给出 day-plan / funnel / match-outcome / outcome 的下一步
```

---

## 一批岗位短名单

```text
我已把多个 JD 放在 pasted.txt（或 documents/zh/inbox）。
请依次执行并解读结果：
1. python tools/split_jds.py -i pasted.txt -o documents/zh/inbox
2. python tools/flow.py shortlist --jobs documents/zh/inbox/jobs_stub.json --track internet --limit 5
3. python tools/tracker.py funnel
告诉我今天最值得 /apply-zh 的 1～2 个岗位及原因（匹配分、薪资旗标、城市）。
```

---

## 更新结果

```text
请按 .claude/commands/outcome.md 记录结果。
公司：… 岗位：… 发生了：面试邀请 / 拒信 / 不投 …
若不投，必须写 skip_reason（salary_low|location|low_match|unknown_company|other）。
用 tracker update --notes-append 追加笔记。
```
