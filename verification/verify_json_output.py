from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from .common import CsvIssue, PROJECT_ROOT, load_csv_rows, normalize_course_text, row_sending_options, write_issue_report


def college_json_key(cc_name: str) -> str:
    return "_".join(word.capitalize() for word in cc_name.split())


def parse_course(raw: str) -> tuple[str, float | None]:
    raw = normalize_course_text(raw)
    match = re.match(r"(.+?)\s*\(([\d.]+)\)$", raw)
    if not match:
        return raw, None
    course, units = match.groups()
    return normalize_course_text(course), float(units)


def parse_receiving(receiving_raw: str) -> tuple[str, ...]:
    return tuple(
        normalize_course_text(course)
        for course in receiving_raw.split(";")
        if normalize_course_text(course)
    )


def merge_unique_groups(existing: list[tuple[tuple[str, float | None], ...]], new: list[tuple[tuple[str, float | None], ...]]) -> list[tuple[tuple[str, float | None], ...]]:
    merged = []
    seen = set()
    for group in existing + new:
        if group in seen:
            continue
        seen.add(group)
        merged.append(group)
    return merged


def requirement_signature(uc: str, requirement_key: str, entry: dict) -> tuple:
    return (
        uc,
        requirement_key,
        entry["set_id"],
        int(entry["num_required"]),
        tuple(entry["receiving"]),
        tuple(entry["course_groups"]),
    )


def recompute_json_signatures(project_root: Path, cc_name: str) -> set[tuple]:
    filtered_path = project_root / "filtered_results" / f"{cc_name.replace(' ', '_')}_filtered.csv"
    requirements: dict[tuple[str, str], dict] = {}

    for row in load_csv_rows(filtered_path):
        uc = row["UC Name"].strip()
        requirement_key = row["Group ID"].strip()
        set_id = row["Set ID"].strip()
        try:
            num_required = int(row["Num Required"])
        except ValueError:
            num_required = 1

        receiving = parse_receiving(row.get("Receiving", ""))
        course_groups = [
            tuple(parse_course(course) for course in option)
            for option in row_sending_options(row)
            if option and option != ("Not Articulated",)
        ]
        if not course_groups:
            continue

        key = (uc, requirement_key)
        existing = requirements.get(key)
        if existing and existing["set_id"] != set_id:
            key = (uc, f"{requirement_key}_{set_id}")
            existing = requirements.get(key)

        if existing:
            existing["num_required"] = max(existing["num_required"], num_required)
            existing["course_groups"] = merge_unique_groups(existing["course_groups"], course_groups)
            for course in receiving:
                if course not in existing["receiving"]:
                    existing["receiving"].append(course)
            continue

        requirements[key] = {
            "set_id": set_id,
            "num_required": num_required,
            "receiving": list(receiving),
            "course_groups": course_groups,
        }

    return {
        requirement_signature(uc, requirement_key, entry)
        for (uc, requirement_key), entry in requirements.items()
    }


def actual_json_signatures(project_root: Path, cc_name: str) -> set[tuple]:
    json_path = project_root / "articulated_courses_json" / f"{college_json_key(cc_name)}_articulation.json"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    college_data = data[college_json_key(cc_name)]
    signatures = set()

    for uc, requirements in college_data.items():
        for requirement_key, entry in requirements.items():
            receiving = []
            if entry.get("receiving_courses"):
                receiving = [normalize_course_text(course) for course in entry["receiving_courses"]]
            elif entry.get("receiving_course"):
                receiving = [normalize_course_text(entry["receiving_course"])]

            course_groups = []
            for group in entry.get("course_groups", []):
                course_groups.append(
                    tuple(
                        (
                            normalize_course_text(course.get("course", "")),
                            course.get("units"),
                        )
                        for course in group
                    )
                )

            signatures.add(
                requirement_signature(
                    uc,
                    requirement_key,
                    {
                        "set_id": entry["set_id"],
                        "num_required": entry["num_required"],
                        "receiving": receiving,
                        "course_groups": course_groups,
                    },
                )
            )

    return signatures


def verify_json_output(cc_name: str, *, project_root: Path = PROJECT_ROOT) -> list[CsvIssue]:
    expected = recompute_json_signatures(project_root, cc_name)
    actual = actual_json_signatures(project_root, cc_name)

    issues: list[CsvIssue] = []
    for row in sorted(expected - actual):
        issues.append(CsvIssue(row[1], "missing JSON requirement", row, None, "json_missing_requirement"))
    for row in sorted(actual - expected):
        issues.append(CsvIssue(row[1], "unexpected JSON requirement", None, row, "json_unexpected_requirement"))
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify articulated_courses_json output from filtered_results.")
    parser.add_argument("--cc", required=True)
    args = parser.parse_args(argv)

    issues = verify_json_output(args.cc)
    print(write_issue_report(issues))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
