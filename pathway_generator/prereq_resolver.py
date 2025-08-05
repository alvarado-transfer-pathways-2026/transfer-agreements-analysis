import json

def load_prereq_data(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)
    return data

def prereq_block_satisfied(block, completed_courses):
    if not block:
        return True
    if "and" in block:
        return all(prereq_block_satisfied(subblock, completed_courses) for subblock in block["and"])
    if "or" in block:
        for item in block["or"]:
            if isinstance(item, str):
                if item in completed_courses:
                    return True
            elif isinstance(item, dict):
                if prereq_block_satisfied(item, completed_courses):
                    return True
        return False
    return False

def course_prereqs_satisfied(course, completed_courses):
    prereqs = course.get("prerequisites", None)
    if prereqs is None or prereqs == []:
        return True

    # Handle block format
    if isinstance(prereqs, dict):
        return prereq_block_satisfied(prereqs, completed_courses)
    # Handle list format (new logic for OR and AND with semicolon)
    elif isinstance(prereqs, list):
        # If any item has ';' treat as AND, else OR
        if any(';' in item for item in prereqs):
            # AND: split each string by ';' and check all parts
            for and_group in prereqs:
                parts = [part.strip() for part in and_group.split(';')]
                if not all(part in completed_courses for part in parts):
                    return False
            return True
        else:
            # OR: at least one in completed_courses
            return any(item in completed_courses for item in prereqs)
    else:
        # Unknown format - assume no prereqs
        return True

def get_eligible_courses(completed_courses, course_data, required_courses=None):
    eligible = []
    for course in course_data:
        course_code = course["courseCode"]
        if required_courses and course_code not in required_courses:
            continue
        if course_code in completed_courses:
            continue
        if course_prereqs_satisfied(course, completed_courses):
            eligible.append(course)
    return eligible
