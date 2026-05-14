from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOT_ARTICULATED = "Not Articulated"


@dataclass(frozen=True)
class AgreementRow:
    receiving: str
    sending_options: tuple[tuple[str, ...], ...]
    receiving_type: str = "Course"

    def normalized(self) -> "AgreementRow":
        return AgreementRow(
            receiving=normalize_course_text(self.receiving),
            sending_options=tuple(
                tuple(normalize_course_text(course) for course in option)
                for option in self.sending_options
            ),
            receiving_type=self.receiving_type,
        )


@dataclass(frozen=True)
class CsvIssue:
    receiving: str
    message: str
    expected: object = None
    actual: object = None
    issue_type: str = ""

    def format(self) -> str:
        label = f"{self.message} [{self.issue_type}]" if self.issue_type else self.message
        return (
            f"{self.receiving}: {label}\n"
            f"  expected: {self.expected}\n"
            f"  actual:   {self.actual}"
        )


def normalize_course_text(value: str) -> str:
    return " ".join((value or "").strip().split())


def course_group_columns(fieldnames: Iterable[str]) -> list[str]:
    def index(name: str) -> int:
        match = re.search(r"(\d+)$", name)
        return int(match.group(1)) if match else 0

    return sorted(
        [name for name in fieldnames if name.startswith("Courses Group")],
        key=index,
    )


def parse_course_group_cell(value: str) -> tuple[str, ...] | None:
    value = normalize_course_text(value)
    if not value:
        return None
    if value == NOT_ARTICULATED:
        return (NOT_ARTICULATED,)
    return tuple(
        normalize_course_text(course)
        for course in value.split(";")
        if normalize_course_text(course)
    )


def row_sending_options(row: dict[str, str]) -> tuple[tuple[str, ...], ...]:
    options = []
    for column in course_group_columns(row.keys()):
        option = parse_course_group_cell(row.get(column, ""))
        if option:
            options.append(option)
    return tuple(options)


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_issue_report(issues: list[CsvIssue]) -> str:
    if not issues:
        return "PASS: no mismatches found"
    lines = [f"FAIL: {len(issues)} mismatch(es) found"]
    lines.extend(issue.format() for issue in issues)
    return "\n\n".join(lines)


def load_expected_agreement_rows(path: Path) -> dict[str, AgreementRow]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = {}
    for item in data["rows"]:
        row = AgreementRow(
            receiving=item["receiving"],
            receiving_type=item.get("receiving_type", "Course"),
            sending_options=tuple(tuple(option) for option in item["sending_options"]),
        ).normalized()
        rows[row.receiving] = row
    return rows


def rows_by_receiving(rows: Iterable[AgreementRow]) -> dict[str, AgreementRow]:
    by_receiving: dict[str, AgreementRow] = {}
    for row in rows:
        normalized = row.normalized()
        existing = by_receiving.get(normalized.receiving)
        if existing is None:
            by_receiving[normalized.receiving] = normalized
            continue
        by_receiving[normalized.receiving] = merge_agreement_rows(existing, normalized)
    return by_receiving


def merge_agreement_rows(first: AgreementRow, second: AgreementRow) -> AgreementRow:
    first = first.normalized()
    second = second.normalized()
    if first.receiving != second.receiving:
        raise ValueError(f"Cannot merge different receiving rows: {first.receiving} != {second.receiving}")

    options: list[tuple[str, ...]] = []
    seen = set()
    for option in (*first.sending_options, *second.sending_options):
        if option in seen:
            continue
        seen.add(option)
        options.append(option)

    receiving_type = first.receiving_type
    if first.receiving_type != second.receiving_type:
        receiving_type = f"{first.receiving_type}+{second.receiving_type}"

    return AgreementRow(
        receiving=first.receiving,
        receiving_type=receiving_type,
        sending_options=tuple(options),
    )


def option_contains_not_articulated(options: tuple[tuple[str, ...], ...] | None) -> bool:
    if not options:
        return False
    return any(option == (NOT_ARTICULATED,) for option in options)


def classify_sending_mismatch(
    expected: tuple[tuple[str, ...], ...] | None,
    actual: tuple[tuple[str, ...], ...] | None,
) -> str:
    expected = expected or ()
    actual = actual or ()

    if option_contains_not_articulated(expected) or option_contains_not_articulated(actual):
        return "not_articulated_mismatch"

    if len(actual) == 1 and len(expected) > 1:
        flattened_expected = tuple(course for option in expected for course in option)
        if tuple(actual[0]) == flattened_expected:
            return "flattened_or"

    if len(expected) == 1 and len(expected[0]) > 1:
        split_expected = tuple((course,) for course in expected[0])
        if actual == split_expected:
            return "split_and"

    return "sending_options_mismatch"


def classify_agreement_row(row: AgreementRow, *, duplicate_receiving: bool = False) -> tuple[str, ...]:
    cases: list[str] = []
    options = row.sending_options

    if duplicate_receiving:
        cases.append("duplicate_receiving_requirement")

    if row.receiving_type.startswith("Series") or ";" in row.receiving:
        cases.append("multi_course_receiving_series")

    if options == ((NOT_ARTICULATED,),):
        cases.append("no_articulation")
    elif len(options) == 1 and len(options[0]) == 1:
        cases.append("single_course")
    elif len(options) == 1 and len(options[0]) > 1:
        cases.append("pure_and")
    elif len(options) > 1 and all(len(option) == 1 for option in options):
        cases.append("pure_or")
    elif len(options) > 1 and any(len(option) > 1 for option in options):
        cases.append("or_of_and_groups")

    if not cases:
        cases.append("unknown_unsupported_payload_shape")

    return tuple(cases)
