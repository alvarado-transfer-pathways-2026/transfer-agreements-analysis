#!/usr/bin/env python3
"""
prereq_resolver.py - Determines which CCC courses are eligible to be taken
based on prerequisite data and previously completed courses.

Each course has a list of prerequisite blocks.
- Each block is either "and" or "or"
- All blocks must be satisfied to unlock the course
"""

import json
from typing import Dict, List, Set, Any


def load_prereq_data(prereq_path: str) -> Dict[str, dict]:
    """
    Load CCC course prerequisite data from a JSON file.
    Returns a dictionary: courseCode -> { metadata }
    """
    try:
        with open(prereq_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        return {entry["courseCode"]: entry for entry in raw_data}
        
    except FileNotFoundError:
        raise FileNotFoundError(f"Prerequisite file not found: {prereq_path}")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in file {prereq_path}: {str(e)}", e.doc, e.pos)


def has_met_prereqs(course_code: str, completed: Set[str], prereq_data: Dict[str, dict]) -> bool:
    """
    Check if a course's prerequisites are fully met.
    Returns True if all prereq blocks are satisfied.
    """
    course = prereq_data.get(course_code)
    if not course or not course.get("prerequisites"):
        return True  # No prereqs = always eligible

    for block in course["prerequisites"]:
        block_type = block.get("type", "").lower()  # Normalize to lowercase
        items = block.get("items", [])

        if block_type == "and":
            if not all(item in completed for item in items):
                return False
        elif block_type == "or":
            if not any(item in completed for item in items):
                return False
        # Skip unknown block types silently for robustness
        # This prevents crashes from typos like "And" vs "and"

    return True


def get_eligible_courses(completed: Set[str], prereq_data: Dict[str, dict]) -> List[str]:
    """
    Return all courses not in 'completed' that can be taken based on prereqs.
    """
    eligible = []

    for course_code in prereq_data:
        if course_code in completed:
            continue
        if has_met_prereqs(course_code, completed, prereq_data):
            eligible.append(course_code)

    return sorted(eligible)


def explain_unmet_prereqs(course_code: str, completed: Set[str], prereq_data: Dict[str, dict]) -> List[str]:
    """
    Return a list of unmet course codes required to unlock the given course.
    Only includes unmet items; useful for tooltips or debugging.
    """
    course = prereq_data.get(course_code)
    if not course or not course.get("prerequisites"):
        return []

    unmet = []

    for block in course["prerequisites"]:
        block_type = block.get("type", "").lower()
        items = block.get("items", [])

        if block_type == "and":
            unmet += [c for c in items if c not in completed]
        elif block_type == "or":
            if not any(c in completed for c in items):
                unmet += items  # Must show all OR options if none are completed

    return list(set(unmet))  # remove duplicates


# Test stub
if __name__ == "__main__":
    # Sample test data - you can replace with actual file loading
    test_data = [
        {
            "courseCode": "MATH 1A",
            "courseName": "Calculus I", 
            "units": 5,
            "prerequisites": []
        },
        {
            "courseCode": "CS 1A",
            "courseName": "Introduction to Java",
            "units": 4.5,
            "prerequisites": []
        },
        {
            "courseCode": "CS 1B", 
            "courseName": "Intermediate Java",
            "units": 4.5,
            "prerequisites": [
                {
                    "type": "and",
                    "items": ["CS 1A", "MATH 1A"]
                }
            ]
        },
        {
            "courseCode": "CS 2A",
            "courseName": "Data Structures",
            "units": 4.5,
            "prerequisites": [
                {
                    "type": "and", 
                    "items": ["CS 1B"]
                },
                {
                    "type": "or",
                    "items": ["MATH 1B", "MATH 1C"]
                }
            ]
        },
        {
            "courseCode": "CS 1C",
            "courseName": "Advanced Java",
            "units": 4.5,
            "prerequisites": [
                {
                    "type": "or",
                    "items": ["CS 1B", "CS 2A"]
                }
            ]
        }
    ]
    
    # Convert to the expected format
    prereqs = {entry["courseCode"]: entry for entry in test_data}
    completed_courses = {"MATH 1A", "CS 1A"}

    print("=== Prerequisite Resolver Test ===")
    print(f"Completed courses: {completed_courses}")
    print()

    eligible = get_eligible_courses(completed_courses, prereqs)
    print("✅ Eligible courses to take:")
    for c in eligible:
        print(f"  - {c}: {prereqs[c]['courseName']}")

    print("\n🔍 Missing prerequisites for CS 2A:")
    unmet = explain_unmet_prereqs("CS 2A", completed_courses, prereqs)
    print(f"  {unmet}")

    print("\n🔍 Missing prerequisites for CS 1C:")
    unmet = explain_unmet_prereqs("CS 1C", completed_courses, prereqs) 
    print(f"  {unmet}")