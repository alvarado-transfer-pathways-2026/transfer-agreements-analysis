import json
from ge_checker import GE_Tracker

# Load GE structure
with open("prerequisites/ge_reqs.json") as f:
    ge_data = json.load(f)

# Initialize tracker
ge = GE_Tracker(ge_data)

# Simulated plan: adding placeholders with tags
ge.check_course({
    "courseId": "GE_ENG_COMP",
    "courseName": "IGETC – English Composition Placeholder",
    "units": 3,
    "tags": ["IG_1A"]  # Fulfilled English Composition subreq
})

ge.check_course({
    "courseId": "GE_HUMANITIES",
    "courseName": "IGETC – Humanities Placeholder",
    "units": 3,
    "tags": ["IG_3B"]  # Fulfilled Humanities subreq
})

# Fetch remaining requirements
remaining = ge.get_remaining_requirements("IGETC")

print("Remaining IGETC Requirements:")

pattern = next(p for p in ge_data["requirementPatterns"] if p["patternId"] == "IGETC")

for req in pattern["requirements"]:
    req_id = req["reqId"]
    # If has subrequirements, print the group name then each sub
    if "subRequirements" in req and req["subRequirements"]:
        print(f"- {req['name']}:")
        for sub in req["subRequirements"]:
            sub_id = sub["reqId"]
            courses_left = 0
            if sub_id in remaining and isinstance(remaining[sub_id], dict):
                courses_left = remaining[sub_id].get('courses_remaining', 0)
            print(f"  - {sub['name']} ({courses_left} course(s))")

        # Check leftover OR groups (like Arts OR Humanities extra)
        leftover_key = f"{req_id}_Leftover"
        if leftover_key in remaining:
            leftover_info = remaining[leftover_key]
            if isinstance(leftover_info, dict):
                print(f"  - {leftover_info.get('name', 'Additional Option')} ({leftover_info.get('courses_remaining', 0)} course(s))")
            else:
                print(f"  - {leftover_info}")
    else:
        # No subrequirements, just print courses remaining or zero if fulfilled
        courses_left = 0
        if req_id in remaining and isinstance(remaining[req_id], dict):
            courses_left = remaining[req_id].get('courses_remaining', 0)
        print(f"- {req['name']} ({courses_left} course(s))")

print("Is IGETC fulfilled?", ge.is_fulfilled("IGETC"))
