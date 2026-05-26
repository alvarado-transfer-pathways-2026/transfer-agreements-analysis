from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .apply_conjunction_overrides import DEFAULT_OVERRIDES, load_overrides
from .assist_parser import (
    duplicate_receivings_from_payload,
    fetch_assist_payload,
    parse_assist_payload,
    taxonomy_for_assist_payload,
    view_by_key_from_assist_url,
)
from .common import AgreementRow, CsvIssue, PROJECT_ROOT, rows_by_receiving, write_issue_report
from .verify_raw_csv import UC_FIXTURES, compare_rows, expected_rows_from_source, raw_csv_row_list


REPORT_DIR = PROJECT_ROOT / "verification" / "reports"
JSON_REPORT = REPORT_DIR / "raw_assist_verification.json"
CSV_REPORT = REPORT_DIR / "raw_assist_verification_issues.csv"


def agreement_pairs_from_files(
    project_root: Path,
    *,
    cc_name: str | None = None,
    uc_name: str | None = None,
) -> list[dict[str, str]]:
    pairs: list[dict[str, str]] = []
    roots = sorted((project_root / "cc_agreements").glob("*/agreements.txt"))
    for agreement_file in roots:
        cc = agreement_file.parent.name.replace("_", " ")
        if cc_name and cc != cc_name:
            continue
        for line in agreement_file.read_text(encoding="utf-8").splitlines():
            if ":" not in line:
                continue
            uc, url = line.split(":", 1)
            uc = uc.strip()
            url = url.strip()
            if not url.startswith("http"):
                continue
            if uc_name and uc != uc_name:
                continue
            pairs.append({"cc": cc, "uc": uc, "url": url})
    return pairs


def configured_fixture_pairs() -> list[dict[str, str]]:
    pairs = []
    for cc, uc in sorted(UC_FIXTURES):
        pairs.append({"cc": cc, "uc": uc, "url": ""})
    return pairs


def issue_to_dict(issue: CsvIssue, *, exception_covered: bool = False) -> dict[str, object]:
    return {
        "receiving": issue.receiving,
        "message": issue.message,
        "issue_type": issue.issue_type,
        "expected": issue.expected,
        "actual": issue.actual,
        "exception_covered": exception_covered,
    }


def duplicate_issues(rows: list[AgreementRow], *, source_label: str) -> list[CsvIssue]:
    counts = Counter(row.normalized().receiving for row in rows)
    return [
        CsvIssue(
            receiving,
            f"duplicate {source_label} receiving row",
            count,
            None,
            "duplicate_merged_row",
        )
        for receiving, count in sorted(counts.items())
        if count > 1
    ]


def override_index(overrides_path: Path) -> set[tuple[str, str, str]]:
    if not overrides_path.exists():
        return set()
    return {
        (override.cc, override.uc, override.receiving)
        for override in load_overrides(overrides_path)
    }


def issue_is_exception_covered(issue: CsvIssue, cc: str, uc: str, overrides: set[tuple[str, str, str]]) -> bool:
    return (cc, uc, issue.receiving) in overrides


def expected_rows_and_taxonomy(
    pair: dict[str, str],
    *,
    project_root: Path,
    source: str,
    fetch_payload: Callable[[str], dict] = fetch_assist_payload,
) -> tuple[dict[str, AgreementRow], dict[str, tuple[str, ...]], set[str]]:
    cc = pair["cc"]
    uc = pair["uc"]
    if source == "fixture":
        return expected_rows_from_source(project_root, cc, uc, "fixture"), {}, set()

    view_by_key = view_by_key_from_assist_url(pair["url"])
    payload = fetch_payload(view_by_key)
    return (
        parse_assist_payload(payload),
        taxonomy_for_assist_payload(payload),
        duplicate_receivings_from_payload(payload),
    )


def verify_pair(
    pair: dict[str, str],
    *,
    project_root: Path = PROJECT_ROOT,
    source: str = "live",
    reviewed_overrides: set[tuple[str, str, str]] | None = None,
    fetch_payload: Callable[[str], dict] = fetch_assist_payload,
) -> dict[str, object]:
    reviewed_overrides = reviewed_overrides or set()
    cc = pair["cc"]
    uc = pair["uc"]
    url = pair.get("url", "")
    view_by_key = view_by_key_from_assist_url(url) if url else ""

    try:
        expected, taxonomy, duplicate_expected = expected_rows_and_taxonomy(
            pair,
            project_root=project_root,
            source=source,
            fetch_payload=fetch_payload,
        )
        actual_rows = raw_csv_row_list(project_root, cc, uc)
        actual = rows_by_receiving(actual_rows)

        duplicate_actual = {
            issue.receiving: issue.expected
            for issue in duplicate_issues(actual_rows, source_label="raw CSV")
        }
        issues = compare_rows(expected, actual)

        issue_dicts = [
            issue_to_dict(
                issue,
                exception_covered=issue_is_exception_covered(
                    issue,
                    cc,
                    uc,
                    reviewed_overrides,
                ),
            )
            for issue in issues
        ]
        unreviewed_issues = [issue for issue in issue_dicts if not issue["exception_covered"]]
        taxonomy_counts = Counter(case for cases in taxonomy.values() for case in cases)
        unclassified = [
            receiving
            for receiving, cases in taxonomy.items()
            if "unknown_unsupported_payload_shape" in cases
        ]

        if not issues:
            status = "pass"
        elif not unreviewed_issues:
            status = "reviewed_exception"
        else:
            status = "fail"

        return {
            "cc": cc,
            "uc": uc,
            "url": url,
            "view_by_key": view_by_key,
            "status": status,
            "expected_row_count": len(expected),
            "actual_row_count": len(actual),
            "issue_count": len(issues),
            "unreviewed_issue_count": len(unreviewed_issues),
            "taxonomy_counts": dict(sorted(taxonomy_counts.items())),
            "unclassified_rows": unclassified,
            "duplicate_receiving_rows": {
                "assist": sorted(duplicate_expected),
                "raw_csv": dict(sorted(duplicate_actual.items())),
            },
            "issues": issue_dicts,
        }
    except Exception as exc:
        return {
            "cc": cc,
            "uc": uc,
            "url": url,
            "view_by_key": view_by_key,
            "status": "error",
            "error": str(exc),
            "expected_row_count": 0,
            "actual_row_count": 0,
            "issue_count": 1,
            "unreviewed_issue_count": 1,
            "taxonomy_counts": {},
            "unclassified_rows": [],
            "issues": [
                {
                    "receiving": "",
                    "message": "verification error",
                    "issue_type": "verification_error",
                    "expected": None,
                    "actual": str(exc),
                    "exception_covered": False,
                }
            ],
        }


def build_report(
    pairs: list[dict[str, str]],
    *,
    project_root: Path = PROJECT_ROOT,
    source: str = "live",
    overrides_path: Path = DEFAULT_OVERRIDES,
    fetch_payload: Callable[[str], dict] = fetch_assist_payload,
    verbose: bool = False,
) -> dict[str, object]:
    reviewed_overrides = override_index(overrides_path)

    agreements = []
    status_counts = Counter()
    issue_total = 0
    unreviewed_total = 0

    if verbose:
        print(f"Starting ASSIST verification for {len(pairs)} agreement(s) using source={source}.", flush=True)

    for index, pair in enumerate(pairs, start=1):
        if verbose:
            print(f"[{index}/{len(pairs)}] Checking {pair['cc']} -> {pair['uc']}...", flush=True)

        agreement = verify_pair(
            pair,
            project_root=project_root,
            source=source,
            reviewed_overrides=reviewed_overrides,
            fetch_payload=fetch_payload,
        )
        agreements.append(agreement)
        status_counts[str(agreement["status"])] += 1
        issue_total += int(agreement["issue_count"])
        unreviewed_total += int(agreement["unreviewed_issue_count"])

        if verbose:
            print(
                "  "
                f"{str(agreement['status']).upper()} "
                f"rows={agreement['expected_row_count']} "
                f"issues={agreement['issue_count']} "
                f"unreviewed={agreement['unreviewed_issue_count']} "
                f"running_unreviewed={unreviewed_total}",
                flush=True,
            )

    taxonomy_counts = Counter()
    for agreement in agreements:
        taxonomy_counts.update(agreement.get("taxonomy_counts", {}))

    exception_count = sum(
        1
        for agreement in agreements
        for issue in agreement["issues"]
        if issue["exception_covered"]
    )
    unclassified_count = sum(len(agreement["unclassified_rows"]) for agreement in agreements)

    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "agreement_count": len(agreements),
            "row_count": sum(int(agreement["expected_row_count"]) for agreement in agreements),
            "mismatch_count": issue_total,
            "unreviewed_mismatch_count": unreviewed_total,
            "exception_count": exception_count,
            "unclassified_count": unclassified_count,
            "status_counts": dict(sorted(status_counts.items())),
            "taxonomy_counts": dict(sorted(taxonomy_counts.items())),
        },
        "agreements": agreements,
    }


def write_reports(report: dict[str, object], *, json_path: Path = JSON_REPORT, csv_path: Path = CSV_REPORT) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    fieldnames = [
        "cc",
        "uc",
        "status",
        "receiving",
        "issue_type",
        "message",
        "exception_covered",
        "expected",
        "actual",
        "url",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for agreement in report["agreements"]:
            for issue in agreement["issues"]:
                writer.writerow(
                    {
                        "cc": agreement["cc"],
                        "uc": agreement["uc"],
                        "status": agreement["status"],
                        "receiving": issue["receiving"],
                        "issue_type": issue["issue_type"],
                        "message": issue["message"],
                        "exception_covered": issue["exception_covered"],
                        "expected": issue["expected"],
                        "actual": issue["actual"],
                        "url": agreement["url"],
                    }
                )


def report_summary(report: dict[str, object]) -> str:
    metadata = report["metadata"]
    issues = [
        CsvIssue(
            f"{agreement['cc']} -> {agreement['uc']} {issue['receiving']}".strip(),
            str(issue["message"]),
            issue["expected"],
            issue["actual"],
            str(issue["issue_type"]),
        )
        for agreement in report["agreements"]
        for issue in agreement["issues"]
        if not issue["exception_covered"]
    ]
    header = (
        f"Agreements: {metadata['agreement_count']}\n"
        f"Rows checked: {metadata['row_count']}\n"
        f"Unreviewed mismatches: {metadata['unreviewed_mismatch_count']}\n"
        f"Reviewed exceptions: {metadata['exception_count']}\n"
        f"Unclassified rows: {metadata['unclassified_count']}"
    )
    return f"{header}\n\n{write_issue_report(issues)}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify all raw results CSVs against ASSIST agreements.")
    parser.add_argument("--cc", help="Community college name")
    parser.add_argument("--uc", help="UC campus name")
    parser.add_argument("--source", choices=["live", "fixture"], default="live")
    parser.add_argument("--all-agreements", action="store_true", help="Use every URL in cc_agreements.")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Hide per-agreement progress output.",
    )
    args = parser.parse_args(argv)

    if args.source == "fixture" and not args.all_agreements and not args.cc:
        pairs = configured_fixture_pairs()
    else:
        pairs = agreement_pairs_from_files(PROJECT_ROOT, cc_name=args.cc, uc_name=args.uc)

    if not pairs:
        print("No agreement pairs selected.")
        return 1

    report = build_report(
        pairs,
        source=args.source,
        overrides_path=args.overrides,
        verbose=not args.quiet,
    )
    if args.write_report:
        write_reports(report)
        print(f"Wrote {JSON_REPORT}")
        print(f"Wrote {CSV_REPORT}")

    print(report_summary(report))
    metadata = report["metadata"]
    return 1 if metadata["unreviewed_mismatch_count"] or metadata["unclassified_count"] else 0


if __name__ == "__main__":
    sys.exit(main())
