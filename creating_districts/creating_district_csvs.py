import argparse
import json
import os
from collections import defaultdict

import pandas as pd


def count_total_courses(row, course_group_cols):
    """Count the number of mapped CC courses in a candidate articulation row."""
    total = 0
    for col in course_group_cols:
        cell = str(row.get(col, ""))
        if cell and cell != "Not Articulated":
            total += cell.count(";") + 1
    return total


def _normalize_name(value):
    return " ".join(str(value).strip().lower().split())


def generate_district_csvs(input_folder, output_folder, districts_json_path, verbose=True):
    """Build district-level articulation CSVs from per-college filtered CSVs."""
    os.makedirs(output_folder, exist_ok=True)

    with open(districts_json_path, "r", encoding="utf-8") as f:
        districts_data = json.load(f)["districts"]

    college_to_district = {}
    for district, info in districts_data.items():
        for college in info["colleges"]:
            college_to_district[_normalize_name(college)] = district

    district_data = defaultdict(list)

    if verbose:
        print(f"Reading all college CSVs from: {input_folder}")
    for filename in os.listdir(input_folder):
        if not filename.endswith(".csv"):
            continue

        college_name = filename.replace("_filtered.csv", "").replace("_", " ")
        file_path = os.path.join(input_folder, filename)
        df = pd.read_csv(file_path)

        lookup_name = _normalize_name(college_name)
        if lookup_name not in college_to_district:
            if verbose:
                print(f"  Warning: {college_name} not found in districts.json, skipping.")
            continue

        district_name = college_to_district[lookup_name]
        df.insert(0, "College Name", college_name)
        district_data[district_name].append(df)

    if verbose:
        print("\nCombining into district files...")
    written_files = []
    for district, dfs in district_data.items():
        combined = pd.concat(dfs, ignore_index=True)
        base_cols = ["College Name", "UC Name", "Group ID", "Set ID", "Num Required", "Receiving"]
        course_group_cols = [c for c in combined.columns if c not in base_cols]

        final_rows = []
        grouped = combined.groupby(["UC Name", "Group ID", "Set ID", "Receiving"])
        for _, group_df in grouped:
            articulated = group_df[group_df["Courses Group 1"] != "Not Articulated"]
            if not articulated.empty:
                articulated = articulated.copy()
                articulated["Total Courses"] = articulated.apply(
                    lambda r: count_total_courses(r, course_group_cols), axis=1
                )
                best_row = articulated.sort_values("Total Courses").iloc[0].drop("Total Courses")
            else:
                example_row = group_df.iloc[0].copy()
                example_row["College Name"] = "Not Articulated"
                example_row["Courses Group 1"] = "Not Articulated"
                for col in course_group_cols[1:]:
                    example_row[col] = ""
                best_row = example_row
            final_rows.append(best_row)

        final_df = pd.DataFrame(final_rows)
        safe_name = district.replace(" ", "_").replace("/", "_")
        out_csv = os.path.join(output_folder, f"{safe_name}.csv")
        final_df.to_csv(out_csv, index=False)
        written_files.append(out_csv)
        if verbose:
            print(f"  Saved {out_csv}")

    if verbose:
        print("\nAll district CSVs created successfully!")
    return written_files


def _default_paths():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    return {
        "input_folder": os.path.join(root_dir, "filtered_results"),
        "output_folder": os.path.join(root_dir, "district_csvs"),
        "districts_json_path": os.path.join(script_dir, "districts.json"),
    }


def main():
    defaults = _default_paths()
    parser = argparse.ArgumentParser(description="Generate district-level articulation CSVs.")
    parser.add_argument("--input-folder", default=defaults["input_folder"])
    parser.add_argument("--output-folder", default=defaults["output_folder"])
    parser.add_argument("--districts-json", default=defaults["districts_json_path"])
    args = parser.parse_args()

    generate_district_csvs(
        input_folder=args.input_folder,
        output_folder=args.output_folder,
        districts_json_path=args.districts_json,
    )


if __name__ == "__main__":
    main()
