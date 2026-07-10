---
name: interview-mock
version: 1.0.0
description: >
  模拟面试与表现评估。本技能复用开源 AI 面试平台 AuraInterviewer
  （MIT，Spring Boot + Vue3 微服务，集成 GPT/DeepSeek/SiliconFlow 多模型，多维评分 + 结构化报告），
  而非自行实现面试模拟引擎。触发词：模拟面试、练面试、面试练习、面试反馈、mock interview、面评。
context: fork
allowed-tools: Read, Glob, Grep, WebFetch, WebSearch, AskUserQuestion
---

# 模拟面试技能（复用 AuraInterviewer）

> **不要重复造轮子**：AI 模拟面试（智能提问、语义分析、多维评分、结构化反馈报告）已被成熟开源项目
> [GodLeaveMe/AuraInterviewer](https://github.com/GodLeaveMe/AuraInterviewer)（**MIT**）完整实现。
> 本技能直接复用它做"练习 + 评估"，不再手写面试模拟逻辑；本仓库 `07-interview-prep.md` 仅保留为
> **题型与答题方法论**指引（STAR、群面、行测、国企党政面等国内题型）。

## 复用关系

| 能力 | 由谁实现 | 说明 |
|------|----------|------|
| 智能提问 | **AuraInterviewer** AI 服务（GPT/DeepSeek/SiliconFlow） | 按岗位/模板生成贴合问题 |
| 实时对话 | **AuraInterviewer** 面试服务 | 文本多轮问答 |
| 多维评分 | **AuraInterviewer** | 技术准确性 / 表达清晰度 / 情感状态 等维度 |
| 结构化报告 | **AuraInterviewer** | 分数 + 反馈 + 改进建议 |
| 模板管理 | **AuraInterviewer** | 公共/自定义面试模板，按技术栈/难度分类 |
| 国内题型方法 | **本仓库** `07-interview-prep.md` | STAR、群面/无领导、行测、国企党政面等 |

> 多模型接入：AuraInterviewer 支持 OpenAI / DeepSeek / SiliconFlow 等 OpenAI 兼容接口，
> 可接国产模型中转（见本仓库 `MODELS.zh.md`）。

## 技术要点（来自其 README，便于对接）

- **架构**：Spring Boot 3.2 + Spring Cloud 微服务（Eureka / Gateway / user / interview / ai 五服务）；
  前端 Vue 3 + TypeScript + Element Plus；MySQL 8 + Redis。
- **部署**：`docker-compose up -d`（含数据库脚本 `AuraInterviewer.sql`）；需 Java 18+、Node 18+。
- **评估维度**：技术准确性、表达清晰度、情感状态；输出含分数、反馈与改进建议的详细报告。
- **协议**：MIT。

## 工作流（本技能如何编排）

1. 用户选定目标岗位，本仓库 `07-interview-prep.md` 提供**题型与方法论**（如群面、行测、国企党政面）。
2. 在自托管的 **AuraInterviewer** 中创建面试会话（选模板 + 模型），用简历与 JD 作为上下文。
3. 进行多轮实时对话，结束后获取**结构化评估报告**（分数 + 反馈 + 改进建议）。
4. 将报告中的薄弱点回到 `07-interview-prep.md` 做针对性补强；岗位匹配度评估回到 `resume-match` / `04-job-evaluation.md`。

## 安装与运行（摘要，以 AuraInterviewer 仓库为准）

```bash
git clone https://github.com/GodLeaveMe/AuraInterviewer.git
cd AuraInterviewer
docker-compose up -d          # 启动后访问前端 http://localhost:3000
# 配置 AI 模型 API（OpenAI / DeepSeek / SiliconFlow 或国产模型中转）后创建面试
```

## 合规与边界

- 面试报告含个人表现数据，优先自托管部署，谨慎分享，遵守 PIPL。
- AI 评分仅为练习参考，不替代真实面试判断；缺口诚实补强，不虚构经历。
- 模型 API Key 属敏感凭证，优先本地/私有部署。

## 与其他技能的配合

- 题型方法论 → `07-interview-prep.md`
- 岗位匹配度 → `resume-match`（Resume Matcher）/ `04-job-evaluation.md`
- 简历 → `resume-build`（Reactive-Resume）
- 话术 → `09-da-zhaohu-zh.md` + `/打招呼`
- 语音实时面试（可选维度）→ **[ZHAB00/ai_interview](https://github.com/ZHAB00/ai_interview)**（MIT；DeepSeek + 阿里云 Qwen ASR/TTS，四阶段 + 五维评分 + 雷达图报告，需另行自托管）
- 面试题库 / 知识源（可选）→ **[yangshun/tech-interview-handbook](https://github.com/yangshun/tech-interview-handbook)**（MIT；算法/行为/系统/简历/薪资全流程手册，作题库与方法论补充）
- 系统设计知识源（可选）→ **[donnemartin/system-design-primer](https://github.com/donnemartin/system-design-primer)**（356k★，系统设计面试圣经：大规模系统设计 / 权衡 / 计算估算，作系统设计题库与方法论补充；仓库**未声明许可证**，仅作知识引用不复制代码）
- 系统设计图解（可选）→ **[ByteByteGoHq/system-design-101](https://github.com/ByteByteGoHq/system-design-101)**（85k★，可视化讲解复杂系统，作系统设计图形化补充；仓库**未声明许可证**，仅作知识引用）
