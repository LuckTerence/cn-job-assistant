#!/usr/bin/env python3
"""Thin orchestration for the domestic shortlist loop (v0.12).

Does NOT reimplement business logic — only chains existing CLIs:

  import-jobs → rank → day-plan   (command: shortlist)
  plus thin wrappers: import / rank / day-plan / dashboard

Usage (repo root):
  python tools/flow.py shortlist --jobs examples/demo/jobs_sample.json --track internet
  python tools/flow.py rank --track internet
  python tools/flow.py day-plan --limit 3
  python tools/flow.py dashboard
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
TRACKER = ROOT / "tools" / "tracker.py"


def _run(argv: list[str]) -> int:
    print(f"+ {' '.join(argv)}", file=sys.stderr)
    proc = subprocess.run(argv, cwd=str(ROOT), check=False)
    return int(proc.returncode)


def _tracker(args: list[str], csv: str | None) -> list[str]:
    cmd = [PY, str(TRACKER)]
    if csv:
        cmd.extend(["--csv", csv])
    cmd.extend(args)
    return cmd


def cmd_shortlist(args: argparse.Namespace) -> int:
    """import-jobs (optional) → rank → day-plan."""
    csv = args.csv or None
    if args.jobs:
        jobs = str(Path(args.jobs))
        rc = _run(
            _tracker(
                [
                    "import-jobs",
                    jobs,
                    *(["--default-channel", args.default_channel] if args.default_channel else []),
                ],
                csv,
            )
        )
        if rc != 0:
            return rc
    elif not args.skip_import:
        print(
            "note: no --jobs; skipping import (rank existing to_apply only)",
            file=sys.stderr,
        )

    rank_args = ["rank"]
    if args.track:
        rank_args.extend(["--track", args.track])
    if args.limit and args.limit > 0:
        rank_args.extend(["--limit", str(args.limit * 3)])
    if args.write_fit:
        rank_args.append("--write-fit")
    rc = _run(_tracker(rank_args, csv))
    if rc != 0:
        return rc

    day_args = ["day-plan", "--limit", str(args.limit or 3)]
    if args.track:
        day_args.extend(["--track", args.track])
    if args.expected:
        day_args.extend(["--expected-salary", args.expected])
    return _run(_tracker(day_args, csv))


def cmd_passthrough(args: argparse.Namespace) -> int:
    """Forward to tracker subcommand."""
    sub = args.forward
    extra = list(args.forward_args or [])
    return _run(_tracker([sub, *extra], args.csv or None))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="flow",
        description="Thin shortlist orchestration (import → rank → day-plan). No new business logic.",
    )
    p.add_argument(
        "--csv",
        default="",
        help="optional tracker CSV path (default: repo job_search_tracker.csv)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sl = sub.add_parser(
        "shortlist",
        help="import-jobs (if --jobs) → rank → day-plan",
    )
    sl.add_argument("--jobs", default="", help="jobs.json / csv for import-jobs")
    sl.add_argument("--default-channel", default="Boss直聘")
    sl.add_argument("--track", default="", help="synonym track for rank/day-plan")
    sl.add_argument("--limit", type=int, default=3, help="day-plan to_apply count")
    sl.add_argument("--write-fit", action="store_true", help="rank --write-fit")
    sl.add_argument(
        "--expected",
        default="",
        help="expected salary for day-plan flags e.g. 25-40K",
    )
    sl.add_argument(
        "--skip-import",
        action="store_true",
        help="never import even if --jobs set (debug)",
    )
    sl.set_defaults(func=cmd_shortlist)

    for name, help_ in (
        ("import", "alias: needs jobs path as first forward arg — prefer shortlist"),
        ("rank", "wrapper: tracker rank …"),
        ("day-plan", "wrapper: tracker day-plan …"),
        ("dashboard", "wrapper: tracker dashboard …"),
        ("today", "wrapper: tracker today …"),
    ):
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("forward_args", nargs=argparse.REMAINDER, default=[])
        sp.set_defaults(func=cmd_passthrough, forward=name if name != "import" else "import-jobs")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # argparse REMINDER leaves leading '--' sometimes
    if getattr(args, "forward_args", None):
        fa = list(args.forward_args)
        if fa and fa[0] == "--":
            fa = fa[1:]
        args.forward_args = fa
    if args.command == "import" and not args.forward_args:
        print("usage: python tools/flow.py import -- path/to/jobs.json [import-jobs flags]", file=sys.stderr)
        print("   or: python tools/flow.py shortlist --jobs path/to/jobs.json", file=sys.stderr)
        return 2
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
