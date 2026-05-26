from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from datetime import date
from pathlib import Path

from .apply_conjunction_overrides import DEFAULT_OVERRIDES
from .assist_parser import fetch_assist_payload, parse_assist_payload
from .common import AgreementRow, CsvIssue, PROJECT_ROOT, write_issue_report
from .verify_raw_csv import expected_rows_from_source


REQUIRED_FIELDS = {
    "cc",
    "uc",
    "uc_abbr",
    "receiving",
    "sending_options",
    "assist_url",
    "view_by_key",
    "reason",
    "reviewer",
    "reviewed_date",
}


def load_override_items(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8")).get("overrides", [])


def validate_schema(item: dict, index: int) -> list[CsvIssue]:
    issues: list[CsvIssue] = []
    missing = sorted(REQUIRED_FIELDS - set(item))
    if missing:
        issues.append(
            CsvIssue(
                item.get("receiving", f"override[{index}]"),
                "override is missing required metadata",
                missing,
                sorted(item),
                "override_schema_error",
            )
        )

    if (
        item.get("assist_url")
        and item.get("view_by_key")
        and item["view_by_key"] not in urllib.parse.unquote(item["assist_url"])
    ):
        issues.append(
            CsvIssue(
                item.get("receiving", f"override[{index}]"),
                "override view_by_key is not present in assist_url",
                item.get("view_by_key"),
                item.get("assist_url"),
                "override_schema_error",
            )
        )

    reviewed_date = item.get("reviewed_date")
    if reviewed_date:
        try:
            date.fromisoformat(reviewed_date)
        except ValueError:
            issues.append(
                CsvIssue(
                    item.get("receiving", f"override[{index}]"),
                    "override reviewed_date must be ISO formatted YYYY-MM-DD",
                    "YYYY-MM-DD",
                    reviewed_date,
                    "override_schema_error",
                )
            )

    if not item.get("reason", "").strip():
        issues.append(
            CsvIssue(
                item.get("receiving", f"override[{index}]"),
                "override reason must be non-empty",
                "non-empty reason",
                item.get("reason"),
                "override_schema_error",
            )
        )

    return issues


def normalized_override_row(item: dict) -> AgreementRow:
    return AgreementRow(
        receiving=item["receiving"],
        sending_options=tuple(tuple(option) for option in item["sending_options"]),
    ).normalized()


def source_rows_for_override(item: dict, *, source: str) -> dict[str, AgreementRow]:
    if source == "fixture":
        return expected_rows_from_source(PROJECT_ROOT, item["cc"], item["uc"], "fixture")

    payload = fetch_assist_payload(item["view_by_key"])
    return parse_assist_payload(payload)


def verify_override_item(item: dict, index: int, *, source: str) -> list[CsvIssue]:
    issues = validate_schema(item, index)
    if issues:
        return issues

    override_row = normalized_override_row(item)
    try:
        source_rows = source_rows_for_override(item, source=source)
    except Exception as exc:
        return [
            CsvIssue(
                item["receiving"],
                "could not load ASSIST source for override",
                item.get("view_by_key"),
                str(exc),
                "override_source_error",
            )
        ]

    source_row = source_rows.get(override_row.receiving)
    if source_row is None:
        return [
            CsvIssue(
                item["receiving"],
                "override receiving course no longer exists in ASSIST source",
                override_row.receiving,
                sorted(source_rows),
                "stale_override",
            )
        ]

    if source_row.sending_options != override_row.sending_options:
        return [
            CsvIssue(
                item["receiving"],
                "override sending options no longer match ASSIST source",
                source_row.sending_options,
                override_row.sending_options,
                "stale_override",
            )
        ]

    return []


def verify_overrides(
    path: Path = DEFAULT_OVERRIDES,
    *,
    source: str = "fixture",
    verbose: bool = False,
) -> list[CsvIssue]:
    items = load_override_items(path)
    if verbose:
        print(f"Validating {len(items)} reviewed override(s) using source={source}.", flush=True)

    issues: list[CsvIssue] = []
    for index, item in enumerate(items, start=1):
        if verbose:
            print(
                f"[{index}/{len(items)}] Checking {item.get('cc', '<missing cc>')} -> "
                f"{item.get('uc', '<missing uc>')} {item.get('receiving', '<missing receiving>')}...",
                flush=True,
            )
        item_issues = verify_override_item(item, index - 1, source=source)
        issues.extend(item_issues)
        if verbose:
            status = "PASS" if not item_issues else f"FAIL issues={len(item_issues)}"
            print(f"  {status}", flush=True)
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate reviewed conjunction override metadata and freshness.")
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    parser.add_argument("--source", choices=["fixture", "live"], default="fixture")
    parser.add_argument("--quiet", action="store_true", help="Hide per-override progress output.")
    args = parser.parse_args(argv)

    issues = verify_overrides(args.overrides, source=args.source, verbose=not args.quiet)
    print(write_issue_report(issues))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
