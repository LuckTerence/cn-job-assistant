#!/usr/bin/env python3
"""One-shot installer / status checker for domestic job-search backends.

Reuses existing open-source tools (does not reimplement crawlers):

  - boss-cli   (jackwener/boss-cli) — Boss直聘 CLI; license undeclared upstream
  - get_jobs   (loks666/get_jobs)    — 智联/51job/猎聘/拉勾; non-commercial license

Usage (from repo root):
  python tools/install_domestic_search.py status
  python tools/install_domestic_search.py install-boss
  python tools/install_domestic_search.py install-get-jobs
  python tools/install_domestic_search.py install-all
  python tools/install_domestic_search.py smoke          # offline-friendly checks

Personal / non-commercial use only. Respect each tool's license and platform ToS.
This repo never auto-submits applications.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VENDOR = ROOT / "third_party"
GET_JOBS_DIR_NAME = "get_jobs"
GET_JOBS_REPO = "https://github.com/loks666/get_jobs.git"
BOSS_CLI_PIP = "boss-cli"


def run(
    cmd: list[str],
    *,
    check: bool = False,
    capture: bool = True,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture,
        text=True,
        cwd=str(cwd) if cwd else None,
    )


def which(name: str) -> str | None:
    return shutil.which(name)


def vendor_get_jobs(vendor: Path) -> Path:
    return vendor / GET_JOBS_DIR_NAME


def boss_status() -> dict[str, str | bool]:
    path = which("boss")
    version = ""
    if path:
        proc = run([path, "--version"])
        if proc.returncode != 0:
            proc = run([path, "--help"])
        version = (proc.stdout or proc.stderr or "").strip().splitlines()[:1]
        version = version[0] if version else "(installed)"
    # Also try python -m
    mod_ok = False
    if not path:
        proc = run([sys.executable, "-m", "boss", "--help"])
        mod_ok = proc.returncode == 0
    return {
        "installed": bool(path) or mod_ok,
        "path": path or ("python -m boss" if mod_ok else ""),
        "version": version if path else ("module ok" if mod_ok else ""),
    }


def get_jobs_status(vendor: Path) -> dict[str, str | bool]:
    dest = vendor_get_jobs(vendor)
    exists = dest.is_dir() and any(dest.iterdir()) if dest.exists() else False
    return {
        "installed": exists,
        "path": str(dest) if exists else "",
        "hint": "JDK 21 + Gradle required to run (see get_jobs README)",
    }


def cmd_status(args: argparse.Namespace) -> int:
    boss = boss_status()
    gj = get_jobs_status(Path(args.vendor))
    print("Domestic search backends")
    print("========================")
    print(f"boss-cli : {'OK' if boss['installed'] else 'MISSING'}")
    if boss["installed"]:
        print(f"           path={boss['path']}  {boss['version']}")
    else:
        print("           → python tools/install_domestic_search.py install-boss")
    print(f"get_jobs : {'OK' if gj['installed'] else 'MISSING'}")
    if gj["installed"]:
        print(f"           path={gj['path']}")
        print(f"           {gj['hint']}")
    else:
        print("           → python tools/install_domestic_search.py install-get-jobs")
    print()
    print("Notes")
    print("-----")
    print("- Personal / non-commercial use; check boss-cli (undeclared license) and")
    print("  get_jobs (non-commercial) before redistributing.")
    print("- This framework does NOT auto-submit applications.")
    print(f"- Vendor dir: {args.vendor}")
    # Exit 0 even if missing — status is informational.
    return 0


def cmd_install_boss(args: argparse.Namespace) -> int:
    print(f"Installing {BOSS_CLI_PIP} via pip …")
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", BOSS_CLI_PIP]
    if args.user:
        cmd.insert(4, "--user")
    proc = run(cmd, capture=False)
    if proc.returncode != 0:
        print(
            "\ninstall-boss failed. The PyPI package name may differ; clone and install "
            "from https://github.com/jackwener/boss-cli per its README.",
            file=sys.stderr,
        )
        return proc.returncode
    boss = boss_status()
    if not boss["installed"]:
        print(
            "pip reported success but `boss` is not on PATH. "
            "Try: python -m boss --help  or re-open the shell.",
            file=sys.stderr,
        )
        return 1
    print(f"boss-cli ready: {boss['path']} {boss['version']}")
    return 0


def cmd_install_get_jobs(args: argparse.Namespace) -> int:
    vendor = Path(args.vendor)
    dest = vendor_get_jobs(vendor)
    if dest.exists() and any(dest.iterdir()) and not args.force:
        print(f"get_jobs already present at {dest} (pass --force to re-clone)")
        return 0
    if not which("git"):
        print("error: git is required to clone get_jobs", file=sys.stderr)
        return 1
    vendor.mkdir(parents=True, exist_ok=True)
    if dest.exists() and args.force:
        shutil.rmtree(dest)
    print(f"Cloning {GET_JOBS_REPO} → {dest}")
    proc = run(["git", "clone", "--depth", "1", GET_JOBS_REPO, str(dest)], capture=False)
    if proc.returncode != 0:
        return proc.returncode
    print("get_jobs cloned.")
    print("Next steps (manual, heavy deps):")
    print("  1. Install JDK 21 + Gradle (see get_jobs README)")
    print("  2. Configure .env (API keys) inside the clone")
    print("  3. Run GetJobsApplication — auto-submit is optional; this repo prefers manual apply")
    print("  4. License is non-commercial — personal job search only")
    return 0


def cmd_install_all(args: argparse.Namespace) -> int:
    rc = cmd_install_boss(args)
    # get_jobs is optional/heavy; still try clone
    rc2 = cmd_install_get_jobs(args)
    return rc or rc2


def cmd_smoke(args: argparse.Namespace) -> int:
    """Offline-friendly smoke: validate this installer + optional tools if present."""
    failures: list[str] = []

    # Self-check: this script is importable / runnable
    if not Path(__file__).is_file():
        failures.append("install_domestic_search.py missing")

    # Optional: boss
    boss = boss_status()
    if boss["installed"]:
        path = boss["path"]
        if path and path != "python -m boss":
            proc = run([path, "--help"])
            if proc.returncode != 0:
                failures.append("boss --help failed")
            else:
                print("smoke: boss --help OK")
        else:
            proc = run([sys.executable, "-m", "boss", "--help"])
            if proc.returncode != 0:
                failures.append("python -m boss --help failed")
            else:
                print("smoke: python -m boss --help OK")
    else:
        print("smoke: boss-cli not installed (skip live check; run install-boss locally)")

    # Optional: get_jobs tree
    gj = get_jobs_status(Path(args.vendor))
    if gj["installed"]:
        print(f"smoke: get_jobs present at {gj['path']}")
    else:
        print("smoke: get_jobs not cloned (skip; run install-get-jobs locally)")

    # Always verify tracker + matcher companions (core domestic loop)
    for name in ("tracker.py", "match_resume.py", "apply_assist.py"):
        tool = ROOT / "tools" / name
        if not tool.is_file():
            failures.append(f"tools/{name} missing")
            continue
        proc = run([sys.executable, str(tool), "--help"])
        if proc.returncode != 0:
            failures.append(f"tools/{name} --help failed")
        else:
            print(f"smoke: tools/{name} --help OK")

    if failures:
        print("smoke FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("smoke: OK (installer self-check; optional backends skipped if missing)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="install_domestic_search",
        description="Install / check domestic job-search backends (boss-cli, get_jobs).",
    )
    p.add_argument(
        "--vendor",
        default=str(DEFAULT_VENDOR),
        help=f"directory for cloned third-party tools (default: {DEFAULT_VENDOR})",
    )
    p.add_argument(
        "--user",
        action="store_true",
        help="pip install --user for boss-cli",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="re-clone get_jobs even if present",
    )
    sub = p.add_subparsers(dest="command", required=True)

    for name, fn, help_ in [
        ("status", cmd_status, "show install status"),
        ("install-boss", cmd_install_boss, "pip install boss-cli"),
        ("install-get-jobs", cmd_install_get_jobs, "git clone get_jobs into vendor/"),
        ("install-all", cmd_install_all, "install boss-cli + clone get_jobs"),
        ("smoke", cmd_smoke, "offline-friendly smoke checks for CI/local"),
    ]:
        sp = sub.add_parser(name, help=help_)
        sp.set_defaults(func=fn)
    return p


def main(argv: list[str] | None = None) -> int:
    # Allow env override for vendor path
    parser = build_parser()
    args = parser.parse_args(argv)
    if os.environ.get("AI_JOB_SEARCH_VENDOR"):
        args.vendor = os.environ["AI_JOB_SEARCH_VENDOR"]
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
