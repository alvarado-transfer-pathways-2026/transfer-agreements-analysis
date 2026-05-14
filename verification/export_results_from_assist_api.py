from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .assist_parser import fetch_assist_payload, parse_assist_payload, view_by_key_from_assist_url
from .common import AgreementRow, PROJECT_ROOT
from .verify_all_assist import agreement_pairs_from_files


RESULTS_DIR = PROJECT_ROOT / "results"


@dataclass(frozen=True)
class ExportSummary:
    cc: str
    path: Path
    agreement_count: int
    row_count: int
    max_course_groups: int
    dry_run: bool


def csv_safe_cc_name(cc_name: str) -> str:
    return cc_name.replace(" ", "_")


def course_group_cell(option: tuple[str, ...]) -> str:
    return "; ".join(option)


def rows_for_pair(
    pair: dict[str, str],
    *,
    fetch_payload: Callable[[str], dict] = fetch_assist_payload,
) -> list[dict[str, object]]:
    payload = fetch_payload(view_by_key_from_assist_url(pair["url"]))
    rows = parse_assist_payload(payload)
    return [
        {
            "UC Campus": pair["uc"],
            "CC": pair["cc"],
            "UC Course Requirement": row.receiving,
            "sending_options": row.sending_options,
        }
        for row in rows.values()
    ]


def export_rows_for_cc(
    project_root: Path,
    cc_name: str,
    *,
    fetch_payload: Callable[[str], dict] = fetch_assist_payload,
    verbose: bool = False,
) -> tuple[list[dict[str, object]], int]:
    pairs = agreement_pairs_from_files(project_root, cc_name=cc_name)
    if not pairs:
        raise ValueError(f"No agreement URLs found for {cc_name}")

    exported_rows: list[dict[str, object]] = []
    for index, pair in enumerate(pairs, start=1):
        if verbose:
            print(f"  [{index}/{len(pairs)}] Fetching {pair['uc']}...", flush=True)
        pair_rows = rows_for_pair(pair, fetch_payload=fetch_payload)
        exported_rows.extend(pair_rows)
        if verbose:
            print(f"    rows={len(pair_rows)}", flush=True)

    return exported_rows, len(pairs)


def write_results_csv(path: Path, cc_name: str, rows: list[dict[str, object]]) -> int:
    max_groups = max((len(row["sending_options"]) for row in rows), default=0)
    fieldnames = [
        "UC Campus",
        "CC",
        "UC Course Requirement",
        *[f"Courses Group {index}" for index in range(1, max_groups + 1)],
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            output = {
                "UC Campus": row["UC Campus"],
                "CC": cc_name,
                "UC Course Requirement": row["UC Course Requirement"],
            }
            for index, option in enumerate(row["sending_options"], start=1):
                output[f"Courses Group {index}"] = course_group_cell(option)
            for fieldname in fieldnames:
                output.setdefault(fieldname, "")
            writer.writerow(output)

    return max_groups


def export_cc(
    cc_name: str,
    *,
    project_root: Path = PROJECT_ROOT,
    output_dir: Path = RESULTS_DIR,
    dry_run: bool = True,
    fetch_payload: Callable[[str], dict] = fetch_assist_payload,
    verbose: bool = False,
) -> ExportSummary:
    rows, agreement_count = export_rows_for_cc(
        project_root,
        cc_name,
        fetch_payload=fetch_payload,
        verbose=verbose,
    )
    path = output_dir / f"{csv_safe_cc_name(cc_name)}_allUC.csv"
    max_groups = max((len(row["sending_options"]) for row in rows), default=0)

    if not dry_run:
        max_groups = write_results_csv(path, cc_name, rows)

    return ExportSummary(
        cc=cc_name,
        path=path,
        agreement_count=agreement_count,
        row_count=len(rows),
        max_course_groups=max_groups,
        dry_run=dry_run,
    )


def selected_ccs(project_root: Path, *, cc_name: str | None, all_ccs: bool) -> list[str]:
    if cc_name:
        return [cc_name]
    if not all_ccs:
        raise ValueError("Select a college with --cc or export every college with --all.")
    agreement_files = sorted((project_root / "cc_agreements").glob("*/agreements.txt"))
    return [path.parent.name.replace("_", " ") for path in agreement_files]


def print_summary(summary: ExportSummary) -> None:
    action = "DRY-RUN" if summary.dry_run else "WROTE"
    print(
        f"{action} {summary.cc}: agreements={summary.agreement_count} "
        f"rows={summary.row_count} max_course_groups={summary.max_course_groups} "
        f"path={summary.path}",
        flush=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Export results/*_allUC.csv directly from the ASSIST agreement API. "
            "Dry-run is the default so generated row counts can be inspected before replacing files."
        )
    )
    parser.add_argument("--cc", help="Community college name, e.g. 'De Anza College'")
    parser.add_argument("--all", action="store_true", help="Export every college in cc_agreements.")
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument(
        "--write",
        action="store_false",
        dest="dry_run",
        help="Write CSV files. Without this flag, the command only prints planned output.",
    )
    parser.add_argument("--quiet", action="store_true", help="Hide per-agreement fetch progress.")
    args = parser.parse_args(argv)

    try:
        ccs = selected_ccs(PROJECT_ROOT, cc_name=args.cc, all_ccs=args.all)
    except ValueError as exc:
        print(exc)
        return 1

    failures = 0
    for index, cc_name in enumerate(ccs, start=1):
        if not args.quiet:
            print(f"[{index}/{len(ccs)}] Exporting {cc_name} from ASSIST API...", flush=True)
        try:
            summary = export_cc(
                cc_name,
                output_dir=args.output_dir,
                dry_run=args.dry_run,
                verbose=not args.quiet,
            )
            print_summary(summary)
        except Exception as exc:
            failures += 1
            print(f"ERROR {cc_name}: {exc}", flush=True)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
