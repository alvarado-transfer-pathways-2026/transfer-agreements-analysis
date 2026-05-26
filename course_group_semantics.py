from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any


NOT_ARTICULATED = "Not Articulated"


def normalize_cell(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def course_group_columns(row_or_columns: Mapping[str, Any] | Iterable[str]) -> list[str]:
    columns = row_or_columns.keys() if hasattr(row_or_columns, "keys") else row_or_columns

    def index(name: str) -> int:
        match = re.search(r"(\d+)$", str(name))
        return int(match.group(1)) if match else 0

    return sorted(
        [str(name) for name in columns if str(name).startswith("Courses Group")],
        key=index,
    )


def parse_course_group_cell(cell: Any) -> tuple[str, ...] | None:
    value = normalize_cell(cell)
    if not value or value.lower() in {"nan", "none"} or value == NOT_ARTICULATED:
        return None
    courses = tuple(normalize_cell(course) for course in value.split(";") if normalize_cell(course))
    return courses or None


def articulated_options(row: Mapping[str, Any]) -> list[tuple[str, ...]]:
    options = []
    for column in course_group_columns(row):
        option = parse_course_group_cell(row.get(column, "") if hasattr(row, "get") else "")
        if option:
            options.append(option)
    return options


def is_articulated(row: Mapping[str, Any]) -> bool:
    return bool(articulated_options(row))


def best_option(row: Mapping[str, Any]) -> tuple[str, ...] | None:
    options = articulated_options(row)
    if not options:
        return None
    return min(options, key=lambda option: (len(option), option))


def best_option_course_count(row: Mapping[str, Any]) -> int | None:
    option = best_option(row)
    return len(option) if option else None


def option_is_satisfied(option: Iterable[str], completed_courses: Iterable[str]) -> bool:
    completed = {normalize_cell(course) for course in completed_courses}
    return all(normalize_cell(course) in completed for course in option)


def missing_courses(option: Iterable[str], completed_courses: Iterable[str]) -> tuple[str, ...]:
    completed = {normalize_cell(course) for course in completed_courses}
    return tuple(course for course in option if normalize_cell(course) not in completed)


def satisfied_option(
    options: Iterable[Iterable[str]],
    selected_courses: Iterable[str],
) -> tuple[str, ...] | None:
    selected = {normalize_cell(course) for course in selected_courses}
    satisfied = [
        tuple(option)
        for option in options
        if all(normalize_cell(course) in selected for course in option)
    ]
    if not satisfied:
        return None
    return min(satisfied, key=lambda option: (len(option), option))


def greedy_requirement_cover(
    requirements: Iterable[Any],
    course_options: Mapping[Any, Iterable[Iterable[str]]],
) -> tuple[set[str], dict[Any, tuple[str, ...]], set[Any]]:
    """Greedily satisfy requirements by adding complete OR options.

    Each option is an AND block: selecting one course in the option is not enough.
    The greedy score favors options that newly satisfy the most requirements per
    newly added course, then fewer added courses, then lexical option order.
    """
    uncovered = set(requirements)
    selected_courses: set[str] = set()
    req_to_option: dict[Any, tuple[str, ...]] = {}

    while uncovered:
        best_choice = None

        for req in sorted(uncovered, key=str):
            for option in sorted(
                [tuple(opt) for opt in course_options.get(req, [])],
                key=lambda opt: (len(opt), opt),
            ):
                option_set = set(option)
                added = option_set - selected_courses
                candidate_courses = selected_courses | option_set
                covered = {
                    candidate_req
                    for candidate_req in uncovered
                    if satisfied_option(course_options.get(candidate_req, []), candidate_courses)
                }
                if not covered:
                    continue

                score = (
                    len(covered) / max(1, len(added)),
                    len(covered),
                    -len(added),
                    tuple(option),
                    str(req),
                )
                if best_choice is None or score > best_choice[0]:
                    best_choice = (score, option_set)

        if best_choice is None:
            break

        selected_courses.update(best_choice[1])
        newly_satisfied = {
            req
            for req in uncovered
            if satisfied_option(course_options.get(req, []), selected_courses)
        }
        for req in newly_satisfied:
            option = satisfied_option(course_options.get(req, []), selected_courses)
            if option:
                req_to_option[req] = option
        uncovered -= newly_satisfied

    return selected_courses, req_to_option, uncovered
