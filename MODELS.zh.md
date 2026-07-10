# 国产大模型接入说明

本仓库是**提示词 / 技能框架**，自身不调用任何模型 API。它依赖运行它的 AI 编码 Agent
（如 Claude Code、OpenCode、Aider、Codex CLI、Cursor、各类自托管 Agent）来理解
`.claude/` 与 `.agents/skills/` 中的指令。因此"替换模型"的本质是：**把底层 Agent 切换到
国产大模型**，而非改动本仓库代码。

## 为什么改造成本极低

原版已采用"技能 + 命令 + 占位符配置"的模型无关设计（`.claude/` 给 Claude Code，
`.agents/skills/` 给通用 Agent 框架）。本分支延续该设计，并补充国内平台与中文流程。
**所有改造都不涉及模型 API 调用**，故可直接跑在任何支持本仓库结构的 Agent 上。

## 主流国产模型（均提供 OpenAI 兼容 API）

| 厂商 | 模型示例 | 接入方式 |
|------|----------|----------|
| DeepSeek | DeepSeek-V3 / R1 | `base_url=https://api.deepseek.com/v1`，OpenAI 兼容 |
| 智谱 GLM | GLM-4 / GLM-5 | `base_url=https://open.bigmodel.cn/api/paas/v4`，OpenAI 兼容 |
| 通义千问 | Qwen-Max / Plus | `base_url=https://dashscope.aliyuncs.com/compatible-mode/v1`，OpenAI 兼容 |
| 豆包 | Doubao | 火山引擎方舟平台，OpenAI 兼容 |
| Kimi | Moonshot | `base_url=https://api.moonshot.cn/v1`，OpenAI 兼容 |

> 上述信息为各厂商公开 API 文档所示"OpenAI 兼容"特性的概括（力达云《国产大模型 API 全景》
> 2026.06 亦有同类总结）。具体 `base_url`、模型名与密钥管理以各厂商**最新官方文档**为准。

## 三种落地方式

### 方式 A：用支持自定义模型的 Agent（推荐）
选用允许配置 `base_url` 与 `model` 的编码 Agent（如 OpenCode、Aider、自托管 Claude Code 替代），
将其指向 DeepSeek / 智谱 GLM 的 OpenAI 兼容端点，然后在本仓库目录中正常触发
`/setup`、`/打招呼`、`/apply` 等命令即可。

### 方式 B：Claude Code + 国产模型代理
若坚持使用 Claude Code 的指令体系，可通过兼容层将其底层请求转发至国产模型端点
（社区已有多种 OpenAI 兼容代理方案）。本仓库无需改动。

### 方式 C：纯提示词搬运（最轻量）
直接将 `.claude/skills/job-application-assistant/` 下的参考文件与 `.claude/commands/`
下的命令内容，复制到任意支持自定义指令的国产模型对话产品中（如支持"项目指令/技能"的
Agent 平台），即可获得相同工作流。

## 注意事项

- **中文输出质量**：简历与话术对语言流畅度要求高，建议选用中文能力强的模型
  （GLM / Qwen / DeepSeek 均表现良好）。
- **长上下文**：`/apply` 的完整工作流会携带多份参考文件，确保所选模型上下文窗口充足。
- **敏感信息**：简历含个人信息，优先选用**支持私有部署**的模型/代理，避免敏感数据出域
  （呼应 PIPL 合规要求，见 `README.zh.md`）。
- **成本**：国内模型 API 普遍按量计费且价格较低，适合高频改简历/话术的场景。
