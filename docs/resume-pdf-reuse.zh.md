# 简历 PDF：开源对标与复用方案（10 项目）

> 调研日期：2026-07-10  
> 目的：中文简历**必须能投 PDF**，优先复用成熟项目，不自研排版引擎。  
> 现状：仓库内 `tools/export_resume_pdf.py` 是过渡方案（自写 MD→HTML + Chrome 打印）。

---

## 一、对标 10 个项目

| # | 项目 | 形态 | 协议（以仓库为准） | 和我们的关系 | 复用方式 |
|---|------|------|-------------------|--------------|----------|
| 1 | [dyweb/awesome-resume-for-chinese](https://github.com/dyweb/awesome-resume-for-chinese) ~8k★ | 中文简历模板索引（LaTeX/HTML/Typst…） | 合集 | **样式与选型地图** | 不装代码；从中挑 1 套作默认版式 |
| 2 | [OrangeX4/Chinese-Resume-in-Typst](https://github.com/OrangeX4/Chinese-Resume-in-Typst) ~900★ | **中文** Typst 简历，可照片 | 见仓库 | **中文一页 PDF 观感标杆** | 作默认 Typst 模板源；Agent 填内容 → `typst compile` |
| 3 | [rendercv/rendercv](https://github.com/rendercv/rendercv) ~17k★ | YAML → Typst → PDF，CLI/PyPI | 见仓库 | 排版工业级；偏英文学术/工程师 | **可选后端**；中文体验需验证字体与模板 |
| 4 | [AmruthPillai/Reactive-Resume](https://github.com/AmruthPillai/Reactive-Resume) | 自托管简历构建器，PDF/JSON/DOCX | MIT | 已在 catalog | **重 UI 可选**；不适合 Agent 默认一条命令 |
| 5 | [BingyanStudio/LapisCV](https://github.com/BingyanStudio/LapisCV) | Markdown + VSCode/Typora 导出 PDF | 见仓库 | 中文 Markdown 工作流成熟 | **模板 + CSS 观感**；导出靠编辑器插件，CLI 弱 |
| 6 | [mszep/pandoc_resume](https://github.com/mszep/pandoc_resume) | Pandoc + 样式 → PDF/HTML | 见仓库 | 经典 MD→PDF 流水线 | 有 pandoc 时作后端；中文要 xelatex/字体 |
| 7 | [wushanyun64/SmartResume](https://github.com/wushanyun64/SmartResume) | MD + Pandoc + LaTeX 模板 | 见仓库 | 同上，封装更产品化 | 可选 pandoc 路径 |
| 8 | [posquit0/Awesome-CV](https://github.com/posquit0/Awesome-CV) | LaTeX 简历模板（海外标杆） | LPPL | 上游英文 CV 同赛道 | **不要当中文默认**；版式可借鉴；编译重 |
| 9 | [NorthSecond/Auto_Typst_Resume_Template](https://github.com/NorthSecond/Auto_Typst_Resume_Template) | **中英双语** Typst + Actions 出 PDF | 见仓库 | 中文+外企双语 | 双语岗模板；GitHub Actions 可抄 |
| 10 | [srbhr/Resume-Matcher](https://github.com/srbhr/Resume-Matcher) ~27k★ | 匹配 + 本地 PDF 导出 | Apache-2.0 | 已 catalog | **不做版式主引擎**；匹配与导出一体时可选整机 |

### 补充（未进前 10，可参考）

| 项目 | 说明 |
|------|------|
| [matchy233/typst-chi-cv-template](https://github.com/matchy233/typst-chi-cv-template) | 中文 Typst，chicv 系 |
| [nietaki/markdown-resume](https://github.com/nietaki/markdown-resume) | 纯 MD→好看 PDF |
| [Chandler-Song/cvbuilder](https://github.com/Chandler-Song/cvbuilder) / cvbuilder-cli | 中文向 MD→PDF CLI（需核协议与维护状态） |
| [mdxport-cli](https://github.com/cosformula/mdxport-cli) | MD→Typst→PDF 单二进制 |

---

## 二、业界怎么做（别重复造）

| 路径 | 谁在用 | 优点 | 缺点 | 我们是否自研 |
|------|--------|------|------|--------------|
| **Typst 模板** | Chinese-Resume-in-Typst、RenderCV v2、双语模板 | 中文友好、快、PDF 好看 | 要装 `typst`；内容结构非纯自由 MD | **版式用模板，不自研引擎** |
| **Pandoc + LaTeX/HTML** | pandoc_resume、SmartResume | 生态老、可 docx | 中文 LaTeX 重；依赖多 | 有 pandoc 作可选后端 |
| **HTML/CSS + 无头浏览器** | LapisCV 导出思路、MarkdownResume 类、本仓库过渡方案 | 依赖 Chrome 即可 | 版式要自己维护 CSS | **仅作无 Typst 时的回退** |
| **自托管 Web 构建器** | Reactive-Resume | 模板多、所见即所得 | 重，Agent 不友好 | catalog 可选 |
| **从零 PDF 库画字** | — | — | 字体/分页/中文坑多 | **禁止** |

结论：  
**内容继续用我们的 MD（Agent 好改）→ 导出优先接到成熟排版（Typst 中文模板 / Pandoc），Chrome HTML 只做 fallback。**

---

## 三、推荐复用架构（改产品默认）

```text
/apply-zh
  → documents/zh/resume_公司.md          # 内容源（保留）
  → tools/export_resume_pdf.py
       ├─ 优先: Typst 中文模板（复用 OrangeX4 / awesome 列表）
       ├─ 可选: pandoc（若本机有）
       └─ 回退: 现有 HTML + Chrome 打印（已实现）
  → documents/zh/resume_公司.pdf         # 唯一默认投递物
```

### 该复用什么 / 不该写什么

| 做 | 不做 |
|----|------|
| 适配层：MD/结构化字段 → 填入开源模板 | 自研完整排版引擎、自绘 PDF 几何 |
| 检测 `typst` / `pandoc` / Chrome 并选后端 | 强迫用户装 Docker 简历站 |
| 在 catalog 写清各模板许可证与安装 | 复制未声明许可的源码进主仓 |
| 样例 PDF 用开源模板渲一份「好看标杆」 | 把 Reactive-Resume 当默认（太重） |

### 落地优先级

1. **P0**：`export_resume_pdf.py` 增加 `backend=typst|chrome|pandoc`，默认自动探测；文档指向 Chinese-Resume-in-Typst + awesome-resume-for-chinese。  
2. **P1**：提供「Agent 可填」的最小 Typst/YAML 片段（或 MD→Typst 字段映射），一键 `typst compile`。  
3. **P2**：外企双语用 NorthSecond 模板；重 UI 仍指向 Reactive-Resume catalog。

---

## 四、和当前自研代码的关系

| 文件 | 定位调整 |
|------|----------|
| `tools/export_resume_pdf.py` | **适配器/编排器**，不是「我们发明的简历排版」 |
| 自写 CSS HTML | 仅 **fallback**，标注「无 Typst 时使用」 |
| `templates/zh/*.md` | **内容结构规范**（给 Agent），版式交给上游模板 |

---

## 五、许可与合规注意

- 采用模板前核 `LICENSE`；LaTeX Awesome-CV 等为 LPPL，分发模板文件时遵守其条款。  
- Typst/RenderCV 以各仓库 LICENSE 为准。  
- 简历含个人信息：本地编译，PDF 进 `documents/zh/`（gitignore）。

---

## 六、一句话

> 中文 PDF **好看、能投** = 复用 **Typst 中文简历模板**（或 Pandoc 流水线）；  
> 我们只做 **Agent 写内容 + 一条命令导出**，不重复造排版轮子。
