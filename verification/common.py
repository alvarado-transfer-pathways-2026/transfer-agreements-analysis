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

    def format(self) -> str:
        return (
            f"{self.receiving}: {self.message}\n"
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
    return {row.normalized().receiving: row.normalized() for row in rows}

