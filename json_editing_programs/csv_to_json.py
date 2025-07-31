import csv
import json
import os
import re

# Directories
input_dir = "filtered_results"
output_dir = "articulated_courses_json"
os.makedirs(output_dir, exist_ok=True)

# Helper to parse course string with units
def parse_course(raw):
    raw = raw.strip()
    match = re.match(r"(.+?)\s*\(([\d.]+)\)", raw)
    if match:
        name, units = match.groups()
        return {"course": name.strip(), "units": float(units)}
    else:
        return {"course": raw, "units": None}

# Helper to parse receiving courses (handles multiple courses separated by semicolons)
def parse_receiving_courses(receiving_raw):
    if not receiving_raw or receiving_raw.strip() == "":
        return None
    
    courses = [course.strip() for course in receiving_raw.split(";") if course.strip()]
    if len(courses) == 1:
        return courses[0]  # Single course as string
    else:
        return courses     # Multiple courses as array

# Iterate through all filtered CSVs
for filename in os.listdir(input_dir):
    if not filename.endswith("_filtered.csv"):
        continue
    
    # Extract CCC name from filename and format properly
    ccc_name = filename.replace("_filtered.csv", "").replace("_", " ")
    # Capitalize each word for the key (e.g., "de anza college" -> "De_Anza_College")
    ccc_key = "_".join([word.capitalize() for word in ccc_name.split()])
    
    input_path = os.path.join(input_dir, filename)
    output_path = os.path.join(output_dir, f"{ccc_key}_articulation.json")
    
    # Structure: {ccc_name: {UC: {requirement: {...}}}}
    college_json = {ccc_key: {}}
    
    with open(input_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            uc_name = row["UC Name"].strip()
            req_category = row["Group ID"].strip()
            set_id = row["Set ID"].strip()
            num_required_raw = row["Num Required"].strip()
            receiving_raw = row.get("Receiving", "").strip()
            
            # Parse num_required
            try:
                num_required = int(num_required_raw) if num_required_raw.isdigit() else 1
            except:
                num_required = 1
            
            # Parse receiving courses
            receiving_courses = parse_receiving_courses(receiving_raw)
            
            # Pull all course groups (e.g., Courses Group 1, Courses Group 2, etc.)
            course_groups = []
            for key in sorted([k for k in row.keys() if k.startswith("Courses Group")]):
                if row[key].strip() and "Not Articulated" not in row[key]:
                    raw_group = row[key].strip()
                    group_courses = [parse_course(course) for course in raw_group.split(";") if course.strip()]
                    if group_courses:
                        course_groups.append(group_courses)
            
            # Skip if no valid course groups found
            if not course_groups:
                continue
            
            # Initialize UC structure if needed
            if uc_name not in college_json[ccc_key]:
                college_json[ccc_key][uc_name] = {}
            
            # Handle duplicate requirements (like UCSD's Intro A vs B)
            requirement_key = req_category
            if requirement_key in college_json[ccc_key][uc_name]:
                # If we already have this requirement, check if it's the same set_id
                existing = college_json[ccc_key][uc_name][requirement_key]
                if existing["set_id"] != set_id:
                    # Different set_id, create unique key
                    requirement_key = f"{req_category}_{set_id}"
            
            # Create the requirement entry
            requirement_data = {
                "set_id": set_id,
                "num_required": num_required,
                "course_groups": course_groups
            }
            
            # Add receiving course(s) information
            if receiving_courses:
                if isinstance(receiving_courses, list):
                    requirement_data["receiving_courses"] = receiving_courses
                else:
                    requirement_data["receiving_course"] = receiving_courses
            
            college_json[ccc_key][uc_name][requirement_key] = requirement_data
    
    # Save per-college JSON
    with open(output_path, "w", encoding='utf-8') as f:
        json.dump(college_json, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Parsed {filename} → {output_path}")

print("🎉 All files processed successfully!")