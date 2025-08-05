import json

def load_prereq_data(json_path):
    """Load JSON prereq data from file."""
    with open(json_path, "r") as f:
        data = json.load(f)
    # Convert list to dict keyed by courseCode for quick lookup
    return {course["courseCode"]: course for course in data}

def prereq_block_satisfied(block, completed_courses, depth=0):
    """
    Recursively check if a prereq block is satisfied by completed courses.
    A block is a dict with either "and" or "or" keys.
    """
    indent = "  " * depth
    if block is None or block == []:
        print(f"{indent}Empty block or None -> True")
        return True

    if "and" in block:
        print(f"{indent}Checking AND block: {block['and']}")
        result = all(prereq_block_satisfied(subblock, completed_courses, depth+1) for subblock in block["and"])
        print(f"{indent}AND block result: {result}")
        return result

    if "or" in block:
        print(f"{indent}Checking OR block: {block['or']}")
        for item in block["or"]:
            if isinstance(item, str):
                print(f"{indent}Checking course code '{item}' in completed_courses")
                if item in completed_courses:
                    print(f"{indent}Found '{item}' -> True")
                    return True
            elif isinstance(item, dict):
                print(f"{indent}Checking nested block in OR")
                if prereq_block_satisfied(item, completed_courses, depth+1):
                    print(f"{indent}Nested block in OR -> True")
                    return True
        print(f"{indent}OR block result: False")
        return False

    print(f"{indent}Unknown block format: {block} -> False")
    return False

def course_prereqs_satisfied(course, completed_courses):
    """
    Check if the given course's prerequisites are satisfied by completed_courses.
    course is a dict with a 'prerequisites' key (dict or empty).
    """
    prereqs = course.get("prerequisites")
    if not prereqs:  # Covers None, [], {}, ''
        print(f"Course {course['courseCode']} has no prereqs -> True")
        return True
    print(f"Checking prereqs for course {course['courseCode']}")
    return prereq_block_satisfied(prereqs, completed_courses)

def get_eligible_courses(completed_courses, course_data):
    """
    Given a set of completed courses and all course data dict,
    return list of course dicts eligible to take (prereqs met).
    """
    eligible = []
    print(f"Completed courses: {completed_courses}")
    for course_code, course in course_data.items():
        if course_code in completed_courses:
            print(f"Skipping {course_code} (already completed)")
            continue
        if course_prereqs_satisfied(course, completed_courses):
            print(f"Eligible: {course_code} (Prereqs met)")
            eligible.append(course)
        else:
            print(f"Not eligible: {course_code} (Prereqs NOT met)")
    return eligible


# #!/usr/bin/env python3
# """
# prereq_resolver.py - Determines which CCC courses are eligible to be taken
# based on prerequisite data and previously completed courses.

# Each course has a list of prerequisite blocks.
# - Each block is either "and" or "or"
# - All blocks must be satisfied to unlock the course
# """

# import json
# from typing import Dict, List, Set, Any


# def load_prereq_data(prereq_path: str) -> Dict[str, dict]:
#     """
#     Load CCC course prerequisite data from a JSON file.
#     Returns a dictionary: courseCode -> { metadata }
#     """
#     try:
#         with open(prereq_path, "r", encoding="utf-8") as f:
#             raw_data = json.load(f)

#         return {entry["courseCode"]: entry for entry in raw_data}
        
#     except FileNotFoundError:
#         raise FileNotFoundError(f"Prerequisite file not found: {prereq_path}")
#     except json.JSONDecodeError as e:
#         raise json.JSONDecodeError(f"Invalid JSON in file {prereq_path}: {str(e)}", e.doc, e.pos)


# def has_met_prereqs(course_code: str, completed: Set[str], prereq_data: Dict[str, dict]) -> bool:
#     """
#     Check if a course's prerequisites are fully met.
#     Returns True if all prereq blocks are satisfied.
#     """
#     course = prereq_data.get(course_code)
#     prereqs = course.get("prerequisites") if course else None
#     if not prereqs:
#         return True

#     # Case A: a simple list of course‐code strings → implicit AND
#     if isinstance(prereqs, list) and prereqs and all(isinstance(b, str) for b in prereqs):
#         return all(item in completed for item in prereqs)

#     # Case B: mixed or explicit blocks
#     for block in prereqs:
#         # single string entries → treat as singleton AND
#         if isinstance(block, str):
#             if block not in completed:
#                 return False
#             else:
#                 continue

#         # otherwise expect a dict with 'type' and 'items'
#         block_type = block.get("type", "").lower()
#         items = block.get("items", [])

#         if block_type == "and":
#             if not all(item in completed for item in items):
#                 return False
#         elif block_type == "or":
#             if not any(item in completed for item in items):
#                 return False
#         # silently skip unknown block types

#     return True


# def get_eligible_courses(completed: Set[str], prereq_data: Dict[str, dict]) -> List[str]:
#     """
#     Return all courses not in 'completed' that can be taken based on prereqs.
#     Each entry is the original prereq_data dict (so it carries units, courseCode, name, etc.).
#     """
#     eligible = []

#     for course_code, entry in prereq_data.items():
#         if course_code in completed:
#             continue
#         if has_met_prereqs(course_code, completed, prereq_data):
#             eligible.append(entry)

#     # Sort by courseCode for deterministic ordering
#     return sorted(eligible, key=lambda e: e.get("courseCode", ""))


# def explain_unmet_prereqs(course_code: str, completed: Set[str], prereq_data: Dict[str, dict]) -> List[str]:
#     """
#     Return a list of unmet course codes required to unlock the given course.
#     Only includes unmet items; useful for tooltips or debugging.
#     """
#     course = prereq_data.get(course_code)
#     if not course or not course.get("prerequisites"):
#         return []

#     unmet = []

#     for block in course["prerequisites"]:
#         block_type = block.get("type", "").lower()
#         items = block.get("items", [])

#         if block_type == "and":
#             unmet += [c for c in items if c not in completed]
#         elif block_type == "or":
#             if not any(c in completed for c in items):
#                 unmet += items  # Must show all OR options if none are completed

#     return list(set(unmet))  # remove duplicates


# # Test stub
# if __name__ == "__main__":
#     # Sample test data - you can replace with actual file loading
#     test_data = [
#         {
#             "courseCode": "MATH 1A",
#             "courseName": "Calculus I", 
#             "units": 5,
#             "prerequisites": []
#         },
#         {
#             "courseCode": "CS 1A",
#             "courseName": "Introduction to Java",
#             "units": 4.5,
#             "prerequisites": []
#         },
#         {
#             "courseCode": "CS 1B", 
#             "courseName": "Intermediate Java",
#             "units": 4.5,
#             "prerequisites": [
#                 {
#                     "type": "and",
#                     "items": ["CS 1A", "MATH 1A"]
#                 }
#             ]
#         },
#         {
#             "courseCode": "CS 2A",
#             "courseName": "Data Structures",
#             "units": 4.5,
#             "prerequisites": [
#                 {
#                     "type": "and", 
#                     "items": ["CS 1B"]
#                 },
#                 {
#                     "type": "or",
#                     "items": ["MATH 1B", "MATH 1C"]
#                 }
#             ]
#         },
#         {
#             "courseCode": "CS 1C",
#             "courseName": "Advanced Java",
#             "units": 4.5,
#             "prerequisites": [
#                 {
#                     "type": "or",
#                     "items": ["CS 1B", "CS 2A"]
#                 }
#             ]
#         }
#     ]
    
#     # Convert to the expected format
#     prereqs = {entry["courseCode"]: entry for entry in test_data}
#     completed_courses = {"MATH 1A", "CS 1A"}

#     print("=== Prerequisite Resolver Test ===")
#     print(f"Completed courses: {completed_courses}")
#     print()

#     eligible = get_eligible_courses(completed_courses, prereqs)
#     print("✅ Eligible courses to take:")
#     for c in eligible:
#         print(f"  - {c}: {prereqs[c]['courseName']}")

#     print("\n🔍 Missing prerequisites for CS 2A:")
#     unmet = explain_unmet_prereqs("CS 2A", completed_courses, prereqs)
#     print(f"  {unmet}")

#     print("\n🔍 Missing prerequisites for CS 1C:")
#     unmet = explain_unmet_prereqs("CS 1C", completed_courses, prereqs) 
#     print(f"  {unmet}")