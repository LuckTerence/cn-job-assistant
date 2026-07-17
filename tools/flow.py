#!/usr/bin/env python3
"""Thin orchestration for the domestic shortlist loop (v0.12+).

Does NOT reimplement business logic — only chains existing CLIs:

  import-jobs → rank → day-plan   (command: shortlist)
  quality_gate                    (command: gate) — 投前门禁
  plus thin wrappers: import / rank / day-plan / dashboard

Usage (repo root):
  python tools/flow.py shortlist --jobs examples/demo/jobs_sample.json --track internet
  python tools/flow.py ingest -i boss_raw.json   # normalize + import
  python tools/flow.py rank --track internet
  python tools/flow.py day-plan --limit 3
  python tools/flow.py report                  # weekly-report + funnel
  python tools/flow.py gate --resume r.md --jd j.md [--export-pdf]
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
NORMALIZE = ROOT / "tools" / "normalize_job_export.py"
GATE = ROOT / "tools" / "quality_gate.py"


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


def cmd_ingest(args: argparse.Namespace) -> int:
    """normalize third-party export → import-jobs."""
    csv = args.csv or None
    raw = str(Path(args.input))
    out = str(Path(args.output or "jobs.normalized.json"))
    rc = _run(
        [
            PY,
            str(NORMALIZE),
            "-i",
            raw,
            "-o",
            out,
            "--default-channel",
            args.default_channel or "Boss直聘",
        ]
    )
    if rc != 0:
        return rc
    return _run(
        _tracker(
            [
                "import-jobs",
                out,
                *(["--default-channel", args.default_channel] if args.default_channel else []),
            ],
            csv,
        )
    )


def cmd_report(args: argparse.Namespace) -> int:
    """weekly-report + funnel + match-outcome (human cockpit)."""
    csv = args.csv or None
    rc = _run(_tracker(["weekly-report"], csv))
    if rc != 0:
        return rc
    print()
    rc = _run(_tracker(["funnel"], csv))
    if rc != 0:
        return rc
    print()
    return _run(_tracker(["match-outcome"], csv))


def cmd_shortlist(args: argparse.Namespace) -> int:
    """import-jobs (optional) → rank → day-plan."""
    csv = args.csv or None
    if args.raw:
        # normalize first
        out = str(Path(args.jobs or "jobs.normalized.json"))
        rc = _run(
            [
                PY,
                str(NORMALIZE),
                "-i",
                str(Path(args.raw)),
                "-o",
                out,
                "--default-channel",
                args.default_channel or "Boss直聘",
            ]
        )
        if rc != 0:
            return rc
        args.jobs = out
    if args.jobs and not args.skip_import:
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
    elif args.jobs and args.skip_import:
        print(
            "note: --skip-import set; not importing --jobs (rank existing only)",
            file=sys.stderr,
        )
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


def cmd_gate(args: argparse.Namespace) -> int:
    """Forward to quality_gate.py (pre-submit match + integrity + ATS)."""
    cmd = [PY, str(GATE), "--resume", args.resume, "--jd", args.jd]
    if args.cover:
        cmd.extend(["--cover", args.cover])
    if args.profile:
        cmd.extend(["--profile", args.profile])
    if args.pdf:
        cmd.extend(["--pdf", args.pdf])
    if args.export_pdf:
        cmd.append("--export-pdf")
    if args.template:
        cmd.extend(["--template", args.template])
    if args.track:
        cmd.extend(["--track", args.track])
    if args.expected:
        cmd.extend(["--expected-salary", args.expected])
    if args.force:
        cmd.append("--force")
    if args.force_hard:
        cmd.append("--force-hard")
    if getattr(args, "min_score", None) is not None:
        cmd.extend(["--min-score", str(args.min_score)])
    if getattr(args, "min_coverage", None) is not None:
        cmd.extend(["--min-coverage", str(args.min_coverage)])
    if getattr(args, "no_salary", False):
        cmd.append("--no-salary")
    if getattr(args, "zh_only", False):
        cmd.append("--zh-only")
    if args.out:
        cmd.extend(["--out", args.out])
    if args.brief_out:
        cmd.extend(["--brief-out", args.brief_out])
    if args.json:
        cmd.append("--json")
    return _run(cmd)


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
    sl.add_argument(
        "--raw",
        default="",
        help="third-party export (boss-agent envelope/CSV); normalize then import",
    )
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

    ing = sub.add_parser("ingest", help="normalize export → import-jobs")
    ing.add_argument("-i", "--input", required=True, help="raw JSON/CSV/envelope")
    ing.add_argument("-o", "--output", default="jobs.normalized.json")
    ing.add_argument("--default-channel", default="Boss直聘")
    ing.set_defaults(func=cmd_ingest)

    rep = sub.add_parser("report", help="weekly-report + funnel")
    rep.set_defaults(func=cmd_report)

    gt = sub.add_parser(
        "gate",
        help="投前质量门禁 → quality_gate.py（匹配+诚信+ATS）",
    )
    gt.add_argument("--resume", required=True)
    gt.add_argument("--jd", required=True)
    gt.add_argument("--cover", default="")
    gt.add_argument("--profile", default="")
    gt.add_argument("--pdf", default="")
    gt.add_argument("--export-pdf", action="store_true")
    gt.add_argument("--template", default="classic")
    gt.add_argument("--track", default="")
    gt.add_argument("--expected", default="", help="expected salary e.g. 25-40K")
    gt.add_argument("--force", action="store_true")
    gt.add_argument("--force-hard", action="store_true")
    gt.add_argument("--min-score", type=float, default=None)
    gt.add_argument("--min-coverage", type=float, default=None)
    gt.add_argument("--no-salary", action="store_true")
    gt.add_argument("--zh-only", action="store_true")
    gt.add_argument("--out", default="")
    gt.add_argument("--brief-out", default="")
    gt.add_argument("--json", action="store_true")
    gt.set_defaults(func=cmd_gate)

    for name, help_ in (
        ("import", "alias: needs jobs path as first forward arg — prefer shortlist"),
        ("rank", "wrapper: tracker rank …"),
        ("day-plan", "wrapper: tracker day-plan …"),
        ("dashboard", "wrapper: tracker dashboard …"),
        ("today", "wrapper: tracker today …"),
        ("weekly-report", "wrapper: tracker weekly-report"),
        ("funnel", "wrapper: tracker funnel"),
    ):
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("forward_args", nargs=argparse.REMAINDER, default=[])
        fwd = {
            "import": "import-jobs",
            "weekly-report": "weekly-report",
            "funnel": "funnel",
        }.get(name, name)
        sp.set_defaults(func=cmd_passthrough, forward=fwd)

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
