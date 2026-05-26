from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from .common import PROJECT_ROOT, course_group_columns, normalize_course_text, row_sending_options


DEFAULT_OVERRIDES = PROJECT_ROOT / "verification" / "fixtures" / "conjunction_overrides.json"


@dataclass(frozen=True)
class Override:
    cc: str
    uc: str
    uc_abbr: str
    receiving: str
    sending_options: tuple[tuple[str, ...], ...]
    reason: str = ""

    @property
    def raw_options(self) -> list[str]:
        return ["; ".join(option) for option in self.sending_options]


def load_overrides(path: Path) -> list[Override]:
    data = json.loads(path.read_text(encoding="utf-8"))
    overrides = []
    for item in data.get("overrides", []):
        overrides.append(
            Override(
                cc=item["cc"],
                uc=item["uc"],
                uc_abbr=item["uc_abbr"],
                receiving=item["receiving"],
                sending_options=tuple(tuple(option) for option in item["sending_options"]),
                reason=item.get("reason", ""),
            )
        )
    return overrides


def cc_filename(cc_name: str, suffix: str) -> str:
    return f"{cc_name.replace(' ', '_')}{suffix}"


def ensure_course_group_columns(fieldnames: list[str], option_count: int) -> list[str]:
    updated = list(fieldnames)
    existing = set(updated)
    for index in range(1, option_count + 1):
        column = f"Courses Group {index}"
        if column not in existing:
            updated.append(column)
            existing.add(column)
    return updated


def apply_options_to_row(row: dict[str, str], fieldnames: list[str], options: list[str]) -> dict[str, str]:
    updated = dict(row)
    for column in course_group_columns(fieldnames):
        updated[column] = ""
    for index, option in enumerate(options, start=1):
        updated[f"Courses Group {index}"] = option
    for column in fieldnames:
        updated.setdefault(column, "")
    return updated


def row_matches_raw(row: dict[str, str], override: Override) -> bool:
    return (
        row.get("UC Campus") == override.uc
        and normalize_course_text(row.get("UC Course Requirement", "")) == normalize_course_text(override.receiving)
    )


def row_matches_filtered(row: dict[str, str], override: Override) -> bool:
    return (
        row.get("UC Name") == override.uc_abbr
        and normalize_course_text(row.get("Receiving", "")) == normalize_course_text(override.receiving)
    )


def apply_overrides_to_csv(
    path: Path,
    overrides: list[Override],
    *,
    target: str,
    dry_run: bool,
) -> list[str]:
    if not path.exists():
        return [f"SKIP missing file: {path}"]

    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    max_options = max([len(override.raw_options) for override in overrides] + [0])
    fieldnames = ensure_course_group_columns(fieldnames, max_options)

    messages = []
    changed = False
    match_fn = row_matches_raw if target == "results" else row_matches_filtered

    updated_rows = []
    for row in rows:
        applied = None
        for override in overrides:
            if match_fn(row, override):
                applied = override
                break

        if not applied:
            updated_rows.append(row)
            continue

        before = row_sending_options(row)
        after = tuple(tuple(option) for option in applied.sending_options)
        if before == after:
            messages.append(f"UNCHANGED {path.name}: {applied.uc_abbr} {applied.receiving}")
            updated_rows.append(row)
            continue

        changed = True
        messages.append(
            f"UPDATED {path.name}: {applied.uc_abbr} {applied.receiving} "
            f"{before} -> {after}"
        )
        updated_rows.append(apply_options_to_row(row, fieldnames, applied.raw_options))

    if changed and not dry_run:
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for row in updated_rows:
                writer.writerow({column: row.get(column, "") for column in fieldnames})

    if not messages:
        messages.append(f"NO MATCHES {path}")
    return messages


def selected_overrides(
    all_overrides: list[Override],
    *,
    cc_name: str | None,
    uc_name: str | None,
) -> list[Override]:
    selected = all_overrides
    if cc_name:
        selected = [override for override in selected if override.cc == cc_name]
    if uc_name:
        selected = [override for override in selected if override.uc == uc_name or override.uc_abbr == uc_name]
    return selected


def apply_conjunction_overrides(
    *,
    project_root: Path = PROJECT_ROOT,
    overrides_path: Path = DEFAULT_OVERRIDES,
    cc_name: str | None = None,
    uc_name: str | None = None,
    target: str = "all",
    dry_run: bool = False,
) -> list[str]:
    overrides = selected_overrides(
        load_overrides(overrides_path),
        cc_name=cc_name,
        uc_name=uc_name,
    )
    if not overrides:
        return ["No overrides selected."]

    messages = []
    by_cc: dict[str, list[Override]] = {}
    for override in overrides:
        by_cc.setdefault(override.cc, []).append(override)

    for cc, cc_overrides in sorted(by_cc.items()):
        if target in {"all", "results"}:
            path = project_root / "results" / cc_filename(cc, "_allUC.csv")
            messages.extend(apply_overrides_to_csv(path, cc_overrides, target="results", dry_run=dry_run))
        if target in {"all", "filtered"}:
            path = project_root / "filtered_results" / cc_filename(cc, "_filtered.csv")
            messages.extend(apply_overrides_to_csv(path, cc_overrides, target="filtered", dry_run=dry_run))

    return messages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Apply hand-reviewed temporary conjunction overrides to existing CSV outputs."
    )
    parser.add_argument("--cc", help="Community college name, e.g. 'De Anza College'")
    parser.add_argument("--uc", help="UC campus full name or abbreviation")
    parser.add_argument("--target", choices=["all", "results", "filtered"], default="all")
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    messages = apply_conjunction_overrides(
        overrides_path=args.overrides,
        cc_name=args.cc,
        uc_name=args.uc,
        target=args.target,
        dry_run=args.dry_run,
    )
    print("\n".join(messages))
    return 0


if __name__ == "__main__":
    sys.exit(main())

