from unit_balancer import select_courses_for_term

def main():
    eligible_courses = [
        {'courseCode': 'MATH 5A', 'units': 4},  # Major
        {'courseCode': 'CS 101', 'units': 4},   # Major
        {'courseCode': 'PHYS 2A', 'units': 5},  # Major
        { 'reqIds': ['IG_1A'], 'units': 3},  # GE
        {'reqIds': ['GE_CritThink'], 'units': 3},  # GE
        {'reqIds': ['IG_3A'], 'units': 3},  # GE
        {'reqIds': ['GE_Hist'], 'units': 3},  # GE
        {'reqIds': ['GE_Arts'], 'units': 2},  # GE
        {'courseCode': 'SOC 101', 'units': 3},  # No tag - Other (should be deprioritized)
    ]

    completed_courses = ['MATH 5A', 'GE_1A']  # Already took the major course and one GE

    max_units = 15

    selected_courses, total_units = select_courses_for_term(
        eligible_courses,
        completed_courses,
        max_units
    )

    print("Selected Courses (updated test):")
    for course in selected_courses:
        label = course.get("courseCode") or course.get("courseName")
        print(f"- {label} ({course['units']} units)")

    print(f"\nTotal Units: {total_units}")

if __name__ == "__main__":
    main()
