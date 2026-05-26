from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from .common import CsvIssue, NOT_ARTICULATED, PROJECT_ROOT, course_group_columns, load_csv_rows, normalize_course_text, row_sending_options, write_issue_report
from course_group_semantics import best_option_course_count


BASE_COLUMNS = ["College Name", "UC Name", "Group ID", "Set ID", "Num Required", "Receiving"]


def normalize_requirement_value(value: str) -> str:
    return " ".join(str(value).strip().split())


def normalize_receiving_requirement(value: str) -> str:
    parts = [normalize_requirement_value(part) for part in str(value).split(";")]
    parts = [part for part in parts if part]
    return "; ".join(sorted(parts)) if len(parts) > 1 else (parts[0] if parts else "")


def load_current_requirement_keys(project_root: Path) -> set[tuple[str, str, str, str]] | None:
    path = project_root / "scraping" / "files" / "course_reqs.json"
    if not path.exists():
        return None
    requirements = json.loads(path.read_text(encoding="utf-8")).get("UC_REQUIREMENTS", {})
    keys = set()
    for uc_name, groups in requirements.items():
        for group_id, options in groups.items():
            by_set: dict[str, list[str]] = defaultdict(list)
            for option in options:
                if len(option) < 2:
                    continue
                receiving, set_id = option[0], option[1]
                by_set[normalize_requirement_value(set_id)].append(normalize_requirement_value(receiving))
                keys.add((
                    normalize_requirement_value(uc_name),
                    normalize_requirement_value(group_id),
                    normalize_requirement_value(set_id),
                    normalize_receiving_requirement(receiving),
                ))
            for set_id, receiving_courses in by_set.items():
                keys.add((
                    normalize_requirement_value(uc_name),
                    normalize_requirement_value(group_id),
                    set_id,
                    normalize_receiving_requirement("; ".join(receiving_courses)),
                ))
    return keys


def normalize_college_name(name: str) -> str:
    return " ".join(str(name).split()).casefold()


def safe_district_filename(district: str) -> str:
    return district.replace(" ", "_").replace("/", "_") + ".csv"


def count_total_courses(row: dict[str, str]) -> int:
    count = best_option_course_count(row)
    return count if count is not None else sys.maxsize


def district_colleges(project_root: Path, district: str) -> list[str]:
    path = project_root / "creating_districts" / "districts.json"
    districts = json.loads(path.read_text(encoding="utf-8"))["districts"]
    return districts[district]["colleges"]


def filtered_rows_for_college(project_root: Path, college: str) -> list[dict[str, str]]:
    path = project_root / "filtered_results" / f"{college.replace(' ', '_')}_filtered.csv"
    if not path.exists():
        target_name = normalize_college_name(college)
        for candidate in (project_root / "filtered_results").glob("*_filtered.csv"):
            candidate_name = candidate.name.replace("_filtered.csv", "").replace("_", " ")
            if normalize_college_name(candidate_name) == target_name:
                path = candidate
                break

    rows = []
    for row in load_csv_rows(path):
        row = dict(row)
        row["College Name"] = college
        rows.append(row)
    return rows


def district_group_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        row["UC Name"],
        row["Group ID"],
        row["Set ID"],
        normalize_course_text(row["Receiving"]),
    )


def current_requirement_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        normalize_requirement_value(row.get("UC Name", "")),
        normalize_requirement_value(row.get("Group ID", "")),
        normalize_requirement_value(row.get("Set ID", "")),
        normalize_receiving_requirement(row.get("Receiving", "")),
    )


def normalize_district_row(row: dict[str, str]) -> tuple:
    return (
        row.get("College Name", ""),
        row["UC Name"],
        row["Group ID"],
        row["Set ID"],
        str(row["Num Required"]),
        normalize_course_text(row["Receiving"]),
        tuple(normalize_course_text("; ".join(option)) for option in row_sending_options(row)),
    )


def blank_course_group_columns(row: dict[str, str]) -> dict[str, str]:
    cleaned = dict(row)
    group_columns = course_group_columns(cleaned.keys())
    for column in group_columns:
        cleaned[column] = ""
    if group_columns:
        cleaned[group_columns[0]] = NOT_ARTICULATED
    return cleaned


def recompute_district_rows(project_root: Path, district: str) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    current_requirement_keys = load_current_requirement_keys(project_root)
    for college in district_colleges(project_root, district):
        for row in filtered_rows_for_college(project_root, college):
            if current_requirement_keys is not None and current_requirement_key(row) not in current_requirement_keys:
                continue
            grouped[district_group_key(row)].append(row)

    expected = []
    for key in sorted(grouped):
        rows = grouped[key]
        articulated = [
            row for row in rows
            if row_sending_options(row) and row_sending_options(row)[0] != (NOT_ARTICULATED,)
        ]
        if articulated:
            expected.append(sorted(articulated, key=count_total_courses)[0])
        else:
            row = blank_course_group_columns(rows[0])
            row["College Name"] = NOT_ARTICULATED
            expected.append(row)
    return expected


def acceptable_district_rows(project_root: Path, district: str) -> dict[tuple[str, str, str, str], set[tuple]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    current_requirement_keys = load_current_requirement_keys(project_root)
    for college in district_colleges(project_root, district):
        for row in filtered_rows_for_college(project_root, college):
            if current_requirement_keys is not None and current_requirement_key(row) not in current_requirement_keys:
                continue
            grouped[district_group_key(row)].append(row)

    acceptable = {}
    for key, rows in grouped.items():
        articulated = [
            row for row in rows
            if row_sending_options(row) and row_sending_options(row)[0] != (NOT_ARTICULATED,)
        ]
        if articulated:
            min_courses = min(count_total_courses(row) for row in articulated)
            acceptable[key] = {
                normalize_district_row(row)
                for row in articulated
                if count_total_courses(row) == min_courses
            }
        else:
            row = blank_course_group_columns(rows[0])
            row["College Name"] = NOT_ARTICULATED
            acceptable[key] = {normalize_district_row(row)}
    return acceptable


def verify_district_csv(district: str, *, project_root: Path = PROJECT_ROOT) -> list[CsvIssue]:
    expected_by_key = acceptable_district_rows(project_root, district)
    actual_path = project_root / "district_csvs" / safe_district_filename(district)
    actual_by_key = {
        district_group_key(row): normalize_district_row(row)
        for row in load_csv_rows(actual_path)
    }

    issues: list[CsvIssue] = []
    for key in sorted(set(expected_by_key) | set(actual_by_key)):
        expected_rows = expected_by_key.get(key)
        actual_row = actual_by_key.get(key)
        receiving = key[3]
        if expected_rows is None:
            issues.append(CsvIssue(receiving, "unexpected district row", None, actual_row))
            continue
        if actual_row is None:
            issues.append(CsvIssue(receiving, "missing district row", expected_rows, None))
            continue
        if actual_row not in expected_rows:
            issues.append(CsvIssue(receiving, "district row is not an acceptable best row", expected_rows, actual_row))
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify district CSVs from filtered_results CSVs.")
    parser.add_argument("--district", required=True)
    args = parser.parse_args(argv)

    issues = verify_district_csv(args.district)
    print(write_issue_report(issues))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
