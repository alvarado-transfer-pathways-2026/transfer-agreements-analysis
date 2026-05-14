from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .common import PROJECT_ROOT, CsvIssue
from .verify_raw_csv import UC_FIXTURES, verify_raw_csv


def agreement_pairs_for_cc(project_root: Path, cc_name: str) -> list[tuple[str, str]]:
    agreement_path = (
        project_root
        / "cc_agreements"
        / cc_name.replace(" ", "_").replace("/", "-")
        / "agreements.txt"
    )
    pairs = []
    for line in agreement_path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        uc_name, url = line.split(":", 1)
        if url.strip().startswith("http"):
            pairs.append((cc_name, uc_name.strip()))
    return pairs


def configured_fixture_pairs(cc_name: str | None = None) -> list[tuple[str, str]]:
    pairs = sorted(UC_FIXTURES)
    if cc_name:
        pairs = [pair for pair in pairs if pair[0] == cc_name]
    return pairs


def is_probable_flattened_or(issue: CsvIssue) -> bool:
    if issue.issue_type == "flattened_or":
        return True
    if issue.message != "sending options differ":
        return False
    expected = issue.expected or ()
    actual = issue.actual or ()
    if len(actual) != 1 or len(expected) <= 1:
        return False
    flattened_expected = tuple(course for option in expected for course in option)
    return tuple(actual[0]) == flattened_expected


def report_for_pairs(
    pairs: list[tuple[str, str]],
    *,
    source: str,
    only_probable_flattened_or: bool,
) -> tuple[list[str], int]:
    lines = []
    finding_count = 0

    for cc_name, uc_name in pairs:
        try:
            issues = verify_raw_csv(cc_name, uc_name, source=source)
        except Exception as exc:
            lines.append(f"{cc_name} -> {uc_name}: ERROR: {exc}")
            continue

        if only_probable_flattened_or:
            issues = [issue for issue in issues if is_probable_flattened_or(issue)]
        else:
            issues = [issue for issue in issues if issue.message == "sending options differ"]

        if not issues:
            lines.append(f"{cc_name} -> {uc_name}: no conjunction issues found")
            continue

        finding_count += len(issues)
        lines.append(f"{cc_name} -> {uc_name}: {len(issues)} conjunction issue(s)")
        for issue in issues:
            label = "probable flattened OR" if is_probable_flattened_or(issue) else issue.message
            lines.append(f"  - {issue.receiving}: {label}")
            lines.append(f"    Assist/expected: {issue.expected}")
            lines.append(f"    CSV/current:     {issue.actual}")

    return lines, finding_count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Report likely sending-side conjunction flattening in existing results CSVs. "
            "This command reads current CSV outputs and does not rerun scraping."
        )
    )
    parser.add_argument("--cc", help="Community college name, e.g. 'De Anza College'")
    parser.add_argument("--uc", help="UC campus name. Requires --cc.")
    parser.add_argument("--source", choices=["fixture", "live"], default="fixture")
    parser.add_argument(
        "--all-configured-fixtures",
        action="store_true",
        help="Check all fixture-backed raw CSV cases.",
    )
    parser.add_argument(
        "--include-all-sending-mismatches",
        action="store_true",
        help="Include all sending option mismatches, not only probable flattened OR cases.",
    )
    parser.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="Exit with status 1 when findings are reported.",
    )
    args = parser.parse_args(argv)

    if args.uc and not args.cc:
        parser.error("--uc requires --cc")

    if args.all_configured_fixtures:
        pairs = configured_fixture_pairs(args.cc)
    elif args.cc and args.uc:
        pairs = [(args.cc, args.uc)]
    elif args.cc:
        if args.source == "fixture":
            pairs = configured_fixture_pairs(args.cc)
        else:
            pairs = agreement_pairs_for_cc(PROJECT_ROOT, args.cc)
    else:
        pairs = configured_fixture_pairs()

    if not pairs:
        print("No agreement pairs selected.")
        return 1

    lines, finding_count = report_for_pairs(
        pairs,
        source=args.source,
        only_probable_flattened_or=not args.include_all_sending_mismatches,
    )
    print("\n".join(lines))
    print(f"\nTotal findings: {finding_count}")
    return 1 if args.fail_on_issues and finding_count else 0


if __name__ == "__main__":
    sys.exit(main())
