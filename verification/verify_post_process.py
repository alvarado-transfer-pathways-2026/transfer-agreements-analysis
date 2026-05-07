from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scraping.files.course_reqs import UC_REQUIREMENTS

from .common import CsvIssue, PROJECT_ROOT, load_csv_rows, row_sending_options, write_issue_report, normalize_course_text


UC_ABBREVIATIONS = {
    "University of California San Diego": "UCSD",
    "University of California Irvine": "UCI",
    "University of California Davis": "UCD",
    "University of California Riverside": "UCR",
    "University of California Los Angeles": "UCLA",
    "University of California Berkeley": "UCB",
    "University of California Merced": "UCM",
    "University of California Santa Cruz": "UCSC",
    "University of California Santa Barbara": "UCSB",
}


def receiving_tokens(receiving_course: str) -> set[str]:
    return {
        normalize_course_text(token).upper()
        for token in (receiving_course or "").split(";")
        if normalize_course_text(token)
    }


def match_requirement(uc_abbr: str, receiving_course: str) -> list[tuple[str, str, int]]:
    receiving_codes = receiving_tokens(receiving_course)
    if not receiving_codes:
        return []

    matches = []
    for group_id, entries in UC_REQUIREMENTS.get(uc_abbr, {}).items():
        if not isinstance(entries[0], list):
            entries = [entries]
        matched_by_set: dict[tuple[str, str], list[int]] = {}
        for course_code, set_id, num_required in entries:
            if normalize_course_text(course_code).upper() in receiving_codes:
                key = (group_id, set_id)
                if key not in matched_by_set:
                    matched_by_set[key] = [int(num_required), 1]
                else:
                    matched_by_set[key][1] += 1

        for (gid, sid), (configured_required, matched_count) in matched_by_set.items():
            matches.append((gid, sid, min(configured_required, matched_count)))

    return matches


def recompute_filtered_rows(project_root: Path, cc_name: str) -> list[dict[str, str]]:
    raw_path = project_root / "results" / f"{cc_name.replace(' ', '_')}_allUC.csv"
    rows = []
    seen = set()
    max_groups = 0

    for raw_row in load_csv_rows(raw_path):
        uc_abbr = UC_ABBREVIATIONS.get(raw_row["UC Campus"].strip())
        if not uc_abbr:
            continue

        receiving = raw_row["UC Course Requirement"].strip()
        if not receiving or receiving == "Not Articulated":
            continue

        options = ["; ".join(option) for option in row_sending_options(raw_row)]
        matches = match_requirement(uc_abbr, receiving)
        for group_id, set_id, num_required in matches:
            key = (uc_abbr, group_id, set_id, num_required, receiving, tuple(options))
            if key in seen:
                continue
            seen.add(key)
            max_groups = max(max_groups, len(options))
            rows.append(
                {
                    "UC Name": uc_abbr,
                    "Group ID": group_id,
                    "Set ID": set_id,
                    "Num Required": str(num_required),
                    "Receiving": receiving,
                    "_options": options,
                }
            )

    for row in rows:
        options = row.pop("_options")
        for index in range(max_groups):
            row[f"Courses Group {index + 1}"] = options[index] if index < len(options) else ""
    return rows


def normalize_filtered_row(row: dict[str, str]) -> tuple:
    groups = tuple(
        normalize_course_text("; ".join(option) if isinstance(option, tuple) else option)
        for option in row_sending_options(row)
    )
    return (
        row["UC Name"],
        row["Group ID"],
        row["Set ID"],
        str(row["Num Required"]),
        normalize_course_text(row["Receiving"]),
        groups,
    )


def verify_post_process(cc_name: str, *, project_root: Path = PROJECT_ROOT) -> list[CsvIssue]:
    expected = {normalize_filtered_row(row) for row in recompute_filtered_rows(project_root, cc_name)}
    actual_path = project_root / "filtered_results" / f"{cc_name.replace(' ', '_')}_filtered.csv"
    actual = {normalize_filtered_row(row) for row in load_csv_rows(actual_path)}

    issues: list[CsvIssue] = []
    for row in sorted(expected - actual):
        issues.append(CsvIssue(row[4], "missing filtered row", row, None))
    for row in sorted(actual - expected):
        issues.append(CsvIssue(row[4], "unexpected filtered row", None, row))
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify filtered_results CSVs from raw results CSVs.")
    parser.add_argument("--cc", required=True)
    args = parser.parse_args(argv)

    issues = verify_post_process(args.cc)
    print(write_issue_report(issues))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())

