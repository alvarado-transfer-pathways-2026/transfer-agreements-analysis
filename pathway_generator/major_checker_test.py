#!/usr/bin/env python3
"""
Test runner for tag-based MajorChecker

Loads a course_tags JSON file for a selected CCC and tests
major fulfillment progress for each UC in the default requirement set.

Author: UC CS Transfer Planner
"""

from major_checker import MajorChecker

# === Configuration ===
CC_NAME = "foothill_college"  # lowercase, underscore
COMPLETED_COURSES = [
    "CS 1A",    # Foothill: Java 1
    "CS 1B",    # Java 2
    "MATH 1A"   # Calculus
]
TAGS_DIR = "course_tags"  # adjust if you relocate the tag files


def run_test():
    print(f"\n🎓 Testing major fulfillment for: {CC_NAME}")
    print(f"📚 Completed courses: {', '.join(COMPLETED_COURSES)}")

    checker = MajorChecker()
    result = checker.load_and_check_cc_courses(
        cc_name=CC_NAME,
        completed_course_codes=COMPLETED_COURSES,
        course_tags_dir=TAGS_DIR
    )

    print(f"\n✅ Loaded {result['total_completed']} courses from {result['cc_name']}")
    print(f"🧮 Total units: {result['total_units']}")

    print("\n📘 Course Breakdown:")
    for course in result['loaded_courses']:
        print(f"  - {course['courseCode']}: {course['courseName']} ({course['units']} units)")
        print(f"    Tags: {', '.join(course['tags'])}")

    print("\n🎯 UC Major Fulfillment Status:")
    for uc, status in result['uc_fulfillment_status'].items():
        if 'error' in status:
            print(f"  ❌ {uc}: {status['error']}")
        else:
            print(f"  ✅ {uc}: {status['completed_requirements']}/{status['total_requirements']} "
                  f"({status['completion_percentage']}%)")
            if status["remaining_details"]:
                print("     🔎 Remaining:")
                for req_id, req in status["remaining_details"].items():
                    print(f"       - {req_id}: {req['name']}")


if __name__ == "__main__":
    run_test()
