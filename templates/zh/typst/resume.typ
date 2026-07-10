// Chinese résumé template for cn-job-assistant.
// Original layout for this project (MIT with the repo).
// Design goals: clean A4 one-pager, CJK-first fonts, ATS-friendly single column.
// See docs/resume-pdf-reuse.zh.md for upstream alternatives (OrangeX4, RenderCV, …).

#let resume(
  name: "",
  meta: "",
  sections: (),
) = {
  set page(paper: "a4", margin: (x: 1.4cm, y: 1.2cm))
  set text(
    font: (
      "PingFang SC",
      "Hiragino Sans GB",
      "Heiti SC",
      "Microsoft YaHei",
      "Noto Sans CJK SC",
      "Source Han Sans SC",
      "Songti SC",
      "STSong",
      "Arial Unicode MS",
      "Arial",
    ),
    size: 10.5pt,
    lang: "zh",
  )
  set par(leading: 0.55em, justify: false)

  // Name
  text(size: 18pt, weight: "bold", fill: rgb("#0f172a"), name)
  v(0.25em)
  if meta != "" {
    text(size: 9.5pt, fill: rgb("#475569"), meta)
    v(0.35em)
  }
  line(length: 100%, stroke: 1.4pt + rgb("#1e3a5f"))
  v(0.55em)

  for sec in sections {
    let title = sec.at("title", default: "")
    let blocks = sec.at("blocks", default: ())
    if title != "" {
      text(size: 11pt, weight: "bold", fill: rgb("#1e3a5f"), title)
      v(0.15em)
      line(length: 100%, stroke: 0.6pt + rgb("#cbd5e1"))
      v(0.3em)
    }
    for b in blocks {
      let head = b.at("head", default: "")
      let items = b.at("items", default: ())
      let paras = b.at("paras", default: ())
      if head != "" {
        text(size: 10.5pt, weight: "bold", head)
        v(0.15em)
      }
      for p in paras {
        if p != "" {
          text(size: 10pt, p)
          v(0.2em)
        }
      }
      if items.len() > 0 {
        set list(indent: 0.9em, body-indent: 0.3em, marker: "•")
        for it in items {
          list.item(text(size: 10pt, it))
        }
        v(0.25em)
      } else {
        v(0.15em)
      }
    }
    v(0.35em)
  }
}

// --- data injected below by export_resume_pdf.py ---
#resume(
  name: "姓名",
  meta: "城市 · 电话 · 邮箱",
  sections: (
    (
      title: "专业技能",
      blocks: (
        (head: "", items: ("示例技能",), paras: ()),
      ),
    ),
  ),
)
