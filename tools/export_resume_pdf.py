#!/usr/bin/env python3
"""Export Chinese résumé Markdown to a clean, submittable A4 PDF.

Pipeline: Markdown → print-ready HTML (embedded CSS) → PDF via Chrome/Chromium
headless (preferred) or Microsoft Edge. No heavy Python PDF deps.

Usage:
  python tools/export_resume_pdf.py --input documents/zh/resume_公司.md
  python tools/export_resume_pdf.py --input path.md --output path.pdf
  python tools/export_resume_pdf.py --input path.md --html-only   # debug layout

Exit 0 on success. PDF is the default delivery format for domestic applications.
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Prefer system Chinese UI fonts so PDF is not "tofu" or Latin-only.
CSS = """
@page {
  size: A4;
  margin: 12mm 14mm 12mm 14mm;
}
* { box-sizing: border-box; }
html, body {
  margin: 0;
  padding: 0;
  font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei",
               "Noto Sans CJK SC", "Source Han Sans SC", "WenQuanYi Micro Hei",
               "Segoe UI", sans-serif;
  font-size: 10.5pt;
  line-height: 1.45;
  color: #1a1a1a;
  background: #fff;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.page {
  max-width: 180mm;
  margin: 0 auto;
}
/* Header */
header.identity {
  border-bottom: 2px solid #1e3a5f;
  padding-bottom: 8px;
  margin-bottom: 12px;
}
header.identity h1 {
  margin: 0 0 4px 0;
  font-size: 18pt;
  font-weight: 650;
  letter-spacing: 0.02em;
  color: #0f172a;
}
header.identity .meta {
  margin: 0;
  font-size: 9.5pt;
  color: #475569;
}
/* Sections */
section {
  margin: 0 0 10px 0;
  page-break-inside: avoid;
}
section h2 {
  margin: 0 0 5px 0;
  padding: 0 0 3px 0;
  font-size: 11pt;
  font-weight: 650;
  color: #1e3a5f;
  border-bottom: 1px solid #cbd5e1;
  letter-spacing: 0.04em;
}
section h3 {
  margin: 7px 0 2px 0;
  font-size: 10.5pt;
  font-weight: 600;
  color: #0f172a;
}
p {
  margin: 0 0 4px 0;
}
ul {
  margin: 2px 0 6px 0;
  padding-left: 1.15em;
}
li {
  margin: 0 0 2px 0;
}
strong { font-weight: 600; }
.footer-note {
  margin-top: 10px;
  font-size: 8pt;
  color: #94a3b8;
  text-align: right;
}
@media screen {
  body { background: #e2e8f0; padding: 16px; }
  .page {
    background: #fff;
    padding: 14mm 12mm;
    box-shadow: 0 1px 4px rgba(0,0,0,.12);
  }
}
"""


def find_chrome() -> str | None:
    env = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which(
        "chromium-browser"
    )
    if env:
        return env
    candidates = [
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
        Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
        Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    # Windows
    for c in (
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    ):
        if c.is_file():
            return str(c)
    return None


def inline_format(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


def md_to_resume_html(md: str, title: str = "简历") -> str:
    """Convert simple résumé Markdown into semantic HTML."""
    lines = md.replace("\r\n", "\n").split("\n")
    body: list[str] = []
    i = 0
    in_ul = False
    header_done = False
    meta_lines: list[str] = []

    def close_ul() -> None:
        nonlocal in_ul
        if in_ul:
            body.append("</ul>")
            in_ul = False

    def flush_meta() -> None:
        nonlocal meta_lines, header_done
        if header_done or not meta_lines:
            return
        # First line after h1 often contact line
        body.append('<header class="identity">')
        # h1 already written
        meta = " · ".join(m for m in meta_lines if m.strip())
        if meta:
            body.append(f'<p class="meta">{inline_format(meta)}</p>')
        body.append("</header>")
        meta_lines = []
        header_done = True

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()

        # skip pure HTML comments / blockquote tips in templates
        if stripped.startswith("<!--") or stripped.startswith("-->"):
            i += 1
            continue
        if stripped.startswith(">"):
            i += 1
            continue
        if stripped in ("---", "***", "___"):
            close_ul()
            i += 1
            continue
        if not stripped:
            close_ul()
            i += 1
            continue

        # AT1 → name
        m = re.match(r"^#\s+(.+)$", stripped)
        if m:
            close_ul()
            flush_meta()
            name = m.group(1).strip()
            # strip demo markers
            name = re.sub(r"[（(].*演示.*[）)]", "", name).strip()
            body.append(f"<header class=\"identity\"><h1>{inline_format(name)}</h1>")
            # peek following non-heading lines as meta until blank or ##
            j = i + 1
            metas: list[str] = []
            while j < len(lines):
                s = lines[j].strip()
                if not s or s.startswith("#") or s.startswith(">"):
                    break
                if s.startswith("-") or s.startswith("*"):
                    break
                metas.append(s)
                j += 1
            if metas:
                body.append(
                    f'<p class="meta">{inline_format(" · ".join(metas))}</p>'
                )
                i = j
            else:
                i += 1
            body.append("</header>")
            header_done = True
            continue

        # H2 section
        m = re.match(r"^##\s+(.+)$", stripped)
        if m:
            close_ul()
            flush_meta()
            title_s = m.group(1).strip()
            body.append("<section>")
            body.append(f"<h2>{inline_format(title_s)}</h2>")
            i += 1
            # consume until next ## or # 
            continue

        # H3 job title
        m = re.match(r"^###\s+(.+)$", stripped)
        if m:
            close_ul()
            body.append(f"<h3>{inline_format(m.group(1).strip())}</h3>")
            i += 1
            continue

        # list item
        m = re.match(r"^[-*+]\s+(.+)$", stripped)
        if m:
            if not in_ul:
                body.append("<ul>")
                in_ul = True
            body.append(f"<li>{inline_format(m.group(1).strip())}</li>")
            i += 1
            continue

        # bold line as soft heading **Company — Role**　dates
        m = re.match(r"^\*\*(.+)\*\*\s*(.*)$", stripped)
        if m:
            close_ul()
            rest = m.group(2).strip()
            body.append(
                f"<h3>{inline_format(m.group(1).strip())}"
                + (f" <span style=\"font-weight:400;color:#64748b\">{inline_format(rest)}</span>" if rest else "")
                + "</h3>"
            )
            i += 1
            continue

        close_ul()
        body.append(f"<p>{inline_format(stripped)}</p>")
        i += 1

    close_ul()

    # auto-close dangling section tags: wrap consecutive h2-opened content loosely
    # (we open <section> on h2 but never close — fix by post-process)
    html_body = "\n".join(body)
    # insert </section> before each <section> except first, and at end
    parts = html_body.split("<section>")
    if len(parts) > 1:
        rebuilt = [parts[0]]
        for p in parts[1:]:
            rebuilt.append("<section>" + p)
        html_body = rebuilt[0]
        for p in rebuilt[1:]:
            html_body += p + "</section>"
        # the above doubles — simpler approach:
    # redo section closing properly
    html_body = re.sub(r"</section>\s*", "", html_body)
    chunks = re.split(r"(?=<section>)", html_body)
    fixed: list[str] = []
    for ch in chunks:
        if ch.startswith("<section>"):
            if not ch.rstrip().endswith("</section>"):
                ch = ch.rstrip() + "</section>"
        fixed.append(ch)
    html_body = "\n".join(fixed)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="page">
{html_body}
</div>
</body>
</html>
"""


def chrome_print_pdf(chrome: str, html_path: Path, pdf_path: Path) -> None:
    html_path = html_path.resolve()
    pdf_path = pdf_path.resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    uri = html_path.as_uri()
    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--no-margins",
        f"--print-to-pdf={pdf_path}",
        uri,
    ]
    # Some Chrome versions dislike --no-margins; retry without
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not pdf_path.is_file() or pdf_path.stat().st_size < 500:
        cmd2 = [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            uri,
        ]
        proc = subprocess.run(cmd2, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Chrome print failed ({proc.returncode}): {proc.stderr or proc.stdout}"
        )
    if not pdf_path.is_file() or pdf_path.stat().st_size < 500:
        raise RuntimeError("PDF was not created or is empty")


def export_pdf(md_path: Path, pdf_path: Path | None = None, *, keep_html: bool = False) -> Path:
    md_path = md_path.resolve()
    if not md_path.is_file():
        raise FileNotFoundError(md_path)
    if pdf_path is None:
        pdf_path = md_path.with_suffix(".pdf")
    else:
        pdf_path = pdf_path.resolve()

    md_text = md_path.read_text(encoding="utf-8")
    # title from first h1
    title = "简历"
    m = re.search(r"^#\s+(.+)$", md_text, re.M)
    if m:
        title = re.sub(r"[（(].*演示.*[）)]", "", m.group(1)).strip() or title

    html_doc = md_to_resume_html(md_text, title=title)

    chrome = find_chrome()
    if not chrome and not keep_html:
        # still write HTML so user can print manually
        html_fallback = pdf_path.with_suffix(".html")
        html_fallback.write_text(html_doc, encoding="utf-8")
        raise RuntimeError(
            "未找到 Chrome / Chromium / Edge，无法自动生成 PDF。\n"
            f"已写出可打印 HTML：{html_fallback}\n"
            "请安装 Chrome 后重试，或用浏览器打开该 HTML → 打印 → 另存为 PDF（纸张 A4）。"
        )

    with tempfile.TemporaryDirectory() as tmp:
        html_path = Path(tmp) / "resume.html"
        html_path.write_text(html_doc, encoding="utf-8")
        if keep_html:
            side = pdf_path.with_suffix(".html")
            side.write_text(html_doc, encoding="utf-8")
        if chrome:
            chrome_print_pdf(chrome, html_path, pdf_path)
        else:
            raise RuntimeError("no chrome")

    return pdf_path


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="将中文简历 Markdown 导出为可投递的 A4 PDF（默认交付格式）"
    )
    p.add_argument("--input", "-i", required=True, help="resume_*.md 路径")
    p.add_argument("--output", "-o", default="", help="输出 PDF 路径（默认与 md 同名）")
    p.add_argument(
        "--html-only",
        action="store_true",
        help="只写 HTML（调试排版），不生成 PDF",
    )
    p.add_argument(
        "--keep-html",
        action="store_true",
        help="生成 PDF 同时保留同名 .html",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    md_path = Path(args.input)
    if not md_path.is_file():
        alt = ROOT / args.input
        if alt.is_file():
            md_path = alt
    out = Path(args.output) if args.output else md_path.with_suffix(".pdf")
    if not out.is_absolute() and not str(out).startswith(str(ROOT)):
        # relative to cwd
        out = Path(out)

    try:
        if args.html_only:
            md_text = md_path.read_text(encoding="utf-8")
            title = "简历"
            m = re.search(r"^#\s+(.+)$", md_text, re.M)
            if m:
                title = m.group(1).strip()
            html_path = out.with_suffix(".html") if out.suffix.lower() == ".pdf" else out
            if html_path.suffix.lower() != ".html":
                html_path = Path(str(html_path) + ".html")
            html_path.write_text(md_to_resume_html(md_text, title=title), encoding="utf-8")
            print(f"HTML → {html_path}")
            return 0

        pdf = export_pdf(md_path, out, keep_html=args.keep_html)
        print(f"PDF → {pdf}  ({pdf.stat().st_size} bytes)")
        print("投递建议：国内平台优先上传此 PDF；内容请人工核对真实后再投。")
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
