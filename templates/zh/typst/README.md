# Typst 中文简历导出（复用路径）

本目录提供 **本仓库自有的精简 Typst 模板**（`resume.typ`），由 `tools/export_resume_pdf.py` 填入内容后调用 `typst compile` 生成 PDF。

## 为什么不直接 vendoring OrangeX4？

[OrangeX4/Chinese-Resume-in-Typst](https://github.com/OrangeX4/Chinese-Resume-in-Typst) 观感优秀，但仓库 **未声明 LICENSE**（GitHub API 为 null），不能擅自复制源码进主仓。  
完整选型与其它 9 个项目见 [`docs/resume-pdf-reuse.zh.md`](../../../docs/resume-pdf-reuse.zh.md)。

若你个人获得授权或接受其条款，可自行 clone 后用：

```bash
export CN_JOB_TYPST_TEMPLATE=/path/to/Chinese-Resume-in-Typst
# 后续版本可支持外部模板目录；当前默认使用本目录 resume.typ
```

## 安装 Typst

```bash
# macOS
brew install typst

# 或官方 release：https://github.com/typst/typst/releases
```

## 导出

```bash
python tools/export_resume_pdf.py -i documents/zh/resume_公司.md --backend typst
# 第二套紧凑模板（青绿头栏，更密）
python tools/export_resume_pdf.py -i documents/zh/resume_公司.md --template compact
# 或自动探测（优先 typst）
python tools/export_resume_pdf.py -i documents/zh/resume_公司.md
```

| 模板 | 文件 | 风格 |
|------|------|------|
| `classic`（默认） | `resume.typ` | 深蓝分割线、经典单栏 |
| `compact` | `resume_compact.typ` | 青绿头栏、更小边距与字号 |
