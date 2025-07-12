import pandas as pd
import math
import re

def extract_course_and_credits(course_str):
    match = re.match(r'(.+?)\s*\((\d+)\)', course_str)
    if match:
        return match.group(1).strip(), int(match.group(2))
    else:
        return course_str.strip(), None

def min_courses_for_group(df_group):
    sets = []
    group_cols = [col for col in df_group.columns if col.startswith("Courses Group")]
    for set_id, df_set in df_group.groupby('Set ID'):
        uc_req = str(df_set.iloc[0]['Receiving']).strip()
        uc_name = str(df_set.iloc[0]['UC Name']).strip()
        best_courses = None
        for col in group_cols:
            cell = str(df_set.iloc[0][col]).strip()
            if cell and cell != 'nan' and cell != 'Not Articulated':
                courses = [c.strip() for c in cell.split(';') if c.strip()]
                if best_courses is None or len(courses) < len(best_courses):
                    best_courses = courses
        if best_courses:
            course_names = []
            course_credits = []
            for c in best_courses:
                name, credits = extract_course_and_credits(c)
                course_names.append(name)
                if credits is not None:
                    course_credits.append(credits)
            sets.append({
                'articulated': True,
                'courses': len(course_names),
                'cc_courses': course_names,
                'cc_credits': course_credits,
                'uc_name': uc_name,
                'uc_req': uc_req
            })
        else:
            sets.append({
                'articulated': False,
                'courses': 1,
                'cc_courses': [],
                'cc_credits': [],
                'uc_name': uc_name,
                'uc_req': uc_req
            })
    group_num_required = int(df_group['Num Required'].iloc[0])
    sets_sorted = sorted(sets, key=lambda x: (not x['articulated'], x['courses']))
    selected_sets = sets_sorted[:group_num_required]
    total_courses = sum(s['courses'] for s in selected_sets)
    cc_courses_in_group = []
    cc_credits_in_group = []
    unarticulated_count = 0
    unarticulated_in_group = []
    ucs_with_unarticulated = set()
    for s in selected_sets:
        cc_courses_in_group.extend(s['cc_courses'])
        cc_credits_in_group.extend(s['cc_credits'])
        if not s['articulated']:
            ucs_with_unarticulated.add(s['uc_name'])
            unarticulated_count += 1
            unarticulated_in_group.append(s['uc_req'])
    return total_courses, unarticulated_count, ucs_with_unarticulated, cc_courses_in_group, cc_credits_in_group, unarticulated_in_group
def distribute_credits_into_semesters(cc_courses, cc_credits, max_per_sem=18):
    semesters = []
    current_semester = []
    current_credits = 0
    # Sort by credits descending for better packing
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

def calculating_cc_years(cc_csv_path, selected_ucs, output_csv_path=None):
    df = pd.read_csv(cc_csv_path)
    df = df[df['UC Name'].isin(selected_ucs)]

    total_courses = 0
    total_unarticulated = 0
    ucs_with_unarticulated = set()
    course_credit_dict = {}  # course name -> credits
    all_unarticulated = []

    for (uc_name, group_id), df_group in df.groupby(['UC Name', 'Group ID']):
        courses, unarticulated, group_ucs_with_unarticulated, cc_courses, cc_credits, unarticulated_courses = min_courses_for_group(df_group)
        total_courses += courses
        total_unarticulated += unarticulated
        ucs_with_unarticulated.update(group_ucs_with_unarticulated)
        # Only add unique courses, and if a course appears with different credits, keep the highest
        for course, credit in zip(cc_courses, cc_credits):
            if course not in course_credit_dict or (credit is not None and credit > course_credit_dict[course]):
                course_credit_dict[course] = credit
        all_unarticulated.extend(unarticulated_courses)

    # Use only unique courses for all calculations
    unique_cc_courses = list(course_credit_dict.keys())
    unique_cc_credits = [course_credit_dict[c] for c in unique_cc_courses]
    total_credits = sum(c for c in unique_cc_credits if c is not None)
    semesters = distribute_credits_into_semesters(unique_cc_courses, unique_cc_credits, max_per_sem=18)
    semesters_credits = []
    for semester in semesters:
        credits = sum(
            course_credit_dict[course]
            for course in semester
            if course_credit_dict[course] is not None
        )
        semesters_credits.append(credits)

    semesters_needed = len(semesters)
    years_needed = math.ceil(semesters_needed / 2)

    print(f"To fulfill requirements for {selected_ucs} at this CC:")
    print(f"  - Total CC COURSES required: {len(unique_cc_courses)}")
    print(f"  - Total CC CREDITS required: {total_credits}")
    print(f"  - CC courses counted: {sorted(unique_cc_courses)}")
    print(f"  - CC credits counted: {unique_cc_credits}")
    print(f"  - Unarticulated courses: {total_unarticulated}")
    print(f"  - Unarticulated UC requirements: {sorted(set(all_unarticulated))}")
    print(f"  - Minimum semesters needed: {semesters_needed}")
    print(f"  - Minimum years needed: {years_needed}")
    for i, (semester, credits) in enumerate(zip(semesters, semesters_credits), 1):
        print(f"    Semester {i}: {credits} credits ({', '.join(semester)})")
    if ucs_with_unarticulated:
        print(f"  - UC articulations with unarticulated courses: {sorted(ucs_with_unarticulated)}")
    else:
        print("  - No unarticulated courses for selected UCs.")

    # --- CSV Output ---
    if output_csv_path:
        rows = []
        for i, semester in enumerate(semesters, 1):
            for course in semester:
                credit = course_credit_dict[course]
                rows.append({'Semester': i, 'Course': course, 'Credits': credit})
        semester_df = pd.DataFrame(rows)
        semester_df.to_csv(output_csv_path, index=False)
        print(f"\nSemester breakdown saved to: {output_csv_path}")

if __name__ == "__main__":
    cc_csv_path = "/Users/yasminkabir/GitHub/transfer-agreements-analysis/calculating_years/fakecreditvals_Allan_Hancock_College_filtered - Allan_Hancock_College_filtered (1).csv"
    selected_ucs = ['UCSD', 'UCB']
    output_csv_path = "semester_breakdown.csv"
    calculating_cc_years(cc_csv_path, selected_ucs, output_csv_path)