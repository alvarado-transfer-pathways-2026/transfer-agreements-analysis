import os
import pandas as pd
import math
import re

def extract_course_and_credits(course_str):
    match = re.match(r'(.+?)\s*\((\d+(?:\.\d+)?)\)', course_str)
    if match:
        return match.group(1).strip(), float(match.group(2))
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

def process_cc_file(cc_csv_path, selected_ucs, output_csv_path):
    df = pd.read_csv(cc_csv_path)
    df = df[df['UC Name'].isin(selected_ucs)]
    course_credit_dict = {}
    course_uc_dict = {}  # course name -> set of UCs it fulfills
    unarticulated_uc_map = {}  # uc_name -> set of unarticulated requirements

    for (uc_name, group_id), df_group in df.groupby(['UC Name', 'Group ID']):
        _, _, _, cc_courses, cc_credits, unarticulated_courses = min_courses_for_group(df_group)
        for course, credit in zip(cc_courses, cc_credits):
            if course not in course_credit_dict or (credit is not None and credit > course_credit_dict[course]):
                course_credit_dict[course] = credit
            if course not in course_uc_dict:
                course_uc_dict[course] = set()
            course_uc_dict[course].add(uc_name)
        if unarticulated_courses:
            if uc_name not in unarticulated_uc_map:
                unarticulated_uc_map[uc_name] = set()
            unarticulated_uc_map[uc_name].update(unarticulated_courses)

    unique_cc_courses = list(course_credit_dict.keys())
    unique_cc_credits = [course_credit_dict[c] for c in unique_cc_courses]
    semesters = distribute_credits_into_semesters(unique_cc_courses, unique_cc_credits, max_per_sem=18)

    # --- CSV Output ---
    rows = []
    for i, semester in enumerate(semesters, 1):
        for course in semester:
            credit = course_credit_dict[course]
            ucs_fulfilled = "; ".join(sorted(course_uc_dict[course]))
            rows.append({
                'Semester': i,
                'Course': course,
                'Credits': credit,
                'UCs Fulfilled': ucs_fulfilled
            })

    # Add unarticulated courses as rows labeled "UNARTICULATED"
    for uc, reqs in unarticulated_uc_map.items():
        for req in sorted(reqs):
            rows.append({
                'Semester': 'UNARTICULATED',
                'Course': req,
                'Credits': '',
                'UCs Fulfilled': uc
            })

    semester_df = pd.DataFrame(rows)
    semester_df.to_csv(output_csv_path, index=False)

    
if __name__ == "__main__":
    selected_ucs = ['UCSD', 'UCSB', 'UCSC', 'UCB', 'UCLA', 'UCI', 'UCM', 'UCD', 'UCR']  # set as needed
    input_folder = "/Users/yasminkabir/GitHub/transfer-agreements-analysis/filtered_results"  # folder with CC csvs
    output_folder = "semester_breakdown_ccs"
    os.makedirs(output_folder, exist_ok=True)
    for filename in os.listdir(input_folder):
        if filename.endswith(".csv"):
            cc_csv_path = os.path.join(input_folder, filename)
            cc_name = os.path.splitext(filename)[0]
            output_csv_path = os.path.join(output_folder, f"{cc_name}_semester_breakdown.csv")
            process_cc_file(cc_csv_path, selected_ucs, output_csv_path)
            print(f"Processed {filename} -> {output_csv_path}")