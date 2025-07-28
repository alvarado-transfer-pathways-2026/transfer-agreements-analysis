import csv
import json
import os
import re

# Directories
input_dir = "filtered_results"
output_dir = "articulated_course_json"
os.makedirs(output_dir, exist_ok=True)

# Go through all *_filtered.csv files
for filename in os.listdir(input_dir):
    if not filename.endswith("_filtered.csv"):
        continue

    input_path = os.path.join(input_dir, filename)

    # Clean college name from filename
    ccc_name = filename.replace("_filtered.csv", "").replace("_", " ")
    output_path = os.path.join(output_dir, f"{ccc_name.replace(' ', '_')}.json")

    artic_json = {}

    with open(input_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            uc_name = row['UC Name'].strip()
            req_category = row['Group ID'].strip()
            set_id = row['Set ID'].strip()
            num_required = int(row['Num Required'].strip()) if row['Num Required'].strip().isdigit() else None
            receiving_course = row['Courses Group 1'].strip()

            # Skip unarticulated entries
            if "Not Articulated" in receiving_course or receiving_course == "":
                continue

            # Parse course and unit
            match = re.match(r"(.+?)\s*\(([\d.]+)\)", receiving_course)
            if match:
                course_name, units = match.groups()
                course_obj = {
                    "course": course_name.strip(),
                    "units": float(units)
                }
            else:
                course_obj = {
                    "course": receiving_course.strip(),
                    "units": None
                }

            # Initialize structure
            if uc_name not in artic_json:
                artic_json[uc_name] = {}
            if req_category not in artic_json[uc_name]:
                artic_json[uc_name][req_category] = {
                    "SetID": set_id,
                    "NumRequired": num_required,
                    "Colleges": {}
                }
            if ccc_name not in artic_json[uc_name][req_category]["Colleges"]:
                artic_json[uc_name][req_category]["Colleges"][ccc_name] = []

            if course_obj not in artic_json[uc_name][req_category]["Colleges"][ccc_name]:
                artic_json[uc_name][req_category]["Colleges"][ccc_name].append(course_obj)

    # Write one JSON file per college
    with open(output_path, "w") as f:
        json.dump(artic_json, f, indent=2)

    print(f"✅ Created {output_path}")
