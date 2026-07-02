from collections import defaultdict
import os
import pandas as pd
import pulp

uc_schools = ["UCSD", "UCSB", "UCSC", "UCLA", "UCB", "UCI", "UCD", "UCR", "UCM"]


def get_cc_name_from_path(file_path):
    base = os.path.basename(file_path)
    name = base.replace("_filtered.csv", "").replace(".csv", "")
    return name.replace("_", " ")


def get_requirement_options(df, combo):
    df = df.copy()
    df.columns = df.columns.str.strip()
    df['UC Name'] = df['UC Name'].str.lower().str.strip()
    combo_lower = [uc.lower() for uc in combo]
    filtered_df = df[df['UC Name'].isin(combo_lower)]

    requirements = []
    course_options = defaultdict(set)
    uc_group_map = {}
    receiving_map = {}

    for (uc, group_id), group_df in filtered_df.groupby(['UC Name', 'Group ID']):
        uc_group_map.setdefault((uc, group_id), [])
        for set_id, set_df in group_df.groupby('Set ID'):
            for idx, (_, row) in enumerate(set_df.iterrows()):
                req = (uc, group_id, set_id, idx)
                options = set()
                for col in row.index:
                    if col.lower().startswith("courses group"):
                        val = str(row[col]).strip()
                        if val and val.lower() != "not articulated" and val.lower() != "nan":
                            options.update([v.strip() for v in val.split(';') if v.strip()])

                receiving = set([r.strip() for r in str(row['Receiving']).split(';') if r.strip()])

                requirements.append(req)
                course_options[req] = options

                uc_group_map[(uc, group_id)].append(req)
                receiving_map[req] = receiving

    return requirements, course_options, uc_group_map, receiving_map


def optimal_set_cover(requirements, course_options):
    """
    Exact minimum-course selection using MILP.
    Minimizes number of selected courses while covering all coverable requirements.
    """
    course_to_reqs = defaultdict(set)
    for req in requirements:
        for course in course_options.get(req, set()):
            course_to_reqs[course].add(req)

    all_courses = sorted(course_to_reqs.keys())

    model = pulp.LpProblem("OptimalSetCover", pulp.LpMinimize)
    x = pulp.LpVariable.dicts("x", all_courses, cat="Binary")

    # Objective: minimize number of selected courses
    model += pulp.lpSum(x[c] for c in all_courses)

    # Every requirement with at least one option must be covered by at least one chosen course
    for req in requirements:
        options = sorted(course_options.get(req, set()))
        if not options:
            continue
        model += pulp.lpSum(x[c] for c in options) >= 1, f"cover_{req[0]}_{req[1]}_{req[2]}_{req[3]}"

    solver = pulp.PULP_CBC_CMD(msg=False)
    status = model.solve(solver)

    if pulp.LpStatus[status] != "Optimal":
        return set(), {}, set(requirements)

    selected_courses = {c for c in all_courses if pulp.value(x[c]) > 0.5}

    req_to_course = {}
    for req in requirements:
        for course in sorted(course_options.get(req, set())):
            if course in selected_courses:
                req_to_course[req] = course
                break

    uncovered = {req for req in requirements if req not in req_to_course}
    return selected_courses, req_to_course, uncovered


def build_uc_counts(df, combo, requirements, uc_group_map, receiving_map, req_to_course):
    uc_counts = {uc: {'articulated': set(), 'unarticulated': set()} for uc in [uc.lower() for uc in combo]}

    for uc in uc_counts:
        uc_groups = [k for k in uc_group_map if k[0] == uc]
        for group_key in uc_groups:
            group_reqs = uc_group_map[group_key]
            sets = {}
            for req in group_reqs:
                _, _, set_id, idx = req
                sets.setdefault(set_id, []).append(req)

            group_fulfilled = False
            for set_id, reqs in sets.items():
                num_required = None
                for req in reqs:
                    mask = (
                        (df['UC Name'].str.lower() == uc)
                        & (df['Group ID'] == group_key[1])
                        & (df['Set ID'] == set_id)
                    )
                    if mask.any():
                        num_required = int(df[mask]['Num Required'].iloc[0])
                        break

                fulfilled = sum(1 for req in reqs if req in req_to_course)
                if num_required is not None and fulfilled >= num_required:
                    group_fulfilled = True
                    break

            if not group_fulfilled:
                min_needed = None
                min_unfulfilled_reqs = []
                for set_id, reqs in sets.items():
                    num_required = None
                    for req in reqs:
                        mask = (
                            (df['UC Name'].str.lower() == uc)
                            & (df['Group ID'] == group_key[1])
                            & (df['Set ID'] == set_id)
                        )
                        if mask.any():
                            num_required = int(df[mask]['Num Required'].iloc[0])
                            break

                    unfulfilled_reqs = [req for req in reqs if req not in req_to_course]
                    needed = max(0, num_required - sum(1 for req in reqs if req in req_to_course)) if num_required is not None else len(unfulfilled_reqs)
                    if min_needed is None or needed < min_needed:
                        min_needed = needed
                        min_unfulfilled_reqs = unfulfilled_reqs[:needed]

                for req in min_unfulfilled_reqs:
                    uc_counts[uc]['unarticulated'].update(receiving_map[req])

    for req in requirements:
        uc, group_id, set_id, idx = req
        if req in req_to_course:
            uc_counts[uc]['articulated'].add(req_to_course[req])

    return uc_counts


def process_optimal_path(df, uc_list, txt_file="optimal_combination_output.txt", cc_name="Unknown CC"):
    combo = tuple(uc_list)
    requirements, course_options, uc_group_map, receiving_map = get_requirement_options(df, combo)
    selected_courses, req_to_course, uncovered = optimal_set_cover(requirements, course_options)
    uc_counts = build_uc_counts(df, combo, requirements, uc_group_map, receiving_map, req_to_course)

    coverable_requirements = sum(1 for req in requirements if course_options.get(req))

    print(f"Community College: {cc_name}")
    print(f"UCs included: {', '.join(uc_list)}")
    print(f"Requirements covered: {len(req_to_course)}/{coverable_requirements} coverable ({len(requirements)} total)")
    print(f"Total selected courses: {len(selected_courses)}")

    with open(txt_file, "w") as f:
        f.write(f"Community College: {cc_name}\n")
        f.write(f"UCs included: {', '.join(uc_list)}\n")
        f.write(f"Total requirements: {len(requirements)}\n")
        f.write(f"Coverable requirements: {coverable_requirements}\n")
        f.write(f"Covered requirements: {len(req_to_course)}\n")
        f.write(f"Uncovered requirements: {len(uncovered)}\n")
        f.write(f"Total selected courses: {len(selected_courses)}\n")

        f.write("\n=== Optimal Course List ===\n")
        for idx, course in enumerate(sorted(selected_courses), start=1):
            f.write(f"{idx}. {course}\n")

        f.write("\n=== Per-UC Summary ===\n")
        for uc in uc_list:
            uc_lower = uc.lower()
            art_courses = sorted(uc_counts[uc_lower]['articulated'])
            unart_courses = sorted(uc_counts[uc_lower]['unarticulated'])
            f.write(f"\n{uc}:\n")
            f.write(f"  articulated: {len(art_courses)}\n")
            f.write(f"  unarticulated: {len(unart_courses)}\n")
            f.write(f"  articulated_courses: {'; '.join(art_courses) if art_courses else '-'}\n")
            f.write(f"  unarticulated_courses: {'; '.join(unart_courses) if unart_courses else '-'}\n")


def load_csv(file_path):
    return pd.read_csv(file_path)


if __name__ == "__main__":
    file_path = "/Users/yasminkabir/Documents/GitHub/transfer-agreements-analysis/filtered_results/Allan_Hancock_College_filtered.csv" #change to path of csv of the cc/district you want

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"CSV file not found: {file_path}")

    df = load_csv(file_path)
    uc_list = uc_schools
    cc_name = get_cc_name_from_path(file_path)
    process_optimal_path(df, uc_list, cc_name=cc_name)