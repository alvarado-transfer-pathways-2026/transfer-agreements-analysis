from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from .common import PROJECT_ROOT, load_csv_rows, normalize_course_text, row_sending_options
from .verify_all_assist import JSON_REPORT
from .verify_post_process import UC_ABBREVIATIONS, match_requirement


UC_LABELS = {
    "University of California Berkeley": "UCB",
    "University of California Davis": "UCD",
    "University of California Irvine": "UCI",
    "University of California Los Angeles": "UCLA",
    "University of California Merced": "UCM",
    "University of California Riverside": "UCR",
    "University of California San Diego": "UCSD",
    "University of California Santa Barbara": "UCSB",
    "University of California Santa Cruz": "UCSC",
}


ROOT_CAUSE_SEVERITY = {
    "flattened_or": "high",
    "sending_grouping_mismatch": "high",
    "not_articulated_mismatch": "high",
    "missing_row": "medium",
    "duplicate_receiving_label": "low",
    "option_order_only": "low",
    "non_course_requirement_placeholder": "info",
    "non_course_requirement_duplicate": "info",
}


ROOT_CAUSE_ACTIONS = {
    "flattened_or": "Fix exporter/parser so OR alternatives remain separate course groups; verify against ASSIST.",
    "sending_grouping_mismatch": "Inspect ASSIST row and fix exporter/parser grouping; this can change AND/OR meaning.",
    "not_articulated_mismatch": "Manually inspect ASSIST and current CSV; this can change whether a requirement is available.",
    "missing_row": "Check whether the missing row is a real course requirement or an ASSIST placeholder.",
    "duplicate_receiving_label": "Check whether ASSIST repeats the same receiving course in multiple contexts; usually lower priority than grouping errors.",
    "option_order_only": "No articulation meaning change; normalize option order in verifier/exporter if desired.",
    "non_course_requirement_placeholder": "Treat as raw audit noise unless it maps to a CS requirement used downstream.",
    "non_course_requirement_duplicate": "Treat as raw audit noise from repeated non-course requirement labels.",
}


SEVERITY_ORDER = {
    "high": 0,
    "medium": 1,
    "low": 2,
    "info": 3,
    "unknown": 4,
}


def uc_label(name: str) -> str:
    return UC_LABELS.get(name, name.replace("University of California ", "UC "))


def issue_root_cause(issue: dict) -> str:
    issue_type = issue.get("issue_type", "")
    receiving = (issue.get("receiving") or "").strip()
    expected = issue.get("expected")
    actual = issue.get("actual")

    if receiving in {"", "Requirement"}:
        return "non_course_requirement_placeholder"

    if issue_type == "duplicate_merged_row":
        return "duplicate_receiving_label"

    if issue_type == "flattened_or":
        return "flattened_or"

    if issue_type == "not_articulated_mismatch":
        return "not_articulated_mismatch"

    if issue_type == "sending_options_mismatch":
        expected_options = [tuple(option) for option in (expected or [])]
        actual_options = [tuple(option) for option in (actual or [])]
        if sorted(expected_options) == sorted(actual_options):
            return "option_order_only"
        return "sending_grouping_mismatch"

    return issue_type or "unknown"


def issue_severity(root_cause: str) -> str:
    return ROOT_CAUSE_SEVERITY.get(root_cause, "unknown")


def recommended_action(root_cause: str) -> str:
    return ROOT_CAUSE_ACTIONS.get(root_cause, "Review manually; no rule has been assigned for this root cause.")


def iter_unreviewed_issues(report: dict):
    for agreement in report.get("agreements", []):
        for issue in agreement.get("issues", []):
            if issue.get("exception_covered"):
                continue
            yield agreement, issue


def load_report(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"No report found at {path}. Run: python3 -m verification.verify_all_assist --all-agreements --source live --write-report"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def print_counter(title: str, counter: Counter, *, limit: int | None = None) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    items = counter.most_common(limit)
    for key, count in items:
        print(f"{key}: {count}")
    if limit and len(counter) > limit:
        print(f"... {len(counter) - limit} more")


def summarize(report: dict, *, examples_per_group: int = 3, top: int = 20) -> dict[str, object]:
    metadata = report.get("metadata", {})
    by_uc = Counter()
    by_issue_type = Counter()
    by_root_cause = Counter()
    by_severity = Counter()
    by_uc_root_cause = Counter()
    by_receiving = Counter()
    examples: dict[tuple[str, str], list[tuple[str, str, str, object, object]]] = defaultdict(list)

    for agreement, issue in iter_unreviewed_issues(report):
        uc = uc_label(agreement.get("uc", ""))
        issue_type = issue.get("issue_type") or issue.get("message") or "unknown"
        root_cause = issue_root_cause(issue)
        severity = issue_severity(root_cause)
        receiving = issue.get("receiving") or "<blank>"

        by_uc[uc] += 1
        by_issue_type[issue_type] += 1
        by_root_cause[root_cause] += 1
        by_severity[severity] += 1
        by_uc_root_cause[(uc, root_cause)] += 1
        by_receiving[(uc, receiving, root_cause)] += 1

        key = (uc, root_cause)
        if len(examples[key]) < examples_per_group:
            examples[key].append(
                (
                    agreement.get("cc", ""),
                    issue.get("receiving") or "<blank>",
                    issue_type,
                    issue.get("expected"),
                    issue.get("actual"),
                )
            )

    return {
        "metadata": metadata,
        "by_uc": by_uc,
        "by_issue_type": by_issue_type,
        "by_root_cause": by_root_cause,
        "by_severity": by_severity,
        "by_uc_root_cause": by_uc_root_cause,
        "by_receiving": by_receiving,
        "examples": examples,
        "top": top,
    }


def print_summary(summary: dict[str, object]) -> None:
    metadata = summary["metadata"]
    print("ASSIST Verification Report Summary")
    print("=================================")
    print(f"Generated at: {metadata.get('generated_at', '<unknown>')}")
    print(f"Agreements checked: {metadata.get('agreement_count', 0)}")
    print(f"Rows checked: {metadata.get('row_count', 0)}")
    print(f"Unreviewed mismatches: {metadata.get('unreviewed_mismatch_count', 0)}")
    print(f"Unclassified rows: {metadata.get('unclassified_count', 0)}")

    print_counter("By UC", summary["by_uc"])
    print_counter("By Severity", summary["by_severity"])
    print_counter("By Issue Type", summary["by_issue_type"])
    print_counter("By Likely Root Cause", summary["by_root_cause"])
    print_counter("Top UC + Root Cause", summary["by_uc_root_cause"], limit=summary["top"])
    print_counter("Top Receiving Rows", summary["by_receiving"], limit=summary["top"])

    has_examples = any(summary["examples"].values())
    if has_examples:
        print("\nExamples")
        print("--------")
        for (uc, root_cause), rows in sorted(summary["examples"].items()):
            if not rows:
                continue
            print(f"\n{uc} / {root_cause}")
            for cc, receiving, issue_type, expected, actual in rows:
                print(f"  - {cc}: {receiving} ({issue_type})")
                print(f"    expected: {expected}")
                print(f"    actual:   {actual}")

    print("\nSuggested Next Steps")
    print("--------------------")
    print("1. Treat non_course_requirement_* rows as a verifier classification issue before manual review.")
    print("2. Investigate duplicate_receiving_label rows by checking whether ASSIST intentionally repeats the same receiving course in multiple requirement contexts.")
    print("3. Fix flattened_or and sending_grouping_mismatch rows in the exporter/parser path; these are most likely to affect articulation conclusions.")
    print("4. Manually inspect not_articulated_mismatch rows because they can change whether a requirement is considered available.")


def write_root_cause_csv(summary: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["uc", "root_cause", "count"])
        for (uc, root_cause), count in summary["by_uc_root_cause"].most_common():
            writer.writerow([uc, root_cause, count])


def triage_rows(report: dict) -> list[dict[str, object]]:
    rows = []
    for agreement, issue in iter_unreviewed_issues(report):
        root_cause = issue_root_cause(issue)
        severity = issue_severity(root_cause)
        rows.append(
            {
                "severity": severity,
                "root_cause": root_cause,
                "recommended_action": recommended_action(root_cause),
                "uc": uc_label(agreement.get("uc", "")),
                "uc_full": agreement.get("uc", ""),
                "cc": agreement.get("cc", ""),
                "status": agreement.get("status", ""),
                "receiving": issue.get("receiving") or "<blank>",
                "issue_type": issue.get("issue_type", ""),
                "message": issue.get("message", ""),
                "expected": issue.get("expected"),
                "actual": issue.get("actual"),
                "url": agreement.get("url", ""),
                "view_by_key": agreement.get("view_by_key", ""),
            }
        )

    return sorted(
        rows,
        key=lambda row: (
            SEVERITY_ORDER.get(str(row["severity"]), SEVERITY_ORDER["unknown"]),
            str(row["uc"]),
            str(row["root_cause"]),
            str(row["receiving"]),
            str(row["cc"]),
        ),
    )


def write_triage_csv(report: dict, path: Path) -> Counter:
    rows = triage_rows(report)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "severity",
        "root_cause",
        "recommended_action",
        "uc",
        "uc_full",
        "cc",
        "status",
        "receiving",
        "issue_type",
        "message",
        "expected",
        "actual",
        "url",
        "view_by_key",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    return Counter(row["severity"] for row in rows)


def normalized_option_set(options: object) -> frozenset[tuple[str, ...]]:
    if not isinstance(options, list):
        return frozenset()
    normalized = []
    for option in options:
        if not isinstance(option, list):
            continue
        courses = tuple(sorted(normalize_course_text(str(course)) for course in option if normalize_course_text(str(course))))
        if courses:
            normalized.append(courses)
    return frozenset(normalized)


def filtered_signatures_from_options(uc_abbr: str, receiving: str, options: object) -> set[tuple]:
    option_set = normalized_option_set(options)
    if not option_set:
        return set()
    signatures = set()
    for group_id, set_id, num_required in match_requirement(uc_abbr, receiving):
        signatures.add(
            (
                uc_abbr,
                group_id,
                set_id,
                str(num_required),
                normalize_course_text(receiving),
                option_set,
            )
        )
    return signatures


def actual_filtered_signatures(project_root: Path, cc: str, uc_abbr: str, receiving: str) -> set[tuple]:
    path = project_root / "filtered_results" / f"{cc.replace(' ', '_')}_filtered.csv"
    if not path.exists():
        return set()
    signatures = set()
    target_receiving = normalize_course_text(receiving)
    for row in load_csv_rows(path):
        if row.get("UC Name") != uc_abbr:
            continue
        if normalize_course_text(row.get("Receiving", "")) != target_receiving:
            continue
        option_set = frozenset(
            tuple(sorted(normalize_course_text(course) for course in option))
            for option in row_sending_options(row)
            if option
        )
        signatures.add(
            (
                uc_abbr,
                row.get("Group ID", ""),
                row.get("Set ID", ""),
                str(row.get("Num Required", "")),
                target_receiving,
                option_set,
            )
        )
    return signatures


def research_severity(root_cause: str, in_course_reqs: bool, filtered_impact: str) -> str:
    if not in_course_reqs:
        return "info"
    if filtered_impact == "no":
        return "low"
    if filtered_impact == "unknown":
        return "medium" if root_cause == "duplicate_receiving_label" else issue_severity(root_cause)
    if root_cause in {"flattened_or", "sending_grouping_mismatch", "not_articulated_mismatch"}:
        return "high"
    if root_cause == "missing_row":
        return "medium"
    if root_cause in {"option_order_only", "duplicate_receiving_label"}:
        return "low"
    return issue_severity(root_cause)


def filtered_impact_rows(report: dict, *, project_root: Path = PROJECT_ROOT) -> list[dict[str, object]]:
    rows = []
    seen_filtered_issues = set()
    for agreement, issue in iter_unreviewed_issues(report):
        uc_full = agreement.get("uc", "")
        uc_abbr = UC_ABBREVIATIONS.get(uc_full, uc_label(uc_full))
        cc = agreement.get("cc", "")
        receiving = issue.get("receiving") or ""
        root_cause = issue_root_cause(issue)
        dedupe_key = (cc, uc_abbr, normalize_course_text(receiving), root_cause)
        if dedupe_key in seen_filtered_issues:
            continue
        seen_filtered_issues.add(dedupe_key)

        matches = match_requirement(uc_abbr, receiving)
        in_course_reqs = bool(matches)
        actual_filtered = actual_filtered_signatures(project_root, cc, uc_abbr, receiving)
        in_filtered_results = bool(actual_filtered)

        expected_filtered = filtered_signatures_from_options(uc_abbr, receiving, issue.get("expected"))
        if not in_course_reqs:
            filtered_impact = "no"
        elif expected_filtered:
            filtered_impact = "yes" if expected_filtered != actual_filtered else "no"
        elif root_cause == "option_order_only":
            filtered_impact = "no"
        else:
            filtered_impact = "unknown"

        rows.append(
            {
                "research_severity": research_severity(root_cause, in_course_reqs, filtered_impact),
                "filtered_impact": filtered_impact,
                "in_course_reqs": in_course_reqs,
                "in_filtered_results": in_filtered_results,
                "root_cause": root_cause,
                "raw_severity": issue_severity(root_cause),
                "uc": uc_abbr,
                "uc_full": uc_full,
                "cc": cc,
                "receiving": receiving or "<blank>",
                "issue_type": issue.get("issue_type", ""),
                "message": issue.get("message", ""),
                "expected_raw": issue.get("expected"),
                "actual_raw": issue.get("actual"),
                "expected_filtered": sorted(map(str, expected_filtered)),
                "actual_filtered": sorted(map(str, actual_filtered)),
                "recommended_action": filtered_impact_action(root_cause, in_course_reqs, filtered_impact),
                "url": agreement.get("url", ""),
                "view_by_key": agreement.get("view_by_key", ""),
            }
        )

    return sorted(
        rows,
        key=lambda row: (
            SEVERITY_ORDER.get(str(row["research_severity"]), SEVERITY_ORDER["unknown"]),
            str(row["filtered_impact"]),
            str(row["uc"]),
            str(row["root_cause"]),
            str(row["receiving"]),
            str(row["cc"]),
        ),
    )


def filtered_impact_action(root_cause: str, in_course_reqs: bool, filtered_impact: str) -> str:
    if not in_course_reqs:
        return "No CS-filtered impact: receiving course is not configured in course_reqs.py."
    if filtered_impact == "no":
        return "No semantic filtered_results difference detected; keep as audit context."
    if filtered_impact == "unknown":
        return "Maps to course_reqs.py, but filtered impact cannot be inferred from raw issue alone; inspect manually."
    return recommended_action(root_cause)


def write_filtered_impact_csv(report: dict, path: Path, *, project_root: Path = PROJECT_ROOT) -> Counter:
    rows = filtered_impact_rows(report, project_root=project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "research_severity",
        "filtered_impact",
        "in_course_reqs",
        "in_filtered_results",
        "root_cause",
        "raw_severity",
        "uc",
        "uc_full",
        "cc",
        "receiving",
        "issue_type",
        "message",
        "expected_raw",
        "actual_raw",
        "expected_filtered",
        "actual_filtered",
        "recommended_action",
        "url",
        "view_by_key",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return Counter(row["research_severity"] for row in rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize raw ASSIST verification reports by issue type and likely root cause.")
    parser.add_argument("--report", type=Path, default=JSON_REPORT)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--examples", type=int, default=3)
    parser.add_argument("--write-root-cause-csv", type=Path)
    parser.add_argument("--write-triage-csv", type=Path)
    parser.add_argument("--write-filtered-impact-csv", type=Path)
    args = parser.parse_args(argv)

    try:
        report = load_report(args.report)
    except FileNotFoundError as exc:
        print(exc)
        return 1

    summary = summarize(report, examples_per_group=args.examples, top=args.top)
    print_summary(summary)

    if args.write_root_cause_csv:
        write_root_cause_csv(summary, args.write_root_cause_csv)
        print(f"\nWrote {args.write_root_cause_csv}")

    if args.write_triage_csv:
        severity_counts = write_triage_csv(report, args.write_triage_csv)
        print(f"\nWrote {args.write_triage_csv}")
        print("Triage severity counts:")
        for severity, count in sorted(severity_counts.items(), key=lambda item: SEVERITY_ORDER.get(item[0], SEVERITY_ORDER["unknown"])):
            print(f"  {severity}: {count}")

    if args.write_filtered_impact_csv:
        severity_counts = write_filtered_impact_csv(report, args.write_filtered_impact_csv)
        print(f"\nWrote {args.write_filtered_impact_csv}")
        print("Filtered-impact research severity counts:")
        for severity, count in sorted(severity_counts.items(), key=lambda item: SEVERITY_ORDER.get(item[0], SEVERITY_ORDER["unknown"])):
            print(f"  {severity}: {count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
