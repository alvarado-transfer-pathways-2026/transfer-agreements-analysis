import csv
import json
import os
import re

# Input/output folders
input_dir = "results"
output_dir = "articulated_courses_json"
os.makedirs(output_dir, exist_ok=True)

# Strip units and clean course names
def clean_course(course_str):
    course_str = course_str.strip()
    return re.sub(r"\s*\([\d.]+\)", "", course_str)

# Parse a single group: e.g., "CIS 22A; CIS 22B" → ["CIS 22A", "CIS 22B"]
def parse_group(raw_group):
    return [clean_course(course) for course in raw_group.split(";") if course.strip()]

# Process all *_allUC.csv files
for filename in os.listdir(input_dir):
    if not filename.endswith("_allUC.csv"):
        continue

    # Extract CCC name from filename (e.g., "De_Anza_College")
    ccc_name = filename.replace("_allUC.csv", "")
    output_path = os.path.join(output_dir, f"{ccc_name}_articulation.json")

    uc_data = {}

    with open(os.path.join(input_dir, filename), encoding="utf-8") as f:
        reader = csv.DictReader(f)
        group_columns = [col for col in reader.fieldnames if col.startswith("Courses Group")]

        for row in reader:
            uc_name = row["UC Campus"].strip()
            uc_requirement = row["UC Course Requirement"].strip()

            if not uc_name or not uc_requirement:
                continue  # Skip malformed rows

            course_groups = []
            for col in group_columns:
                raw = row[col].strip()
                if raw and "Not Articulated" not in raw:
                    group = parse_group(raw)
                    if group:
                        course_groups.append(group)

            # Initialize UC entry if not already there
            if uc_name not in uc_data:
                uc_data[uc_name] = []

            # Always append, even if course_groups is empty
            uc_data[uc_name].append({
                "uc_requirement": uc_requirement,
                "num_required": 1,
                "course_groups": course_groups,
                "articulated": bool(course_groups)
})

    # Wrap in CCC name as top-level key
    final_json = {ccc_name: uc_data}

    # Write to output
    with open(output_path, "w", encoding="utf-8") as f_out:
        json.dump(final_json, f_out, indent=2, ensure_ascii=False)

    print(f"✅ Parsed {filename} → {output_path}")

print("🎉 All *_allUC.csv files processed successfully!")
