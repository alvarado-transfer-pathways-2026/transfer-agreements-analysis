import json
from ge_checker import GE_Tracker

# Load GE structure
with open("/Users/yasminkabir/GitHub/transfer-agreements-analysis-2/prerequisites/ge_reqs.json") as f:
    ge_data = json.load(f)

# Initialize tracker
ge = GE_Tracker(ge_data)

# Simulated plan: adding placeholders with tags
ge.check_course({
    "courseId": "GE_ENG_COMP",
    "courseName": "IGETC – English Composition Placeholder",
    "units": 3,
    "tags": ["IG_1A"]
})

ge.check_course({
    "courseId": "GE_HUMANITIES",
    "courseName": "IGETC – Humanities Placeholder",
    "units": 3,
    "tags": ["IG_3B"]
})

# Check what’s still missing
missing = ge.get_remaining_requirements("IGETC")
print("Remaining IGETC Requirements:")
for req_id, info in missing.items():
    print(f"- {info['name']}: {info['courses_remaining']} course(s), {info['units_remaining']} unit(s) remaining")

# Check if all is fulfilled
print("Is IGETC fulfilled?", ge.is_fulfilled("IGETC"))


# Remaining IGETC Requirements:
# - English Communication: 2 course(s), 6 unit(s) remaining
# - Critical Thinking/English Composition: 0 course(s), 3 unit(s) remaining
# - Mathematical Concepts/Quantitative Reasoning: 1 course(s), 3 unit(s) remaining
# - Arts & Humanities: 3 course(s), 9 unit(s) remaining
# - Arts: 1 course(s), 3 unit(s) remaining
# - Social & Behavioral Sciences: 2 course(s), 6 unit(s) remaining
# - Physical & Biological Sciences: 2 course(s), 7 unit(s) remaining
# - Physical Science: 1 course(s), 3 unit(s) remaining
# - Biological Science: 1 course(s), 3 unit(s) remaining
# - Laboratory Science (in either Physical or Biological): 1 course(s), 0 unit(s) remaining
# - Ethinic Studies: 1 course(s), 3 unit(s) remaining
# Is IGETC fulfilled? False