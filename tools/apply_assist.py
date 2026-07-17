#!/usr/bin/env python3
"""投递辅助：三档模式，选择权在用户。

  manual  默认——只提示你自己去 App 投
  semi    半自动——打开链接 + 复制话术，发送仍由你点
  auto    全自动——高风险，需配置文件三项风险确认 + 命令行显式开关

用法：
  python tools/apply_assist.py status
  python tools/apply_assist.py init-config
  python tools/apply_assist.py set-mode manual|semi|auto
  python tools/apply_assist.py semi --url URL --text-file path [--company 公司]
  python tools/apply_assist.py auto-greet --security-id ID [--text-file path] [--execute]
  python tools/apply_assist.py explain

说明（诚实能力边界）：
  - auto-greet 的 --text-file 仅在 boss-cli 实测支持自定义话术参数时才会传入；
    当前主流 boss-cli 的 `boss greet <id>` 往往不支持自定义话术——此时会明确拒绝，
    请改用 semi 模式复制话术后手动发送。
  - auto.max_batch 限制单次 --security-id 的数量（逗号分隔多 ID）。
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
EXAMPLE = CONFIG_DIR / "apply_mode.example.yaml"
CONFIG = CONFIG_DIR / "apply_mode.yaml"

MODES = ("manual", "semi", "auto")

RISK_KEYS = ("platform_tos", "account_ban", "personal_use_only")

MODE_HELP = {
    "manual": "手动：生成材料后，你自己在 Boss/智联 App 里点发送（默认，人人可用）",
    "semi": "半自动：打开岗位页并复制话术到剪贴板，最后一步仍由你点发送（多数人更爽）",
    "auto": "全自动：调用外部 CLI 代发/批量打招呼（可能封号，默认关，须显式确认）",
}


def _load_yaml(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
    except ImportError:
        return _parse_yaml_lite(text)
    data = yaml.safe_load(text)
    return data if isinstance(data, dict) else {}


def _parse_yaml_lite(text: str) -> dict:
    """Minimal parser for our flat-ish config if PyYAML missing."""
    data: dict = {"risk_acknowledgement": {}, "auto": {}}
    section = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" ") and line.endswith(":"):
            key = line[:-1].strip()
            section = key
            if key not in data:
                data[key] = {}
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()
        if v in ("true", "false"):
            val: object = v == "true"
        elif v.isdigit():
            val = int(v)
        else:
            val = v.strip("'\"")
        if section in ("risk_acknowledgement", "auto") and line.startswith(" "):
            data[section][k] = val
        elif section is None or section == "mode" or k == "mode":
            data[k] = val
            section = None
        elif not line.startswith(" "):
            data[k] = val
            section = None
    return data


def load_config() -> dict:
    path = Path(os.environ.get("CN_JOB_APPLY_CONFIG", str(CONFIG)))
    if not path.is_file():
        return {
            "mode": os.environ.get("CN_JOB_APPLY_MODE", "manual"),
            "risk_acknowledgement": {k: False for k in RISK_KEYS},
            "auto": {"max_batch": 5, "default_dry_run": True},
        }
    data = _load_yaml(path)
    mode = str(data.get("mode") or "manual").lower()
    if mode not in MODES:
        mode = "manual"
    risk = data.get("risk_acknowledgement") or {}
    auto = data.get("auto") or {}
    return {
        "mode": mode,
        "risk_acknowledgement": {k: bool(risk.get(k)) for k in RISK_KEYS},
        "auto": {
            "max_batch": int(auto.get("max_batch") or 5),
            "default_dry_run": bool(auto.get("default_dry_run", True)),
        },
        "_path": str(path),
    }


def save_mode(mode: str) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG.is_file():
        if EXAMPLE.is_file():
            shutil.copy2(EXAMPLE, CONFIG)
        else:
            CONFIG.write_text(
                f"mode: {mode}\n"
                "risk_acknowledgement:\n"
                "  platform_tos: false\n"
                "  account_ban: false\n"
                "  personal_use_only: false\n"
                "auto:\n"
                "  max_batch: 5\n"
                "  default_dry_run: true\n",
                encoding="utf-8",
            )
            return
    text = CONFIG.read_text(encoding="utf-8")
    if "mode:" in text:
        import re

        text = re.sub(r"(?m)^mode:\s*\S+", f"mode: {mode}", text, count=1)
    else:
        text = f"mode: {mode}\n" + text
    CONFIG.write_text(text, encoding="utf-8")


def risks_all_acked(cfg: dict) -> bool:
    risk = cfg.get("risk_acknowledgement") or {}
    return all(risk.get(k) for k in RISK_KEYS)


def cmd_status(_: argparse.Namespace) -> int:
    cfg = load_config()
    mode = cfg["mode"]
    print("当前投递模式:", mode)
    print(" ", MODE_HELP[mode])
    path = cfg.get("_path") or f"(未找到 {CONFIG.name}，使用默认 manual)"
    print("配置文件:", path)
    print()
    print("三档说明:")
    for m in MODES:
        mark = "← 当前" if m == mode else ""
        print(f"  {m:6}  {MODE_HELP[m]} {mark}")
    print()
    if mode == "auto":
        risk = cfg["risk_acknowledgement"]
        print("全自动风险确认（须全部为 true）:")
        for k in RISK_KEYS:
            print(f"  {k}: {risk.get(k)}")
        if not risks_all_acked(cfg):
            print()
            print("尚未完成风险确认：请编辑 config/apply_mode.yaml，")
            print("把 risk_acknowledgement 下三项都改成 true，否则 auto 会拒绝执行。")
    print()
    print("切换模式: python tools/apply_assist.py set-mode manual|semi|auto")
    return 0


def cmd_explain(_: argparse.Namespace) -> int:
    print(
        """
投递三档（选择权在你）

1) manual  默认
   搜岗 → 改简历/话术 → 打分 → 你在 App 里点发送 → tracker 记进度
   最安全，推荐日常使用。

2) semi  半自动
   打开岗位页、把打招呼/求职信复制到剪贴板；
   填表可以靠页面和复制内容，但「发送」必须你自己点。
   体验接近自动，封号风险远低于脚本连点。

3) auto  全自动（高风险）
   调用 boss-cli 等外部工具打招呼（默认平台招呼语）。
   可能违反平台协议、触发验证码甚至封号。
   必须同时满足：
     - config/apply_mode.yaml 里 mode: auto
     - risk_acknowledgement 三项全为 true
     - 命令行加 --i-understand-ban-risk
     - 真正发送还要再加 --execute（否则只 dry-run 打印命令）
   定制话术：多数 boss-cli 不支持 greet 自定义文案 → 请用 semi。
   --text-file 仅在探测到上游参数时才会传入，否则拒绝（不假装成功）。
   多 ID 时受 auto.max_batch 限制。

本仓库不替你承担账号损失；个人求职自负风险。
""".strip()
    )
    return 0


def cmd_init_config(_: argparse.Namespace) -> int:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG.exists():
        print(f"已存在: {CONFIG}")
        return 0
    if EXAMPLE.is_file():
        shutil.copy2(EXAMPLE, CONFIG)
    else:
        save_mode("manual")
    print(f"已创建: {CONFIG}")
    print("用编辑器改 mode 与 risk_acknowledgement，或：")
    print("  python tools/apply_assist.py set-mode semi")
    return 0


def cmd_set_mode(args: argparse.Namespace) -> int:
    mode = args.mode.lower()
    if mode not in MODES:
        print("mode 只能是 manual / semi / auto", file=sys.stderr)
        return 2
    if mode == "auto":
        print("将切换到 auto（全自动，高风险）。")
        print("请确认你已阅读: python tools/apply_assist.py explain")
        if not args.yes:
            ans = input("输入 YES 继续切换（其它任意键取消）: ").strip()
            if ans != "YES":
                print("已取消，模式未改。")
                return 1
        save_mode("auto")
        print(f"已写入 mode: auto → {CONFIG}")
        print("下一步：编辑 config/apply_mode.yaml，将 risk_acknowledgement 三项改为 true。")
        print("执行自动发送时还需 --i-understand-ban-risk 与 --execute。")
        return 0
    save_mode(mode)
    print(f"已切换为 {mode}: {MODE_HELP[mode]}")
    print(f"配置: {CONFIG if CONFIG.is_file() else '(将在首次 set-mode 时创建)'}")
    return 0


def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard. Supports macOS / Linux / Windows."""
    data = text.encode("utf-8")
    # macOS
    if shutil.which("pbcopy"):
        p = subprocess.run(["pbcopy"], input=data, check=False)
        return p.returncode == 0
    # Wayland
    if shutil.which("wl-copy"):
        p = subprocess.run(["wl-copy"], input=data, check=False)
        return p.returncode == 0
    # X11
    if shutil.which("xclip"):
        p = subprocess.run(
            ["xclip", "-selection", "clipboard"], input=data, check=False
        )
        return p.returncode == 0
    if shutil.which("xsel"):
        p = subprocess.run(
            ["xsel", "--clipboard", "--input"], input=data, check=False
        )
        return p.returncode == 0
    # Windows: PowerShell first (Unicode / 中文话术), then clip.exe
    if sys.platform == "win32" or shutil.which("powershell") or shutil.which("pwsh"):
        for shell in ("pwsh", "powershell"):
            if not shutil.which(shell):
                continue
            try:
                p = subprocess.run(
                    [
                        shell,
                        "-NoProfile",
                        "-NonInteractive",
                        "-Command",
                        "Set-Clipboard -Value ([Console]::In.ReadToEnd())",
                    ],
                    input=text,
                    text=True,
                    encoding="utf-8",
                    check=False,
                    timeout=15,
                )
                if p.returncode == 0:
                    return True
            except (OSError, subprocess.TimeoutExpired):
                continue
        if shutil.which("clip"):
            try:
                # clip.exe expects UTF-16LE on modern Windows consoles
                p = subprocess.run(
                    ["clip"],
                    input=text.encode("utf-16-le"),
                    check=False,
                    timeout=10,
                )
                return p.returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                pass
    return False


def parse_security_ids(raw: str) -> list[str]:
    """Split --security-id value: commas and whitespace."""
    if not raw or not str(raw).strip():
        return []
    parts = re.split(r"[,;\s]+", str(raw).strip())
    return [p for p in parts if p]


def probe_boss_greet_text_argv(text_file: str, message: str) -> tuple[list[str] | None, str]:
    """Detect whether boss-cli can take a custom greet message.

    Returns (extra_argv or None, human reason).
    Prefer file-based flags; fall back to inline message flags.
    """
    help_text = ""
    for cmd in (["boss", "greet", "--help"], ["boss", "greet", "-h"], ["boss", "--help"]):
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=12,
                check=False,
            )
            chunk = (proc.stdout or "") + "\n" + (proc.stderr or "")
            if chunk.strip():
                help_text = chunk
                break
        except (OSError, subprocess.TimeoutExpired):
            continue

    if not help_text.strip():
        return (
            None,
            "无法读取 boss greet --help；无法确认是否支持自定义话术。"
            "请改用 semi 模式复制话术，或去掉 --text-file 使用平台默认招呼。",
        )

    lower = help_text.lower()
    # File-based flags (path passed through)
    file_flags = (
        "--message-file",
        "--text-file",
        "--greet-file",
        "--content-file",
    )
    for flag in file_flags:
        if flag in lower or flag.replace("-", "") in lower.replace("-", ""):
            return [flag, text_file], f"检测到 {flag}，将把话术文件传入 boss"

    # Short -f / --file only if help mentions greet-related file
    if re.search(r"(?m)^\s*-f\b|--file\b", help_text) and re.search(
        r"message|text|content|话术|招呼|greet", lower
    ):
        return ["--file", text_file], "检测到 --file/-f，将把话术文件传入 boss"

    # Inline message flags (pass file contents)
    inline_flags = ("--message", "--text", "--content", "-m")
    for flag in inline_flags:
        # require word boundary-ish match in help
        pat = re.escape(flag)
        if re.search(rf"(?m)\s{pat}\b|{pat}\s", help_text) or flag in lower:
            if flag == "-m" and not re.search(r"(?m)\s-m\b", help_text):
                continue
            return [flag, message], f"检测到 {flag}，将把话术正文传入 boss"

    return (
        None,
        "当前 boss-cli 的 greet 未暴露自定义话术参数（常见仅 `boss greet <id> [--json]`）。"
        "自定义话术请用 semi：python tools/apply_assist.py semi --text-file …",
    )


def build_boss_greet_cmd(
    security_id: str,
    text_file: str = "",
    *,
    probe: bool = True,
) -> tuple[list[str] | None, str]:
    """Build boss greet argv. Returns (cmd or None, note/error)."""
    cmd: list[str] = ["boss", "greet", security_id]
    if not text_file:
        return cmd, "使用 boss-cli / 平台默认招呼语（未传 --text-file）"

    # Resolve path early so dry-run is honest
    try:
        path = Path(text_file)
        if not path.is_file():
            alt = ROOT / text_file
            if alt.is_file():
                path = alt
            else:
                return None, f"话术文件不存在: {text_file}"
        message = path.read_text(encoding="utf-8").strip()
        resolved = str(path)
    except OSError as exc:
        return None, f"无法读取话术文件: {exc}"

    if not message:
        return None, f"话术文件为空: {resolved}"

    if not probe:
        return None, "跳过探测"

    extra, reason = probe_boss_greet_text_argv(resolved, message)
    if extra is None:
        return None, reason
    return cmd + extra, reason


def read_text_file(path: str) -> str:
    p = Path(path)
    if not p.is_file():
        alt = ROOT / path
        if alt.is_file():
            p = alt
        else:
            raise FileNotFoundError(path)
    return p.read_text(encoding="utf-8")


def cmd_semi(args: argparse.Namespace) -> int:
    """Semi-auto: open URL + clipboard. Never sends."""
    cfg = load_config()
    if cfg["mode"] == "manual":
        print("提示：当前配置是 manual。半自动仍可单次执行；")
        print("若希望默认半自动: python tools/apply_assist.py set-mode semi")
        print()
    if cfg["mode"] == "auto":
        print("提示：当前配置是 auto，但本命令是 semi：只打开页面/复制文本，不会代发。")
        print()

    text = ""
    if args.text_file:
        text = read_text_file(args.text_file).strip()
    elif args.text:
        text = args.text.strip()

    company = args.company or ""
    print("=== 半自动投递辅助（发送仍须你亲手点）===")
    if company:
        print(f"公司: {company}")
    if args.url:
        print(f"打开: {args.url}")
        try:
            webbrowser.open(args.url)
            print("  已尝试在浏览器打开。")
        except Exception as exc:
            print(f"  打不开浏览器: {exc}，请手动打开链接。")
    if text:
        ok = copy_to_clipboard(text)
        preview = text.replace("\n", " ")[:80]
        if ok:
            print(f"  话术已复制到剪贴板: {preview}…")
        else:
            print("  无法写剪贴板，请手动复制以下内容：")
            print("---")
            print(text)
            print("---")
            print("  剪贴板排障：")
            if sys.platform == "darwin":
                print("    · macOS 需有 pbcopy（系统自带）")
            elif sys.platform.startswith("linux"):
                print("    · Linux: 安装 wl-clipboard（Wayland）或 xclip/xsel（X11）")
            elif sys.platform == "win32":
                print("    · Windows: 确认 PowerShell 可用，或使用 clip.exe")
            else:
                print("    · 当前环境未检测到剪贴板工具，粘贴步骤请纯手动")
    else:
        print("  未提供 --text-file / --text，只处理链接。")

    print()
    print("请你现在：")
    print("  1. 在打开的页面里确认是目标岗位")
    print("  2. 粘贴话术 / 上传简历（Cmd/Ctrl+V）")
    print("  3. 自己点「发送」或「立即沟通」——本工具绝不会代点")
    print("  4. 回来记一笔（若刚过 quality_gate，把分写上便于 match-outcome）:")
    if company:
        print(
            f"     python tools/tracker.py add --company {company} "
            f"--role '{args.role or ''}' --channel '{args.channel or 'Boss直聘'}' "
            f"--status applied "
            f"[--match-score N --match-coverage N --match-verdict …]"
        )
    else:
        print(
            "     python tools/tracker.py add --company … --role … --status applied "
            "[--match-score N --match-coverage N --match-verdict …]"
        )
    print(
        "     # 投前: python tools/quality_gate.py --resume … --jd … --pdf …"
    )
    return 0


def cmd_auto_greet(args: argparse.Namespace) -> int:
    """Full auto path via boss-cli — gated hard."""
    cfg = load_config()
    if cfg["mode"] != "auto":
        print(
            "拒绝：当前 mode 不是 auto。\n"
            "全自动必须你主动打开：\n"
            "  python tools/apply_assist.py set-mode auto\n"
            "并编辑 config/apply_mode.yaml 完成风险确认。",
            file=sys.stderr,
        )
        return 2
    if not risks_all_acked(cfg):
        print(
            "拒绝：risk_acknowledgement 未全部为 true。\n"
            "请编辑 config/apply_mode.yaml：\n"
            "  platform_tos / account_ban / personal_use_only 都改成 true",
            file=sys.stderr,
        )
        return 2
    if not args.i_understand_ban_risk:
        print(
            "拒绝：缺少 --i-understand-ban-risk\n"
            "全自动可能限流/封号。确认自担风险后再加该参数。",
            file=sys.stderr,
        )
        return 2

    if not shutil.which("boss"):
        print(
            "未找到 boss 命令。请先:\n"
            "  python tools/install_domestic_search.py install-boss",
            file=sys.stderr,
        )
        return 1

    sids = parse_security_ids(args.security_id)
    if not sids:
        print("拒绝：--security-id 为空。", file=sys.stderr)
        return 2

    max_batch = int(cfg["auto"].get("max_batch") or 5)
    if len(sids) > max_batch:
        print(
            f"拒绝：本次 {len(sids)} 个 security-id，超过 auto.max_batch={max_batch}。\n"
            f"请减少 ID，或编辑 config/apply_mode.yaml 提高 max_batch（仍建议保守）。",
            file=sys.stderr,
        )
        return 2

    text_file = (args.text_file or "").strip()
    # Build one representative command (message flags same for all IDs)
    sample_cmd, note = build_boss_greet_cmd(sids[0], text_file)
    if sample_cmd is None:
        print("拒绝：自定义话术无法安全传入 boss-cli。", file=sys.stderr)
        print(note, file=sys.stderr)
        print(
            "\n推荐：\n"
            "  python tools/apply_assist.py semi "
            f"--text-file {text_file or 'documents/zh/da-zhaohu_….md'} "
            "--company …\n"
            "或去掉 --text-file，仅触发平台默认招呼：\n"
            f"  python tools/apply_assist.py auto-greet --security-id {sids[0]} "
            "--i-understand-ban-risk [--execute]",
            file=sys.stderr,
        )
        return 2

    cmds: list[list[str]] = []
    for sid in sids:
        cmd, _ = build_boss_greet_cmd(sid, text_file)
        if cmd is None:
            print(f"拒绝：无法为 {sid} 构建命令。", file=sys.stderr)
            return 2
        cmds.append(cmd)

    dry = cfg["auto"].get("default_dry_run", True) and not args.execute
    print("=== 全自动路径（boss-cli）===")
    print(f"条数: {len(cmds)} / max_batch={max_batch}")
    print(f"话术: {note}")
    print("将执行:" if not dry else "【dry-run】将要执行:")
    for cmd in cmds:
        print(" ", " ".join(cmd))
    print()
    if dry:
        print("未加 --execute：只预览，不调用 boss。")
        print("确认无误后：")
        print(
            "  python tools/apply_assist.py auto-greet "
            f"--security-id {','.join(sids)} "
            + (f"--text-file {text_file} " if text_file else "")
            + "--i-understand-ban-risk --execute"
        )
        if text_file:
            print(
                "\n注意：若 dry-run 显示的命令不含话术参数，"
                "说明当前 boss-cli 不支持自定义话术（本工具会在探测失败时已拒绝）。"
            )
        return 0

    print("正在调用 boss-cli（可能产生真实打招呼）…")
    failed = 0
    for cmd in cmds:
        print("→", " ".join(cmd))
        proc = subprocess.run(cmd, check=False)
        if proc.returncode != 0:
            failed += 1
            print(
                f"  boss 返回 {proc.returncode}。"
                "请检查: boss status / boss login --qrcode",
                file=sys.stderr,
            )
    if failed:
        print(f"完成：{len(cmds) - failed}/{len(cmds)} 成功，{failed} 失败。", file=sys.stderr)
        return 1
    print("已全部调用完成。请到 App 核对是否发出；并用 tracker 记一笔。")
    if args.company:
        print(
            "建议: python tools/tracker.py add "
            f"--company {args.company} --role '{args.role or ''}' "
            f"--channel Boss直聘 --status applied "
            "[--match-score N --match-coverage N --match-verdict …]"
        )
    print("复盘: python tools/tracker.py match-outcome")
    return 0


def cmd_dispatch_by_mode(args: argparse.Namespace) -> int:
    """After /apply-zh: run the right helper for current mode."""
    cfg = load_config()
    mode = cfg["mode"]
    print(f"当前模式: {mode} — {MODE_HELP[mode]}")
    print()
    if mode == "manual":
        print("请把生成的话术/简历，自己粘贴到招聘 App 后点发送。")
        print("投前: python tools/quality_gate.py --resume … --jd … --pdf …")
        print(
            "记进度: python tools/tracker.py suggest-add --company … --role … "
            "[--match-score N --match-coverage N --match-verdict …]"
        )
        return 0
    if mode == "semi":
        if not args.url and not args.text_file and not args.text:
            print("semi 模式请提供 --url 和/或 --text-file")
            print(
                "示例: python tools/apply_assist.py after-generate "
                "--url 'https://…' --text-file documents/zh/da-zhaohu_….md "
                "--company 某某"
            )
            return 2
        return cmd_semi(args)
    # auto: never silent-send; only remind how to opt in execute
    print("全自动已开启配置，但仍不会在 after-generate 里静默发送。")
    print("自定义话术请优先 semi（多数 boss-cli 不支持 greet 自定义文案）：")
    print(
        "  python tools/apply_assist.py semi --url … --text-file … --company …"
    )
    print("若坚持 auto（平台默认招呼，须风险参数 + --execute）：")
    print(
        "  python tools/apply_assist.py auto-greet "
        "--security-id <id> --i-understand-ban-risk --execute"
    )
    print("带 --text-file 时：仅当 boss-cli 探测支持话术参数才会执行，否则拒绝。")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="apply_assist",
        description="投递辅助：manual / semi / auto，默认手动，选择权在用户。",
    )
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("status", help="查看当前模式")
    s.set_defaults(func=cmd_status)

    e = sub.add_parser("explain", help="说明三档差异与风险")
    e.set_defaults(func=cmd_explain)

    i = sub.add_parser("init-config", help="创建 config/apply_mode.yaml")
    i.set_defaults(func=cmd_init_config)

    m = sub.add_parser("set-mode", help="切换 manual|semi|auto")
    m.add_argument("mode", choices=MODES)
    m.add_argument("-y", "--yes", action="store_true", help="auto 切换时跳过 YES 确认")
    m.set_defaults(func=cmd_set_mode)

    semi = sub.add_parser("semi", help="半自动：打开链接 + 复制话术")
    semi.add_argument("--url", default="")
    semi.add_argument("--text-file", default="")
    semi.add_argument("--text", default="")
    semi.add_argument("--company", default="")
    semi.add_argument("--role", default="")
    semi.add_argument("--channel", default="Boss直聘")
    semi.set_defaults(func=cmd_semi)

    ag = sub.add_parser("auto-greet", help="全自动打招呼（高风险，多重门禁）")
    ag.add_argument(
        "--security-id",
        required=True,
        help="Boss 岗位 securityId；多个用逗号分隔，受 auto.max_batch 限制",
    )
    ag.add_argument(
        "--text-file",
        default="",
        help="自定义话术文件；仅当 boss-cli 支持对应参数时才会传入，否则拒绝并建议 semi",
    )
    ag.add_argument("--company", default="")
    ag.add_argument("--role", default="")
    ag.add_argument(
        "--i-understand-ban-risk",
        action="store_true",
        help="确认自担封号/限流风险",
    )
    ag.add_argument(
        "--execute",
        action="store_true",
        help="真正调用 boss；默认 dry-run 只打印",
    )
    ag.set_defaults(func=cmd_auto_greet)

    agn = sub.add_parser(
        "after-generate",
        help="生成材料后按当前 mode 给出下一步（auto 不会静默发送）",
    )
    agn.add_argument("--url", default="")
    agn.add_argument("--text-file", default="")
    agn.add_argument("--text", default="")
    agn.add_argument("--company", default="")
    agn.add_argument("--role", default="")
    agn.add_argument("--channel", default="Boss直聘")
    agn.set_defaults(func=cmd_dispatch_by_mode)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
