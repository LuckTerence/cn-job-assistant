// Compact Chinese résumé — denser second style for cn-job-assistant (MIT with repo).
// Same data API as resume.typ (#resume name/meta/sections) so export_resume_pdf can swap templates.

#let resume(
  name: "",
  meta: "",
  sections: (),
) = {
  set page(paper: "a4", margin: (x: 1.15cm, y: 1.0cm))
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
    size: 9.8pt,
    lang: "zh",
  )
  set par(leading: 0.48em, justify: false)

  // Header bar
  block(
    width: 100%,
    fill: rgb("#0f766e"),
    inset: (x: 10pt, y: 9pt),
    radius: 3pt,
    {
      text(size: 16pt, weight: "bold", fill: white, name)
      if meta != "" {
        v(0.2em)
        text(size: 8.8pt, fill: rgb("#ccfbf1"), meta)
      }
    },
  )
  v(0.45em)

  for sec in sections {
    let title = sec.at("title", default: "")
    let blocks = sec.at("blocks", default: ())
    if title != "" {
      // Left accent section title
      grid(
        columns: (3.2pt, 1fr),
        column-gutter: 6pt,
        rect(width: 100%, height: 11pt, fill: rgb("#0d9488"), radius: 1pt),
        text(size: 10.5pt, weight: "bold", fill: rgb("#134e4a"), title),
      )
      v(0.18em)
    }
    for b in blocks {
      let head = b.at("head", default: "")
      let items = b.at("items", default: ())
      let paras = b.at("paras", default: ())
      if head != "" {
        text(size: 9.8pt, weight: "bold", fill: rgb("#0f172a"), head)
        v(0.08em)
      }
      for p in paras {
        if p != "" {
          text(size: 9.4pt, fill: rgb("#1e293b"), p)
          v(0.12em)
        }
      }
      if items.len() > 0 {
        set list(indent: 0.7em, body-indent: 0.25em, marker: text(fill: rgb("#0d9488"), "▸"))
        for it in items {
          list.item(text(size: 9.4pt, it))
        }
        v(0.15em)
      } else {
        v(0.08em)
      }
    }
    v(0.28em)
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
