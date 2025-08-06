# test_prereq_resolver.py

from prereq_resolver import get_eligible_courses, load_prereq_data

def main():
    # TODO: Replace this path with the actual path to your JSON prereqs file
    prereq_json_path = "/Users/yasminkabir/GitHub/transfer-agreements-analysis-3/prerequisites/cabrillo_college_prereqs.json"

    course_data = load_prereq_data(prereq_json_path)

    # Example completed courses (you can change this to test)
    # completed_courses = {"MATH 1A", "MATH 2B"}

    # required_courses = {"MATH 1A", "MATH 1B", "MATH 1C", "MATH 1D", "MATH 2A", "MATH 2B", "CIS 22A", "MATH 22"}
    
    completed_courses = {"MATH 5A", "CS 11"}
    required_courses = {"MATH 5A", "MATH 5B", "CS 11", "MATH 23"}

    # Pass the course_data to get_eligible_courses
    eligible_courses = get_eligible_courses(completed_courses, course_data, required_courses)

    print("Eligible courses given completed courses:")
    print(f"Completed courses: {completed_courses}\n")
    for c in eligible_courses:
        print(f"{c['courseCode']}: {c['courseName']} (Units: {c['units']})")

if __name__ == "__main__":
    main()
