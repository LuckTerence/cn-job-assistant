#!/usr/bin/env python3
"""Export Chinese résumé Markdown → submittable A4 PDF.

Backends (auto-detect order unless --backend is set):
  1. typst   — templates/zh/typst/resume.typ  (preferred; professional typesetting)
  2. pandoc  — if pandoc is installed
  3. chrome  — HTML print CSS + headless Chrome/Edge (fallback)

This tool is an *adapter*, not a home-grown typesetting engine.
See docs/resume-pdf-reuse.zh.md for upstream projects (Typst Chinese templates,
RenderCV, pandoc_resume, …). OrangeX4 Chinese-Resume-in-Typst is recommended
as a personal template source but is not vendored (no LICENSE on GitHub).

Usage:
  python tools/export_resume_pdf.py -i documents/zh/resume_公司.md
  python tools/export_resume_pdf.py -i path.md --backend typst
  python tools/export_resume_pdf.py -i path.md --backend chrome --keep-html
  python tools/export_resume_pdf.py --which
"""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TYPST_TEMPLATE = ROOT / "templates" / "zh" / "typst" / "resume.typ"

# ---------------------------------------------------------------------------
# Resume model + Markdown parse
# ---------------------------------------------------------------------------


@dataclass
class Block:
    head: str = ""
    items: list[str] = field(default_factory=list)
    paras: list[str] = field(default_factory=list)


@dataclass
class Section:
    title: str
    blocks: list[Block] = field(default_factory=list)


@dataclass
class Resume:
    name: str = "简历"
    meta: str = ""
    sections: list[Section] = field(default_factory=list)


def parse_resume_md(md: str) -> Resume:
    lines = md.replace("\r\n", "\n").split("\n")
    res = Resume()
    i = 0
    current: Section | None = None
    block: Block | None = None

    def flush_block() -> None:
        nonlocal block
        if current is not None and block is not None:
            if block.head or block.items or block.paras:
                current.blocks.append(block)
        block = None

    def ensure_block() -> Block:
        nonlocal block
        if block is None:
            block = Block()
        return block

    while i < len(lines):
        s = lines[i].strip()
        if (
            not s
            or s.startswith("<!--")
            or s.startswith("-->")
            or s.startswith(">")
            or s in ("---", "***", "___")
        ):
            i += 1
            continue

        m = re.match(r"^#\s+(.+)$", s)
        if m:
            name = re.sub(r"[（(].*演示.*[）)]", "", m.group(1).strip()).strip()
            res.name = name or res.name
            j = i + 1
            metas: list[str] = []
            while j < len(lines):
                t = lines[j].strip()
                if not t or t.startswith("#") or t.startswith(">") or t.startswith(("-", "*", "+")):
                    break
                metas.append(t)
                j += 1
            res.meta = " · ".join(metas)
            i = j
            continue

        m = re.match(r"^##\s+(.+)$", s)
        if m:
            flush_block()
            if current is not None:
                res.sections.append(current)
            current = Section(title=m.group(1).strip())
            block = None
            i += 1
            continue

        m = re.match(r"^###\s+(.+)$", s)
        if m:
            flush_block()
            block = Block(head=m.group(1).strip())
            i += 1
            continue

        m = re.match(r"^\*\*(.+)\*\*\s*(.*)$", s)
        if m:
            flush_block()
            head = m.group(1).strip()
            rest = m.group(2).strip()
            if rest:
                head = f"{head}  {rest}"
            block = Block(head=head)
            i += 1
            continue

        m = re.match(r"^[-*+]\s+(.+)$", s)
        if m:
            ensure_block().items.append(m.group(1).strip())
            i += 1
            continue

        ensure_block().paras.append(s)
        i += 1

    flush_block()
    if current is not None:
        res.sections.append(current)
    return res


# ---------------------------------------------------------------------------
# Typst backend
# ---------------------------------------------------------------------------


def typst_escape(s: str) -> str:
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("#", "\\#")
        .replace("$", "\\$")
        .replace("@", "\\@")
    )


def resume_to_typst(res: Resume, template_path: Path = TYPST_TEMPLATE) -> str:
    """Build a complete .typ file: template functions + #resume(...) call."""
    raw = template_path.read_text(encoding="utf-8")
    # Drop the demo #resume(...) at the bottom of the template file
    cut = raw.find("// --- data injected")
    if cut == -1:
        cut = raw.find("#resume(")
    head = raw[:cut].rstrip() + "\n\n" if cut != -1 else raw + "\n\n"

    sec_parts: list[str] = []
    for sec in res.sections:
        blocks: list[str] = []
        for b in sec.blocks:
            items = ", ".join(f'"{typst_escape(it)}"' for it in b.items)
            paras = ", ".join(f'"{typst_escape(p)}"' for p in b.paras)
            blocks.append(
                f'(head: "{typst_escape(b.head)}", '
                f"items: ({items}" + ("," if items else "") + "), "
                f"paras: ({paras}" + ("," if paras else "") + "))"
            )
        blocks_joined = ",\n        ".join(blocks)
        sec_parts.append(
            f'(\n      title: "{typst_escape(sec.title)}",\n'
            f"      blocks: (\n        {blocks_joined}\n      "
            + ("," if blocks else "")
            + "\n      ),\n    )"
        )
    sections_joined = ",\n    ".join(sec_parts)
    call = (
        f"#resume(\n"
        f'  name: "{typst_escape(res.name)}",\n'
        f'  meta: "{typst_escape(res.meta)}",\n'
        f"  sections: (\n    {sections_joined}\n  "
        + ("," if sec_parts else "")
        + "\n  ),\n)\n"
    )
    return head + call


def find_typst() -> str | None:
    env = os.environ.get("TYPST_BIN") or os.environ.get("CN_JOB_TYPST")
    if env and Path(env).is_file():
        return env
    return shutil.which("typst")


def compile_typst(typ_path: Path, pdf_path: Path, typst_bin: str) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    # font-path: help typst find CJK on macOS
    font_paths = [
        "/System/Library/Fonts",
        "/Library/Fonts",
        str(Path.home() / "Library/Fonts"),
        "/usr/share/fonts",
    ]
    cmd = [typst_bin, "compile"]
    for fp in font_paths:
        if Path(fp).is_dir():
            cmd.extend(["--font-path", fp])
    cmd.extend([str(typ_path), str(pdf_path)])
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"typst compile failed:\n{proc.stderr or proc.stdout}"
        )
    if not pdf_path.is_file() or pdf_path.stat().st_size < 500:
        raise RuntimeError("typst produced empty PDF")


# ---------------------------------------------------------------------------
# Chrome HTML backend (fallback)
# ---------------------------------------------------------------------------

CSS = """
@page { size: A4; margin: 12mm 14mm; }
* { box-sizing: border-box; }
html, body {
  margin: 0; padding: 0;
  font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei",
               "Noto Sans CJK SC", "Source Han Sans SC", "Heiti SC", sans-serif;
  font-size: 10.5pt; line-height: 1.45; color: #1a1a1a; background: #fff;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
.page { max-width: 180mm; margin: 0 auto; }
header.identity { border-bottom: 2px solid #1e3a5f; padding-bottom: 8px; margin-bottom: 12px; }
header.identity h1 { margin: 0 0 4px 0; font-size: 18pt; font-weight: 650; color: #0f172a; }
header.identity .meta { margin: 0; font-size: 9.5pt; color: #475569; }
section { margin: 0 0 10px 0; page-break-inside: avoid; }
section h2 {
  margin: 0 0 5px 0; padding: 0 0 3px 0; font-size: 11pt; font-weight: 650;
  color: #1e3a5f; border-bottom: 1px solid #cbd5e1;
}
section h3 { margin: 7px 0 2px 0; font-size: 10.5pt; font-weight: 600; color: #0f172a; }
p { margin: 0 0 4px 0; }
ul { margin: 2px 0 6px 0; padding-left: 1.15em; }
li { margin: 0 0 2px 0; }
strong { font-weight: 600; }
"""


def inline_format(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return text


def resume_to_html(res: Resume) -> str:
    parts: list[str] = []
    parts.append('<header class="identity">')
    parts.append(f"<h1>{inline_format(res.name)}</h1>")
    if res.meta:
        parts.append(f'<p class="meta">{inline_format(res.meta)}</p>')
    parts.append("</header>")
    for sec in res.sections:
        parts.append("<section>")
        parts.append(f"<h2>{inline_format(sec.title)}</h2>")
        for b in sec.blocks:
            if b.head:
                parts.append(f"<h3>{inline_format(b.head)}</h3>")
            for p in b.paras:
                parts.append(f"<p>{inline_format(p)}</p>")
            if b.items:
                parts.append("<ul>")
                for it in b.items:
                    parts.append(f"<li>{inline_format(it)}</li>")
                parts.append("</ul>")
        parts.append("</section>")
    body = "\n".join(parts)
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/>
<title>{html.escape(res.name)}</title>
<style>{CSS}</style></head>
<body><div class="page">{body}</div></body></html>
"""


def find_chrome() -> str | None:
    env = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which(
        "chromium-browser"
    )
    if env:
        return env
    for c in (
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
        Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    ):
        if c.is_file():
            return str(c)
    return None


def chrome_print_pdf(chrome: str, html_path: Path, pdf_path: Path) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    uri = html_path.resolve().as_uri()
    for extra in (["--no-margins"], []):
        cmd = [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            *extra,
            f"--print-to-pdf={pdf_path.resolve()}",
            uri,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0 and pdf_path.is_file() and pdf_path.stat().st_size > 500:
            return
    raise RuntimeError(f"Chrome print failed: {proc.stderr or proc.stdout}")


# ---------------------------------------------------------------------------
# Pandoc backend
# ---------------------------------------------------------------------------


def find_pandoc() -> str | None:
    return shutil.which("pandoc")


def compile_pandoc(md_path: Path, pdf_path: Path, pandoc: str) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    # Prefer xelatex for CJK when available
    for pdf_engine in ("xelatex", "lualatex", "pdflatex", None):
        cmd = [pandoc, str(md_path), "-o", str(pdf_path)]
        if pdf_engine:
            cmd.extend([f"--pdf-engine={pdf_engine}"])
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0 and pdf_path.is_file() and pdf_path.stat().st_size > 500:
            return
    raise RuntimeError(
        f"pandoc failed (install xelatex for Chinese):\n{proc.stderr or proc.stdout}"
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def detect_backends() -> dict[str, str | None]:
    return {
        "typst": find_typst(),
        "pandoc": find_pandoc(),
        "chrome": find_chrome(),
    }


def pick_backend(prefer: str = "auto") -> str:
    found = detect_backends()
    if prefer != "auto":
        if prefer == "typst" and not found["typst"]:
            raise RuntimeError(
                "未找到 typst。安装: brew install typst\n"
                "或 https://github.com/typst/typst/releases\n"
                "也可 --backend chrome"
            )
        if prefer == "chrome" and not found["chrome"]:
            raise RuntimeError("未找到 Chrome/Chromium/Edge")
        if prefer == "pandoc" and not found["pandoc"]:
            raise RuntimeError("未找到 pandoc")
        return prefer
    for name in ("typst", "pandoc", "chrome"):
        if found[name]:
            return name
    raise RuntimeError(
        "没有可用 PDF 后端。请至少安装其一：\n"
        "  - typst（推荐）: brew install typst\n"
        "  - Chrome / Edge\n"
        "  - pandoc + xelatex（中文）"
    )


def export_pdf(
    md_path: Path,
    pdf_path: Path | None = None,
    *,
    backend: str = "auto",
    keep_html: bool = False,
    keep_typst: bool = False,
) -> tuple[Path, str]:
    md_path = md_path.resolve()
    if not md_path.is_file():
        raise FileNotFoundError(md_path)
    if pdf_path is None:
        pdf_path = md_path.with_suffix(".pdf")
    else:
        pdf_path = pdf_path.resolve()

    md_text = md_path.read_text(encoding="utf-8")
    res = parse_resume_md(md_text)
    be = pick_backend(backend)

    if be == "typst":
        typ_src = resume_to_typst(res)
        with tempfile.TemporaryDirectory() as tmp:
            typ_path = Path(tmp) / "resume.typ"
            typ_path.write_text(typ_src, encoding="utf-8")
            if keep_typst:
                side = pdf_path.with_suffix(".typ")
                side.write_text(typ_src, encoding="utf-8")
            compile_typst(typ_path, pdf_path, find_typst() or "typst")
        return pdf_path, "typst"

    if be == "pandoc":
        compile_pandoc(md_path, pdf_path, find_pandoc() or "pandoc")
        return pdf_path, "pandoc"

    # chrome
    html_doc = resume_to_html(res)
    with tempfile.TemporaryDirectory() as tmp:
        html_path = Path(tmp) / "resume.html"
        html_path.write_text(html_doc, encoding="utf-8")
        if keep_html:
            pdf_path.with_suffix(".html").write_text(html_doc, encoding="utf-8")
        chrome = find_chrome()
        if not chrome:
            fallback = pdf_path.with_suffix(".html")
            fallback.write_text(html_doc, encoding="utf-8")
            raise RuntimeError(
                f"未找到 Chrome。已写出 HTML：{fallback}\n"
                "用浏览器打开 → 打印 → 存为 PDF（纸张 A4）。"
            )
        chrome_print_pdf(chrome, html_path, pdf_path)
    return pdf_path, "chrome"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="中文简历 Markdown → 可投递 A4 PDF（优先 Typst，回退 Chrome/Pandoc）"
    )
    p.add_argument("--input", "-i", help="resume_*.md")
    p.add_argument("--output", "-o", default="", help="输出 PDF")
    p.add_argument(
        "--backend",
        choices=("auto", "typst", "chrome", "pandoc"),
        default="auto",
        help="导出后端（默认 auto：typst > pandoc > chrome）",
    )
    p.add_argument("--keep-html", action="store_true", help="chrome 模式保留 html")
    p.add_argument("--keep-typst", action="store_true", help="typst 模式保留 .typ 源")
    p.add_argument("--html-only", action="store_true", help="只写 HTML，不导出 PDF")
    p.add_argument("--which", action="store_true", help="列出本机可用后端")
    p.add_argument(
        "--verify-text",
        action="store_true",
        help="导出后若本机有 pdftotext，检查文本层（ATS 可读性）",
    )
    return p


def verify_pdf_text_layer(pdf_path: Path) -> tuple[bool, str]:
    """Optional ATS text-layer check via poppler pdftotext."""
    bin_ = shutil.which("pdftotext")
    if not bin_:
        return True, "skip: pdftotext not installed (brew install poppler)"
    try:
        proc = subprocess.run(
            [bin_, "-layout", str(pdf_path), "-"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"pdftotext failed: {e}"
    text = proc.stdout or ""
    if proc.returncode != 0:
        return False, (proc.stderr or "pdftotext error")[:200]
    if "cid:" in text.lower() or "\ufffd" in text:
        return False, "text layer has (cid:*) or replacement chars — ATS may misread"
    if len(re.sub(r"\s+", "", text)) < 40:
        return False, "extracted text too short — PDF may be image-only"
    return True, f"ok ({len(text)} chars extracted)"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.which:
        found = detect_backends()
        print("PDF backends:")
        for k, v in found.items():
            print(f"  {k:8}  {'OK  ' + v if v else 'missing'}")
        try:
            print("auto picks:", pick_backend("auto"))
        except RuntimeError as e:
            print("auto picks: none —", e)
        print()
        print("推荐安装 Typst: brew install typst")
        print("选型说明: docs/resume-pdf-reuse.zh.md")
        return 0

    if not args.input:
        print("error: --input required (or use --which)", file=sys.stderr)
        return 2

    md_path = Path(args.input)
    if not md_path.is_file():
        alt = ROOT / args.input
        if alt.is_file():
            md_path = alt
    out = Path(args.output) if args.output else md_path.with_suffix(".pdf")

    try:
        if args.html_only:
            res = parse_resume_md(md_path.read_text(encoding="utf-8"))
            html_path = out.with_suffix(".html")
            html_path.write_text(resume_to_html(res), encoding="utf-8")
            print(f"HTML → {html_path}")
            return 0

        pdf, used = export_pdf(
            md_path,
            out,
            backend=args.backend,
            keep_html=args.keep_html,
            keep_typst=args.keep_typst,
        )
        print(f"PDF → {pdf}  ({pdf.stat().st_size} bytes)  [backend={used}]")
        if used == "chrome":
            print("提示: 安装 typst 后版式更稳更好看 — brew install typst")
        if getattr(args, "verify_text", False):
            ok, msg = verify_pdf_text_layer(Path(pdf))
            print(f"ATS 文本层: {'✅' if ok else '❌'} {msg}")
            if not ok and not msg.startswith("skip:"):
                print("投递前请人工打开 PDF 核对；或换 typst/后端重导。", file=sys.stderr)
        print("投递用此 PDF；内容请人工核对真实后再投。")
        print("诚信检查: python tools/check_profile_resume.py --profile CLAUDE.zh.md --resume <md>")
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
