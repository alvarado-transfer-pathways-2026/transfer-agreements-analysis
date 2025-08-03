import json
import os

def parse_and_display_json(filepath):
    """Display all articulation data in a readable format (new JSON structure)"""
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading JSON: {e}")
        return

    college_name = list(data.keys())[0]
    uc_data = data[college_name]

    print(f"\n🏫 COLLEGE: {college_name}")
    print(f"📁 FILE: {os.path.basename(filepath)}")
    print(f"🎯 UC CAMPUSES: {len(uc_data)}")
    print("=" * 80)

    for uc_name, requirements in uc_data.items():
        print(f"\n📍 {uc_name} ({len(requirements)} requirements)")
        print("-" * 60)
        for entry in requirements:
            uc_req = entry.get("uc_requirement", "Unknown")
            articulated = entry.get("articulated", True)  # Default to True if missing
            print(f"\n  🔹 UC Requirement: {uc_req}")
            print(f"     Articulated: {'✅ Yes' if articulated else '❌ No'}")
            print(f"     Num Required: {entry.get('num_required', 1)}")

            course_groups = entry.get("course_groups", [])
            print(f"     Course Groups: {len(course_groups)}")

            for i, group in enumerate(course_groups, 1):
                print(f"       GROUP {i} (All required):")
                for course in group:
                    if isinstance(course, str):
                        print(f"         - {course}")
                    elif isinstance(course, dict):
                        print(f"         - {course.get('course', 'Unknown')} ({course.get('units', 'N/A')} units)")
                if i < len(course_groups):
                    print(f"       --- OR ---")
        print("-" * 60)

if __name__ == "__main__":
    filepath = os.path.join("articulated_courses_json", "Cabrillo_College_articulation.json")
    
    # Redirect stdout to a file
    with open("cabrillo_summary.txt", "w", encoding="utf-8") as out:
        from contextlib import redirect_stdout
        with redirect_stdout(out):
            parse_and_display_json(filepath)

    print("✅ Output saved to cabrillo_summary.txt")
