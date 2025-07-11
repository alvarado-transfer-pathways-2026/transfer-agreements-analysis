import pandas as pd
import math
import re

def extract_course_and_credits(course_str):
    """
    Extracts course name and credits from a string like 'MATH 150 (5)'.
    Returns (course_name, credits) or (course_name, None) if credits not found.
    """
    match = re.match(r'(.+?)\s*\((\d+)\)', course_str)
    if match:
        return match.group(1).strip(), int(match.group(2))
    else:
        return course_str.strip(), None

def min_courses_for_group(df_group):
    sets = []
    cc_courses_in_group = []
    cc_credits_in_group = []
    unarticulated_in_group = []
    for set_id, df_set in df_group.groupby('Set ID'):
        cell = str(df_set.iloc[0]['Courses Group 1']).strip()
        uc_req = str(df_set.iloc[0]['Receiving']).strip()
        if cell and cell != 'nan' and cell != 'Not Articulated':
            courses = [c.strip() for c in cell.split(';') if c.strip()]
            course_names = []
            course_credits = []
            for c in courses:
                name, credits = extract_course_and_credits(c)
                course_names.append(name)
                if credits is not None:
                    course_credits.append(credits)
            sets.append({
                'articulated': True,
                'courses': len(courses),
                'cc_courses': course_names,
                'cc_credits': course_credits,
                'uc_names': df_set['UC Name'].unique(),
                'uc_req': uc_req
            })
        else:
            sets.append({
                'articulated': False,
                'courses': 1,
                'cc_courses': [],
                'cc_credits': [],
                'uc_names': df_set['UC Name'].unique(),
                'uc_req': uc_req
            })

    group_num_required = int(df_group['Num Required'].iloc[0])
    sets_sorted = sorted(sets, key=lambda x: (not x['articulated'], x['courses']))
    selected_sets = sets_sorted[:group_num_required]
    total_courses = sum(s['courses'] for s in selected_sets)
    cc_courses_in_group = []
    cc_credits_in_group = []
    unarticulated_count = sum(1 for s in selected_sets if not s['articulated'])
    ucs_with_unarticulated = set()
    unarticulated_in_group = []
    for s in selected_sets:
        cc_courses_in_group.extend(s['cc_courses'])
        cc_credits_in_group.extend(s['cc_credits'])
        if not s['articulated']:
            ucs_with_unarticulated.update(s['uc_names'])
            unarticulated_in_group.append(s['uc_req'])
    return total_courses, unarticulated_count, ucs_with_unarticulated, cc_courses_in_group, cc_credits_in_group, unarticulated_in_group

def distribute_credits_into_semesters(cc_courses, cc_credits, max_per_sem=18):
    """
    Distributes courses into semesters so that no semester exceeds max_per_sem credits.
    Returns a list of lists: each sublist is the courses in that semester.
    """
    semesters = []
    current_semester = []
    current_credits = 0
    for course, credits in sorted(zip(cc_courses, cc_credits), key=lambda x: -x[1] if x[1] is not None else 0):
        if credits is None:
            credits = 0
        if current_credits + credits > max_per_sem:
            semesters.append(current_semester)
            current_semester = [course]
            current_credits = credits
        else:
            current_semester.append(course)
            current_credits += credits
    if current_semester:
        semesters.append(current_semester)
    return semesters

def calculating_cc_years(cc_csv_path, selected_ucs):
    df = pd.read_csv(cc_csv_path)
    df = df[df['UC Name'].isin(selected_ucs)]

    total_courses = 0
    total_unarticulated = 0
    ucs_with_unarticulated = set()
    all_cc_courses = []
    all_cc_credits = []
    all_unarticulated = []

    for group_id, df_group in df.groupby('Group ID'):
        courses, unarticulated, group_ucs_with_unarticulated, cc_courses, cc_credits, unarticulated_courses = min_courses_for_group(df_group)
        total_courses += courses
        total_unarticulated += unarticulated
        ucs_with_unarticulated.update(group_ucs_with_unarticulated)
        all_cc_courses.extend(cc_courses)
        all_cc_credits.extend(cc_credits)
        all_unarticulated.extend(unarticulated_courses)

    total_credits = sum(c for c in all_cc_credits if c is not None)
    semesters = distribute_credits_into_semesters(all_cc_courses, all_cc_credits, max_per_sem=18)
    semesters_credits = []
    for semester in semesters:
        credits = sum(
            all_cc_credits[all_cc_courses.index(course)]
            for course in semester
            if all_cc_credits[all_cc_courses.index(course)] is not None
        )
        semesters_credits.append(credits)

    semesters_needed = len(semesters)
    years_needed = math.ceil(semesters_needed / 2)

    print(f"To fulfill requirements for {selected_ucs} at this CC:")
    print(f"  - Total CC courses required: {total_courses}")
    print(f"  - Total CC credits required: {total_credits}")
    print(f"  - CC courses counted: {sorted(set(all_cc_courses))}")
    print(f"  - CC credits counted: {all_cc_credits}")
    print(f"  - Unarticulated courses: {total_unarticulated}")
    print(f"  - Unarticulated UC requirements: {sorted(set(all_unarticulated))}")
    print(f"  - Minimum semesters needed: {semesters_needed}")
    print(f"  - Minimum years needed: {years_needed}")
    for i, (semester, credits) in enumerate(zip(semesters, semesters_credits), 1):
        print(f"    Semester {i}: {credits} credits ({', '.join(semester)})")
    if ucs_with_unarticulated:
        print(f"  - UCs with unarticulated courses: {sorted(ucs_with_unarticulated)}")
    else:
        print("  - No unarticulated courses for selected UCs.")

if __name__ == "__main__":
    cc_csv_path = "/Users/yasminkabir/GitHub/transfer-agreements-analysis/calculating_years/fakecreditvals_Allan_Hancock_College_filtered - Allan_Hancock_College_filtered (1).csv"
    selected_ucs = ['UCSD', 'UCB']
    calculating_cc_years(cc_csv_path, selected_ucs)