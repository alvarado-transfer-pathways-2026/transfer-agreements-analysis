from unit_balancer import select_courses_for_term

def main():
    candidates = [
        {'courseCode': 'MATH 5A', 'units': 4},  # Major
        {'courseCode': 'CS 101', 'units': 4},   # Major
        {'courseCode': 'PHYS 2A', 'units': 5},  # Major
        {'courseCode': 'IG_1A', 'reqIds': ['IG_1A'], 'units': 3},  # GE
        {'courseCode': 'GE_CritThink', 'reqIds': ['GE_CritThink'], 'units': 3},  # GE
        {'courseCode': 'IG_3A', 'reqIds': ['IG_3A'], 'units': 3},  # GE
        {'courseCode': 'GE_Hist', 'reqIds': ['GE_Hist'], 'units': 3},  # GE
        {'courseCode': 'GE_Arts', 'reqIds': ['GE_Arts'], 'units': 2},  # GE
        {'courseCode': 'SOC 101', 'units': 3},  # No tag - Other (should be deprioritized)
    ]

    completed = {'MATH 5A', 'IG_1A'}  # Already took one major and one GE
    uc_to_cc_map = {
        'UC_COURSE_A': [['CS 101'], ['PHYS 2A', 'MATH 5A']],
        'UC_COURSE_B': [['SOC 101']],
    }
    all_cc_course_codes = {c['courseCode'] for c in candidates}

    selected_courses, total_units, pruned_codes = select_courses_for_term(
        candidates,
        completed,
        uc_to_cc_map,
        all_cc_course_codes,
        MAX_UNITS=15
    )

    print("Selected Courses (updated test):")
    for course in selected_courses:
        print(f"- {course['courseCode']} ({course['units']} units)")

    print(f"\nTotal Units: {total_units}")
    print(f"Pruned Codes: {sorted(pruned_codes)}")

if __name__ == "__main__":
    main()
