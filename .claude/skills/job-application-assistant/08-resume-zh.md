# 中文简历模板与定制指南（适配国内求职）

<!-- SETUP: 个人画像源 = `CLAUDE.zh.md`（由 /setup-zh 填充）；本文件给出结构与分赛道规则。生成中文简历时读取 `CLAUDE.zh.md` 取候选信息 -->

## 与西方 CV 的关键差异

| 维度 | 西方 CV（moderncv） | 国内简历 |
|------|---------------------|----------|
| 篇幅 | 2 页 | **1 页**（校招可放宽至 1–2 页，社招严格 1 页） |
| 格式 | LaTeX PDF | **Word / WPS（.docx）为主**，PDF 亦可 |
| 照片 | 一般不放 | 互联网/外企多不放；**国企/体制内常放证件照** |
| 板块顺序 | 技能前置 | 教育（应届）或 工作经历（社招）前置 |
| 薪资 | 不写 | 一般不写（面试谈）；猎聘年薪岗可写期望 |
| 语言 | 英语（或当地官方语言） | 中文（外企可中英双语） |

> **交付格式（产品默认）**：Markdown 只作**源文件**；**投递用 PDF**。  
> 一键导出：运行 tools 目录下的 export_resume_pdf.py（参数 --input 指向 resume 的 md）。  
> 依赖本机 Chrome / Chromium / Edge 无头打印为 A4 PDF；没有浏览器时会写出 HTML，再用浏览器「打印 → 存 PDF」。  
> 若某平台强制 Word，再另存 docx；默认仍以 **PDF** 为准。

## 分赛道模板

国内不同雇主审美差异大，按赛道采用不同模板（见 `templates/zh/`）：

| 赛道 | 模板文件 | 适用 | 关键差异 |
|------|----------|------|----------|
| 互联网 | `templates/zh/resume_internet.md` | 大厂/中厂技术产品运营 | 重项目与数据、不放照片、强调技术栈与业务结果 |
| 国企央企 | `templates/zh/resume_soe.md` | 国资/央企/事业单位 | **放证件照**、政治面貌、党员优先标注、稳重排版 |
| 外企 | `templates/zh/resume_foreign.md` | 欧美/日韩企业在华 | 中英双语、国际化经历、社团/志愿者 |
| 体制内 | `templates/zh/resume_civil.md` | 公务员/选调/事业编 | 严格按招考简章板块、无花哨设计、突出学历与奖项 |
| 应届校招 | `templates/zh/resume_freshgrad.md` | 毕业生 | 教育前置、实习与项目并重、GPA/竞赛/证书 |

## 一页纸硬约束（社招）

中文简历**必须控制在一页 A4**。各板块预算参考：

| 板块 | 上限 |
|------|------|
| 求职意向 / 个人总结 | 2–3 行 |
| 教育 | 1–3 条（倒序） |
| 工作经历 | 近期岗 4–5 条要点，往前递减 |
| 项目经历 | 2–3 个，每条 2–3 行 |
| 技能 | 6–10 项，分类 |
| 证书/荣誉 | 各 2–3 条 |

## 撰写规则（与西方一致的部分）

- **不造假**：所有经历、技能、数据必须真实，缺口诚实表述，不堆砌关键词。
- **量化结果**：用"将 X 提升 Y%"而非"负责 X"；国内 HR 极看重可量化业绩。
- **关键词对齐 JD**：从职位描述抽取硬性要求，逐条在简历中体现（真实具备的前提下）。
- **相关性裁剪**：与目标岗位无关的内容果断删减，不为"完整"牺牲聚焦。

## 投递与解析注意

- **默认投 PDF**（本仓库 `export_resume_pdf.py` 生成的是可选中文本的 PDF，不是扫描件图片）。
- 避免复杂表格、文本框、艺术字。
- 邮箱与电话写在正文里，不要做成图标。
- 单栏、一页 A4（社招）；版式由导出 CSS 控制，勿在 md 里堆 HTML。

## 输出文件

- 源文件：`documents/zh/resume_<company>.md`
- **投递文件：`documents/zh/resume_<company>.pdf`**（`export_resume_pdf.py` 必出）
- 定制时以 `templates/zh/resume_<track>.md` 为结构基线。

## 与原有 LaTeX 流程的关系

原 `05-cv-templates.md`（moderncv/2 页/PDF）保留用于**海外或英文岗**；本文件用于**国内中文岗**。
两者并列，由 `apply` / `打招呼` 命令按岗位语言与市场自动选择。

## 可选：样式模板源（不重复造轮子）

若需更丰富的排版样式，直接复用成熟开源模板库，而非从零手写 LaTeX / Typst：

- **[dyweb/awesome-resume-for-chinese](https://github.com/dyweb/awesome-resume-for-chinese)** — 中文简历模板合集
  （LaTeX / HTML / **Typst** 多套，含应届、双栏等），本分支 `templates/zh/` 的样式可向其借鉴。
- 需要 PDF 排版时，可用任意编辑器导出，或可选自托管 Reactive-Resume（`integrations/catalog/resume-build/`）；`templates/zh` 与 awesome-resume 类库仅作样式参考。

