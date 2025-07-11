# This script will calculate the number of years it would take at a selected CC to transfer to a UC or UCs
import pandas as pd
import math

def min_courses_for_group(df_group):
    sets = []
    cc_courses_in_group = []
    unarticulated_in_group = []
    for set_id, df_set in df_group.groupby('Set ID'):
        cell = str(df_set.iloc[0]['Courses Group 1']).strip()
        uc_req = str(df_set.iloc[0]['Receiving']).strip()
        if cell and cell != 'nan' and cell != 'Not Articulated':
            courses = [c.strip() for c in cell.split(';') if c.strip()]
            sets.append({'articulated': True, 'courses': len(courses), 'cc_courses': courses, 'uc_names': df_set['UC Name'].unique(), 'uc_req': uc_req})
        else:
            sets.append({'articulated': False, 'courses': 1, 'cc_courses': [], 'uc_names': df_set['UC Name'].unique(), 'uc_req': uc_req})

    group_num_required = int(df_group['Num Required'].iloc[0])
    sets_sorted = sorted(sets, key=lambda x: (not x['articulated'], x['courses']))
    selected_sets = sets_sorted[:group_num_required]
    total_courses = sum(s['courses'] for s in selected_sets)
    unarticulated_count = sum(1 for s in selected_sets if not s['articulated'])
    ucs_with_unarticulated = set()
    cc_courses_in_group = []
    unarticulated_in_group = []
    for s in selected_sets:
        cc_courses_in_group.extend(s['cc_courses'])
        if not s['articulated']:
            ucs_with_unarticulated.update(s['uc_names'])
            unarticulated_in_group.append(s['uc_req'])
    return total_courses, unarticulated_count, ucs_with_unarticulated, cc_courses_in_group, unarticulated_in_group

def calculating_cc_years(cc_csv_path, selected_ucs):
    df = pd.read_csv(cc_csv_path)
    df = df[df['UC Name'].isin(selected_ucs)]

    total_courses = 0
    total_unarticulated = 0
    ucs_with_unarticulated = set()
    all_cc_courses = []
    all_unarticulated = []

    for group_id, df_group in df.groupby('Group ID'):
        courses, unarticulated, group_ucs_with_unarticulated, cc_courses, unarticulated_courses = min_courses_for_group(df_group)
        total_courses += courses
        total_unarticulated += unarticulated
        ucs_with_unarticulated.update(group_ucs_with_unarticulated)
        all_cc_courses.extend(cc_courses)
        all_unarticulated.extend(unarticulated_courses)

    semesters_needed = math.ceil(total_courses / 4)
    years_needed = math.ceil(semesters_needed / 2)

    print(f"To fulfill requirements for {selected_ucs} at this CC:")
    print(f"  - Total CC courses required: {total_courses}")
    print(f"  - CC courses counted: {sorted(set(all_cc_courses))}")
    print(f"  - Unarticulated courses: {total_unarticulated}")
    print(f"  - Unarticulated UC requirements: {sorted(set(all_unarticulated))}")
    print(f"  - Minimum semesters needed: {semesters_needed}")
    print(f"  - Minimum years needed: {years_needed}")
    if ucs_with_unarticulated:
        print(f"  - UCs with unarticulated courses: {sorted(ucs_with_unarticulated)}")
    else:
        print("  - No unarticulated courses for selected UCs.")

if __name__ == "__main__":
    cc_csv_path = "/Users/yasminkabir/GitHub/transfer-agreements-analysis/filtered_results/Allan_Hancock_College_filtered.csv"
    selected_ucs = ['UCSD', 'UCB']
    calculating_cc_years(cc_csv_path, selected_ucs)