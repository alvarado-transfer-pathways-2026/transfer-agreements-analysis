#!/usr/bin/env python3
"""
Validate that district-level COURSE_GROUPS patterns cover every requirement
group key found in scraping/files/course_reqs.json.
"""

import argparse
import ast
import json
from pathlib import Path
from typing import Dict, List, Tuple


def _load_course_groups(helper_path: Path) -> Dict[str, Dict[str, List[str]]]:
    module = ast.parse(helper_path.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "COURSE_GROUPS":
                    return ast.literal_eval(node.value)
    raise ValueError(f"Could not find COURSE_GROUPS in {helper_path}")


def _collect_requirement_group_ids(course_reqs_path: Path) -> List[str]:
    data = json.loads(course_reqs_path.read_text(encoding="utf-8"))
    uc_reqs = data.get("UC_REQUIREMENTS", {})
    group_ids = {
        group_id
        for uc_map in uc_reqs.values()
        for group_id in uc_map.keys()
    }
    return sorted(group_ids)


def _match_categories(
    group_id: str,
    course_groups: Dict[str, Dict[str, List[str]]],
) -> List[str]:
    lowered = group_id.lower()
    return [
        category
        for category, metadata in course_groups.items()
        if any(pattern in lowered for pattern in metadata.get("patterns", []))
    ]


def validate(
    helper_path: Path,
    course_reqs_path: Path,
) -> Tuple[List[str], List[Tuple[str, List[str]]]]:
    course_groups = _load_course_groups(helper_path)
    group_ids = _collect_requirement_group_ids(course_reqs_path)

    unmatched: List[str] = []
    ambiguous: List[Tuple[str, List[str]]] = []

    for group_id in group_ids:
        matches = _match_categories(group_id, course_groups)
        if not matches:
            unmatched.append(group_id)
        elif len(matches) > 1:
            ambiguous.append((group_id, matches))

    print(f"Validated {len(group_ids)} unique group IDs from {course_reqs_path}.")
    print(f"Unmatched group IDs: {len(unmatched)}")
    print(f"Ambiguous group IDs: {len(ambiguous)}")

    if unmatched:
        print("\nUnmatched:")
        for group_id in unmatched:
            print(f"  - {group_id}")

    if ambiguous:
        print("\nAmbiguous:")
        for group_id, matches in ambiguous:
            joined = ", ".join(matches)
            print(f"  - {group_id}: {joined}")

    return unmatched, ambiguous


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Validate COURSE_GROUPS coverage against course_reqs.json."
    )
    parser.add_argument(
        "--helper",
        type=Path,
        default=project_root / "question_2-3" / "district-level" / "helper.py",
        help="Path to helper.py containing COURSE_GROUPS.",
    )
    parser.add_argument(
        "--course-reqs",
        type=Path,
        default=project_root / "scraping" / "files" / "course_reqs.json",
        help="Path to course_reqs.json.",
    )
    args = parser.parse_args()

    unmatched, ambiguous = validate(args.helper, args.course_reqs)
    return 1 if unmatched or ambiguous else 0


if __name__ == "__main__":
    raise SystemExit(main())
