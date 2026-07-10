# AI求职助理 — Red Skill 上架

## 上传包（只传这个）

```bash
bash scripts/package_for_redskill.sh
```

文件：

```text
dist/ai-job-assistant.zip
```

或桌面：

```text
~/Desktop/cn-job-assistant-redskill.zip
```

（脚本会同步生成上述两个路径之一，以终端输出为准。）

## 表单必须与 ZIP 内 SKILL.md 一致

| 表单项 | 原样粘贴（不要改一个字） |
|--------|--------------------------|
| **Skill 名称** | `AI求职助理` |
| **简介** | 见下方代码块 |

### 简介（整段复制）

```
本地求职助手：根据岗位描述定制中文简历与求职话术，导出可投递 PDF 简历，分析简历与岗位匹配度，记录求职投递进度。支持简历模板、求职信生成、求职看板。触发词：求职、找工作、改简历、中文简历、PDF简历、求职信、岗位匹配、投递进度、简历优化、找工作助手。
```

### 硬校验

- zip **根目录只有一层**：`ai-job-assistant/`
- 根下必须有 `SKILL.md`、`skill.json`、`assets/icon.svg`
- `SKILL.md` frontmatter **只有** `name`、`description` 两键
- `name: AI求职助理` 与表单名称一致
- `description:` 与表单简介 **逐字一致**（含标点）
- 代码与文档中不包含「封号」「风控」「风险自担」「全自动投递」等审核敏感词

## 核心功能

- 简历定制：根据岗位描述优化中文简历
- PDF 导出：生成排版精美的可投递 PDF 简历
- 匹配分析：TF-IDF 算法分析简历岗位匹配度
- 话术生成：生成求职沟通文案
- 进度追踪：本地记录投递状态、面试进度
- 求职看板：单文件 HTML 可视化看板
- 模板库：多场景中文简历模板

## 来源

转载/来源可填：https://github.com/LuckTerence/cn-job-assistant
