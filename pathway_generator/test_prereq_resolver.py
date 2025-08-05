# test_prereq_resolver.py

from prereq_resolver import get_eligible_courses, load_prereq_data

def main():
    # TODO: Replace this path with the actual path to your JSON prereqs file
    prereq_json_path = "/Users/yasminkabir/GitHub/transfer-agreements-analysis-3/prerequisites/chabot_college_prereqs.json"

    course_data = load_prereq_data(prereq_json_path)

    # Example completed courses (you can change this to test)
    completed_courses = {"MTH 1", "MTH 15"}

    # Pass the course_data to get_eligible_courses
    eligible_courses = get_eligible_courses(completed_courses, course_data)

    print("Eligible courses given completed courses:")
    print(f"Completed courses: {completed_courses}\n")
    for c in eligible_courses:
        print(f"{c['courseCode']}: {c['courseName']} (Units: {c['units']})")

if __name__ == "__main__":
    main()
