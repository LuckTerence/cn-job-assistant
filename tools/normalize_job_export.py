#!/usr/bin/env python3
"""Normalize third-party job exports → tracker import-jobs JSON.

Inspired by (not vendoring):
  - boss-agent-cli (MIT): {ok, data, pagination, error, hints} envelope
  - common Boss/门户 CSV column names (brandName, jobName, …)

Usage:
  python tools/normalize_job_export.py -i raw.json -o jobs.json
  python tools/normalize_job_export.py -i export.csv -o jobs.json --default-channel Boss直聘
  python tools/tracker.py import-jobs jobs.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import tracker as tr  # noqa: E402


def _load_raw(path: Path) -> object:
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        return []
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    data = json.loads(text)
    return data


def unwrap_records(data: object) -> list[dict]:
    """Accept list, {jobs}, boss-agent envelope {ok,data}, nested list."""
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if not isinstance(data, dict):
        return []
    # boss-agent-cli style envelope
    if "ok" in data and "data" in data:
        inner = data.get("data")
        if isinstance(inner, list):
            return [x for x in inner if isinstance(x, dict)]
        if isinstance(inner, dict):
            for k in ("jobs", "items", "list", "results", "records"):
                if isinstance(inner.get(k), list):
                    return [x for x in inner[k] if isinstance(x, dict)]
            return [inner]
    for k in ("jobs", "items", "data", "results", "list", "records"):
        if isinstance(data.get(k), list):
            return [x for x in data[k] if isinstance(x, dict)]
    return [data]


def normalize_file(
    path: Path,
    *,
    default_channel: str = "Boss直聘",
    default_status: str = "to_apply",
    limit: int = 0,
) -> dict:
    raw = _load_raw(path)
    records = unwrap_records(raw)
    jobs: list[dict] = []
    skipped = 0
    for rec in records:
        # Flatten one level of nesting common in agent envelopes
        if "job" in rec and isinstance(rec["job"], dict):
            merged = {**rec["job"], **{k: v for k, v in rec.items() if k != "job"}}
            rec = merged
        job = tr.normalize_job_record(
            rec,
            default_channel=default_channel,
            default_status=default_status,
        )
        if job is None:
            skipped += 1
            continue
        # Prefer relative paths as plain fields for import
        out = {
            "company": job["company"],
            "role": job["role"],
            "channel": job["channel"] or default_channel,
            "source": job["source"],
            "city": job["city"],
            "salary": job["salary"],
            "status": job["status"] or default_status,
            "notes": job.get("notes", ""),
            "education": job.get("education", ""),
            "experience": job.get("experience", ""),
        }
        jobs.append(out)
        if limit and len(jobs) >= limit:
            break
    return {
        "jobs": jobs,
        "meta": {
            "source_file": str(path),
            "parsed": len(records),
            "normalized": len(jobs),
            "skipped": skipped,
            "adapter": "normalize_job_export.py",
            "inspired_by": [
                "boss-agent-cli JSON envelope (MIT)",
                "portal CSV aliases",
            ],
        },
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Normalize Boss/agent/CSV job exports → import-jobs JSON"
    )
    p.add_argument("-i", "--input", required=True, help="raw JSON/CSV/envelope")
    p.add_argument("-o", "--output", required=True, help="jobs.json for import-jobs")
    p.add_argument("--default-channel", default="Boss直聘")
    p.add_argument("--default-status", default="to_apply")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--json-meta", action="store_true", help="print meta to stdout")
    args = p.parse_args(argv)

    src = Path(args.input)
    if not src.is_file():
        alt = ROOT / args.input
        if alt.is_file():
            src = alt
        else:
            print(f"error: not found: {args.input}", file=sys.stderr)
            return 2

    result = normalize_file(
        src,
        default_channel=args.default_channel,
        default_status=args.default_status,
        limit=args.limit,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"jobs": result["jobs"]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    meta = result["meta"]
    print(
        f"normalized {meta['normalized']}/{meta['parsed']} "
        f"(skipped {meta['skipped']}) → {out}"
    )
    if meta["normalized"] == 0:
        print(tr.IMPORT_FIELD_HINT, file=sys.stderr)
        return 1
    print("next: python tools/tracker.py import-jobs", out)
    print("  or: python tools/flow.py shortlist --jobs", out)
    if args.json_meta:
        print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
