# test_unit_balancer_complex.py

from unit_balancer import select_courses_for_term

def main():
    # Mix of Major, GE, and other courses with varying units and completion
    eligible_courses = [
        {'courseCode': 'CS 101', 'units': 4, 'tags': ['Major']},
        {'courseCode': 'CS 102', 'units': 4, 'tags': ['Major']},
        {'courseCode': 'MATH 200', 'units': 3, 'tags': ['Major']},
        {'courseCode': 'ENGL 100', 'units': 3, 'tags': ['GE']},
        {'courseCode': 'PHYS 100', 'units': 4, 'tags': ['Major']},  # will exceed units if all taken
        {'courseCode': 'HIST 150', 'units': 3, 'tags': ['GE']},
        {'courseCode': 'ART 101', 'units': 3, 'tags': ['GE']},
        {'courseCode': 'PE 101', 'units': 2, 'tags': ['GE']},
        {'courseCode': 'MUSIC 100', 'units': 1, 'tags': ['GE']},
        {'courseCode': 'SOC 200', 'units': 3, 'tags': []},  # no tag, should be ignored in prioritization
    ]

    completed_courses = ['ENGL 100']  # already done, so won't be re-added

    max_units = 15

    selected, total = select_courses_for_term(eligible_courses, completed_courses, max_units)

    print("Selected Courses (complex test):")
    for course in selected:
        print(f"- {course['courseCode']} ({course['units']} units)")

    print(f"\nTotal Units: {total}")

if __name__ == "__main__":
    main()
