import json

def load_prereq_data(json_path):
    """Load JSON prereq data from file."""
    with open(json_path, "r") as f:
        data = json.load(f)
    # Convert list to dict keyed by courseCode for quick lookup
    return {course["courseCode"]: course for course in data}

def prereq_block_satisfied(block, completed_courses):
    """
    Recursively check if a prereq block is satisfied by completed courses.
    Supports nested dict blocks with "and"/"or".
    """
    if block is None or block == []:
        return True

    if isinstance(block, list):
        # If block is a list of course codes, treat as AND of all
        return all(item in completed_courses for item in block if isinstance(item, str))

    if isinstance(block, dict):
        if "and" in block:
            return all(prereq_block_satisfied(subblock, completed_courses) for subblock in block["and"])
        if "or" in block:
            return any(
                prereq_block_satisfied(item, completed_courses) if isinstance(item, dict) else (item in completed_courses)
                for item in block["or"]
            )

    # If block is a string (single course code), check directly
    if isinstance(block, str):
        return block in completed_courses

    return False

def course_prereqs_satisfied(course, completed_courses):
    """
    Check if the given course's prerequisites are satisfied by completed_courses.
    Supports:
      - None or empty prereqs -> True
      - Flat list of course codes (AND logic)
      - Nested dict with "and"/"or"
      - Single course code string
    """
    prereqs = course.get("prerequisites")
    if not prereqs:
        return True
    return prereq_block_satisfied(prereqs, completed_courses)

def get_eligible_courses(completed_courses, course_data):
    """
    Given a set of completed courses and all course data dict,
    return list of course dicts eligible to take (prereqs met).
    """
    eligible = []
    for course_code, course in course_data.items():
        if course_code in completed_courses:
            continue
        if course_prereqs_satisfied(course, completed_courses):
            eligible.append(course)
    return eligible
