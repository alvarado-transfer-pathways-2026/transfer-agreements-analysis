from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

from .export_filtered_from_raw import write_filtered_csv
from .export_json_from_filtered import write_json_for_cc
from .export_results_from_assist_api import export_cc
from .verify_all_assist import REPORT_DIR


DEFAULT_IMPACT_CSV = REPORT_DIR / "filtered_impact.csv"


def selected_rows(
    path: Path,
    *,
    severity: str,
    root_cause: str,
    filtered_impact: str,
) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return [
        row
        for row in rows
        if row.get("research_severity") == severity
        and row.get("root_cause") == root_cause
        and row.get("filtered_impact") == filtered_impact
    ]


def selected_colleges(rows: list[dict[str, str]]) -> list[str]:
    return sorted({row["cc"] for row in rows if row.get("cc")})


def print_selection(rows: list[dict[str, str]]) -> None:
    colleges = selected_colleges(rows)
    by_college = Counter(row["cc"] for row in rows)
    by_uc = Counter(row["uc"] for row in rows)
    by_receiving = Counter((row["uc"], row["receiving"]) for row in rows)

    print(f"Selected rows: {len(rows)}")
    print(f"Selected colleges: {len(colleges)}")

    print("\nBy UC")
    for uc, count in by_uc.most_common():
        print(f"  {uc}: {count}")

    print("\nBy receiving")
    for (uc, receiving), count in by_receiving.most_common():
        print(f"  {uc} {receiving}: {count}")

    print("\nColleges")
    for college in colleges:
        print(f"  {by_college[college]:>2}  {college}")


def refresh_college(college: str, *, quiet: bool) -> None:
    if not quiet:
        print(f"\nRefreshing {college}", flush=True)
    export_cc(college, dry_run=False, verbose=not quiet)
    filtered_path = write_filtered_csv(college)
    json_path = write_json_for_cc(college)
    if not quiet:
        print(f"  WROTE {filtered_path}", flush=True)
        print(f"  WROTE {json_path}", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Batch-refresh colleges selected from filtered_impact.csv. "
            "Dry-run is the default and only prints the selected colleges."
        )
    )
    parser.add_argument("--impact-csv", type=Path, default=DEFAULT_IMPACT_CSV)
    parser.add_argument("--severity", default="high")
    parser.add_argument("--root-cause", default="flattened_or")
    parser.add_argument("--filtered-impact", default="yes")
    parser.add_argument("--write", action="store_true", help="Refresh raw results, filtered CSV, and JSON for selected colleges.")
    parser.add_argument("--limit", type=int, help="Only process the first N selected colleges.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    rows = selected_rows(
        args.impact_csv,
        severity=args.severity,
        root_cause=args.root_cause,
        filtered_impact=args.filtered_impact,
    )
    colleges = selected_colleges(rows)
    if args.limit:
        colleges = colleges[: args.limit]

    if not rows:
        print("No matching filtered-impact rows found.")
        return 1

    print_selection([row for row in rows if row.get("cc") in set(colleges)])

    if not args.write:
        print("\nDRY-RUN only. Add --write to refresh these colleges.")
        return 0

    failures = 0
    for index, college in enumerate(colleges, start=1):
        print(f"\n[{index}/{len(colleges)}] {college}", flush=True)
        try:
            refresh_college(college, quiet=args.quiet)
        except Exception as exc:
            failures += 1
            print(f"ERROR {college}: {exc}", flush=True)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
