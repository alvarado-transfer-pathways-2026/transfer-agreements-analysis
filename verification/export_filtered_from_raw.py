from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from .common import PROJECT_ROOT
from .verify_post_process import recompute_filtered_rows


FILTERED_DIR = PROJECT_ROOT / "filtered_results"


def write_filtered_csv(cc_name: str, *, project_root: Path = PROJECT_ROOT, output_dir: Path = FILTERED_DIR) -> Path:
    rows = recompute_filtered_rows(project_root, cc_name)
    if not rows:
        raise ValueError(f"No filtered rows produced for {cc_name}")

    max_groups = max(
        len([key for key, value in row.items() if key.startswith("Courses Group") and value])
        for row in rows
    )
    fieldnames = [
        "UC Name",
        "Group ID",
        "Set ID",
        "Num Required",
        "Receiving",
        *[f"Courses Group {index}" for index in range(1, max_groups + 1)],
    ]

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{cc_name.replace(' ', '_')}_filtered.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({fieldname: row.get(fieldname, "") for fieldname in fieldnames})
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Regenerate one filtered_results CSV from an existing raw results CSV.")
    parser.add_argument("--cc", required=True, help="Community college name, e.g. 'De Anza College'")
    parser.add_argument("--output-dir", type=Path, default=FILTERED_DIR)
    args = parser.parse_args(argv)

    try:
        path = write_filtered_csv(args.cc, output_dir=args.output_dir)
    except Exception as exc:
        print(f"ERROR {args.cc}: {exc}")
        return 1

    print(f"WROTE {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
