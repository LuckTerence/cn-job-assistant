# AI求职助理 — Red Skill 上架

## 上传包（只传这个）

```bash
bash scripts/package_for_redskill.sh
```

文件：

```text
dist/AI求职助理.zip
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
帮你在本地做求职材料：按岗位描述定制中文简历与 Boss 话术，导出可投 PDF，看匹配度，记录投了哪些公司。默认你自己点发送；需要时再开半自动复制话术或全自动（风险自担）。适合用 Agent / 命令行的求职者。
```

### 硬校验

- zip **根目录只有一层**：`AI求职助理/`
- 根下必须有 `SKILL.md`
- `SKILL.md` frontmatter **只有** `name`、`description` 两键
- `name: AI求职助理` 与表单名称一致
- `description:` 与表单简介 **逐字一致**（含标点）

## 来源

转载/来源可填：https://github.com/LuckTerence/cn-job-assistant
