import json
from ge_checker import GE_Tracker

# Load GE structure JSON
with open("prerequisites/ge_reqs.json") as f:
    ge_data = json.load(f)

# Initialize tracker and load the pattern requirements
ge = GE_Tracker(ge_data)
ge.load_pattern("IGETC")
ge.load_pattern("7CoursePattern")

# Add completed courses for IGETC (same as before)
ge.add_completed_course("English Composition", ["IG_1A"])
ge.add_completed_course("English Composition", ["IG_1A"]) # if duplicate courses are created it doesn't fulfill the requirement
ge.add_completed_course("Humanities", ["IG_3B"])
ge.add_completed_course("Humanities", ["IG_3B"]) # duplicate because of the either course requirement in IGETC 
ge.add_completed_course("Biological Science", ["IG_Biological"])
ge.add_completed_course("Laboratory Science (in either Physical or Biological)", ["IG_Lab"])


# Add some completed courses for 7CoursePattern to test
ge.add_completed_course("Written Communication Course 1", ["GE_WrittenComm"])
ge.add_completed_course("Arts & Humanities Course 1", ["GE_ArtsHum"])
# no math course added, so 1 remaining there
# no general subcategories added so taken counts should be zero

def print_remaining_requirements(pattern_id):
    remaining = ge.get_remaining_requirements(pattern_id)
    pattern = next(p for p in ge_data["requirementPatterns"] if p["patternId"] == pattern_id)

    print(f"Remaining {pattern['patternName']} Requirements:")

    for req in pattern["requirements"]:
        req_id = req["reqId"]

        if "subRequirements" in req and req["subRequirements"]:
            if pattern_id == "IGETC":
                parent_remaining = 0
                for sub in req["subRequirements"]:
                    sub_id = sub["reqId"]
                    if sub_id in remaining:
                        parent_remaining += remaining[sub_id]["courses_remaining"]

                leftover_key = f"{req_id}_Leftover"
                leftover_courses = 0
                if leftover_key in remaining:
                    leftover_courses = remaining[leftover_key]["courses_remaining"]
                    parent_remaining += leftover_courses

                print(f"- {req['name']} ({parent_remaining} course(s)):")

                for sub in req["subRequirements"]:
                    sub_id = sub["reqId"]
                    courses_left = remaining[sub_id]["courses_remaining"] if sub_id in remaining else 0
                    print(f"  - {sub['name']} ({courses_left} course(s))")

                # Always print leftover OR line, even if 0 remaining
                if leftover_key in remaining:
                    leftover_info = remaining[leftover_key]
                    print(f"  - {leftover_info['name']} ({leftover_info['courses_remaining']} course(s))")

            elif pattern_id == "7CoursePattern" and req_id == "GE_General":
                parent_remaining = remaining.get(req_id, {}).get("courses_remaining", 0)
                print(f"- {req['name']} ({parent_remaining} course(s)):")

                for sub in req["subRequirements"]:
                    sub_id = sub["reqId"]
                    taken_count = sum(1 for c in ge.completed_courses if sub_id in c.get("tags", []))
                    print(f"  - {sub['name']} (taken {taken_count} course(s))")

            else:
                parent_remaining = 0
                for sub in req["subRequirements"]:
                    sub_id = sub["reqId"]
                    if sub_id in remaining:
                        parent_remaining += remaining[sub_id]["courses_remaining"]
                print(f"- {req['name']} ({parent_remaining} course(s)):")

                for sub in req["subRequirements"]:
                    sub_id = sub["reqId"]
                    courses_left = remaining[sub_id]["courses_remaining"] if sub_id in remaining else 0
                    print(f"  - {sub['name']} ({courses_left} course(s))")

        else:
            courses_left = remaining[req_id]["courses_remaining"] if req_id in remaining else 0
            print(f"- {req['name']} ({courses_left} course(s))")

    print(f"Is {pattern['patternName']} fulfilled? {ge.is_fulfilled(pattern_id)}\n")


# Print IGETC remaining
print_remaining_requirements("IGETC")

# Print 7-Course Pattern remaining
print_remaining_requirements("7CoursePattern")
