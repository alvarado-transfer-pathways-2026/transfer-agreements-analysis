from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .assist_parser import agreement_url_for_pair, fetch_assist_payload, parse_assist_payload, view_by_key_from_assist_url
from .common import (
    AgreementRow,
    CsvIssue,
    PROJECT_ROOT,
    classify_sending_mismatch,
    load_csv_rows,
    load_expected_agreement_rows,
    row_sending_options,
    rows_by_receiving,
    normalize_course_text,
    write_issue_report,
)


UC_FIXTURES = {
    ("De Anza College", "University of California San Diego"):
        PROJECT_ROOT / "verification" / "fixtures" / "assist_raw" / "de_anza_ucsd_expected.json",
    ("De Anza College", "University of California Irvine"):
        PROJECT_ROOT / "verification" / "fixtures" / "assist_raw" / "de_anza_uci_expected.json",
}


def raw_csv_row_list(project_root: Path, cc_name: str, uc_name: str) -> list[AgreementRow]:
    path = project_root / "results" / f"{cc_name.replace(' ', '_')}_allUC.csv"
    rows = []
    for csv_row in load_csv_rows(path):
        if csv_row.get("UC Campus") != uc_name:
            continue
        rows.append(
            AgreementRow(
                receiving=csv_row["UC Course Requirement"],
                sending_options=row_sending_options(csv_row),
            )
        )
    return rows


def raw_csv_rows(project_root: Path, cc_name: str, uc_name: str) -> dict[str, AgreementRow]:
    rows = raw_csv_row_list(project_root, cc_name, uc_name)
    return rows_by_receiving(rows)


def compare_rows(expected: dict[str, AgreementRow], actual: dict[str, AgreementRow]) -> list[CsvIssue]:
    issues: list[CsvIssue] = []
    for receiving in sorted(set(expected) | set(actual)):
        expected_row = expected.get(receiving)
        actual_row = actual.get(receiving)
        if expected_row is None:
            issues.append(
                CsvIssue(
                    receiving,
                    "unexpected raw CSV row",
                    None,
                    actual_row.sending_options,
                    "unexpected_row",
                )
            )
            continue
        if actual_row is None:
            issues.append(
                CsvIssue(
                    receiving,
                    "missing raw CSV row",
                    expected_row.sending_options,
                    None,
                    "missing_row",
                )
            )
            continue
        if expected_row.sending_options != actual_row.sending_options:
            issue_type = classify_sending_mismatch(
                expected_row.sending_options,
                actual_row.sending_options,
            )
            issues.append(
                CsvIssue(
                    receiving,
                    "sending options differ",
                    expected_row.sending_options,
                    actual_row.sending_options,
                    issue_type,
                )
            )
    return issues


def expected_rows_from_source(
    project_root: Path,
    cc_name: str,
    uc_name: str,
    source: str,
    fixture: Path | None = None,
) -> dict[str, AgreementRow]:
    if source == "fixture":
        fixture_path = fixture or UC_FIXTURES.get((cc_name, uc_name))
        if not fixture_path:
            raise ValueError(f"No fixture configured for {cc_name} -> {uc_name}")
        return load_expected_agreement_rows(fixture_path)

    if source == "live":
        url = agreement_url_for_pair(project_root, cc_name, uc_name)
        payload = fetch_assist_payload(view_by_key_from_assist_url(url))
        return parse_assist_payload(payload)

    raise ValueError(f"Unknown source: {source}")


def verify_raw_csv(
    cc_name: str,
    uc_name: str,
    *,
    project_root: Path = PROJECT_ROOT,
    source: str = "fixture",
    fixture: Path | None = None,
) -> list[CsvIssue]:
    expected = expected_rows_from_source(project_root, cc_name, uc_name, source, fixture)
    actual = raw_csv_rows(project_root, cc_name, uc_name)
    return compare_rows(expected, actual)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify raw results CSV rows against Assist data.")
    parser.add_argument("--cc", required=True)
    parser.add_argument("--uc", required=True)
    parser.add_argument("--source", choices=["fixture", "live"], default="fixture")
    parser.add_argument("--fixture", type=Path)
    args = parser.parse_args(argv)

    issues = verify_raw_csv(args.cc, args.uc, source=args.source, fixture=args.fixture)
    print(write_issue_report(issues))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
