#!/usr/bin/env python3
"""Generate docs/assets/demo-loop.gif (requires Pillow; Chrome optional for board shot).

  python scripts/generate_demo_gif.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "assets" / "demo-loop.gif"
POSTER = ROOT / "docs" / "assets" / "demo-poster.png"
FRAME_DIR = ROOT / "docs" / "assets" / "_gif_frames"
BOARD_PNG = FRAME_DIR / "board.png"
HTML = ROOT / "examples" / "demo" / "output" / "job_search_tracker.html"
W, H = 1200, 675

BG = (248, 250, 252)
CARD = (255, 255, 255)
INK = (15, 23, 42)
MUTED = (100, 116, 139)
LINE = (226, 232, 240)
ACCENT = (37, 99, 235)
OK = (22, 163, 74)
TERM_BG = (24, 24, 27)
TERM_FG = (228, 228, 231)
TERM_DIM = (161, 161, 170)
TERM_GRN = (74, 222, 128)
TERM_CYN = (34, 211, 238)
TERM_YEL = (253, 224, 71)


def font(size: int, mono: bool = False):
    paths = []
    if mono:
        paths = [
            "/System/Library/Fonts/Menlo.ttc",
            "/System/Library/Fonts/Monaco.ttf",
        ]
    paths += [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size, index=0)
        except Exception:
            continue
    return ImageFont.load_default()


F_TITLE = font(34)
F_H = font(22)
F_BODY = font(18)
F_SMALL = font(15)
F_MONO = font(16, mono=True)
F_MONO_SM = font(14, mono=True)
F_BIG = font(48)


def rounded(draw, box, r, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def base(step: int, total: int = 5, title: str = ""):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 56), fill=CARD)
    d.line((0, 56, W, 56), fill=LINE, width=1)
    d.text((32, 14), "cn-job-assistant", font=F_H, fill=INK)
    d.text((280, 18), "本地求职流程示意", font=F_SMALL, fill=MUTED)
    bar_x, bar_y, bar_w = 32, H - 36, W - 64
    d.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + 8), radius=4, fill=LINE)
    fill_w = int(bar_w * (step + 1) / total)
    d.rounded_rectangle((bar_x, bar_y, bar_x + max(fill_w, 12), bar_y + 8), radius=4, fill=ACCENT)
    d.text((32, H - 58), f"{step + 1}/{total}  {title}", font=F_SMALL, fill=MUTED)
    return im, d


def terminal_card(d, x, y, w, h, title: str):
    rounded(d, (x, y, x + w, y + h), 12, TERM_BG)
    rounded(d, (x, y, x + w, y + 36), 12, (39, 39, 42))
    d.rectangle((x, y + 20, x + w, y + 36), fill=(39, 39, 42))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse((x + 14 + i * 18, y + 11, x + 26 + i * 18, y + 23), fill=c)
    d.text((x + 78, y + 9), title, font=F_MONO_SM, fill=TERM_DIM)


def write_term(d, x, y, lines, line_h=26):
    for i, (col, text) in enumerate(lines):
        d.text((x, y + i * line_h), text, font=F_MONO, fill=col)


def ensure_board_shot() -> Image.Image:
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if chrome.is_file() and HTML.is_file():
        subprocess.run(
            [
                str(chrome),
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--window-size=1200,900",
                f"--screenshot={BOARD_PNG}",
                f"file://{HTML.resolve()}",
            ],
            check=False,
            capture_output=True,
        )
    if BOARD_PNG.is_file():
        return Image.open(BOARD_PNG).convert("RGB")
    im = Image.new("RGB", (1200, 800), (255, 255, 255))
    ImageDraw.Draw(im).text((40, 40), "求职投递看板", font=F_TITLE, fill=INK)
    return im


def fit_contain(im: Image.Image, tw: int, th: int, bg=(255, 255, 255)) -> Image.Image:
    im = im.copy()
    im.thumbnail((tw, th), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (tw, th), bg)
    canvas.paste(im, ((tw - im.width) // 2, (th - im.height) // 2))
    return canvas


def crossfade(a: Image.Image, b: Image.Image, steps: int = 2):
    return [
        Image.blend(a.convert("RGB"), b.convert("RGB"), i / (steps + 1))
        for i in range(1, steps + 1)
    ]


def build_frames():
    frames, durs = [], []

    im, d = base(0, 5, "一条命令试跑")
    rounded(d, (80, 120, W - 80, 520), 16, CARD, LINE, 1)
    d.text((120, 180), "国内求职助手", font=F_TITLE, fill=INK)
    d.text((120, 240), "按岗位改简历 · 打分 · 记进度", font=F_H, fill=MUTED)
    d.text((120, 300), "投递：手动 / 半自动 / 全自动（默认手动）", font=F_BODY, fill=MUTED)
    rounded(d, (120, 380, 780, 450), 10, (15, 23, 42))
    d.text((148, 402), "$  bash scripts/demo.sh", font=F_MONO, fill=TERM_GRN)
    frames.append(im)
    durs.append(1500)

    im, d = base(1, 5, "生成简历和打招呼")
    terminal_card(d, 60, 90, W - 120, 480, "agent · /apply-zh")
    write_term(
        d,
        90,
        150,
        [
            (TERM_DIM, "# 粘贴岗位描述后生成"),
            (TERM_CYN, "岗位  星云科技 · 高级后端 · 杭州"),
            (TERM_DIM, "要求  Java / Go · Spring Boot · Kafka · K8s"),
            (TERM_FG, ""),
            (TERM_GRN, "✓  documents/zh/resume_星云科技.md"),
            (TERM_GRN, "✓  documents/zh/da-zhaohu_星云科技_后端.md"),
            (TERM_GRN, "✓  documents/zh/jd_星云科技_后端.md"),
            (TERM_FG, ""),
            (TERM_YEL, "内容请自己核对后再投"),
        ],
    )
    frames.append(im)
    durs.append(1900)

    im, d = base(2, 5, "本地匹配打分")
    terminal_card(d, 48, 90, 560, 480, "python tools/match_resume.py report")
    write_term(
        d,
        72,
        150,
        [
            (TERM_DIM, "$ report --zh-only …"),
            (TERM_FG, ""),
            (TERM_FG, "匹配摘要"),
            (TERM_GRN, "综合 54.9 / 100  ·  匹配中等"),
            (TERM_CYN, "关键词覆盖 81%"),
            (TERM_FG, ""),
            (TERM_DIM, "已对上：高并发 微服务 Kafka …"),
            (TERM_YEL, "还没有：大模型  英语"),
            (TERM_FG, ""),
            (TERM_DIM, "不会的别硬写上去刷分"),
        ],
        line_h=28,
    )
    rounded(d, (640, 120, 1150, 520), 16, CARD, LINE, 1)
    d.text((680, 160), "综合分", font=F_SMALL, fill=MUTED)
    d.text((680, 190), "54.9", font=F_BIG, fill=OK)
    d.text((820, 220), "/ 100", font=F_H, fill=MUTED)
    d.text((680, 300), "关键词覆盖", font=F_SMALL, fill=MUTED)
    d.text((680, 330), "81%", font=F_TITLE, fill=ACCENT)
    d.text((680, 420), "零模型下载 · 本地计算", font=F_SMALL, fill=MUTED)
    frames.append(im)
    durs.append(2100)

    board = ensure_board_shot()
    crop_h = min(board.size[1], int(board.size[0] * 0.62))
    board_fit = fit_contain(board.crop((0, 0, board.size[0], crop_h)), W - 100, 480)
    stage = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(stage)
    d.rectangle((0, 0, W, 56), fill=CARD)
    d.line((0, 56, W, 56), fill=LINE, width=1)
    d.text((32, 14), "cn-job-assistant", font=F_H, fill=INK)
    d.text((280, 18), "真实看板截图", font=F_SMALL, fill=MUTED)
    rounded(d, (40, 80, W - 40, 580), 14, CARD, LINE, 1)
    stage.paste(board_fit, ((W - board_fit.width) // 2, 100))
    d = ImageDraw.Draw(stage)
    d.rectangle((0, H - 64, W, H), fill=BG)
    bar_x, bar_y, bar_w = 32, H - 36, W - 64
    d.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + 8), radius=4, fill=LINE)
    d.rounded_rectangle((bar_x, bar_y, bar_x + int(bar_w * 4 / 5), bar_y + 8), radius=4, fill=ACCENT)
    d.text((32, H - 58), "4/5  本地投递看板", font=F_SMALL, fill=MUTED)
    d.text((50, 88), "examples/demo/output/job_search_tracker.html", font=F_MONO_SM, fill=MUTED)
    frames.append(stage)
    durs.append(2300)

    im, d = base(4, 5, "记进度 · 投递方式你选")
    rounded(d, (48, 90, 580, 560), 14, CARD, LINE, 1)
    d.text((72, 120), "今日进度", font=F_H, fill=INK)
    for i, (st, name, col) in enumerate(
        [("面试中", "青梧数据 · 后端", OK), ("已投递", "星云科技 · 高级后端", ACCENT), ("已结束", "北岸出行 · 服务端", MUTED)]
    ):
        y = 180 + i * 72
        rounded(d, (72, y, 540, y + 56), 8, (248, 250, 252), LINE, 1)
        d.text((92, y + 16), st, font=F_BODY, fill=col)
        d.text((200, y + 16), name, font=F_BODY, fill=INK)
    d.text((72, 420), "$ python tools/tracker.py today", font=F_MONO_SM, fill=MUTED)
    rounded(d, (610, 90, 1150, 560), 14, CARD, LINE, 1)
    d.text((640, 120), "投递方式（你来选）", font=F_H, fill=INK)
    for i, (name, desc, on) in enumerate(
        [
            ("manual", "默认 · 自己在 App 点发送", True),
            ("semi", "打开页面 + 复制话术", False),
            ("auto", "全自动（高风险，默认关）", False),
        ]
    ):
        y = 180 + i * 90
        rounded(d, (640, y, 1120, y + 70), 10, (239, 246, 255) if on else (248, 250, 252), ACCENT if on else LINE, 2 if on else 1)
        d.text((670, y + 12), name, font=F_BODY, fill=ACCENT if on else INK)
        d.text((670, y + 40), desc, font=F_SMALL, fill=MUTED)
    frames.append(im)
    durs.append(2300)

    im, d = base(4, 5, "自己试跑")
    rounded(d, (120, 140, W - 120, 500), 16, CARD, LINE, 1)
    d.text((180, 200), "clone 后先跑", font=F_H, fill=MUTED)
    rounded(d, (180, 250, 1020, 340), 10, (15, 23, 42))
    d.text((210, 278), "bash scripts/demo.sh", font=F_MONO, fill=TERM_GRN)
    d.text((180, 380), "真用：/setup-zh → /apply-zh → 自己投 → tracker", font=F_BODY, fill=INK)
    d.text((180, 430), "不默认自动投 · 数据在本地", font=F_SMALL, fill=MUTED)
    frames.append(im)
    durs.append(1700)

    final_f, final_d = [], []
    for i, fr in enumerate(frames):
        final_f.append(fr)
        final_d.append(durs[i])
        if i < len(frames) - 1:
            for cf in crossfade(fr, frames[i + 1], steps=2):
                final_f.append(cf)
                final_d.append(60)
    return final_f, final_d


def main() -> int:
    frames, durs = build_frames()
    # poster
    frames[2].save(POSTER, optimize=True)
    # downscale + palette
    out_rgb, out_d = [], []
    for f, d in zip(frames, durs):
        if d <= 70 and out_rgb and len(out_rgb) % 2 == 1:
            continue
        w, h = f.size
        nw = 1000
        nh = int(h * nw / w)
        out_rgb.append(
            f.resize((nw, nh), Image.Resampling.LANCZOS).filter(
                ImageFilter.UnsharpMask(radius=0.5, percent=70, threshold=2)
            )
        )
        out_d.append(d if d > 70 else 60)
    pal = [f.convert("P", palette=Image.Palette.ADAPTIVE, colors=128) for f in out_rgb]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pal[0].save(
        OUT,
        save_all=True,
        append_images=pal[1:],
        duration=out_d,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(pal)} frames)")
    print(f"wrote {POSTER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
