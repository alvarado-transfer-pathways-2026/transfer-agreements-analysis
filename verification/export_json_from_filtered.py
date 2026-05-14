from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from .common import PROJECT_ROOT, row_sending_options


JSON_DIR = PROJECT_ROOT / "articulated_courses_json"


def college_key(cc_name: str) -> str:
    return "_".join(word.capitalize() for word in cc_name.split())


def parse_course(raw: str) -> dict[str, object]:
    match = re.match(r"(.+?)\s*\(([\d.]+)\)$", raw.strip())
    if not match:
        return {"course": raw.strip(), "units": None}
    course, units = match.groups()
    return {"course": course.strip(), "units": float(units)}


def receiving_values(raw: str) -> list[str]:
    return [course.strip() for course in raw.split(";") if course.strip()]


def set_receiving(entry: dict, values: list[str]) -> None:
    entry.pop("receiving_course", None)
    entry.pop("receiving_courses", None)
    if len(values) == 1:
        entry["receiving_course"] = values[0]
    elif values:
        entry["receiving_courses"] = values


def merge_unique_groups(existing: list[list[dict]], new: list[list[dict]]) -> list[list[dict]]:
    merged = []
    seen = set()
    for group in existing + new:
        signature = tuple((course.get("course"), course.get("units")) for course in group)
        if signature in seen:
            continue
        seen.add(signature)
        merged.append(group)
    return merged


def build_json_for_cc(project_root: Path, cc_name: str) -> dict:
    filtered_path = project_root / "filtered_results" / f"{cc_name.replace(' ', '_')}_filtered.csv"
    key = college_key(cc_name)
    output = {key: {}}

    with filtered_path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            uc = row["UC Name"].strip()
            group_id = row["Group ID"].strip()
            set_id = row["Set ID"].strip()
            try:
                num_required = int(row["Num Required"])
            except ValueError:
                num_required = 1

            groups = [
                [parse_course(course) for course in option if course != "Not Articulated"]
                for option in row_sending_options(row)
                if option and option != ("Not Articulated",)
            ]
            groups = [group for group in groups if group]
            if not groups:
                continue

            output[key].setdefault(uc, {})
            requirement_key = group_id
            existing = output[key][uc].get(requirement_key)
            if existing and existing["set_id"] != set_id:
                requirement_key = f"{group_id}_{set_id}"
                existing = output[key][uc].get(requirement_key)

            receiving = receiving_values(row.get("Receiving", ""))
            if existing:
                existing["num_required"] = max(existing["num_required"], num_required)
                existing["course_groups"] = merge_unique_groups(existing["course_groups"], groups)
                existing_receiving = receiving_values("; ".join(existing.get("receiving_courses", [])))
                if not existing_receiving and existing.get("receiving_course"):
                    existing_receiving = [existing["receiving_course"]]
                for course in receiving:
                    if course not in existing_receiving:
                        existing_receiving.append(course)
                set_receiving(existing, existing_receiving)
                continue

            entry = {
                "set_id": set_id,
                "num_required": num_required,
                "course_groups": groups,
            }
            set_receiving(entry, receiving)
            output[key][uc][requirement_key] = entry

    return output


def write_json_for_cc(cc_name: str, *, project_root: Path = PROJECT_ROOT, output_dir: Path = JSON_DIR) -> Path:
    data = build_json_for_cc(project_root, cc_name)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{college_key(cc_name)}_articulation.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Regenerate one articulated_courses_json file from filtered_results.")
    parser.add_argument("--cc", required=True)
    parser.add_argument("--output-dir", type=Path, default=JSON_DIR)
    args = parser.parse_args(argv)

    try:
        path = write_json_for_cc(args.cc, output_dir=args.output_dir)
    except Exception as exc:
        print(f"ERROR {args.cc}: {exc}")
        return 1
    print(f"WROTE {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
